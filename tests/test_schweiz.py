"""Schweiz, Liechtenstein, Gastein, Ramsau (E-20): Schweiz Tourismus (P29), tourinfra-Regionen (P26).

Schnappschuesse vom 13.11.2026 (Workflow Schnappschuss, Runden 10 und 11):
- tests/fixtures/myswitzerland/2026-11-13/<ort>-<id>.html: 110 Ortsseiten von snow.myswitzerland.com
  (Liste der 126 Langlauforte: tests/fixtures/recherche-2026-11-13/myswitzerland-liste/p1..p5.html).
  Mitte November melden die meisten Orte "geschlossen", Davos, Val Muestair und Malbun schon "gut".
- tests/fixtures/<engadin|davos-klosters|goms|gastein|ramsau|seefeld-tourinfra>/2026-11-13/loipenmanager.json:
  tourinfra-Loipenmanager (gleiches Format wie Chiemgau).
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.schweiz import MySwitzerlandAdapter, lese_loipen, lese_netz, ort_daten, stand
from loipen.adapters.tourinfra import TourinfraAdapter
from loipen.konfig import CONFIG_DIR, lade_yaml, pruefe
from loipen.models import Status, Technik
from tests.helpers import FIXTURES, SEITEN_QUELLEN, FixtureFetcher

MYS = FIXTURES / "myswitzerland/2026-11-13"
TOURINFRA_CH = ("engadin", "davos-klosters", "goms")


def sources() -> dict:
    return lade_yaml(CONFIG_DIR / "sources.yaml")


def gebiete_yaml() -> dict:
    return lade_yaml(CONFIG_DIR / "gebiete.yaml")


def quelle(key: str) -> dict:
    return next(q for q in sources()["quellen"] if q["key"] == key)


def gebiete() -> dict[str, dict]:
    return {g["slug"]: g for g in gebiete_yaml()["gebiete"]}


def regionen() -> dict[str, dict]:
    return {r["slug"]: r for r in gebiete_yaml()["regionen"]}


def lauf(key: str, ersetze: dict | None = None):
    q = quelle(key)
    fetcher = FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN.get(key), ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], q["config"], fetcher), fetcher


def seite(name: str) -> str:
    return next(MYS.glob(f"{name}-[0-9]*.html")).read_text(encoding="utf-8")


# ---------- P29: Schweiz Tourismus ----------

@pytest.mark.req("P29", ak=1)
def test_p29_alle_orte_mit_langlauf_werden_gelesen():
    erg, fetcher = lauf("myswitzerland")
    orte = quelle("myswitzerland")["config"]["orte"]
    assert len(fetcher.abgerufen) == len(orte) == 100  # eine Seite je Ort
    assert erg.warnungen == []
    assert len(erg.loipen) == 340
    g, r = gebiete(), regionen()
    assert {r[g[d.gebiet_slug]["region"]]["land"] for d in erg.loipen} == {"CH", "LI"}
    assert len({d.gebiet_slug for d in erg.loipen}) == 94
    assert len({d.source_key for d in erg.loipen}) == len(erg.loipen)
    # Orte, die tourinfra genauer liefert, sind nicht doppelt abgefragt
    assert not [o for o in orte if re.search(r"/(davos|klosters|goms|engadin-st-moritz|st-moritz|\w+engadin)-\d+/$",
                                                o["pfad"])]
    # jede Loipe hat den Stand der Ortsseite (Ortszeit)
    assert all(d.quelle_aktualisiert_at is not None for d in erg.loipen)


@pytest.mark.req("P29", ak=2)
def test_p29_klassisch_und_skating_werden_zusammengefuehrt():
    s = seite("leukerbad")
    zeilen = lese_loipen(s)
    assert zeilen and {z["typ"] for z in zeilen} <= {"Klassisch", "Skating", "Klassisch und Skating"}
    erg, _ = lauf("myswitzerland")
    san = [d for d in erg.loipen if d.gebiet_slug == "san-bernardino"]
    assert san and all(d.status == Status.GESCHLOSSEN for d in san)
    beide = [d for d in erg.loipen if d.technik == Technik.BEIDES]
    assert beide and all(d.status_klassisch is not None and d.status_skating is not None for d in beide)
    # Hundeloipen fallen weg
    assert not [d for d in erg.loipen if "hunde" in (d.status_rohtext or "").lower()]
    # Zustand "gut" ist offen, "Saisonschluss" geschlossen, "keine Meldung" unbekannt; nichts ist unbekannt geblieben
    assert {d.status for d in erg.loipen} == {Status.OFFEN, Status.GESCHLOSSEN, Status.UNBEKANNT}
    assert not [b for d in erg.loipen for b in d.unbekannte_begriffe]


@pytest.mark.req("P29", ak=3)
def test_p29_ort_ohne_einzelne_loipen_bekommt_das_loipennetz():
    s = seite("val-muestair")
    assert lese_loipen(s) == []
    netz = lese_netz(s)
    assert [(z["typ"], z["offen_km"], z["gesamt_km"], z["zustand"]) for z in netz] == [
        ("Klassisch", 28.0, 28.0, "gut"), ("Skating", 28.0, 28.0, "gut")]
    erg, _ = lauf("myswitzerland")
    muestair = [d for d in erg.loipen if d.gebiet_slug == "val-muestair"]
    assert len(muestair) == 1
    d = muestair[0]
    assert d.name == "Loipennetz Val Müstair" and d.status == Status.OFFEN and d.technik == Technik.BEIDES
    assert d.laenge_km == 28.0 and d.gespurt_gesamt_km == 28.0 and d.schneehoehe_cm == 25
    assert d.quelle_aktualisiert_at.tzinfo == ZoneInfo("Europe/Zurich")


def test_p29_ortsdaten_und_stand():
    s = (FIXTURES / "recherche-2026-11-13/schweiz/myswitzerland-snow/davos-69.html").read_text(encoding="utf-8")
    assert ort_daten(s) == {"name": "Davos", "region": "Graubünden", "lat": 46.7976, "lon": 9.8273, "hoehe_m": 1560}
    assert stand(s) == datetime(2026, 11, 13, 8, 0, tzinfo=ZoneInfo("Europe/Zurich"))


def test_p29_zwei_ortsseiten_mit_denselben_loipen_zaehlen_einmal():
    erg, _ = lauf("myswitzerland")
    namen = [(d.gebiet_slug, d.name) for d in erg.loipen]
    assert len(namen) == len(set(namen))
    # Andermatt-Oberalp-Sedrun und Sedrun-Oberalp-Andermatt sind ein Gebiet
    assert len([n for g, n in namen if g == "andermatt-sedrun"]) == 19


def test_p29_ort_ohne_langlauf_abschnitt_gibt_warnung_statt_abbruch():
    q = quelle("myswitzerland")
    erste = q["config"]["orte"][0]["pfad"].strip("/")
    erg, _ = lauf("myswitzerland", ersetze={erste: "<html><body>Wartung</body></html>"})
    assert len(erg.warnungen) == 1 and "Abschnitt Langlauf fehlt" in erg.warnungen[0]
    assert len(erg.loipen) < 340


def test_p29_englische_seite_wird_ebenso_gelesen():
    englisch = (FIXTURES / "recherche-2026-11-13/schweiz/myswitzerland-snow/engadin-65.html").read_text(encoding="utf-8")
    zeilen = lese_loipen(englisch)
    assert len(zeilen) > 100 and zeilen[0]["typ"] == "Classic" and zeilen[0]["zustand"] == "closed"
    adapter = MySwitzerlandAdapter()
    erg = adapter.run("https://x", {"orte": [{"pfad": "/schneebericht/engadin-65/", "gebiet": "st-moritz"}]},
                      type("F", (), {"get": lambda self, url: englisch})())
    assert erg.loipen and not [b for d in erg.loipen for b in d.unbekannte_begriffe]


# ---------- P26: tourinfra-Regionen ----------

@pytest.mark.req("P26", ak=1)
@pytest.mark.parametrize("key,anzahl,gebiete_erwartet", [
    ("engadin", 108, {"oberengadin-seen", "st-moritz", "pontresina", "samedan-bever", "zuoz-s-chanf", "zernez"}),
    ("davos-klosters", 36, {"davos", "klosters"}),
    ("goms", 39, {"obergoms", "goms-muenster"}),
    ("gastein", 15, {"gastein"}),
    ("ramsau", 42, {"ramsau-am-dachstein"}),
    ("seefeld-tourinfra", 42, {"seefeld", "leutasch"}),
])
def test_p26_tourinfra_regionen_mit_strecke_und_gebiet(key, anzahl, gebiete_erwartet):
    erg, fetcher = lauf(key)
    assert len(fetcher.abgerufen) == 1
    assert erg.warnungen == []  # jeder Ort ist in gebiet_map, die Summenzeile ist keine Loipe
    assert len(erg.loipen) == anzahl
    assert {d.gebiet_slug for d in erg.loipen} == gebiete_erwartet
    assert all(d.lat and d.verlauf for d in erg.loipen)


@pytest.mark.req("P26", ak=2)
def test_p26_status_je_technik_aus_tourinfra():
    erg, _ = lauf("davos-klosters")
    offen = [d for d in erg.loipen if d.status == Status.OFFEN]
    assert len(offen) == 2 and all(d.status_rohtext.startswith("klassisch:") for d in offen)
    erg, _ = lauf("engadin")
    assert {d.status for d in erg.loipen} == {Status.OFFEN, Status.EINGESCHRAENKT, Status.GESCHLOSSEN}


@pytest.mark.req("P26", ak=3)
def test_p26_schweizer_orte_nur_einmal_abgefragt():
    """Engadin St. Moritz, Davos, Klosters und Goms kommen nur von tourinfra, nicht auch von Schweiz Tourismus."""
    tourinfra = {d.gebiet_slug for k in TOURINFRA_CH for d in lauf(k)[0].loipen}
    mys = {o["gebiet"] for o in quelle("myswitzerland")["config"]["orte"]}
    assert not tourinfra & mys


# ---------- Gebiete ----------

@pytest.mark.req("P29", ak=4)
def test_p29_gebiete_der_schweiz_mit_lage_land_und_grenzhinweis():
    assert pruefe(sources(), gebiete_yaml()) == []
    g, r = gebiete(), regionen()
    ch = [x for x in g.values() if r[x["region"]]["land"] in ("CH", "LI")]
    assert len(ch) == 104
    for x in ch:
        assert x["lat"] and x["lon"] and x["tourist_url"], x["slug"]
        assert "Vignette" in x["grenzinfo"], x["slug"]
        assert 45.8 < x["lat"] < 47.9 and 5.9 < x["lon"] < 10.5, x["slug"]
    assert r[g["malbun-steg"]["region"]]["land"] == "LI"
    assert r[g["gastein"]["region"]]["bundesland"] == "Salzburg"
    assert r[g["ramsau-am-dachstein"]["region"]]["bundesland"] == "Steiermark"
    assert g["gastein"]["wetterstation"]["dienst"] == "geosphere"


def test_neue_hosts_stehen_in_der_cloud_liste():
    hosts = set(lade_yaml(CONFIG_DIR / "cloud-umgebung.yaml")["hosts"])
    assert {"snow.myswitzerland.com", "module.tourinfra.com"} <= hosts


def test_tourinfra_summenzeile_ist_keine_loipe():
    erg = TourinfraAdapter().run("https://module.tourinfra.com/x", {"json_path": "/j", "default_gebiet": "davos"},
                                 type("F", (), {"get": lambda self, url: '[{"kms": 1, "anzk": 2, "status": []}]'})())
    assert erg.loipen == [] and erg.warnungen == []
