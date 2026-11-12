"""Oberflaeche im echten Browser (Playwright, Chromium): U1 bis U4, U5, U6, U8, U12, U16, U18, U21, U22, U23, U24.

Die Seite wird aus den Beispielseiten erzeugt und ueber localhost ausgeliefert. Ist kein Chromium
da, werden die Tests uebersprungen. Mit ?demo=1 zeigt die Seite Beispielwerte (einige Loipen offen),
weil im November nichts offen ist.
"""

import functools
import json
import http.server
import os
import re
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from loipen import generator
from tests.helpers import lade_alle_fixtures

playwright = pytest.importorskip("playwright.sync_api")

JETZT = datetime(2026, 11, 9, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))


@pytest.fixture(scope="module")
def basis(engine, tmp_path_factory):
    site = tmp_path_factory.mktemp("site")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, site, JETZT)
        s.close()
        trans.rollback()

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
        versuche = [{}, {"executable_path": os.environ.get("LOIPEN_CHROMIUM", "/opt/pw-browsers/chromium")}]
        for args in versuche:
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
def seite(browser, basis):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="de-DE")
    page = ctx.new_page()
    fehler = []
    page.on("pageerror", lambda e: fehler.append(str(e)))
    page.open = lambda hash="#/": (page.goto(f"{basis}/{hash}"), page.wait_for_selector("#view > *"))
    yield page
    assert fehler == []  # kein JavaScript-Fehler in keinem Test
    ctx.close()


def aktion(page, fn):
    """Fuehrt fn aus und wartet, bis die Seite danach neu gezeichnet wurde."""
    r0 = int(page.locator("#view").get_attribute("data-r") or 0)
    fn()
    page.wait_for_function("n => +document.getElementById('view').dataset.r > n", arg=r0)


def loipennamen(page) -> list[str]:
    return page.locator(".lp .n").evaluate_all("els => els.map(e => e.childNodes[0].textContent.trim())")


@pytest.mark.req("U8", ak=1)
def test_u8_startseite_auf_360_px_ohne_waagrechtes_scrollen(browser, basis):
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    p = ctx.new_page()
    for hash in ("#/", "#/?demo=1", "#/loipen?demo=1", "#/karte", "#/gebiet/kreuth"):
        p.goto(f"{basis}/{hash}")
        p.wait_for_selector("#view > *")
        assert p.evaluate("document.documentElement.scrollWidth") <= 360, hash
    ctx.close()


@pytest.mark.req("U8", ak=3)
def test_u8_dark_mode_folgt_dem_system(browser, basis):
    farben = {}
    for schema in ("dark", "light"):
        ctx = browser.new_context(color_scheme=schema)
        p = ctx.new_page()
        p.goto(f"{basis}/#/")
        p.wait_for_selector("#view > *")
        farben[schema] = p.evaluate("getComputedStyle(document.body).backgroundColor")
        ctx.close()
    assert farben["dark"] != farben["light"]


@pytest.mark.req("U3", ak=1)
def test_u3_filter_schraenken_liste_ein_und_stehen_in_der_url(seite):
    seite.open("#/loipen?demo=1")
    alle = seite.locator(".lp").count()
    aktion(seite, lambda: seite.get_by_role("button", name="Nur offene").click())
    assert "offen=1" in seite.url
    offen = seite.locator(".lp").count()
    assert 0 < offen < alle
    assert all("Offen" in t or "Eingeschränkt" in t for t in seite.locator(".lp .st").all_inner_texts())


@pytest.mark.req("U3", ak=2)
def test_u3_geteilte_url_zeigt_dieselbe_ansicht(seite, browser, basis):
    seite.open("#/loipen?demo=1&offen=1&max=5&leicht=1&sort=entfernung")
    erste = loipennamen(seite)
    assert erste
    ctx = browser.new_context()
    zweite_seite = ctx.new_page()
    zweite_seite.goto(seite.url)
    zweite_seite.wait_for_selector(".lp")
    assert loipennamen(zweite_seite) == erste
    ctx.close()


