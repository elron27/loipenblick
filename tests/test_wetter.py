"""Wetter und Schnee: D11, D13, U15. Die Fixtures sind nach dem dokumentierten DWD- und
Bright-Sky-Format gebaut (das Netz ist in der Cloud gesperrt); echte Antworten ersetzen sie spaeter."""

import io
import json
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen.konfig import lade_und_abgleichen
from loipen.models import Gebiet, Wetter
from loipen.wetter import (
    aktualisiere_wetter, gebiet_position, neuschnee_summen, parse_brightsky, parse_dwd_tageswerte,
    schnee_uebersicht,
)
from tests.wetterformat import KOPF, brightsky, dwd_zip  # noqa: F401  (KOPF nutzen Tests unten)

JETZT = datetime(2026, 12, 10, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))


GEOSPHERE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "geosphere" / "2026-11-12" / "klima-v2-1d.json"
# Zweiter Abruf am selben Tag: alle aktiven Tiroler Stationen (Stationswahl fuer ganz Tirol)
GEOSPHERE_TIROL = GEOSPHERE_FIXTURE.with_name("klima-v2-1d_tirol.json")


def geosphere_antwort() -> str:
    """Alle echten Antworten zu einer zusammengefasst, wie sie ein Abruf mit allen Stationen liefert.

    Weitere Abrufe fuer denselben Zeitraum: klima-v2-1d_tirol.json (ganz Tirol), klima-v2-1d_ausbau3.json und
    klima-v2-1d_gastein.json (Gastein, Ramsau, Kaernten; Schnappschuss-Runden 12 und 13 vom 13.11.2026).
    """
    erste = json.loads(GEOSPHERE_FIXTURE.read_text(encoding="utf-8"))
    bekannt = {f["properties"]["station"] for f in erste["features"]}
    for datei in sorted(GEOSPHERE_FIXTURE.parent.glob("klima-v2-1d_*.json")):
        if datei.name == "klima-v2-1d_metadata.json":
            continue
        weitere = json.loads(datei.read_text(encoding="utf-8"))
        assert erste["timestamps"] == weitere["timestamps"], datei.name
        neu = [f for f in weitere["features"] if f["properties"]["station"] not in bekannt]
        erste["features"] += neu
        bekannt |= {f["properties"]["station"] for f in neu}
    return json.dumps(erste)


class WetterFetcher:
    def __init__(self, zip_bytes=None, vorhersage=None, fehler_station=None, geosphere=None):
        self.zip_bytes, self.vorhersage, self.fehler_station = zip_bytes, vorhersage, fehler_station
        self.geosphere = geosphere
        self.urls: list[str] = []

    def get_bytes(self, url):
        self.urls.append(url)
        if self.fehler_station and self.fehler_station in url:
            raise RuntimeError("HTTP 404")
        return self.zip_bytes

    def get(self, url):
        self.urls.append(url)
        if "geosphere" in url:
            return self.geosphere if self.geosphere is not None else geosphere_antwort()
        return self.vorhersage


def messzeilen(tage=10, sh=None):
    start = date(2026, 12, 10) - timedelta(days=tage)
    return [(start + timedelta(days=i), 1.0, (sh if sh is not None else 20 + i), 2.0) for i in range(tage)]


@pytest.mark.req("D11", ak=1)
def test_d11_neuschnee_24_48_72():
    m = parse_dwd_tageswerte(dwd_zip([
        (date(2026, 12, 7), 0, 10, 0.0), (date(2026, 12, 8), 4, 14, 4.0),
        (date(2026, 12, 9), 6, 26, 12.0), (date(2026, 12, 10), 2, 30, 5.0),
    ]))
    assert neuschnee_summen(m) == {24: 5.0, 48: 17.0, 72: 21.0}
    assert m[-1].schneehoehe_cm == 30 and m[-1].niederschlag_mm == 2


@pytest.mark.req("D11", ak=2)
def test_d11_fehlender_wert_ist_unbekannt_nicht_null():
    m = parse_dwd_tageswerte(dwd_zip([
        (date(2026, 12, 8), 1, 10, 3.0), (date(2026, 12, 9), 1, None, None), (date(2026, 12, 10), 1, 12, 2.0),
    ]))
    assert m[1].schneehoehe_cm is None and m[1].neuschnee_cm is None
    assert neuschnee_summen(m) == {24: 2.0, 48: None, 72: None}  # Luecke -> nicht als 0 gerechnet
    assert neuschnee_summen([]) == {24: None, 48: None, 72: None}


