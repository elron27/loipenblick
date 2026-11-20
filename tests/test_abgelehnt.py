"""Abgelehnte Quellen und ausgeblendete Gebiete (B30, E-30).

Anlass: Achensee Tourismus hat am 20.11.2026 schriftlich widersprochen ("Wir stimmen dem automatisierten Abruf
und der Uebernahme unserer Loipendaten jedoch nicht zu"). Die Quelle wird nie abgerufen und nirgends gezeigt,
auch nicht in der Testversion. Dieselben Loipen kommen ueber tirol.at; bis zur Klaerung sind die Gebiete von
Achensee Tourismus deshalb ganz ausgeblendet (config/gebiete.yaml, Block ausgeblendet)."""

import json
from datetime import timedelta

import pytest
import yaml
from sqlalchemy import select

from loipen import generator
from loipen.ereignisse import Ereignis
from loipen.generator.abo import ziele
from loipen.generator.daten import baue
from loipen.konfig import (CONFIG_DIR, ERLAUBNIS, abgelehnte_quellen, abgleichen, ausgeblendet, lade_und_abgleichen,
                           lade_yaml, nur_test_quellen, pruefe)
from loipen.models import Quelle
from loipen.worker.__main__ import ohne_ausgeblendete
from tests.helpers import lade_alle_fixtures
from tests.test_plausibel import JETZT, Welt, loipen_nach_name

SOURCES = lade_yaml(CONFIG_DIR / "sources.yaml")
GEBIETE = lade_yaml(CONFIG_DIR / "gebiete.yaml")
ACHENSEE_GEBIETE = {"achensee", "steinberg-rofan"}


# ---------- AK 1: nie abrufen ----------

@pytest.mark.req("B30", ak=1)
def test_b30_abgelehnte_quelle_ist_immer_aus(session):
    """Auch ein vergessenes enabled: true schaltet eine abgelehnte Quelle nicht ein."""
    q = next(dict(q) for q in SOURCES["quellen"] if q["key"] == "achensee")
    q["enabled"] = True
    abgleichen(session, {"quellen": [q]}, GEBIETE)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "achensee"))
    assert quelle.enabled is False and quelle.config["erlaubnis"] == "abgelehnt"


@pytest.mark.req("B30", ak=1)
def test_b30_worker_ruft_achensee_nicht_ab(session):
    lade_und_abgleichen(session)
    aktiv = {q.key for q in session.scalars(select(Quelle).where(Quelle.enabled))}
    assert "achensee" not in aktiv and "tirol" in aktiv
    assert abgelehnte_quellen(SOURCES) == ["achensee"]
    assert "achensee" not in nur_test_quellen(SOURCES)


@pytest.mark.req("B30", ak=1)
def test_b30_erlaubnis_kennt_abgelehnt():
    assert ERLAUBNIS == ("liegt_vor", "ausstehend", "nur_test", "abgelehnt")
    q = {"key": "x", "adapter": "tirolat", "name": "X", "base_url": "https://x.example",
         "nutzung": {"robots": "erlaubt", "robots_geprueft": "2026-11-20", "nutzungsbedingungen_geprueft": None,
                     "erlaubnis": "abgelehnt"}, "config": {"default_gebiet": GEBIETE["gebiete"][0]["slug"]}}
    assert not any("nutzung.erlaubnis" in f for f in pruefe({"quellen": [q]}, GEBIETE))


# ---------- AK 2: nirgends zeigen, auch mit alten Daten in der Datenbank ----------

def _welt_mit_alten_daten(session):
    w = Welt(session)
    g = w.gebiet("pertisau-test", schnee_cm=None, messtag=None)
    w.loipe(g, "Gerntal", "tirol", 3, stand=JETZT - timedelta(hours=2), km=3.0)
    w.loipe(g, "P4 - Loipe Pletzach-Gern", "abgelehnt-test", 2, stand=JETZT - timedelta(hours=2), km=2.0, lat=47.5)
    # Datenbank vom NAS: Quelle noch eingeschaltet, Erlaubnis inzwischen abgelehnt
    w.quellen["abgelehnt-test"].config = {**w.quellen["abgelehnt-test"].config, "erlaubnis": "abgelehnt"}
    session.flush()


@pytest.mark.req("B30", ak=2)
@pytest.mark.parametrize("oeffentlich", [False, True])
def test_b30_abgelehnte_quelle_fehlt_in_beiden_versionen(session, oeffentlich):
    _welt_mit_alten_daten(session)
    daten = baue(session, JETZT, CONFIG_DIR, oeffentlich=oeffentlich)
    assert set(loipen_nach_name(daten)) == {"Gerntal"}
    assert "abgelehnt-test" not in {q["key"] for q in daten["index"]["quellen"]}
    assert "abgelehnt-test" not in daten["index"]["nur_test"]
    gerntal = loipen_nach_name(daten)["Gerntal"]
    assert all(a["quelle"] != "Quelle abgelehnt-test" for a in gerntal["auch_bei"])


# ---------- AK 3: Gebiete und Loipen ausblenden, gleich von welcher Quelle ----------