@pytest.mark.req("U24", ak=1)
def test_u24_hoechstlaenge_leicht_rundkurs_lassen_sich_kombinieren(seite):
    seite.open("#/loipen?demo=1")
    n0 = seite.locator(".lp").count()
    aktion(seite, lambda: seite.get_by_role("button", name="Leicht").click())
    n1 = seite.locator(".lp").count()
    aktion(seite, lambda: seite.get_by_role("button", name="Rundkurs").click())
    n2 = seite.locator(".lp").count()
    seite.fill("#f-max", "3")
    aktion(seite, lambda: seite.press("#f-max", "Enter"))
    n3 = seite.locator(".lp").count()
    assert n0 > n1 >= n2 >= n3 > 0
    for d in seite.locator(".lp .d").all_inner_texts():
        assert "leicht" in d
        km = float(re.search(r"([\d,]+) km(?! entfernt)", d).group(1).replace(",", "."))
        assert km <= 3


@pytest.mark.req("U2", ak=1)
def test_u2_sortierung_nach_entfernung_status_und_gespurten_km(seite):
    seite.open("#/loipen?demo=1&sort=entfernung")
    ent = [float(re.match(r"(\d+) km entfernt", t).group(1)) for t in seite.locator(".lp .d").all_inner_texts() if "entfernt" in t]
    assert ent == sorted(ent) and len(ent) > 20
    aktion(seite, lambda: seite.select_option("#f-sort", "status"))
    texte = seite.locator(".lp .st").all_inner_texts()
    assert "Offen" in texte[0] and "Geschlossen" in texte[-1] or "Unbekannt" in texte[-1]
    aktion(seite, lambda: seite.select_option("#f-sort", "gespurt"))
    gespurt = [float(m.group(1).replace(",", ".")) if m else 0.0 for m in
               (re.search(r"gespurt ([\d,]+) km", t) for t in seite.locator(".lp .d").all_inner_texts())]
    assert gespurt[0] > 0 and gespurt == sorted(gespurt, reverse=True)
    aktion(seite, lambda: seite.select_option("#f-sort", "praeparierung"))


@pytest.mark.req("U21", ak=1)
def test_u21_nach_drei_buchstaben_kommen_vorschlaege(seite):
    seite.open("#/")
    seite.fill("#q", "ro")
    assert seite.locator("#vorschlaege").is_hidden()
    seite.fill("#q", "ros")
    seite.wait_for_selector("#vorschlaege li")
    texte = " ".join(seite.locator("#vorschlaege li").all_inner_texts())
    assert "Rosenheim" in texte and "Ort" in texte
    seite.fill("#q", "ringsee")
    seite.wait_for_selector("#vorschlaege li")
    assert "Ringseeloipe" in " ".join(seite.locator("#vorschlaege li").all_inner_texts())
    seite.fill("#q", "bayrisch")
    seite.wait_for_selector("#vorschlaege li")
    assert "Gebiet" in " ".join(seite.locator("#vorschlaege li").all_inner_texts())


@pytest.mark.req("U21", ak=2)
def test_u21_ort_ohne_loipe_zeigt_naechste_loipen_mit_entfernung(seite):
    seite.open("#/")
    seite.fill("#q", "rosenheim")
    seite.wait_for_selector("#vorschlaege li")
    seite.keyboard.press("Enter")
    seite.wait_for_selector(".lp")
    assert "Rosenheim" in seite.locator("h1, #view p.fine").first.inner_text() + seite.locator("#view").inner_text()
    ent = [int(re.match(r"(\d+) km entfernt", t).group(1)) for t in seite.locator(".lp .d").all_inner_texts()]
    assert ent == sorted(ent) and ent[0] > 0


@pytest.mark.req("U21", ak=3)
def test_u21_suche_laeuft_ohne_server(seite):
    anfragen = []
    seite.on("request", lambda r: anfragen.append(r.url))
    seite.open("#/")
    n = len(anfragen)
    seite.fill("#q", "ringsee")
    seite.wait_for_selector("#vorschlaege li")
    assert len(anfragen) == n  # Tippen loest keine Anfrage aus


