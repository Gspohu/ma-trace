#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ground elevation for a tracé, and an honest climb figure out of it"""

import bisect
import math
import os
import sqlite3
import time

import requests

from . import dem_cache
from .geometry import cumulative, resample

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "cache", "elevation.sqlite")

ENDPOINT = os.environ.get("ELEVATION_ENDPOINT", "https://api.opentopodata.org/v1/eudem25m")
BATCH = 100
COOLDOWN = 1.1

# the tracé is walked on a constant step before anything is measured. Raw osm nodes
# sit anywhere from under a metre to two hundred apart, which made every figure below
# depend on how finely a mapper happened to draw that particular chemin
RESAMPLE_STEP = 20.0

# eu-dem is sepcified at 7 m rmse, its validation report measures 2.9 m overall, and
# both figures get worse exactly where we walk : under canopy and on steep ground
# Sigma is a real distance, a wavelenght well over the 25 m grid, which is what kills
# the sub cell noise without flattening a col
SMOOTH_SIGMA = 25.0
CLIMB_THRESHOLD = 1.5

# a long tracé is hundreds of points, dozens of calls to the very same host
_session = requests.Session()


class ElevationError(RuntimeError):
    pass 


def fetch(points, log=print):
    """Opentopodata caps at a hundred locations per call and one call per second"""
    heights = []

    for start in range(0, len(points), BATCH):
        chunk = points[start:start + BATCH]
        locations = "|".join("%.6f,%.6f" % (p[0], p[1]) for p in chunk)
        landed = False

        for attempt in range(6):
            response = _session.get(ENDPOINT, params={"locations": locations}, timeout=90)
            if (response.status_code == 200):
                heights.extend(row["elevation"] for row in response.json()["results"])
                landed = True
                break

            wait = 2 ** attempt
            log("   altimetrie : HTTP %d, nouvelle tentative dans %d s"
                % (response.status_code, wait))
            time.sleep(wait)

        if (not landed):
            raise ElevationError("altimetrie indisponible apres plusieurs tentatives")

        time.sleep(COOLDOWN)

    if (None in heights):
        raise ElevationError("le modele de terrain a renvoye des trous")
    return heights


def default_cache():
    """None disables the memo outright, which is what the tests want"""
    if (os.environ.get("ELEVATION_CACHE", "").lower() in ("0", "off", "no")):
        return None  

    path = os.environ.get("ELEVATION_CACHE") or CACHE_PATH
    try:
        return dem_cache.Cache(path)
    except sqlite3.Error:
        # a cache is an accelerator, never a reason to refuse to draw a walk
        return None


def sample(points, log=print, cache=False):
    """Heights for every point, asking the network only for what is not already known.

    Each trace from the web front runs in a brand new process, so an in memory memo
    would die with it. The one that pays is on disk : moving a single waypoint reuses
    every sample of the untouched parts of the tracé"""
    if (cache is False):
        cache = default_cache()

    if (cache is None):
        return fetch(points, log=log)

    known = cache.lookup(points)
    missing = []
    seen = set()

    for point in points:
        mark = dem_cache.key(point)
        if (mark not in known and mark not in seen):
            seen.add(mark)
            missing.append(point)

    if (missing):
        log("   altimetrie : %d points a recuperer, %d deja connus"
            % (len(missing), len(points) - len(missing)))
        fresh = fetch(missing, log=log)
        cache.store(zip(missing, fresh))
        known.update({dem_cache.key(p): h for p, h in zip(missing, fresh)})
    else:
        log("   altimetrie : %d points, tous en cache" % len(points))

    return [known[dem_cache.key(p)] for p in points]   


def _weights(sigma, step):
    reach = max(1, int(math.ceil(3.0 * sigma / step)))
    kernel = [math.exp(-0.5 * ((offset * step) / sigma) ** 2)
              for offset in range(-reach, reach + 1)]
    return kernel, reach


def smooth(heights, sigma=SMOOTH_SIGMA, step=RESAMPLE_STEP):
    """Gaussian low pass over the resampled grid.

    A plain moving average is a boxcar, whose frequency response rings and lets dem
    noise leak straight through. A gaussian rolls off cleanly. The reach is given in
    metres rather than in points, which only means anything on an even grid"""
    if (len(heights) < 3):
        return list(heights)

    kernel, reach = _weights(sigma, step)
    count = len(heights)
    out = []

    for i in range(count):
        total = 0.0   
        mass = 0.0
        for offset, weight in enumerate(kernel):
            j = i + offset - reach
            if (0 <= j < count):
                total += heights[j] * weight
                mass += weight

        out.append(total / mass)

    return out


def climb(heights, threshold=CLIMB_THRESHOLD):
    """Total ascent and descent, tracking turning points rather than chasing every sample.

    The reference has to follow the local extreme, not whichever height last cleared
    the floor. Anchoring it on the sample itself loses the top of each rise, and that
    loss is systematic : measured against real vosges profiles it shaved seven percent
    off, and it broke the one identity a closed loop must satisfy, D+ equal to D-"""
    if (len(heights) < 2):
        return 0.0, 0.0

    up = 0.0
    down = 0.0
    pivot = heights[0]
    extreme = heights[0]
    rising = None

    for height in heights[1:]:
        if (rising is None):
            if (height > pivot + threshold):
                rising, extreme = True, height
            elif (height < pivot - threshold):
                rising, extreme = False, height
            continue

        if (rising):
            if (height > extreme):
                extreme = height
            elif (height < extreme - threshold):
                up += extreme - pivot
                pivot, extreme, rising = extreme, height, False
        else:
            if (height < extreme):
                extreme = height
            elif (height > extreme + threshold):
                down += pivot - extreme
                pivot, extreme, rising = extreme, height, True

    # the leg still in progress hwen the walk ends counts too
    if (rising is True):
        up += max(0.0, extreme - pivot)
    elif (rising is False):
        down += max(0.0, pivot - extreme)

    return up, down


def _height_at(marks, heights, target):
    """Linear read of the smoothed profile at an arbitrary distance"""
    index = bisect.bisect_right(marks, target) - 1
    index = min(max(index, 0), len(heights) - 2)

    span = marks[index + 1] - marks[index]
    if (span <= 0.0):
        return heights[index]  

    ratio = (target - marks[index]) / span
    return heights[index] + (heights[index + 1] - heights[index]) * ratio


def profile(points, log=print, step=RESAMPLE_STEP, sigma=SMOOTH_SIGMA):
    """Heights along the tracé, and an honest climb figure.

    The measuring happens on an even grid, the answer comes back on the caller's own
    points. Those are two different things : the walker wants a height under every
    node they can see, the D+ wants a spacing that owes nothing to osm"""
    if (len(points) < 2):
        flat = sample(points, log=log)
        return {"heights": flat, "up": 0.0, "down": 0.0,
                "min": min(flat), "max": max(flat)}


    grid = resample(points, step)
    heights = smooth(sample(grid, log=log), sigma=sigma, step=step)
    up, down = climb(heights)

    grid_marks = cumulative(grid)
    aligned = [_height_at(grid_marks, heights, mark) for mark in cumulative(points)]

    return {
        "heights": aligned,
        "up": up,
        "down": down,
        "min": min(heights),
        "max": max(heights),
    }
