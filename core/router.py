#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shade weighted routing, and the statistics that come out of a finished loop"""

import collections
import heapq

from .geometry import haversine
from .graph import ROADLIKE

# walking the same segment twice is dull, each leg makes its own deges expensive
# for the legs that follow. Six is enough to push the return leg onto fresh ground
# iwthout ever making a genuinely unavoidable corridor impossible
REUSE_PENALTY = 6.0


class NoRouteError(RuntimeError):
    pass


def shortest_path(graph, start, goal, penalties=None):
    """Plain Dijkstra over the exposure weighted costs.

    A star would visit fewer nodes for the identical answer, but the graph is
    thirty thousand edges and this returns in milliseconds. The heuristic would
    buy nothing and could only introduce a bug"""
    penalties = penalties or {}
    distance = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    settled = set()

    while (queue):
        cost, node = heapq.heappop(queue)
        if (node in settled):
            continue

        settled.add(node)
        if (node == goal):
            break 

        for neighbour, base in graph.adjacency.get(node, ()):
            weight = base * penalties.get(frozenset((node, neighbour)), 1.0)
            candidate = cost + weight
            if (candidate < distance.get(neighbour, float("inf"))):
                distance[neighbour] = candidate 
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))

    if (goal not in distance):
        return None

    path = [goal]
    while (path[-1] != start):
        path.append(previous[path[-1]])
    path.reverse()
    return path


def route_through(graph, anchors):
    """Chain the waypoints into one continuous path, discouraging repeated ground"""
    penalties = {}
    full = []
    legs = []

    for start, goal in zip(anchors, anchors[1:]):
        leg = shortest_path(graph, start, goal, penalties)
        if (leg is None):
            raise NoRouteError("aucun chemin entre deux points de passage")

        for a, b in zip(leg, leg[1:]):
            key = frozenset((a, b))
            penalties[key] = penalties.get(key, 1.0) * REUSE_PENALTY 

        legs.append(sum(haversine(a, b) for a, b in zip(leg, leg[1:])))
        full.extend(leg if not full else leg[1:])

    return full, legs


def summarise(graph, path):
    """Everything the interface needs to describe the tracé, computed once"""
    total = 0.0
    shaded = 0.0
    road = 0.0
    off_network = 0.0
    surfaces = collections.Counter()
    highways = collections.Counter()
    segments = []   

    for a, b in zip(path, path[1:]):
        length = haversine(a, b)
        total += length

        edge = graph.edge(a, b)   
        if (edge is None):
            # cannot happen, the path is built form the graph itself. If it ever
            # does, the numebr stays visible and nothing gets swallowed
            off_network += length
            segments.append({"a": a, "b": b, "shaded": False, "length": length,
                             "surface": "non renseigne", "highway": "?"})
            continue

        if (edge["shaded"]):
            shaded += length
        if (edge["highway"] in ROADLIKE):
            road += length

        surfaces[edge["surface"]] += length
        highways[edge["highway"]] += length
        segments.append({"a": a, "b": b, "shaded": edge["shaded"], "length": length,
                         "surface": edge["surface"], "highway": edge["highway"]})

    return {
        "metres": total,
        "shaded_metres": shaded,
        "shade_pct": (100.0 * shaded / total) if total else 0.0,
        "road_metres": road,
        "off_network_metres": off_network,
        "surfaces": surfaces.most_common(),
        "highways": highways.most_common(),   
        "segments": segments,
    }
