#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The elevation memo, and the promise that it never invents a height"""

import pytest 

from core import dem_cache, elevation


@pytest.fixture   
def cache(tmp_path):
    return dem_cache.Cache(str(tmp_path / "eleve.sqlite"))


def test_what_goes_in_comes_back(cache):
    cache.store([((49.0, 7.5), 240.0), ((49.001, 7.501), 255.5)])
    found = cache.lookup([(49.0, 7.5), (49.001, 7.501)])

    assert found[dem_cache.key((49.0, 7.5))] == pytest.approx(240.0)
    assert found[dem_cache.key((49.001, 7.501))] == pytest.approx(255.5)


def test_an_unknown_point_is_simply_absent(cache):
    cache.store([((49.0, 7.5), 240.0)])
    assert cache.lookup([(48.0, 6.0)]) == {}


def test_two_points_a_millimetre_apart_share_an_entry(cache):
    """Six decimals is a tenth of a metre, nothing the terrain model can tell apart"""
    cache.store([((49.0000001, 7.5000001), 240.0)])
    assert cache.lookup([(49.0, 7.5)])


def test_two_points_a_metre_apart_do_not(cache):
    cache.store([((49.0, 7.5), 240.0)])
    assert cache.lookup([(49.00001, 7.5)]) == {}


def test_storing_again_updates_rather_than_duplicates(cache):
    cache.store([((49.0, 7.5), 240.0)])
    cache.store([((49.0, 7.5), 999.0)])

    assert cache.count() == 1
    assert cache.lookup([(49.0, 7.5)])[dem_cache.key((49.0, 7.5))] == pytest.approx(999.0)


def test_it_survives_being_reopened(tmp_path):
    # the web front spawns a fres process per trace, an in memory memo would die
    path = str(tmp_path / "eleve.sqlite") 

    first = dem_cache.Cache(path)
    first.store([((49.0, 7.5), 240.0)])
    first.close()

    assert dem_cache.Cache(path).lookup([(49.0, 7.5)])


def test_a_big_batch_survives_the_query_chunking(cache):
    """Sqlite has a ceiling on bound variables, the lookup splits around it"""
    points = [(49.0 + i / 10000.0, 7.5) for i in range(950)]
    cache.store([(p, 200.0 + i) for i, p in enumerate(points)])

    found = cache.lookup(points)
    assert len(found) == 950


class Counter:
    # stands in for the reseau, and tells how much of it was actaully used
    def __init__(self):
        self.asked = []

    def __call__(self, points, log=print):
        self.asked.extend(points)
        log("   %d points demandes au reseau" % len(points))
        return [200.0 + i for i, _ in enumerate(points)]


def test_sample_only_asks_for_what_is_missing(cache, monkeypatch):
    counter = Counter()
    monkeypatch.setattr(elevation, "fetch", counter)

    points = [(49.0, 7.5), (49.001, 7.5), (49.002, 7.5)]
    first = elevation.sample(points, log=lambda m: None, cache=cache)

    assert len(counter.asked) == 3

    second = elevation.sample(points, log=lambda m: None, cache=cache)
    assert len(counter.asked) == 3, "le reseau a ete rappele pour des points connus"
    assert second == pytest.approx(first)


def test_only_the_new_stretch_of_a_moved_trace_is_fetched(cache, monkeypatch):
    # nudging one waypoint must not re-buy the untoched half of the walk
    counter = Counter()
    monkeypatch.setattr(elevation, "fetch", counter)

    shared = [(49.0, 7.5), (49.001, 7.5)]
    elevation.sample(shared, log=lambda m: None, cache=cache)
    counter.asked.clear()

    elevation.sample(shared + [(49.005, 7.5)], log=lambda m: None, cache=cache)
    assert len(counter.asked) == 1


def test_a_repeated_point_is_asked_for_once(cache, monkeypatch):
    counter = Counter()
    monkeypatch.setattr(elevation, "fetch", counter)

    doubled = [(49.0, 7.5), (49.001, 7.5), (49.0, 7.5)]
    heights = elevation.sample(doubled, log=lambda m: None, cache=cache)

    assert len(counter.asked) == 2
    assert heights[0] == pytest.approx(heights[2])


def test_a_broken_cache_never_stops_the_walk(cache, monkeypatch):
    # a cache is an accelerator, losing it costs seconds and not the trace
    counter = Counter()
    monkeypatch.setattr(elevation, "fetch", counter)
    cache.close()

    heights = elevation.sample([(49.0, 7.5)], log=lambda m: None, cache=cache)
    assert heights == pytest.approx([200.0])


def test_the_order_of_the_answer_follows_the_tracé(cache, monkeypatch):
    """A height landing against the wrong point would bend the profile silently"""
    monkeypatch.setattr(elevation, "fetch",
                        lambda points, log=print: [p[0] * 100.0 for p in points])

    points = [(49.003, 7.5), (49.001, 7.5), (49.002, 7.5)]
    heights = elevation.sample(points, log=lambda m: None, cache=cache)

    assert heights == pytest.approx([4900.3, 4900.1, 4900.2])
