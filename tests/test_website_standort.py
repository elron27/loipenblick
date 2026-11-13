"""Oberflaeche nach Stefans NAS-Test vom 13.11.2026 im echten Browser: U33, U34, U35, U36, P21 AK 3.

Nutzt die Seite aus tests/test_website_ui.py (Beispielseiten aller Quellen). Die Online-Ortssuche
(photon.komoot.io) wird im Browser abgefangen und mit einer festen Antwort bedient; kein Test geht ins Netz.
"""

import json
import re

import pytest

from tests.test_website_ui import aktion, basis, browser, seite  # noqa: F401  (Fixtures)

playwright = pytest.importorskip("playwright.sync_api")

PHOTON = {"features": [{"geometry": {"coordinates": [11.6994, 47.8853]}, "properties": {
    "name": "Holzkirchen", "postcode": "83607", "county": "Landkreis Miesbach", "countrycode": "DE"}}]}


def neue_seite(browser, basis, **ctx_args):  # noqa: F811
    ctx = browser.new_context(locale="de-DE", **ctx_args)
    page = ctx.new_page()
    fehler = []
    page.on("pageerror", lambda e: fehler.append(str(e)))
    page.on("dialog", lambda d: fehler.append("Browser-Dialog: " + d.message))
    page.fehler = fehler
    page.basis = basis
    return ctx, page


def ortname(page) -> str:
    return page.locator("#ort").inner_text().replace("▾", "").strip()


@pytest.mark.req("U34", ak=1)
def test_u34_befahrbar_fuehrt_zur_liste_der_offenen(seite):
    seite.open("#/?demo=1")
    zahl = int(seite.locator("#k-offen b").inner_text())
    assert zahl > 0
    aktion(seite, lambda: seite.locator("#k-offen").click())
    assert "#/loipen?" in seite.url and "offen=1" in seite.url and "sort=entfernung" in seite.url
    assert seite.locator('.tog[data-k="offen"][aria-pressed="true"]').count() == 1
    stati = set(seite.locator(".lp .st").all_inner_texts())
    assert stati and stati <= {"Offen", "Eingeschränkt"}
    assert seite.locator(".lp").count() == zahl


UEBERLAPPUNG = """() => {
  const boxen = [...document.querySelectorAll('.sky svg text.s-t')].map(t => t.getBBox());
  const koepfe = [...document.querySelectorAll('.sky svg circle')].map(c => c.getBBox());
  const schneidet = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
  const fehler = [];
  boxen.forEach((a, i) => {
    boxen.forEach((b, j) => { if (j > i && schneidet(a, b)) fehler.push(['Name', i, j]); });
    koepfe.forEach((k, j) => { if (j !== i && schneidet(a, k)) fehler.push(['Kopf', i, j]); });
  });
  return {n: boxen.length, fehler};
}"""


@pytest.mark.req("U33", ak=1)
@pytest.mark.parametrize("ort", ["Tannheimer Tal", "Kufstein", "Rottach-Egern", "Seefeld"])
def test_u33_talprofil_ohne_ueberlappende_namen(seite, ort):
    seite.open(f"#/?ort={ort}")
    seite.wait_for_selector(".sky svg text.s-t", state="attached")
    r = seite.evaluate(UEBERLAPPUNG)
    assert r["n"] == 10
    assert r["fehler"] == [], r


@pytest.mark.req("U33", ak=2)
def test_u33_ausweichende_namen_haben_eine_linie(seite):
    seite.open("#/?ort=Tannheimer Tal")
    seite.wait_for_selector(".sky svg text.s-t", state="attached")
    zeilen = seite.evaluate("""() => [...document.querySelectorAll('.sky svg a')].map(a => {
      const t = a.querySelector('text'), c = a.querySelector('circle');
      return {weg: Math.abs(+t.getAttribute('x') - +c.getAttribute('cx')) > 1 || +t.getAttribute('y') < +c.getAttribute('cy') - 19,
              linie: !!a.querySelector('line.s-f')};
    })""")
    assert any(z["weg"] for z in zeilen)  # bei den engen Gebieten muss mindestens ein Name ausweichen
    assert all(z["linie"] == z["weg"] for z in zeilen), zeilen


def test_talprofil_beschriftung_einzeln(seite):
    """Drei Nadeln dicht nebeneinander, verschieden hoch: alle Namen frei, alle im Bild."""
    seite.open("#/")
    r = seite.evaluate("""() => window.__beschriftung([
      {name: 'Tannheimer Tal', x: 400, kopf: 150}, {name: 'Jungholz', x: 430, kopf: 170}, {name: 'Weißenbach', x: 460, kopf: 140},
      {name: 'Ganz links am Rand', x: 5, kopf: 160}])""")
    boxen = [b["box"] for b in r]
    for i, a in enumerate(boxen):
        assert a["l"] >= 0 and a["r"] <= 900 and a["o"] >= 0
        for b in boxen[i + 1:]:
            assert a["r"] <= b["l"] or b["r"] <= a["l"] or a["u"] <= b["o"] or b["u"] <= a["o"]


