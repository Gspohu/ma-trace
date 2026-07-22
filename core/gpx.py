#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPX 1.1 writer, kept deliberately dumb"""  

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
        lines.append('    <trkpt lat="%.7f" lon="%.7f"><ele>%.1f</ele></trkpt>\n'
                     % (lat, lon, height))
    lines.append("  </trkseg></trk>\n</gpx>\n")

    return "".join(lines) 
