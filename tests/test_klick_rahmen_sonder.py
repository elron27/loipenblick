"""Befunde vom NAS-Test am 13.11.2026: Loipen oeffnen sich zuverlaessig (U42), Rahmendaten je Gebiet und
Region (U43), Sonderloipen (U44) und Laenge/Stil der tirol.at-Loipen aus der Liste (P25).

Schnappschuss: tests/fixtures/tirol/2026-11-13/ (Listen mit 12 geoeffneten Loipen, darunter
Snowfarming Leutasch, SnowFactory Seefeld, Opening Sedlsee, Hoehenloipe Pitztaler Gletscher).
"""

import re

import pytest

from loipen.adapters.tirolat import (TirolAtAdapter, listen_daten, listen_pfade, marker, naechste_seite, slug,
                                     technik_aus_stilen)
from loipen.models import Technik
from loipen.sonderloipen import sonderloipe
from tests.helpers import SEITEN_QUELLEN, TIROL_LISTE, FixtureFetcher
from tests.test_adapter_tirol import Q, konfig
from tests.test_website_ui import JETZT, aktion, basis, browser, seite  # noqa: F401  (Fixtures)

OFFEN_URL = f"{TIROL_LISTE}?addressbaseOpened%5B209%5D%5B%5D=OPEN"
SEITE2_URL = f"{TIROL_LISTE}?addressbaseOpened%5B209%5D%5B0%5D=OPEN&listpos=2"


def fetcher(seiten=None) -> FixtureFetcher:
    return FixtureFetcher("tirol", Q["base_url"], seiten=seiten or SEITEN_QUELLEN["tirol"])


def offene_namen() -> dict[str, str]:
    f = fetcher()
    return {m["ident"]: m["title"] for m in marker(f.seite("2026-11-13/loipen_offen.html"))}


# ---------- P25: tirol.at-Listendaten ----------

@pytest.mark.req("P25", ak=1)
def test_p25_listeneintraege_liefern_laenge_schwierigkeit_stil():
    f = fetcher()
    s1, s2 = f.seite("2026-11-13/loipen_offen.html"), f.seite("2026-11-13/loipen_offen_listpos2.html")
    assert naechste_seite(s1).endswith("OPEN&listpos=2") and naechste_seite(s2) is None
    daten = {**listen_daten(s1), **listen_daten(s2)}
    namen = offene_namen()
    assert len(namen) == 12 and set(daten) == set(namen)  # 6 je Seite, zusammen alle offenen
    nach_name = {namen[k]: v for k, v in daten.items()}
    assert nach_name["SnowFactory Loipe Seefeld"] == {"laenge_km": 1.0, "schwierigkeit": "mittelschwierig",
                                                      "stile": "skating, klassisch"}
    assert nach_name["A2 - Snowfarmingloipe Leutasch"]["laenge_km"] == 2.8
    assert nach_name["Rundloipe Gaichtpaß"]["stile"] == "klassisch"
    assert technik_aus_stilen("skating, klassisch") == Technik.BEIDES
    assert technik_aus_stilen("Skating / Klassisch") == Technik.BEIDES
    assert technik_aus_stilen("klassisch") == Technik.KLASSISCH


@pytest.mark.req("P25", ak=1)
def test_p25_jede_offene_loipe_hat_nach_einem_lauf_ihre_laenge():
    f = fetcher()
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=0), f)
    offen = [l for l in erg.loipen if l.status.value == "offen"]
    assert len(offen) == 12
    assert all(l.laenge_km for l in offen), [l.name for l in offen if not l.laenge_km]
    sf = next(l for l in offen if l.name == "SnowFactory Loipe Seefeld")
    assert sf.technik == Technik.BEIDES and sf.schwierigkeit.value == "mittel"
    assert SEITE2_URL in [u[len(Q["base_url"]) + 1:] for u in f.abgerufen]
    assert not erg.warnungen


