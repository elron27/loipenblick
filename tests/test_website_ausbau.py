"""Oberflaeche fuer die Ausbaustufe 1 im echten Browser: D15, D16, P13, P16, U30, U31, U32.

Nutzt die Seite aus tests/test_website_ui.py (Beispielseiten aller Quellen). Fuer U32 wird zusaetzlich
eine Seite mit 750 synthetischen Loipen erzeugt.
"""

import functools
import http.server
import json
import re
import threading
import time

import pytest
from sqlalchemy.orm import Session

from loipen import generator
from tests.helpers import lade_alle_fixtures
from tests.test_website_ui import JETZT, aktion, basis, browser, seite  # noqa: F401  (Fixtures)

playwright = pytest.importorskip("playwright.sync_api")


# wie playwright.devices["Pixel 7"]; ein zweites sync_playwright() ist neben dem Browser-Fixture nicht moeglich
PIXEL_7 = {"viewport": {"width": 412, "height": 839}, "device_scale_factor": 2.625, "is_mobile": True, "has_touch": True,
           "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/131.0.0.0 Mobile Safari/537.36"}


def text(page) -> str:
    return page.locator("#view").inner_text()


@pytest.mark.req("D16", ak=2)
def test_d16_liste_und_regionswechsler_nach_land_und_region(seite):
    seite.open("#/loipen")
    laender = seite.locator("h2.land").all_inner_texts()
    assert laender == ["Deutschland · Bayern", "Österreich · Salzburg", "Österreich · Tirol"]
    regionen = seite.locator("section.rg").evaluate_all("els => els.map(e => e.dataset.region)")
    assert regionen.index("chiemgau") < regionen.index("kufsteinerland") < regionen.index("wilder-kaiser")
    # jede Loipe steht genau in ihrer Region
    gesamt = sum(int(re.search(r"(\d+) Loipen", t).group(1)) for t in seite.locator("h3.reg").all_inner_texts())
    assert gesamt == seite.locator(".lp").count()
    gruppen = seite.locator("#f-reg optgroup").evaluate_all("els => els.map(e => e.label)")
    assert gruppen == laender
    tirol = seite.locator('#f-reg optgroup[label="Österreich · Tirol"] option').all_inner_texts()
    assert "Kufsteinerland" in tirol and "Chiemgau" not in tirol
    aktion(seite, lambda: seite.select_option("#f-reg", "kufsteinerland"))
    assert "region=kufsteinerland" in seite.url
    assert seite.locator("section.rg").evaluate_all("els => els.map(e => e.dataset.region)") == ["kufsteinerland"]


@pytest.mark.req("U30", ak=1)
def test_u30_tirol_loipe_zeigt_abrufzeit_und_status_ohne_datum(seite):
    seite.open("#/loipen?region=kufsteinerland")
    for d in seite.locator(".lp .d").all_inner_texts():
        assert re.search(r"Status ohne Datum · Stand vor \d+ (Min\.|Std\.|Tagen)", d), d
        assert "veraltet" not in d
    seite.locator(".lp").first.click()
    seite.wait_for_selector(".hist")
    t = text(seite)
    assert re.search(r"Stand laut Quelle\s+Quelle nennt nur den Status, kein Präparierdatum", t)
    assert re.search(r"Zuletzt von uns geprüft\s+\d{2}\.\d{2}\.\d{4}", t)


@pytest.mark.req("U30", ak=1)
def test_u30_ohne_datum_steht_bei_letzter_praeparierung_hinten(seite):
    seite.open("#/loipen?demo=1&sort=praeparierung")
    ohne = ["Status ohne Datum" in d or "keinen Zustand" in d for d in seite.locator(".lp .d").all_inner_texts()]
    assert any(ohne) and not all(ohne)
    erste = ohne.index(True)
    assert all(ohne[erste:])  # danach nur noch Loipen ohne Datum


@pytest.mark.req("P16", ak=2)
def test_p16_berchtesgaden_unbekannt_mit_hinweis(seite):
    seite.open("#/loipen?region=berchtesgadener-land")
    assert seite.locator(".lp").count() >= 5
    assert set(seite.locator(".lp .st").all_inner_texts()) == {"Unbekannt"}
    assert all("Quelle meldet keinen Zustand" in d for d in seite.locator(".lp .d").all_inner_texts())
    seite.open("#/gebiet/ramsau")
    assert "meldet keinen Loipenzustand" in text(seite)


@pytest.mark.req("U31", ak=1)
@pytest.mark.req("U31", ak=2)
def test_u31_vignette_und_loipengebuehr_am_gebiet(seite):
    seite.open("#/gebiet/kufstein")
    t = text(seite)
    assert re.search(r"Vignette\s+Österreich: Vignettenpflicht", t)
    assert "Österreich · Tirol" in t
    seite.open("#/gebiet/faistenau")
    t = text(seite)
    assert "Vignette" in t and re.search(r"Loipengebühr\s+Tageskarte 11 €", t)
    seite.open("#/gebiet/kreuth")
    assert "Vignette" not in text(seite)


