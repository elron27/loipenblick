"""Wetter und Schnee fuer Oesterreich: D17. Echte Antworten von GeoSphere Austria und Bright Sky
(Schnappschuss 12.11.2026, tests/fixtures/geosphere/ und tests/fixtures/brightsky/)."""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml
from loipen.models import Gebiet, Wetter
from loipen.wetter import QUELLE_GEOSPHERE, aktualisiere_wetter, parse_brightsky, parse_geosphere_klima, schnee_uebersicht
from tests.test_wetter import GEOSPHERE_FIXTURE, WetterFetcher, geosphere_antwort

FIX = Path(__file__).resolve().parent / "fixtures"
JETZT = datetime(2026, 11, 12, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
GEBIETE = lade_yaml(CONFIG_DIR / "gebiete.yaml")
AT_REGIONEN = {r["slug"] for r in GEBIETE["regionen"] if r.get("land") == "AT"}


@pytest.mark.req("D17", ak=1)
def test_d17_jedes_oesterreichische_gebiet_hat_eine_geosphere_station():
    stationen = {str(f["properties"]["station"]) for f in json.loads(geosphere_antwort())["features"]
                 if any(x is not None for x in f["properties"]["parameters"]["sh"]["data"])}
    at = [g for g in GEBIETE["gebiete"] if g["region"] in AT_REGIONEN]
    assert len(at) >= 19
    for g in at:
        st = g.get("wetterstation") or {}
        assert st.get("dienst") == "geosphere", g["slug"]
        # Station liefert im Schnappschuss eine Schneehoehe (Pegel sh)
        assert st["id"] in stationen, g["slug"]


@pytest.mark.req("D17", ak=1)
def test_d17_geosphere_klima_echte_antwort():
    m = parse_geosphere_klima(GEOSPHERE_FIXTURE.read_text(encoding="utf-8"))
    kufstein = m["9016"]
    assert len(kufstein) == 14 and kufstein[0].datum == date(2026, 10, 29)
    assert kufstein[-1].datum == date(2026, 11, 11)
    # -1 heisst bei GeoSphere "kein Niederschlag" -> 0, nicht -1
    assert kufstein[0].niederschlag_mm == 0.0 and kufstein[-1].niederschlag_mm == 1.0
    assert all(x.schneehoehe_cm == 0.0 for x in kufstein)  # Anfang November: kein Schnee
    assert all(x.neuschnee_cm == 0.0 for x in kufstein)
    # Soell hat keine Handmessung (None): Neuschnee aus dem Zuwachs der Pegelmessung
    assert m["9019"][1].neuschnee_cm == 0.0


def test_d17_neuschnee_aus_zuwachs_und_fehlende_werte():
    roh = {"timestamps": ["2026-12-01T00:00+00:00", "2026-12-02T00:00+00:00", "2026-12-03T00:00+00:00"],
           "features": [{"properties": {"station": 1, "parameters": {
               "rr": {"data": [-1, 12.0, None]}, "sh": {"data": [10, 22, None]},
               "sh_manu": {"data": [None, None, 18]}, "shneu_manu": {"data": [None, None, None]}}}}]}
    m = parse_geosphere_klima(json.dumps(roh))["1"]
    assert [x.schneehoehe_cm for x in m] == [10, 22, 18]
    assert [x.neuschnee_cm for x in m] == [None, 12, 0.0]
    assert [x.niederschlag_mm for x in m] == [0.0, 12.0, None]


@pytest.mark.req("D17", ak=[1, 2])
def test_d17_messwerte_landen_beim_gebiet_mit_namensnennung(session):
    lade_und_abgleichen(session)
    f = WetterFetcher(zip_bytes=None, vorhersage=(FIX / "brightsky" / "2026-11-12" / "kufstein.json").read_text())
    lauf = aktualisiere_wetter(session, f, JETZT)
    geo = [u for u in f.urls if "geosphere" in u]
    assert len(geo) == 1  # ein Abruf fuer alle Stationen
    ids = set(geo[0].split("station_ids=")[1].split("&")[0].split(","))
    at = {g["wetterstation"]["id"] for g in GEBIETE["gebiete"] if g["region"] in AT_REGIONEN}
    assert ids == at and len(ids) >= 25
    kufstein = session.scalar(select(Gebiet).where(Gebiet.slug == "kufstein"))
    zeilen = session.scalars(select(Wetter).where(Wetter.gebiet_id == kufstein.id, Wetter.art == "messung")).all()
    assert len(zeilen) == 14 and {z.quelle for z in zeilen} == {QUELLE_GEOSPHERE}
    s = schnee_uebersicht(session, kufstein)
    assert s["schneehoehe_cm"] == 0.0 and s["station_id"] == "9016" and s["station_name"] == "Kufstein"
    assert s["quelle"] == "GeoSphere Austria (CC BY 4.0)"
    assert not [w for w in lauf.warnungen if "GeoSphere" in w]


@pytest.mark.req("D17", ak=2)
def test_d17_geosphere_auf_der_seite_genannt():
    html = (Path(__file__).resolve().parents[1] / "loipen" / "generator" / "static" / "index.html").read_text("utf-8")
    assert "GeoSphere Austria" in html


def test_vorhersage_fuer_oesterreich_aus_bright_sky_echte_antwort():
    """Bright Sky liefert auch fuer Kufstein und Faistenau 8 Tage (MOSMIX-Stationen an der Grenze)."""
    for ort in ("kufstein", "faistenau"):
        v = parse_brightsky((FIX / "brightsky" / "2026-11-12" / f"{ort}.json").read_text(encoding="utf-8"))
        assert len(v) >= 8, ort
        assert all(t.temp_min_c is not None and t.temp_max_c is not None for t in v[:8])
        assert all(t.symbol for t in v[:8])