@pytest.mark.req("B30", ak=3)
def test_b30_gebiete_von_achensee_tourismus_sind_ausgeblendet():
    gebiete, loipen = ausgeblendet(GEBIETE)
    assert set(gebiete) == ACHENSEE_GEBIETE
    assert ("alpbachtal", "W1 - Loipe Buchbergl") in loipen
    assert all("20.11.2026" in grund for grund in gebiete.values())
    assert pruefe(SOURCES, GEBIETE) == []


@pytest.mark.req("B30", ak=3)
def test_b30_ausblenden_braucht_bekanntes_gebiet_und_grund():
    kaputt = {**GEBIETE, "ausgeblendet": {"gebiete": {"gibt-es-nicht": "x", "achensee": ""},
                                          "loipen": [{"gebiet": "achensee", "name": "A"}]}}
    fehler = pruefe(SOURCES, kaputt)
    assert any("unbekanntes Gebiet gibt-es-nicht" in f for f in fehler)
    assert any("achensee ohne Grund" in f for f in fehler)
    assert any("Loipe A" in f for f in fehler)


@pytest.mark.req("B30", ak=3)
def test_b30_ausgeblendetes_gebiet_fehlt_mit_allen_quellen(session, tmp_path):
    w = Welt(session)
    weg = w.gebiet("weg", schnee_cm=None, messtag=None)
    bleibt = w.gebiet("bleibt", schnee_cm=None, messtag=None)
    bleibt.nachbarn = [weg]
    w.loipe(weg, "Seeloipe", "tirol", 3, stand=JETZT)
    w.loipe(bleibt, "Dorfloipe", "tirol", 3, stand=JETZT)
    w.loipe(bleibt, "Einzelne Loipe", "tirol", 3, stand=JETZT, lat=47.2)
    session.flush()
    (tmp_path / "gebiete.yaml").write_text(yaml.safe_dump({"ausgeblendet": {
        "gebiete": {"weg": "Test"}, "loipen": [{"gebiet": "bleibt", "name": "Einzelne Loipe", "grund": "Test"}]}}),
        encoding="utf-8")
    for oeffentlich in (False, True):
        daten = baue(session, JETZT, tmp_path, oeffentlich=oeffentlich)
        assert set(loipen_nach_name(daten)) == {"Dorfloipe"}
        g = [g for r in daten["regionen"].values() for g in r["gebiete"]]
        assert [x["slug"] for x in g] == ["bleibt"]
        assert g[0]["nachbarn"] == []


@pytest.fixture(scope="module")
def site(engine, tmp_path_factory):
    from sqlalchemy.orm import Session

    ziel = tmp_path_factory.mktemp("site_abgelehnt")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, ziel, JETZT)
        abo_ziele = ziele(s)
        s.close()
        trans.rollback()
    return ziel, abo_ziele


@pytest.mark.req("B30", ak=3)
def test_b30_seite_zeigt_keine_achensee_loipen(site):
    ziel, _ = site
    index = json.loads((ziel / "daten.json").read_text(encoding="utf-8"))
    assert "achensee" not in {q["key"] for q in index["quellen"]}
    alle = [g for r in index["regionen"] for g in json.loads((ziel / r["datei"]).read_text(encoding="utf-8"))["gebiete"]]
    slugs = {g["slug"] for g in alle}
    assert not slugs & ACHENSEE_GEBIETE
    assert {"hinterriss", "silberregion-karwendel"} <= slugs  # Rest der Region bleibt
    namen = {l["name"] for g in alle for l in g["loipen"]}
    for name in ("P4 - Gerntal", "Dorfloipe Pertisau", "Seeloipe Oberautal", "S2 - Guffertloipe", "W1 - Loipe Buchbergl"):
        assert name not in namen
    assert not any(ACHENSEE_GEBIETE & set(g["nachbarn"]) for g in alle)
    text = json.dumps(alle, ensure_ascii=False)
    assert "Achensee Tourismus" not in text and "achensee.com" not in text


@pytest.mark.req("B30", ak=3)
def test_b30_kein_abo_und_kein_push_fuer_ausgeblendetes(site):
    _, abo_ziele = site
    assert "g:achensee" not in abo_ziele and "g:steinberg-rofan" not in abo_ziele
    assert not any("W1 - Loipe Buchbergl" in v or "Pertisau" in v for v in abo_ziele.values())
    assert "g:hinterriss" in abo_ziele
    e = [Ereignis("oeffnet", "Dorfloipe Pertisau", "achensee", "Achensee", "achensee-karwendel", "offen"),
         Ereignis("oeffnet", "W1 - Loipe Buchbergl", "alpbachtal", "Alpbachtal", "alpbachtal-wildschoenau", "offen"),
         Ereignis("oeffnet", "Loipe Hinterriss", "hinterriss", "Hinterriß", "achensee-karwendel", "offen")]
    assert [x.loipe for x in ohne_ausgeblendete(e, CONFIG_DIR)] == ["Loipe Hinterriss"]


# ---------- AK 4: Kontaktliste und Checkliste ----------

@pytest.mark.req("B30", ak=4)
def test_b30_kontaktliste_und_checkliste_nennen_die_absage():
    docs = CONFIG_DIR.parent / "docs"
    kontakt = (docs / "kontaktliste.md").read_text(encoding="utf-8")
    checkliste = (docs / "livegang-checkliste-stefan.md").read_text(encoding="utf-8")
    assert "abgelehnt am 20.11.2026" in kontakt
    assert "abgelehnt" in checkliste and "Achensee" in checkliste

