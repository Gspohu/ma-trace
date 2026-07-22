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

    monkeypatch.setattr(bridge, "plan_from_request", fake)
    return fake


def run(monkeypatch, payload):
    """Feeds the bridge a request and hands back whatever landed on stdout"""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    code = bridge.main()
    return code, out.getvalue()


@pytest.mark.usefixtures("answered")
def test_stdout_carries_json_and_nothing_else(monkeypatch):
    """The regression this file exists for.

    A stray print anywhere upstream lands in front of the payload and the front then
    reads chien{...}. It cost a broken interface once, so the contract is now tested"""
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

    monkeypatch.setattr(bridge, "plan_from_request", boom)
    code, written = run(monkeypatch, {"waypoints": [1, 2]})

    assert code == 1
    assert "praticable" in json.loads(written)["error"]


def test_an_unexpected_failure_is_not_swallowed(monkeypatch):
    """A real bug must crash loudly, not come back as a polite message to the walker"""
    def boom(request, log=print):
        raise KeyError("un vrai bug")

    monkeypatch.setattr(bridge, "plan_from_request", boom)

    with pytest.raises(KeyError):
        run(monkeypatch, {"waypoints": [1, 2]})


def test_the_two_adapters_share_one_marshaller():
    # serve.py and bridge.py both go through it, a default cannot drift between them
    from cli import serve
    assert serve.plan_from_request is engine.plan_from_request
    assert bridge.plan_from_request is engine.plan_from_request
