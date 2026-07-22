#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gpx output, the one artefact that leaves the machine and lands on a gps"""

import xml.etree.ElementTree as ET

import pytest

from core import gpx

NS = {"g": "http://www.topografix.com/GPX/1/1"}


TRACK = [(49.0, 7.5), (49.001, 7.501), (49.002, 7.502)]
HEIGHTS = [220.0, 235.5, 251.0]


def parse(document):
    return ET.fromstring(document)


def test_the_document_is_well_formed():
    root = parse(gpx.write("Boucle", TRACK, HEIGHTS))
    assert root.tag.endswith("gpx")
    assert root.get("version") == "1.1"


def test_every_point_lands_in_the_track():
    root = parse(gpx.write("Boucle", TRACK, HEIGHTS))
    points = root.findall(".//g:trkpt", NS)

    assert len(points) == len(TRACK)
    assert float(points[0].get("lat")) == pytest.approx(49.0)
    assert float(points[-1].get("lon")) == pytest.approx(7.502)


def test_heights_ride_along():
    root = parse(gpx.write("Boucle", TRACK, HEIGHTS))
    elevations = [float(e.text) for e in root.findall(".//g:ele", NS)] 
    assert elevations == pytest.approx(HEIGHTS, abs=0.05)


def test_named_waypoints_are_written():
    marks = [{"name": "Depart", "lat": 49.0, "lon": 7.5}]
    root = parse(gpx.write("Boucle", TRACK, HEIGHTS, marks))

    written = root.findall(".//g:wpt", NS)
    assert len(written) == 1
    assert written[0].find("g:name", NS).text == "Depart"


def test_an_ampersand_in_a_name_cannot_break_the_file():
    """A place called Fer & Feu must not produce a document nobody can open"""
    marks = [{"name": "Fer & Feu <test>", "lat": 49.0, "lon": 7.5}]
    root = parse(gpx.write("Rando & retour", TRACK, HEIGHTS, marks))

    assert root.findall(".//g:wpt", NS)[0].find("g:name", NS).text == "Fer & Feu <test>"


def test_a_mismatched_height_tableau_is_refused():
    """Silently zipping to the shorter of the two would truncate the tracé"""
    with pytest.raises(ValueError):
        gpx.write("Boucle", TRACK, HEIGHTS[:2])


def test_coordinates_keep_enough_decimals():
    """Seven decimals is about a centimetre, rounding harder would visibly wander"""
    document = gpx.write("Boucle", [(49.0123456, 7.5123456)], [100.0])
    assert "49.0123456" in document
    assert "7.5123456" in document  
