"""Adapter der Ausbaustufe 1 neben tirol.at: Kitzbueheler Alpen (P15), langlaufdorf.at und
Berchtesgaden (P16). Echte Schnappschuesse vom 12.11.2026."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.kitzalps import KitzAlpsAdapter
from loipen.adapters.langlaufdorf import LanglaufdorfAdapter, bloecke
from loipen.adapters.stammdaten import KEIN_ZUSTAND, StammdatenAdapter
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Status, Technik
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher

QUELLEN = {q["key"]: q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"]}


def lauf(key, adapter, ersetze=None):
    q = QUELLEN[key]
    f = FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN.get(key), ersetze=ersetze)
    return adapter.run(q["base_url"], q["config"], f), f


@pytest.mark.req("P15", ak=1)
def test_p15_kitzbueheler_alpen_je_region():
    assert isinstance(ADAPTERS["kitzalps"], KitzAlpsAdapter)
    erg, f = lauf("kitzbueheler-alpen", KitzAlpsAdapter())
    assert len(f.abgerufen) == 1 and erg.warnungen == []
    je = {}
    for l in erg.loipen:
        je[l.gebiet_slug] = je.get(l.gebiet_slug, 0) + 1
    assert je == {"brixental": 6, "hohe-salve": 19, "pillerseetal": 23, "st-johann-in-tirol": 23}
    l = next(l for l in erg.loipen if l.name == "Brixentaler Langlaufloipe")
    assert (l.laenge_km, l.technik, l.status, l.status_rohtext) == (17.9, Technik.BEIDES, Status.GESCHLOSSEN, "Gesperrt")
    assert l.source_url == "https://www.kitzbueheler-alpen.com/de/bri/touren/brixentaler-langlaufloipe.html"
    assert l.quelle_aktualisiert_at is None and l.lat is None  # kein Datum, keine Koordinate


@pytest.mark.req("P15", ak=1)
@pytest.mark.req("P18", ak=1)
def test_p15_geoeffnet_und_unbekanntes_wort():
    q = QUELLEN["kitzbueheler-alpen"]
    seite = FixtureFetcher("kitzbueheler-alpen", q["base_url"], seiten=SEITEN_QUELLEN["kitzbueheler-alpen"]).seite(
        "2026-11-12/bri.html")
    seite = seite.replace('<div class="column state closed"><span>Gesperrt</span>',
                          '<div class="column state open"><span>Geöffnet</span>', 1)
    seite = seite.replace('<div class="column state closed"><span>Gesperrt</span>',
                          '<div class="column state"><span>Spur folgt</span>', 1)
    erg, _ = lauf("kitzbueheler-alpen", KitzAlpsAdapter(), {"de/bri/aktuelles/loipen-status.html": seite})
    assert erg.loipen[0].status == Status.OFFEN
    assert erg.loipen[1].status == Status.UNBEKANNT and ("status", "Spur folgt") in erg.loipen[1].unbekannte_begriffe


@pytest.mark.req("P16", ak=1)
def test_p16_langlaufdorf_x_von_y_km_und_stand():
    assert isinstance(ADAPTERS["langlaufdorf"], LanglaufdorfAdapter)
    erg, f = lauf("langlaufdorf", LanglaufdorfAdapter())
    assert f.abgerufen == ["https://www.langlaufdorf.at/"]
    namen = [l.name for l in erg.loipen]
    assert namen == ["Kugelberg- & Nachtloipe", "Maschinenschnee- / Übungsloipe", "Dorf-Loipe", "Tiefbrunnau-Loipe",
                     "Loipe Hintersee"]
    stand = datetime(2026, 3, 6, 13, 11, tzinfo=ZoneInfo("Europe/Berlin"))
    for l in erg.loipen:
        assert l.gespurt_gesamt_km == 0 and l.status == Status.GESCHLOSSEN and l.quelle_aktualisiert_at == stand
    hintersee = erg.loipen[-1]
    assert (hintersee.gebiet_slug, hintersee.laenge_km, hintersee.status_rohtext) == ("hintersee", 20, "0 von 20 km")
    assert {l.gebiet_slug for l in erg.loipen[:-1]} == {"faistenau"}


def test_p16_versteckte_alte_bloecke_werden_ignoriert():
    """Die Seite enthaelt versteckte Bloecke frueherer Winter ('5 von 5 km', Stand 2021)."""
    q = QUELLEN["langlaufdorf"]
    texte = bloecke(FixtureFetcher("langlaufdorf", q["base_url"]).seite("2026-11-12/index.html"))
    assert not any("5 von 5 km" in t or "2021" in t for t in texte)


@pytest.mark.req("P16", ak=1)
@pytest.mark.parametrize("gespurt, status", [("0", Status.GESCHLOSSEN), ("3", Status.EINGESCHRAENKT),
                                             ("5", Status.OFFEN)])
def test_p16_status_aus_gespurten_km(gespurt, status):
    q = QUELLEN["langlaufdorf"]
    seite = re.sub(r"(Nachtloipe(?:</a>)?\s*)0 von 5 km", rf"\g<1>{gespurt} von 5 km",
                   FixtureFetcher("langlaufdorf", q["base_url"]).seite("2026-11-12/index.html"))
    erg, _ = lauf("langlaufdorf", LanglaufdorfAdapter(), {"": seite})
    l = erg.loipen[0]
    assert l.status == status and l.gespurt_gesamt_km == float(gespurt)


@pytest.mark.req("P16", ak=2)
def test_p16_berchtesgaden_nur_stammdaten():
    assert isinstance(ADAPTERS["stammdaten"], StammdatenAdapter)
    erg, f = lauf("berchtesgaden", StammdatenAdapter())
    assert len(f.abgerufen) == 6 and erg.warnungen == []
    nach = {l.name: l for l in erg.loipen}
    s = nach["Langlaufloipen Schönau a. Königssee"]
    assert (s.gebiet_slug, s.laenge_km, s.startpunkt, s.lat, s.lon) == (
        "schoenau-am-koenigssee", 18.2, "Oberschönau", 47.61016, 12.97756)
    assert nach["Langlaufzentrum Aschauerweiher"].laenge_km == 16  # aus sources.yaml, die Seite nennt keine Distanz
    for l in erg.loipen:
        assert l.status == Status.UNBEKANNT and l.status_rohtext == KEIN_ZUSTAND
        assert l.lat is not None
