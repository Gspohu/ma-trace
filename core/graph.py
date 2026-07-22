#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the walkable graph and prices every edge by how much sun it takes"""

from .geometry import haversine

WALKABLE = frozenset((
    "path", "footway", "track", "bridleway", "steps", "cycleway", "living_street",
    "pedestrian", "residential", "unclassified", "service", "tertiary", "secondary",   
    "primary", "road",
))

ROADLIKE = frozenset((
    "residential", "unclassified", "service", "tertiary", "secondary",
    "primary", "living_street", "road",
))

FOOT_ALLOWED = frozenset(("yes", "designated", "permissive", "official"))
FOOT_BLOCKED = frozenset(("no", "private"))
ACCESS_BLOCKED = frozenset(("no", "private"))


def is_walkable(tags):
    """OSM access semantics, spelled out rather than crammed into an Overpass regex.

    A foot tag always wins over the generic access tag. That is what saves the
    Waldeck castle steps, taggued access=no + foot=yes : shut to cars, open to us"""
    if (tags.get("highway") not in WALKABLE): 
        return False

    foot = tags.get("foot") 
    if (foot in FOOT_BLOCKED):
        return False
    if (foot in FOOT_ALLOWED):
        return True

    # no explicit foot tag, the egneric access tag has the last word
    return tags.get("access") not in ACCESS_BLOCKED


# osm juntcions share the exact same coordinate, rounding here joins the ways
# Overpass "out gemo" gives us no node ids, the point itself becomes the identity
def node_key(lat, lon):
    return (round(lat, 7), round(lon, 7))


class Graph:
    """Undirected walking graph whose edge cost is metres, inflated by exposure"""

    def __init__(self, elements, canopy, sun_penalty=4.0, road_penalty=2.2):
        self.adjacency = {}
        self.edges = {}
        self.sun_penalty = sun_penalty
        self.road_penalty = road_penalty

        skipped = 0
        for way in elements:
            tags = way.get("tags", {})
            if (not is_walkable(tags)):
                skipped += 1
                continue

            highway = tags["highway"] 
            surface = tags.get("surface") or "non renseigne"
            geometry = way.get("geometry") or []
            if (len(geometry) < 2):
                continue

            nodes = [node_key(p["lat"], p["lon"]) for p in geometry]
            for a, b in zip(nodes, nodes[1:]):
                length = haversine(a, b)
                if (length <= 0.0):
                    continue

                shaded = canopy.covers_segment(a, b)
                cost = length if shaded else length * sun_penalty
                if (highway in ROADLIKE):
                    cost *= road_penalty

                self.adjacency.setdefault(a, []).append((b, cost))
                self.adjacency.setdefault(b, []).append((a, cost))
                self.edges[frozenset((a, b))] = {
                    "length": length,   
                    "shaded": shaded,
                    "highway": highway,
                    "surface": surface,
                    "way": way.get("id"),
                }


        self.rejected = skipped

    @property
    def node_count(self):
        return len(self.adjacency)

    @property
    def edge_count(self):
        return len(self.edges)

    def shaded_share(self):
        if (not self.edges):
            return 0.0
        under = sum(1 for e in self.edges.values() if e["shaded"])
        return 100.0 * under / len(self.edges)   

    def nearest_node(self, lat, lon):
        """Snap an arbitrary click onto the network. A linear scan, and it stays linear :
        thirty thousand nodes cost a millisecond, an index would only add bugs"""
        target = (lat, lon)
        best = None
        best_distance = float("inf")

        for node in self.adjacency: 
            gap = haversine(node, target)
            if (gap < best_distance):
                best = node
                best_distance = gap

        return best, best_distance

    def edge(self, a, b):
        return self.edges.get(frozenset((a, b)))