@pytest.mark.req("D11", ak=1)
def test_d11_schnee_uebersicht_mit_zeitpunkt_und_quelle(session):
    lade_und_abgleichen(session)
    fetcher = WetterFetcher(dwd_zip([
        (date(2026, 12, 8), 4, 14, 4.0), (date(2026, 12, 9), 6, 26, 12.0), (date(2026, 12, 10), 2, 30, 5.0)]),
        vorhersage=json.dumps({"weather": []}))
    aktualisiere_wetter(session, fetcher, JETZT)
    g = session.scalar(select(Gebiet).where(Gebiet.slug == "sachrang"))
    u = schnee_uebersicht(session, g)
    assert (u["schneehoehe_cm"], u["neuschnee_24h_cm"], u["neuschnee_48h_cm"], u["neuschnee_72h_cm"]) == (30, 5.0, 17.0, 21.0)
    assert u["messtag"] == date(2026, 12, 10)
    assert u["station_id"] == "00205" and u["station_name"] == "Aschau-Stein"
    assert u["quelle"] == "DWD Klimadaten Tageswerte"


@pytest.mark.req("D13", ak=2)
def test_d13_jeder_wert_hat_quelle_und_station(session):
    lade_und_abgleichen(session)
    aktualisiere_wetter(session, WetterFetcher(dwd_zip(messzeilen()), json.dumps({"weather": []})), JETZT)
    zeilen = session.scalars(select(Wetter).where(Wetter.art == "messung")).all()
    assert zeilen and all(z.quelle and z.station_id for z in zeilen)


@pytest.mark.req("D13", ak=1)
def test_d13_ein_datensatz_pro_tag_ohne_doppelte(session):
    lade_und_abgleichen(session)
    f = WetterFetcher(dwd_zip(messzeilen()), json.dumps({"weather": []}))
    aktualisiere_wetter(session, f, JETZT)
    n = session.query(Wetter).count()
    aktualisiere_wetter(session, f, JETZT)  # zweiter Lauf: aktualisiert, legt nichts doppelt an
    assert session.query(Wetter).count() == n
    g = session.scalar(select(Gebiet).where(Gebiet.slug == "sachrang"))
    tage = [z.datum for z in session.scalars(select(Wetter).where(Wetter.gebiet_id == g.id, Wetter.art == "messung")).all()]
    assert len(tage) == len(set(tage)) == 10


@pytest.mark.req("D13", ak=3)
def test_d13_fruehere_winter_per_parameter_nachladen(session):
    lade_und_abgleichen(session)
    zeilen = [(date(2025, 12, 1) + timedelta(days=i), 0.0, 5, 0.0) for i in range(400)]
    aktualisiere_wetter(session, WetterFetcher(dwd_zip(zeilen), json.dumps({"weather": []})), JETZT, tage=400)
    g = session.scalar(select(Gebiet).where(Gebiet.slug == "sachrang"))
    assert session.query(Wetter).filter_by(gebiet_id=g.id, art="messung").count() >= 365


@pytest.mark.req("U15", ak=1)
def test_u15_vorhersage_mindestens_drei_tage():
    tage = {date(2026, 12, 10) + timedelta(days=i): [(-4.0 + h * .3, 0.2 if h in (3, 4) else 0.0, "snow" if h in (3, 4) else "dry")
                                                     for h in range(24)] for i in range(4)}
    v = parse_brightsky(brightsky(tage))
    assert len(v) == 4
    assert v[0].datum == date(2026, 12, 10)
    assert v[0].temp_min_c == -4.0 and v[0].temp_max_c == pytest.approx(2.9)
    assert v[0].niederschlag_mm == 0.4 and v[0].schneefall is True


@pytest.mark.req("U15", ak=2)
def test_u15_quelle_genannt_und_kostenlos(session):
    lade_und_abgleichen(session)
    tage = {date(2026, 12, 10): [(-1.0, 0.0, "dry")] * 24}
    aktualisiere_wetter(session, WetterFetcher(dwd_zip(messzeilen()), brightsky(tage)), JETZT)
    z = session.scalars(select(Wetter).where(Wetter.art == "vorhersage")).first()
    assert z.quelle == "Bright Sky (DWD MOSMIX)"


