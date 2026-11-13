"""Statistik-Seite im echten Browser (Playwright, Chromium): U19, U37, U38, U39.

Echte Daten gibt es im November erst ab dem ersten Abruf; den vollen Winter zeigt die Beispielansicht
(?demo=1) mit einem erfundenen Winter 2025/26.
"""

import pytest

from tests.test_website_ui import aktion, basis, browser, seite  # noqa: F401  (Fixtures wiederverwenden)

pytest.importorskip("playwright.sync_api")


@pytest.mark.req("U37", ak=2)
@pytest.mark.req("U39", ak=1)
def test_u37_statistik_mit_echten_daten_zeigt_den_laufenden_winter(seite):
    seite.open("#/statistik")
    seite.wait_for_selector("#s-verlauf svg")
    assert seite.locator('.tabs a[data-tab="statistik"]').get_attribute("aria-current") == "page"
    text = seite.locator("#view").inner_text()
    assert "Winter 2026/27" in text and "Laufender Winter" in text
    assert seite.locator("#s-quellen tbody tr").count() >= 10
    assert seite.locator(".demo").count() == 0


@pytest.mark.req("U37", ak=[3, 5])
def test_u37_beispielwinter_mit_verlauf_und_wert_beim_zeigen(seite):
    seite.open("#/statistik?demo=1")
    seite.wait_for_selector("#s-verlauf svg")
    assert "erfundenen Werten" in seite.locator(".demo").inner_text()
    assert int(seite.locator("#s-tage").inner_text()) > 30
    box = seite.locator("#s-verlauf .hit").bounding_box()
    seite.mouse.move(box["x"] + box["width"] * 0.45, box["y"] + 60)
    tip = seite.locator("#s-verlauf .tip")
    assert tip.is_visible() and "2026" in tip.inner_text() and "befahrbar" in tip.inner_text()
    seite.locator("details.werte summary").first.click()
    assert seite.locator("details.werte").first.locator("tbody tr").count() == 6  # November bis April


@pytest.mark.req("U37", ak=4)
@pytest.mark.req("U38", ak=[1, 2])
def test_u38_rangliste_region_und_gebiet_auswaehlen(seite):
    seite.open("#/statistik?demo=1")
    seite.wait_for_selector("#s-gebiete")
    tage = [int(x) for x in seite.locator("#s-gebiete tbody td:nth-child(2)").all_inner_texts()]
    assert tage == sorted(tage, reverse=True) and tage[0] > 0
    aktion(seite, lambda: seite.select_option("#s-region", "leitzachtal"))
    seite.wait_for_selector("#s-gebiete")
    assert "region=leitzachtal" in seite.url
    namen = seite.locator("#s-gebiete tbody th a").all_inner_texts()
    assert "Bayrischzell" in namen and "Vent" not in namen
    aktion(seite, lambda: seite.get_by_role("link", name="Bayrischzell", exact=True).first.click())
    seite.wait_for_selector("#s-schnee svg")
    assert "gebiet=bayrischzell" in seite.url
    assert seite.locator("h2.sec").first.inner_text().endswith("Bayrischzell")
    loipen = [int(x) for x in seite.locator("#s-loipen tbody td:nth-child(2)").all_inner_texts()]
    assert loipen and loipen == sorted(loipen, reverse=True)
    assert seite.locator("#s-loipen tbody th a").first.get_attribute("href").startswith("#/loipe/")


@pytest.mark.req("U19", ak=[1, 3])
def test_u19_loipenseite_zeigt_saisonstatistik(seite):
    seite.open("#/gebiet/bayrischzell?demo=1")
    aktion(seite, lambda: seite.locator(".lp a, a.lp").first.click())
    seite.wait_for_selector("#saison-tab")
    zeile = seite.locator("#saison-tab tbody tr").first.inner_text()
    assert "2025/26" in zeile and "Tage" in zeile
    seite.open("#/statistik?demo=0")
    seite.wait_for_timeout(500)
    seite.open("#/gebiet/bayrischzell")
    aktion(seite, lambda: seite.locator(".lp a, a.lp").first.click())
    seite.wait_for_selector("#saison .tab, #saison p.fine:not(:empty)")
    assert "2025/26" not in seite.locator("#saison").inner_text()


@pytest.mark.req("U39", ak=[2, 3])
def test_u39_quellen_mit_uebereinstimmung_oder_hinweis(seite):
    seite.open("#/statistik?demo=1")
    seite.wait_for_selector("#s-quellen")
    zellen = seite.locator("#s-quellen tbody td:nth-child(3)").all_inner_texts()
    assert any("%" in z for z in zellen)
    assert any("kein Vergleich" in z for z in zellen)  # z. B. Tegernsee: keine gemeinsame Loipe


@pytest.mark.req("U8", ak=1)
def test_u8_statistik_auf_360_px_ohne_waagrechtes_scrollen(browser, basis):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    p = ctx.new_page()
    for hash in ("#/statistik", "#/statistik?demo=1", "#/statistik?gebiet=bayrischzell"):
        p.goto(f"{basis}/{hash}")
        p.wait_for_selector("#s-verlauf svg")
        assert p.evaluate("document.documentElement.scrollWidth") <= 360, hash
    ctx.close()
