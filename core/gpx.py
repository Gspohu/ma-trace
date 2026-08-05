#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPX 1.1 writer, kept deliberately dumb, and a reader that trusts nothing"""

import re

# the stdlib parser expands internal entities, and this reader is fed whatever fichier
# a walker uploads. defusedxml is the same api with the traps shut
from defusedxml import ElementTree

HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<gpx version="1.1" creator="ma-trace" '
    'xmlns="http://www.topografix.com/GPX/1/1">\n'
)


def escape(text):
    # the ampersand goes first, otherwise the entities writen after it get escaped agian
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write(name, points, heights, waypoints=()):  
    """points is a list of (lat, lon), heights runs alongside it, waypoints are named"""
    if (len(points) != len(heights)):
        raise ValueError("le tableau d'altitudes ne suit pas la trace")

    lines = [HEADER,"  <metadata><name>%s</name></metadata>\n" % escape(name)]

    for waypoint in waypoints:
        lines.append('  <wpt lat="%.7f" lon="%.7f"><name>%s</name></wpt>\n'
                     % (waypoint["lat"], waypoint["lon"], escape(waypoint["name"])))

    lines.append("  <trk><name>%s</name><trkseg>\n" % escape(name))
    for (lat, lon), height in zip(points, heights):
        if (height is None):
            # a walk drawn without altimetrie writes no ele at all, a gps shown
            # zero metres everywhere would believe the walk runs under the sea
            lines.append('    <trkpt lat="%.7f" lon="%.7f"/>\n' % (lat, lon))
        else:
            lines.append('    <trkpt lat="%.7f" lon="%.7f"><ele>%.1f</ele></trkpt>\n'
                         % (lat, lon, height))
    lines.append("  </trkseg></trk>\n</gpx>\n")

    return "".join(lines)


class GpxError(ValueError):
    """A file we cannot make sense of, said plainly enough to show a walker"""


# A well formed document escapes a literal < as &lt,. A match here is therefore always
# a real declaration and never the name somebody gave a waypoint
_DOCTYPE_RE = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)", re.IGNORECASE)


def _refuse_dtd(text):
    """Turn away any document carrying a dtd, before a parser ever sees it.

    Gpx is defined by a schema and has no use for one, while an internal entity
    expands on its way in : measured on python 3.12, 342 octets of nested entities
    come back as a megabyte of text. Expat caps the amplification past eight mebibytes
    of output, which still leaves an uploaded fichier a long way to grow, and the size
    limit upstream weighs what arrives rather than what it turns into. The external
    entity that would read /etc/passwd is already refused, this closes the other half
    """
    if (_DOCTYPE_RE.search(text)):
        raise GpxError("ce gpx embarque une dtd, il est refuse")


def _local(tag):
    # gpx 1.0 and 1.1 declare different namespaces and plenty of devices declare none
    # of them at all, which never moves where the coordinates sit
    return tag.rsplit("}", 1)[-1]


def _number(raw):
    """Whatever a device wrote where a number belongs, None when it is not one"""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _point_of(element):
    """(lat, lon) off a wpt, trkpt or rtept, None when the attributes are unusable"""
    lat = _number(element.get("lat"))
    lon = _number(element.get("lon"))
    if (lat is None or lon is None):
        return None

    if (not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def _height_of(element):
    for child in element:
        if (_local(child.tag) == "ele"):
            return _number((child.text or "").strip())
    return None


def _name_of(element):
    for child in element:
        if (_local(child.tag) == "name"):
            return (child.text or "").strip()
    return ""


def read(text):
    """Track, altitudes and named waypoints out of a gpx document.

    The tree is walked node by node rather than searched : a stray <name> inside the
    first <wpt> would otherwise be taken for the name of the whole trace. Routes are
    read too, some devices hand back a rte where we would have writen a trk"""
    _refuse_dtd(text)

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise GpxError("fichier gpx illisible : %s" % exc)

    if (_local(root.tag) != "gpx"):
        raise GpxError("ce fichier n'est pas un gpx")

    name = ""
    points = []
    heights = []
    waypoints = []

    def take(element):
        point = _point_of(element)
        if (point is None):
            return
        points.append(point)
        heights.append(_height_of(element))

    for child in root:
        tag = _local(child.tag)

        if (tag == "metadata"):
            name = name or _name_of(child)
        elif (tag == "wpt"):
            point = _point_of(child)
            if (point is not None):
                waypoints.append({"name": _name_of(child) or "Point",
                                  "lat": point[0], "lon": point[1]})
        elif (tag in ("trk", "rte")):
            name = name or _name_of(child)
            for sub in child:
                if (_local(sub.tag) == "trkseg"):
                    for node in sub:
                        if (_local(node.tag) == "trkpt"):
                            take(node)
                elif (_local(sub.tag) == "rtept"):
                    take(sub)

    if (len(points) < 2):
        raise GpxError("ce gpx ne contient aucune trace, il faut au moins deux points")

    return {
        "name": name or "Trace importee",
        "points": points,
        # None wherever the file carried no ele, the caller decides what to do about it
        "heights": heights,
        "waypoints": waypoints,
    }
