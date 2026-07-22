#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distances, boxes and the resampling the D+ leans on"""

import pytest

from core.geometry import at_distance, bbox_of, cumulative, haversine, path_length, resample


def test_a_known_distance():
    # Strasbourg to Colmar, about 64 km as the crow flies
    gap = haversine((48.5734, 7.7521), (48.0794, 7.3585))
    assert 60_000 < gap < 68_000


def test_the_same_point_is_zero():
    assert haversine((49.0, 7.5), (49.0, 7.5)) == pytest.approx(0.0)


def test_the_box_swallows_every_point():
    points = [(49.0, 7.5), (49.02, 7.56), (48.99, 7.48)]
    low_lat, low_lon, high_lat, high_lon = bbox_of(points)

    for lat, lon in points:
        assert low_lat < lat < high_lat
        assert low_lon < lon < high_lon


def test_an_empty_box_is_refused():
    with pytest.raises(ValueError):
        bbox_of([])


def test_the_pad_is_metres_not_degrees():
    """A degree of longitude is shorter than a degree of latitude at this latitude"""
    low_lat, low_lon, high_lat, high_lon = bbox_of([(49.0, 7.5)], pad_metres=1000.0)
    assert (high_lon - low_lon) > (high_lat - low_lat)


def test_resampling_lands_on_the_polyline():
    # a hairpin, the case where cutting the corner would leave the sentier
    line = [(49.000, 7.500), (49.000, 7.520), (49.002, 7.520)]
    walked = resample(line, 50.0)

    assert walked[0] == line[0]
    assert walked[-1] == line[-1]
    assert path_length(walked) == pytest.approx(path_length(line), rel=0.01)


def test_resampling_spaces_points_evenly():
    line = [(49.0, 7.5), (49.0, 7.52)]
    marks = cumulative(resample(line, 100.0))
    gaps = [b - a for a, b in zip(marks, marks[1:])]

    assert max(gaps[:-1]) == pytest.approx(100.0, abs=1.0)


def test_a_degenrate_line_survives_resampling():
    assert resample([(49.0, 7.5)], 20.0) == [(49.0, 7.5)]
    assert resample([(49.0, 7.5), (49.0, 7.5)], 20.0)


def test_reading_a_point_at_a_distance():
    line = [(49.0, 7.5), (49.0, 7.6)]
    marks = cumulative(line)
    middle = at_distance(line, marks, marks[-1] / 2.0)

    assert middle[1] == pytest.approx(7.55, abs=0.001)
