#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestration : waypoints in, a fully described loop out"""

import functools
import os

from shapely.geometry import box

from . import gpx, library, overpass, pace
from .canopy import Canopy
from .elevation import profile
from .extract import LocalSource
from .geometry import bbox_of
from .graph import DEFAULT_MAX_SAC, MAX_SAC, Graph
from .matching import Network, match
from .router import route_through, summarise, tally

DEFAULT_SUN_PENALTY = 4.0
DEFAULT_ROAD_PENALTY = 2.2

# one is tobler's own pace, measured on people who kept walking. Above one for a walker
# who stops to look at things, and pace.calibrate reads it back off real outings
DEFAULT_PACE_FACTOR = 1.0

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


def _pick_source(bbox, source, log):
    """Whoever answers for this zone, the caller's own index included"""
    if (source is None):
        return source_for(bbox, log=log)

    if (isinstance(source, LocalSource) and not source.covers(bbox)):
        # a caller handing us its own index still gtes sent back on the wire when
        # the walk wanders outside of it
        log("Hors de l'index local, repli sur Overpass")
        return overpass

    return source


def _gather(source, bbox, with_landmarks, log):
    """The network, the assembled canopy and the reperes, for the zone"""
    # one ask for the three, which is what saves the minutes on a slow overpass. A
    # source too old to know the call still answers the three separately
    if (hasattr(source, "fetch_everything")):
        network, woods, reperes = source.fetch_everything(
            bbox, with_landmarks=with_landmarks, log=log)
    else:
        network = source.fetch_network(bbox, log=log)
        woods = source.fetch_canopy(bbox, log=log)
        reperes = source.fetch_landmarks(bbox, log=log) if with_landmarks else []

    canopy = Canopy(woods["elements"])
    kinds = ", ".join("%s %d" % (kind, count)
                      for kind, count in sorted(canopy.kind_counts.items()))
    log("Canopee : %d contours, %d clairieres (%s)"
        % (canopy.outer_count, canopy.clearing_count, kinds or "aucun"))

    return network, canopy, reperes


def analyse(points, name=None, waypoints=(), with_elevation=True, with_landmarks=True,
            pace_factor=DEFAULT_PACE_FACTOR, source=None, log=print):
    """Read a trace somebody else drew, and say what it actually crosses.

    Nothing is routed here. The trace is taken exactly as given and we only look up
    what runs underneath it, which is why the network is loaded unfiltered : a trace
    may well cross a T4, and being told so is the whole reason to open the fichier"""
    if (len(points) < 2):
        raise ValueError("il faut au moins deux points pour analyser une trace")

    bbox = bbox_of(points)
    log("Zone : %.4f,%.4f -> %.4f,%.4f" % bbox)

    source = _pick_source(bbox, source, log)
    network, canopy, reperes = _gather(source, bbox, with_landmarks, log)

    graph = Graph(network["elements"], canopy, max_sac=MAX_SAC)
    log("Graphe : %d noeuds, %d aretes" % (graph.node_count, graph.edge_count))
    if (graph.edge_count == 0):
        raise ValueError("aucun chemin praticable dans cette zone")

    index = Network(graph)
    described = match(points, index, canopy)
    if (not described):
        raise ValueError("cette trace ne couvre aucune distance")

    stats = tally(described)
    log("Trace : %.2f km, %.1f %% a l'ombre, %.0f %% du plein soleil recu, %.0f m de route"
        % (stats["metres"] / 1000.0, stats["shade_pct"], stats["exposure_pct"],
           stats["road_metres"]))

    hard = [(kind, metres) for kind, metres in stats["difficulties"]
            if kind not in ("non renseigne", "hiking", "mountain_hiking")]
    for kind, metres in hard:
        log("ATTENTION : %.0f m annonces en %s" % (metres, kind))

    return _present(name or "Trace importee", stats, canopy, bbox, list(waypoints),
                    reperes, graph, MAX_SAC, pace_factor=pace_factor,
                    with_elevation=with_elevation, log=log)


def plan(waypoints, sun_penalty=DEFAULT_SUN_PENALTY, road_penalty=DEFAULT_ROAD_PENALTY,
         close_loop=True, with_elevation=True, with_landmarks=True,
         pace_factor=DEFAULT_PACE_FACTOR, max_sac=DEFAULT_MAX_SAC,
         source=None, log=print):
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

    source = _pick_source(bbox, source, log)
    network, canopy, reperes = _gather(source, bbox, with_landmarks, log)

    graph = Graph(network["elements"], canopy, sun_penalty=sun_penalty,
                  road_penalty=road_penalty, max_sac=max_sac)
    log("Graphe : %d noeuds, %d aretes, %.0f %% sous couvert, %d voies ecartees"
        % (graph.node_count, graph.edge_count, graph.shaded_share(), graph.rejected))
    if (graph.too_hard):
        log("   dont %d au-dessus du niveau T%d demande" % (graph.too_hard, max_sac))

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
    log("Boucle : %.2f km, %.1f %% a l'ombre, %.0f %% du plein soleil recu, %.0f m de route"
        % (stats["metres"] / 1000.0, stats["shade_pct"], stats["exposure_pct"],
           stats["road_metres"]))

    # the named waypoints are snapped onto the network too, the marker then sts on the tracé
    marks = []
    for waypoint, node in zip(ordered, anchors):
        marks.append({"name": waypoint.get("name") or "Point", "lat": node[0], "lon": node[1]})

    return _present(
        waypoints[0].get("name") or "Boucle", stats, canopy, bbox, marks, reperes,
        graph, max_sac, pace_factor=pace_factor, with_elevation=with_elevation,
        # a closed loop ends where it started, writing that waypoint twice into the
        # gpx puts two markers on one spot
        gpx_marks=marks[:-1] if close_loop else marks, log=log)


