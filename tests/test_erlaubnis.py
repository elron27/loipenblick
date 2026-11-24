"""Erlaubnis je Quelle (B27, Stefan 19.11.2026): Quellen ohne Zustimmung laufen nur in der Testversion."""

import json
import re
from datetime import timedelta

import pytest

from loipen import generator
from loipen.generator.daten import baue
from loipen.konfig import CONFIG_DIR, ERLAUBNIS, lade_yaml, nur_test_quellen, pruefe
from tests.helpers import lade_alle_fixtures
from tests.test_livegang import JETZT as JETZT_FIXTURES, RECHT
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
    assert ERLAUBNIS == ("liegt_vor", "ausstehend", "nur_test", "abgelehnt")


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


@pytest.mark.req("B27", ak=3)
def test_b27_chiemgau_ohne_freigabe_nur_in_der_testversion():
    """Chiemgau GmbH 20.11.2026: Freigabe ausstehend, Loipenmanager-Daten vorerst nicht uebernehmen."""
    assert "chiemgau" in nur_test_quellen(lade_yaml(CONFIG_DIR / "sources.yaml"))


@pytest.mark.req("B31", ak=1)
def test_b31_liegt_vor_nur_mit_beleg():
    gebiete = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    q = {"key": "x", "adapter": "tirolat", "name": "X", "base_url": "https://x.example", "default_gebiet": None,
         "nutzung": {"robots": "erlaubt", "robots_geprueft": "2026-11-23", "nutzungsbedingungen_geprueft": None,
                     "erlaubnis": "liegt_vor"}, "config": {"default_gebiet": gebiete["gebiete"][0]["slug"]}}
    assert any("nutzung.beleg" in f for f in pruefe({"quellen": [q]}, gebiete))
    q["nutzung"]["beleg"] = "irgendwo/beleg.txt"
    assert any("nutzung.beleg" in f for f in pruefe({"quellen": [q]}, gebiete))
    q["nutzung"]["beleg"] = "docs/erlaubnisse/tirol-werbung-2026-11-23.md"
    assert not any("nutzung.beleg" in f for f in pruefe({"quellen": [q]}, gebiete))
    # die echte Konfiguration: jede Zustimmung ist belegt, und die Belegdatei liegt im Repo
    sources = lade_yaml(CONFIG_DIR / "sources.yaml")
    assert not any("nutzung.beleg" in f for f in pruefe(sources, gebiete))
    belege = [q["nutzung"]["beleg"] for q in sources["quellen"] if (q.get("nutzung") or {}).get("erlaubnis") == "liegt_vor"]
    assert belege and all((CONFIG_DIR.parent / b).is_file() for b in belege)


@pytest.mark.req("B31", ak=2)
def test_b31_tirol_at_freigegeben_mit_beleg_ohne_telefonnummern():
    """Tirol Werbung GmbH 23.11.2026: Abholung mit Quellangabe und Verlinkung zu tirol.at in Ordnung."""
    tirol = next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == "tirol")
    assert tirol["nutzung"]["erlaubnis"] == "liegt_vor"
    beleg = (CONFIG_DIR.parent / tirol["nutzung"]["beleg"]).read_text(encoding="utf-8")
    assert "23.11.2026" in beleg and "Quellangabe und Verlinkung zu unserer Seite" in beleg
    assert "LTO Freigabetool" in beleg
    assert not re.search(r"\+\d{2}[\d ]{6,}", beleg), "keine Telefonnummern im Beleg"
    assert "tirol" not in nur_test_quellen(lade_yaml(CONFIG_DIR / "sources.yaml"))
    kontakte = (CONFIG_DIR.parent / "docs" / "kontaktliste.md").read_text(encoding="utf-8")
    zeile = next(z for z in kontakte.splitlines() if z.startswith("| Tirol Werbung GmbH"))
    assert "Erlaubnis am 23.11.2026" in zeile and "nachfassen, falls" not in zeile


