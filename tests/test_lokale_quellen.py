"""Regionale Loipenberichte vor tirol.at (P21, E-16) und Doppeleintraege (D18).

Schnappschuesse vom 13.11.2026 (Workflow Schnappschuss, Runde 6 und 7):
- tests/fixtures/tannheimer/2026-11-13/loipenmanager.json: tourinfra-Loipenmanager des Tannheimer Tals
- tests/fixtures/seefeld/2026-11-13/loipenbericht.html: Loipenbericht der Olympiaregion Seefeld
Am 13.11. war im Tannheimer Tal alles geschlossen (tannheimertal.com: "Geöffnete Loipen 0 / 27"),
waehrend tirol.at sieben alte Doppeleintraege als geoeffnet fuehrte.
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen import generator
from loipen.adapters.seefeld import SeefeldAdapter, laengen
from loipen.adapters.tourinfra import TourinfraAdapter, _name
from loipen.dubletten import Eintrag, finde_dubletten, gleich, schluessel
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import FIXTURES, SEITEN_QUELLEN, FixtureFetcher, lade_alle_fixtures

JETZT = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def quelle(key: str) -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == key)


def lauf(key: str, adapter):
    q = quelle(key)
    return adapter.run(q["base_url"], q["config"], FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN[key]))


# ---------- Tannheimer Tal (tourinfra) ----------

@pytest.mark.req("P21", ak=1)
def test_p21_tannheimer_tal_aus_dem_loipenbericht_des_verbands():
    r = lauf("tannheimer", TourinfraAdapter())
    roh = json.loads((FIXTURES / "tannheimer/2026-11-13/loipenmanager.json").read_text(encoding="utf-8"))
    assert len(roh) == 22
    assert len(r.loipen) == 21  # ein Eintrag ohne Felder wird gemeldet und uebersprungen
    assert any("uebersprungen" in w for w in r.warnungen)
    assert not [w for w in r.warnungen if "gebiet_map" in w]  # jeder Ort ist zugeordnet
    assert {d.gebiet_slug for d in r.loipen} == {"tannheimer-tal"}
    # am 13.11. alles geschlossen, je Technik getrennt gemeldet
    assert {d.status for d in r.loipen} == {Status.GESCHLOSSEN}
    assert {d.status_klassisch for d in r.loipen} == {Status.GESCHLOSSEN}
    vils = next(d for d in r.loipen if "Vilsalpsee" in d.name and d.name.startswith("Nr"))
    assert vils.name == "Nr. 2 Rundloipe Vilsalpsee"  # Laenge steht nicht mehr im Namen
    assert vils.laenge_km == 12.5
    assert vils.technik == Technik.BEIDES
    # Streckenverlauf fuer die Karte (U36), ausgeduennt
    assert vils.verlauf and 2 < len(vils.verlauf) <= 120
    assert vils.lat == pytest.approx(47.5, abs=0.01)
    # geschlossen: kein Praeparierdatum ("---"), also Status ohne Datum
    assert all(d.quelle_aktualisiert_at is None for d in r.loipen)


@pytest.mark.req("P21", ak=1)
def test_p21_tannheimer_praeparierdatum_wird_uebernommen_wenn_gemeldet():
    """Im November meldet niemand ein Datum; das Format ist dasselbe wie im Chiemgau (dd.mm.yyyy HH:MM)."""
    roh = json.loads((FIXTURES / "tannheimer/2026-11-13/loipenmanager.json").read_text(encoding="utf-8"))
    eintrag = dict(roh["1"], status_text="Gespurt", status_klassisch_text="Gespurt", praep_datum="14.12.2026 07:30",
                   prep_km_klassisch="24.1")
    q = quelle("tannheimer")
    r = TourinfraAdapter().run(q["base_url"], q["config"], FixtureFetcher(
        "tannheimer", q["base_url"], ersetze={"inc/ajax.php?ajaxtype=getLoipenmanager": json.dumps({"1": eintrag})}))
    d = r.loipen[0]
    assert d.status == Status.OFFEN
    assert d.quelle_aktualisiert_at.strftime("%d.%m.%Y %H:%M") == "14.12.2026 07:30"
    assert d.gespurt_klassisch_km == 24.1


def test_tourinfra_name_ohne_laenge():
    assert _name("Nr.1 Rundlopie Ski-Trail  - 24,1 km") == "Nr.1 Rundlopie Ski-Trail"
    assert _name("Nr. 4 Expertenrunde - 5 km") == "Nr. 4 Expertenrunde"
    assert _name("Nr. 7 Grenzland-Loipe klassisch + skating | 5,2 km") == "Nr. 7 Grenzland-Loipe klassisch + skating"
    assert _name("Zubringer Schmieden/Vilsalpsee") == "Zubringer Schmieden/Vilsalpsee"


# ---------- Olympiaregion Seefeld ----------

@pytest.mark.req("P21", ak=2)
def test_p21_seefeld_loipenbericht_mit_gespurten_km():
    r = lauf("seefeld", SeefeldAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 49  # 10 Seefeld, 20 Leutasch, 10 Moesern bis Reith, 5 Uebungsgelaende, 4 Runden
    namen = [d.name for d in r.loipen]
    assert len(set(namen)) == len(namen)  # die barrierefreien Wiederholungen fehlen
    snow = next(d for d in r.loipen if d.name == "SnowFactory Loipe Seefeld")
    assert (snow.status, snow.gespurt_gesamt_km, snow.laenge_km) == (Status.OFFEN, 1.0, 1.0)
    assert snow.schwierigkeit == Schwierigkeit.MITTEL
    assert [d.name for d in r.loipen if d.status == Status.OFFEN] == ["SnowFactory Loipe Seefeld"]
    a2 = next(d for d in r.loipen if d.name.startswith("A2 "))
    assert (a2.gebiet_slug, a2.laenge_km, a2.gespurt_gesamt_km, a2.technik) == ("leutasch", 2.8, 0.0, Technik.BEIDES)
    assert next(d for d in r.loipen if "Alpenbad Leutasch" in d.name).gebiet_slug == "leutasch"
    assert next(d for d in r.loipen if d.name == "B1 - Mösern").gebiet_slug == "seefeld"
    assert next(d for d in r.loipen if d.name.startswith("C1 ")).schwierigkeit == Schwierigkeit.SCHWER
    assert all(d.lat is None for d in r.loipen)  # die Lage kommt von tirol.at (D18 AK 2)


def test_seefeld_laengen():
    assert laengen("0 m / 2,80 km") == (0.0, 2.8)
    assert laengen("1,00 km / 1,00 km") == (1.0, 1.0)
    assert laengen("0 m / 500 m") == (0.0, 0.5)
    assert laengen("0 m") == (0.0, None)


def test_seefeld_geaenderter_aufbau_gibt_warnung():
    q = quelle("seefeld")
    r = SeefeldAdapter().run(q["base_url"], q["config"], FixtureFetcher(
        "seefeld", q["base_url"], ersetze={"de/loipenbericht.html": "<html><main><h2>Neu</h2></main></html>"}))
    assert r.loipen == [] and r.warnungen


# ---------- Dubletten (D18) ----------

def e(i, name, quelle, rang, lat=None, lon=None, gebiet="tannheimer-tal", gname="Tannheimer Tal", region="ausserfern"):
    return Eintrag(i, name, quelle, rang, gebiet, gname, lat, lon, region)


@pytest.mark.req("D18", ak=1)
def test_d18_doppeleintraege_einer_quelle_erscheinen_einmal():
    a = e(1, "Rundloipe Grän", "tirol", 3, 47.4976, 10.55388)
    b = e(2, "Rundloipe Grän", "tirol", 3, 47.4976, 10.55388)
    c = e(3, "Rundloipe Grän", "tirol", 3, 47.52, 10.60)  # gleicher Name, aber 4 km weg
    d = e(4, "KU2 Weissach II", "tirol", 3, 47.4976, 10.55388)
    assert finde_dubletten([a, b, c, d]) == {2: 1}
    assert not gleich(e(5, "KU1 Weissach I", "tirol", 3, 47.58, 12.17), e(6, "KU2 Weissach II", "tirol", 3, 47.58, 12.17))


@pytest.mark.req("P21", ak=3)
def test_p21_verbandsbericht_fuehrt_vor_tirol_at():
    verband = e(1, "Nr.1 Rundlopie Ski-Trail", "tannheimer", 2, 47.496625, 10.51383)
    tirol = [e(2, "Rundloipe Ski-Trail", "tirol", 3, 47.49662, 10.51383),
             e(3, "Rundloipe Ski-Trail", "tirol", 3, 47.49662, 10.51383)]
    assert finde_dubletten([*tirol, verband]) == {2: 1, 3: 1}
    assert schluessel("Nr. 2 Rundloipe Vilsalpsee - 12,5 km") == schluessel("Rundloipe Vilsalpsee")


@pytest.mark.req("D18", ak=2)
def test_d18_ohne_koordinate_gleiche_woerter_in_der_region():
    seefeld = e(1, "C9 - Plaik", "seefeld", 2, gebiet="leutasch", gname="Leutasch", region="seefeld-mieming")
    tirol = e(2, "Plaik Loipe (C9)", "tirol", 3, 47.37, 11.15, gebiet="seefeld", gname="Seefeld", region="seefeld-mieming")
    assert gleich(seefeld, tirol)
    andere_region = e(3, "Plaik Loipe (C9)", "tirol", 3, 47.37, 11.15, gebiet="x", gname="X", region="anders")
    assert not gleich(seefeld, andere_region)
    # ein einzelnes gemeinsames Wort reicht nicht
    assert not gleich(e(4, "Waldloipe", "seefeld", 2, gebiet="leutasch", gname="Leutasch", region="seefeld-mieming"),
                      e(5, "B14 - Waldloipe Alpenbad", "tirol", 3, 47.37, 11.15, gebiet="leutasch", gname="Leutasch",
                        region="seefeld-mieming"))


# ---------- Generator: was die Seite bekommt ----------

@pytest.fixture(scope="module")
def site(engine, tmp_path_factory):
    from sqlalchemy.orm import Session

    ziel = tmp_path_factory.mktemp("site_lokal")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, ziel, JETZT)
        s.close()
        trans.rollback()
    return ziel


def gebiet(site, slug):
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    for r in index["regionen"]:
        for g in json.loads((site / r["datei"]).read_text(encoding="utf-8"))["gebiete"]:
            if g["slug"] == slug:
                return g
    raise KeyError(slug)


@pytest.mark.req("P21", ak=3)
def test_p21_tannheimer_tal_ohne_falsch_offene_tirol_eintraege(site):
    g = gebiet(site, "tannheimer-tal")
    offen = [l["name"] for l in g["loipen"] if l["status"] in ("offen", "eingeschraenkt")]
    assert offen == []  # vorher: sieben alte tirol.at-Eintraege offen
    gaicht = next(l for l in g["loipen"] if "Gaichtpass" in l["name"])
    assert gaicht["quelle"]["name"].startswith("Tourismusverband Tannheimer Tal")
    assert gaicht["status"] == "geschlossen"
    # tirol.at steht einmal dabei, mit seinem abweichenden Status
    assert [(a["quelle"], a["status"]) for a in gaicht["auch_bei"]] == [("Tirol Werbung (tirol.at)", "offen")]
    assert g["tourist_url"].startswith("https://www.tannheimertal.com")


@pytest.mark.req("D18", ak=1)
def test_d18_keine_doppelten_namen_in_tannheimer_tal(site):
    namen = [l["name"] for l in gebiet(site, "tannheimer-tal")["loipen"]]
    assert len(namen) == len(set(namen))


@pytest.mark.req("D18", ak=2)
def test_d18_seefeld_loipe_bekommt_lage_von_tirol(site):
    l = next(l for l in gebiet(site, "leutasch")["loipen"] if l["name"] == "A2 - Snowfarmingloipe Leutasch")
    assert l["quelle"]["name"].startswith("Olympiaregion Seefeld")
    assert l["lat"] == pytest.approx(47.373, abs=0.001)
    assert l["gespurt_km"] == 0.0 and l["laenge_km"] == 2.8


@pytest.mark.req("U36", ak=1)
def test_u36_index_nennt_regionen_mit_strecken(site):
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    mit = {r["slug"]: r["strecken_anzahl"] for r in index["regionen"] if r["strecken_anzahl"]}
    assert set(mit) == {"chiemgau", "ausserfern"}  # Chiemgau und Tannheimer Tal (tourinfra)
    assert mit["ausserfern"] >= 20


@pytest.mark.req("U36", ak=2)
def test_u36_tiroler_loipe_nennt_den_grund_ohne_strecke(site):
    l = next(l for l in gebiet(site, "kufstein")["loipen"])
    assert "robots.txt" in l["strecke_hinweis"]
    vils = next(l for l in gebiet(site, "tannheimer-tal")["loipen"] if "Vilsalpsee" in l["name"])
    assert vils["strecke_hinweis"] is None
