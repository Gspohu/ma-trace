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


def test_a_missing_height_writes_no_ele_at_all():
    # a walk drawn without altimetrie must not claim to run at sea level
    document = gpx.write("Boucle", TRACK, [None] * len(TRACK))

    assert "<ele>" not in document
    assert len(parse(document).findall(".//g:trkpt", NS)) == len(TRACK)


def test_a_mismatched_height_tableau_is_refused():
    """Silently zipping to the shorter of the two would truncate the tracé"""
    with pytest.raises(ValueError):
        gpx.write("Boucle", TRACK, HEIGHTS[:2])


def test_coordinates_keep_enough_decimals():
    """Seven decimals is about a centimetre, rounding harder would visibly wander"""
    document = gpx.write("Boucle", [(49.0123456, 7.5123456)], [100.0])
    assert "49.0123456" in document
    assert "7.5123456" in document


def test_what_we_write_is_what_we_read_back():
    marks = [{"name": "Falkenstein", "lat": 49.004, "lon": 7.565}]
    trace = gpx.read(gpx.write("Boucle", TRACK, HEIGHTS, marks))

    assert trace["name"] == "Boucle"
    assert trace["points"] == TRACK
    assert trace["heights"] == HEIGHTS
    assert trace["waypoints"][0]["name"] == "Falkenstein"


def test_a_file_without_a_namespace_is_read_all_the_same():
    """Plenty of devices declare none, and it changes nothing about where the
    coordinates sit. Reading by local tag name is what makes that a non-event"""
    bare = ('<gpx version="1.1"><trk><name>Sans espace</name><trkseg>'
            '<trkpt lat="49.0" lon="7.5"><ele>220</ele></trkpt>'
            '<trkpt lat="49.001" lon="7.501"/>'
            "</trkseg></trk></gpx>")
    trace = gpx.read(bare)

    assert trace["name"] == "Sans espace"
    assert trace["points"] == [(49.0, 7.5), (49.001, 7.501)]
    assert trace["heights"] == [220.0, None]


def test_the_gpx_1_0_namespace_is_read_too():
    old = ('<gpx xmlns="http://www.topografix.com/GPX/1/0" version="1.0">'
           '<trk><trkseg><trkpt lat="49.0" lon="7.5"/>'
           '<trkpt lat="49.001" lon="7.501"/></trkseg></trk></gpx>')
    assert len(gpx.read(old)["points"]) == 2


def test_a_route_is_read_like_a_track():
    # some devices hand back a rte where we would have writen a trk
    document = ('<gpx version="1.1"><rte><name>Itineraire</name>'
                '<rtept lat="49.0" lon="7.5"/><rtept lat="49.001" lon="7.501"/>'
                "</rte></gpx>")
    trace = gpx.read(document)

    assert trace["name"] == "Itineraire"
    assert len(trace["points"]) == 2


def test_a_name_inside_a_waypoint_is_not_the_name_of_the_trace():
    """Searching the tree for the first <name> would pick this one up"""
    document = ('<gpx version="1.1">'
                '<wpt lat="49.0" lon="7.5"><name>Parking</name></wpt>'
                '<trk><name>La vraie boucle</name><trkseg>'
                '<trkpt lat="49.0" lon="7.5"/><trkpt lat="49.001" lon="7.501"/>'
                "</trkseg></trk></gpx>")

    assert gpx.read(document)["name"] == "La vraie boucle"


def test_several_segments_join_into_one_trace():
    document = ('<gpx version="1.1"><trk><trkseg>'
                '<trkpt lat="49.0" lon="7.5"/><trkpt lat="49.001" lon="7.501"/>'
                "</trkseg><trkseg>"
                '<trkpt lat="49.002" lon="7.502"/>'
                "</trkseg></trk></gpx>")
    assert len(gpx.read(document)["points"]) == 3


def test_a_point_with_broken_coordinates_is_dropped():
    document = ('<gpx version="1.1"><trk><trkseg>'
                '<trkpt lat="49.0" lon="7.5"/>'
                '<trkpt lat="quatre-vingt" lon="7.501"/>'
                '<trkpt lat="200.0" lon="7.502"/>'
                '<trkpt lat="49.003" lon="7.503"/>'
                "</trkseg></trk></gpx>")
    assert len(gpx.read(document)["points"]) == 2


def test_a_dtd_is_turned_away_before_the_parser_sees_it():
    """An internal entity expands on the way in : 342 octets of nested ones come back
    as a megabyte, and the size cap upstream weighs the fichier and not what it grows
    into. Gpx is defined by a schema, a document carrying a dtd is an attack"""
    bomb = ('<?xml version="1.0"?><!DOCTYPE gpx ['
            '<!ENTITY a "aaaaaaaaaa">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            ']><gpx><trk><trkseg><trkpt lat="49" lon="7"><name>&b;</name></trkpt>'
            "</trkseg></trk></gpx>")

    with pytest.raises(gpx.GpxError):
        gpx.read(bomb)


def test_an_external_entity_is_turned_away_too():
    xxe = ('<?xml version="1.0"?>'
           '<!DOCTYPE gpx [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
           "<gpx>&x;</gpx>")

    with pytest.raises(gpx.GpxError):
        gpx.read(xxe)


def test_something_that_is_not_a_gpx_is_refused():
    for rubbish in ("<html><body>bonjour</body></html>", "pas du xml du tout",
                    '<gpx version="1.1"><trk><trkseg/></trk></gpx>'):
        with pytest.raises(gpx.GpxError):
            gpx.read(rubbish)  