def _present(name, stats, canopy, bbox, marks, reperes, graph, max_sac,
             pace_factor=DEFAULT_PACE_FACTOR, with_elevation=True, gpx_marks=None,
             log=print):
    """Everything both entry points hand back, off the described segments alone.

    plan draws a tracé and analyse reads one somebody else drew. Past the point where
    the segments are described the two have nothing left to disagree about, and one of
    them quietly growing a figure the other lacks is how interfaces go blank"""
    described = stats["segments"]
    if (not described):
        raise ValueError("aucun segment a decrire")

    if (stats["off_network_metres"] > 0.0):
        log("ATTENTION : %.0f m hors reseau OSM" % stats["off_network_metres"])
    if (stats["faint_metres"] > 0.0):
        log("ATTENTION : %.0f m de sentier annonce difficile a suivre"
            % stats["faint_metres"])
    if (stats["steepest_pct"] is not None and abs(stats["steepest_pct"]) >= 20.0):
        log("ATTENTION : passage annonce a %.0f %% de pente" % stats["steepest_pct"])

    track = [segment["a"] for segment in described]
    track.append(described[-1]["b"])

    if (with_elevation):
        log("Altimetrie : %d points..." % len(track))
        alti = profile(track, log=log)
        log("D+ %.0f m / D- %.0f m (entre %.0f et %.0f m)"
            % (alti["up"], alti["down"], alti["min"], alti["max"]))
    else:
        alti = {"heights": [0.0] * len(track), "up": 0.0, "down": 0.0,
                "min": 0.0, "max": 0.0}

    cumulative = []
    running = 0.0
    for segment in described:
        cumulative.append(running)
        running += segment["length"]
    cumulative.append(running)

    # tobler reads the gradient every twenty five metres, and a walk that climbs then
    # drops the same amount is not the same effort as a flat one of equal denivele
    hours = pace.duration(cumulative, alti["heights"], factor=pace_factor)
    log("Duree estimee : %.2f h (facteur d'allure %.2f)" % (hours, pace_factor))

    # the json keeps its zeros for the charts, the gpx stays silent on a missing height
    document = gpx.write(name, track,
                         alti["heights"] if with_elevation else [None] * len(track),
                         marks if gpx_marks is None else gpx_marks)

    return {
        "name": name,
        "bbox": {"minlat": bbox[0], "minlon": bbox[1], "maxlat": bbox[2], "maxlon": bbox[3]},
        "waypoints": marks,
        "landmarks": reperes,
        "points": [{"lat": lat, "lon": lon, "ele": round(h, 1), "km": round(d / 1000.0, 4)}
                   for (lat, lon), h, d in zip(track, alti["heights"], cumulative)],
        "shade": [1 if s["shaded"] else 0 for s in described],
        # per segment surface, the map can then colour by what is underfoot and not
        # only by exposure. A tarmac lane under the trees reads as shaded, which is
        # true but hides the atrmac from the eye
        "seg_surface": [s["surface"] for s in described],
        "canopy": canopy.clipped_rings(box(bbox[1], bbox[0], bbox[3], bbox[2])),
        "stats": {
            "km": round(stats["metres"] / 1000.0, 3),
            "shade_pct": round(stats["shade_pct"], 1),
            "exposure_pct": round(stats["exposure_pct"], 1),
            "sun_metres": round(stats["metres"] - stats["shaded_metres"]),
            "road_metres": round(stats["road_metres"]),
            "off_network_metres": round(stats["off_network_metres"]),
            "faint_metres": round(stats["faint_metres"]),
            "steepest_pct": stats["steepest_pct"],
            "max_sac": max_sac,
            # whether the ground was actually measured. Without it every height sits at
            # zero, and up, down and the tobler duration describe a flat walk nobody
            # took. An interface has to know not to show them
            "has_elevation": bool(with_elevation),
            "up": round(alti["up"]),
            "down": round(alti["down"]),
            "hours": round(hours, 3),
            "pace_factor": pace_factor,
            "min_ele": round(alti["min"]),
            "max_ele": round(alti["max"]),
            "nodes": graph.node_count,
            "edges": graph.edge_count,
            "clearings": canopy.clearing_count,
        },
        "surfaces": [{"key": k, "metres": round(m)} for k, m in stats["surfaces"]],
        "highways": [{"key": k, "metres": round(m)} for k, m in stats["highways"]],
        "covers": [{"key": k, "metres": round(m)} for k, m in stats["covers"]],
        "gpx": document,
    }
