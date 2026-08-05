#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The json bridge, whose whole contract is that stdout carries json and nothing else"""

import io
import json

import pytest

from cli import bridge, engine

TRACK = {
    "name": "Boucle",
    "stats": {"km": 8.99},
    "gpx": "<?xml version=\"1.0\"?><gpx/>",
}


@pytest.fixture
def answered(monkeypatch):
    def fake(request, log=print):
        log("Zone : une trace bidon pour %d points" % len(request["waypoints"]))
        return dict(TRACK)

    monkeypatch.setattr(bridge, "handle_request", fake)
    return fake


def run(monkeypatch, payload):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    code = bridge.main()
    return code, out.getvalue()


@pytest.mark.usefixtures("answered")
def test_stdout_carries_json_and_nothing_else(monkeypatch):
    """A stray print upstream lands before the payload and the front reads chien{...}"""
    code, written = run(monkeypatch, {"waypoints": [1, 2], "withElevation": False})

    assert code == 0
    assert written.lstrip().startswith("{"), "quelque chose a pollue stdout"
    assert json.loads(written)["stats"]["km"] == pytest.approx(8.99)


@pytest.mark.usefixtures("answered")
def test_the_engine_log_never_reaches_stdout(monkeypatch):
    code, written = run(monkeypatch, {"waypoints": [1, 2]})

    assert code == 0
    assert "bidon" not in written


def test_a_refused_request_still_answers_json(monkeypatch):
    code, written = run(monkeypatch, {"waypoints": [{"lat": 49.0, "lon": 7.5}]})

    assert code == 1
    assert "error" in json.loads(written)


def test_unreadable_input_answers_json(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("ceci n'est pas du json"))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    assert bridge.main() == 1
    assert "error" in json.loads(out.getvalue())


def test_an_expected_failure_is_dressed_as_an_error(monkeypatch):
    def boom(request, log=print):
        raise ValueError("aucun chemin praticable dans cette zone")

    monkeypatch.setattr(bridge, "handle_request", boom)
    code, written = run(monkeypatch, {"waypoints": [1, 2]})

    assert code == 1
    assert "praticable" in json.loads(written)["error"]


def test_an_unexpected_failure_is_not_swallowed(monkeypatch):
    """A real bug must crash loudly, not come back as a polite message to the walker"""
    def boom(request, log=print):
        raise KeyError("un vrai bug")

    monkeypatch.setattr(bridge, "handle_request", boom)

    with pytest.raises(KeyError):
        run(monkeypatch, {"waypoints": [1, 2]})


def test_the_two_adapters_share_one_marshaller():
    # serve.py and bridge.py both go through it, a default cannot drift between them
    from cli import serve
    assert serve.handle_request is engine.handle_request
    assert bridge.handle_request is engine.handle_request


def test_a_request_carrying_a_gpx_is_read_and_not_routed(monkeypatch):
    """A front that uploads a fichier must not be told it lacks waypoints"""
    seen = {}

    def fake_analyse(request, log=print):
        seen["analysed"] = True
        return dict(TRACK)

    def fake_plan(request, log=print):
        seen["planned"] = True
        return dict(TRACK)

    monkeypatch.setattr(engine, "analyse_from_request", fake_analyse)
    monkeypatch.setattr(engine, "plan_from_request", fake_plan)

    engine.handle_request({"gpx": "<gpx/>"}, log=lambda _: None)
    assert seen == {"analysed": True}

    engine.handle_request({"waypoints": [1, 2]}, log=lambda _: None)
    assert seen == {"analysed": True, "planned": True}


def test_an_oversized_gpx_is_refused_before_it_is_parsed():
    with pytest.raises(ValueError):
        engine.analyse_from_request({"gpx": "x" * (engine.MAX_GPX_BYTES + 1)},
                                    log=lambda _: None)


TWO_POINTS = [{"lat": 49.0, "lon": 7.5}, {"lat": 49.0, "lon": 7.51}]


def test_a_nan_penalty_is_refused_before_it_reaches_the_router():
    """The bridge is the real API, a NaN posted at it rides into every edge cost"""
    with pytest.raises(ValueError):
        engine.plan_from_request({"waypoints": TWO_POINTS, "sunPenalty": float("nan")},
                                 log=lambda _: None)


def test_a_sac_grade_that_does_not_exist_is_refused():
    with pytest.raises(ValueError):
        engine.plan_from_request({"waypoints": TWO_POINTS, "maxSac": 9},
                                 log=lambda _: None)
