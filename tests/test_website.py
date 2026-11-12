"""Statische Website, Daten-Seite: B7, B15, D11, U5, U6, U8, U10, U14, U15, U18, U21, U22, U26."""

import json
import re
import struct
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from loipen import generator
from loipen.models import Loipe, Quelle
from tests.helpers import lade_alle_fixtures

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
STATIC = Path(generator.__file__).parent / "static"


@pytest.fixture
def site(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    generator.erzeuge(session, tmp_path, JETZT)
    return tmp_path


def lies(site: Path, rel: str):
    return json.loads((site / rel).read_text(encoding="utf-8"))


def alle_loipen(site: Path) -> list[dict]:
    return [l for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"] for l in g["loipen"]]


@pytest.mark.req("B7", ak=1)
def test_b7_seite_braucht_keinen_server(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<(script|link)[^>]+(src|href)=\"https?://", html)  # nichts von fremden Servern
    dateien = {p.suffix for p in site.rglob("*") if p.is_file()}
    assert dateien <= {".html", ".js", ".css", ".json", ".png", ".webmanifest", ".txt"}  # nur statische Dateien
    js = (site / "app.js").read_text(encoding="utf-8")
    assert "fetch(url)" in js and not re.search(r"fetch\(\s*[\"']https?://", js)  # Daten nur relativ


@pytest.mark.req("B7", ak=2)
def test_b7_daten_liegen_als_json_je_region(site):
    index = lies(site, "daten.json")
    assert {r["slug"] for r in index["regionen"]} == {"tegernseer-tal", "leitzachtal", "priental", "chiemgau"}
    for r in index["regionen"]:
        region = lies(site, r["datei"])
        assert region["region"]["slug"] == r["slug"] and region["gebiete"]
        assert isinstance(lies(site, r["strecken"]), dict)
    # Chiemgau liefert Streckenverlaeufe als [lat, lon]
    strecken = lies(site, "strecken/chiemgau.json")
    assert len(strecken) > 30
    lat, lon = next(iter(strecken.values()))[0]
    assert 47 < lat < 48 and 12 < lon < 13


@pytest.mark.req("B15", ak=1)
def test_b15_fusszeile_mit_ohne_gewaehr(site):
    assert "Alle Angaben ohne Gewähr" in (site / "index.html").read_text(encoding="utf-8")


@pytest.mark.req("B15", ak=2)
def test_b15_detailseite_nennt_quelle_und_stand(site):
    js = (site / "app.js").read_text(encoding="utf-8")
    assert "Quelle und Stand" in js and "Stand laut Quelle" in js
    for l in alle_loipen(site):
        assert l["quelle"]["name"] and l["quelle"]["url"].startswith("http")


def luminanz(hexfarbe: str) -> float:
    r, g, b = (int(hexfarbe[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def kontrast(a: str, b: str) -> float:
    hell, dunkel = sorted((luminanz(a), luminanz(b)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


@pytest.mark.req("U22", ak=2)
def test_u22_kontrast_der_statusfarben_mindestens_4_5():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    hell = re.search(r":root\{[^}]*\}", css).group(0)
    dunkel = re.search(r"prefers-color-scheme:dark\)\{:root\{([^}]*)\}", css).group(1)
    for name, block in (("hell", hell), ("dunkel", dunkel)):
        v = dict(re.findall(r"--([a-z0-9-]+):(#[0-9a-fA-F]{6})", block))
        for s in ("ok", "mid", "bad", "unk"):
            assert kontrast(v[s], v[f"{s}-bg"]) >= 4.5, f"{name}: Status {s} {kontrast(v[s], v[f'{s}-bg']):.2f}"
    # Haupttext auf dem Hintergrund
    v = dict(re.findall(r"--([a-z0-9-]+):(#[0-9a-fA-F]{6})", hell))
    assert kontrast(v["ink"], v["bg"]) >= 4.5 and kontrast(v["mute"], v["bg"]) >= 4.5
    v = dict(re.findall(r"--([a-z0-9-]+):(#[0-9a-fA-F]{6})", dunkel))
    assert kontrast(v["ink"], v["bg"]) >= 4.5 and kontrast(v["mute"], v["bg"]) >= 4.5


@pytest.mark.req("U22", ak=1)
def test_u22_jeder_status_hat_symbol_und_wort():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    wort = re.search(r"var WORT = \{([^}]*)\}", js).group(1)
    sym = re.search(r"var SYM = \{(.*?)\n\};", js, re.S).group(1)
    for status in ("offen", "eingeschraenkt", "geschlossen", "unbekannt"):
        assert status in wort and status in sym
    assert len(set(re.findall(r"<path d=\"([^\"]+)\"", sym))) >= 4  # vier verschiedene Symbole


@pytest.mark.req("U10", ak=1)
def test_u10_kennzahlen_stimmen_mit_der_datenbank(session, site):
    kz = lies(site, "daten.json")["kennzahlen"]
    assert kz["loipen"] == session.scalar(select(func.count()).select_from(Loipe))
    assert kz["offen"] + kz["eingeschraenkt"] + kz["geschlossen"] + kz["unbekannt"] == kz["loipen"]
    assert kz["gebiete"] == sum(r["gebiete"] for r in lies(site, "daten.json")["regionen"])
    assert {q["key"] for q in lies(site, "daten.json")["quellen"]} == {"tegernsee", "bayrischzell", "fischbachau", "sachrang", "chiemgau"}


@pytest.mark.req("U6", ak=1)
def test_u6_jede_loipe_hat_abrufzeit(site):
    loipen = alle_loipen(site)
    assert loipen and all(l["abgerufen"] for l in loipen)
    assert not any(l["veraltet"] for l in loipen)  # frisch abgerufen


@pytest.mark.req("U6", ak=2)
def test_u6_alte_daten_und_fehlgeschlagene_laeufe_sind_markiert(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    generator.erzeuge(session, tmp_path, JETZT + timedelta(hours=49))  # 49 h spaeter, kein neuer Abruf
    assert all(l["veraltet"] for l in alle_loipen(tmp_path))
    q = session.scalar(select(Quelle).where(Quelle.key == "sachrang"))
    q.last_status, q.last_error = "fehler", "HTTP 500"
    generator.erzeuge(session, tmp_path, JETZT)
    sachrang = [l for r in lies(tmp_path, "daten.json")["regionen"] for g in lies(tmp_path, r["datei"])["gebiete"] if g["slug"] == "sachrang" for l in g["loipen"]]
    assert sachrang and all(l["veraltet"] and l["quelle_fehler"] for l in sachrang)


@pytest.mark.req("U6")
def test_zustand_ohne_bestaetigung_gilt_nach_stale_days_als_unbekannt(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    generator.erzeuge(session, tmp_path, JETZT + timedelta(days=8), stale_days=7)
    assert {l["status"] for l in alle_loipen(tmp_path)} == {"unbekannt"}


@pytest.mark.req("U5", ak=1)
def test_u5_detaildaten_historie_14_tage_und_quelle(site):
    l = next(l for l in alle_loipen(site) if l["name"] == "Sonnenmoosrunde")
    assert len(l["historie"]) == 14
    assert l["historie"][-1] == {"tag": "2026-11-09", "status": "geschlossen"}
    assert l["historie"][0]["status"] is None  # vor dem ersten Abruf keine Daten, nicht erfunden
    assert l["laenge_km"] and l["quelle"]["url"].startswith("https://www.tegernsee.com")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "Letzte 14 Tage" in js and "Karte der Loipe" in js and "Navigation" in js


@pytest.mark.req("U14", ak=2)
def test_u14_parkplaetze_mit_navigation_und_gebuehr_oder_unbekannt(site):
    gebiete = [g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"]]
    kreuth = next(g for g in gebiete if g["slug"] == "kreuth")
    assert kreuth["parkplaetze"]
    for p in kreuth["parkplaetze"]:
        assert -90 < p["lat"] < 90 and -180 < p["lon"] < 180
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "google.com/maps/dir/?api=1&destination=" in js and '"unbekannt"' in js


@pytest.mark.req("U26", ak=1)
def test_u26_haltestelle_mit_name_und_koordinaten_oder_keine_bekannt(site):
    gebiete = [g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"]]
    sachrang = next(g for g in gebiete if g["slug"] == "sachrang")
    assert sachrang["haltestellen"] and all(h["name"] and h["lat"] and h["lon"] for h in sachrang["haltestellen"])
    assert any(g["haltestellen"] == [] for g in gebiete)  # dort zeigt die Seite "keine bekannt"
    assert "keine bekannt" in (STATIC / "app.js").read_text(encoding="utf-8")


@pytest.mark.req("U15", ak=1)
def test_u15_vorhersage_reicht_ueber_sieben_tage(site):
    kreuth = next(g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"] if g["slug"] == "kreuth")
    assert len(kreuth["vorhersage"]) >= 7
    assert kreuth["vorhersage"][0]["datum"] == "2026-11-09"


@pytest.mark.req("U18", ak=3)
def test_u18_vorhersage_ist_von_messwerten_getrennt(site):
    kreuth = next(g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"] if g["slug"] == "kreuth")
    assert "vorhersage" in kreuth and "schnee" in kreuth and kreuth["schnee"]["quelle"] == "DWD Klimadaten Tageswerte"
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "Vorhersage (keine Messung)" in js and "Gemessen am" in js


@pytest.mark.req("D11", ak=1)
def test_d11_schnee_im_gebiet_mit_zeitpunkt_und_quelle(site):
    sachrang = next(g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"] if g["slug"] == "sachrang")
    s = sachrang["schnee"]
    assert s["schneehoehe_cm"] == 23 and s["messtag"] == "2026-11-09" and s["station_name"] == "Aschau-Stein"
    assert s["neuschnee_24h_cm"] == 6.0 and s["neuschnee_72h_cm"] == 6.0 + 4.0 + 2.0


@pytest.mark.req("U21", ak=3)
def test_u21_orte_ohne_loipe_stehen_in_den_daten(site):
    namen = {o["name"] for o in lies(site, "daten.json")["orte"]}
    assert {"Rosenheim", "München"} <= namen
    assert lies(site, "daten.json")["standardort"] == "Rottach-Egern"


@pytest.mark.req("U8", ak=2)
def test_u8_installierbar_manifest_icons_service_worker(site):
    m = lies(site, "manifest.webmanifest")
    assert m["display"] == "standalone" and m["start_url"] and m["name"]
    groessen = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= groessen
    for i in m["icons"]:
        png = (site / i["src"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        breite, hoehe = struct.unpack(">II", png[16:24])
        assert f"{breite}x{hoehe}" == i["sizes"]
    assert "manifest.webmanifest" in (site / "index.html").read_text(encoding="utf-8")
    assert "serviceWorker" in (site / "app.js").read_text(encoding="utf-8") and (site / "sw.js").exists()


@pytest.mark.req("U8", ak=3)
def test_u8_dark_mode_folgt_der_systemeinstellung():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme:dark" in css and "color-scheme:light dark" in css


@pytest.mark.req("B7")
def test_generator_raeumt_entfernte_regionen_auf(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    generator.erzeuge(session, tmp_path, JETZT)
    (tmp_path / "daten" / "alt.json").write_text("{}")
    generator.erzeuge(session, tmp_path, JETZT)
    assert not (tmp_path / "daten" / "alt.json").exists()
    assert not list(tmp_path.rglob(".tmp-*"))


def test_gebiete_haben_hoehe_in_den_daten(session):
    from loipen.generator.daten import baue
    from loipen.konfig import CONFIG_DIR
    jetzt = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    lade_alle_fixtures(session, jetzt)
    regionen = baue(session, jetzt, CONFIG_DIR)["regionen"].values()
    hoehen = {g["slug"]: g["hoehe_m"] for r in regionen for g in r["gebiete"]}
    assert hoehen["bayrischzell"] > hoehen["marquartstein-grassau"] and None not in hoehen.values()


@pytest.mark.req("U15", ak=3)
def test_u15_wetter_kommt_mit_der_statischen_seite(site):
    """Die Vorhersage steht in den erzeugten JSON-Dateien, der Browser fragt keinen Wetterdienst."""
    gebiete = [g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"]]
    assert sum(1 for g in gebiete if g["vorhersage"]) >= len(gebiete) // 2
    for datei in site.rglob("*.js"):
        js = datei.read_text(encoding="utf-8")
        for host in ("brightsky", "dwd.de", "open-meteo", "openweathermap"):
            assert host not in js, (datei.name, host)