@pytest.mark.req("P25", ak=2)
def test_p25_detailseiten_zuerst_fuer_loipen_ohne_laenge():
    alle = marker(fetcher().seite("2026-11-13/loipen.html"))
    idents = sorted(m["ident"] for m in alle)
    offen = set(offene_namen())
    # Bestand: alle bis auf drei geschlossene Loipen kennen ihre Laenge
    fehlend = [i for i in idents if i not in offen][100:103]
    bestand = set(idents) - set(fehlend)
    f = fetcher()
    TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=3, _mit_laenge=bestand), f)
    details = [u for u in f.abgerufen if "?" not in u and not u.endswith("/loipen")]
    titel = {m["ident"]: m["title"] for m in alle}
    pfade = {**listen_pfade(fetcher().seite("2026-11-13/loipen.html")),
             **listen_pfade(fetcher().seite("2026-11-13/loipen_offen.html"))}
    erwartet = {pfade.get(i) or slug(titel[i]) for i in fehlend}
    assert len(details) == 3 and {u.rsplit("/", 1)[-1] for u in details} == erwartet
    # offene Loipen ohne Bestand brauchen keine Detailseite: die Liste nennt ihre Laenge
    f2 = fetcher()
    TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=40, _mit_laenge=set(idents) - offen), f2)
    assert len([u for u in f2.abgerufen if "?" not in u and not u.endswith("/loipen")]) == 40  # Rest im Wechsel


@pytest.mark.req("P25", ak=3)
def test_p25_fehlende_folgeseite_gibt_warnung_und_behaelt_seite_eins():
    seiten = {k: v for k, v in SEITEN_QUELLEN["tirol"].items() if "listpos" not in k}
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=0), fetcher(seiten))
    assert any("Liste der geöffneten Loipen" in w for w in erg.warnungen)
    mit = [l for l in erg.loipen if l.status.value == "offen" and l.laenge_km]
    assert len(mit) == 6  # die erste Seite


# ---------- U44: Sonderloipen ----------

@pytest.mark.req("U44", ak=1)
@pytest.mark.parametrize("name, art", [
    ("A2 - Snowfarmingloipe Leutasch", "snowfarming"),
    ("SnowFactory Loipe Seefeld", "snowfarming"),
    ("Opening Loipe Sedlsee small", "opening"),
    ("Höhenloipe am Pitztaler Gletscher im Herbst für Gruppen mit Voranmeldung", "gruppen"),
    ("Loipe Fernau am Stubaier Gletscher (11)", "gletscher"),
    ("KU1 Weissach I", None),
    ("Rundloipe Grän", None),
])
def test_u44_sonderloipen_am_namen_erkannt(name, art):
    s = sonderloipe(name)
    assert (s["art"] if s else None) == art
    if s:
        assert s["kurz"] and len(s["text"]) > 30


# ---------- Oberflaeche ----------

def _hrefs(seite) -> list[str]:
    return seite.locator("#view a[href^='#/loipe/']").evaluate_all("els => els.map(e => e.getAttribute('href'))")


@pytest.mark.req("U42", ak=1)
def test_u42_jeder_loipenlink_zeigt_auf_eine_loipe(seite):
    seite.open("#/loipen")
    hrefs = _hrefs(seite)
    ids = seite.evaluate("() => { const ids = new Set(); document.querySelectorAll('.lp').forEach(a => ids.add(a.getAttribute('href'))); return ids.size; }")
    gesamt = int(re.search(r"von (\d+) Loipen", seite.locator("#view .fine").first.inner_text()).group(1))
    assert len(hrefs) == gesamt == ids  # jede Loipe genau einmal, jede mit Link


