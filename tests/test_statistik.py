"""Saisonstatistik (loipen/statistik.py): U19, U37, U38, U39.

Die Regeln werden zuerst ohne Datenbank an erfundenen Tagesreihen geprueft, danach einmal mit den
Beispielseiten und einer nachgespielten Woche Historie bis in die erzeugte JSON-Datei.
"""

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator
from loipen.adapters.stammdaten import KEIN_ZUSTAND
from loipen.models import Loipe, Quelle, Zustand
from loipen.statistik import (
    LoipeInfo,
    Struktur,
    auswerten,
    beispiel_statistik,
    tagesstatus,
    winter_jahr,
    winter_name,
)
from loipen.upload import HASH_DATEI, _verweise
from loipen.zustand import speichere_zustand
from tests.helpers import lade_alle_fixtures

B = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=B)


def z(status, von, bis=None, rohtext=None):
    return Zustand(status=status, abgerufen_at=von, zuletzt_bestaetigt_at=bis or von, rohtext=rohtext)


def t(tag, stunde=12):
    return datetime(2026, 11, tag, stunde, tzinfo=B)


# ---------- Winter und Tagesstatus ----------

@pytest.mark.req("U19", ak=2)
def test_u19_winter_vom_1_november_bis_30_april():
    assert winter_jahr(date(2026, 11, 1)) == 2026
    assert winter_jahr(date(2027, 4, 30)) == 2026
    assert winter_jahr(date(2027, 5, 1)) is None
    assert winter_jahr(date(2026, 10, 31)) is None
    assert winter_name(2026) == "2026/27" and winter_name(2099) == "2099/00"


@pytest.mark.req("U37", ak=1)
def test_u37_tag_zaehlt_mit_dem_besten_status_luecken_bleiben_leer():
    s = tagesstatus([
        z("geschlossen", t(10, 7), t(12, 7)),
        z("offen", t(12, 17), t(13, 7)),     # am 12. erst geschlossen, abends offen: der Tag ist befahrbar
        z("unbekannt", t(16, 7), t(16, 17)),  # 14. und 15.: kein Abruf
    ])
    assert s == {date(2026, 11, 10): "geschlossen", date(2026, 11, 11): "geschlossen", date(2026, 11, 12): "offen",
                 date(2026, 11, 13): "offen", date(2026, 11, 16): "unbekannt"}


@pytest.mark.req("U37", ak=1)
def test_u37_zeit_zaehlt_nach_berliner_tag_und_stammdaten_zaehlen_nicht():
    spaet = datetime(2026, 11, 10, 23, 30, tzinfo=ZoneInfo("UTC"))  # in Berlin schon der 11.
    assert tagesstatus([z("offen", spaet)]) == {date(2026, 11, 11): "offen"}
    assert tagesstatus([z("unbekannt", t(10), rohtext=KEIN_ZUSTAND)]) == {}


# ---------- Auswertung ----------

def struktur() -> Struktur:
    st = Struktur(regionen={"tal": ["a", "b"]}, gebiete={"a": {"name": "Alm", "region": "tal"}, "b": {"name": "Berg", "region": "tal"}})
    st.loipen = {1: LoipeInfo(1, "Ort", "a"), 2: LoipeInfo(2, "Ort", "a"), 3: LoipeInfo(3, "Land", "b"),
                 4: LoipeInfo(4, "Land", "a", unbestaetigt=True), 5: LoipeInfo(5, "Land", None)}
    st.paare = [(1, 5)]
    return st


def tage(von: date, status: list[str | None]) -> dict[date, str]:
    return {von + timedelta(days=i): s for i, s in enumerate(status) if s}


N1 = date(2026, 11, 1)


def winter_2026(status, schnee=None, heute=date(2026, 11, 6)):
    erg = auswerten(status, schnee or {}, struktur(), heute)
    return erg, erg["winter"][0]


@pytest.mark.req("U19", ak=1)
def test_u19_tage_erster_und_letzter_befahrbarer_tag_pro_loipe():
    _, w = winter_2026({1: tage(N1, ["geschlossen", "offen", "eingeschraenkt", None, "offen", "unbekannt"])})
    assert w["name"] == "2026/27" and w["bis"] == "2026-11-06" and w["tage"] == 6
    assert w["loipen"]["1"] == {"tage": 3, "offen": 2, "beobachtet": 4, "erster": "2026-11-02", "letzter": "2026-11-05",
                                "unbestaetigt": False}


@pytest.mark.req("U37", ak=2)
def test_u37_reihe_pro_gebiet_und_region_mit_luecken():
    _, w = winter_2026({
        1: tage(N1, ["geschlossen", "offen", None, None, "offen"]),
        2: tage(N1, ["geschlossen", "offen", None, None, "geschlossen"]),
        3: tage(N1, [None, "offen", "offen"]),
    }, schnee={"a": {N1: 12.4, N1 + timedelta(days=1): 20}})
    a = w["gebiete"]["a"]
    assert a["befahrbar"] == [0, 2, None, None, 1, None]
    assert (a["tage"], a["beobachtet"], a["erster"], a["letzter"], a["max"]) == (2, 3, "2026-11-02", "2026-11-05", 2)
    assert a["schnee"][:3] == [12, 20, None]
    assert w["regionen"]["tal"]["befahrbar"] == [0, 3, 1, None, 1, None]
    assert w["gesamt"]["befahrbar"] == w["regionen"]["tal"]["befahrbar"]
    assert w["gesamt"]["tage"] == 3


