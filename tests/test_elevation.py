#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Climb figures : the threshold is what stops dem noise from inventing a mountain"""

import random

import pytest

from core.elevation import CLIMB_THRESHOLD, climb, smooth


def test_a_flat_walk_climbs_nothing():
    up, down = climb([200.0] * 40)
    assert up == 0.0
    assert down == 0.0


def test_a_real_ascent_is_counted():
    up, down = climb([100.0, 150.0, 200.0])
    assert up == pytest.approx(100.0)
    assert down == 0.0


def test_a_descent_is_counted_positive():
    up, down = climb([200.0, 150.0, 100.0])
    assert up == 0.0
    assert down == pytest.approx(100.0)


def test_wobble_under_the_threshold_never_banks():
    small = CLIMB_THRESHOLD / 4.0
    wobble = [300.0 + (small if i % 2 else -small) for i in range(500)]

    up, down = climb(wobble)
    assert up == 0.0
    assert down == 0.0


def test_smoothing_is_what_keeps_flat_ground_flat():
    """Fed raw samples, a flat walk under eu-dem grade noise reports thousands of
    metres of climb nobody walked. The noise here is drawn per point, harsher than
    reality where dem error is correlated over neighbouring cells"""
    noise = random.Random(42)
    flat = [300.0 + noise.gauss(0, 7.0) for _ in range(600)]

    raw_up, _ = climb(flat)
    smoothed_up, _ = climb(smooth(flat))

    assert raw_up > 1000.0   
    assert smoothed_up < raw_up / 3.0


def test_a_rise_just_over_the_threshold_is_kept():
    up, _ = climb([100.0, 100.0 + CLIMB_THRESHOLD + 0.5])
    assert up > 0.0


def test_the_threshold_does_not_eat_a_long_steady_climb():
    # small steps that genuinely go somewhere must still add up to the summit
    steady = [100.0 + i * 0.5 for i in range(400)]
    up, down = climb(steady)

    assert up == pytest.approx(steady[-1] - steady[0], rel=0.05)
    assert down == 0.0


def test_smoothing_keeps_the_lenght_and_the_ends():
    raw = [100.0, 120.0, 90.0, 130.0, 110.0]
    out = smooth(raw)

    assert len(out) == len(raw)
    assert min(raw) <= min(out) and max(out) <= max(raw) 


def test_smoothing_flattens_a_spike():
    spike = [100.0] * 6 + [200.0] + [100.0] * 6
    out = smooth(spike)
    assert max(out) < 200.0


def test_the_smoothing_reach_is_a_distance_not_a_point_count():
    # the old window counted points, its physical reach breathed with the node spacing
    coarse = [100.0 + (5.0 if i % 2 else 0.0) for i in range(40)]
    fine = [100.0 + (5.0 if (i // 2) % 2 else 0.0) for i in range(80)]

    spread = max(smooth(coarse, step=20.0)) - min(smooth(coarse, step=20.0))
    same = max(smooth(fine, step=10.0)) - min(smooth(fine, step=10.0))

    assert spread == pytest.approx(same, abs=0.35)


def test_smoothing_leaves_a_flat_profile_alone():
    flat = [42.0] * 10
    assert smooth(flat) == pytest.approx(flat)


def test_a_closed_loop_climbs_exactly_what_it_drops():
    """Come back where you started and the ascent has to equal the descent.

    Anchoring on the last sample instead of the turning point broke this identity"""
    noise = random.Random(3)
    out = [200.0]
    for _ in range(300):
        out.append(out[-1] + noise.gauss(0, 4.0))

    loop = out + out[::-1][1:]
    up, down = climb(loop)

    assert up == pytest.approx(down, abs=0.01)


def test_a_there_and_back_walk_is_symmetric(): 
    there = [100.0, 180.0, 140.0, 260.0]
    up, down = climb(there + there[::-1][1:])
    assert up == pytest.approx(down, abs=0.01)


def test_the_top_of_each_rise_is_not_shaved_off():
    up, down = climb([100.0, 130.0, 128.0, 160.0])

    assert up == pytest.approx(62.0, abs=0.01)
    assert down == pytest.approx(2.0, abs=0.01)


def test_ascent_minus_descent_is_the_net_change():
    noise = random.Random(19)
    walk = [150.0]
    for _ in range(400):
        walk.append(walk[-1] + noise.gauss(0, 3.0))

    up, down = climb(walk)
    net = walk[-1] - walk[0]

    # only the wobble left hangng under the floor may go missing, nevr a whole leg
    assert up - down == pytest.approx(net, abs=2 * CLIMB_THRESHOLD)
