"""Abgelehnte Quellen und ausgeblendete Gebiete (B30, E-30).

Anlass: Achensee Tourismus hat am 20.11.2026 schriftlich widersprochen ("Wir stimmen dem automatisierten Abruf
und der Uebernahme unserer Loipendaten jedoch nicht zu"). Die Quelle wird nie abgerufen und nirgends gezeigt,
auch nicht in der Testversion. Dieselben Loipen kommen ueber tirol.at; bis 23.11.2026 waren die Gebiete von
Achensee Tourismus deshalb ganz ausgeblendet. Seit der Freigabe der Tirol Werbung (23.11.2026) zeigt die Seite sie
ueber tirol.at wieder (Stefans Entscheidung, E-37); der Block ausgeblendet in config/gebiete.yaml ist leer.
Am 25.11.2026 hat Achensee Tourismus die Darstellung endgueltig abgelehnt. Seitdem zeigt nur die Testversion
(LOIPEN_OEFFENTLICH=false) die Gebiete, mit sichtbarem Hinweis; die oeffentliche Seite laesst sie weg (B30 AK 5, E-43)."""

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

@pytest.mark.req("B31", ak=4)
@pytest.mark.req("B30", ak=5)
def test_b30_achensee_nur_in_der_testversion():
    """In keiner Version ausgeblendet ist nichts mehr; Achensee fehlt nur auf der oeffentlichen Seite (E-43)."""
    assert GEBIETE["ausgeblendet"] == {"gebiete": {}, "loipen": []}
    gebiete, loipen = ausgeblendet(GEBIETE, oeffentlich=False)
    assert gebiete == {} and loipen == set()
    gebiete, loipen = ausgeblendet(GEBIETE, oeffentlich=True)
    assert set(gebiete) == ACHENSEE_GEBIETE and loipen == {("alpbachtal", "W1 - Loipe Buchbergl")}
    assert ausgeblendet(GEBIETE) == ausgeblendet(GEBIETE, oeffentlich=True)  # ohne Angabe die sichere Seite
    assert pruefe(SOURCES, GEBIETE) == []


@pytest.mark.req("B30", ak=5)
def test_b30_nur_test_braucht_bekanntes_gebiet_und_grund():
    kaputt = {**GEBIETE, "nur_test": {"gebiete": {"gibt-es-nicht": "x", "achensee": ""},
                                      "loipen": [{"gebiet": "achensee", "name": "A"}]}}
    fehler = pruefe(SOURCES, kaputt)
    assert "nur_test: unbekanntes Gebiet gibt-es-nicht" in fehler
    assert "nur_test: Gebiet achensee ohne Grund" in fehler
    assert any(f.startswith("nur_test: Loipe A") for f in fehler)


@pytest.mark.req("B30", ak=5)
def test_b30_nur_test_gebiet_fehlt_nur_oeffentlich(session, tmp_path):
    w = Welt(session)
    test = w.gebiet("test-gebiet", schnee_cm=None, messtag=None)
    bleibt = w.gebiet("bleibt", schnee_cm=None, messtag=None)
    bleibt.nachbarn = [test]
    w.loipe(test, "Seeloipe", "tirol", 3, stand=JETZT)
    w.loipe(bleibt, "Dorfloipe", "tirol", 3, stand=JETZT)
    w.loipe(bleibt, "Einzelne Loipe", "tirol", 3, stand=JETZT, lat=47.2)
    session.flush()
    (tmp_path / "gebiete.yaml").write_text(yaml.safe_dump({"nur_test": {
        "gebiete": {"test-gebiet": "Grund G"},
        "loipen": [{"gebiet": "bleibt", "name": "Einzelne Loipe", "grund": "Grund L"}]}}), encoding="utf-8")
    test_daten = baue(session, JETZT, tmp_path, oeffentlich=False)
    loipen = loipen_nach_name(test_daten)
    assert set(loipen) == {"Seeloipe", "Dorfloipe", "Einzelne Loipe"}
    assert (loipen["Seeloipe"]["nur_test"], loipen["Einzelne Loipe"]["nur_test"], loipen["Dorfloipe"]["nur_test"]) \
        == ("Grund G", "Grund L", None)
    g = {x["slug"]: x for r in test_daten["regionen"].values() for x in r["gebiete"]}
    assert g["test-gebiet"]["nur_test"] == "Grund G" and g["bleibt"]["nur_test"] is None
    assert g["bleibt"]["nachbarn"] == ["test-gebiet"]
    assert test_daten["index"]["testversion"] is True

    oeff = baue(session, JETZT, tmp_path, oeffentlich=True)
    assert set(loipen_nach_name(oeff)) == {"Dorfloipe"}
    g = [x for r in oeff["regionen"].values() for x in r["gebiete"]]
    assert [x["slug"] for x in g] == ["bleibt"] and g[0]["nachbarn"] == [] and g[0]["nur_test"] is None
    assert loipen_nach_name(oeff)["Dorfloipe"]["nur_test"] is None
    assert oeff["index"]["testversion"] is False


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
def seiten(engine, tmp_path_factory):
    """Testversion und oeffentliche Seite aus denselben Daten."""
    from sqlalchemy.orm import Session

    test = tmp_path_factory.mktemp("site_abgelehnt_test")
    oeff = tmp_path_factory.mktemp("site_abgelehnt_oeffentlich")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, test, JETZT)
        generator.erzeuge(s, oeff, JETZT, oeffentlich=True)
        abo_ziele = ziele(s)
        s.close()
        trans.rollback()
    return test, oeff, abo_ziele


