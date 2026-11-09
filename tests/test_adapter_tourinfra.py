"""Adapter C: tourinfra-Loipenmanager (Chiemgau). P1, P5, P11."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen.ablauf import rufe_quelle_ab
from loipen.adapters import ADAPTERS
from loipen.adapters.tourinfra import TourinfraAdapter
from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml
from loipen.models import Gebiet, Loipe, Quelle, Status, Technik
from tests.helpers import FixtureFetcher

Q = next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == "chiemgau")
SEITEN = {"inc/ajax.php?ajaxtype=getLoipenmanager": "loipenmanager.json"}


def fetcher(ersetze=None):
    return FixtureFetcher("chiemgau", Q["base_url"], ersetze=ersetze, seiten=SEITEN)


def roh() -> dict:
    return json.loads(fetcher().seite("loipenmanager.json"))


def lauf(daten: dict | None = None):
    ersetze = {"inc/ajax.php?ajaxtype=getLoipenmanager": json.dumps(daten)} if daten is not None else None
    return TourinfraAdapter().run(Q["base_url"], Q["config"], fetcher(ersetze))


@pytest.mark.req("P11", ak=1)
def test_p11_chiemgau_orte_aus_einer_abfrage():
    assert isinstance(ADAPTERS["tourinfra"], TourinfraAdapter)
    f = fetcher()
    erg = TourinfraAdapter().run(Q["base_url"], Q["config"], f)
    assert len(f.abgerufen) == 1
    assert len(erg.loipen) == 69  # 70 Eintraege, einer ohne Name
    assert {l.gebiet_slug for l in erg.loipen} == {
        "ruhpolding", "reit-im-winkl", "inzell", "schleching", "unterwoessen",
        "marquartstein-grassau", "bergen", "siegsdorf", "chieming",
    }
    assert erg.warnungen == ["Eintrag ohne Name oder ID uebersprungen"]


@pytest.mark.req("P11", ak=1)
def test_p11_felder_einer_loipe():
    l = next(l for l in lauf().loipen if l.source_key == "45988")
    assert l.name == "Nr. 7 Grenzland-Loipe klassisch + skating"
    assert l.gebiet_slug == "reit-im-winkl"
    assert l.status == Status.GESCHLOSSEN
    assert l.status_klassisch == l.status_skating == Status.GESCHLOSSEN
    assert l.technik == Technik.KLASSISCH
    assert l.laenge_km == 5.2 and l.nachtloipe is False
    assert (l.lat, l.lon) == (47.654822703781, 12.580032348633)
    assert l.startpunkt == "Winklmoos - Alm Gondel"
    assert l.source_url == "https://module.tourinfra.com/chiemgau/details.php?id=45988"
    assert l.gespurt_klassisch_km == 0 and l.quelle_aktualisiert_at is None


@pytest.mark.req("P5")
def test_p5_status_getrennt_fuer_klassisch_und_skating():
    daten = roh()
    k = next(k for k, v in daten.items() if v.get("tid") == "45988")
    daten[k].update(
        status_klassisch_text="Gut", status_skating_text="Geschlossen", status_text="Mittel",
        prep_km_klassisch=4.5, prep_km_skating=-1, praep_datum="14.12.2026 / 06:55",
    )
    l = next(l for l in lauf(daten).loipen if l.source_key == "45988")
    assert (l.status_klassisch, l.status_skating, l.status) == (Status.OFFEN, Status.GESCHLOSSEN, Status.EINGESCHRAENKT)
    assert (l.gespurt_klassisch_km, l.gespurt_skating_km, l.gespurt_gesamt_km) == (4.5, None, 4.5)
    assert l.quelle_aktualisiert_at == datetime(2026, 12, 14, 6, 55, tzinfo=ZoneInfo("Europe/Berlin"))


@pytest.mark.req("P5")
def test_p5_unbekannter_status_wird_gemeldet():
    daten = roh()
    k = next(iter(daten))
    daten[k]["status_klassisch_text"] = "Pulverschnee"
    l = next(l for l in lauf(daten).loipen if l.source_key == daten[k]["tid"])
    assert ("status_klassisch", "Pulverschnee") in l.unbekannte_begriffe
    assert l.status_klassisch == Status.UNBEKANNT


@pytest.mark.req("P11", ak=2)
def test_p11_unbekannter_ort_wird_gemeldet_nicht_verschluckt():
    daten = roh()
    k = next(iter(daten))
    daten[k]["startort"] = "Neustadt"
    erg = lauf(daten)
    assert any("Neustadt" in w for w in erg.warnungen)
    assert next(l for l in erg.loipen if l.source_key == daten[k]["tid"]).gebiet_slug == "chieming"


@pytest.mark.req("P11")
def test_p11_lauf_speichert_loipen_je_gebiet(session):
    lade_und_abgleichen(session)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "chiemgau"))
    ergebnis = rufe_quelle_ab(session, quelle, fetcher())
    assert (ergebnis.gefunden, ergebnis.neu) == (69, 69)
    assert quelle.last_status == "warnung" and quelle.last_count == 69
    assert session.scalar(select(Gebiet).where(Gebiet.slug == "inzell")).loipen
    nochmal = rufe_quelle_ab(session, quelle, fetcher())
    assert nochmal.neu == 0  # D4: unveraendert, keine neue Zeile
