#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walking time from the shape of the ground, and the personal factor that corrects it"""

import bisect
import math

# Tobler's hiknig function, fitted by Waldo Tobler on Eduard Imhof's field measurements
#   V = 6 * exp(-3.5 * |S + 0.05|)   in km/h, S being the gradient dh/dx
# Reference : Tobler W. (1993), Three Presentations on Geographical Analysis and
# Modelling, NCGIA Technical Report 93-1. A technical report, it carries no doi
TOBLER_BASE = 6.0
TOBLER_DECAY = 3.5
TOBLER_OPTIMUM = 0.05

# raw osm segments go down to well under a metre, where a metre of dem error reads as
# a cliff and Tobler hands back a speed near zero. This is the terrain model's maille
PACE_STEP = 25.0

# past this we have left the ground the curve was fitted on, scrambling is not walking
MAX_GRADIENT = 1.2


def speed(gradient):
    clamped = max(-MAX_GRADIENT, min(MAX_GRADIENT, gradient))
    return TOBLER_BASE * math.exp(-TOBLER_DECAY * abs(clamped + TOBLER_OPTIMUM))


def _height_at(distances, heights, target):
    index = bisect.bisect_right(distances, target) - 1
    index = min(max(index, 0), len(heights) - 2)   

    span = distances[index + 1] - distances[index]
    if (span <= 0.0):
        return heights[index]

    ratio = (target - distances[index]) / span
    return heights[index] + (heights[index + 1] - heights[index]) * ratio


def duration(distances, heights, factor=1.0, step=PACE_STEP):
    """Hours of walking. distances is cumulative metres, heights runs alongside it.

    factor is the personal correction, above one for a walker slower than Tobler, who
    measured people moving and not people eating lunch"""
    if (len(distances) < 2 or len(distances) != len(heights)):
        return 0.0

    total = distances[-1]
    if (total <= 0.0):
        return 0.0

    hours = 0.0
    previous_mark = 0.0
    previous_height = heights[0]

    marks = [i * step for i in range(1, int(total // step) + 1)]
    if (not marks or marks[-1] < total):
        marks.append(total)

    for mark in marks:
        run = mark - previous_mark
        if (run <= 0.0):
            continue

        height = _height_at(distances, heights, mark)
        hours += (run / 1000.0) / speed((height - previous_height) / run)
        previous_mark, previous_height = mark, height

    return hours * factor


def calibrate(outings, floor=3):
    """Personal factor from walks actually done, None while there are too few.

    Each outing carries what was predicted and what it really took. The median rather
    than the mean, one walk cut short by a storm should not reshape every estimate"""
    ratios = []
    for outing in outings:
        predicted = outing.get("predicted_hours")
        real = outing.get("hours")
        if (predicted and real and predicted > 0.0 and real > 0.0):
            ratios.append(real / predicted)

    if (len(ratios) < floor):
        return None

    ratios.sort()
    middle = len(ratios) // 2
    if (len(ratios) % 2):
        return ratios[middle]
    return (ratios[middle - 1] + ratios[middle]) / 2.0
