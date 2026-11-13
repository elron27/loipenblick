"""Formulare fuer E-Mail-Abo und Meldungen im echten Browser, gegen die echten PHP-Skripte (N5, N9).

Die Seite wird mit Abo-Konfiguration erzeugt und vom eingebauten PHP-Server ausgeliefert, so wie
spaeter vom Webspace. Ohne PHP oder Chromium werden die Tests uebersprungen.
"""

import os
import shutil
import socket
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen import generator
from loipen.generator import abo as abo_vorlage
from loipen.mailabo import AboKonfig
from loipen.models import Gebiet, Loipe
from tests.helpers import lade_alle_fixtures

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.skipif(shutil.which("php") is None, reason="PHP nicht installiert")

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
SCREENSHOTS = os.environ.get("LOIPEN_SCREENSHOTS")  # Ordner fuer Bildschirmfotos, nur bei Bedarf


@pytest.fixture(scope="module")
def webspace(engine, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("abo-ui")
    site = tmp / "site"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    cfg = AboKonfig(seite_url=url, schluessel="k", absender="abo@loipen.example")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT, mit_wetter=False)
        loipe = s.scalar(select(Loipe).join(Gebiet).where(Gebiet.slug == "kreuth").order_by(Loipe.id))
        ids = {"loipe": loipe.id, "name": loipe.name}
        generator.erzeuge(s, site, JETZT, rechtliches={"name": "Erika Muster", "anschrift": "Weg 1|83700 Ort",
                                                      "email": "kontakt@example.org"},
                          abo_dateien=abo_vorlage.dateien(s, cfg, meldungen_an="kontakt@example.org"))
        s.close()
        trans.rollback()
    mails = tmp / "mails.txt"
    sendmail = tmp / "sendmail.sh"
    sendmail.write_text(f"#!/bin/sh\ncat >> '{mails}'\necho '----ENDE----' >> '{mails}'\n")
    sendmail.chmod(0o755)
    proc = subprocess.Popen(["php", "-d", f"sendmail_path={sendmail}", "-S", f"127.0.0.1:{port}", "-t", str(site)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield {"url": url, "mails": mails, **ids}
    proc.terminate()
    proc.wait(5)


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = None
        for args in ({}, {"executable_path": os.environ.get("LOIPEN_CHROMIUM", "/opt/pw-browsers/chromium")}):
            try:
                b = p.chromium.launch(**args)
                break
            except Exception:
                pass
        if b is None:
            pytest.skip("kein Chromium verfuegbar")
        yield b
        b.close()


def neue_seite(browser, breite=1280, hoehe=900, handy=False):
    ctx = browser.new_context(viewport={"width": breite, "height": hoehe}, locale="de-DE",
                              device_scale_factor=2 if SCREENSHOTS else 1, is_mobile=handy, has_touch=handy)
    page = ctx.new_page()
    page.fehler = []
    page.on("pageerror", lambda e: page.fehler.append(str(e)))
    return ctx, page


def foto(page, name, element=None):
    if SCREENSHOTS:
        os.makedirs(SCREENSHOTS, exist_ok=True)
        (element or page).screenshot(path=os.path.join(SCREENSHOTS, f"{name}.png"), **({} if element else {"full_page": False}))


@pytest.mark.req("N5", ak=1)
def test_n5_abo_formular_auf_der_loipenseite(browser, webspace):
    ctx, page = neue_seite(browser)
    page.goto(f"{webspace['url']}/#/loipe/{webspace['loipe']}")
    page.wait_for_selector("#abo")
    page.click("#abo summary")
    page.fill("#abo input[name=email]", "ski@example.org")
    page.check("#abo input[name=einwilligung]")
    page.locator("#abo").scroll_into_view_if_needed()
    foto(page, "desktop-abo-formular")
    page.click("#abo button[type=submit]")
    page.wait_for_selector("#abo .antwort.gut")
    assert "Fast geschafft" in page.inner_text("#abo .antwort")
    foto(page, "desktop-abo-gesendet")
    text = webspace["mails"].read_text(encoding="utf-8")
    assert "To: ski@example.org" in text and webspace["name"] in text
    # Bestaetigungsseite aus der Mail
    link = [z for z in text.splitlines() if "/abo/bestaetigen.php?t=" in z][-1].strip()
    page.goto(link)
    assert "Abo bestätigen" in page.inner_text("h1")
    foto(page, "desktop-abo-bestaetigen")
    page.click("button[type=submit]")
    assert page.inner_text("h1") == "Abo ist aktiv"
    foto(page, "desktop-abo-aktiv")
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("N5", ak=1)
def test_n5_abo_formular_auf_der_gebietsseite(browser, webspace):
    ctx, page = neue_seite(browser, 390, 844, handy=True)
    page.goto(f"{webspace['url']}/#/gebiet/kreuth")
    page.wait_for_selector("#abo")
    assert page.input_value("#abo input[name='ziel[]']") == "g:kreuth"
    page.click("#abo summary")
    page.locator("#abo").scroll_into_view_if_needed()
    foto(page, "handy-abo-gebiet")
    # Pflichtfelder: ohne Einwilligung schickt der Browser nicht ab
    page.fill("#abo input[name=email]", "ski2@example.org")
    page.click("#abo button[type=submit]")
    assert page.inner_text("#abo .antwort") == ""
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("N9", ak=4)
def test_n9_melden_knopf_auf_der_loipenseite(browser, webspace):
    ctx, page = neue_seite(browser, 390, 844, handy=True)
    page.goto(f"{webspace['url']}/#/loipe/{webspace['loipe']}")
    page.wait_for_selector("#melden")
    assert page.inner_text("#melden summary") == "Angabe falsch? Melden"
    page.click("#melden summary")
    page.check("#melden input[value=geschlossen]")
    page.fill("#melden textarea", "Seit gestern gesperrt")
    page.locator("#melden").scroll_into_view_if_needed()
    foto(page, "handy-melden-formular")
    page.click("#melden button[type=submit]")
    page.wait_for_selector("#melden .antwort.gut")
    foto(page, "handy-melden-gesendet")
    text = webspace["mails"].read_text(encoding="utf-8")
    assert "To: kontakt@example.org" in text and "Seit gestern gesperrt" in text
    assert page.fehler == []
    ctx.close()


def test_datenschutzseite_mit_abo_abschnitt(browser, webspace):
    ctx, page = neue_seite(browser)
    page.goto(f"{webspace['url']}/datenschutz.html")
    h = page.locator("h2", has_text="E-Mail-Benachrichtigung")
    h.scroll_into_view_if_needed()
    foto(page, "desktop-datenschutz-abo")
    ctx2, handy = neue_seite(browser, 390, 844, handy=True)
    handy.goto(f"{webspace['url']}/datenschutz.html")
    handy.locator("h2", has_text="E-Mail-Benachrichtigung").scroll_into_view_if_needed()
    foto(handy, "handy-datenschutz-abo")
    ctx.close()
    ctx2.close()
