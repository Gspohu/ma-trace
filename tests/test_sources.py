#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The two sources are picked between at runtime, they have to answer the same calls"""

import gzip
import json

import pytest

from core import overpass
from core.extract import LocalSource

BBOX = (48.99, 7.49, 49.01, 7.53)

CONTRACT = ("fetch_network", "fetch_canopy", "fetch_landmarks")


def index(tmp_path, **extra):
    payload = {"bbox": list(BBOX), "network": [], "canopy": []}
    payload.update(extra)

    path = tmp_path / "zone.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)

    return LocalSource(str(path))


@pytest.mark.parametrize("call", CONTRACT)
def test_both_sources_answer_the_same_calls(tmp_path, call):
    """fetch_landmarks lived on overpass alone for a while, an AttributeError waiting"""
    local = index(tmp_path)

    assert callable(getattr(overpass, call))
    assert callable(getattr(local, call))


def test_the_local_reperes_come_back_in_the_overpass_shape(tmp_path):
    # the index predates drinkable, the record must still come back whole
    local = index(tmp_path, landmarks=[
        {"name": "Falkenstein", "kind": "castle", "lat": 49.0, "lon": 7.51, "fee": None},
    ])

    found = local.fetch_landmarks(BBOX, log=lambda _: None)

    assert len(found) == 1
    assert set(found[0]) == {"name", "kind", "lat", "lon", "fee", "drinkable"}
    assert found[0]["drinkable"] is None


def test_a_repere_outside_the_zone_is_left_out(tmp_path):
    local = index(tmp_path, landmarks=[
        {"name": "Loin", "kind": "water", "lat": 45.0, "lon": 6.0, "fee": None},
        {"name": "Ici", "kind": "rock", "lat": 49.0, "lon": 7.5, "fee": None},
    ])

    found = local.fetch_landmarks(BBOX, log=lambda _: None)
    assert [f["name"] for f in found] == ["Ici"]


def test_an_index_built_before_the_reperes_still_loads(tmp_path):
    """Twenty megabytes take three minutes to rebuild, and yesterday's fichier routes"""
    local = index(tmp_path)

    assert local.fetch_landmarks(BBOX, log=lambda _: None) == []
    assert local.covers(BBOX)


class _Answer:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        if (isinstance(self._payload, Exception)):
            raise self._payload
        return self._payload


def test_a_timed_out_answer_is_not_taken_for_a_network(monkeypatch):
    """Overpass says 200 with a partial payload, and half a network walks into a wall"""
    truncated = {"elements": [], "remark": "runtime error: Query timed out after 26 seconds."}
    whole = {"elements": [{"type": "way", "id": 1}]}
    answers = iter([truncated, whole])

    monkeypatch.setattr(overpass._session, "post",
                        lambda url, data=None, timeout=0: _Answer(next(answers)))
    monkeypatch.setattr(overpass.time, "sleep", lambda seconds: None)

    assert overpass.query("bidon", log=lambda _: None) == whole


def test_every_mirror_truncating_fails_loudly(monkeypatch):
    truncated = {"elements": [], "remark": "runtime error: Query timed out"}
    monkeypatch.setattr(overpass._session, "post",
                        lambda url, data=None, timeout=0: _Answer(truncated))
    monkeypatch.setattr(overpass.time, "sleep", lambda seconds: None)

    with pytest.raises(overpass.OverpassError):
        overpass.query("bidon", tries=1, log=lambda _: None)


def test_an_unreadable_body_moves_on_to_the_next_mirror(monkeypatch):
    answers = iter([ValueError("pas du json"), {"elements": []}])
    monkeypatch.setattr(overpass._session, "post",
                        lambda url, data=None, timeout=0: _Answer(next(answers)))
    monkeypatch.setattr(overpass.time, "sleep", lambda seconds: None)

    assert overpass.query("bidon", log=lambda _: None) == {"elements": []}
