#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puts a trace somebody else walked back onto the osm network underneath it"""

import collections

from .geometry import haversine, point_to_segment
from .router import describe

# roughly two hundred metres of latitude. The nine cells around a point then always
# cover the snapping radius, and one cell holds few enough aretes to scan them all
CELL = 0.002

# a gps under canopy wanders by a good ten metres on its own, and a contributor draws
# the sentier along their own walk and not along ours. Past this the trace really is
# somewhere the network is not, and saying so is the honest answer
SNAP_RADIUS = 25.0


def _cell_of(lat, lon):
    return (int(lat // CELL), int(lon // CELL))


def _cells_between(a, b):
    """Every cell the segment's box touches, so a long way stays findable along it"""
    low = _cell_of(min(a[0], b[0]), min(a[1], b[1]))
    high = _cell_of(max(a[0], b[0]), max(a[1], b[1]))

    return [(y, x)
            for y in range(low[0], high[0] + 1)
            for x in range(low[1], high[1] + 1)]


class Network:
    """Grid index over the graph aretes, built once and asked once per segment.

    A linear scan is what nearest_node gets away with, at one call per point de
    passage. Matching a trace asks the same question several hundred times, which
    turns sixteen milliseconds into a quarter of a minute"""

    def __init__(self, graph):
        self._cells = collections.defaultdict(list)
        self.edge_count = 0

        for key, edge in graph.edges.items():
            ends = tuple(key)
            if (len(ends) != 2):
                continue

            self.edge_count += 1
            entry = (ends[0], ends[1], edge)
            for cell in _cells_between(ends[0], ends[1]):
                self._cells[cell].append(entry)

    def nearest(self, point, radius=SNAP_RADIUS):
        """Closest arete to a point, None when the network is further off than radius"""
        home = _cell_of(point[0], point[1])
        best = None
        best_gap = radius

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for a, b, edge in self._cells.get((home[0] + dy, home[1] + dx), ()):
                    gap = point_to_segment(point, a, b)
                    if (gap < best_gap):
                        best = edge
                        best_gap = gap

        return best


def match(points, index, canopy):
    """Describe every segment of a trace, from the network and from the canopy.

    The shade is read off the ground the walker actually covers and never off the
    matched arete : which way we recognised under a trace is a guess, where the trace
    runs is not"""
    described = []

    for a, b in zip(points, points[1:]):
        length = haversine(a, b)
        if (length <= 0.0):
            continue

        middle = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        segment = describe(a, b, length, index.nearest(middle))

        cover, transmittance = canopy.cover_of_segment(a, b)
        segment["cover"] = cover or "decouvert"
        segment["transmittance"] = transmittance
        segment["shaded"] = cover is not None

        described.append(segment)

    return described
