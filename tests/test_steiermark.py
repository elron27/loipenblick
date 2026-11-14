"""Steiermark und Lungau (E-22): Tourenportal von Steiermark Tourismus (P30), Loipennetze mit Zaehler (U43 AK 4).

Schnappschuesse vom 14.11.2026 (Workflow Schnappschuss, Runden 17 und 18):
- tests/fixtures/steiermark/2026-11-14/tourenportal-langlauf-p1..p7.html: Tourenportal, Kategorie Langlauf,
  "89 Ergebnisse", 16 je Seite; Seite 7 ist leer. Mitte November: 81 geschlossen, 5 ohne Meldung,
  in Ramsau 2 geoeffnet (Nachtloipe, Rollerstrecke) und 1 teilweise (Stadionloipe).
"""

import json
import re
from pathlib import Path

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.steiermark import steiermark_teaser
from loipen.dubletten import Eintrag, finde_dubletten
from loipen.generator.daten import _netz
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status
from tests.helpers import SEITEN_QUELLEN, STEIERMARK_LISTE, FixtureFetcher
from tests.test_website_ui import JETZT, basis, browser, seite  # noqa: F401  (Fixtures)

GEOSPHERE = Path(__file__).resolve().parent / "fixtures" / "geosphere" / "2026-11-12"
NEUE_REGIONEN = {"ausseerland", "gesaeuse", "murau", "murtal", "hochsteiermark", "oststeiermark", "lipizzanerheimat",
                 "lungau"}


def quelle(key: str) -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == key)


def lauf(key: str, config: dict | None = None, ersetze: dict | None = None):
    q = quelle(key)
    fetcher = FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN.get(key), ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], config or q["config"], fetcher), fetcher


def gebiete() -> tuple[dict, dict]:
    daten = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    return {g["slug"]: g for g in daten["gebiete"]}, {r["slug"]: r for r in daten["regionen"]}


# ---------- P30: Tourenportal der Steiermark ----------

@pytest.mark.req("P30", ak=1)
def test_p30_alle_seiten_mit_status_laenge_und_startort():
    erg, fetcher = lauf("steiermark")
    assert erg.warnungen == []
    assert len(erg.loipen) == 89 and len({d.source_key for d in erg.loipen}) == 89
    assert len(fetcher.abgerufen) == 6  # Seite 7 waere leer: nach 89 von 89 Ergebnissen ist Schluss
    assert fetcher.abgerufen[1].endswith("tourCategory=46459526&page=2")
    status = {s: sum(1 for d in erg.loipen if d.status == s) for s in Status}
    assert status == {Status.GESCHLOSSEN: 81, Status.UNBEKANNT: 5, Status.OFFEN: 2, Status.EINGESCHRAENKT: 1}
    kulm = next(d for d in erg.loipen if d.name == "Kulm Loipe (M1)")
    assert (kulm.gebiet_slug, kulm.laenge_km, kulm.schwierigkeit, kulm.startpunkt) == (
        "bad-mitterndorf", 5.6, Schwierigkeit.LEICHT, "Bad Mitterndorf")
    assert kulm.status_rohtext == "Geschlossen" and kulm.quelle_aktualisiert_at is None
    assert kulm.source_url.startswith("https://www.steiermark.com/de/") and kulm.source_url.endswith("_tour_1430746")
    stadion = next(d for d in erg.loipen if d.name == "Stadionloipe")
    assert stadion.status == Status.EINGESCHRAENKT and stadion.gebiet_slug == "ramsau-am-dachstein"
    hebalm = next(d for d in erg.loipen if d.name == "Hebalm Runde")
    assert hebalm.status == Status.UNBEKANNT and hebalm.status_rohtext is None  # ohne Badge = keine Meldung
    # Lungau: die Prebersee-Loipe startet in Tamsweg
    preber = next(d for d in erg.loipen if d.name == "Höhenloipe Prebersee")
    assert preber.gebiet_slug == "prebersee"


@pytest.mark.req("P30", ak=1)
def test_p30_badges_der_seite_sind_bekannt():
    f = FixtureFetcher("steiermark", quelle("steiermark")["base_url"], seiten=SEITEN_QUELLEN["steiermark"])
    seite1 = f.seite("2026-11-14/tourenportal-langlauf-p1.html")
    # Die Seite definiert ihre Badges im CSS; jeder davon hat eine Zuordnung
    from loipen.adapters.steiermark import BADGE
    im_css = set(re.findall(r"\.icon-path-([a-z-]+):before", seite1))
    assert im_css == set(BADGE)
    offen = seite1.replace("icon icon-path-closed me-2", "icon icon-path-open me-2", 1)
    assert steiermark_teaser(offen)[3]["badge"] == "open"


