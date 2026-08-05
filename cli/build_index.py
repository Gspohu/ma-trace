#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds a local OSM index once, the router then never touches the network again"""

import argparse
import glob
import os
import sys
import time  

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import library
from core.extract import build_index, header_bbox

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX_DIR = os.path.join(ROOT, "data", "index")
DEFAULT_EXTRACTS = os.path.join(ROOT, "extracts", "*.osm.pbf")


def describe(entry):
    zone = entry["bbox"]
    return "%-16s %-34s %.2f,%.2f -> %.2f,%.2f" % (
        entry["name"], entry["label"][:34], zone[0], zone[1], zone[2], zone[3])


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cli.build_index",
        description="Prepare un index OSM local a partir des extraits geofabrik")  
    parser.add_argument("-e", "--extracts", default=DEFAULT_EXTRACTS,
                        help="motif glob vers les fichiers .osm.pbf")
    parser.add_argument("-n", "--name", help="nom de l'index, sert de nom de fichier")
    parser.add_argument("-l", "--label", help="libelle lisible affiche dans l'interface")
    parser.add_argument("-o", "--out", help="chemin complet de sortie, prime sur --name")
    parser.add_argument("--bbox", nargs=4, type=float,
                        metavar=("MINLAT", "MINLON", "MAXLAT", "MAXLON"),
                        help="zone a decouper, deduite des extraits si omise")
    parser.add_argument("--list", action="store_true",
                        help="lister les index deja construits et sortir")

    args = parser.parse_args(argv)

    if (args.list):
        entries = library.available(INDEX_DIR)
        if (not entries):
            print("Aucun index dans %s" % INDEX_DIR)
            return 0

        for entry in entries:
            print(describe(entry))
        return 0

    paths = sorted(glob.glob(args.extracts))
    if (not paths):
        raise SystemExit("aucun extrait trouve pour le motif : %s" % args.extracts)

    bbox = tuple(args.bbox) if args.bbox else header_bbox(paths)
    if (bbox is None):
        raise SystemExit("les extraits ne declarent aucune zone, donnez --bbox a la main")

    if (bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
        raise SystemExit("zone incoherente : %.4f,%.4f -> %.4f,%.4f" % bbox)

    # naming the index afte the extracts keeps a foldre of them readable
    name = args.name or "-".join(sorted(
        os.path.basename(p).split(".")[0].replace("-latest", "") for p in paths))
    out = args.out or os.path.join(INDEX_DIR, name + ".json.gz")

    os.makedirs(os.path.dirname(out), exist_ok=True)

    print("Index : %s" % name)
    print("Zone : %.4f,%.4f -> %.4f,%.4f%s"
          % (bbox + ("" if args.bbox else "  (deduite des extraits)",)))
    print("Extraits : %s" % ", ".join(os.path.basename(p) for p in paths))
    print()

    started = time.perf_counter()
    build_index(paths, bbox, out, label=args.label or name)
    print()
    print("Termine en %.0f s" % (time.perf_counter() - started))
    return 0


if (__name__ == "__main__"):
    raise SystemExit(main())
