"""U50: geschlossen und unbekannt auf Karte und Talprofil unterscheidbar, Legende, Marker mit 44-px-Tippflaeche.

Nutzt die Seite aus tests/test_website_ui.py (Beispielseiten aller Quellen, Vorschau mit ?demo=1).
"""

import pytest

from tests.test_website_ui import basis, browser, seite  # noqa: F401  (Fixtures)

playwright = pytest.importorskip("playwright.sync_api")

MARKER = """sel => [...document.querySelectorAll(sel)].map(e => {
  const cs = getComputedStyle(e);
  return {s: e.dataset.s, bg: cs.backgroundColor, rand: cs.borderTopStyle, kreuz: !!e.querySelector('path[d^="M17 7 7 17"]')};
})"""


def _je_status(eintraege):
    return {e["s"]: e for e in eintraege}


@pytest.mark.req("U50", ak=1)
def test_u50_geschlossen_und_unbekannt_auf_der_karte_unterscheidbar(seite):
    seite.open("#/karte?demo=1&region=tegernseer-tal")
    seite.wait_for_selector("#map .mk, #map .mkc")
    seite.evaluate("window.__map.setZoom(17, {animate: false})")
    seite.wait_for_timeout(300)
    # alle Zustaende sicher im Bild: die Legende der Karte nutzt dieselben Marker
    je = _je_status(seite.evaluate(MARKER, ".mapw .legende .mk"))
    assert set(je) == {"offen", "eingeschraenkt", "geschlossen", "unbekannt"}
    assert je["geschlossen"]["bg"] != je["unbekannt"]["bg"]
    assert je["geschlossen"]["kreuz"] and not je["unbekannt"]["kreuz"]
    assert je["unbekannt"]["rand"] == "dashed" and je["geschlossen"]["rand"] == "solid"
    r, g, b = [int(x) for x in je["geschlossen"]["bg"][4:-1].split(",")]
    assert r > g + 60 and r > b + 60  # geschlossen ist rot, nicht grau
    # echte Marker folgen derselben Darstellung
    for m in seite.evaluate(MARKER, "#map .leaflet-marker-icon .mk"):
        assert m["bg"] == je[m["s"]]["bg"] and m["rand"] == je[m["s"]]["rand"] and m["kreuz"] == (m["s"] == "geschlossen")


@pytest.mark.req("U50", ak=1)
def test_u50_talprofil_kopf_zeigt_zustand_mit_farbe_und_form(seite):
    # um Berchtesgaden melden die Beispielquellen Gebiete geschlossen und andere ohne Angabe
    seite.open("#/?ort=Berchtesgaden")
    seite.wait_for_selector(".sky svg circle.kopf", state="attached")
    koepfe = seite.evaluate("""() => [...document.querySelectorAll('.sky svg circle.kopf')].map(c => ({
      s: c.dataset.s, fill: c.getAttribute('fill'), strich: c.getAttribute('stroke-dasharray'),
      kreuz: !!c.parentNode.querySelector('path[d^="M17 7 7 17"]')}))""")
    assert {"geschlossen", "unbekannt"} <= {k["s"] for k in koepfe}
    farbe = {}
    for k in koepfe:
        farbe.setdefault(k["s"], set()).add(k["fill"])
        assert k["kreuz"] == (k["s"] == "geschlossen")
        assert bool(k["strich"]) == (k["s"] == "unbekannt")
    assert all(len(f) == 1 for f in farbe.values())
    assert len({next(iter(f)) for f in farbe.values()}) == len(farbe)  # je Zustand eine eigene Farbe


@pytest.mark.req("U50", ak=2)
@pytest.mark.parametrize("ziel,ort", [("#/", ".sky .legende"), ("#/karte", ".mapw .legende")])
def test_u50_legende_an_karte_und_talprofil(seite, ziel, ort):
    seite.open(ziel)
    seite.wait_for_selector(ort)
    text = seite.locator(ort).inner_text()
    for wort in ("Offen", "Eingeschränkt", "Geschlossen", "Keine Angabe"):
        assert wort in text


@pytest.mark.req("U50", ak=3)
@pytest.mark.parametrize("breite", [1280, 360])
def test_u50_marker_haben_44_px_tippflaeche(browser, basis, breite):  # noqa: F811
    ctx = browser.new_context(viewport={"width": breite, "height": 800}, locale="de-DE")
    p = ctx.new_page()
    p.goto(f"{basis}/#/karte?demo=1&region=tegernseer-tal")
    p.wait_for_selector("#map .leaflet-marker-icon .mk, #map .leaflet-marker-icon .mkc")
    groessen = p.evaluate("""() => [...document.querySelectorAll('#map .leaflet-marker-icon.mkw')].map(e => {
      const r = e.getBoundingClientRect(); return [r.width, r.height]; })""")
    assert groessen and all(w >= 44 and h >= 44 for w, h in groessen), groessen
    # die Legende verdeckt am Handy weder Zoom-Knoepfe noch "Alles zeigen"
    leg, zoom, alles = (p.locator(s).bounding_box() for s in (".mapw .legende", ".leaflet-control-zoom", "button.alles"))
    for k in (zoom, alles):
        assert leg["x"] + leg["width"] <= k["x"] or k["x"] + k["width"] <= leg["x"] or leg["y"] >= k["y"] + k["height"]
    ctx.close()
