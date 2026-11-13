"""Suedtirol (E-18): Dolomiti NordicSki (P23), Open Data Hub Suedtirol (P24), Dubletten zwischen beiden.

Schnappschuesse vom 13.11.2026 (Workflow Schnappschuss, Runde 9):
- tests/fixtures/dolomiti-nordicski/2026-11-13/loipen-de.html: Loipentabelle aller Mitgliedsregionen
  (173 Loipen, im November alle geschlossen oder "nicht bekannt"); js_trails.js zeigt, dass der
  Regionsfilter nur im Browser wirkt (?region= liefert dieselbe Seite).
- tests/fixtures/opendatahub/2026-11-13/loipen.json: 272 Loipen aus dem Open Data Hub (CC0).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator
from loipen.ablauf import rufe_quelle_ab
from loipen.adapters.suedtirol import DolomitiNordicSkiAdapter, OpenDataHubAdapter, lese_tabelle, name_und_kennung
from loipen.dubletten import Eintrag, gleich, nummern
from loipen.konfig import CONFIG_DIR, abgleichen, lade_yaml, pruefe
from loipen.models import Quelle, Schwierigkeit, Status, Technik
from tests.helpers import FIXTURES, SEITEN_QUELLEN, FixtureFetcher

JETZT = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
DNS_SEITE = FIXTURES / "dolomiti-nordicski/2026-11-13/loipen-de.html"
ODH_DATEI = FIXTURES / "opendatahub/2026-11-13/loipen.json"
ODH_PFAD = next(iter(SEITEN_QUELLEN["opendatahub"]))
DNS_PFAD = next(iter(SEITEN_QUELLEN["dolomiti-nordicski"]))
SUEDTIROL = {"drei-zinnen", "pustertal", "groeden-seiser-alm", "eisacktal-wipptal", "eggental", "vinschgau-meran"}


def sources() -> dict:
    return lade_yaml(CONFIG_DIR / "sources.yaml")


def gebiete_yaml() -> dict:
    return lade_yaml(CONFIG_DIR / "gebiete.yaml")


def quelle(key: str) -> dict:
    return next(q for q in sources()["quellen"] if q["key"] == key)


def gebiete() -> dict[str, dict]:
    return {g["slug"]: g for g in gebiete_yaml()["gebiete"]}


def odh_config() -> dict:
    """Wie konfig.abgleichen: die Gebietsmitten kommen aus gebiete.yaml."""
    cfg = dict(quelle("opendatahub")["config"])
    g = gebiete()
    cfg["gebiet_punkte"] = {s: [g[s]["lat"], g[s]["lon"]] for s in cfg["gebiete"]}
    return cfg


def dns(ersetze: str | None = None):
    q = quelle("dolomiti-nordicski")
    fetcher = FixtureFetcher("dolomiti-nordicski", q["base_url"], seiten=SEITEN_QUELLEN["dolomiti-nordicski"],
                             ersetze={DNS_PFAD: ersetze} if ersetze else None)
    return DolomitiNordicSkiAdapter().run(q["base_url"], q["config"], fetcher), fetcher


def odh(jetzt: datetime = JETZT, ersetze: str | None = None):
    q = quelle("opendatahub")
    fetcher = FixtureFetcher("opendatahub", q["base_url"], seiten=SEITEN_QUELLEN["opendatahub"],
                             ersetze={ODH_PFAD: ersetze} if ersetze else None)
    return OpenDataHubAdapter(uhr=lambda: jetzt.timestamp()).run(q["base_url"], odh_config(), fetcher)


# ---------- P23: Dolomiti NordicSki ----------

@pytest.mark.req("P23", ak=1)
def test_p23_dolomiti_nordicski_liest_alle_loipen_mit_gebiet():
    erg, fetcher = dns()
    assert len(fetcher.abgerufen) == 1  # eine Seite fuer alle Regionen
    assert len(lese_tabelle(DNS_SEITE.read_text(encoding="utf-8"))) == 173
    # 55 Osttiroler Loipen fallen weg (P23 AK 3), alle anderen haben ein Gebiet
    assert len(erg.loipen) == 118 and erg.warnungen == []
    g = gebiete()
    assert {g[d.gebiet_slug]["region"] for d in erg.loipen} == {"drei-zinnen", "pustertal", "groeden-seiser-alm",
                                                                "cortina-comelico"}
    assert len({d.source_key for d in erg.loipen}) == len(erg.loipen)
    wolfsbuehl = next(d for d in erg.loipen if d.name == "6 Wolfsbühl")  # ohne "| SEISER ALM"
    assert wolfsbuehl.gebiet_slug == "seiser-alm"
    assert wolfsbuehl.laenge_km == 8.77 and wolfsbuehl.schwierigkeit == Schwierigkeit.LEICHT
    assert wolfsbuehl.status == Status.GESCHLOSSEN and wolfsbuehl.quelle_aktualisiert_at is None  # kein Datum
    assert wolfsbuehl.lat is None  # keine Koordinaten in der Quelle
    fisch = next(d for d in erg.loipen if d.name == "18 SEXTEN - Rundloipe Fischleintal")
    assert fisch.gebiet_slug == "sexten"
    assert json.loads(fisch.rohtext)["hinweis"] == "Bei Schneemangel nur Skating möglich."
    by_name = {d.name: d.gebiet_slug for d in erg.loipen}
    assert by_name["01 Toblacher Stadionrunde"] == "toblach"
    assert by_name["01 Gsiesertal Loipe"] == "gsies"
    assert by_name["Sonnenloipe Kasern"] == "ahrntal"
    assert by_name["Campotrondo"] == "comelico"
    assert by_name["1B Loipe Biathlonzentrum"] == "antholz"  # Name wie im ODH (namen_ersatz)


def test_p23_regionskennung_wird_vom_namen_getrennt():
    assert name_und_kennung("6 Wolfsbühl | SEISER ALM") == ("6 Wolfsbühl", "SEISER ALM")
    assert name_und_kennung("11 Verbindungsloipe Saltria - Monte Pana | Teilstück SEISER ALM") == (
        "11 Verbindungsloipe Saltria - Monte Pana (Teilstück)", "SEISER ALM")
    assert name_und_kennung("1 Antholzertal: Talloipe | Sonnenloipe (Nr.2)") == (
        "1 Antholzertal: Talloipe | Sonnenloipe (Nr.2)", None)


@pytest.mark.req("P23", ak=2)
def test_p23_fuenf_statusstufen_werden_abgebildet():
    seite = DNS_SEITE.read_text(encoding="utf-8")
    zeilen = seite.split('<td data-status="closed"')
    # die ersten vier geschlossenen Zeilen (Seiser Alm, Groeden, Antholz) bekommen die anderen Stufen
    codes = ["open", "partially_open", "open_not_prepared", "unknown", "fehlcode"]
    neu = zeilen[0] + "".join(f'<td data-status="{codes[i - 1] if i <= len(codes) else "closed"}"' + z
                              for i, z in enumerate(zeilen[1:], start=1))
    erg, _ = dns(ersetze=neu)
    status = {d.name: (d.status, d.status_rohtext) for d in erg.loipen}
    assert status["10 Verbindungsloipe Ritsch - Saltria"] == (Status.OFFEN, "Dolomiti NordicSki: geöffnet")
    assert status["Droc"][0] == Status.EINGESCHRAENKT
    assert status["6 Wolfsbühl"] == (Status.EINGESCHRAENKT, "Dolomiti NordicSki: geöffnet, nicht präpariert")
    assert status["1B Loipe Biathlonzentrum"][0] == Status.UNBEKANNT
    # ein unbekannter Code wird nicht verschluckt (P5)
    fehl = next(d for d in erg.loipen if d.name == "5B Loipe Biathlonzentrum")
    assert fehl.status == Status.UNBEKANNT and fehl.unbekannte_begriffe == [("status", "fehlcode")]


@pytest.mark.req("P23", ak=3)
def test_p23_osttirol_bleibt_bei_tirol_at_und_unbekannte_orte_werden_gemeldet():
    erg, _ = dns()
    osttirol = {g["slug"] for g in gebiete_yaml()["gebiete"] if g["region"] == "osttirol"}
    assert not {d.gebiet_slug for d in erg.loipen} & osttirol
    assert not [d for d in erg.loipen if "Obertilliach" in d.name or "Kals" in d.name]
    # eine Loipe ohne passenden Ort wird gemeldet statt geraten
    seite = DNS_SEITE.read_text(encoding="utf-8").replace("<strong>Droc | DOLOMITES VAL GARDENA",
                                                          "<strong>Neue Loipe Irgendwo")
    erg, _ = dns(ersetze=seite)
    assert len(erg.loipen) == 117
    assert erg.warnungen and "Neue Loipe Irgendwo" in erg.warnungen[0] and "gebiet_map" in erg.warnungen[0]


def test_p23_seitenaufbau_geaendert_ist_ein_fehler():
    with pytest.raises(ValueError, match="table-trails"):
        dns(ersetze="<html><body>Wartung</body></html>")


# ---------- P24: Open Data Hub Suedtirol ----------

@pytest.mark.req("P24", ak=1)
def test_p24_open_data_hub_liefert_suedtirol_mit_lage():
    erg = odh()
    roh = json.loads(ODH_DATEI.read_text(encoding="utf-8"))
    assert roh["TotalResults"] == 272
    assert len(erg.loipen) == 190 and erg.warnungen == []
    g = gebiete()
    assert {g[d.gebiet_slug]["region"] for d in erg.loipen} == SUEDTIROL
    assert all(d.lat and d.lon for d in erg.loipen)
    namen = {d.name for d in erg.loipen}
    # Schweiz, Nauders (tirol.at), Cadore und Cortina/Comelico (Dolomiti NordicSki) gehoeren nicht dazu
    assert not [n for n in namen if "Zernez" in n or "Nauders" in n or "Scuol" in n or "Fuldera" in n]
    assert not [n for n in namen if n.startswith(("PISTA", "Track 3G", "Loipe \"Ferrovia\"", "Lorenzago"))]
    # Testeintraege fallen weg
    assert not [n for n in namen if n.startswith("TEST")]
    # Loipen mit Suedtiroler Verein gehoeren immer dazu, auch nahe der Grenze oder am Rand
    assert {"Reschen - Reschenseeloipe", "Sonnenloipe Kasern", "Langlaufloipe Hafling/Falzeben"} <= namen
    stadion = next(d for d in erg.loipen if d.name == "01 Toblacher Stadionrunde")
    assert stadion.gebiet_slug == "toblach" and stadion.technik == Technik.BEIDES
    gsies = next(d for d in erg.loipen if d.name == "01 Gsiesertal Loipe")
    assert gsies.gebiet_slug == "gsies"  # Verein entscheidet, obwohl der Start naeher an Niederdorf liegt
    assert {d.technik for d in erg.loipen} == {Technik.BEIDES, Technik.KLASSISCH, Technik.SKATING}
    assert json.loads(stadion.rohtext)["lizenz"] == "CC0"


@pytest.mark.req("P24", ak=2)
def test_p24_offen_nur_mit_frischer_aenderung():
    erg = odh()
    # 13.11.: Eintraege stehen seit dem letzten Winter auf "offen" -> unbekannt, nie offen
    alt = [d for d in erg.loipen if d.status == Status.UNBEKANNT]
    assert {d.name for d in alt} >= {"Rundloipe Laurin", "25 Niederdorf - Marathonloipe / Grenze Toblach bis Grenze Prags"}
    assert all("unbestätigt" in d.status_rohtext for d in alt)
    assert not [d for d in erg.loipen if d.status == Status.OFFEN]
    assert {d.status for d in erg.loipen} == {Status.GESCHLOSSEN, Status.UNBEKANNT}
    laurin = next(d for d in alt if d.name == "Rundloipe Laurin")
    assert laurin.quelle_aktualisiert_at.date().isoformat() == "2025-12-02"
    # derselbe Eintrag, am Tag nach der Aenderung abgerufen: offen
    erg = odh(jetzt=laurin.quelle_aktualisiert_at.astimezone(ZoneInfo("Europe/Berlin")).replace(hour=23, minute=0))
    laurin = next(d for d in erg.loipen if d.name == "Rundloipe Laurin")
    assert laurin.status == Status.OFFEN and laurin.status_rohtext.startswith("Open Data Hub: geöffnet")


def test_p24_mehrere_seiten_werden_nachgeladen():
    roh = json.loads(ODH_DATEI.read_text(encoding="utf-8"))
    teil1 = dict(roh, Items=roh["Items"][:100], NextPage="https://tourism.api.opendatahub.com/v1/seite2")
    teil2 = dict(roh, Items=roh["Items"][100:], NextPage=None)
    q = quelle("opendatahub")
    fetcher = FixtureFetcher("opendatahub", q["base_url"],
                             ersetze={ODH_PFAD: json.dumps(teil1), "v1/seite2": json.dumps(teil2)})
    erg = OpenDataHubAdapter(uhr=lambda: JETZT.timestamp()).run(q["base_url"], odh_config(), fetcher)
    assert len(fetcher.abgerufen) == 2 and len(erg.loipen) == 190


def test_p24_verein_map_nennt_nur_bekannte_gebiete():
    s = sources()
    next(q for q in s["quellen"] if q["key"] == "opendatahub")["config"]["verein_map"]["Toblach"] = "gibt-es-nicht"
    assert any("gibt-es-nicht" in f for f in pruefe(s, gebiete_yaml()))
    assert pruefe(sources(), gebiete_yaml()) == []


# ---------- D15/P24 AK 3: dieselbe Loipe in beiden Quellen ----------

def _e(i, name, quelle, rang, gebiet, gebiet_name, lat=None, lon=None, region="drei-zinnen"):
    return Eintrag(i, name, quelle, rang, gebiet, gebiet_name, lat, lon, region)


@pytest.mark.req("P24", ak=3)
def test_p24_loipennummern_trennen_varianten():
    assert nummern("11 B Val Fonda Runde") == nummern("11B Toblach: Val Fonda Runde") == {"11b"}
    assert nummern("Rennloipe Tavella 1- 5 km") == {"1"}
    a = _e(1, "11 Nordic Arena – Gemärk", "dns", 2, "toblach", "Toblach")
    b = _e(2, "11 Nordic Arena – Gemärk", "odh", 3, "toblach", "Toblach", 46.719, 12.224)
    c = _e(3, "11A Gemärk - Nordic Arena (Variante)", "odh", 3, "toblach", "Toblach", 46.719, 12.224)
    assert gleich(a, b) and not gleich(a, c)
    # verschiedene Gebiete derselben Region: beide Ortsnamen zaehlen nicht
    d = _e(4, "25 Niederdorf - Marathonloipe / Prags bis Nordic Arena", "dns", 2, "prags", "Prags")
    e = _e(5, "25 Niederdorf - Marathonloipe / Prags bis Nordic Arena", "odh", 3, "niederdorf", "Niederdorf",
           46.73, 12.17)
    assert gleich(d, e)
    f = _e(6, "1B Loipe Biathlonzentrum", "dns", 2, "antholz", "Antholzertal")
    g = _e(7, "Loipe Biathlonzentrum 2B", "odh", 3, "antholz", "Antholzertal", 46.885, 12.154)
    h = _e(8, "Loipe Biathlonzentrum 1B", "odh", 3, "antholz", "Antholzertal", 46.885, 12.154)
    assert gleich(f, h) and not gleich(f, g)


@pytest.fixture
def suedtirol_site(session, tmp_path) -> Path:
    s = sources()
    s["quellen"] = [q for q in s["quellen"] if q["key"] in ("dolomiti-nordicski", "opendatahub")]
    abgleichen(session, s, gebiete_yaml())
    for q in session.scalars(select(Quelle)):
        rufe_quelle_ab(session, q, FixtureFetcher(q.key, q.base_url, seiten=SEITEN_QUELLEN[q.key]), JETZT)
    generator.erzeuge(session, tmp_path, JETZT)
    return tmp_path


def _lies(site: Path, rel: str):
    return json.loads((site / rel).read_text(encoding="utf-8"))


@pytest.mark.req("P24", ak=3)
@pytest.mark.req("D15", ak=1)
def test_p24_dolomiti_fuehrt_und_bekommt_die_lage_vom_open_data_hub(suedtirol_site):
    index = _lies(suedtirol_site, "daten.json")
    regionen = {r["slug"]: r for r in index["regionen"]}
    assert SUEDTIROL | {"cortina-comelico"} <= set(regionen)
    assert {regionen[s]["land"] for s in SUEDTIROL} == {"IT"}
    assert {regionen[s]["bundesland"] for s in SUEDTIROL} == {"Südtirol"}
    # gut 80 Loipen stehen in beiden Quellen und werden einmal gezeigt
    assert index["dubletten"] >= 80
    assert index["kennzahlen"]["loipen"] == sum(q["anzahl"] for q in index["quellen"]) - index["dubletten"]
    loipen = [l for r in index["regionen"] for g in _lies(suedtirol_site, r["datei"])["gebiete"] for l in g["loipen"]]
    stadion = [l for l in loipen if l["name"] == "01 Toblacher Stadionrunde"]
    assert len(stadion) == 1
    l = stadion[0]
    assert l["quelle"]["name"] == "Dolomiti NordicSki (Loipenstatus)"
    assert [a["quelle"] for a in l["auch_bei"]] == ["Open Data Hub Südtirol (LTS)"]
    assert l["lat"] == pytest.approx(46.719, abs=0.01) and l["lage_von"] == "Open Data Hub Südtirol (LTS)"
    assert l["ohne_datum"] and l["laenge_km"]
    # Loipen nur im ODH, in einem Gebiet mit Bericht von Dolomiti NordicSki: Hinweis (P22 AK 3)
    seeloipe = next(l for l in loipen if l["name"] == "Seeloipe")
    assert seeloipe["nicht_im_bericht"] == "Dolomiti NordicSki (Loipenstatus)"
    # Westen nur ueber den ODH: kein Hinweis, eigene Lage
    martell = [l for l in loipen if l["quelle"]["name"].startswith("Open Data Hub") and l["lat"] and l["lon"] < 11]
    assert martell and not any(l["nicht_im_bericht"] for l in martell)
    # Cortina/Comelico nur von Dolomiti NordicSki, ohne Startpunkt, aber im Gebiet
    cortina = next(g for g in _lies(suedtirol_site, regionen["cortina-comelico"]["datei"])["gebiete"]
                   if g["slug"] == "cortina")
    assert cortina["loipen"] and cortina["lat"] and cortina["namen"]["it"] == "Cortina d'Ampezzo"


@pytest.mark.req("U31", ak=1)
def test_u31_italienische_gebiete_nennen_maut_und_vignette():
    for g in gebiete_yaml()["gebiete"]:
        if g["region"] in SUEDTIROL | {"cortina-comelico"}:
            assert "Vignette" in g["grenzinfo"] and "Maut" in g["grenzinfo"], g["slug"]
            assert g["namen"]["it"], g["slug"]