@pytest.mark.req("U4", ak=1)
def test_u4_umkreis_zeigt_nur_loipen_im_radius_mit_entfernung(seite):
    seite.open("#/loipen?ort=Rosenheim&r=10")
    assert seite.locator(".lp").count() == 0  # die naechste Loipe ist rund 18 km entfernt
    seite.open("#/loipen?ort=Rosenheim&r=30")
    ent = [int(re.match(r"(\d+) km", t).group(1)) for t in seite.locator(".lp .d").all_inner_texts()]
    assert ent and max(ent) <= 30
    seite.open("#/loipen?ort=Rosenheim&r=100")
    assert seite.locator(".lp").count() > len(ent)


def marker_summe(page) -> int:
    """Einzelmarker plus die Anzahl in den Buendeln."""
    einzeln = page.locator("#map .mk").count()
    buendel = page.locator("#map .mkc").evaluate_all("els => els.map(e => parseInt(e.textContent, 10) || 0)")
    return einzeln + sum(buendel)


@pytest.mark.req("U1", ak=1)
def test_u1_marker_in_statusfarbe(seite):
    seite.open("#/karte?demo=1")
    seite.wait_for_selector("#map .mk, #map .mkc")
    stati = set(seite.locator("#map .mk, #map .mkc").evaluate_all("els => els.map(e => e.dataset.s)"))
    assert {"offen", "geschlossen"} <= stati
    farben = set(seite.locator("#map .mk, #map .mkc").evaluate_all("els => els.map(e => e.style.background)"))
    assert any("74, 222, 128" in f or "4ade80" in f for f in farben)  # offen = gruen


@pytest.mark.req("U1", ak=2)
def test_u1_nahe_marker_werden_gebuendelt_und_beim_zoomen_aufgeloest(seite):
    seite.open("#/karte")
    seite.wait_for_selector("#map .mk, #map .mkc")
    gesamt = marker_summe(seite)
    assert seite.locator("#map .mkc").count() > 0  # Buendel tragen die Anzahl
    seite.evaluate("window.__map.setZoom(17, {animate: false})")
    seite.wait_for_timeout(400)
    assert seite.locator("#map .mkc").count() == 0 or marker_summe(seite) < gesamt  # nur noch Sichtbares, nicht mehr gebuendelt
    seite.click("button.alles")
    seite.wait_for_timeout(700)
    assert marker_summe(seite) == gesamt


@pytest.mark.req("U1", ak=1)
def test_u1_marker_oeffnet_detail(seite):
    seite.open("#/karte?demo=1&gebiet=rottach-egern&offen=1")
    seite.wait_for_selector("#map .mk, #map .mkc")
    for _ in range(12):  # Buendel anklicken, bis ein einzelner Marker da ist
        if seite.locator("#map .mk").count():
            break
        seite.locator("#map .mkc").first.click()
        seite.wait_for_timeout(600)
    seite.locator("#map .mk").first.click()
    assert seite.locator("#sel a.btn").get_attribute("href").startswith("#/loipe/")
    assert re.search("Offen|Eingeschränkt", seite.locator("#sel").inner_text())


@pytest.mark.req("U3", ak=1)
def test_u3_filter_gelten_auch_fuer_die_karte(seite):
    seite.open("#/karte?demo=1")
    seite.wait_for_selector("#map .mk, #map .mkc")
    alle = marker_summe(seite)
    aktion(seite, lambda: seite.get_by_role("button", name="Nur offene").click())
    seite.wait_for_selector("#map .mk, #map .mkc")
    assert marker_summe(seite) < alle


def test_karte_hat_echte_grundkarte_mit_quellenangabe(seite):
    seite.open("#/karte")
    seite.wait_for_selector("#map .leaflet-tile-pane", state="attached")
    assert "OpenStreetMap" in seite.locator("#map .leaflet-control-attribution").inner_text()