@pytest.mark.req("B31", ak=3)
def test_b31_tirol_loipen_oeffentlich_mit_quellangabe_und_link(session, tmp_path):
    lade_alle_fixtures(session, JETZT_FIXTURES)
    generator.erzeuge(session, tmp_path, JETZT_FIXTURES, oeffentlich=True, rechtliches=RECHT)
    index = json.loads((tmp_path / "daten.json").read_text(encoding="utf-8"))
    tirol = [l for r in index["regionen"]
             for g in json.loads((tmp_path / r["datei"]).read_text(encoding="utf-8"))["gebiete"]
             for l in g["loipen"] if l["quelle"]["name"] == "Tirol Werbung (tirol.at)"]
    assert tirol, "tirol.at-Loipen fehlen auf der oeffentlichen Seite"
    assert all(l["quelle"]["url"].startswith("https://www.tirol.at/") for l in tirol)
    hinweise = (tmp_path / "hinweise.html").read_text(encoding="utf-8")
    assert "Tirol Werbung (tirol.at)" in hinweise and 'href="https://www.tirol.at"' in hinweise


@pytest.mark.req("B31", ak=2)
def test_b31_kaiserwinkl_freigegeben_mit_beleg_und_vorbehalt():
    """Tourismusverband Kaiserwinkl 24.11.2026: Umsetzung wie angefragt erlaubt, bis ein Widget geklaert ist (E-41)."""
    sources = lade_yaml(CONFIG_DIR / "sources.yaml")
    kw = next(q for q in sources["quellen"] if q["key"] == "kaiserwinkl")
    assert kw["nutzung"]["erlaubnis"] == "liegt_vor"
    assert "kaiserwinkl.com" in kw["nutzung"]["bedingung"]
    beleg = (CONFIG_DIR.parent / kw["nutzung"]["beleg"]).read_text(encoding="utf-8")
    assert "24.11.2026" in beleg and "Bis dahin können Sie gerne das wie von Ihnen gewünscht umsetzen" in beleg
    assert "Widget" in beleg and "meldet sich" in beleg
    assert not re.search(r"\+\d{2}[\d ]{6,}", beleg), "keine Telefonnummern im Beleg"
    assert "Hamberger" not in beleg, "kein Personenname im Beleg"
    assert "kaiserwinkl" not in nur_test_quellen(sources)
    kontakte = (CONFIG_DIR.parent / "docs" / "kontaktliste.md").read_text(encoding="utf-8")
    zeile = next(z for z in kontakte.splitlines() if z.startswith("| TVB Kaiserwinkl"))
    assert "Erlaubnis am 24.11.2026" in zeile and "Widget" in zeile


@pytest.mark.req("B31", ak=5)
def test_b31_kaiserwinkl_loipen_oeffentlich_mit_quellangabe_und_link(session, tmp_path):
    lade_alle_fixtures(session, JETZT_FIXTURES)
    generator.erzeuge(session, tmp_path, JETZT_FIXTURES, oeffentlich=True, rechtliches=RECHT)
    index = json.loads((tmp_path / "daten.json").read_text(encoding="utf-8"))
    kw = [l for r in index["regionen"]
          for g in json.loads((tmp_path / r["datei"]).read_text(encoding="utf-8"))["gebiete"]
          for l in g["loipen"] if l["quelle"]["name"] == "Tourismusverband Kaiserwinkl (Loipenbericht)"]
    assert kw, "Kaiserwinkl-Loipen fehlen auf der oeffentlichen Seite"
    assert all(l["quelle"]["url"].startswith("https://www.kaiserwinkl.com/") for l in kw)
    hinweise = (tmp_path / "hinweise.html").read_text(encoding="utf-8")
    assert "Tourismusverband Kaiserwinkl (Loipenbericht)" in hinweise and 'href="https://www.kaiserwinkl.com"' in hinweise