@pytest.fixture(scope="module")
def site(seiten):
    return seiten[0], seiten[2]


def _alle_gebiete(ziel) -> list[dict]:
    index = json.loads((ziel / "daten.json").read_text(encoding="utf-8"))
    return [g for r in index["regionen"]
            for g in json.loads((ziel / r["datei"]).read_text(encoding="utf-8"))["gebiete"]]


@pytest.mark.req("B30", ak=2)
@pytest.mark.req("B31", ak=4)
@pytest.mark.req("B30", ak=5)
def test_b30_testversion_zeigt_achensee_nur_ueber_tirol_at(site):
    ziel, _ = site
    index = json.loads((ziel / "daten.json").read_text(encoding="utf-8"))
    assert "achensee" not in {q["key"] for q in index["quellen"]}
    alle = [g for r in index["regionen"] for g in json.loads((ziel / r["datei"]).read_text(encoding="utf-8"))["gebiete"]]
    achensee = [g for g in alle if g["slug"] in ACHENSEE_GEBIETE]
    assert {g["slug"] for g in achensee} == ACHENSEE_GEBIETE
    loipen = [l for g in achensee for l in g["loipen"]]
    assert loipen and all(l["quelle"]["name"] == "Tirol Werbung (tirol.at)" for l in loipen)
    # Daten von achensee.com fehlen; nur der Hinweis nur_test nennt den Verband als Grund
    ohne_grund = [{**g, "nur_test": None, "loipen": [{**l, "nur_test": None} for l in g["loipen"]]} for g in alle]
    text = json.dumps(ohne_grund, ensure_ascii=False)
    assert "Achensee Tourismus" not in text, "Achensee Tourismus steht ausserhalb des Hinweises"
    assert "achensee.com" not in text, "achensee.com steht ausserhalb des Hinweises"
    # B30 AK 5: sichtbarer Hinweis an Gebiet, Loipen und Seite
    assert all(g["nur_test"] and "25.11.2026" in g["nur_test"] for g in achensee)
    assert all(l["nur_test"] for l in loipen)
    assert index["testversion"] is True


@pytest.mark.req("B30", ak=5)
def test_b30_testversion_traegt_hinweis_nur_test(seiten):
    test, oeff, _ = seiten
    for datei in ("index.html", "impressum.html", "hinweise.html"):
        assert "nur Test, nicht öffentlich" in (test / datei).read_text(encoding="utf-8"), datei
        assert 'id="testband"' not in (oeff / datei).read_text(encoding="utf-8"), datei
    js = (test / "app.js").read_text(encoding="utf-8")
    assert 'id="nur-test"' in js and "Nur in der Testversion, nicht öffentlich." in js


@pytest.mark.req("B30", ak=5)
def test_b30_oeffentliche_seite_laesst_achensee_weg(seiten):
    _, oeff, _ = seiten
    index = json.loads((oeff / "daten.json").read_text(encoding="utf-8"))
    assert index["testversion"] is False
    alle = _alle_gebiete(oeff)
    slugs = {g["slug"] for g in alle}
    assert not slugs & ACHENSEE_GEBIETE and "alpbachtal" in slugs and "hinterriss" in slugs
    assert not any(n in ACHENSEE_GEBIETE for g in alle for n in g["nachbarn"])
    namen = {l["name"] for g in alle for l in g["loipen"]}
    assert "W1 - Loipe Buchbergl" not in namen
    assert all(g["nur_test"] is None and all(l["nur_test"] is None for l in g["loipen"]) for g in alle)
    # auch Strecken, Statistik und alle anderen Dateien nennen die Achensee-Gebiete nicht
    for datei in oeff.rglob("*.json"):
        text = datei.read_text(encoding="utf-8")
        for slug in ACHENSEE_GEBIETE:
            assert f'"{slug}"' not in text, f"{datei.name} nennt {slug}"
        assert "W1 - Loipe Buchbergl" not in text, f"{datei.name} nennt W1 - Loipe Buchbergl"


@pytest.mark.req("B30", ak=5)
def test_b30_abo_und_push_ohne_achensee_auch_in_der_testversion(site):
    """Mails und Push gehen nach aussen, deshalb gilt fuer sie immer die oeffentliche Seite."""
    _, abo_ziele = site
    assert "g:achensee" not in abo_ziele and "g:steinberg-rofan" not in abo_ziele and "g:hinterriss" in abo_ziele
    assert not any(v.startswith("W1 - Loipe Buchbergl") for v in abo_ziele.values())
    e = [Ereignis("oeffnet", "Dorfloipe Pertisau", "achensee", "Achensee", "achensee-karwendel", "offen"),
         Ereignis("oeffnet", "W1 - Loipe Buchbergl", "alpbachtal", "Alpbachtal", "alpbachtal", "offen"),
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

