"""Erlaubnis je Quelle (B27, Stefan 19.11.2026): Quellen ohne Zustimmung laufen nur in der Testversion."""

from datetime import timedelta

import pytest

from loipen.generator.daten import baue
from loipen.konfig import CONFIG_DIR, ERLAUBNIS, lade_yaml, nur_test_quellen, pruefe
from tests.test_plausibel import JETZT, Welt, loipen_nach_name


def _welt(session):
    w = Welt(session)
    g = w.gebiet("mayrhofen", schnee_cm=None, messtag=None)
    w.loipe(g, "Ginzling Loipe", "tirol", 3, stand=JETZT - timedelta(hours=2), km=3.0)
    w.loipe(g, "Zillergrund", "zillertal", 4, stand=JETZT - timedelta(hours=2), km=2.0, lat=47.05)
    w.quellen["zillertal"].config = {**w.quellen["zillertal"].config, "erlaubnis": "nur_test"}
    session.flush()
    return w


@pytest.mark.req("B27", ak=1)
def test_b27_nur_test_quelle_fehlt_auf_der_oeffentlichen_seite(session):
    _welt(session)
    oeffentlich = baue(session, JETZT, CONFIG_DIR, oeffentlich=True)
    assert set(loipen_nach_name(oeffentlich)) == {"Ginzling Loipe"}
    assert "zillertal" not in {q["key"] for q in oeffentlich["index"]["quellen"]}
    assert oeffentlich["index"]["nur_test"] == []


@pytest.mark.req("B27", ak=1)
def test_b27_testversion_zeigt_nur_test_quelle(session):
    _welt(session)
    test = baue(session, JETZT, CONFIG_DIR)
    assert set(loipen_nach_name(test)) == {"Ginzling Loipe", "Zillergrund"}
    assert test["index"]["nur_test"] == ["zillertal"]


@pytest.mark.req("B27", ak=2)
def test_b27_erlaubnis_nur_mit_erlaubten_werten():
    gebiete = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    q = {"key": "x", "adapter": "tirolat", "name": "X", "base_url": "https://x.example", "default_gebiet": None,
         "nutzung": {"robots": "erlaubt", "robots_geprueft": "2026-11-19", "nutzungsbedingungen_geprueft": None,
                     "erlaubnis": "vielleicht"}, "config": {"default_gebiet": gebiete["gebiete"][0]["slug"]}}
    fehler = pruefe({"quellen": [q]}, gebiete)
    assert any("nutzung.erlaubnis" in f for f in fehler)
    q["nutzung"]["erlaubnis"] = "nur_test"
    assert not any("nutzung.erlaubnis" in f for f in pruefe({"quellen": [q]}, gebiete))
    assert ERLAUBNIS == ("liegt_vor", "ausstehend", "nur_test")


@pytest.mark.req("B27", ak=3)
def test_b27_livegang_liste_nennt_nur_test_quellen():
    sources = {"quellen": [{"key": "a", "nutzung": {"erlaubnis": "nur_test"}},
                           {"key": "b", "nutzung": {"erlaubnis": "liegt_vor"}},
                           {"key": "c", "enabled": False, "nutzung": {"erlaubnis": "nur_test"}},
                           {"key": "d"}]}
    assert nur_test_quellen(sources) == ["a"]
    assert isinstance(nur_test_quellen(lade_yaml(CONFIG_DIR / "sources.yaml")), list)
    checkliste = (CONFIG_DIR.parent / "docs" / "livegang-checkliste-stefan.md").read_text(encoding="utf-8")
    assert "nur_test" in checkliste and "kontaktliste.md" in checkliste
