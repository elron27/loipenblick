"""U46 / E-28: dezenter Spendenlink, nur aus LOIPEN_SPENDEN_URL, ohne Fremdskript."""

import functools
import http.server
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from loipen import generator
from loipen.config import Settings
from loipen.worker import __main__ as worker
from tests.helpers import lade_alle_fixtures

JETZT = datetime(2026, 12, 10, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
PAYPAL = "https://paypal.me/LoipenblickTest"
RECHT = {"name": "Erika Muster", "anschrift": "Musterweg 1|83700 Rottach-Egern", "email": "kontakt@example.org"}
TEXTSEITEN = ("impressum.html", "datenschutz.html", "hinweise.html", "404.html")


ARTEN = {"ohne": None, "mit": PAYPAL, "ungueltig": "javascript:alert(1)"}


@pytest.fixture(scope="module")
def sites(engine, tmp_path_factory):
    """Die Seite einmal je Variante erzeugen (das Laden aller Fixtures dauert)."""
    ziele = {art: tmp_path_factory.mktemp(art) for art in ARTEN}
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        for art, url in ARTEN.items():
            generator.erzeuge(s, ziele[art], JETZT, rechtliches={**RECHT, "spenden_url": url})
        s.close()
        trans.rollback()
    return ziele


def lies(site: Path, name: str) -> str:
    return (site / name).read_text(encoding="utf-8")


# ---------- Generator ----------

@pytest.mark.req("U46", ak=1)
def test_u45_ohne_adresse_kein_spendenlink(sites):
    site = sites["ohne"]
    assert "spenden" not in json.loads(lies(site, "daten.json"))
    for name in TEXTSEITEN:
        assert "unterstützen" not in lies(site, name).lower(), name
    assert 'id="spenden" class="fine spenden" hidden' in lies(site, "index.html")
    assert 'id="spenden-kopf" href="hinweise.html#unterstuetzen" title="Loipenblick unterstützen" hidden' in lies(site, "index.html")
    assert all("spenden-kopf" not in lies(site, name) for name in TEXTSEITEN)


@pytest.mark.req("U46", ak=2)
def test_u45_link_in_fusszeile_und_hinweisen_mit_freiwillig_ohne_gegenleistung(sites):
    site = sites["mit"]
    assert json.loads(lies(site, "daten.json"))["spenden"] == {"url": PAYPAL, "anbieter": "PayPal"}
    for name in TEXTSEITEN:  # Fusszeile jeder Textseite
        assert f'<a href="{PAYPAL}" rel="noopener noreferrer">über PayPal unterstützen</a>' in lies(site, name), name
    for name in TEXTSEITEN:  # Herz in der Kopfzeile jeder Textseite
        assert 'class="spenden-kopf" href="hinweise.html#unterstuetzen"' in lies(site, name), name
    hinweise = lies(site, "hinweise.html")
    assert 'id="unterstuetzen"' in hinweise
    for satz in ("freiwillig", "keine Gegenleistung", "Spendenquittung ist nicht möglich", "Privatperson"):
        assert satz in hinweise, satz


@pytest.mark.req("U46", ak=2)
@pytest.mark.parametrize("url, anbieter", [
    ("https://paypal.me/Name", "PayPal"),
    ("https://www.paypal.com/donate/?hosted_button_id=ABC", "PayPal"),
    ("https://buymeacoffee.com/name", "Buy Me a Coffee"),
    ("https://www.buymeacoffee.com/name", "Buy Me a Coffee"),
    ("https://ko-fi.com/name", "Ko-fi"),
    ("https://spenden.example.org/loipen", "spenden.example.org"),
])
def test_u45_anbieter_aus_der_adresse(url, anbieter):
    assert generator.spenden(url) == {"url": url, "anbieter": anbieter}


@pytest.mark.req("U46", ak=3)
@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "http://paypal.me/Name", "paypal.me/Name", "https://", "data:text/html,x",
    'https://paypal.me/x" onclick="alert(1)', "https://paypal.me/x<script>", "  ",
])
def test_u45_nur_https_adressen_sonst_warnung(url, caplog):
    with caplog.at_level(logging.WARNING, logger="loipen.generator"):
        assert generator.spenden(url) is None
    assert ("LOIPEN_SPENDEN_URL" in caplog.text) == bool(url.strip())