@pytest.mark.req("U42", ak=1)
@pytest.mark.parametrize("handy", [False, True])
def test_u42_klick_und_tippen_oeffnen_die_loipe(browser, basis, handy):
    opts = {"viewport": {"width": 412, "height": 839}, "is_mobile": True, "has_touch": True} if handy else \
        {"viewport": {"width": 1280, "height": 900}}
    ctx = browser.new_context(locale="de-DE", **opts)
    p = ctx.new_page()
    fehler = []
    p.on("pageerror", lambda e: fehler.append(str(e)))
    for start in ("#/loipen?offen=1", "#/loipen?region=seefeld-mieming", "#/gebiet/seefeld", "#/loipen?region=oetztal-pitztal"):
        p.goto(f"{basis}/{start}")
        p.wait_for_selector("#view a.lp")
        n = p.locator("#view a.lp").count()
        for i in sorted({0, n // 2, n - 1}):
            p.goto(f"{basis}/{start}")
            p.wait_for_selector("#view a.lp")
            a = p.locator("#view a.lp").nth(i)
            name = a.locator(".n").evaluate("e => e.childNodes[0].textContent.trim()")
            (a.tap if handy else a.click)()
            p.wait_for_function("n => (document.querySelector('#view h1') || {}).textContent === n", arg=name)
    # Startseite: jede genannte Loipe fuehrt direkt zur Loipe, der Kopf zum Gebiet
    p.goto(f"{basis}/#/?ort=Seefeld")
    p.wait_for_selector(".gc .r")
    assert p.locator(".gc a.gk").first.get_attribute("href").startswith("#/gebiet/")
    r = p.locator(".gc a.r").first
    ziel = r.get_attribute("href")
    assert ziel.startswith("#/loipe/")
    (r.tap if handy else r.click)()
    p.wait_for_function("h => location.hash === h && document.querySelector('#view h1')", arg=ziel)
    assert fehler == []
    ctx.close()


@pytest.mark.req("U42", ak=2)
def test_u42_detailseite_ohne_streckendatei_und_neuer_datenstand(browser, basis):
    """Die Streckendatei fehlt (der Worker hat inzwischen neu erzeugt): die Seite steht trotzdem und holt
    den Index neu."""
    # ohne Service Worker, sonst greift die Umleitung nicht (Playwright sieht dessen Abrufe nicht)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="de-DE", service_workers="block")
    p = ctx.new_page()
    p.route("**/strecken/**", lambda r: r.fulfill(status=404, body="weg"))
    p.goto(f"{basis}/#/loipen?region=chiemgau")
    p.wait_for_selector("#view a.lp")
    index_abrufe = []
    p.on("request", lambda r: index_abrufe.append(r.url) if r.url.endswith("/daten.json") else None)
    a = p.locator("#view a.lp").first
    name = a.locator(".n").evaluate("e => e.childNodes[0].textContent.trim()")
    a.click()
    p.wait_for_function("n => (document.querySelector('#view h1') || {}).textContent === n", arg=name)
    assert "Quelle und Stand" in p.locator("#view").inner_text()
    p.wait_for_timeout(500)
    assert index_abrufe, "nach dem Fehlschlag wird der Datenstand neu geprueft"
    ctx.close()


@pytest.mark.req("U42", ak=3)
def test_u42_fehler_in_einer_ansicht_bleibt_nicht_stumm(seite):
    seite.open("#/loipen?region=seefeld-mieming")
    seite.evaluate("() => { window.LB.saisonLoipe = function () { throw new Error('Testfehler'); }; }")
    seite.locator("#view a.lp").first.click()
    seite.wait_for_selector("#ansicht-fehler")
    assert "Testfehler" in seite.locator("#ansicht-fehler").inner_text()
    assert seite.locator("#neu-laden").is_visible()


@pytest.mark.req("U42", ak=4)
def test_u42_karte_marker_nicht_unter_dem_auswahlfeld(browser, basis):
    ctx = browser.new_context(viewport={"width": 412, "height": 839}, is_mobile=True, has_touch=True, locale="de-DE")
    p = ctx.new_page()
    p.goto(f"{basis}/#/karte?region=seefeld-mieming")
    p.wait_for_selector(".leaflet-marker-icon")
    p.wait_for_timeout(400)
    sel = p.locator("#sel").bounding_box()
    boxen = p.locator(".leaflet-marker-icon").evaluate_all(
        "els => els.map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
    assert boxen
    unter = [b for b in boxen if b[3] > sel["y"] and b[1] < sel["y"] + sel["height"]
             and b[2] > sel["x"] and b[0] < sel["x"] + sel["width"]]
    assert unter == []
    assert re.search(r"\d+ Loipen mit Standort", p.locator("#sel").inner_text())
    ctx.close()


@pytest.mark.req("U43", ak=1)
def test_u43_gebietsseite_mit_rahmendaten(seite):
    seite.open("#/gebiet/seefeld")
    t = seite.locator("#rahmen").inner_text()
    assert re.search(r"LOIPEN OFFEN\s+\d+ von \d+", t, re.I)
    assert re.search(r"KM OFFEN\s+[\d,]+ von [\d,]+ km", t, re.I)
    assert re.search(r"LÄNGE BEKANNT\s+\d+ von \d+ Loipen", t, re.I)
    assert "Sonderloipe" in seite.locator("#view").inner_text()  # SnowFactory nicht mitgezaehlt


@pytest.mark.req("U43", ak=2)
def test_u43_liste_und_startseite_mit_rahmendaten_je_region_und_gebiet(seite):
    seite.open("#/loipen?offen=1")
    for t in seite.locator(".rahmen").all_inner_texts():
        assert re.search(r"Region gesamt: \d+ von \d+ Loipen offen", t), t
    seite.open("#/?ort=Seefeld")
    assert all(re.search(r"\d+ von \d+ Loipen offen", t) for t in seite.locator(".gc .gk p").all_inner_texts())


@pytest.mark.req("U44", ak=1)
def test_u44_sonderloipe_mit_kennzeichen_und_erklaerung(seite):
    seite.open("#/loipen?region=oetztal-pitztal")
    karte = seite.locator(".lp", has_text="Pitztaler Gletscher im Herbst")
    assert karte.locator(".badge.sonder").inner_text() == "Nur für Gruppen"
    karte.click()
    seite.wait_for_selector("#sonder")
    assert "Voranmeldung" in seite.locator("#sonder").inner_text()


@pytest.mark.req("U44", ak=2)
def test_u44_sonderloipen_zaehlen_nicht_als_befahrbar(seite):
    seite.open("#/loipen?offen=1&sort=status&demo=1")  # Beispielansicht: einige gewoehnliche Loipen offen
    karten = seite.locator(".lp").evaluate_all(
        "els => els.map(e => [e.classList.contains('sonderlp'), e.querySelector('.st').className])")
    normal_offen = [i for i, (s, st) in enumerate(karten) if not s and "offen" in st.split()]
    sonder = [i for i, (s, _) in enumerate(karten) if s]
    assert sonder and normal_offen and max(normal_offen) < min(sonder)
    seite.open("#/")
    stat = seite.locator("#k-offen").inner_text().replace("\xad", "")
    zahl = int(re.match(r"\s*(\d+)", stat).group(1))
    befahrbar = seite.evaluate("() => window.__LB_befahrbar()")
    assert zahl == befahrbar and "Sonderloipe" in stat
    h1 = seite.locator(".herotxt h1").inner_text()
    assert not any(w in h1 for w in ("Snow", "Opening", "Gletscher"))


@pytest.mark.req("U42", ak=4)
def test_u42_handy_tipp_auf_marker_zeigt_details_ueber_der_tab_leiste(browser, basis):
    ctx = browser.new_context(viewport={"width": 412, "height": 839}, is_mobile=True, has_touch=True, locale="de-DE")
    p = ctx.new_page()
    p.goto(f"{basis}/#/karte?region=seefeld-mieming")
    p.wait_for_selector(".leaflet-marker-icon")
    # bis auf eine einzelne Loipe hineinzoomen (sonst Buendel)
    p.evaluate("() => { const l = window.LB.S.loipen.find(x => x.name === 'SnowFactory Loipe Seefeld'); window.__map.setView([l.lat, l.lon], 18, {animate: false}); }")
    p.wait_for_selector(".leaflet-marker-icon .mk")
    p.locator(".leaflet-marker-icon .mk").first.tap()
    p.wait_for_selector("#sel .btn.prim")
    knopf = p.locator("#sel .btn.prim")
    b = knopf.bounding_box()
    oben = p.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e && e.closest('a') && e.closest('a').getAttribute('href'); }",
                      [b["x"] + b["width"] / 2, b["y"] + b["height"] / 2])
    assert oben and oben.startswith("#/loipe/"), "Details-Knopf verdeckt oder ausserhalb des Bildschirms"
    knopf.tap()
    p.wait_for_selector("#view h1")
    ctx.close()
