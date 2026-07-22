#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Overpass client with mirror failover, plus the queries the router needs"""

import os
import time

import requests

_DEFAULT_MIRRORS = (
    "https://overpass.kumi.systems/api/interpreter",  
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
) 

MIRRORS = tuple(
    m.strip() for m in os.environ.get("OVERPASS_MIRRORS", "").split(",") if m.strip()
) or _DEFAULT_MIRRORS

# overpass answers 406 to the defaut requests user agent, it wants a real one
HEADERS = {"User-Agent": "ma-trace/0.2 (shade weighted hiking router)"}


# one session for the whole run, the mirrors are hit severa times each and a
# fresh tcp handshake per call is pure waste
_session = requests.Session()
_session.headers.update(HEADERS)

# we only reject the hopeless classes here. The access rules are far too subtle to
# express in an overpass filter : access=no with foot=yes is walkable (the Waldeck
# castle steps are exactly that), access=no aolne is not. That triage lives in graph.py
NETWORK_FILTER = (
    '["highway"]'
    '["highway"!~"^(motorway|motorway_link|trunk|trunk_link|proposed|construction|raceway)$"]'
)


class OverpassError(RuntimeError):
    pass


def query(body, tries=3, timeout=240, log=print):
    """Fire the same query at each mirror until one of them answers"""   
    last = "aucun miroir contacte"

    for attempt in range(tries):
        for url in MIRRORS:
            try:
                response = _session.post(url, data={"data": body}, timeout=timeout)
            except requests.RequestException as exc:
                last = "%s : %s" % (url, exc)
                log("   miroir indisponible : %s" % last)
                continue

            if (response.status_code == 200):
                return response.json()

            last = "%s : HTTP %d" % (url, response.status_code)
            log("   miroir indisponible : %s" % last)

        time.sleep(5 * (attempt + 1))

    raise OverpassError("tous les miroirs Overpass ont echoue, dernier : %s" % last)


def _bbox(box):
    return "%.6f,%.6f,%.6f,%.6f" % (box[0], box[1], box[2], box[3])


def fetch_network(bbox, log=print): 
    """Every way a walker may legally use inside the box"""
    log("   reseau pietonnier...")
    body = "[out:json][timeout:240];way(%s)%s;out geom tags;" % (_bbox(bbox), NETWORK_FILTER)
    data = query(body, log=log)
    log("   %d chemins" % len(data["elements"]))
    return data


def fetch_canopy(bbox, log=print):
    """Forest and wood polygons, relations included, they carry the clairieres as inner rings"""
    log("   couvert forestier...")
    box = _bbox(bbox)
    body = ("[out:json][timeout:240];("
            'way(%s)["landuse"="forest"];'
            'way(%s)["natural"="wood"];'
            'rel(%s)["landuse"="forest"];'
            'rel(%s)["natural"="wood"];'
            ");out geom;" % (box, box, box, box))
    data = query(body, log=log)
    log("   %d polygones" % len(data["elements"]))
    return data


def fetch_landmarks(bbox, log=print):
    """Castles, water, rocks and parkings, the things worth routing through"""
    log("   points remarquables...")
    box = _bbox(bbox)
    body = ("[out:json][timeout:180];("
            'nwr(%s)["historic"="castle"];'
            'nwr(%s)["natural"="water"];'
            'nwr(%s)["natural"="rock"];'
            'nwr(%s)["amenity"="parking"];'
            ");out center tags;" % (box, box, box, box))
    data = query(body, log=log)

    out = []
    for element in data["elements"]:
        tags = element.get("tags", {})
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")
        if (lat is None or lon is None):
            continue

        kind = "parking"
        if (tags.get("historic") == "castle"):
            kind = "castle"
        elif (tags.get("natural") == "water"):
            kind = "water"
        elif (tags.get("natural") == "rock"):
            kind = "rock"

        out.append({
            "name": tags.get("name") or "",
            "kind": kind,
            "lat": lat,
            "lon": lon,
            "fee": tags.get("fee"),
        })

    log("   %d reperes" % len(out))
    return out
