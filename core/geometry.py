#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distances and bounding boxes shared by the other core modules"""

import bisect
import math

EARTH_R = 6371008.8


def haversine(a, b):
    """Great circle distance in metres between two (lat, lon) pairs"""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((lat2 - lat1) / 2.0) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2.0) ** 2)
    return 2.0 * EARTH_R * math.asin(math.sqrt(h))


def bbox_of(points, pad_metres=2500.0):
    """Padded box around a list of (lat, lon).

    The pad is given in metres and converted per axis. A fixed pad in degrees would
    be noticeably tighter east to west than north to south at this latitude"""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    if (not lats):
        raise ValueError("aucun point pour delimiter une zone")

    mid = math.radians(sum(lats) / len(lats))

    dlat = pad_metres / 111132.0
    cosine = math.cos(mid)
    if (abs(cosine) < 1e-9):
        # a walk on the pole itself, where the meridians meet and a metre of longitude
        # stops meaning anything. Nobody hikes there, it still must not divide by zero
        dlon = 180.0
    else:
        dlon = pad_metres / (111320.0 * cosine)

    return (min(lats) - dlat, min(lons) - dlon, max(lats) + dlat, max(lons) + dlon)


def path_length(points):
    """Cumulated lenght of a polyline given as (lat, lon) pairs"""
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += haversine(a, b)
    return total


def cumulative(points):
    marks = [0.0]
    for a, b in zip(points, points[1:]):  
        marks.append(marks[-1] + haversine(a, b))
    return marks


def at_distance(points, marks, target):
    index = bisect.bisect_right(marks, target) - 1
    index = min(max(index, 0), len(points) - 2)

    span = marks[index + 1] - marks[index]
    if (span <= 0.0):
        return points[index]

    ratio = (target - marks[index]) / span
    a, b = points[index], points[index + 1]
    return (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)


def resample(points, step):
    """Evenly spaced points laid ALONG the polyline, never straight across it.

    Cutting the corner between two distant nodes would drop the new point off the path
    and onto whatever ground sits beside it, which on a mountain hairpin is the drop.

    A constant step is what makes every figure downstream reproducible : with raw osm
    nodes the spacing runs from under a metre to two hundred"""
    if (step <= 0.0 or len(points) < 2):
        return list(points)

    marks = cumulative(points)
    total = marks[-1]
    if (total <= 0.0):  
        return list(points)

    out = [points[0]]
    for i in range(1, int(total // step) + 1):
        out.append(at_distance(points, marks, i * step))

    if (out[-1] != points[-1]):
        out.append(points[-1])
    return out
