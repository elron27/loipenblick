"""Ausbaustufe 1 (Kufstein/Tirol und Salzburg): Konfiguration, Dubletten, Daten fuer die Seite.

P12, P13, P15, P17, P19, P20, B19, D15, D16, U30, U31. Die Oberflaeche dazu steht in
tests/test_website_ausbau.py, die Adapter in tests/test_adapter_tirol.py und tests/test_adapter_ausbau.py.
"""

import copy
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator
from loipen.ablauf import rufe_quelle_ab
from loipen.dubletten import Eintrag, finde_dubletten, gleich
from loipen.konfig import CONFIG_DIR, abgleichen, lade_yaml, pruefe
from loipen.models import Gebiet, Quelle, Region
from loipen.zeitplan import ist_faellig
from tests.helpers import FIXTURES, SEITEN_QUELLEN, STAND_QUELLEN, TIROL_LISTE, FixtureFetcher, lade_alle_fixtures

ROOT = Path(__file__).resolve().parent.parent
JETZT = datetime(2026, 11, 12, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
UA = "LoipenBot"
VERBOTEN = ("salzkammergut.at", "intermaps", "bergfex")
NEUE_QUELLEN = ("tirol", "kitzbueheler-alpen", "langlaufdorf", "berchtesgaden")
DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sources() -> dict:
    return lade_yaml(CONFIG_DIR / "sources.yaml")


def gebiete_yaml() -> dict:
    return lade_yaml(CONFIG_DIR / "gebiete.yaml")


def quellen() -> list[dict]:
    return sources()["quellen"]


@pytest.fixture
def site(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    generator.erzeuge(session, tmp_path, JETZT)
    return tmp_path


def lies(site: Path, rel: str):
    return json.loads((site / rel).read_text(encoding="utf-8"))


def alle_gebiete(site: Path) -> list[dict]:
    return [g for r in lies(site, "daten.json")["regionen"] for g in lies(site, r["datei"])["gebiete"]]


def alle_loipen(site: Path) -> list[dict]:
    return [l for g in alle_gebiete(site) for l in g["loipen"]]


# ---------- P17: nur erlaubte Quellen ----------

@pytest.mark.req("P17", ak=1)
def test_p17_jede_quelle_hat_einen_eintrag_zur_nutzung():
    for q in quellen():
        n = q.get("nutzung")
        assert n, q["key"]
        assert DATUM.match(str(n["robots_geprueft"])), q["key"]
        # null heisst: vor dem Oeffentlichschalten noch zu pruefen (Blindspot 6); der Schluessel muss da sein
        assert "nutzungsbedingungen_geprueft" in n, q["key"]
        assert n["nutzungsbedingungen_geprueft"] is None or DATUM.match(str(n["nutzungsbedingungen_geprueft"]))


@pytest.mark.req("P17", ak=1)
def test_p17_pruefung_meldet_fehlenden_nutzungseintrag():
    s = sources()
    del s["quellen"][0]["nutzung"]
    assert any("nutzung.robots_geprueft fehlt" in f for f in pruefe(s, gebiete_yaml()))


def _pfade(q: dict) -> list[str]:
    cfg = q.get("config", {})
    if q["key"] == "tirol":
        return ["/" + TIROL_LISTE, "/aktivitaeten/sport/langlaufen/loipen/kufstein"]
    if "seiten" in cfg:
        return [s["pfad"] for s in cfg["seiten"]]
    return [cfg.get("pfad", "/")]


@pytest.mark.req("P17", ak=2)
@pytest.mark.parametrize("key", NEUE_QUELLEN)
def test_p17_gespeicherte_robots_txt_erlaubt_unsere_abrufe(key):
    """Die robots.txt vom Schnappschusstag erlaubt jeden Pfad, den der Adapter abruft."""
    q = next(x for x in quellen() if x["key"] == key)
    assert q["nutzung"]["robots"] == "erlaubt"
    robots = FIXTURES / key / STAND_QUELLEN[key] / "robots.txt"
    rp = RobotFileParser()
    rp.parse(robots.read_text(encoding="utf-8", errors="replace").splitlines())
    for pfad in _pfade(q):
        assert rp.can_fetch(UA, q["base_url"] + pfad), (key, pfad)


@pytest.mark.req("P17", ak=2)
def test_p17_keine_quelle_mit_robots_sperre_konfiguriert():
    for q in quellen():
        assert q["nutzung"]["robots"] == "erlaubt", q["key"]
        assert not any(v in q["base_url"].lower() for v in VERBOTEN), q["key"]
    s = sources()
    s["quellen"][0]["nutzung"]["robots"] = "gesperrt"
    assert any("robots.txt erlaubt den Abruf nicht" in f for f in pruefe(s, gebiete_yaml()))


# ---------- P20: Portale vor Ortsseiten ----------

@pytest.mark.req("P20", ak=1)
def test_p20_jede_ortsseite_nennt_das_gebiet_das_sie_schliesst():
    slugs = {g["slug"] for g in gebiete_yaml()["gebiete"]}
    ortsseiten = [q for q in quellen() if q["art"] == "ortsseite"]
    assert {q["key"] for q in ortsseiten} >= {"langlaufdorf"}
    for q in ortsseiten:
        assert q["schliesst"] and set(q["schliesst"]) <= slugs, q["key"]
    assert {q["art"] for q in quellen()} <= {"portal", "ortsseite"}
    s = sources()
    next(q for q in s["quellen"] if q["key"] == "langlaufdorf").pop("schliesst")
    assert any("Ortsseite ohne Angabe" in f for f in pruefe(s, gebiete_yaml()))


# ---------- B19: echte Schnappschuesse ----------

@pytest.mark.req("B19", ak=1)
def test_b19_jede_quelle_hat_einen_fixture_ordner_mit_datum():
    """Neue Quellen haben tests/fixtures/<quelle>/<datum>/, die alten vom 09.11. eine Datei STAND."""
    for q in quellen():
        ordner = FIXTURES / q["key"]
        assert ordner.is_dir(), q["key"]
        datiert = [p for p in ordner.iterdir() if p.is_dir() and DATUM.match(p.name)]
        stand = ordner / "STAND"
        assert datiert or (stand.exists() and DATUM.match(stand.read_text().strip())), q["key"]
        if q["key"] in NEUE_QUELLEN:
            assert datiert and any(p.suffix == ".html" for d in datiert for p in d.iterdir()), q["key"]
    # Jeder Schnappschuss-Abruf steht im Protokoll (wer, wann, robots geprueft)
    protokoll = (FIXTURES / "schnappschuss-protokoll.txt").read_text(encoding="utf-8")
    for key in NEUE_QUELLEN:
        assert urlparse(next(q["base_url"] for q in quellen() if q["key"] == key)).hostname in protokoll


@pytest.mark.req("B19", ak=2)
def test_b19_host_jeder_quelle_steht_in_der_cloud_umgebung():
    umgebung = lade_yaml(CONFIG_DIR / "cloud-umgebung.yaml")
    assert umgebung["umgebung"] == "loipenblick"
    hosts = set(umgebung["hosts"])
    for q in quellen():
        assert urlparse(q["base_url"]).hostname in hosts, q["key"]
    # Wetterdienste ebenso
    from loipen import wetter

    for url in (wetter.GEOSPHERE_URL, wetter.BRIGHTSKY_URL):
        assert urlparse(url).hostname in hosts
    assert not any(v in h for h in hosts for v in VERBOTEN)


# ---------- P19: eigener Abrufplan je Quelle ----------

@pytest.mark.req("P19", ak=1)
def test_p19_quelle_mit_eigenem_zeitplan_wird_danach_abgerufen(session):
    abgleichen(session, sources(), gebiete_yaml())
    plan = {q.key: q.config["zeitplan"] for q in session.scalars(select(Quelle))}
    mittag = datetime(2026, 12, 15, 12, 0)
    frueh = datetime(2026, 12, 15, 7, 0)
    assert ist_faellig(mittag, plan["tirol"]) and not ist_faellig(mittag, plan["berchtesgaden"])
    assert ist_faellig(frueh, plan["berchtesgaden"])
    # Die Saisongrenze bleibt die gemeinsame, nur die Uhrzeiten weichen ab
    assert plan["berchtesgaden"]["saison"] == plan["tirol"]["saison"]
    worker = (ROOT / "loipen" / "worker" / "__main__.py").read_text(encoding="utf-8")
    assert 'ist_faellig(nur_faellige, quelle.config.get("zeitplan"))' in worker


# ---------- P12, D16: Laender, Sprachen, Regionen ----------

@pytest.mark.req("D16", ak=1)
@pytest.mark.req("P12", ak=1)
def test_d16_jedes_gebiet_hat_land_bundesland_und_region(session, site):
    regionen = {r["slug"]: r for r in gebiete_yaml()["regionen"]}
    for g in gebiete_yaml()["gebiete"]:
        r = regionen[g["region"]]
        assert r["land"] in ("DE", "AT", "IT", "CH", "LI") and r["bundesland"], g["slug"]
    for r in session.scalars(select(Region)):
        assert r.land in ("DE", "AT", "IT", "CH", "LI") and r.bundesland, r.slug
    for g in alle_gebiete(site):
        assert g["land"] in ("DE", "AT", "IT", "CH", "LI") and g["bundesland"], g["slug"]
    laender = [r["land"] for r in lies(site, "daten.json")["regionen"]]
    # Deutschland zuerst, dann Oesterreich, Italien, Schweiz, Liechtenstein (E-20)
    assert laender == sorted(laender, key=lambda x: {"DE": 0, "AT": 1, "IT": 2, "CH": 3, "LI": 4}[x])
    assert {g["slug"]: g["bundesland"] for g in alle_gebiete(site)}["faistenau"] == "Salzburg"


@pytest.mark.req("P12", ak=1)
def test_p12_gebiet_kann_mehrere_namen_haben(session, tmp_path):
    geb = copy.deepcopy(gebiete_yaml())
    kufstein = next(g for g in geb["gebiete"] if g["slug"] == "kufstein")
    kufstein["namen"] = {"de": "Kufstein", "it": "Kufstein (Tirolo)"}
    abgleichen(session, sources(), geb)
    assert session.scalar(select(Gebiet).where(Gebiet.slug == "kufstein")).namen["it"] == "Kufstein (Tirolo)"
    generator.erzeuge(session, tmp_path, JETZT)
    g = next(g for g in alle_gebiete(tmp_path) if g["slug"] == "kufstein")
    assert g["namen"] == {"de": "Kufstein", "it": "Kufstein (Tirolo)"} and g["land"] == "AT"


# ---------- D15, P15: Dubletten ----------

def _e(i, name, quelle, rang, lat=47.58, lon=12.17, gebiet="kufstein"):
    return Eintrag(i, name, quelle, rang, gebiet, gebiet.title(), lat, lon)


@pytest.mark.req("D15", ak=1)
def test_d15_aehnlicher_name_und_start_unter_300_m_ist_eine_loipe():
    a = _e(1, "Kaiserlift-Loipe", "tirol", 3)
    b = _e(2, "Kaiserliftloipe Kufstein", "kufsteinerland", 2, lat=47.58 + 0.002)  # gut 220 m
    c = _e(3, "Kaiserlift-Loipe", "andere", 5, lat=47.58 + 0.03)  # 3,3 km weg
    d = _e(4, "Thierseer Höhenloipe", "kufsteinerland", 2, lat=47.5801)
    assert gleich(a, b) and not gleich(a, c) and not gleich(a, d)
    assert finde_dubletten([a, b, c, d]) == {1: 2}  # b fuehrt (Rang 2), a wird verdeckt


@pytest.mark.req("D15", ak=1)
def test_d15_echte_dublette_steht_einmal_in_den_daten(session, site):
    """Die Hauswies-Runde melden Bayrischzell und Fischbachau; die Seite zeigt sie einmal."""
    namen = [l["name"] for l in alle_loipen(site)]
    hauswies = [l for l in alle_loipen(site) if l["name"].startswith("Hauswies-Runde")]
    assert len(hauswies) == 1
    l = hauswies[0]
    assert sorted(a["quelle"] for a in l["auch_bei"]) == ["Fischbachau Tourismus", "Tirol Werbung (tirol.at)"]
    index = lies(site, "daten.json")
    # tirol.at fuehrt Bayrischzell und die Kitzbueheler Gebiete mit: gut 50 Dubletten, jede einmal gezeigt
    assert index["dubletten"] >= 50 and index["kennzahlen"]["loipen"] == len(namen)
    assert sum(q["anzahl"] for q in index["quellen"]) - index["dubletten"] == len(namen)


@pytest.mark.req("D15", ak=2)
def test_d15_fuehrende_quelle_steht_in_sources_yaml(session):
    raenge = {q["key"]: q["rang"] for q in quellen()}
    assert all(isinstance(r, int) and r >= 1 for r in raenge.values())
    # Ortsquelle mit Praeparierdatum vor tirol.at vor Kitzbueheler Alpen (Kommentar in sources.yaml)
    assert raenge["langlaufdorf"] < raenge["tirol"] < raenge["kitzbueheler-alpen"]
    abgleichen(session, sources(), gebiete_yaml())
    assert {q.key: q.config["rang"] for q in session.scalars(select(Quelle))} == raenge


def _tirol_mit_kitzbuehel(session, tmp_path) -> Path:
    """P14 AK 2 + P15 AK 2: weitere Tiroler Gebiete nur ueber sources.yaml zuschalten."""
    s = sources()
    s["quellen"] = [q for q in s["quellen"] if q["key"] in ("tirol", "kitzbueheler-alpen")]
    tirol = s["quellen"][0]
    tirol["config"]["gebiete"] += ["brixental", "hohe-salve", "pillerseetal", "st-johann-in-tirol"]
    abgleichen(session, s, gebiete_yaml())
    for q in session.scalars(select(Quelle)):
        rufe_quelle_ab(session, q, FixtureFetcher(q.key, q.base_url, seiten=SEITEN_QUELLEN.get(q.key)), JETZT)
    generator.erzeuge(session, tmp_path, JETZT)
    return tmp_path


@pytest.mark.req("P15", ak=2)
@pytest.mark.req("D15", ak=2)
def test_p15_loipen_von_tirol_at_und_kitzbuehel_erscheinen_einmal(session, tmp_path):
    site = _tirol_mit_kitzbuehel(session, tmp_path)
    index = lies(site, "daten.json")
    assert index["dubletten"] >= 10
    kitz = [g for g in alle_gebiete(site) if g["slug"] in ("brixental", "hohe-salve", "pillerseetal", "st-johann-in-tirol")]
    for g in kitz:
        namen = [l["name"] for l in g["loipen"]]
        assert len(namen) == len(set(namen)), g["slug"]
    doppelt = [l for g in kitz for l in g["loipen"] if l["auch_bei"]]
    # tirol.at fuehrt (Rang 3 vor 4) und traegt den Kitzbueheler Eintrag als "auch bei"
    assert doppelt and all(l["quelle"]["name"].startswith("Tirol") for l in doppelt)
    assert all(a["quelle"] == "Kitzbüheler Alpen Loipenstatus" for l in doppelt for a in l["auch_bei"])
    assert index["kennzahlen"]["loipen"] == sum(q["anzahl"] for q in index["quellen"]) - index["dubletten"]


# ---------- P13: neue Region, Abdeckung ----------

@pytest.mark.req("P13", ak=2)
def test_p13_uebersicht_zeigt_anbindungsstand_je_region(site):
    abdeckung = {a["region"]: a for a in lies(site, "daten.json")["abdeckung"]}
    regionen = lies(site, "daten.json")["regionen"]
    assert set(abdeckung) == {r["name"] for r in regionen}
    for r in regionen:
        a = abdeckung[r["name"]]
        assert a["angebunden"] + a["nur_stammdaten"] + a["ohne_quelle"] == a["gebiete"] == r["gebiete"]
        assert a["land"] == r["land"] and a["bundesland"] == r["bundesland"]
    assert abdeckung["Berchtesgadener Land"]["nur_stammdaten"] == abdeckung["Berchtesgadener Land"]["gebiete"]
    assert abdeckung["Kufsteinerland"]["angebunden"] == abdeckung["Kufsteinerland"]["gebiete"]
    assert abdeckung["Tegernseer Tal"]["ohne_quelle"] >= 1  # Gebiet Tegernsee selbst ohne eigene Loipe


# ---------- U30: Status ohne Datum ----------

@pytest.mark.req("U30", ak=1)
@pytest.mark.req("U30", ak=2)
def test_u30_tirol_loipen_ohne_datum_sind_nicht_faelschlich_veraltet(site):
    tirol = [l for l in alle_loipen(site) if l["quelle"]["name"].startswith("Tirol")]
    assert len(tirol) >= 50
    for l in tirol:
        assert l["ohne_datum"] and l["quelle_stand"] is None and l["abgerufen"], l["name"]
        assert l["veraltet"] is False, l["name"]
    mit_datum = [l for l in alle_loipen(site) if l["quelle"]["name"] == "Bayrischzell Tourismus"]
    assert mit_datum and not any(l["ohne_datum"] for l in mit_datum)


# ---------- U31: Vignette und Loipengebuehr ----------

@pytest.mark.req("U31", ak=1)
def test_u31_jedes_oesterreichische_gebiet_zeigt_den_vignettenhinweis(site):
    for g in alle_gebiete(site):
        if g["land"] in ("AT", "IT", "CH", "LI"):
            # Italien (E-18): Anfahrt ueber Oesterreich, dazu Brenner- und Autobahnmaut
            assert g["grenzinfo"] and "Vignette" in g["grenzinfo"], g["slug"]
        else:
            assert not g["grenzinfo"], g["slug"]


@pytest.mark.req("U31", ak=2)
def test_u31_loipengebuehr_steht_dabei_wenn_bekannt(site):
    g = {g["slug"]: g for g in alle_gebiete(site)}
    for slug in ("faistenau", "hintersee"):
        assert g[slug]["loipengebuehr"]["eur"] == 11.0
        assert g[slug]["loipengebuehr"]["url"].startswith("https://www.langlaufdorf.at")
