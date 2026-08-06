#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End to end : waypoints in, a described loop out, over a world we control entirely"""

import pytest

from conftest import Shelf
from core import landmarks
from core.canopy import Canopy
from core.graph import Graph, node_key
from core.pipeline import plan
from core.router import NoRouteError, describe

A = {"name": "Depart", "lat": 49.000, "lon": 7.500}
B = {"name": "Arrivee", "lat": 49.000, "lon": 7.520}

NEAR = node_key(49.000, 7.500)
FAR = node_key(49.000, 7.510)


def quiet(message):
    return None


@pytest.fixture
def world(shelf):
    return shelf


def test_the_shaded_detour_is_preferred(world):
    """The northern route is longer on the ground and still wins, which is the projet"""
    result = plan([A, B], sun_penalty=4.0, road_penalty=1.0, close_loop=False,
                  with_elevation=False, source=world, log=quiet)

    northern = [p for p in result["points"] if p["lat"] > 49.002]
    assert northern, "le routeur a ignore le couvert"
    assert result["stats"]["shade_pct"] > 50.0


def test_without_a_penalty_the_short_way_wins(world):
    result = plan([A, B], sun_penalty=1.0, road_penalty=1.0, close_loop=False,
                  with_elevation=False, source=world, log=quiet)

    northern = [p for p in result["points"] if p["lat"] > 49.002]
    assert not northern
    assert result["stats"]["shade_pct"] == 0.0


def test_the_loop_comes_back_by_the_other_route(world): 
    result = plan([A, B], sun_penalty=4.0, road_penalty=1.0, close_loop=True,
                  with_elevation=False, source=world, log=quiet)

    latitudes = {round(p["lat"], 3) for p in result["points"]}
    assert 49.004 in latitudes and 49.0 in latitudes

    assert result["points"][0]["lat"] == pytest.approx(result["points"][-1]["lat"])
    assert result["points"][0]["lon"] == pytest.approx(result["points"][-1]["lon"])


def test_distances_and_segments_line_up(world):
    result = plan([A, B], close_loop=False, with_elevation=False, source=world, log=quiet)

    points = result["points"]
    assert len(result["shade"]) == len(points) - 1
    assert len(result["seg_surface"]) == len(points) - 1

    # the running distance has to grow, a flat or falling km column is a real bug
    kilometres = [p["km"] for p in points]
    assert kilometres == sorted(kilometres)
    assert kilometres[0] == 0.0
    assert result["stats"]["km"] == pytest.approx(kilometres[-1], abs=0.01)


def test_nothing_off_the_network(world):
    result = plan([A, B], close_loop=False, with_elevation=False, source=world, log=quiet)
    assert result["stats"]["off_network_metres"] == 0


def test_a_single_waypoint_is_refused(world):
    with pytest.raises(ValueError):
        plan([A], source=world, log=quiet)


def test_two_islands_cannot_be_joined(northern_wood):
    # two disconnected paths. It must say so and never invent a link
    far = [
        {"type": "way", "id": 1, "tags": {"highway": "path"},
         "geometry": [{"lat": 49.0, "lon": 7.50}, {"lat": 49.0, "lon": 7.501}]},
        {"type": "way", "id": 2, "tags": {"highway": "path"},
         "geometry": [{"lat": 49.0, "lon": 7.52}, {"lat": 49.0, "lon": 7.521}]},
    ]

    with pytest.raises(NoRouteError):
        plan([A, B], close_loop=False, with_elevation=False, 
             source=Shelf(far, northern_wood), log=quiet)


def test_an_empty_network_is_refused(northern_wood):
    with pytest.raises(ValueError):
        plan([A, B], close_loop=False, with_elevation=False,
             source=Shelf([], northern_wood), log=quiet)


def test_a_described_segment_carries_its_whole_contract(two_ways, northern_wood):
    """Both the router and the matcher fill this record, and a key appearing on one
    side only is how a routed loop and an imported trace stop being comparable"""
    expected = {"a", "b", "cover", "incline", "length", "on_network", "sac_scale",
                "shaded", "surface", "transmittance", "visibility", "highway"}

    graph = Graph(two_ways, Canopy(northern_wood), sun_penalty=4.0, road_penalty=1.0)
    described = describe(NEAR, FAR, 120.0, graph.edge(NEAR, FAR))

    assert expected <= set(described)


def test_a_repere_carries_its_whole_contract():
    """The local index and overpass both build one through landmarks.describe"""
    repere = landmarks.describe({"amenity": "drinking_water", "name": "Source"},
                                49.0, 7.5)

    assert set(repere) == {"name", "kind", "lat", "lon", "fee", "drinkable"}
    assert repere["kind"] == "drinking_water"
    assert repere["drinkable"] is True
    assert repere["fee"] is None