@pytest.mark.req("U38", ak=3)
def test_u38_unbestaetigte_loipe_zaehlt_nicht_fuers_gebiet():
    _, w = winter_2026({4: tage(N1, ["offen", "offen"])})
    assert w["loipen"]["4"]["unbestaetigt"] is True and w["loipen"]["4"]["tage"] == 2
    assert "a" not in w["gebiete"]  # keine bestaetigte Loipe mit Daten, keine Schneewerte


@pytest.mark.req("U19", ak=3)
def test_u19_vorwinter_steht_als_eigener_winter_daneben():
    erg = auswerten({1: {date(2025, 12, 24): "offen", date(2026, 11, 2): "offen"}}, {}, struktur(), date(2026, 11, 3))
    assert [w["name"] for w in erg["winter"]] == ["2026/27", "2025/26"]
    assert erg["winter"][1]["tage"] == 181 and erg["winter"][1]["loipen"]["1"]["erster"] == "2025-12-24"


@pytest.mark.req("U39", ak=1)
def test_u39_tage_mit_daten_seit_dem_ersten_abruf():
    _, w = winter_2026({1: tage(N1 + timedelta(days=2), ["offen", None, "unbekannt", "offen"])})
    ort = next(q for q in w["quellen"] if q["name"] == "Ort")
    assert (ort["tage_mit_daten"], ort["tage_moeglich"], ort["erster"]) == (3, 4, "2026-11-03")


@pytest.mark.req("U39", ak=[2, 3])
def test_u39_uebereinstimmung_ueber_dubletten():
    _, w = winter_2026({
        1: tage(N1, ["offen", "offen", "geschlossen", "eingeschraenkt", "unbekannt"]),
        5: tage(N1, ["eingeschraenkt", "geschlossen", "geschlossen", None, "offen"]),  # Dublette bei "Land"
        3: tage(N1, ["offen"]),
    })
    q = {x["name"]: x for x in w["quellen"]}
    # verglichen: Tag 1 (beide befahrbar), 2 (verschieden), 3 (beide zu); Tag 4 fehlt bei 5, Tag 5 unbekannt bei 1
    assert q["Ort"]["vergleich"] == {"tage": 3, "gleich": 2}
    assert q["Land"]["paare"] == [{"mit": "Ort", "tage": 3, "gleich": 2, "loipen": 1}]
    st = struktur()
    st.paare = []
    ohne = auswerten({1: tage(N1, ["offen"])}, {}, st, date(2026, 11, 2))["winter"][0]
    assert next(x for x in ohne["quellen"] if x["name"] == "Ort")["vergleich"] == {"tage": 0, "gleich": 0}


def test_ausserhalb_der_saison_ohne_daten_gibt_es_keinen_winter():
    assert auswerten({}, {}, struktur(), date(2026, 7, 1))["winter"] == []


# ---------- Mit Datenbank und Generator ----------

@pytest.fixture
def site_mit_historie(session, tmp_path):
    """Beispielseiten am 9.11., dann eine Woche, in der eine Loipe zwei Tage offen ist."""
    lade_alle_fixtures(session, JETZT)
    loipe = session.scalars(select(Loipe).join(Quelle).where(Quelle.key == "bayrischzell").order_by(Loipe.name)).first()
    for tag, status in ((10, "geschlossen"), (11, "offen"), (12, "offen"), (13, "geschlossen")):
        speichere_zustand(session, loipe, {"status": status}, datetime(2026, 11, tag, 7, tzinfo=B))
    jetzt = datetime(2026, 11, 13, 18, tzinfo=B)
    generator.erzeuge(session, tmp_path, jetzt)
    return tmp_path, loipe


@pytest.mark.req("U19", ak=1)
@pytest.mark.req("U37", ak=2)
def test_u37_generator_schreibt_statistik_mit_inhalts_hash(site_mit_historie):
    site, loipe = site_mit_historie
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    assert set(index["statistik"]) == {"datei", "beispiel"}
    for rel in index["statistik"].values():
        assert HASH_DATEI.match(rel) and (site / rel).exists()
    assert set(index["statistik"].values()) <= _verweise(index)  # B21: der Upload kennt die Dateien
    st = json.loads((site / index["statistik"]["datei"]).read_text(encoding="utf-8"))
    w = st["winter"][0]
    assert st["beispiel"] is False and w["name"] == "2026/27" and w["bis"] == "2026-11-13" and w["tage"] == 13
    s = w["loipen"][str(loipe.id)]
    assert (s["tage"], s["offen"], s["erster"], s["letzter"]) == (2, 2, "2026-11-11", "2026-11-12")
    g = w["gebiete"][loipe.gebiet.slug]["befahrbar"]
    assert g[:8] == [None] * 8 and g[10] >= 1 and g[11] >= 1
    assert w["quellen"] and all(0 < q["tage_mit_daten"] <= q["tage_moeglich"] for q in w["quellen"])


@pytest.mark.req("U37", ak=5)
def test_u37_beispielwinter_ist_gekennzeichnet_und_gleichbleibend(session):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    from loipen.generator.daten import baue
    from loipen.konfig import CONFIG_DIR

    daten = baue(session, JETZT, CONFIG_DIR)
    a, b = beispiel_statistik(session, daten, JETZT), beispiel_statistik(session, daten, JETZT)
    a["erzeugt"] = b["erzeugt"] = None
    assert a == b
    assert a["beispiel"] is True and [w["name"] for w in a["winter"]] == ["2025/26"]
    w = a["winter"][0]
    assert w["tage"] == 181 and 30 < w["gesamt"]["tage"] < 181
    assert any(q["vergleich"]["tage"] for q in w["quellen"])
