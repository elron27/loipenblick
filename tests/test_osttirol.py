"""Osttirol (P33, E-24): Loipenliste von Osttirol Tourismus als Ortsseite zur Querpruefung von tirol.at.

Fixture-Regressionstest (CLAUDE.md Regel 10) mit dem Schnappschuss vom 19.11.2026 (Workflow Schnappschuss,
Runde P33-1): tests/fixtures/osttirol/2026-11-19/alle-loipen.html, 59 Loipen, 58 "Status: geschlossen",
eine ohne Status (Verbindung Promenadenloipe und Talblickloipe Kals). Kein Datum, keine Schneehoehe, keine Koordinaten.
"""

import pytest

from loipen.adapters import ADAPTERS
from loipen.konfig import CONFIG_DIR, lade_yaml, pruefe
from loipen.models import Schwierigkeit, Status
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher


def quelle() -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == "osttirol")


def lauf(config: dict | None = None, ersetze: dict | None = None):
    q = quelle()
    fetcher = FixtureFetcher("osttirol", q["base_url"], seiten=SEITEN_QUELLEN["osttirol"], ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], config or q["config"], fetcher), fetcher


@pytest.mark.req("P33", ak=1)
def test_p33_alle_loipen_mit_status_laenge_und_schwierigkeit():
    erg, fetcher = lauf()
    assert erg.warnungen == []
    assert fetcher.abgerufen == ["https://www.osttirol.com/aktiv-outdoor/langlaufen-und-biathlon/alle-loipen"]
    assert len(erg.loipen) == 59 and len({d.source_key for d in erg.loipen}) == 59
    status = {s: sum(1 for d in erg.loipen if d.status == s) for s in Status if any(d.status == s for d in erg.loipen)}
    assert status == {Status.GESCHLOSSEN: 58, Status.UNBEKANNT: 1}
    assert all(not d.unbekannte_begriffe for d in erg.loipen)
    sillian = next(d for d in erg.loipen if d.name == "Sonnenloipe Sillian")
    assert (sillian.source_key, sillian.gebiet_slug, sillian.laenge_km, sillian.schwierigkeit) == (
        "1765418", "hochpustertal", 0.6, Schwierigkeit.LEICHT)
    assert sillian.status_rohtext == "geschlossen" and sillian.quelle_aktualisiert_at is None
    assert sillian.source_url == ("https://www.osttirol.com/aktiv-outdoor/langlaufen-und-biathlon/detail/"
                                  "sonnenloipe-sillian")
    ohne = next(d for d in erg.loipen if d.name == "Verbindung Promenadenloipe und Talblickloipe Kals")
    assert ohne.status == Status.UNBEKANNT and ohne.status_rohtext is None
    assert next(d for d in erg.loipen if d.name == "Beleuchtete Runde Lavant").nachtloipe is True


@pytest.mark.req("P33", ak=2)
def test_p33_gebiet_aus_namen_oder_schluessel_sonst_warnung():
    erg, _ = lauf()
    gebiete = {d.name: d.gebiet_slug for d in erg.loipen}
    assert gebiete["Grenzlandloipe"] == "obertilliach" and gebiete["Grenzloipe"] == "hochpustertal"
    assert gebiete["Erlsbachloipe"] == "defereggental" and gebiete["Romantikloipe Kals"] == "kals"
    assert gebiete["Übungsplatz Matreier Tauernhaus"] == "matrei"
    assert gebiete["Verbindungsloipe Dorf - Gries"] == "matrei"  # nur ueber gebiet_je_loipe
    assert {d.gebiet_slug for d in erg.loipen} == {
        "hochpustertal", "obertilliach", "matrei", "kals", "osttirol-lienz", "defereggental"}
    config = {**quelle()["config"], "gebiet_je_loipe": {}}
    erg, _ = lauf(config)
    assert len(erg.warnungen) == 2 and all("ohne Gebiet" in w for w in erg.warnungen)
    assert next(d for d in erg.loipen if d.name == "Verbindungsloipe Dorf - Gries").gebiet_slug == "osttirol-lienz"


@pytest.mark.req("P33", ak=2)
def test_p33_leere_seite_ergibt_warnung():
    erg, _ = lauf(ersetze={"aktiv-outdoor/langlaufen-und-biathlon/alle-loipen": "<html><body></body></html>"})
    assert erg.loipen == [] and len(erg.warnungen) == 1


@pytest.mark.req("P33", ak=3)
def test_p33_quelle_nur_test_rang_4_querpruefung():
    q = quelle()
    assert q["nutzung"]["erlaubnis"] == "nur_test" and q["rang"] == 4 and q["querpruefung"] is True
    assert q["nutzung"]["robots"] == "erlaubt" and q["nutzung"]["robots_geprueft"]
    sources = lade_yaml(CONFIG_DIR / "sources.yaml")
    gebiete = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    assert not [f for f in pruefe(sources, gebiete) if "osttirol" in f]
    slugs = {g["slug"] for g in gebiete["gebiete"]}
    assert set(q["config"]["gebiet_map"].values()) | {q["config"]["default_gebiet"]} <= slugs
    kontakt = (CONFIG_DIR.parent / "docs" / "kontaktliste.md").read_text(encoding="utf-8")
    assert "Osttirol" in kontakt.split("## 3.")[1]
