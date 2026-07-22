#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turns raw OSM forest polygons into one geometry we can hit-test against"""

from shapely.errors import GEOSException, TopologicalError
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
from shapely.prepared import prep

_BROKEN_RING = (GEOSException, TopologicalError, ValueError)


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
    """The tree cover, holes included.

    Punching the inner rings out is not cosmetic : skipping them once made an
    early run claim 100 % of shade, because every clairiere, the car park and
    the road through it were all being counted as forest"""  

    def __init__(self, elements):
        outers = []
        inners = []

        for element in elements:
            if (element.get("type") == "way"):
                poly = _ring_to_polygon([(p["lon"], p["lat"])
                                         for p in element.get("geometry") or []])
                if (poly is not None):
                    outers.append(poly)
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

        cover = unary_union(outers) if outers else Polygon()
        if (inners):
            cover = cover.difference(unary_union(inners))
        if (isinstance(cover, Polygon)):
            cover = MultiPolygon([cover] if not cover.is_empty else [])   

        self.shape = cover
        self.outer_count = len(outers)
        self.clearing_count = len(inners)
        self._prepared = prep(cover)

    def covers_segment(self, a, b):
        """True when the whole segment stays under the trees.
        The midpoint is sampled too, a two point line can bridge a clairiere unnoticed"""
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        line = LineString([(a[1], a[0]), (mid[1], mid[0]), (b[1], b[0])])
        return bool(self._prepared.covers(line))

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
