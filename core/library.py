#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalogue of the prebuilt indexes, and the pick of whichever one covers a zone"""

import glob
import gzip
import json
import os

META_SUFFIX = ".meta.json"
INDEX_GLOB = "*.json.gz" 


def _stem(path):
    name = os.path.basename(path)
    if (name.endswith(".json.gz")):
        return name[:-len(".json.gz")]
    return os.path.splitext(name)[0]


def _meta_for(index_path):
    return os.path.join(os.path.dirname(index_path), _stem(index_path) + META_SUFFIX)


def write_meta(index_path, bbox, label=None):
    name = _stem(index_path)
    payload = {"name": name, "label": label or name, "bbox": list(bbox)}


    with open(_meta_for(index_path), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return payload


def read_meta(index_path):
    """Reach of one index, read from the sidecar.

    An index built before the sidecar existed has none, and gets one written the
    first time it is seen. That costs one full read of a twenty megabyte fichier,
    once, rather than on every single trace"""
    side = _meta_for(index_path)
    if (os.path.exists(side)):
        with open(side, encoding="utf-8") as handle:
            return json.load(handle)

    with gzip.open(index_path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    return write_meta(index_path, payload["bbox"])


def available(directory):
    """Every usable index in the folder, with its label and its reach.

    A file we cannot make sense of is skipped rather than fatal, one broken index
    must never stop the others from being offered"""
    entries = []

    for path in sorted(glob.glob(os.path.join(directory, INDEX_GLOB))):
        try: 
            meta = read_meta(path)
            bbox = tuple(float(v) for v in meta["bbox"])
        except (OSError, ValueError, KeyError, TypeError):
            continue

        if (len(bbox) != 4):
            continue

        entries.append({
            "path": path,
            "name": meta.get("name") or _stem(path),
            "label": meta.get("label") or _stem(path),
            "bbox": bbox,
        })

    return entries


def covers(zone, bbox):
    return (bbox[0] >= zone[0] and bbox[1] >= zone[1]
            and bbox[2] <= zone[2] and bbox[3] <= zone[3])


def _area(bbox):
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def pick(directory, bbox):
    """The tightest index that fully contains the zone, or None when none does.

    Tightest and not first : a small index holds fewer chemins to scan, and the
    narrowest match keeps the per trace filtering cheap when zones overlap"""
    fitting = [entry for entry in available(directory) if covers(entry["bbox"], bbox)]
    if (not fitting):
        return None

    fitting.sort(key=lambda entry: _area(entry["bbox"]))
    return fitting[0]
