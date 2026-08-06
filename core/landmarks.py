#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What counts as a landmark, and the record both sources hand back for one"""

# the three water kinds stay apart : walking thirty minutes to a lake you cannot drink
# is the mistake this tells apart
LANDMARK_TAGS = (
    ("historic", "castle", "castle"),
    ("amenity", "drinking_water", "drinking_water"),
    ("natural", "spring", "spring"),
    ("man_made", "water_well", "well"),
    ("natural", "water", "water"),
    ("natural", "rock", "rock"),
    ("amenity", "parking", "parking"),
)

# what you may actually fill a bottle from, whatever osm says about how sure it is
WATER_KINDS = frozenset(("drinking_water", "spring", "well"))


def classify(tags):
    """The kind these osm tags describe, None when none of ours match"""
    for key, value, kind in LANDMARK_TAGS:
        if (tags.get(key) == value):
            return kind

    return None


def describe(tags, lat, lon):
    """One landmark record, None when the tags are not one of ours"""
    kind = classify(tags)
    if (kind is None or lat is None or lon is None):
        return None

    return {
        "name": tags.get("name") or "",
        "kind": kind,
        "lat": lat,
        "lon": lon,
        "fee": tags.get("fee"),
        # None means nobody said, and on a spring that is a reason to carry a full one
        "drinkable": _drinkable(tags, kind),
    }


def _drinkable(tags, kind):
    stated = tags.get("drinking_water")
    if (stated in ("yes", "treated")):
        return True
    if (stated in ("no", "untreated")):
        return False

    # a tap tagged as drinking water is one by definition, a spring never is
    if (kind == "drinking_water"):
        return True

    return None


def within(landmark, bbox):
    # bbox is (minlat, minlon, maxlat, maxlon)
    return (bbox[0] <= landmark["lat"] <= bbox[2]
            and bbox[1] <= landmark["lon"] <= bbox[3])