@pytest.mark.req("D15", ak=1)
def test_d15_dublette_einmal_mit_auch_gemeldet_von(seite):
    seite.open("#/loipen?text=Hauswies")
    assert seite.locator(".lp").count() == 1
    seite.locator(".lp").first.click()
    seite.wait_for_selector(".hist")
    assert re.search(r"Auch gemeldet von\s+Fischbachau Tourismus", text(seite))


@pytest.mark.req("P13", ak=2)
def test_p13_abdeckung_je_region(seite):
    seite.open("#/")
    seite.get_by_role("link", name="Abdeckung und Quellen").click()
    seite.wait_for_selector("table.tab")
    zeilen = seite.locator("table.tab tbody tr").all_inner_texts()
    assert len(zeilen) == 19  # 10 Regionen der Stufe 1 und 9 weitere fuer ganz Tirol
    berchtesgaden = next(z for z in zeilen if z.startswith("Berchtesgadener Land")).split("\t")
    assert berchtesgaden[1:] == ["5", "0", "0", "5", "0"]
    assert "Tirol Werbung (tirol.at)" in text(seite)


def strecken_abrufe(page) -> list[str]:
    return sorted({re.search(r"strecken/([^/?]+)\.json", u).group(1) for u in page.abrufe if "/strecken/" in u})


@pytest.mark.req("U32", ak=2)
def test_u32_karte_laedt_strecken_nur_fuer_die_gewaehlte_region(seite):
    seite.abrufe = []
    seite.on("request", lambda r: seite.abrufe.append(r.url))
    seite.open("#/karte?region=chiemgau")
    seite.wait_for_selector("#map path.leaflet-interactive", state="attached")
    assert strecken_abrufe(seite) == ["chiemgau"]
    seite.abrufe.clear()
    seite.open("#/karte")  # ohne Wahl: nur Regionen mit Streckenverlauf (U36), nicht alle
    seite.wait_for_selector("#map .mk, #map .mkc")
    seite.wait_for_timeout(500)
    assert 0 < len(strecken_abrufe(seite)) < 10


# ---------- U32 AK 1: 750 Loipen ----------

@pytest.fixture(scope="module")
def basis_750(engine, tmp_path_factory):
    """Echte Beispielseiten, je Gebiet mit erfundenen Loipen aufgefuellt bis 750 Loipen."""
    site = tmp_path_factory.mktemp("site750")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        generator.erzeuge(s, site, JETZT)
        s.close()
        trans.rollback()
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    regionen = {r["slug"]: json.loads((site / r["datei"]).read_text(encoding="utf-8")) for r in index["regionen"]}
    gebiete = [g for r in regionen.values() for g in r["gebiete"]]
    n = sum(len(g["loipen"]) for g in gebiete)
    neue_id = 100000
    while n < 750:
        for g in gebiete:
            if n >= 750:
                break
            vorlage = (g["loipen"] or [None])[0]
            if vorlage is None:
                continue
            kopie = {**vorlage, "id": neue_id, "name": f"{vorlage['name']} {neue_id}", "auch_bei": []}
            if kopie["lat"] is not None:
                kopie["lat"] += (neue_id % 17) * 0.001
            g["loipen"].append(kopie)
            neue_id += 1
            n += 1
    for r in index["regionen"]:
        (site / r["datei"]).write_text(json.dumps(regionen[r["slug"]], ensure_ascii=False), encoding="utf-8")
    index["kennzahlen"]["loipen"] = n
    (site / "daten.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    class Still(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Still, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", n
    server.shutdown()


@pytest.mark.req("U32", ak=1)
def test_u32_startseite_mit_750_loipen_auf_dem_handy_unter_3_s(browser, basis_750):  # noqa: F811
    url, n = basis_750
    assert n >= 750
    ctx = browser.new_context(**PIXEL_7, locale="de-DE")
    page = ctx.new_page()
    fehler = []
    page.on("pageerror", lambda e: fehler.append(str(e)))
    # langsameres Handy nachstellen: 4-fach gedrosselte CPU
    page.context.new_cdp_session(page).send("Emulation.setCPUThrottlingRate", {"rate": 4})
    t0 = time.monotonic()
    page.goto(url + "/#/")
    page.wait_for_selector("#view .sky")
    dauer = time.monotonic() - t0
    assert f"{n}" in page.locator(".stat").nth(1).inner_text()
    print(f"U32: Startseite mit {n} Loipen in {dauer:.2f} s")
    assert dauer < 3.0, f"{dauer:.2f} s"
    # Liste und Karte bleiben bedienbar
    t0 = time.monotonic()
    page.goto(url + "/#/loipen")
    page.wait_for_selector(".lp")
    assert page.locator(".lp").count() == n
    assert time.monotonic() - t0 < 3.0
    assert fehler == []
    ctx.close()
