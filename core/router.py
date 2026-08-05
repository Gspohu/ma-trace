#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shade weighted routing, and the statistics that come out of a finished loop"""

import collections
import heapq

from .geometry import haversine
from .graph import ROADLIKE

# past this the sentier is one you can lose, and the walker deserves to be told
FAINT = frozenset(("bad", "horrible", "no"))

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


# what a segment looks like when nothing on the network answers for it
UNKNOWN = {
    "shaded": False,
    "cover": "decouvert",
    "transmittance": 1.0,
    "surface": "non renseigne",
    "highway": "?",
    "visibility": "non renseigne",
    "sac_scale": "non renseigne",
    "incline": None,
    "on_network": False,
}


def describe(a, b, length, edge):
    # one segment in the shape the tally reads, edge being None off the network
    if (edge is None):
        return dict(UNKNOWN, a=a, b=b, length=length)

    return {
        "a": a, "b": b, "length": length, "on_network": True,
        "shaded": edge["shaded"], "cover": edge["cover"],
        "transmittance": edge["transmittance"], "surface": edge["surface"],
        "highway": edge["highway"], "visibility": edge["visibility"],
        "sac_scale": edge["sac_scale"], "incline": edge["incline"],
    }


def summarise(graph, path):
    # everything the interface needs to describe the tracé, computed once
    segments = []
    for a, b in zip(path, path[1:]):
        # cannot miss, the path is built form the graph itself. If it ever does, the
        # numebr stays visible and nothing gets swallowed
        segments.append(describe(a, b, haversine(a, b), graph.edge(a, b)))

    return tally(segments)


def tally(described):
    """Roll described segments into the figures an interface shows.

    A routed path and an imported trace both land here. One reads its segments off the
    graph it was drawn on, the other off whatever the matcher recognised under it"""
    total = 0.0
    shaded = 0.0
    road = 0.0
    off_network = 0.0
    # metres weighted by the light that gets through, which says more than the
    # yes-or-no of being under a canopy : an hour under spruce is not an hour under
    # a thin chenaie, and the walker feels the difference long before the map shows it
    sunlight = 0.0
    faint = 0.0
    steepest = None
    surfaces = collections.Counter()
    highways = collections.Counter()
    covers = collections.Counter()
    visibilities = collections.Counter()
    difficulties = collections.Counter()

    for segment in described:
        length = segment["length"]
        total += length

        if (not segment["on_network"]):
            off_network += length

        if (segment["shaded"]):
            shaded += length
        if (segment["highway"] in ROADLIKE):
            road += length
        if (segment["visibility"] in FAINT):
            faint += length

        slope = segment["incline"]
        if (slope is not None and (steepest is None or abs(slope) > abs(steepest))):
            steepest = slope

        sunlight += length * segment["transmittance"]
        surfaces[segment["surface"]] += length
        highways[segment["highway"]] += length
        covers[segment["cover"]] += length
        visibilities[segment["visibility"]] += length
        difficulties[segment["sac_scale"]] += length

    return {
        "metres": total,
        "shaded_metres": shaded,
        "shade_pct": (100.0 * shaded / total) if total else 0.0,
        "exposure_pct": (100.0 * sunlight / total) if total else 0.0,
        "road_metres": road,
        "off_network_metres": off_network,
        "faint_metres": faint,
        "steepest_pct": steepest,
        "surfaces": surfaces.most_common(),
        "highways": highways.most_common(),
        "covers": covers.most_common(),
        "visibilities": visibilities.most_common(),
        "difficulties": difficulties.most_common(),
        "segments": described,
    }
