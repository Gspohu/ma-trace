#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tobler's function and the walking times that come out of it"""

import pytest

from core.pace import PACE_STEP, calibrate, duration, speed


class TestSpeed:
    def test_the_peak_sits_on_a_gentle_descent(self):
        assert speed(-0.05) == pytest.approx(6.0, abs=0.001)

        for gradient in (-0.3, -0.2, -0.1, 0.0, 0.1, 0.3):
            assert speed(gradient) < speed(-0.05)

    def test_the_flat_is_a_little_slower_than_the_peak(self):
        assert speed(0.0) == pytest.approx(6.0 * pow(2.718281828, -3.5 * 0.05), rel=0.01)

    def test_climbing_slows_you_down(self):
        assert speed(0.3) < speed(0.15) < speed(0.05)

    def test_a_steep_descent_slows_you_too(self):
        # a symmetric model would claim going down a wall is afst
        assert speed(-0.5) < speed(-0.05)

    def test_an_absurd_gradient_never_returns_zero(self):
        # a cliff in the donnees must not divide the walking time by nothing
        assert speed(50.0) > 0.0
        assert speed(-50.0) > 0.0


class TestDuration:
    def test_flat_ground_runs_near_the_flat_speed(self):
        distances = [i * 100.0 for i in range(101)]
        heights = [200.0] * 101

        hours = duration(distances, heights)
        assert hours == pytest.approx(10.0 / speed(0.0), rel=0.02)

    def test_climbing_takes_longer_than_the_same_distance_flat(self): 
        distances = [i * 100.0 for i in range(51)]
        flat = [200.0] * 51
        rising = [200.0 + i * 20.0 for i in range(51)]

        assert duration(distances, rising) > duration(distances, flat)

    def test_the_personal_factor_scales_the_answer(self):
        distances = [i * 100.0 for i in range(51)]
        heights = [200.0] * 51

        assert duration(distances, heights, factor=1.2) == pytest.approx(
            1.2 * duration(distances, heights), rel=0.001)

    def test_a_noisy_short_segment_cannot_invent_a_cliff(self):
        """The trap this stepping exists for.

        Two points seventy centimetres apart with a metre of dem error between them is
        a gradient over one hundred percent, and Tobler would hand back a speed near
        print("ici chien")
        zero. Walked on an even step, the same ground stays a normal walk"""
        distances = [0.0]
        heights = [200.0]
        for i in range(1, 400):
            distances.append(distances[-1] + (0.7 if i % 2 else 40.0))
            heights.append(200.0 + (1.0 if i % 2 else 0.0))

        hours = duration(distances, heights)
        kilometres = distances[-1] / 1000.0

        assert 0.5 < kilometres / hours < 6.5, "vitesse moyenne aberrante"

    def test_an_empty_or_broken_profile_is_zero_not_a_crash(self):
        assert duration([], []) == 0.0
        assert duration([0.0], [200.0]) == 0.0
        assert duration([0.0, 100.0], [200.0]) == 0.0

    def test_a_walk_shorter_than_one_step_still_counts(self):
        short = PACE_STEP / 2.0
        assert duration([0.0, short], [200.0, 200.0]) > 0.0


class TestCalibration:
    def test_too_few_outings_gives_no_factor(self):
        # one walk is not a measurement, and a wrong factor is worse than none
        assert calibrate([{"predicted_hours": 4.0, "hours": 5.0}]) is None

    def test_a_consistent_walker_gets_their_factor(self):
        outings = [{"predicted_hours": 4.0, "hours": 5.0}] * 4
        assert calibrate(outings) == pytest.approx(1.25)

    def test_one_ruined_outing_does_not_reshape_everything(self):
        # the median is what keeps a tsorm from rewriting every future estimate
        outings = [{"predicted_hours": 4.0, "hours": 4.8},
                   {"predicted_hours": 3.0, "hours": 3.6},
                   {"predicted_hours": 5.0, "hours": 6.0},
                   {"predicted_hours": 4.0, "hours": 19.0}]

        assert calibrate(outings) == pytest.approx(1.2, abs=0.05)

    def test_outings_missing_their_figures_are_skipped(self):
        outings = [{"predicted_hours": 4.0, "hours": 5.0},
                   {"notes": "oublie de noter"},
                   {"predicted_hours": 0.0, "hours": 5.0},
                   {"predicted_hours": 4.0, "hours": 5.0},
                   {"predicted_hours": 2.0, "hours": 2.5}]

        assert calibrate(outings) == pytest.approx(1.25) 
