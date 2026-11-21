"""Merkliste "Meine Loipen" (U7), Abo fuer alle gemerkten Loipen (N12) und Push-Themen (N10) im echten Browser.

Die Seite wird mit Abo- und Push-Konfiguration erzeugt und vom eingebauten PHP-Server ausgeliefert, so wie
spaeter vom Webspace. Ohne PHP oder Chromium werden die Tests uebersprungen.
"""

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
from loipen.benachrichtigung import PushKonfig
from loipen.generator import abo as abo_vorlage
from loipen.mailabo import AboKonfig
from loipen.models import Gebiet, Loipe
from tests.helpers import lade_alle_fixtures
from tests.test_abo_ui import browser, foto, neue_seite  # noqa: F401  (Fixture und Hilfen teilen)

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.skipif(shutil.which("php") is None, reason="PHP nicht installiert")

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
PUSH = PushKonfig(praefix="lb-test", server="https://ntfy.example")


@pytest.fixture(scope="module")
def webspace(engine, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("merkliste-ui")
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
        lps = s.scalars(select(Loipe).join(Gebiet).where(Gebiet.slug == "kreuth").order_by(Loipe.id)).all()[:2]
        ids = {"loipen": [(l.id, l.name) for l in lps]}
        generator.erzeuge(s, site, JETZT, rechtliches={"name": "Erika Muster", "anschrift": "Weg 1|83700 Ort",
                                                      "email": "kontakt@example.org"},
                          abo_dateien=abo_vorlage.dateien(s, cfg, meldungen_an="kontakt@example.org"),
                          push=PUSH.fuer_seite())
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


def merke_beide(page, webspace):
    for lid, _ in webspace["loipen"]:
        page.goto(f"{webspace['url']}/#/loipe/{lid}")
        page.wait_for_selector("button.merken")
        assert page.inner_text("button.merken") == "Merken"
        page.click("button.merken")
        assert page.get_attribute("button.merken", "aria-pressed") == "true"
        assert page.inner_text("button.merken") == "Gemerkt"


@pytest.mark.req("U7", ak=[1, 2])
def test_u7_merken_bleibt_nach_dem_neuladen(browser, webspace):
    ctx, page = neue_seite(browser)
    merke_beide(page, webspace)
    foto(page, "desktop-loipe-gemerkt")
    page.reload()
    page.wait_for_selector("button.merken")
    assert page.inner_text("button.merken") == "Gemerkt"
    # wieder entfernen
    page.click("button.merken")
    assert page.inner_text("button.merken") == "Merken"
    page.reload()
    page.wait_for_selector("button.merken")
    assert page.inner_text("button.merken") == "Merken"
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("U7", ak=3)
def test_u7_meine_loipen_auf_startseite_und_eigener_seite(browser, webspace):
    ctx, page = neue_seite(browser, 390, 844, handy=True)
    page.goto(f"{webspace['url']}/#/meine")
    page.wait_for_selector("#meine-leer")
    merke_beide(page, webspace)
    page.goto(f"{webspace['url']}/#/")
    page.wait_for_selector("#meine-kurz")
    kurz = page.inner_text("#meine-kurz")
    for _, name in webspace["loipen"]:
        assert name in kurz
    page.locator("#meine-kurz").scroll_into_view_if_needed()
    foto(page, "handy-heute-meine-loipen")
    page.click("#meine-kurz .kopf a")
    page.wait_for_selector("#meine-liste")
    assert page.locator("#meine-liste .mz").count() == 2
    foto(page, "handy-meine-loipen")
    # Entfernen auf der Seite selbst
    page.click("#meine-liste .mz:first-child button.weg")
    page.wait_for_function("document.querySelectorAll('#meine-liste .mz').length === 1")
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("N12", ak=1)
def test_n12_ein_abo_fuer_alle_gemerkten_loipen(browser, webspace):
    ctx, page = neue_seite(browser)
    merke_beide(page, webspace)
    page.goto(f"{webspace['url']}/#/meine")
    page.wait_for_selector("#abo")
    ziele = page.eval_on_selector_all("#abo input[name='ziel[]']", "els => els.map(e => e.value)")
    assert ziele == [f"l:{lid}" for lid, _ in webspace["loipen"]]
    page.click("#abo summary")
    page.fill("#abo input[name=email]", "fav@example.org")
    page.check("#abo input[name=einwilligung]")
    page.locator("#abo").scroll_into_view_if_needed()
    foto(page, "desktop-meine-abo")
    page.click("#abo button[type=submit]")
    page.wait_for_selector("#abo .antwort.gut")
    text = webspace["mails"].read_text(encoding="utf-8")
    teil = text.split("To: fav@example.org", 1)[1]
    for _, name in webspace["loipen"]:
        assert name in teil.split("----ENDE----")[0], name
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("N10", ak=[1, 5])
@pytest.mark.req("N12", ak=2)
def test_n10_push_themen_auf_loipe_gebiet_und_meine_loipen(browser, webspace):
    ctx, page = neue_seite(browser, 390, 844, handy=True)
    anfragen = []
    page.on("request", lambda r: anfragen.append(r.url))
    lid, name = webspace["loipen"][0]
    page.goto(f"{webspace['url']}/#/loipe/{lid}")
    page.wait_for_selector("#push")
    page.click("#push summary")
    links = page.eval_on_selector_all("#push a.btn", "els => els.map(e => e.href)")
    assert links == [f"https://ntfy.example/lb-test-l{lid}", "https://ntfy.example/lb-test-g-kreuth"]
    assert f"lb-test-l{lid}" in page.inner_text("#push")
    page.locator("#push").scroll_into_view_if_needed()
    foto(page, "handy-loipe-push")
    # Gebietsseite: nur das Gebietsthema
    page.goto(f"{webspace['url']}/#/gebiet/kreuth")
    page.wait_for_selector("#push")
    assert page.eval_on_selector_all("#push a.btn", "els => els.map(e => e.href)") == ["https://ntfy.example/lb-test-g-kreuth"]
    # Meine Loipen: ein Thema je gemerkter Loipe
    merke_beide(page, webspace)
    page.goto(f"{webspace['url']}/#/meine")
    page.wait_for_selector("#push")
    assert page.eval_on_selector_all("#push a.btn", "els => els.map(e => e.href)") == [
        f"https://ntfy.example/lb-test-l{i}" for i, _ in webspace["loipen"]]
    # N10 AK 5: die Seite selbst hat nichts von ntfy geladen
    assert not [u for u in anfragen if "ntfy" in u]
    assert page.fehler == []
    ctx.close()
