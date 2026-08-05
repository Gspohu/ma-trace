#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Forest assembly, where a forgotten hole once turned a car park into deep woods"""

from shapely.geometry import box

from core.canopy import DEFAULT_TRANSMITTANCE, FULL_SUN, TRANSMITTANCE, Canopy


def wood(leaf_type=None, west=7.490, east=7.530):
    tags = {"landuse": "forest"}
    if (leaf_type is not None):
        tags["leaf_type"] = leaf_type

    ring = [(west, 49.002), (east, 49.002), (east, 49.006), (west, 49.006),
            (west, 49.002)]
    return {"type": "way", "id": 1, "tags": tags,
            "geometry": [{"lat": lat, "lon": lon} for lon, lat in ring]}


UNDER = ((49.004, 7.500), (49.004, 7.510))
OPEN = ((49.000, 7.500), (49.000, 7.510))


def test_a_segment_under_the_trees_is_covered(northern_wood):
    canopy = Canopy(northern_wood)   
    assert canopy.covers_segment((49.004, 7.500), (49.004, 7.510)) is True


def test_a_segment_in_the_open_is_not(northern_wood):
    canopy = Canopy(northern_wood)
    assert canopy.covers_segment((49.000, 7.500), (49.000, 7.510)) is False


def test_a_segment_leaving_the_wood_is_not_covered(northern_wood):
    """Partly sheltered is not sheltered, the walker still cooks on the exposed half"""
    canopy = Canopy(northern_wood) 
    assert canopy.covers_segment((49.000, 7.500), (49.004, 7.500)) is False


def test_the_clearing_is_punched_out(wood_with_clearing):
    """The bug that mattered : without the inner ring this returned covered"""
    canopy = Canopy(wood_with_clearing)

    assert canopy.clearing_count == 1
    assert canopy.covers_segment((49.010, 7.508), (49.010, 7.512)) is False


def test_the_wood_around_the_clearing_still_shelters(wood_with_clearing):
    canopy = Canopy(wood_with_clearing)
    assert canopy.covers_segment((48.995, 7.508), (48.995, 7.512)) is True


def test_a_line_bridging_the_clearing_is_caught(wood_with_clearing):
    """Two endpoints in the trees with a clairiere between them, and covers() weighs
    the whole line rather than its vertices"""
    canopy = Canopy(wood_with_clearing)
    assert canopy.covers_segment((49.010, 7.500), (49.010, 7.520)) is False


def test_no_forest_at_all_shelters_nothing():
    canopy = Canopy([])
    assert canopy.outer_count == 0
    assert canopy.covers_segment((49.0, 7.5), (49.0, 7.51)) is False


def test_a_degenrate_ring_is_dropped_quietly():
    """Osm carries broken geometry, one bad ring must never sink the whole run"""
    broken = [{"type": "way", "id": 1, "tags": {"landuse": "forest"},
               "geometry": [{"lat": 49.0, "lon": 7.5}, {"lat": 49.0, "lon": 7.51}]}]

    canopy = Canopy(broken)
    assert canopy.outer_count == 0


def test_needles_shelter_better_than_leaves():
    spruce = Canopy([wood("needleleaved")])
    beech = Canopy([wood("broadleaved")])

    assert spruce.transmittance_of_segment(*UNDER) < beech.transmittance_of_segment(*UNDER)
    assert spruce.transmittance_of_segment(*UNDER) == TRANSMITTANCE["needleleaved"]
    assert beech.transmittance_of_segment(*UNDER) == TRANSMITTANCE["broadleaved"]


def test_the_open_takes_the_whole_sun():
    canopy = Canopy([wood("needleleaved")])
    assert canopy.transmittance_of_segment(*OPEN) == FULL_SUN


def test_an_untagged_massif_falls_back_on_the_prudent_reading():
    canopy = Canopy([wood()])

    assert canopy.transmittance_of_segment(*UNDER) == DEFAULT_TRANSMITTANCE
    assert canopy.covers_segment(*UNDER) is True


def test_leafless_is_no_shelter_at_all():
    # bare wood must not be handed the transmittance of a healthy chenaie
    canopy = Canopy([wood("leafless")])

    assert canopy.transmittance_of_segment(*UNDER) == FULL_SUN
    assert canopy.covers_segment(*UNDER) is False
    assert canopy.outer_count == 0


def test_the_darkest_cover_wins_where_two_massifs_overlap():
    both = [wood("broadleaved"), dict(wood("needleleaved"), id=2)]
    canopy = Canopy(both)

    assert canopy.transmittance_of_segment(*UNDER) == TRANSMITTANCE["needleleaved"]


def test_the_kinds_are_counted_for_the_log():
    canopy = Canopy([wood("needleleaved"), dict(wood(), id=2)])
    assert canopy.kind_counts == {"needleleaved": 1, "inconnu": 1}


def test_rings_come_back_clipped_for_drawing(northern_wood):
    canopy = Canopy(northern_wood)
    rings = canopy.clipped_rings(box(7.495, 48.999, 7.525, 49.007))

    assert rings
    for ring in rings:
        assert len(ring["outer"]) >= 4
        for lat, lon in ring["outer"]:
            assert 48.9 < lat < 49.1
            assert 7.4 < lon < 7.6
