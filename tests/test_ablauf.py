"""Abruf, Speichern, Historie und Monitoring mit Beispielseiten und echter PostgreSQL.

Anforderungen: P5 (Protokoll), D1 (Hauswies-Runde), D3, D4, B2 (Anfang), P2.
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from loipen.ablauf import rufe_quelle_ab
from loipen.konfig import lade_und_abgleichen
from loipen.models import Gebiet, Loipe, Quelle, Zustand
from tests.helpers import FixtureFetcher

T0 = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
RINGSEE = "a-ringseeloipe-42-km-skating-u-klassisch"


@pytest.fixture
def db(session):
    lade_und_abgleichen(session)
    return session


def quelle(session, key) -> Quelle:
    return session.scalar(select(Quelle).where(Quelle.key == key))


def abrufen(session, key, zeit=T0, **fetcher_args):
    q = quelle(session, key)
    return rufe_quelle_ab(session, q, FixtureFetcher(key, q.base_url, **fetcher_args), zeit)


def anzahl(session, modell):
    return session.scalar(select(func.count()).select_from(modell))


@pytest.mark.req("P1", ak=1)
def test_alle_drei_orte_landen_in_der_datenbank(db):
    for key in ("tegernsee", "bayrischzell", "fischbachau"):
        abrufen(db, key)
    assert anzahl(db, Loipe) == 26 + 9 + 7
    assert anzahl(db, Zustand) == 26 + 9 + 7
    kreuth = db.scalar(select(Gebiet).where(Gebiet.slug == "kreuth"))
    assert {l.name for l in kreuth.loipen} >= {"Ringseeloipe", "Rundkurs Point"}


@pytest.mark.req("D1", ak=1)
def test_hauswies_runde_in_bayrischzell_und_fischbachau_sind_getrennt(db):
    abrufen(db, "bayrischzell")
    abrufen(db, "fischbachau")
    hauswies = db.scalars(select(Loipe).where(Loipe.name.like("%Hauswies%"))).all()
    assert len(hauswies) == 2
    assert {l.quelle.key for l in hauswies} == {"bayrischzell", "fischbachau"}
    assert len({l.id for l in hauswies}) == 2


@pytest.mark.req("D3", ak=2)
def test_zustand_speichert_abrufzeit_und_zeit_laut_quelle_getrennt(db):
    abrufen(db, "tegernsee")
    ring = db.scalar(select(Loipe).where(Loipe.source_key == "a-ringseeloipe"))
    z = ring.zustaende[0]
    assert z.abgerufen_at == T0
    assert z.quelle_aktualisiert_at == datetime(2026, 3, 15, 7, 47, tzinfo=timezone.utc)
    assert z.status == "geschlossen" and z.gespurt_gesamt_km == 8.4
    assert "Loipenzustand: nicht befahrbar" in z.rohtext  # D3 Rohtext


@pytest.mark.req("D4", ak=1)
def test_zweiter_abruf_mit_gleichen_daten_erzeugt_keine_historie(db):
    abrufen(db, "tegernsee", T0)
    nach_erstem = anzahl(db, Zustand)
    lauf = abrufen(db, "tegernsee", T0 + timedelta(hours=5))
    assert lauf.neu == 0 and anzahl(db, Zustand) == nach_erstem
    ring = db.scalar(select(Loipe).where(Loipe.source_key == "a-ringseeloipe"))
    assert ring.zustaende[0].zuletzt_bestaetigt_at == T0 + timedelta(hours=5)


@pytest.mark.req("D4", ak=1)
def test_aenderung_der_quelle_erzeugt_einen_historieneintrag(db):
    abrufen(db, "tegernsee", T0)
    q = quelle(db, "tegernsee")
    seite = FixtureFetcher("tegernsee", q.base_url).seite(f"schneebericht/{RINGSEE}.html")
    offen = seite.replace("<strong>nicht befahrbar</strong>", "<strong>geöffnet</strong>")
    lauf = abrufen(db, "tegernsee", T0 + timedelta(days=40), ersetze={RINGSEE: offen})
    assert lauf.neu == 1
    ring = db.scalar(select(Loipe).where(Loipe.source_key == "a-ringseeloipe"))
    assert [z.status for z in ring.zustaende] == ["offen", "geschlossen"]  # neueste zuerst


@pytest.mark.req("P5", ak=2)
def test_unbekannter_quelltext_steht_mit_quelle_und_rohtext_im_protokoll(db, caplog):
    q = quelle(db, "tegernsee")
    seite = FixtureFetcher("tegernsee", q.base_url).seite(f"schneebericht/{RINGSEE}.html")
    unsinn = seite.replace("<strong>nicht befahrbar</strong>", "<strong>Pulverschnee deluxe</strong>")
    with caplog.at_level(logging.WARNING, logger="loipen.ablauf"):
        abrufen(db, "tegernsee", ersetze={RINGSEE: unsinn})
    meldung = " ".join(r.getMessage() for r in caplog.records)
    assert "tegernsee" in meldung and "Pulverschnee deluxe" in meldung and "Ringseeloipe" in meldung
    ring = db.scalar(select(Loipe).where(Loipe.source_key == "a-ringseeloipe"))
    assert ring.zustaende[0].status == "unbekannt"  # nicht geraten und nicht verschluckt


@pytest.mark.req("B2", ak=1)
def test_monitoring_pro_quelle_letzter_lauf_und_anzahl(db):
    lauf = abrufen(db, "bayrischzell")
    q = quelle(db, "bayrischzell")
    assert lauf.fehler is None
    assert q.last_run_at == T0 and q.last_count == 9 and q.last_status == "ok" and q.last_error is None


@pytest.mark.req("B2", ak=1)
def test_monitoring_meldet_fehlende_seite_und_ausfall(db):
    q = quelle(db, "bayrischzell")
    q.config = {**q.config, "statusseiten": [*q.config["statusseiten"], "a-gibt-es-nicht"]}
    lauf = rufe_quelle_ab(db, q, FixtureFetcher("bayrischzell", q.base_url), T0)
    assert q.last_status == "warnung" and "a-gibt-es-nicht" in q.last_error and lauf.gefunden == 9

    class Kaputt:
        def get(self, url):
            raise ConnectionError("Quelle nicht erreichbar")

    lauf = rufe_quelle_ab(db, q, Kaputt(), T0 + timedelta(hours=1))
    assert q.last_status == "fehler" and "nicht erreichbar" in q.last_error
    assert anzahl(db, Loipe) == 9  # bisherige Daten bleiben erhalten


@pytest.mark.req("P2", ak=2)
def test_quelle_ohne_adapter_stoppt_den_lauf_nicht(db):
    q = quelle(db, "sachrang")
    lauf = rufe_quelle_ab(db, q, FixtureFetcher("sachrang", q.base_url), T0)
    assert lauf.fehler and q.last_status == "fehler"