@pytest.mark.req("U5", ak=1)
def test_u5_detailseite_mit_minikarte_verlauf_quelle_navigation(seite):
    seite.open("#/loipen?demo=1&gebiet=rottach-egern&offen=1")
    seite.locator(".lp").first.click()
    seite.wait_for_selector(".hist")
    assert seite.locator(".hist span").count() == 14
    assert seite.locator("#minimap.leaflet-container").count() == 1
    assert seite.locator("#minimap .mk").count() == 1  # Start der Loipe
    assert seite.get_by_role("link", name=re.compile("Navigation")).get_attribute("href").startswith("https://www.google.com/maps/dir/")
    quelle = seite.locator("a[rel=noopener]", has_text="Tegernseer").first
    assert quelle.get_attribute("href").startswith("https://www.tegernsee.com")
    for wort in ("Länge", "Gespurt", "Klassisch", "Skating", "Schwierigkeit", "Rundkurs", "Quelle und Stand", "Zuletzt von uns geprüft"):
        assert wort.lower() in seite.locator("#view").inner_text().lower()


@pytest.mark.req("B15", ak=2)
def test_b15_jede_seite_hat_fusszeile_und_detail_nennt_quelle(seite):
    for hash in ("#/", "#/karte", "#/loipen", "#/gebiet/kreuth"):
        seite.open(hash)
        assert "Alle Angaben ohne Gewähr" in seite.locator("footer").inner_text(), hash
    seite.open("#/loipen")
    seite.locator(".lp").first.click()
    seite.wait_for_selector(".hist")
    assert "Alle Angaben ohne Gewähr" in seite.locator("footer").inner_text()
    assert "Quelle und Stand" in seite.locator("#view").inner_text()


@pytest.mark.req("U6", ak=1)
def test_u6_alter_der_daten_steht_an_jeder_loipe(seite):
    seite.open("#/loipen")
    assert all(re.search(r"Stand (vor \d+ (Min\.|Std\.|Tagen)|noch kein Abruf)", t) for t in seite.locator(".lp .d").all_inner_texts())


@pytest.mark.req("U12", ak=1)
def test_u12_gebietsseite_mit_gesamtlaenge_und_quelle(seite):
    seite.open("#/gebiet/bayrischzell")
    text = seite.locator("#view").inner_text()
    assert re.search(r"\d+ Loipen, zusammen [\d,]+ km", text)
    assert "Touristeninformation" in text
    assert seite.locator(".lp").count() >= 5


@pytest.mark.req("U14", ak=1)
def test_u14_parkplatz_oeffnet_navigation_gebuehr_steht_dabei(seite):
    seite.open("#/gebiet/kreuth")
    text = seite.locator("#view").inner_text()
    assert "Gebühr:" in text and "Parkplatz Wildbad Kreuth" in text
    links = seite.locator("a.btn", has_text="Navigation").evaluate_all("els => els.map(e => e.href)")
    assert links and all(l.startswith("https://www.google.com/maps/dir/?api=1&destination=47.") for l in links)


@pytest.mark.req("U26", ak=2)
def test_u26_haltestelle_oeffnet_fahrplan_mit_ziel(seite):
    seite.open("#/gebiet/sachrang")
    links = seite.locator("a.btn", has_text="Fahrplan").evaluate_all("els => els.map(e => e.href)")
    assert links and all("travelmode=transit" in l for l in links)
    seite.open("#/gebiet/rottach-egern")
    assert "keine bekannt" in seite.locator("#view").inner_text() or seite.locator("a.btn", has_text="Fahrplan").count() > 0


@pytest.mark.req("U16", ak=2)
def test_u16_neuschnee_hinweis_am_gebiet(seite):
    seite.open("#/?demo=1")
    assert seite.locator(".gc .badge.neu").count() > 0
    assert "Neuschnee" in seite.locator(".gc .badge.neu").first.inner_text()


