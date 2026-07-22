#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Index catalogue : picking the right zone without opening twenty megabytes of others"""

import gzip  
import json

import pytest

from core import library


def make_index(directory, name, bbox, sidecar=True):
    path = directory / (name + ".json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as handle: 
        json.dump({"bbox": list(bbox), "network": [], "canopy": []}, handle)

    if (sidecar):
        library.write_meta(str(path), bbox, label=name.title())
    return str(path)


@pytest.fixture
def shelf(tmp_path):
    make_index(tmp_path, "grandest", (47.0, 4.8, 49.6, 8.3))
    make_index(tmp_path, "vosges", (48.3, 6.9, 49.1, 7.8))
    return tmp_path


def test_an_index_is_found(shelf):
    entries = library.available(str(shelf))
    assert {e["name"] for e in entries} == {"grandest", "vosges"}


def test_the_tightest_covering_index_wins(shelf):
    # both cover the zone, the narrow one holsd fewer chemins to sift through
    chosen = library.pick(str(shelf), (48.98, 7.49, 49.04, 7.60))
    assert chosen["name"] == "vosges"


def test_a_zone_only_the_wide_one_holds(shelf):
    chosen = library.pick(str(shelf), (47.5, 5.0, 47.8, 5.4))
    assert chosen["name"] == "grandest"


def test_nothing_covers_the_alps(shelf):
    assert library.pick(str(shelf), (45.90, 6.85, 45.95, 6.90)) is None


def test_a_zone_hanging_over_the_edge_is_refused(shelf):
    # partly covered is not covered, half a netowrk would route into a wall
    assert library.pick(str(shelf), (49.0, 7.5, 49.9, 7.6)) is None


def test_a_missing_sidecar_is_written_on_first_sight(tmp_path):
    path = make_index(tmp_path, "ancien", (48.0, 7.0, 49.0, 8.0), sidecar=False)

    meta = library.read_meta(path)
    assert tuple(meta["bbox"]) == (48.0, 7.0, 49.0, 8.0)
    assert (tmp_path / "ancien.meta.json").exists()


def test_a_broken_fichier_does_not_sink_the_others(shelf):
    (shelf / "casse.json.gz").write_bytes(b"ceci n'est pas du gzip")

    entries = library.available(str(shelf))
    assert {e["name"] for e in entries} == {"grandest", "vosges"}


def test_an_empty_shelf_offers_nothing(tmp_path):
    assert library.available(str(tmp_path)) == []
    assert library.pick(str(tmp_path), (49.0, 7.5, 49.1, 7.6)) is None


def test_the_label_survives_the_round_trip(shelf):
    chosen = library.pick(str(shelf), (48.98, 7.49, 49.04, 7.60))
    assert chosen["label"] == "Vosges"
