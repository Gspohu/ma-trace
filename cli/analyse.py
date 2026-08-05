#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reads a gpx from anywhere and says what it crosses. Marshals arguments, calls core"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import analyse
from core.gpx import GpxError, read
from core.pipeline import DEFAULT_PACE_FACTOR


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cli.analyse",
        description="Analyse une trace gpx existante : ombre, revetements, denivele")
    parser.add_argument("gpx", help="le fichier a lire")
    parser.add_argument("-o", "--out", help="prefixe de sortie, sinon rien n'est ecrit")
    parser.add_argument("--pace-factor", type=float, default=DEFAULT_PACE_FACTOR,
                        help="allure personnelle, au-dessus de 1 si vous marchez moins vite")
    parser.add_argument("--no-elevation", action="store_true",
                        help="sauter l'altimetrie, bien plus rapide")
    parser.add_argument("--no-landmarks", action="store_true",
                        help="sauter les reperes, un appel Overpass de moins")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with open(args.gpx, encoding="utf-8") as handle:
            trace = read(handle.read())
    except OSError as exc:
        raise SystemExit("lecture impossible : %s" % exc)
    except GpxError as exc:
        raise SystemExit(str(exc))

    print("Trace lue : %s, %d points, %d reperes nommes"
          % (trace["name"], len(trace["points"]), len(trace["waypoints"])))

    measured = sum(1 for h in trace["heights"] if h is not None)
    if (measured and not args.no_elevation):
        # the file's own altitudes are left alone, a barometer and eu-dem do not measure
        # the same thing and mixing them makes two traces incomparable
        print("   %d altitudes dans le fichier, ignorees au profit du modele de terrain"
              % measured)

    result = analyse(
        trace["points"],
        name=trace["name"],
        waypoints=trace["waypoints"],
        with_elevation=not args.no_elevation,
        with_landmarks=not args.no_landmarks,
        pace_factor=args.pace_factor,
    )

    if (not args.out):
        return 0

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
