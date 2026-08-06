#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End to end through plan(), on a source that answers out of the fixtures"""

import pytest

from core.pipeline import DEFAULT_PACE_FACTOR, analyse, plan

WEST = {"name": "Depart", "lat": 49.000, "lon": 7.500}
EAST = {"name": "Bout", "lat": 49.000, "lon": 7.520}


def quiet(_):
    return None


def test_the_walking_time_comes_out_of_the_plan(shelf):
    # tobler sat here uncalled while the interface ran a naismith line of its own
    result = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)

    assert result["stats"]["hours"] > 0.0
    assert result["stats"]["pace_factor"] == DEFAULT_PACE_FACTOR


def test_a_slower_walker_takes_proportionally_longer(shelf):
    base = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)
    slow = plan([WEST, EAST], source=shelf, with_elevation=False, pace_factor=1.5,
                log=quiet)

    assert slow["stats"]["hours"] == pytest.approx(1.5 * base["stats"]["hours"], rel=0.001)
    assert slow["stats"]["km"] == pytest.approx(base["stats"]["km"])


def test_flat_ground_is_walked_at_toblers_own_speed(shelf):
    result = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)

    speed = result["stats"]["km"] / result["stats"]["hours"]
    assert speed == pytest.approx(5.04, abs=0.05)


def test_reading_back_our_own_trace_gives_the_same_figures(shelf):
    """The bare points handed back as a stranger's must give every figure again"""
    drawn = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)
    points = [(p["lat"], p["lon"]) for p in drawn["points"]]

    read = analyse(points, source=shelf, with_elevation=False, log=quiet)

    for key in ("km", "shade_pct", "exposure_pct", "road_metres", "off_network_metres"):
        assert read["stats"][key] == pytest.approx(drawn["stats"][key], rel=0.001)

    assert read["surfaces"] == drawn["surfaces"]
    assert read["covers"] == drawn["covers"]


def test_an_imported_trace_keeps_its_name_and_its_reperes(shelf):
    marks = [{"name": "Depart", "lat": 49.0, "lon": 7.5}]
    read = analyse([(49.0, 7.5), (49.0, 7.51)], name="Balade du dimanche",
                   waypoints=marks, source=shelf, with_elevation=False, log=quiet)

    assert read["name"] == "Balade du dimanche"
    assert read["waypoints"] == marks
    assert "Balade du dimanche" in read["gpx"]


def test_a_trace_of_one_point_is_refused(shelf):
    with pytest.raises(ValueError):
        analyse([(49.0, 7.5)], source=shelf, with_elevation=False, log=quiet)


def test_every_figure_the_interface_reads_is_present(shelf):
    result = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)

    expected = {"km", "shade_pct", "sun_metres", "road_metres", "off_network_metres",
                "up", "down", "hours", "pace_factor", "min_ele", "max_ele", "nodes",
                "edges", "clearings"}
    assert expected <= set(result["stats"])


def test_the_whole_payload_and_not_only_its_figures(shelf):
    """One of them quietly going missing is how a panel goes blank"""
    drawn = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)

    for key in ("bbox", "canopy", "highways", "landmarks", "seg_surface", "shade",
                "points", "waypoints", "surfaces", "covers", "gpx", "name"):
        assert key in drawn, key

    assert set(drawn["bbox"]) == {"minlat", "minlon", "maxlat", "maxlon"}
    assert len(drawn["shade"]) == len(drawn["seg_surface"])
    assert len(drawn["shade"]) == len(drawn["points"]) - 1

    read = analyse([(p["lat"], p["lon"]) for p in drawn["points"]],
                   source=shelf, with_elevation=False, log=quiet)
    assert set(read) == set(drawn)


def test_a_run_without_the_ground_says_so(shelf):
    """A D+ of zero on a real walk is a lie an interface would print without blinking"""
    result = plan([WEST, EAST], source=shelf, with_elevation=False, log=quiet)
    assert result["stats"]["has_elevation"] is False

    measured = plan([WEST, EAST], source=shelf, with_elevation=True, log=quiet)
    assert measured["stats"]["has_elevation"] is True
