"""Adapter B: Schneebericht von aschau.de (Sachrang). P1, P5, P6, P9."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen.ablauf import rufe_quelle_ab
from loipen.adapters import ADAPTERS
from loipen.adapters.aschau import AschauAdapter, lese_schneebericht
from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml
from loipen.models import Loipe, Quelle, Schwierigkeit, Status
from tests.helpers import FixtureFetcher

Q = next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == "sachrang")
BERLIN = ZoneInfo("Europe/Berlin")
SEITEN = {"schneebericht-sachrang": "schneebericht.html"}


def fetcher(ersetze=None):
    return FixtureFetcher("sachrang", Q["base_url"], ersetze=ersetze, seiten=SEITEN)


def lauf(ersetze=None):
    return AschauAdapter().run(Q["base_url"], Q["config"], fetcher(ersetze))


def seite():
    return fetcher().seite("schneebericht.html")


@pytest.mark.req("P1", ak=1)
def test_p1_adapter_b_ist_registriert_und_liest_sachrang():
    assert isinstance(ADAPTERS["aschau"], AschauAdapter)
    assert Q["adapter"] == "aschau"
    namen = [l.name for l in lauf().loipen]
    assert namen == ["Nachtloipe", "Bergerfeld", "Langlaufrundkurs Lengauer Feld", "Priental Loipe"]


@pytest.mark.req("P9", ak=1)
def test_p9_nur_der_langlauf_bereich_wird_gelesen():
    """Lifte, Huetten, Rodeln und Skischulen stehen auf derselben Seite und sind keine Loipen."""
    alle = " ".join(l.name for l in lauf().loipen)
    for fremd in ("Kaiserblick", "Schlepplift", "Priener", "Rodel", "Skischule", "Eislauf"):
        assert fremd not in alle


@pytest.mark.req("P9", ak=1)
def test_p9_felder():
    nacht, berger, lengauer, priental = lauf().loipen
    assert berger.status == Status.GESCHLOSSEN and berger.status_rohtext == "Zustand: Geschlossen"
    assert (berger.gespurt_gesamt_km, berger.laenge_km) == (1.7, 1.7)  # "1,7 km von Gesamtkilometer: 1,7 km"
    assert (priental.gespurt_gesamt_km, priental.laenge_km) == (8.0, 8.0)  # "8 km" ohne Komma
    assert nacht.nachtloipe is True and berger.nachtloipe is False
    assert berger.schwierigkeit == Schwierigkeit.LEICHT and lengauer.schwierigkeit == Schwierigkeit.MITTEL
    assert (berger.lat, berger.lon) == (47.7105, 12.2425)
    assert {l.gebiet_slug for l in lauf().loipen} == {"sachrang"}
    assert [l.source_key for l in lauf().loipen] == [
        "nachtloipe", "bergerfeld", "langlaufrundkurs-lengauer-feld", "priental-loipe"
    ]
    assert "Webcam" in berger.rohtext and "10.03.2026" in berger.rohtext


@pytest.mark.req("P6", ak=2)
def test_p6_stand_mit_sekunden_in_berlin():
    assert lauf().loipen[0].quelle_aktualisiert_at == datetime(2026, 3, 10, 10, 13, tzinfo=BERLIN)


@pytest.mark.req("P5", ak=1)
@pytest.mark.parametrize(
    "wort,status",
    [("Gut", Status.OFFEN), ("Mittel", Status.EINGESCHRAENKT), ("Geöffnet", Status.OFFEN), ("Geschlossen", Status.GESCHLOSSEN)],
)
def test_p5_gut_und_mittel_aus_sachrang_sind_normiert_nicht_unbekannt(wort, status):
    """Abgeleitete Seite: der Zustand der 'Bergerfeld' wird ersetzt. Nicht echt, siehe Testkonzept."""
    html = seite().replace("<em> Geschlossen</em></div></div><p>Webcam", f"<em> {wort}</em></div></div><p>Webcam")
    berger = next(l for l in lauf({"schneebericht-sachrang": html}).loipen if l.name == "Bergerfeld")
    assert berger.status == status and berger.unbekannte_begriffe == []


@pytest.mark.req("P5", ak=2)
def test_p5_unbekanntes_wort_wird_gemeldet():
    html = seite().replace("<em> Geschlossen</em></div></div><p>Webcam", "<em> Lawinengefahr</em></div></div><p>Webcam")
    berger = next(l for l in lauf({"schneebericht-sachrang": html}).loipen if l.name == "Bergerfeld")
    assert berger.status == Status.UNBEKANNT
    assert berger.unbekannte_begriffe == [("zustand", "Lawinengefahr")]


@pytest.mark.req("P9")
def test_p9_seite_ohne_langlauf_bereich_ist_eine_warnung():
    ergebnis = lauf({"schneebericht-sachrang": "<html><body><h1>Wartung</h1></body></html>"})
    assert ergebnis.loipen == [] and ergebnis.warnungen
    assert lese_schneebericht("<html></html>")["loipen"] == []


@pytest.mark.req("P9")
def test_p9_ablauf_speichert_sachrang(session, caplog):
    lade_und_abgleichen(session)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "sachrang"))
    ergebnis = rufe_quelle_ab(session, quelle, fetcher())
    assert ergebnis.gefunden == 4 and ergebnis.fehler is None
    loipen = session.scalars(select(Loipe).where(Loipe.quelle_id == quelle.id)).all()
    assert {l.name for l in loipen} == {"Nachtloipe", "Bergerfeld", "Langlaufrundkurs Lengauer Feld", "Priental Loipe"}
    assert all(l.gebiet.slug == "sachrang" and l.zustaende[0].status == "geschlossen" for l in loipen)
