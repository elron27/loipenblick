"""Osttirol (P33, E-24): Loipenliste von Osttirol Tourismus als Ortsseite zur Querpruefung von tirol.at.

Fixture-Regressionstest (CLAUDE.md Regel 10) mit dem Schnappschuss vom 19.11.2026 (Workflow Schnappschuss,
Runde P33-1): tests/fixtures/osttirol/2026-11-19/alle-loipen.html, 59 Loipen, 58 "Status: geschlossen",
eine ohne Status (Verbindung Promenadenloipe und Talblickloipe Kals). Kein Datum, keine Schneehoehe, keine Koordinaten.
"""

import re

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


# ---------- Tiroler Zugspitz Arena: Wintersportbericht bei Intermaps (P33 AK 4, P17 AK 3) ----------
# Schnappschuss vom 19.11.2026 (Runde P33-1): 21 Langlaufloipen, alle geschlossen, Stand 19.11.2026 13:20,
# Schneehoehe Tal "- cm" (keine Meldung).

def lauf_zugspitz(config: dict | None = None, ersetze: dict | None = None):
    q = next(x for x in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if x["key"] == "zugspitzarena")
    fetcher = FixtureFetcher("zugspitzarena", q["base_url"], seiten=SEITEN_QUELLEN["zugspitzarena"], ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], config or q["config"], fetcher), fetcher, q


@pytest.mark.req("P33", ak=4)
def test_p33_zugspitz_arena_loipen_mit_status_stand_und_gebiet():
    erg, fetcher, _ = lauf_zugspitz()
    assert erg.warnungen == []
    assert fetcher.abgerufen == ["https://sdds4.intermaps.com/zugspitzarena/snowreport_zugspitzarena.aspx?lang=de"]
    assert len(erg.loipen) == 21 and len({d.source_key for d in erg.loipen}) == 21
    assert {d.status for d in erg.loipen} == {Status.GESCHLOSSEN}
    assert all(d.schneehoehe_cm is None for d in erg.loipen)  # "- cm" = keine Meldung
    assert {d.quelle_aktualisiert_at.strftime("%d.%m.%Y %H:%M") for d in erg.loipen} == {"19.11.2026 13:20"}
    kelmen = next(d for d in erg.loipen if d.name == "Berwang Loipe Kelmen - Namlos B23")
    assert (kelmen.gebiet_slug, kelmen.laenge_km, kelmen.schwierigkeit) == ("berwang", 3.4, Schwierigkeit.MITTEL)
    maehberg = next(d for d in erg.loipen if d.name.startswith("Bichlbach-Lähn"))
    assert (maehberg.gebiet_slug, maehberg.schwierigkeit) == ("zugspitz-arena", Schwierigkeit.SCHWER)
    moos = next(d for d in erg.loipen if d.name.startswith("Moos Ehrwald"))
    assert moos.laenge_km == 13.9 and moos.gebiet_slug == "zugspitz-arena"


@pytest.mark.req("P33", ak=4)
def test_p33_zugspitz_arena_offen_in_vorbereitung_und_schneehoehe():
    seite = (FixtureFetcher("zugspitzarena", "https://sdds4.intermaps.com",
                            seiten=SEITEN_QUELLEN["zugspitzarena"])
             .get("https://sdds4.intermaps.com/zugspitzarena/snowreport_zugspitzarena.aspx?lang=de"))
    kelmer = seite.index("Berwang Kelmerfeld Loipe A23")
    kelmen = seite.index("Berwang Loipe Kelmen - Namlos B23")
    vor = seite[:kelmer].rsplit("images/icons/closed.png", 1)
    zwischen = seite[kelmer:kelmen].rsplit("images/icons/closed.png", 1)
    seite = (vor[0] + "images/icons/open.png" + vor[1] + zwischen[0] + "images/icons/inprep.png" + zwischen[1]
             + seite[kelmen:])
    seite = re.sub(r"(TAL</span>\s*<br />\s*)- cm", r"\g<1>0 cm", seite, count=1)
    erg, _, _ = lauf_zugspitz(ersetze={"zugspitzarena/snowreport_zugspitzarena.aspx?lang=de": seite})
    status = {d.name: (d.status, d.status_rohtext) for d in erg.loipen}
    assert status["Berwang Kelmerfeld Loipe A23"] == (Status.OFFEN, "offen")
    assert status["Berwang Loipe Kelmen - Namlos B23"] == (Status.GESCHLOSSEN, "in Vorbereitung")
    assert {d.schneehoehe_cm for d in erg.loipen} == {0}


@pytest.mark.req("P33", ak=2)
def test_p33_zugspitz_arena_unbekannter_ort_und_leerer_bericht_warnen():
    _, _, q = lauf_zugspitz()
    config = {**q["config"], "gebiet_map": {k: v for k, v in q["config"]["gebiet_map"].items() if k != "Heiterwang"}}
    erg, _, _ = lauf_zugspitz(config)
    assert len(erg.warnungen) == 6 and all("Heiterwang" in w for w in erg.warnungen)
    erg, _, _ = lauf_zugspitz(ersetze={"zugspitzarena/snowreport_zugspitzarena.aspx?lang=de": "<html></html>"})
    assert erg.loipen == [] and len(erg.warnungen) == 2  # kein Stand, keine Loipen


def ausnahme_p17(q: dict) -> bool:
    """Dieselbe Bedingung wie in tests/test_ausbau.py (P17): nur_test und eine Begruendung unter p17_ausnahme."""
    return q["nutzung"].get("erlaubnis") == "nur_test" and bool(q["nutzung"].get("p17_ausnahme"))


@pytest.mark.req("P17", ak=3)
def test_p17_intermaps_nur_mit_ausnahme_fuer_die_testversion():
    _, _, q = lauf_zugspitz()
    assert ausnahme_p17(q) and q["rang"] == 4 and q["querpruefung"] is True
    ohne = {**q, "nutzung": {**q["nutzung"], "erlaubnis": "ausstehend"}}
    assert not ausnahme_p17(ohne)
    ohne_grund = {**q, "nutzung": {k: v for k, v in q["nutzung"].items() if k != "p17_ausnahme"}}
    assert not ausnahme_p17(ohne_grund)
    kontakt = (CONFIG_DIR.parent / "docs" / "kontaktliste.md").read_text(encoding="utf-8").split("## 3.")[1]
    assert "Zugspitz Arena" in kontakt and "Intermaps" in kontakt
