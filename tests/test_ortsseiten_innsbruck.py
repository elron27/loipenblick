"""Ortsseiten Innsbruck, Hall-Wattens, Silberregion Karwendel als Querpruefung (P32, E-24, nur Test).

Schnappschuesse vom 19.11.2026 (Workflow Schnappschuss, Runden P32-1 bis P32-3):
- tests/fixtures/innsbruck/2026-11-19/lebensraum_innsbruck.html: Intermaps-Wintersportbericht, den
  innsbruck.info als iframe einbettet. 40 Langlaufloipen in 9 Orten, alle geschlossen,
  "Letzte Aktualisierung 19.11.2026 15:46:31".
- tests/fixtures/hall-wattens/2026-11-19/langlaufen.html: 7 Loipen (Rinn, Gnadenwald), alle geschlossen.
- tests/fixtures/silberregion-karwendel/2026-11-19/langlaufen.html: 7 Loipen und ein Eintrag
  "TEST Loipe", alle geschlossen; Breite und Laenge im JSON vertauscht.
Nicht angebunden (Befund in docs/kontaktliste.md): Stubai (robots.txt liefert dem Abruf 403, gilt als
Verbot), Wipptal (keine eigene Statusseite, die Karte maps.wipptal.at zeigt die tirol.at-Daten).
Im November ist alles geschlossen; "offen" wird mit abgeleiteten Seiten geprueft.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.intermaps import IntermapsAdapter
from loipen.adapters.tourismus_mco import TourismusMcoAdapter, touren
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import FIXTURES, FixtureFetcher

STAND = "2026-11-19"
INTERMAPS_PFAD = "innsbruck_new/lebensraum_innsbruck.aspx?lang=de"
KEYS = ("innsbruck", "hall-wattens", "silberregion-karwendel")


def quelle(key: str) -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == key)


def fixture(key: str, datei: str) -> str:
    return (FIXTURES / key / STAND / datei).read_text(encoding="utf-8")


def lauf(key: str, ersetze: dict | None = None):
    q = quelle(key)
    seiten = {INTERMAPS_PFAD: f"{STAND}/lebensraum_innsbruck.html"} if key == "innsbruck" else None
    fetcher = FixtureFetcher(key, q["base_url"], seiten=seiten, stand=STAND, ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], q["config"], fetcher), fetcher


# ---------- AK 1: Innsbruck, Intermaps-Bericht ----------

@pytest.mark.req("P32", ak=1)
def test_p32_innsbruck_alle_loipen_mit_ort_stand_und_status():
    erg, fetcher = lauf("innsbruck")
    assert erg.warnungen == []
    assert fetcher.abgerufen == ["https://sdds4.intermaps.com/" + INTERMAPS_PFAD]
    assert len(erg.loipen) == 40 and len({d.source_key for d in erg.loipen}) == 40
    assert {d.status for d in erg.loipen} == {Status.GESCHLOSSEN}
    assert all(d.unbekannte_begriffe == [] for d in erg.loipen)
    orte = {d.startpunkt for d in erg.loipen}
    assert orte == {"Gries im Sellrain", "Kühtai", "Mieming", "Natters", "Oberperfuss", "Obsteig",
                    "Praxmar - Lüsens", "Rinn", "Wildermieming"}
    stand = datetime(2026, 11, 19, 15, 46, tzinfo=ZoneInfo("Europe/Berlin"))
    assert {d.quelle_aktualisiert_at for d in erg.loipen} == {stand}
    gries = next(d for d in erg.loipen if d.name == "Rundloipe Gries (klassisch & skating)")
    assert (gries.gebiet_slug, gries.technik, gries.status_rohtext) == ("sellraintal", Technik.BEIDES, "geschlossen")
    gebiete = {d.startpunkt: d.gebiet_slug for d in erg.loipen}
    assert gebiete["Kühtai"] == "kuehtai" and gebiete["Obsteig"] == "mieming" and gebiete["Rinn"] == "hall-wattens"
    assert next(d for d in erg.loipen if d.name == "SK2 Mieming (skating)").technik == Technik.SKATING


@pytest.mark.req("P32", ak=1)
def test_p32_innsbruck_symbole_aus_der_legende():
    vorher, loipen = fixture("innsbruck", "lebensraum_innsbruck.html").split("Langlaufloipen <span>", 1)
    # Gries offen, Bilgeriloipe "in Vorbereitung", Claudialoipe "offen (nicht frisch präpariert)"
    symbol = "lift_type_set_9_30x30_weiß/{}.png"
    teile = loipen.split(symbol.format(94), 3)
    abgeleitet = (vorher + "Langlaufloipen <span>" + teile[0] + symbol.format(169) + teile[1] + symbol.format(126)
                  + teile[2] + symbol.format(412) + teile[3])
    erg, _ = lauf("innsbruck", ersetze={INTERMAPS_PFAD: abgeleitet})
    status = {d.name: (d.status, d.status_rohtext) for d in erg.loipen}
    assert status["Rundloipe Gries (klassisch & skating)"] == (Status.OFFEN, "offen")
    assert status["Bilgeriloipe"] == (Status.GESCHLOSSEN, "in Vorbereitung")
    assert status["Claudialoipe"] == (Status.EINGESCHRAENKT, "offen (nicht frisch präpariert)")
    assert status["Maximilianloipe"] == (Status.GESCHLOSSEN, "geschlossen")


@pytest.mark.req("P32", ak=3)
def test_p32_innsbruck_leere_oder_geaenderte_seite_warnt():
    html = fixture("innsbruck", "lebensraum_innsbruck.html")
    erg, _ = lauf("innsbruck", ersetze={INTERMAPS_PFAD: html.replace("Langlaufloipen <span>", "Loipen <span>")})
    assert erg.loipen == [] and any("Keine Langlaufloipen" in w for w in erg.warnungen)
    ohne_symbol = html.replace("lift_type_set_9_30x30_weiß/94.png", "lift_type_set_9_30x30_weiß/999.png")
    erg, _ = lauf("innsbruck", ersetze={INTERMAPS_PFAD: ohne_symbol})
    assert {d.status for d in erg.loipen} == {Status.UNBEKANNT}
    assert erg.loipen[0].unbekannte_begriffe == [("status", "Symbol ohne Legende")]


# ---------- AK 2: Hall-Wattens und Silberregion Karwendel, Tourenportal ----------

@pytest.mark.req("P32", ak=2)
def test_p32_hall_wattens_loipen_aus_dem_server_strom():
    erg, fetcher = lauf("hall-wattens")
    assert erg.warnungen == [] and fetcher.abgerufen == ["https://www.hall-wattens.at/de/langlaufen.html"]
    assert len(erg.loipen) == 7 and {d.status for d in erg.loipen} == {Status.GESCHLOSSEN}
    assert {d.gebiet_slug for d in erg.loipen} == {"hall-wattens"}
    gnadenwald = next(d for d in erg.loipen if d.name == "Langlauf Loipe Gnadenwald")
    assert (gnadenwald.laenge_km, gnadenwald.schwierigkeit, gnadenwald.status_rohtext) == (15.7, Schwierigkeit.LEICHT, "closed")
    assert (gnadenwald.lat, gnadenwald.lon) == (47.313355, 11.539421)
    assert gnadenwald.source_url == "https://www.hall-wattens.at/de/tours/langlauf-loipe-gnadenwald.html"
    assert gnadenwald.quelle_aktualisiert_at is None


@pytest.mark.req("P32", ak=2)
def test_p32_karwendel_ohne_testeintrag_und_mit_richtiger_lage():
    erg, _ = lauf("silberregion-karwendel")
    assert erg.warnungen == []
    namen = {d.name for d in erg.loipen}
    assert len(namen) == 7 and not any(n.lower().startswith("test") for n in namen)
    hinterriss = next(d for d in erg.loipen if d.name == "Loipe Hinterriss")
    assert hinterriss.gebiet_slug == "hinterriss" and hinterriss.laenge_km == 27.0
    assert (hinterriss.lat, hinterriss.lon) == (47.46692, 11.48496)  # Quelle vertauscht Breite und Laenge
    assert hinterriss.startpunkt == "Mautstelle Hinterriss"
    assert next(d for d in erg.loipen if d.name == "Loipe Vomperberg").gebiet_slug == "silberregion-karwendel"


@pytest.mark.req("P32", ak=2)
def test_p32_offen_und_unbekannter_status():
    html = fixture("hall-wattens", "langlaufen.html")
    abgeleitet = html.replace('\\"statusType\\":\\"closed\\"', '\\"statusType\\":\\"open\\"', 1)
    abgeleitet = abgeleitet.replace('\\"statusType\\":\\"closed\\"', '\\"statusType\\":\\"wartung\\"', 1)
    erg, _ = lauf("hall-wattens", ersetze={"de/langlaufen.html": abgeleitet})
    status = sorted(d.status.value for d in erg.loipen)
    assert status.count("offen") == 1 and status.count("unbekannt") == 1
    unbekannt = next(d for d in erg.loipen if d.status == Status.UNBEKANNT)
    assert unbekannt.unbekannte_begriffe == [("status", "wartung")]


@pytest.mark.req("P32", ak=3)
def test_p32_tourenportal_ohne_server_strom_warnt():
    erg, _ = lauf("silberregion-karwendel", ersetze={"de/langlaufen.html": "<html><body>Wartung</body></html>"})
    assert erg.loipen == [] and erg.warnungen
    assert touren("<html></html>") == []


# ---------- AK 4: Quellen nur fuer die Testversion, Rang 4 ----------

@pytest.mark.req("P32", ak=4)
def test_p32_quellen_nur_test_rang_4_und_robots_geprueft():
    for key in KEYS:
        q = quelle(key)
        assert q["rang"] == 4 and q["querpruefung"] is True, key
        assert q["nutzung"]["erlaubnis"] == "nur_test", key
        assert q["nutzung"]["robots"] == "erlaubt" and str(q["nutzung"]["robots_geprueft"]) == STAND, key
    assert isinstance(ADAPTERS["intermaps"], IntermapsAdapter)
    assert isinstance(ADAPTERS["tourismus_mco"], TourismusMcoAdapter)
    keys = {q["key"] for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"]}
    assert not keys & {"stubai", "wipptal"}  # Stubai sperrt den Abruf, Wipptal hat nur tirol.at-Daten