@pytest.mark.req("D11")
def test_ausfall_einer_station_stoppt_die_anderen_nicht(session):
    lade_und_abgleichen(session)
    f = WetterFetcher(dwd_zip(messzeilen()), json.dumps({"weather": []}), fehler_station="04319")
    lauf = aktualisiere_wetter(session, f, JETZT)
    assert any("04319" in w for w in lauf.warnungen)
    assert lauf.messungen > 0
    ruh = session.scalar(select(Gebiet).where(Gebiet.slug == "ruhpolding"))
    assert session.query(Wetter).filter_by(gebiet_id=ruh.id, art="messung").count() == 0


@pytest.mark.req("D11")
def test_station_wird_nur_einmal_abgerufen(session):
    lade_und_abgleichen(session)
    f = WetterFetcher(dwd_zip(messzeilen()), json.dumps({"weather": []}))
    aktualisiere_wetter(session, f, JETZT)
    dwd = [u for u in f.urls if "opendata.dwd.de" in u]
    assert len(dwd) == len(set(dwd))  # Reit im Winkl, Schleching, Unterwoessen teilen 20189


@pytest.mark.req("U15")
def test_gebiet_position_aus_parkplaetzen_oder_loipen(session):
    lade_und_abgleichen(session)
    g = session.scalar(select(Gebiet).where(Gebiet.slug == "bayrischzell"))
    lat, lon = gebiet_position(g)
    assert 47.6 < lat < 47.7 and 11.9 < lon < 12.1
    leer = session.scalar(select(Gebiet).where(Gebiet.slug == "chieming"))
    assert gebiet_position(leer) is None


def _tag(tag, bedingung="dry", wolken=10, nied=0.0, sonne=30, stunden=24):
    return [{"timestamp": datetime(tag.year, tag.month, tag.day, h, tzinfo=ZoneInfo("Europe/Berlin")).isoformat(),
             "temperature": 2.0, "precipitation": nied / stunden, "condition": bedingung, "icon": bedingung,
             "cloud_cover": wolken, "sunshine": sonne if 8 <= h <= 15 else 0} for h in range(stunden)]


@pytest.mark.req("U15", ak=1)
def test_u15_tagessymbole_aus_stundenwerten():
    t = date(2026, 12, 10)
    faelle = {
        "sonne": _tag(t, wolken=10), "wolkig": _tag(t, wolken=55, sonne=10), "bedeckt": _tag(t, wolken=95, sonne=0),
        "regen": _tag(t, "rain", 90, 4.0, 0), "schnee": _tag(t, "snow", 95, 3.0, 0),
        "schneeregen": _tag(t, "sleet", 95, 2.0, 0), "gewitter": _tag(t, "thunderstorm", 95, 5.0, 0),
    }
    for erwartet, stunden in faelle.items():
        v = parse_brightsky(json.dumps({"weather": stunden}))[0]
        assert v.symbol == erwartet, (erwartet, v.symbol)
    assert parse_brightsky(json.dumps({"weather": faelle["sonne"]}))[0].sonne_h == 4.0  # 8 h mal 30 min
    assert parse_brightsky(json.dumps({"weather": [{"timestamp": "2026-12-10T12:00:00+01:00"}]}))[0].symbol is None


@pytest.mark.req("U18", ak=1)
def test_u18_vorhersage_wird_fuer_mindestens_sieben_tage_angefragt(session):
    """Am Montag reicht die Anfrage bis einschliesslich Sonntag der Woche."""
    lade_und_abgleichen(session)
    montag = datetime(2026, 12, 7, 6, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    f = WetterFetcher(dwd_zip(messzeilen()), json.dumps({"weather": []}))
    aktualisiere_wetter(session, f, montag)
    anfragen = [u for u in f.urls if "brightsky" in u]
    assert anfragen
    for u in anfragen:
        bis = date.fromisoformat(u.split("last_date=")[1].split("&")[0])
        assert bis >= date(2026, 12, 13), u  # Sonntag
