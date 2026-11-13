"""E-Mail-Abo und Meldungen in der erzeugten Seite (E-18): N5, N7, N9, dazu Upload und Server-Konfiguration.
Die Formulare im echten Browser stehen in test_abo_ui.py."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen import generator
from loipen.config import Settings
from loipen.generator import abo as abo_vorlage
from loipen.mailabo import AboKonfig
from loipen.upload import OrdnerZiel, freigegeben, lade_hoch
from loipen.worker import __main__ as worker
from tests.helpers import lade_alle_fixtures

JETZT = datetime(2026, 12, 10, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
CFG = AboKonfig(seite_url="https://loipen.example", schluessel="geheimer-schluessel", absender="abo@loipen.example")
RECHT = {"name": "Erika Muster", "anschrift": "Musterweg 1|83700 Rottach-Egern", "email": "kontakt@example.org"}


@pytest.fixture
def site_mit_abo(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    ziel = tmp_path / "site"
    generator.erzeuge(session, ziel, JETZT, rechtliches=RECHT,
                      abo_dateien=abo_vorlage.dateien(session, CFG, meldungen_an="kontakt@example.org"))
    return ziel


@pytest.mark.req("N5", ak=3)
def test_n5_ohne_konfiguration_keine_formulare_und_kein_abo_ordner(session, tmp_path):
    generator.erzeuge(session, tmp_path, JETZT)
    assert json.loads((tmp_path / "daten.json").read_text())["abo"] is False
    assert not (tmp_path / "abo").exists()
    assert "E-Mail-Benachrichtigung" not in (tmp_path / "datenschutz.html").read_text(encoding="utf-8")


@pytest.mark.req("N5", ak=1)
def test_n5_mit_konfiguration_abo_ordner_und_schalter(site_mit_abo, session, tmp_path):
    assert json.loads((site_mit_abo / "daten.json").read_text())["abo"] is True
    for name in ("anmelden", "bestaetigen", "abmelden", "melden", "export", "_kern", "einstellungen", "ziele"):
        assert (site_mit_abo / "abo" / f"{name}.php").exists(), name
    ziele = (site_mit_abo / "abo" / "ziele.php").read_text(encoding="utf-8")
    assert "'g:tegernsee' => 'Alle Loipen im Gebiet" in ziele and "'l:" in ziele
    # wird das Abo wieder abgeschaltet, verschwindet der Ordner
    generator.erzeuge(session, site_mit_abo, JETZT, rechtliches=RECHT)
    assert not (site_mit_abo / "abo").exists()


@pytest.mark.req("N7", ak=4)
def test_n7_datenschutzerklaerung_beschreibt_abo_und_meldungen(site_mit_abo):
    text = (site_mit_abo / "datenschutz.html").read_text(encoding="utf-8")
    for teil in ("E-Mail-Benachrichtigung", "Double-Opt-In", "Art. 6 Abs. 1 lit. a DSGVO", "48 Stunden",
                 "Link in jeder Mail", "Falsche Angaben melden", "nur wenn du sie angibst",
                 "ändert den angezeigten Status nicht"):
        assert teil in text, teil


@pytest.mark.req("N7", ak=3)
def test_n7_kein_schluessel_in_der_seite(site_mit_abo):
    for p in site_mit_abo.rglob("*"):
        if p.is_file():
            assert b"geheimer-schluessel" not in p.read_bytes(), p


@pytest.mark.req("N8", ak=3)
def test_n8_server_sperrt_abo_daten_und_erlaubt_formulare(site_mit_abo):
    h = (site_mit_abo / ".htaccess").read_text(encoding="utf-8")
    assert "RewriteRule ^abo/daten/ - [F]" in h
    assert "form-action 'self'" in h and "connect-src 'self'" in h


@pytest.mark.req("N5", ak=4)
def test_n5_upload_nimmt_die_abo_skripte_mit_aber_nie_abo_daten(site_mit_abo, tmp_path):
    assert freigegeben("abo/anmelden.php") and freigegeben("abo/.htaccess") and freigegeben("abo/daten/.htaccess")
    assert not freigegeben("abo/daten/warteschlange.php") and not freigegeben("index.php")
    (site_mit_abo / "abo" / "daten" / "warteschlange.php").write_text("<?php exit; ?>\n{}")
    server = tmp_path / "server"
    lade_hoch(site_mit_abo, OrdnerZiel(server))
    assert (server / "abo" / "anmelden.php").exists() and (server / "abo" / "daten" / ".htaccess").exists()
    assert not (server / "abo" / "daten" / "warteschlange.php").exists()


def test_worker_baut_abo_nur_mit_vollstaendiger_konfiguration(session):
    leer = Settings(_env_file=None)
    assert worker.abo_dateien(session, leer) == {}
    voll = Settings(_env_file=None, oeffentliche_url="https://loipen.example", abo_schluessel="k",
                    abo_absender="abo@loipen.example", impressum_email="kontakt@loipen.example")
    d = worker.abo_dateien(session, voll)
    assert "'meldungen_an' => 'kontakt@loipen.example'" in d["abo/einstellungen.php"].decode()
