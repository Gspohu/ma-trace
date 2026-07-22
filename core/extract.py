#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local OSM source, same shapes as the overpass module and none of the waiting"""

import gzip
import json
import os

from . import library
from .graph import WALKABLE     

CANOPY_TAGS = (("landuse", "forest"), ("natural", "wood"))


def _tagged_canopy(tags):
    for key, value in CANOPY_TAGS:
        if (tags.get(key) == value):
            return True
    return False


def _hits(bbox, lats, lons):
    """Cheap bbox overlap. bbox is (minlat, minlon, maxlat, maxlon)"""
    if (not lats):
        return False
    return not (max(lats) < bbox[0] or min(lats) > bbox[2]
                or max(lons) < bbox[1] or min(lons) > bbox[3])


def header_bbox(pbf_paths):
    """Union of what the extracts themselves declare they cover.

    Geofabrik writes the reach into the pbf header, which saves the caller from
    typing coordinates by hand. Nothing guarantees it is there though, an extract cut
    by other tools may carry no box at all, and then the caller has to say the zone"""
    import osmium

    boxes = []
    for path in pbf_paths:
        reader = osmium.io.Reader(path)
        try:
            box = reader.header().box()
            if (box is None or not box.valid()):
                continue
            boxes.append((box.bottom_left.lat, box.bottom_left.lon,
                          box.top_right.lat, box.top_right.lon))
        finally:
            reader.close()

    if (not boxes):
        return None

    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def build_index(pbf_paths, bbox, out_path, label=None, log=print):
    """One slow pass over the extracts, keeping only what the router can ever use.

    Overpass was ninety nine percent of the wall clock, and not a millisecond of it
    was ours to optimise. Reading a geofabrik extract once and slicing it in memory
    kills the whole cost and lets the router work with no connection at all"""

    # kept out of the module header : osmium reads the pbf extracts and nothing else
    # Routing goes through LocalSource just below and mut stay usable on a machine
    # that never builds an index
    import osmium

    network = []
    canopy = []

    for path in pbf_paths:
        log("Lecture de %s..." % os.path.basename(path))
        seen_ways = 0
        dropped = 0

        processor = osmium.FileProcessor(path).with_locations().with_areas()
        for obj in processor:
            if (obj.type_str() == "w"):
                tags = dict(obj.tags)
                if (tags.get("highway") not in WALKABLE):
                    continue

                try:
                    geometry = [{"lat": n.lat, "lon": n.lon}
                                for n in obj.nodes if n.location.valid()]
                except osmium.InvalidLocationError:
                    dropped += 1
                    continue

                if (len(geometry) < 2):
                    continue

                lats = [p["lat"] for p in geometry]
                lons = [p["lon"] for p in geometry]
                if (not _hits(bbox, lats, lons)):
                    continue

                network.append({"type": "way", "id": obj.id, "tags": tags,
                                "geometry": geometry})
                seen_ways += 1

            elif (obj.type_str() == "a"):
                tags = dict(obj.tags)
                if (not _tagged_canopy(tags)):
                    continue

                members = []
                lats = []
                lons = []
                for ring in obj.outer_rings():
                    coords = [{"lat": n.lat, "lon": n.lon} for n in ring] 
                    if (len(coords) < 4):
                        continue

                    members.append({"role": "outer", "geometry": coords})
                    lats.extend(p["lat"] for p in coords)
                    lons.extend(p["lon"] for p in coords) 

                    for hole in obj.inner_rings(ring):
                        inner = [{"lat": n.lat, "lon": n.lon} for n in hole]
                        if (len(inner) >= 4):
                            members.append({"role": "inner", "geometry": inner})

                if (not members or not _hits(bbox, lats, lons)):
                    continue

                canopy.append({"type": "relation", "id": obj.orig_id(), "members": members})

        log("   %d chemins retenus, %d massifs cumules" % (seen_ways, len(canopy)))   
        if (dropped):
            log("   %d chemins ecartes, coordonnees absentes de l'extrait" % dropped)

    payload = {"bbox": list(bbox), "network": network, "canopy": canopy}


    with gzip.open(out_path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    # the sidecar carries the reach. Picking an index later never opens this one
    library.write_meta(out_path, bbox, label=label)

    size = os.path.getsize(out_path) / 1048576.0
    log("Index ecrit : %s (%.1f Mo, %d chemins, %d massifs)"
        % (out_path, size, len(network), len(canopy)))
    return payload


class LocalSource:
    """Reads the prebuilt index and hands out overpass shaped answers, instantly"""

    def __init__(self, index_path):
        with gzip.open(index_path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.bbox = tuple(payload["bbox"])
        self._network = payload["network"]
        self._canopy = payload["canopy"]

    def covers(self, bbox):
        return (bbox[0] >= self.bbox[0] and bbox[1] >= self.bbox[1]
                and bbox[2] <= self.bbox[2] and bbox[3] <= self.bbox[3])

    def fetch_network(self, bbox, log=print):
        kept = []
        for way in self._network:
            lats = [p["lat"] for p in way["geometry"]]
            lons = [p["lon"] for p in way["geometry"]]
            if (_hits(bbox, lats, lons)):
                kept.append(way)

        log("   reseau local : %d chemins" % len(kept))
        return {"elements": kept}


    def fetch_canopy(self, bbox, log=print):
        kept = []
        for area in self._canopy:
            lats = []
            lons = []
            for member in area["members"]:
                if (member["role"] != "outer"):
                    continue
                lats.extend(p["lat"] for p in member["geometry"])
                lons.extend(p["lon"] for p in member["geometry"])

            if (_hits(bbox, lats, lons)):
                kept.append(area)

        log("   foret locale : %d massifs" % len(kept))
        return {"elements": kept}