@pytest.mark.req("U46", ak=3)
def test_u45_ungueltige_adresse_erscheint_nirgends(sites):
    site = sites["ungueltig"]
    assert "spenden" not in json.loads(lies(site, "daten.json"))
    for name in TEXTSEITEN:
        assert "javascript:" not in lies(site, name)


@pytest.mark.req("U46", ak=4)
def test_u45_datenschutz_nennt_anbieter_nur_mit_link(sites):
    assert "PayPal" not in lies(sites["ohne"], "datenschutz.html")
    ds = lies(sites["mit"], "datenschutz.html")
    assert "<h2>Unterstützen über PayPal</h2>" in ds and "gewöhnlicher Link" in ds
    assert "Art. 6 Abs. 1 lit. b DSGVO" in ds


@pytest.mark.req("U46")
def test_u45_adresse_kommt_aus_der_env(monkeypatch):
    monkeypatch.setenv("LOIPEN_SPENDEN_URL", PAYPAL)
    assert worker.rechtliches(Settings(_env_file=None))["spenden_url"] == PAYPAL
    monkeypatch.delenv("LOIPEN_SPENDEN_URL")
    assert worker.rechtliches(Settings(_env_file=None))["spenden_url"] is None


# ---------- Oberflaeche ----------

playwright = pytest.importorskip("playwright.sync_api")


def _server(site: Path):
    class Still(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Still, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture(scope="module")
def seiten(sites):
    server = {art: _server(sites[art]) for art in ("ohne", "mit")}
    yield {art: f"http://127.0.0.1:{s.server_address[1]}" for art, s in server.items()}
    for s in server.values():
        s.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
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


def oeffne(browser, basis, pfad="/#/", breite=1280):
    ctx = browser.new_context(viewport={"width": breite, "height": 900}, locale="de-DE")
    page = ctx.new_page()
    fehler, anfragen = [], []
    page.on("pageerror", lambda e: fehler.append(str(e)))
    page.on("request", lambda r: anfragen.append(r.url))
    page.goto(basis + pfad)
    page.wait_for_load_state("networkidle")
    return ctx, page, fehler, anfragen


@pytest.mark.req("U46", ak=1)
def test_u45_app_ohne_adresse_zeigt_keinen_link(browser, seiten):
    ctx, page, fehler, _ = oeffne(browser, seiten["ohne"])
    page.wait_for_selector("#view > *")
    assert page.locator("#spenden").is_hidden()
    assert page.locator("#spenden-kopf").is_hidden()
    assert fehler == []
    ctx.close()


@pytest.mark.req("U46", ak=[2, 4])
@pytest.mark.parametrize("breite", [1280, 360])
def test_u45_app_zeigt_link_in_fusszeile_ohne_anfrage_an_den_anbieter(browser, seiten, breite):
    for pfad in ("/#/", "/hinweise.html"):
        ctx, page, fehler, anfragen = oeffne(browser, seiten["mit"], pfad, breite)
        link = page.locator("footer .spenden a")
        link.wait_for()
        assert link.get_attribute("href") == PAYPAL
        assert "noopener" in link.get_attribute("rel")
        assert link.inner_text() == "über PayPal unterstützen"
        herz = page.locator("header .spenden-kopf")  # Herz oben: fuehrt erst zur Erklaerung
        assert herz.is_visible() and herz.get_attribute("href") == "hinweise.html#unterstuetzen"
        assert herz.get_attribute("title") == "Loipenblick unterstützen"
        basis = seiten["mit"]
        assert [u for u in anfragen if not u.startswith(basis)] == []  # B23: nichts von Dritten, auch nicht PayPal
        assert page.evaluate("document.documentElement.scrollWidth") <= breite
        assert fehler == []
        ctx.close()
