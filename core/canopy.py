#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turns raw OSM forest polygons into one geometry we can hit-test against"""

import collections

from shapely.errors import GEOSException, TopologicalError
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
from shapely.prepared import prep

_BROKEN_RING = (GEOSException, TopologicalError, ValueError)

# What a closed canopy lets down to the ground, as a fraction of the light above it
# Needles hold their shade all year and pack it tighter than any leaf does, which is
# why a spruce plantation and a chenaie claire are not the same shelter at all :
#
#   needleleaved  Cescatti A. (1998), Effects of needle clumping in shoots and crowns
#                 on the radiative regime of a Norway spruce canopy, Annales des
#                 Sciences Forestieres 55, 89-102, doi 10.1051/forest:19980106
#                 4.9 % of direct and 10.9 % of diffuse radiation under a closed stand
#                 of LAI 7.84, a little under a tenth either way
#
#   broadleaved   Sercu B.K. et al. (2017), How tree species identity and diversity
#                 affect light transmittance to the understory in mature temperate
#                 forests, Ecology and Evolution 7(24) pages 10861-10870
#                 doi 10.1002/ece3.3528
#                 gap light index after leaf expansion : 15 % under Fagus sylvatica
#                 and 16 % under Quercus robur, 19 % under Quercus rubra
#                 those readings are taken at the forest floor, counting the shrub
#                 layer together with the canopy. The paper is explicit that the oak
#                 figure leans on an abundant one, and a chenaie with a bare
#                 understory lets more through than the 16 % says
#
# Both describe a closed stand, which is what the osm polygon claims to be. Cescatti
# simulates his with a 3D radiative transfer model, Sercu measures his by hemispherical
# photography. The needleleaf figure is modelled, the broadleaf one measured
TRANSMITTANCE = {
    "needleleaved": 0.08,
    "broadleaved": 0.16,
    "mixed": 0.12,
}

# a massif nobody tagged, or an index built before the leaf type was carried. The
# lighter of the two readings is the prudent one, we never promise more shade than
# what is neccessary to stand behind
DEFAULT_TRANSMITTANCE = TRANSMITTANCE["broadleaved"]

FULL_SUN = 1.0


def _shelters(tags):
    # leafless is bare wood, dead or permanently so. Counting it would hand a walker
    # the transmittance of a healthy chenaie over ground that has no shade at all
    return (tags or {}).get("leaf_type") != "leafless"


def _leaf_kind(tags):
    """The osm leaf_type we know how to price, None for a stand nobody tagged"""
    kind = (tags or {}).get("leaf_type")
    if (kind in TRANSMITTANCE):
        return kind

    return None


def _ring_to_polygon(ring):
    if (len(ring) < 4):
        return None

    try:
        poly = Polygon(ring)
        if (not poly.is_valid):
            poly = poly.buffer(0)
    except _BROKEN_RING:
        return None

    if (poly.is_empty):
        return None
    return poly


class Canopy:
    """The tree cover, holes included, priced by how much light each stand lets down.

    Punching the inner rings out is not cosmetic : skipping them once made an
    early run claim 100 % of shade, because every clairiere, the car park and
    the road through it were all being counted as forest"""

    def __init__(self, elements):
        outers = []
        inners = []
        by_kind = collections.defaultdict(list)

        for element in elements:
            tags = element.get("tags")
            if (not _shelters(tags)):
                continue

            kind = _leaf_kind(tags)

            if (element.get("type") == "way"):
                poly = _ring_to_polygon([(p["lon"], p["lat"])
                                         for p in element.get("geometry") or []])
                if (poly is not None):
                    outers.append(poly)
                    by_kind[kind].append(poly)
                continue

            for member in element.get("members", []):
                poly = _ring_to_polygon([(p["lon"], p["lat"])
                                         for p in member.get("geometry") or []])
                if (poly is None):
                    continue

                if (member.get("role") == "inner"):
                    inners.append(poly)
                else:
                    outers.append(poly)
                    by_kind[kind].append(poly)

        cover = unary_union(outers) if outers else Polygon()
        clearings = unary_union(inners) if inners else None
        if (clearings is not None):
            cover = cover.difference(clearings)
        if (isinstance(cover, Polygon)):
            cover = MultiPolygon([cover] if not cover.is_empty else [])

        self.shape = cover
        self.outer_count = len(outers)
        self.clearing_count = len(inners)
        self._prepared = prep(cover)

        # one prepared geometry per leaf type, darkest first. An untagged massif gets
        # no layer at all and falls through to the default further down
        self._layers = []
        self.kind_counts = {}
        for kind, polys in by_kind.items():
            self.kind_counts[kind or "inconnu"] = len(polys)
            if (kind is None):
                continue

            shape = unary_union(polys)
            if (clearings is not None):
                shape = shape.difference(clearings)
            self._layers.append((TRANSMITTANCE[kind], kind, prep(shape)))

        self._layers.sort(key=lambda layer: layer[0])

    def cover_of_segment(self, a, b):
        """What grows over the segment and what it lets through, as (kind, share).

        The union is asked first : it settles the exposed segments in one hit test
        and those are the ones the router is trying to avoid anyway"""
        line = LineString([(a[1], a[0]), (b[1], b[0])])
        if (not self._prepared.covers(line)):
            return None, FULL_SUN

        for transmittance, kind, prepared in self._layers:
            if (prepared.covers(line)):
                return kind, transmittance

        # covered by the union yet by no single layer, which is a segment straddling
        # two massifs whose leaf types differ, or one nobody bothered to tag
        return "inconnu", DEFAULT_TRANSMITTANCE

    def transmittance_of_segment(self, a, b):
        return self.cover_of_segment(a, b)[1]

    def covers_segment(self, a, b):
        # true when the whole segment stays under the trees, whatever grows there
        return self.transmittance_of_segment(a, b) < FULL_SUN

    def clipped_rings(self, bbox_shape, tolerance=0.00012):
        """Simplified outlines for drawing, in lat/lon, ready to be projected"""
        clipped = self.shape.intersection(bbox_shape).simplify(tolerance)
        geoms = clipped.geoms if isinstance(clipped, MultiPolygon) else [clipped]

        rings = []
        for geom in geoms:
            if (geom.is_empty or geom.geom_type != "Polygon"):
                continue

            outer = [(lat, lon) for lon, lat in geom.exterior.coords]
            holes = [[(lat, lon) for lon, lat in hole.coords] for hole in geom.interiors]
            rings.append({"outer": outer, "holes": holes})

        return rings
