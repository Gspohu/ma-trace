#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared fixtures : a tiny synthetic world where the right answer is known by hand"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# a degree of longitude shrinks with the cosine of the latitude, everything below is
# laid out around here so the distnaces stay easy to reaosn about
SOUTH = 49.000
NORTH = 49.004
WEST = 7.500
EAST = 7.520


def way(identifier, points, **tags):
    # an overpass shaped way, which is what both sources hand the graph
    tags.setdefault("highway", "path")
    return {
        "type": "way",
        "id": identifier,
        "tags": tags,
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in points],
    }


@pytest.fixture
def two_ways():
    """Two routes from the same A to the same B.

    The southern one is a straight line and takes full sun. The northern one detours
    and hides under the trees. Which one wins is entirely decided by the sun penalty,
    and that is the whole point of this projet"""
    return [
        way(1, [(SOUTH, WEST), (SOUTH, 7.510), (SOUTH, EAST)]),
        way(2, [(SOUTH, WEST), (NORTH, WEST), (NORTH, 7.510),
                (NORTH, EAST), (SOUTH, EAST)]),
    ]


@pytest.fixture
def northern_wood():
    # a forest band covering the northern route and nothing of the southern one
    ring = [(7.490, 49.002), (7.530, 49.002), (7.530, 49.006), (7.490, 49.006),   
            (7.490, 49.002)]
    return [{
        "type": "way",
        "id": 100,
        "tags": {"landuse": "forest"},
        "geometry": [{"lat": lat, "lon": lon} for lon, lat in ring],
    }]


@pytest.fixture
def wood_with_clearing():
    """One massif with a hole punched in the middle.

    Forgetting the inner ring once made a run claim a hundred percent of shade"""
    outer = [(7.490, 48.990), (7.530, 48.990), (7.530, 49.030), (7.490, 49.030),
             (7.490, 48.990)]
    inner = [(7.505, 49.005), (7.515, 49.005), (7.515, 49.015), (7.505, 49.015),
             (7.505, 49.005)]

    def members(ring, role):
        return {"role": role,
                "geometry": [{"lat": lat, "lon": lon} for lon, lat in ring]}


    return [{
        "type": "relation",
        "id": 200,
        "tags": {"landuse": "forest"},
        "members": [members(outer, "outer"), members(inner, "inner")],
    }]
