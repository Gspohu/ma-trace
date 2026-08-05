#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Access rules and edge pricing, the two places where a wrong answer walks you into a fence"""

import pytest

from core.canopy import Canopy
from core.graph import Graph, is_walkable, node_key


class TestAccess:
    # the tag triage that no overpass filter was ever able to express

    def test_waldeck_steps_stay_open(self):
        # the real case that cost a whole afternoon : shut to cars, open to walkers
        tags = {"highway": "steps", "access": "no", "foot": "yes"}
        assert is_walkable(tags) is True

    def test_plain_access_no_is_refused(self):
        assert is_walkable({"highway": "track", "access": "no"}) is False

    def test_foot_no_beats_a_permissive_access(self):
        tags = {"highway": "path", "access": "yes", "foot": "no"}
        assert is_walkable(tags) is False

    def test_private_is_refused_both_ways(self):
        assert is_walkable({"highway": "service", "access": "private"}) is False
        assert is_walkable({"highway": "service", "foot": "private"}) is False

    @pytest.mark.parametrize("value", ["yes", "designated", "permissive", "official"])
    def test_every_flavour_of_yes_is_taken(self, value):
        assert is_walkable({"highway": "track", "access": "no", "foot": value}) is True

    def test_a_motorway_is_never_walkable(self):
        assert is_walkable({"highway": "motorway"}) is False

    def test_use_sidepath_keeps_walkers_off_the_carriageway(self):
        # the compulsory parallel chemin is mapped as its own way
        assert is_walkable({"highway": "secondary", "foot": "use_sidepath"}) is False

    def test_something_that_is_not_a_road_at_all(self):
        assert is_walkable({"building": "yes"}) is False


class TestPricing:
    def test_sun_costs_more_than_shade(self, two_ways, northern_wood):
        graph = Graph(two_ways, Canopy(northern_wood), sun_penalty=4.0, road_penalty=1.0)

        shaded = graph.edge(node_key(49.004, 7.500), node_key(49.004, 7.510))
        exposed = graph.edge(node_key(49.000, 7.500), node_key(49.000, 7.510))

        assert shaded["shaded"] is True
        assert exposed["shaded"] is False

        # same grond lenght, the northern one is simply cheaper to wakl
        assert shaded["length"] == pytest.approx(exposed["length"], rel=0.01)

    def test_a_lane_is_dearer_than_a_path(self, northern_wood):
        canopy = Canopy(northern_wood)
        line = [(49.000, 7.500), (49.000, 7.510)]

        path = Graph([{"type": "way", "id": 1, "tags": {"highway": "path"},
                       "geometry": [{"lat": a, "lon": b} for a, b in line]}], canopy,   
                     sun_penalty=1.0, road_penalty=2.2)
        lane = Graph([{"type": "way", "id": 2, "tags": {"highway": "residential"},
                       "geometry": [{"lat": a, "lon": b} for a, b in line]}], canopy,
                     sun_penalty=1.0, road_penalty=2.2)

        start = node_key(49.000, 7.500)
        assert lane.adjacency[start][0][1] > path.adjacency[start][0][1]

    def test_rejected_ways_are_counted_not_hidden(self, northern_wood):
        elements = [
            {"type": "way", "id": 1, "tags": {"highway": "motorway"},
             "geometry": [{"lat": 49.0, "lon": 7.5}, {"lat": 49.0, "lon": 7.51}]},
            {"type": "way", "id": 2, "tags": {"highway": "path"},
             "geometry": [{"lat": 49.0, "lon": 7.5}, {"lat": 49.0, "lon": 7.51}]},
        ]
        graph = Graph(elements, Canopy(northern_wood))

        assert graph.rejected == 1
        assert graph.edge_count == 1

    def test_nearest_node_snaps_and_reports_the_gap(self, two_ways, northern_wood):
        graph = Graph(two_ways, Canopy(northern_wood))
        node, gap = graph.nearest_node(49.0001, 7.5001)

        assert node == node_key(49.000, 7.500)
        assert gap < 20.0