@pytest.mark.req("U35", ak=1)
def test_u35_erster_besuch_fragt_einmal_nach_dem_standort(browser, basis):  # noqa: F811
    ctx, page = neue_seite(browser, basis, permissions=["geolocation"], geolocation={"latitude": 47.585, "longitude": 12.165})
    page.goto(f"{basis}/#/")
    page.wait_for_function("document.getElementById('ort').textContent.indexOf('Mein Standort') >= 0")
    assert ortname(page) == "Mein Standort · bei Kufstein"
    assert "Kufstein" in page.locator(".eyebrow").text_content()
    gespeichert = page.evaluate("JSON.parse(localStorage.getItem('ort'))")
    assert gespeichert["art"] == "gps" and round(gespeichert["lat"], 2) == 47.59
    # beim naechsten Besuch frischt die Seite den Standort still auf
    ctx.set_geolocation({"latitude": 47.708, "longitude": 11.757})
    page.reload()
    page.wait_for_function("document.getElementById('ort').textContent.indexOf('bei Kufstein') < 0")
    assert ortname(page).startswith("Mein Standort · bei ")
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("U35", ak=1)
def test_u35_gewaehlter_ort_wird_nicht_ueberschrieben(browser, basis):  # noqa: F811
    ctx, page = neue_seite(browser, basis, permissions=["geolocation"], geolocation={"latitude": 47.585, "longitude": 12.165})
    page.add_init_script("localStorage.setItem('ort', JSON.stringify({name: 'Rosenheim', lat: 47.86, lon: 12.12, art: 'ort'}))")
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    page.wait_for_timeout(500)
    assert ortname(page) == "Rosenheim"
    ctx.close()


@pytest.mark.req("U35", ak=2)
def test_u35_ortssuche_lokal_und_online(browser, basis):  # noqa: F811
    ctx, page = neue_seite(browser, basis)
    anfragen = []

    def photon(route):
        anfragen.append(route.request.url)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(PHOTON),
                      headers={"Access-Control-Allow-Origin": "*"})

    page.route(re.compile(r"https://photon\.komoot\.io/.*"), photon)
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    page.locator("#ort").click()
    page.locator("#ortq").fill("Rosen")
    namen = page.locator("#ortliste button.o").all_inner_texts()
    assert namen and all("Rosen" in n for n in namen)
    page.locator("#ortq").fill("83607")
    page.locator("#ortsuche button[type=submit]").click()
    page.wait_for_selector("#ortliste button.o")
    assert "q=83607" in anfragen[0]
    eintrag = page.locator("#ortliste button.o").first
    assert "Holzkirchen" in eintrag.inner_text() and "Online" in eintrag.inner_text()
    eintrag.click()
    assert page.locator("#ortwahl").is_hidden()
    assert ortname(page) == "Holzkirchen"
    assert "Holzkirchen" in page.locator(".eyebrow").text_content()
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("U35", ak=3)
def test_u35_ohne_https_hinweis_statt_fehler(browser, basis):  # noqa: F811
    ctx, page = neue_seite(browser, basis)
    page.add_init_script("Object.defineProperty(window, 'isSecureContext', {get: () => false})")
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    page.locator("#ort").click()
    assert "nur über https" in page.locator("#geo").inner_text()
    page.locator("#geo").click()
    assert "https" in page.locator("#geo-info").inner_text()
    assert page.locator("#ortq").is_visible()
    assert page.fehler == []  # kein alert(), kein JavaScript-Fehler
    ctx.close()


@pytest.mark.req("U35", ak=3)
def test_u35_standort_verweigert_nennt_den_grund(browser, basis):  # noqa: F811
    ctx, page = neue_seite(browser, basis)  # keine Freigabe: der Browser lehnt ab
    page.goto(f"{basis}/#/")
    page.wait_for_selector("#view > *")
    page.locator("#ort").click()
    page.locator("#geo").click()
    page.wait_for_function("document.getElementById('geo-info').textContent.indexOf('nicht') >= 0")
    assert "Suche" in page.locator("#geo-info").inner_text() or "suche" in page.locator("#geo-info").inner_text()
    assert page.fehler == []
    ctx.close()


@pytest.mark.req("U36", ak=1)
def test_u36_karte_zeigt_strecken_auch_fern_vom_standort(seite):
    seite.abrufe = []
    seite.on("request", lambda r: seite.abrufe.append(r.url))
    seite.open("#/karte?ort=Rottach-Egern")  # Tannheimer Tal liegt rund 90 km entfernt
    seite.wait_for_selector("#map path.leaflet-interactive", state="attached")
    seite.wait_for_timeout(300)
    geladen = {re.search(r"strecken/([^/?]+)\.json", u).group(1) for u in seite.abrufe if "/strecken/" in u}
    assert geladen == {"chiemgau", "ausserfern"}
    assert seite.locator("#map path.leaflet-interactive").count() >= 80


@pytest.mark.req("U36", ak=2)
def test_u36_tiroler_loipe_ohne_strecke_nennt_den_grund(seite):
    seite.open("#/gebiet/kufstein")
    aktion(seite, lambda: seite.locator(".lp").first.click())
    seite.wait_for_selector("#ohne-strecke")
    assert "robots.txt" in seite.locator("#ohne-strecke").inner_text()


@pytest.mark.req("P21", ak=3)
def test_p21_loipenseite_zeigt_abweichende_meldung_von_tirol(seite):
    seite.open("#/gebiet/tannheimer-tal")
    assert "Offen" not in seite.locator(".lp .st").all_inner_texts()
    aktion(seite, lambda: seite.locator(".lp", has_text="Gaichtpass").click())
    seite.wait_for_selector(".hist")
    t = seite.locator("#view").inner_text()
    assert "Tourismusverband Tannheimer Tal" in t
    assert re.search(r"Auch gemeldet von\s+Tirol Werbung \(tirol\.at\) meldet Offen, abweichend", t)
    assert seite.locator("#minimap path.leaflet-interactive").count() == 1  # Streckenverlauf aus dem Loipenbericht
