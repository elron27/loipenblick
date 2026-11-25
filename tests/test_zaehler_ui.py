"""Besucherzaehler im echten Browser (B13): Die App meldet Aufrufe an die echten PHP-Skripte,
automatische Browser und ausgenommene Browser zaehlen nicht, die Auswertung nimmt den Browser aus.
Ohne PHP oder Chromium werden die Tests uebersprungen.
"""

import json
import os
import random
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
from loipen.generator import zaehler as zaehler_vorlage
from loipen.models import Gebiet, Loipe
from tests.helpers import lade_alle_fixtures

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.skipif(shutil.which("php") is None, reason="PHP nicht installiert")

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
SCREENSHOTS = os.environ.get("LOIPEN_SCREENSHOTS")
PASSWORT = "langes-test-passwort"
CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
KEIN_WEBDRIVER = "Object.defineProperty(Navigator.prototype, 'webdriver', {get: () => false});"


@pytest.fixture(scope="module")
def webspace(engine, tmp_path_factory):
    site = tmp_path_factory.mktemp("zaehler-ui") / "site"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT, mit_wetter=False)
        loipe = s.scalar(select(Loipe).join(Gebiet).where(Gebiet.slug == "kreuth").order_by(Loipe.id))
        ids = {"loipe": loipe.id, "gebiet": "kreuth"}
        generator.erzeuge(s, site, JETZT, rechtliches={"name": "Erika Muster", "anschrift": "Weg 1|83700 Ort",
                                                      "email": "kontakt@example.org"},
                          zaehler_dateien=zaehler_vorlage.dateien(s, PASSWORT, oeffentlich=True, seite=url))
        s.close()
        trans.rollback()
    proc = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(site)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield {"url": url, "ordner": site / "zaehler", **ids}
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


def kontext(browser, wie_mensch=True, breite=1280, hoehe=900, handy=False):
    ctx = browser.new_context(viewport={"width": breite, "height": hoehe}, locale="de-DE", user_agent=CHROME,
                              device_scale_factor=2 if SCREENSHOTS else 1, is_mobile=handy, has_touch=handy)
    if wie_mensch:
        ctx.add_init_script(KEIN_WEBDRIVER)
    return ctx


def summe(webspace) -> dict:
    """Aufrufe und Besucher aller Tage, direkt aus den Monatsdateien."""
    s = {"aufrufe": 0, "besucher": 0, "seiten": {}, "gebiete": {}, "loipen": {}}
    for datei in (webspace["ordner"] / "daten").glob("monat-*.php"):
        for t in json.loads(datei.read_text().split("\n", 1)[1]).values():
            s["aufrufe"] += t["aufrufe"]
            s["besucher"] += t["besucher"]
            for f in ("seiten", "gebiete", "loipen"):
                for k, n in t[f].items():
                    s[f][k] = s[f].get(k, 0) + n
    return s


def warte_auf(webspace, aufrufe, sek=6.0) -> dict:
    ende = time.time() + sek
    while time.time() < ende:
        s = summe(webspace)
        if s["aufrufe"] >= aufrufe:
            return s
        time.sleep(0.1)
    return summe(webspace)


def leeren(webspace):
    for datei in (webspace["ordner"] / "daten").glob("*.php"):
        if datei.name != "geheimnis.php":
            datei.unlink()


def oeffne(page, url):
    page.goto(url)
    page.wait_for_function("document.getElementById('view').dataset.r > 0")


@pytest.mark.req("B13", ak=[1, 4])
def test_b13_app_meldet_ansichten_einmal_je_wechsel(browser, webspace):
    leeren(webspace)
    ctx = kontext(browser)
    page = ctx.new_page()
    oeffne(page, webspace["url"] + "/#/")
    page.evaluate(f"location.hash = '#/loipe/{webspace['loipe']}'")
    warte_auf(webspace, 2)
    page.evaluate("location.hash = '#/loipen?offen=1'")
    warte_auf(webspace, 3)
    page.evaluate("location.hash = '#/loipen?offen=1&sort=name'")  # nur Filter: kein neuer Aufruf
    page.evaluate(f"location.hash = '#/gebiet/{webspace['gebiet']}'")
    s = warte_auf(webspace, 4)
    time.sleep(0.5)
    s = summe(webspace)
    assert s["aufrufe"] == 4 and s["besucher"] == 1
    assert s["seiten"] == {"heute": 1, "loipe": 1, "loipen": 1, "gebiet": 1}
    assert s["gebiete"] == {"kreuth": 2} and s["loipen"] == {str(webspace["loipe"]): 1}
    assert ctx.cookies() == []  # B13 AK 2: kein Cookie
    ctx.close()


