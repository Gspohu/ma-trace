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

# use_sidepath is a road whose parallel chemin is compulsory, the carriageway
# itself is closed to walkers and the sidepath is mapped as its own way anyway
FOOT_BLOCKED = frozenset(("no", "private", "use_sidepath"))
ACCESS_BLOCKED = frozenset(("no", "private"))

# The swiss alpine club scale, as osm spells it. T1 is a stroll in walking shoes, T3
# already wants a head for heights, T4 and up is scrambling with your hands. A router
# that hands someone a T4 because it was three hundred metres shorter is dangerous
SAC_SCALE = {
    "hiking": 1,
    "mountain_hiking": 2,
    "demanding_mountain_hiking": 3,
    "alpine_hiking": 4,
    "demanding_alpine_hiking": 5,
    "difficult_alpine_hiking": 6,
}

DEFAULT_MAX_SAC = 2

# the top of the scale, which is what reading an existing trace asks for : filtering
# there would hide the very passage the walker needs warning about
MAX_SAC = 6

# How well the sentier can be followed at all. These multipliers are a judgement call
# and never a measurement : losing a faint path costs time and nerve, which prices it
# like a detour. An untagged path is assumed followable
VISIBILITY_PENALTY = {
    "excellent": 1.0,
    "good": 1.0,
    "intermediate": 1.2,
    "bad": 1.7,
    "horrible": 2.5,
    "no": 3.5,
}


def sac_grade(tags):
    # the numeric grade, None when the way carries no such claim
    return SAC_SCALE.get(tags.get("sac_scale"))


def is_walkable(tags, max_sac=DEFAULT_MAX_SAC):
    """OSM access semantics, spelled out rather than crammed into an Overpass regex.

    A foot tag always wins over the generic access tag. That is what saves the
    Waldeck castle steps, taggued access=no + foot=yes : shut to cars, open to us.

    The sac scale is a gate and never a preference : no detour is long enough to
    make an alpine grade worth proposing to someone who asked for a walk"""
    if (tags.get("highway") not in WALKABLE):
        return False

    grade = sac_grade(tags)
    if (grade is not None and grade > max_sac):
        return False

    foot = tags.get("foot")
    if (foot in FOOT_BLOCKED):
        return False
    if (foot in FOOT_ALLOWED):
        return True

    # no explicit foot tag, the egneric access tag has the last word
    return tags.get("access") not in ACCESS_BLOCKED


def _number(raw):
    """Whatever a contributor typed where a number belongs, None when it is not one"""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def incline_percent(tags):
    # the tag carries "10%", "-5%", "up", "steep" and the odd value in degrees, only
    # the plain numbers compare
    return _number((tags.get("incline") or "").strip().rstrip("%").replace(",", "."))


def width_metres(tags):
    raw = (tags.get("width") or "").strip().replace(",", ".")
    if (raw.endswith("m")):
        raw = raw[:-1].strip()

    return _number(raw)


# osm juntcions share the exact same coordinate, rounding here joins the ways
# Overpass "out gemo" gives us no node ids, the point itself becomes the identity
def node_key(lat, lon):
    return (round(lat, 7), round(lon, 7))


class Graph:
    """Undirected walking graph whose edge cost is metres, inflated by exposure"""

    def __init__(self, elements, canopy, sun_penalty=4.0, road_penalty=2.2,
                 max_sac=DEFAULT_MAX_SAC):
        self.adjacency = {}
        self.edges = {}
        self.sun_penalty = sun_penalty
        self.road_penalty = road_penalty
        self.max_sac = max_sac

        skipped = 0
        too_hard = 0
        for way in elements:
            tags = way.get("tags", {})
            if (not is_walkable(tags, max_sac)):
                skipped += 1
                grade = sac_grade(tags)
                if (grade is not None and grade > max_sac):
                    too_hard += 1
                continue

            highway = tags["highway"]
            surface = tags.get("surface") or "non renseigne"
            visibility = tags.get("trail_visibility") or "non renseigne"
            difficulty = tags.get("sac_scale") or "non renseigne"
            slope = incline_percent(tags)
            width = width_metres(tags)
            geometry = way.get("geometry") or []
            if (len(geometry) < 2):
                continue

            nodes = [node_key(p["lat"], p["lon"]) for p in geometry]
            for a, b in zip(nodes, nodes[1:]):
                length = haversine(a, b)
                if (length <= 0.0):
                    continue

                cover, transmittance = canopy.cover_of_segment(a, b)
                shaded = cover is not None

                # the sun penalty is paid in proportion to the light that actually
                # gets down. A spruce stand lets 8 % through and costs next to nothing
                # while a chenaie claire lets twice that through and costs twice as
                # much, open ground pays the penalty whole. See core.canopy for the
                # figures and where they were measured
                cost = length * (1.0 + (sun_penalty - 1.0) * transmittance)
                if (highway in ROADLIKE):
                    cost *= road_penalty

                # a sentier you cannot make out is a detour waiting to happen
                cost *= VISIBILITY_PENALTY.get(visibility, 1.0)

                self.adjacency.setdefault(a, []).append((b, cost))
                self.adjacency.setdefault(b, []).append((a, cost))

                # osm is a multigraph : 453 elementary segments out of the 1.46 million
                # in the vosges index carry two ways whose tags disagree. Dijkstra walks
                # the cheaper of the two, and the metadata kept here has to describe
                # that very one, never whichever way happened to be read last
                key = frozenset((a, b))
                known = self.edges.get(key)
                if (known is None or cost < known["cost"]):
                    self.edges[key] = {
                        "length": length,
                        "cost": cost,
                        "shaded": shaded,
                        "cover": cover or "decouvert",
                        "transmittance": transmittance,
                        "highway": highway,
                        "surface": surface,
                        "visibility": visibility,
                        "sac_scale": difficulty,
                        "incline": slope,
                        "width": width,
                        "way": way.get("id"),
                    }

        self.rejected = skipped
        self.too_hard = too_hard

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
        """Snap an arbitrary click onto the network.

        A linear scan, and it stays linear : thirty thousand nodes measure at 16 ms,
        which a handful of points de passage turns into a tenth of a second. An rtree
        would claw most of that back, at the price of one more structure to keep in
        step with the graph, against an elevation call that costs whole seconds"""
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
