#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared marshalling for the two adapters that speak json, the bridge and the server"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import analyse, plan
from core.elevation import ElevationError
from core.graph import DEFAULT_MAX_SAC
from core.gpx import GpxError, read
from core.overpass import OverpassError
from core.pipeline import DEFAULT_PACE_FACTOR, DEFAULT_ROAD_PENALTY, DEFAULT_SUN_PENALTY
from core.router import NoRouteError

# what a bad request or an unreachable mirror looks like, anything outside crashes
# loudly. A real bug wearing a ploite error message is a bug nobody ever fixes
EXPECTED = (ElevationError, OverpassError, NoRouteError, GpxError, ValueError, OSError)

MIN_WAYPOINTS = 2

# a gpx bigger than this is not a walk, it is someone probing the moteur. Two hundred
# thousand points of trace fit well inside it
MAX_GPX_BYTES = 8 * 1024 * 1024

# the same fences the web front applies. They live here too because the bridge and
# the server are the real API : a NaN posted straight at them would otherwise ride
# into every edge cost and come out as an opaque routing failure
PENALTY_FLOOR = 1.0
PENALTY_CEILING = 50.0
PACE_FLOOR = 0.5
PACE_CEILING = 2.5


def _bounded(raw, low, high, label):
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError("%s illisible, donnez un nombre" % label)

    if (not math.isfinite(value) or not low <= value <= high):
        raise ValueError("%s hors bornes, entre %g et %g" % (label, low, high))
    return value


def _sac(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError("maxSac illisible, un entier de 1 a 6")

    if (not 1 <= value <= 6):
        raise ValueError("maxSac hors bornes, de 1 (T1) a 6 (T6)")
    return value


def handle_request(request, log=print):
    """A request carrying a gpx is a trace to read, anything else is a boucle to draw"""
    if (request.get("gpx")):
        return analyse_from_request(request, log=log)

    return plan_from_request(request, log=log)


def analyse_from_request(request, log=print):
    """Reads the gpx a front uploaded and describes what it crosses"""
    document = request.get("gpx") or ""
    if (len(document) > MAX_GPX_BYTES):
        raise ValueError("ce fichier gpx est trop gros")

    trace = read(document)
    return analyse(
        trace["points"],
        name=trace["name"],
        waypoints=trace["waypoints"],
        with_elevation=bool(request.get("withElevation", True)),
        with_landmarks=bool(request.get("withLandmarks", True)),
        pace_factor=_bounded(request.get("paceFactor", DEFAULT_PACE_FACTOR),
                             PACE_FLOOR, PACE_CEILING, "paceFactor"),
        log=log,
    )


def plan_from_request(request, log=print):
    """Turns the json a front sends into a call on core, and nothing more"""
    waypoints = request.get("waypoints") or []
    if (len(waypoints) < MIN_WAYPOINTS):
        raise ValueError("il faut au moins deux points de passage")

    return plan(
        waypoints,
        sun_penalty=_bounded(request.get("sunPenalty", DEFAULT_SUN_PENALTY),
                             PENALTY_FLOOR, PENALTY_CEILING, "sunPenalty"),
        road_penalty=_bounded(request.get("roadPenalty", DEFAULT_ROAD_PENALTY),
                              PENALTY_FLOOR, PENALTY_CEILING, "roadPenalty"),
        close_loop=bool(request.get("closeLoop", True)),
        with_elevation=bool(request.get("withElevation", True)),
        with_landmarks=bool(request.get("withLandmarks", True)),
        pace_factor=_bounded(request.get("paceFactor", DEFAULT_PACE_FACTOR),
                             PACE_FLOOR, PACE_CEILING, "paceFactor"),
        max_sac=_sac(request.get("maxSac", DEFAULT_MAX_SAC)),
        log=log,
    )