@pytest.mark.req("B13", ak=4)
def test_b13_automatischer_browser_zaehlt_nicht(browser, webspace):
    leeren(webspace)
    ctx = kontext(browser, wie_mensch=False)  # navigator.webdriver ist wahr
    page = ctx.new_page()
    oeffne(page, webspace["url"] + "/#/karte")
    page.evaluate("location.hash = '#/loipen'")
    time.sleep(1.0)
    assert summe(webspace)["aufrufe"] == 0
    ctx.close()


@pytest.mark.req("B13", ak=[4, 5])
def test_b13_anmeldung_nimmt_browser_aus(browser, webspace):
    leeren(webspace)
    ctx = kontext(browser)
    page = ctx.new_page()
    page.goto(webspace["url"] + "/zaehler/auswertung.php")
    page.fill("input[name=passwort]", PASSWORT)
    page.click("#anmeldung button")
    page.wait_for_selector("#summen")
    assert "nicht mitgezählt" in page.inner_text("#dieser")
    oeffne(page, webspace["url"] + "/#/loipen")
    page.evaluate("location.hash = '#/karte'")
    time.sleep(1.0)
    assert summe(webspace)["aufrufe"] == 0
    # Auf Wunsch wieder mitzaehlen
    page.goto(webspace["url"] + "/zaehler/auswertung.php")
    page.fill("input[name=passwort]", PASSWORT)
    page.click("#anmeldung button")
    page.click("#dieser-knopf")
    assert "Dieser Browser wird mitgezählt." in page.inner_text("#dieser")
    oeffne(page, webspace["url"] + "/#/statistik")
    assert warte_auf(webspace, 1)["seiten"] == {"statistik": 1}
    ctx.close()


@pytest.mark.req("B13", ak=1)
def test_b13_auswertung_bildschirmfotos(browser, webspace):
    """Auswertung mit Beispielwerten fuer den laufenden Monat, Desktop und Handy (CLAUDE.md Regel 17)."""
    leeren(webspace)
    zufall = random.Random(7)
    heute = datetime.now(ZoneInfo("Europe/Berlin"))
    tag0 = int(heute.replace(day=1, hour=12, minute=0, second=0, microsecond=0).timestamp())
    befehle = []
    for tag in range(heute.day):
        for i in range(zufall.randint(3, 9)):
            seite, gebiet = zufall.choice([("heute", ""), ("karte", ""), ("gebiet", "kreuth"), ("gebiet", "tegernsee"),
                                           ("loipe", ""), ("loipen", "")])
            loipe = str(webspace["loipe"]) if seite == "loipe" else ""
            befehle.append(f"z_zaehle('{seite}', '{gebiet}', '{loipe}', '10.0.{tag}.{i}', '{CHROME}', {tag0 + tag * 86400});")
    subprocess.run(["php", "-r", f"require '{webspace['ordner']}/_kern.php'; " + " ".join(befehle)], check=True)
    for name, groesse, handy in (("desktop", (1280, 900), False), ("handy", (390, 844), True)):
        ctx = kontext(browser, breite=groesse[0], hoehe=groesse[1], handy=handy)
        page = ctx.new_page()
        page.goto(webspace["url"] + "/zaehler/auswertung.php")
        if SCREENSHOTS:
            os.makedirs(SCREENSHOTS, exist_ok=True)
            page.wait_for_timeout(700)
            page.screenshot(path=os.path.join(SCREENSHOTS, f"{name}-zaehler-anmeldung.png"))
        page.fill("input[name=passwort]", PASSWORT)
        page.click("#anmeldung button")
        page.wait_for_selector("#summen")
        breite = page.evaluate("document.documentElement.scrollWidth")
        assert breite <= groesse[0], f"{name}: waagrechtes Scrollen ({breite}px)"
        assert "Kreuth" in page.inner_text("main")
        if SCREENSHOTS:
            page.wait_for_timeout(700)  # Einblenden der Kacheln (app.css, rise) abwarten
            page.screenshot(path=os.path.join(SCREENSHOTS, f"{name}-zaehler-auswertung.png"), full_page=True)
        ctx.close()