@pytest.mark.req("P30", ak=2)
def test_p30_gebiet_aus_dem_startort_und_warnungen():
    erg, _ = lauf("steiermark")
    g, r = gebiete()
    assert {d.gebiet_slug for d in erg.loipen} <= set(g)
    assert {r[g[d.gebiet_slug]["region"]]["bundesland"] for d in erg.loipen} == {"Steiermark", "Salzburg"}
    assert next(d for d in erg.loipen if d.name == "Seerunde und Grenzloipe").gebiet_slug == "turracher-hoehe"
    # unbekannter Startort: Warnung, kein falsches Gebiet
    cfg = dict(quelle("steiermark")["config"])
    cfg["gebiet_map"] = {k: v for k, v in cfg["gebiet_map"].items() if k != "Wildalpen"}
    erg2, _ = lauf("steiermark", config=cfg)
    assert len(erg2.loipen) == 86 and not [d for d in erg2.loipen if "Hinterwildalpen" in d.name]
    assert any("Wildalpen" in w for w in erg2.warnungen)
    # weniger Loipen als genannt (eine Seite fehlt) und eine leere Liste
    p3 = f"{STEIERMARK_LISTE}&page=3"
    leer = FixtureFetcher("steiermark", quelle("steiermark")["base_url"],
                          seiten=SEITEN_QUELLEN["steiermark"]).seite("2026-11-14/tourenportal-langlauf-p7.html")
    erg3, _ = lauf("steiermark", ersetze={p3: leer})
    assert len(erg3.loipen) == 32 and any("89 Ergebnisse genannt, 32 gelesen" in w for w in erg3.warnungen)
    erg4, _ = lauf("steiermark", ersetze={STEIERMARK_LISTE: "<html><body>Neu</body></html>"})
    assert erg4.loipen == [] and "Seitenaufbau" in erg4.warnungen[0]


@pytest.mark.req("P30", ak=2)
def test_p30_neue_gebiete_mit_lage_region_und_wetterstation():
    g, r = gebiete()
    neu = [x for x in g.values() if x["region"] in NEUE_REGIONEN or x["slug"] in {
        "schladming", "haus-im-ennstal", "groebminger-land", "grimming-donnersbachtal"}]
    assert len(neu) == 25
    mit_schnee = set()
    for datei in GEOSPHERE.glob("klima-v2-1d_*.json"):
        if "metadata" in datei.name:
            continue
        for f in json.loads(datei.read_text())["features"]:
            p = f["properties"]
            if any(v is not None for k in ("sh", "sh_manu") for v in p["parameters"].get(k, {}).get("data", [])):
                mit_schnee.add(str(p["station"]))
    for x in neu:
        assert x["lat"] and x["lon"] and x["hoehe_m"] and x["tourist_url"].startswith("https://"), x["slug"]
        assert "Vignette" in x["grenzinfo"], x["slug"]
        assert r[x["region"]]["land"] == "AT"
        assert x["wetterstation"]["dienst"] == "geosphere" and x["wetterstation"]["id"] in mit_schnee, x["slug"]
    assert r["lungau"]["bundesland"] == "Salzburg"


@pytest.mark.req("P30", ak=3)
def test_p30_ramsau_einmal_beim_tourinfra_loipenmanager():
    st = [d for d in lauf("steiermark")[0].loipen if d.gebiet_slug == "ramsau-am-dachstein"]
    ra = lauf("ramsau")[0].loipen
    eintraege, i = [], 0
    for key, liste in (("steiermark", st), ("ramsau", ra)):
        for d in liste:
            i += 1
            eintraege.append(Eintrag(i, d.name, key, int(quelle(key)["rang"]), d.gebiet_slug, "Ramsau am Dachstein",
                                     d.lat, d.lon, "schladming-dachstein"))
    verdeckt = finde_dubletten(eintraege)
    nach_id = {e.id: e for e in eintraege}
    paare = {nach_id[a].name: nach_id[b].name for a, b in verdeckt.items()}
    assert all(nach_id[a].quelle == "steiermark" and nach_id[b].quelle == "ramsau" for a, b in verdeckt.items())
    assert paare["Weltcuploipe"] == "Weltcup Loipe"  # zusammengeschrieben = getrennt
    assert paare["Nachtloipe"] == "Nachtloipe" and paare["Kulmloipe"] == "Kulmloipe"
    assert len(paare) == 13  # nur Rollerstrecke & Biathlon-Stadion und Steirerloipe Vorberg bleiben eigene Eintraege
    assert quelle("ramsau")["rang"] < quelle("steiermark")["rang"]


# ---------- U43 AK 4: Loipennetze, die nur gezaehlt sind ----------

@pytest.mark.req("U43", ak=4)
def test_u43_netz_zaehler_aus_dem_rohtext():
    assert _netz('{"ort": "Hermagor", "offen": 3, "alle": 9}') == {"offen": 3, "alle": 9}
    assert _netz('{"ort": "Dellach", "offen": 0, "alle": 0}') is None  # nichts gemeldet
    assert _netz("geschlossen; Loipe") is None and _netz(None) is None and _netz('{"offen": 5, "alle": 2}') is None


@pytest.mark.req("U43", ak=4)
def test_u43_loipennetz_zaehlt_mit_allen_loipen(seite):
    seite.open("#/gebiet/hermagor")
    t = seite.locator("#rahmen").inner_text()
    assert re.search(r"LOIPEN OFFEN\s+0 von 9", t, re.IGNORECASE), t  # Wintersportbericht: "Hermagor 0 / 9"
    assert "nur als Zahl" in seite.locator("#nurgezaehlt").inner_text()
    seite.open("#/loipen?region=nassfeld-gailtal")
    rahmen = seite.locator(".rahmen").all_inner_texts()
    assert rahmen and re.search(r"Region gesamt: 0 von \d{2,} Loipen offen", rahmen[0]), rahmen
