#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestration : waypoints in, a fully described loop out"""

import functools
import os

from shapely.geometry import box

from . import gpx, library, overpass
from .canopy import Canopy  
from .elevation import profile
from .extract import LocalSource
from .geometry import bbox_of
from .graph import Graph
from .router import route_through, summarise

DEFAULT_SUN_PENALTY = 4.0
DEFAULT_ROAD_PENALTY = 2.2

INDEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "index")


# profiling was brutal : overpass ate 99.8 % of the wall clock and every bit of our own
# maths fit in under a second. The index is the fast path, the network the last resort
# Loading one costs about two seconds, the handful last asked for are kept
@functools.lru_cache(maxsize=4)
def load_index(path):
    return LocalSource(path)


def source_for(bbox, directory=None, log=print):
    """Whichever index covers the zone, overpass when not one of them does"""
    chosen = library.pick(directory or INDEX_DIR, bbox)
    if (chosen is None):
        log("Aucun index local ne couvre la zone, repli sur Overpass")
        return overpass

    log("Index local : %s" % chosen["label"])
    return load_index(chosen["path"])


def plan(waypoints, sun_penalty=DEFAULT_SUN_PENALTY, road_penalty=DEFAULT_ROAD_PENALTY,
         close_loop=True, with_elevation=True, source=None, log=print):
    """waypoints is a list of dicts carrying name, lat and lon, in walking order.

    Returns everything an interface could want : the tracé, the per segment shade,
    the surface mix, the altimetry and the gpx. It knows nothing about who calls it"""

    if (len(waypoints) < 2):
        raise ValueError("il faut au moins deux points de passage")

    ordered = list(waypoints)
    first = (ordered[0]["lat"], ordered[0]["lon"])
    last = (ordered[-1]["lat"], ordered[-1]["lon"])
    if (close_loop and first != last):
        ordered.append(dict(ordered[0]))

    coords = [(w["lat"], w["lon"]) for w in ordered]
    bbox = bbox_of(coords)
    log("Zone : %.4f,%.4f -> %.4f,%.4f" % bbox)

    if (source is None):
        source = source_for(bbox, log=log)
    elif (isinstance(source, LocalSource) and not source.covers(bbox)):
        # a caller handing us its own index still gtes sent back on the wire when
        # the walk wanders outside of it
        log("Hors de l'index local, repli sur Overpass")
        source = overpass

    network = source.fetch_network(bbox, log=log)
    woods = source.fetch_canopy(bbox, log=log)

    canopy = Canopy(woods["elements"])
    log("Canopee : %d contours, %d clairieres" % (canopy.outer_count, canopy.clearing_count))

    graph = Graph(network["elements"], canopy,
                  sun_penalty=sun_penalty, road_penalty=road_penalty)
    log("Graphe : %d noeuds, %d aretes, %.0f %% sous couvert, %d voies ecartees"
        % (graph.node_count, graph.edge_count, graph.shaded_share(), graph.rejected))

    if (graph.edge_count == 0):
        raise ValueError("aucun chemin praticable dans cette zone")

    anchors = []
    for waypoint in ordered:
        node, gap = graph.nearest_node(waypoint["lat"], waypoint["lon"])
        if (gap > 500.0):
            log("   %s : accroche a %.0f m, c'est loin de tout chemin"
                % (waypoint.get("name") or "?", gap))
        anchors.append(node)

    path, legs = route_through(graph, anchors)
    for waypoint, leg in zip(ordered[1:], legs):
        log("   -> %-28s %5.2f km" % ((waypoint.get("name") or "?")[:28], leg / 1000.0))

    stats = summarise(graph, path)
    log("Boucle : %.2f km, %.1f %% a l'ombre, %.0f m de route"
        % (stats["metres"] / 1000.0, stats["shade_pct"], stats["road_metres"]))

    if (stats["off_network_metres"] > 0.0):
        log("ATTENTION : %.0f m hors reseau OSM" % stats["off_network_metres"])

    if (with_elevation):
        log("Altimetrie : %d points..." % len(path))
        alti = profile(path, log=log)
        log("D+ %.0f m / D- %.0f m (entre %.0f et %.0f m)"
            % (alti["up"], alti["down"], alti["min"], alti["max"]))
    else:
        alti = {"heights": [0.0] * len(path), "up": 0.0, "down": 0.0, "min": 0.0, "max": 0.0}


    # the named waypoints are snapped onto the network too, the marker then sts on the tracé
    marks = [] 
    for waypoint, node in zip(ordered, anchors):
        marks.append({"name": waypoint.get("name") or "Point", "lat": node[0], "lon": node[1]})

    name = waypoints[0].get("name") or "Boucle"
    track = [(lat, lon) for lat, lon in path]
    document = gpx.write(name, track, alti["heights"], marks[:-1] if close_loop else marks)

    cumulative = []
    running = 0.0
    for segment in stats["segments"]:
        cumulative.append(running)
        running += segment["length"]
    cumulative.append(running)

    return {
        "name": name,
        "bbox": {"minlat": bbox[0], "minlon": bbox[1], "maxlat": bbox[2], "maxlon": bbox[3]},
        "waypoints": marks,
        "points": [{"lat": lat, "lon": lon, "ele": round(h, 1), "km": round(d / 1000.0, 4)}
                   for (lat, lon), h, d in zip(track, alti["heights"], cumulative)],
        "shade": [1 if s["shaded"] else 0 for s in stats["segments"]],
        # per segment surface, the map can then colour by what is underfoot and not
        # only by exposure. A tarmac lane under the trees reads as shaded, which is
        # true but hides the atrmac from the eye
        "seg_surface": [s["surface"] for s in stats["segments"]],
        "canopy": canopy.clipped_rings(box(bbox[1], bbox[0], bbox[3], bbox[2])),
        "stats": {
            "km": round(stats["metres"] / 1000.0, 3),
            "shade_pct": round(stats["shade_pct"], 1),
            "sun_metres": round(stats["metres"] - stats["shaded_metres"]),
            "road_metres": round(stats["road_metres"]),
            "off_network_metres": round(stats["off_network_metres"]),
            "up": round(alti["up"]),
            "down": round(alti["down"]), 
            "min_ele": round(alti["min"]),
            "max_ele": round(alti["max"]),
            "nodes": graph.node_count,
            "edges": graph.edge_count,
            "clearings": canopy.clearing_count,
        },
        "surfaces": [{"key": k, "metres": round(m)} for k, m in stats["surfaces"]],
        "highways": [{"key": k, "metres": round(m)} for k, m in stats["highways"]],
        "gpx": document,
    }