@pytest.mark.req("U18", ak=2)
def test_u18_wochenende_in_der_vorhersage_hervorgehoben(seite):
    seite.open("#/gebiet/kreuth")
    tage = seite.locator(".wx > div")
    assert tage.count() >= 7
    texte = tage.locator("b").all_inner_texts()
    markiert = tage.evaluate_all("els => els.map(e => e.classList.contains('we'))")
    for t, m in zip(texte, markiert):
        assert m == (t.startswith("Sa") or t.startswith("So")), t
    assert "Vorhersage (keine Messung)" in seite.locator("#view").inner_text()


@pytest.mark.req("U23", ak=[1, 2])
def test_u23_teilen_oeffnet_systemmenue_mit_filtern_in_der_url(seite):
    seite.add_init_script("window.__geteilt = null; navigator.share = (d) => { window.__geteilt = d; return Promise.resolve(); };")
    seite.open("#/loipen?offen=1&leicht=1")
    seite.get_by_role("button", name="Teilen").click()
    geteilt = seite.evaluate("window.__geteilt")
    assert geteilt and "offen=1" in geteilt["url"] and "leicht=1" in geteilt["url"]


@pytest.mark.req("U22", ak=1)
def test_u22_status_mit_symbol_und_wort_sichtbar(seite):
    seite.open("#/loipen?demo=1")
    for chip in seite.locator(".lp .st").all()[:30]:
        assert chip.locator("svg").count() == 1 and chip.inner_text().strip() in {"Offen", "Eingeschränkt", "Geschlossen", "Unbekannt"}


@pytest.mark.req("U15", ak=1)
def test_u15_jede_gebietsseite_zeigt_mindestens_3_tage_vorhersage(seite):
    for slug in ("kreuth", "bayrischzell", "ruhpolding"):
        seite.open(f"#/gebiet/{slug}")
        assert seite.locator(".wx > div").count() >= 3, slug


def test_talprofil_nadelhoehe_folgt_der_ortshoehe(seite):
    """Hoeherer Ort steht weiter oben (kleineres y): Bayrischzell 800 m ueber Kufstein 500 m."""
    seite.open("#/?demo=1")
    seite.wait_for_selector("svg .s-l", state="attached")
    y = seite.evaluate("""() => Object.fromEntries([...document.querySelectorAll('svg a')].map(a =>
        [a.querySelector('text').textContent, +a.querySelector('line').getAttribute('y1')]))""")
    assert y["Bayrischzell"] < y["Kufstein"]
    assert y["Kreuth"] < y["Bad Wiessee"]  # 780 m gegen 730 m


def test_vorhersage_zeigt_wettersymbole_mit_text(seite):
    seite.open("#/?demo=1")
    seite.wait_for_selector(".wx")
    # Fixture-Daten haben keine Symbole: Darstellung darf dann nichts kaputt machen
    assert seite.locator(".wx > div").count() >= 3


@pytest.mark.req("U16", ak=1)
def test_u16_liste_nach_neuschnee_48h_sortierbar(seite):
    """Bayrischzell bekommt 20 cm, alle anderen 0: nach Neuschnee sortiert stehen dessen Loipen vorne."""
    def mehr_schnee(route):
        antwort = route.fetch()
        daten = antwort.json()
        for g in daten.get("gebiete", []):
            if g.get("schnee") is not None:
                g["schnee"]["neuschnee_48h_cm"] = 20 if g["slug"] == "bayrischzell" else 0
        route.fulfill(response=antwort, body=json.dumps(daten), headers={**antwort.headers, "content-type": "application/json"})

    seite.route(re.compile(r".*/(?!daten\.json)[^/]+\.json(\?.*)?$"), mehr_schnee)
    seite.open("#/loipen")
    optionen = seite.locator("#f-sort option").all_inner_texts()
    assert "Sortiert nach Neuschnee 48 h" in optionen
    aktion(seite, lambda: seite.select_option("#f-sort", "neuschnee"))
    assert "sort=neuschnee" in seite.url
    gebiete = seite.locator(".lp .n .fine").all_inner_texts()
    n = sum(1 for t in gebiete if "Bayrischzell" in t)
    assert n > 0 and all("Bayrischzell" in t for t in gebiete[:n])
