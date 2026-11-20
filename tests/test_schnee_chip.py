"""Startseite: Schneehoehe zur empfohlenen Loipe (U45).

Stefan am 20.11.2026 mit einem Screenshot der Testseite: Standort Fischbachau, die Karte "Heute in deiner Naehe"
empfiehlt die einzige offene Loipe "Langlaufen: Ginzling Loipe" (Mayrhofen und Hippach, gut 60 km entfernt), der
Chip daneben zeigt aber "Schnee Fischbachau: 0 cm". Der Chip nahm das naechste Gebiet zum Standort statt des
Gebiets der empfohlenen Loipe und nannte das Gebiet statt der Messstation.

Die Welt ist nachgestellt: Fischbachau (DWD, 0 cm) nahe am Standort, Mayrhofen und Hippach (GeoSphere, Station
Mayrhofen) mit der offenen Ginzling Loipe. Echte Seite, echter Browser.
"""

import functools
import http.server
import re
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.orm import Session

from loipen import generator
from loipen.models import Gebiet, Loipe, Quelle, Region, Wetter, WetterArt, Zustand
from tests.test_website_ui import browser  # noqa: F401  (Fixture)

playwright = pytest.importorskip("playwright.sync_api")

BERLIN = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 11, 20, 8, 5, tzinfo=BERLIN)
HEUTE = JETZT.date()


def _welt(s: Session, mayrhofen_cm: float | None) -> None:
    de = Region(slug="leitzachtal", name="Leitzachtal", land="DE", bundesland="Bayern")
    at = Region(slug="zillertal", name="Zillertal", land="AT", bundesland="Tirol")
    tirol = Quelle(key="tirol", adapter="test", name="tirol.at", base_url="https://www.tirol.at",
                   config={"rang": 3}, last_status="ok")
    fischbachau = Gebiet(slug="fischbachau", name="Fischbachau", region=de, tourist_url="https://example.org",
                         lat=47.716, lon=11.951, hoehe_m=780, wetterstation_id="1550",
                         wetterstation_name="Kreuth-Glashütte", wetterdienst="dwd")
    mayrhofen = Gebiet(slug="mayrhofen", name="Mayrhofen und Hippach", region=at, tourist_url="https://www.tirol.at",
                       lat=47.169, lon=11.857, hoehe_m=630, wetterstation_id="61", wetterstation_name="Mayrhofen",
                       wetterdienst="geosphere")
    s.add_all([de, at, tirol, fischbachau, mayrhofen])
    s.flush()
    for g, cm, quelle in ((fischbachau, 0.0, "DWD"), (mayrhofen, mayrhofen_cm, "GeoSphere Austria (CC BY 4.0)")):
        if cm is None:
            continue
        for i in range(1, 4):  # die Messungen kommen mit einem Tag Verzug
            s.add(Wetter(gebiet_id=g.id, datum=HEUTE - timedelta(days=i), art=WetterArt.MESSUNG.value,
                         schneehoehe_cm=cm, neuschnee_cm=0.0, niederschlag_mm=0.0, station_id=g.wetterstation_id,
                         quelle=quelle))
    l = Loipe(quelle=tirol, gebiet=mayrhofen, source_key="ginzling", name="Langlaufen: Ginzling Loipe",
              source_url="https://www.tirol.at/ginzling", lat=47.0994, lon=11.80993)
    s.add(l)
    s.flush()
    s.add(Zustand(loipe_id=l.id, status="offen", abgerufen_at=JETZT - timedelta(minutes=40),
                  zuletzt_bestaetigt_at=JETZT - timedelta(minutes=40)))
    s.flush()


@pytest.fixture(scope="module")
def seiten(engine, tmp_path_factory):
    """Je eine Seite: Station Mayrhofen misst 15 cm, misst nichts, misst 0 cm."""
    wurzel = tmp_path_factory.mktemp("schnee")
    for name, cm in (("schnee", 15.0), ("ohne", None), ("null", 0.0)):
        with engine.connect() as conn:
            trans = conn.begin()
            s = Session(bind=conn, join_transaction_mode="create_savepoint")
            _welt(s, cm)
            generator.erzeuge(s, wurzel / name, JETZT)
            s.close()
            trans.rollback()

    class Still(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Still, directory=str(wurzel)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def startseite(browser, seiten, name):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="de-DE")
    page = ctx.new_page()
    fehler = []
    page.on("pageerror", lambda e: fehler.append(str(e)))
    page.goto(f"{seiten}/{name}/#/?ort=Fischbachau")
    page.wait_for_selector(".reco")
    karte = {"titel": page.locator(".reco h2").inner_text(), "loipe": page.locator(".reco .big").inner_text(),
             "zeile": page.locator(".reco p").inner_text(), "chip": page.locator("#reco-schnee").inner_text()}
    ctx.close()
    assert fehler == []
    return karte


@pytest.mark.req("U45", ak=1)
def test_u45_chip_zeigt_station_der_empfohlenen_loipe(browser, seiten):  # noqa: F811
    k = startseite(browser, seiten, "schnee")
    assert k["loipe"] == "Langlaufen: Ginzling Loipe"
    assert "Fischbachau" not in k["chip"]
    assert re.fullmatch(r"Schnee Station Mayrhofen: 15 cm \(\d\d\.\d\d\.\)", k["chip"]), k["chip"]


@pytest.mark.req("U45", ak=2)
def test_u45_ohne_messung_kein_fremder_wert(browser, seiten):  # noqa: F811
    k = startseite(browser, seiten, "ohne")
    assert k["loipe"] == "Langlaufen: Ginzling Loipe"
    assert k["chip"] == "Schneehöhe Mayrhofen und Hippach: keine Messung"


@pytest.mark.req("U45", ak=3)
def test_u45_weit_entfernte_empfehlung_nennt_die_entfernung(browser, seiten):  # noqa: F811
    k = startseite(browser, seiten, "schnee")
    assert k["titel"].lower() == "nächste offene loipe"
    assert re.fullmatch(r"Mayrhofen und Hippach · Offen · \d+ km entfernt", k["zeile"]), k["zeile"]


@pytest.mark.req("U45", ak=1)
@pytest.mark.req("D19", ak=1)
def test_u45_bei_0_cm_in_mayrhofen_keine_empfehlung(browser, seiten):  # noqa: F811
    """Mit 0 cm an der Station Mayrhofen ist die Ginzling-Meldung unplausibel (E-23): keine Empfehlung, der
    Chip gehoert dann zum Gebiet am Standort und nennt dessen Station."""
    k = startseite(browser, seiten, "null")
    assert k["loipe"] == "Heute keine offene Loipe"
    assert k["titel"].lower() == "heute in deiner nähe"
    assert k["chip"].startswith("Schnee Station Kreuth-Glashütte: 0 cm")
