#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generates a loop from the command line. Marshals arguments, calls core, writes files"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import plan
from core.pipeline import DEFAULT_ROAD_PENALTY, DEFAULT_SUN_PENALTY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS = os.path.join(ROOT, "data", "presets.json")


def parse_waypoint(raw):
    """Accepts lat,lon or lat,lon,name"""
    bits = [b.strip() for b in raw.split(",")]
    if (len(bits) < 2):
        raise argparse.ArgumentTypeError("attendu lat,lon[,nom] mais recu : %s" % raw)

    try:
        lat = float(bits[0])
        lon = float(bits[1])
    except ValueError:
        raise argparse.ArgumentTypeError("coordonnees illisibles : %s" % raw)

    name = bits[2] if len(bits) > 2 else "Point"
    return {"name": name, "lat": lat, "lon": lon}


def load_preset(key):
    with open(PRESETS, encoding="utf-8") as handle:
        presets = json.load(handle)

    if (key not in presets):
        raise SystemExit("preset inconnu : %s (dispo : %s)"
                         % (key, ", ".join(sorted(presets))))
    return presets[key]["waypoints"]


def build_parser(): 
    parser = argparse.ArgumentParser(
        prog="cli.generate",
        description="Trace une boucle de randonnee en privilegiant les chemins ombrages")
    parser.add_argument("-w", "--waypoint", type=parse_waypoint, action="append",
                        metavar="LAT,LON[,NOM]", help="point de passage, repetable")
    parser.add_argument("-p", "--preset", help="jeu de points de passage predefini")
    parser.add_argument("-o", "--out", default="out", help="prefixe des fichiers de sortie")
    parser.add_argument("--sun-penalty", type=float, default=DEFAULT_SUN_PENALTY,
                        help="cout d'un metre au soleil, en metres equivalents")
    parser.add_argument("--road-penalty", type=float, default=DEFAULT_ROAD_PENALTY,
                        help="surcout supplementaire du bitume")
    parser.add_argument("--no-loop", action="store_true", help="ne pas refermer la boucle")
    parser.add_argument("--no-elevation", action="store_true",
                        help="sauter l'altimetrie, bien plus rapide")
    parser.add_argument("--list-presets", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if (args.list_presets):
        with open(PRESETS, encoding="utf-8") as handle:
            for key, value in sorted(json.load(handle).items()):
                print("%-22s %s" % (key, value["label"]))
        return 0

    waypoints = args.waypoint or (load_preset(args.preset) if args.preset else None)
    if (not waypoints):
        parser.error("donnez au moins deux --waypoint, ou un --preset")

    result = plan(   
        waypoints,
        sun_penalty=args.sun_penalty,
        road_penalty=args.road_penalty,
        close_loop=not args.no_loop,
        with_elevation=not args.no_elevation,  
    )

    gpx_path = args.out + ".gpx"
    json_path = args.out + ".json"

    with open(gpx_path, "w", encoding="utf-8") as handle:
        handle.write(result["gpx"])

    payload = {k: v for k, v in result.items() if k != "gpx"}
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    print()
    print("Ecrit : %s" % gpx_path)
    print("Ecrit : %s" % json_path)
    return 0


if (__name__ == "__main__"):
    raise SystemExit(main())
