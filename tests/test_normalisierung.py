"""Zuordnungstabellen (P5) und Zahlen/Datum (P6)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters.normalisierung import (
    normiere_schwierigkeit,
    normiere_zustand,
    parse_datum,
    parse_ja_nein,
    parse_zahl,
)
from loipen.models import Schwierigkeit, Status

BERLIN = ZoneInfo("Europe/Berlin")


@pytest.mark.req("P5", ak=1)
@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("Gut", Status.OFFEN),
        ("Mittel", Status.EINGESCHRAENKT),
        ("Sehr gut", Status.OFFEN),
        ("Geöffnet", Status.OFFEN),
        ("Loipenzustand: befahrbar", Status.OFFEN),
        ("bedingt befahrbar", Status.EINGESCHRAENKT),
        ("nicht befahrbar", Status.GESCHLOSSEN),
        ("  Geschlossen ", Status.GESCHLOSSEN),
    ],
)
def test_p5_zustand_wird_normiert_nicht_unbekannt(text, erwartet):
    status, bekannt = normiere_zustand(text)
    assert status == erwartet and bekannt


@pytest.mark.req("P5", ak=2)
def test_p5_unbekannter_text_wird_gemeldet():
    status, bekannt = normiere_zustand("Loipenzustand: Powder deluxe")
    assert status == Status.UNBEKANNT and not bekannt
    assert normiere_schwierigkeit("Teufelsstrecke") == (Schwierigkeit.UNBEKANNT, False)


@pytest.mark.req("P5")
@pytest.mark.parametrize(
    "text,erwartet",
    [("blau", "leicht"), ("rot", "mittel"), ("schwarz", "schwer"), ("leicht", "leicht"), ("schwer", "schwer")],
)
def test_p5_schwierigkeit_farben_und_worte(text, erwartet):
    assert normiere_schwierigkeit(text) == (Schwierigkeit(erwartet), True)


@pytest.mark.req("P5")
def test_p5_k_a_ist_bekannt_aber_ohne_aussage():
    assert normiere_schwierigkeit("k.A.") == (Schwierigkeit.UNBEKANNT, True)


@pytest.mark.req("P6", ak=1)
@pytest.mark.parametrize(
    "text,erwartet",
    [("9,0km", 9.0), ("12,7km", 12.7), ("8 km", 8.0), ("1.234,5 km", 1234.5), ("0,9 km", 0.9), ("k.A.", None), ("", None)],
)
def test_p6_zahlen(text, erwartet):
    assert parse_zahl(text) == erwartet


@pytest.mark.req("P6", ak=2)
def test_p6_datum_sommerzeit():
    winter = parse_datum("Daten zuletzt aktualisiert am 02.01.26 um 08:53 Uhr")
    assert winter == datetime(2026, 1, 2, 8, 53, tzinfo=BERLIN)
    assert winter.utcoffset().total_seconds() == 3600
    sommer = parse_datum("Daten zuletzt aktualisiert am 27.05.26 um 17:13 Uhr")
    assert sommer == datetime(2026, 5, 27, 17, 13, tzinfo=BERLIN)
    assert sommer.utcoffset().total_seconds() == 7200


@pytest.mark.req("P6")
def test_p6_datum_vierstelliges_jahr_und_ohne_uhrzeit_und_unsinn():
    assert parse_datum("am 3.2.2027") == datetime(2027, 2, 3, 0, 0, tzinfo=BERLIN)
    assert parse_datum("31.02.26 um 10:00 Uhr") is None
    assert parse_datum("gestern") is None
    assert parse_datum(None) is None


@pytest.mark.req("P6")
def test_p6_ja_nein():
    assert parse_ja_nein("Ja") is True and parse_ja_nein("Nein") is False and parse_ja_nein("?") is None
