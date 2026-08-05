#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Putting a foreign trace back onto the network, and what it may not borrow from it"""

from core.canopy import Canopy
from core.graph import Graph
from core.matching import SNAP_RADIUS, Network, match
from core.router import tally

# the fixture wood runs from 49.002 to 49.006. Twenty two metres apart, one under the
# trees and one out of them, both well inside the snapping radius
INSIDE = 49.0021
OUTSIDE = 49.0019


def way(identifier, lat, **tags):
    tags.setdefault("highway", "track")
    tags.setdefault("surface", "gravel")
    return {"type": "way", "id": identifier, "tags": tags,
            "geometry": [{"lat": lat, "lon": 7.500}, {"lat": lat, "lon": 7.510}]}


def built(ways, wood):
    canopy = Canopy(wood)
    graph = Graph(ways, canopy)
    return Network(graph), canopy


def test_a_trace_on_the_network_picks_up_its_tags(northern_wood):
    index, canopy = built([way(1, INSIDE)], northern_wood)
    described = match([(INSIDE, 7.501), (INSIDE, 7.509)], index, canopy)

    assert described[0]["surface"] == "gravel"
    assert described[0]["highway"] == "track"
    assert described[0]["on_network"] is True


def test_a_trace_nowhere_near_a_chemin_is_reported_as_such(northern_wood):
    index, canopy = built([way(1, INSIDE)], northern_wood)
    described = match([(49.0500, 7.501), (49.0500, 7.509)], index, canopy)

    assert described[0]["on_network"] is False
    assert described[0]["surface"] == "non renseigne"
    assert tally(described)["off_network_metres"] > 0.0


def test_the_shade_is_read_off_the_ground_and_not_off_the_matched_arete(northern_wood):
    # which way lies under a trace is a guess, where the trace runs is not
    index, canopy = built([way(1, INSIDE)], northern_wood)

    assert canopy.covers_segment((INSIDE, 7.501), (INSIDE, 7.509)) is True

    described = match([(OUTSIDE, 7.501), (OUTSIDE, 7.509)], index, canopy)

    assert described[0]["on_network"] is True
    assert described[0]["surface"] == "gravel"
    assert described[0]["shaded"] is False
    assert described[0]["cover"] == "decouvert"
    assert described[0]["transmittance"] == 1.0


def test_a_segment_of_no_lenght_is_dropped(northern_wood):
    index, canopy = built([way(1, INSIDE)], northern_wood)
    described = match([(INSIDE, 7.501), (INSIDE, 7.501), (INSIDE, 7.509)], index, canopy)

    assert len(described) == 1


def test_the_grid_finds_an_arete_that_spans_several_cells(northern_wood):
    index, canopy = built([way(1, INSIDE)], northern_wood)

    for lon in (7.5005, 7.5045, 7.5095):
        assert index.nearest((INSIDE, lon)) is not None


def test_nothing_is_matched_past_the_snapping_radius(northern_wood):
    index, _ = built([way(1, INSIDE)], northern_wood)

    beyond = INSIDE + (SNAP_RADIUS + 5.0) / 111132.0
    assert index.nearest((beyond, 7.505)) is None
