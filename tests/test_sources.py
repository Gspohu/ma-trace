#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The two sources are picked between at runtime, they have to answer the same calls"""

import gzip
import json

import pytest

from core import overpass
from core.canopy import Canopy
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


def _asked(monkeypatch, call, *args):
    seen = {}

    def capture(body, log=print):
        seen["body"] = body
        return {"elements": []}

    monkeypatch.setattr(overpass, "query", capture)
    call(*args, log=lambda _: None)
    return seen["body"]


def test_the_canopy_query_asks_for_relation_members(monkeypatch):
    """A verbosity mode excludes the others, and tags prints neither coordinates nor
    members. Asked that way a massif drawn as a multipolygone comes back empty, which
    on the hanau forest meant 2 % of the real cover and an honest looking 0 % of shade"""
    body = _asked(monkeypatch, overpass.fetch_canopy, BBOX)

    assert "out body geom" in body
    assert "out geom tags" not in body


def test_the_canopy_query_still_wants_the_relations(monkeypatch):
    body = _asked(monkeypatch, overpass.fetch_canopy, BBOX)

    assert 'rel(' in body and '"landuse"="forest"' in body


def test_a_relation_without_members_covers_nothing():
    # what overpass hands back under the tags mode, tags and bounds but no geometry
    stripped = [{"type": "relation", "id": 1, "tags": {"landuse": "forest"},
                 "bounds": {"minlat": 48.9, "minlon": 7.5,
                            "maxlat": 49.0, "maxlon": 7.6}}]

    assert Canopy(stripped).outer_count == 0


def test_the_same_massif_with_its_members_does_cover():
    ring = [{"lat": 48.9, "lon": 7.5}, {"lat": 48.9, "lon": 7.6},
            {"lat": 49.0, "lon": 7.6}, {"lat": 49.0, "lon": 7.5},
            {"lat": 48.9, "lon": 7.5}]
    whole = [{"type": "relation", "id": 1, "tags": {"landuse": "forest"},
              "members": [{"role": "outer", "type": "way", "geometry": ring}]}]

    cover = Canopy(whole)
    assert cover.outer_count == 1
    assert cover.shape.area > 0.0


def test_one_answer_is_sorted_back_into_three(monkeypatch):
    """Overpass walks the box once and hands everything back mixed. The three filters
    cannot select the same element, which is what makes sorting on tags safe"""
    ring = [{"lat": 49.0, "lon": 7.5}, {"lat": 49.0, "lon": 7.6},
            {"lat": 49.1, "lon": 7.6}, {"lat": 49.0, "lon": 7.5}]

    mixed = {"elements": [
        {"type": "way", "id": 1, "tags": {"highway": "path"}, "geometry": ring},
        {"type": "way", "id": 2, "tags": {"landuse": "forest"}, "geometry": ring},
        {"type": "relation", "id": 3, "tags": {"natural": "wood"},
         "members": [{"role": "outer", "geometry": ring}]},
        {"type": "node", "id": 4, "tags": {"historic": "castle", "name": "Falkenstein"},
         "lat": 49.05, "lon": 7.55},
        {"type": "way", "id": 5, "tags": {"building": "yes"}, "geometry": ring},
    ]}

    monkeypatch.setattr(overpass, "query", lambda body, log=print: mixed)

    network, canopy, reperes = overpass.fetch_everything(BBOX, log=lambda _: None)

    assert [e["id"] for e in network["elements"]] == [1]
    assert [e["id"] for e in canopy["elements"]] == [2, 3]
    assert [r["name"] for r in reperes] == ["Falkenstein"]


def test_the_single_ask_carries_the_three_output_modes(monkeypatch):
    seen = {}

    def capture(body, log=print):
        seen["body"] = body
        return {"elements": []}

    monkeypatch.setattr(overpass, "query", capture)
    overpass.fetch_everything(BBOX, log=lambda _: None)

    # a massif needs its members, a repere only its centre, a chemin its geometry
    assert ".net out geom tags;" in seen["body"]
    assert ".wood out body geom;" in seen["body"]
    assert ".marks out center tags;" in seen["body"]


def test_the_reperes_can_be_left_out_of_the_ask(monkeypatch):
    seen = {}

    def capture(body, log=print):
        seen["body"] = body
        return {"elements": []}

    monkeypatch.setattr(overpass, "query", capture)
    _, _, reperes = overpass.fetch_everything(BBOX, with_landmarks=False,
                                              log=lambda _: None)

    assert reperes == []
    assert ".marks" not in seen["body"]


def test_the_same_zone_is_not_asked_twice(monkeypatch):
    """Nudging a curseur redraws over the very same box, and that ask is the whole
    wait. The second one has to cost nothing"""
    calls = {"count": 0}

    def answer(url, data=None, timeout=0):
        calls["count"] += 1
        return _Answer({"elements": [{"type": "way", "id": 1}]})

    overpass.forget()
    monkeypatch.setattr(overpass._session, "post", answer)

    first = overpass.query("bidon", log=lambda _: None)
    second = overpass.query("bidon", log=lambda _: None)

    assert calls["count"] == 1
    assert first == second


def test_another_zone_is_asked_for(monkeypatch):
    calls = {"count": 0}

    def answer(url, data=None, timeout=0):
        calls["count"] += 1
        return _Answer({"elements": []})

    overpass.forget()
    monkeypatch.setattr(overpass._session, "post", answer)

    overpass.query("une zone", log=lambda _: None)
    overpass.query("une autre", log=lambda _: None)

    assert calls["count"] == 2


def test_the_memo_never_grows_without_bound(monkeypatch):
    """A phone has little to spare and one answer runs to several megabytes"""
    overpass.forget()
    monkeypatch.setattr(overpass._session, "post",
                        lambda url, data=None, timeout=0: _Answer({"elements": []}))

    for i in range(overpass.CACHE_DEPTH + 4):
        overpass.query("zone %d" % i, log=lambda _: None)

    assert len(overpass._answers) == overpass.CACHE_DEPTH


def test_a_truncated_answer_is_never_kept(monkeypatch):
    """It failed, and serving that failure again from memory would freeze the bug in"""
    truncated = {"elements": [], "remark": "runtime error: Query timed out"}
    overpass.forget()
    monkeypatch.setattr(overpass._session, "post",
                        lambda url, data=None, timeout=0: _Answer(truncated))
    monkeypatch.setattr(overpass.time, "sleep", lambda seconds: None)

    with pytest.raises(overpass.OverpassError):
        overpass.query("bidon", tries=1, log=lambda _: None)

    assert "bidon" not in overpass._answers
