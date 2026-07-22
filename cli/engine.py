#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared marshalling for the two adapters that speak json, the bridge and the server"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import plan
from core.elevation import ElevationError
from core.overpass import OverpassError
from core.pipeline import DEFAULT_ROAD_PENALTY, DEFAULT_SUN_PENALTY
from core.router import NoRouteError

# what a bad request or an unreachable mirror looks like. A real bug is not in here
# Anything outside this list deserves to crash loudly. A real bug wearing a ploite
# error message is a bug nobody ever fixes
EXPECTED = (ElevationError, OverpassError, NoRouteError, ValueError, OSError)

MIN_WAYPOINTS = 2


def plan_from_request(request, log=print):
    """Turns the json a front sends into a call on core, and nothing more.

    Both adapters used to carry their own copy of this, which meant a default 
    changing in one and not the other"""
    waypoints = request.get("waypoints") or []
    if (len(waypoints) < MIN_WAYPOINTS):
        raise ValueError("il faut au moins deux points de passage")

    return plan(
        waypoints,
        sun_penalty=float(request.get("sunPenalty", DEFAULT_SUN_PENALTY)),
        road_penalty=float(request.get("roadPenalty", DEFAULT_ROAD_PENALTY)),
        close_loop=bool(request.get("closeLoop", True)),
        with_elevation=bool(request.get("withElevation", True)),
        log=log,
    )
