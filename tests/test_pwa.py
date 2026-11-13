"""Handy-App (PWA): U40 Installieren wie eine App, U41 offline der letzte Stand.

Statische Pruefungen an den erzeugten Dateien und echte Browser-Tests (Playwright, Chromium) mit
Service Worker, Offline-Modus und nachgestellten iPhone- und Android-Browsern.
"""

import functools
import http.server
import json
import os
import struct
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from loipen import generator
from tests.helpers import lade_alle_fixtures

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")


@pytest.fixture(scope="module")
def site(engine, tmp_path_factory):
    ordner = tmp_path_factory.mktemp("pwa")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, ordner, JETZT)
        s.close()
        trans.rollback()
    return ordner


def lies(site, rel):
    return (site / rel).read_text(encoding="utf-8")


# ---------- statisch ----------

@pytest.mark.req("U40", ak=1)
def test_u37_manifest_mit_maskierbarem_symbol_und_iphone_symbol(site):
    m = json.loads(lies(site, "manifest.webmanifest"))
    assert m["id"] and m["display"] == "standalone" and m["lang"] == "de"
    zwecke = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= zwecke
    for i in m["icons"]:
        png = (site / i["src"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert "x".join(map(str, struct.unpack(">II", png[16:24]))) == i["sizes"]
    html = lies(site, "index.html")
    assert 'rel="apple-touch-icon" href="icon-180.png"' in html
    assert struct.unpack(">II", (site / "icon-180.png").read_bytes()[16:24]) == (180, 180)
    assert 'name="apple-mobile-web-app-capable" content="yes"' in html


@pytest.mark.req("U40", ak=1)
def test_u37_maskierbares_symbol_hat_spuren_nur_in_der_sicheren_mitte():
    from loipen.generator.icons import png_icon
    import zlib
    png = png_icon(100, rand=0.14)
    roh = zlib.decompress(png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8])
    zeilen = [roh[y * 301 + 1:(y + 1) * 301] for y in range(100)]
    weiss = [(x, y) for y, z in enumerate(zeilen) for x in range(100) if z[3 * x:3 * x + 3] == b"\xff\xff\xff"]
    assert weiss and all(10 <= x <= 90 and 10 <= y <= 90 for x, y in weiss)  # Android-Maske: Radius 40 %


@pytest.mark.req("U40", ak=3)
def test_u37_kurzbefehle_fuer_karte_und_liste(site):
    m = json.loads(lies(site, "manifest.webmanifest"))
    assert {s["url"] for s in m["shortcuts"]} == {"./#/", "./#/karte", "./#/loipen"}


@pytest.mark.req("U41", ak=3)
def test_u38_app_version_aendert_sich_nicht_mit_den_daten(engine, tmp_path):
    """Neue Daten jede Stunde, aber die App bleibt gleich: kein stuendliches Neuladen der App auf dem Handy."""
    sw = []
    for stunden in (0, 5):
        ordner = tmp_path / str(stunden)
        with engine.connect() as conn:
            trans = conn.begin()
            s = Session(bind=conn, join_transaction_mode="create_savepoint")
            lade_alle_fixtures(s, JETZT)
            generator.erzeuge(s, ordner, JETZT + timedelta(hours=stunden))
            s.close()
            trans.rollback()
        sw.append(lies(ordner, "sw.js"))
    assert sw[0] == sw[1] and "__STAND__" not in sw[0]
    assert generator.app_version() in sw[0]


@pytest.mark.req("U41", ak=3)
def test_u38_daten_cache_ueberlebt_updates_und_wird_aufgeraeumt(site):
    sw = lies(site, "sw.js")
    assert 'DATEN_CACHE = "loipenblick-daten"' in sw  # ohne Version im Namen
    assert "k !== SCHALE_CACHE && k !== DATEN_CACHE" in sw  # beim Update bleibt der Daten-Cache
    assert "function aufraeumen" in sw and "r.datei" in sw and "r.strecken" in sw
    assert '"/abo/"' in sw  # Formulare nie aus dem Cache


@pytest.mark.req("U41", ak=4)
def test_u38_textseiten_gehoeren_zur_app_schale(site):
    sw = lies(site, "sw.js")
    for datei in ("impressum.html", "datenschutz.html", "hinweise.html", "icon-maskable-512.png", "icon-180.png"):
        assert f'"{datei}"' in sw and (site / datei).exists()


# ---------- im Browser ----------

playwright = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def basis(site):
    class Still(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Still, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = None
        for args in ({}, {"executable_path": os.environ.get("LOIPEN_CHROMIUM", "/opt/pw-browsers/chromium")}):
            try:
                b = p.chromium.launch(**args)
                break
            except Exception:
                b = None
        if b is None:
            pytest.skip("kein Chromium verfuegbar")
        yield b
        b.close()


@pytest.fixture
def kontext(browser):
    offen = []

    def neu(**kw):
        ctx = browser.new_context(locale="de-DE", **{"viewport": {"width": 390, "height": 844}, **kw})
        offen.append(ctx)
        page = ctx.new_page()
        page.fehler = []
        page.on("pageerror", lambda e: page.fehler.append(str(e)))
        return ctx, page

    yield neu
    for ctx in offen:
        ctx.close()


@pytest.mark.req("U41", ak=1)
@pytest.mark.req("U41", ak=2)
def test_u38_offline_startet_mit_letztem_stand_und_hinweis(kontext, basis):
    ctx, page = kontext()
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    page.evaluate("() => navigator.serviceWorker.ready")
    page.reload()  # jetzt steuert der Service Worker die Seite und speichert die Daten
    page.wait_for_selector("#view > *")
    page.wait_for_function("() => !!navigator.serviceWorker.controller")
    assert page.locator("#netz").is_hidden()
    page.wait_for_function("() => caches.open('loipenblick-daten').then(c => c.keys()).then(k => k.length >= 2)")

    ctx.set_offline(True)
    page.reload()
    page.wait_for_selector("#view > *")
    assert "nicht geladen" not in page.locator("#view").inner_text()
    netz = page.locator("#netz")
    netz.wait_for(state="visible")
    assert "Offline" in netz.inner_text() and "gespeicherten Stand vom 09.11.2026" in netz.inner_text()
    page.goto(f"{basis}/#/loipen")  # andere Ansicht, weiterhin offline
    page.wait_for_selector("#view .lp")
    page.goto(f"{basis}/impressum.html")
    assert "Impressum" in page.content()

    ctx.set_offline(False)
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    assert page.locator("#netz").is_hidden()
    assert page.fehler == []


@pytest.mark.req("U40", ak=2)
def test_u37_iphone_zeigt_anleitung_und_merkt_nicht_jetzt(kontext, basis):
    ctx, page = kontext(user_agent=IPHONE, is_mobile=True, has_touch=True)
    page.goto(f"{basis}/#/")
    hinweis = page.locator("#app-hinweis")
    hinweis.wait_for()
    assert "Teilen" in hinweis.inner_text() and "Zum Home-Bildschirm" in hinweis.inner_text()
    assert page.locator("#app-knopf").is_visible()
    page.click("#app-spaeter")
    assert hinweis.count() == 0
    page.reload()
    page.wait_for_selector("#view > *")
    assert page.locator("#app-hinweis").count() == 0  # 30 Tage Ruhe
    page.click("#app-knopf")  # ueber die Fusszeile geht es trotzdem
    assert "Zum Home-Bildschirm" in page.locator("#app-hinweis").inner_text()
    assert page.fehler == []


@pytest.mark.req("U40", ak=2)
def test_u37_android_knopf_ruft_den_installationsdialog(kontext, basis):
    ctx, page = kontext(is_mobile=True, has_touch=True)
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    assert page.locator("#app-hinweis").count() == 0  # ohne Angebot des Browsers kein Hinweis
    assert page.locator("#app-knopf").is_hidden()
    page.evaluate("""() => {
        const ev = new Event('beforeinstallprompt', {cancelable: true});
        ev.prompt = () => { window.__gefragt = true; };
        ev.userChoice = Promise.resolve({outcome: 'accepted'});
        window.dispatchEvent(ev);
    }""")
    page.locator("#app-install").click()
    assert page.evaluate("window.__gefragt") is True
    page.locator("#app-hinweis").wait_for(state="detached")
    assert page.fehler == []


@pytest.mark.req("U40", ak=2)
def test_u37_kein_hinweis_in_der_installierten_app(kontext, basis):
    ctx, page = kontext(user_agent=IPHONE, is_mobile=True, has_touch=True)
    page.add_init_script("Object.defineProperty(navigator, 'standalone', {get: () => true})")
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    assert page.locator("#app-hinweis").count() == 0 and page.locator("#app-knopf").is_hidden()
    assert page.fehler == []
