"""Loipenberichte weiterer Tiroler Tourismusverbaende (P22): Achensee, Kufsteinerland, Kaiserwinkl.

Schnappschuesse vom 13.11.2026 (Workflow Schnappschuss, Runde 8):
- tests/fixtures/achensee/2026-11-13/schneebericht.html: contwise-Schneebericht (24 Loipen, km je Technik)
- tests/fixtures/kufsteinerland/2026-11-13/schneebericht.html: Skidata-Schneebericht (Status je Loipe)
- tests/fixtures/kaiserwinkl/2026-11-13/geoeffnete-loipen.html: Loipenbericht Kaiserwinkl (23 Loipen)
Am 13.11. war in allen drei Regionen noch alles geschlossen.
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator
from loipen.adapters.normalisierung import parse_datum
from loipen.adapters.tvb_tirol import AchenseeAdapter, KaiserwinklAdapter, SkidataAdapter, _zustaende_aus_css
from loipen.dubletten import gleich, kennungen
from loipen.models import Loipe, Quelle, Schwierigkeit, Status, Technik, Zustand
from tests.helpers import lade_alle_fixtures
from tests.test_lokale_quellen import e, gebiet, lauf

JETZT = datetime(2026, 11, 13, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
BERLIN = ZoneInfo("Europe/Berlin")


@pytest.mark.req("P22", ak=1)
def test_p22_achensee_schneebericht_mit_km_je_technik_und_stand():
    r = lauf("achensee", AchenseeAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 24
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    a3 = next(l for l in r.loipen if l.name == "A3 - Ortsloipe Achenkirch")
    assert a3.gebiet_slug == "steinberg-rofan" and a3.technik == Technik.BEIDES
    assert (a3.gespurt_klassisch_km, a3.gespurt_skating_km, a3.laenge_km) == (0.0, 0.0, 10.0)
    assert a3.schwierigkeit == Schwierigkeit.LEICHT
    assert a3.quelle_aktualisiert_at == datetime(2026, 11, 13, 9, 16, tzinfo=BERLIN)
    m2 = next(l for l in r.loipen if l.name.startswith("M2"))
    assert m2.technik == Technik.KLASSISCH and m2.laenge_km == 4.5 and m2.gebiet_slug == "achensee"
    # Maurach meldet seit September nicht mehr: der alte Stand bleibt sichtbar (die Seite nennt ihn veraltet)
    assert m2.quelle_aktualisiert_at.date().isoformat() == "2026-09-23"
    assert all(not l.unbekannte_begriffe for l in r.loipen)


@pytest.mark.req("P22", ak=1)
def test_p22_kufsteinerland_status_aus_dem_css_der_seite():
    r = lauf("kufsteinerland", SkidataAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 22
    assert not any("Bayrischzell" in l.rohtext for l in r.loipen)  # meldet bayrischzell.de selbst
    ku1 = next(l for l in r.loipen if l.name == "KU1 Weissach I")
    assert ku1.status == Status.GESCHLOSSEN and ku1.laenge_km == 2.5 and ku1.gebiet_slug == "kufstein"
    assert ku1.quelle_aktualisiert_at == datetime(2026, 11, 11, 14, 8, tzinfo=BERLIN)
    assert {l.gebiet_slug for l in r.loipen} == {"kufstein", "thiersee", "langkampfen", "bad-haering", "schwoich",
                                                  "ebbs", "niederndorf"}


def test_skidata_zustaende_stehen_im_css():
    css = '.state1:after {content: "geöffnet";} .state2:after {content: "geschlossen";} .state4:after { content: "teilgeöffnet";}'
    assert _zustaende_aus_css(css) == {"state1": "geöffnet", "state2": "geschlossen", "state4": "teilgeöffnet"}
    html = ('<style>' + css + '</style><div class="skidataCrossCountry"><div class="kufsteinerland region"><div class="kufstein">'
            '<h3>Kufstein</h3><div class="headline"></div>'
            '<div class="entry"><div class="name">KU1 Weissach I</div><div class="length">2500 m</div><div class="state state1"></div></div>'
            '<div class="entry"><div class="name">KU2 Weissach II</div><div class="length">-</div><div class="state state4"></div></div>'
            '<div class="entry"><div class="name">KU9 Neu</div><div class="length">1 km</div><div class="state state7"></div></div>'
            '<p class="footer">Letztes Update am 20.12.2026 07:45:00</p></div></div></div>')

    class F:
        def get(self, url):
            return html
    r = SkidataAdapter().run("https://www.kufstein.com", {"default_gebiet": "kufstein", "regionen": ["kufsteinerland"]}, F())
    assert [l.status for l in r.loipen] == [Status.OFFEN, Status.EINGESCHRAENKT, Status.UNBEKANNT]
    assert r.loipen[1].laenge_km is None
    assert r.loipen[2].unbekannte_begriffe == [("status", "state7")]  # neuer Zustand wird gemeldet (P5)
    assert r.loipen[0].quelle_aktualisiert_at == datetime(2026, 12, 20, 7, 45, tzinfo=BERLIN)


@pytest.mark.req("P22", ak=1)
def test_p22_kaiserwinkl_loipenbericht():
    r = lauf("kaiserwinkl", KaiserwinklAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 23
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    hochau = next(l for l in r.loipen if l.name == "Hochauloipe - Kössen Nr. 2")
    assert hochau.laenge_km == 9.0 and hochau.gebiet_slug == "koessen"
    assert hochau.quelle_aktualisiert_at == datetime(2026, 11, 13, 9, 15, tzinfo=BERLIN)
    assert next(l for l in r.loipen if l.name.startswith("Miesbergloipe")).gebiet_slug == "walchsee"
    assert next(l for l in r.loipen if l.name == "Bichlachrunde").gebiet_slug == "schwendt"


def test_parse_datum_mit_komma():
    assert parse_datum("Zuletzt aktualisiert am 13.11.2026, 09:15 Uhr") == datetime(2026, 11, 13, 9, 15, tzinfo=BERLIN)


@pytest.mark.parametrize("adapter, key", [(AchenseeAdapter(), "achensee"), (SkidataAdapter(), "kufsteinerland"),
                                          (KaiserwinklAdapter(), "kaiserwinkl")])
def test_p22_geaenderter_aufbau_gibt_warnung(adapter, key):
    class Leer:
        def get(self, url):
            return "<html><body><main><p>Wartungsarbeiten</p></main></body></html>"
    from tests.test_lokale_quellen import quelle
    q = quelle(key)
    r = adapter.run(q["base_url"], q["config"], Leer())
    assert r.loipen == [] and r.warnungen


# ---------- Abgleich ueber Verbandsnummern ----------

@pytest.mark.req("P22", ak=2)
def test_p22_verbandsnummer_entscheidet_ohne_koordinate():
    def a(i, name, quelle, rang, lat=None, lon=None):
        return e(i, name, quelle, rang, lat, lon, gebiet="achensee", gname="Achensee", region="achensee-karwendel")
    assert kennungen("SC3a Ganzer-Runde(beschneit, beleuchtet)") == {"sc3a"}
    assert kennungen("Hochauloipe - Kössen Nr. 2a") == set()
    assert gleich(a(1, "P4 - Loipe Pletzach-Gern", "achensee", 2), a(2, "P4 - Gerntal", "tirol", 3, 47.4, 11.7))
    assert gleich(a(1, "P3 - Loipe Falzthurn-Gramai", "achensee", 2), a(2, "Falzthurn-Gramai | P3", "tirol", 3, 47.4, 11.7))
    assert not gleich(a(1, "BH3 Sprint-Loipe", "kufsteinerland", 2), a(2, "BH1 Sprint-Loipe", "tirol", 3, 47.5, 12.1))


@pytest.fixture(scope="module")
def site(engine, tmp_path_factory):
    from sqlalchemy.orm import Session

    ziel = tmp_path_factory.mktemp("site_tvb")
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        lade_alle_fixtures(s, JETZT)
        # P22 AK 3: tirol.at meldet eine Loipe als offen, die der Kufsteiner Bericht nicht fuehrt
        tirol = s.scalar(select(Quelle).where(Quelle.key == "tirol"))
        ht1 = s.scalar(select(Loipe).where(Loipe.quelle_id == tirol.id, Loipe.name == "HT1 Übungs-Loipe"))
        s.add(Zustand(loipe_id=ht1.id, status=Status.OFFEN.value, abgerufen_at=JETZT, zuletzt_bestaetigt_at=JETZT))
        s.flush()
        generator.erzeuge(s, ziel, JETZT)
        s.close()
        trans.rollback()
    return ziel


@pytest.mark.req("P22", ak=2)
def test_p22_verbandsbericht_fuehrt_vor_tirol_at(site):
    kufstein = gebiet(site, "kufstein")["loipen"]
    assert [l["name"] for l in kufstein] == [f"KU{i} {n}" for i, n in enumerate(
        ["Weissach I", "Weissach II", "Sparchen I", "Sparchen II", "Endach", "Morsbach I", "Morsbach II"], 1)]
    ku1 = kufstein[0]
    assert ku1["quelle"]["name"] == "Kufsteinerland (Schneebericht)"
    assert ku1["quelle_stand"].startswith("2026-11-11T14:08")
    assert ku1["auch_bei"][0]["quelle"] == "Tirol Werbung (tirol.at)"
    assert ku1["lat"] is not None  # Lage von tirol.at
    namen = [l["name"] for l in gebiet(site, "achensee")["loipen"]]
    assert "P4 - Gerntal" not in namen and "P4 - Loipe Pletzach-Gern" in namen


@pytest.mark.req("P22", ak=3)
def test_p22_offen_nur_bei_tirol_at_gilt_als_unbestaetigt(site):
    ht1 = next(l for l in gebiet(site, "thiersee")["loipen"] if l["name"] == "HT1 Übungs-Loipe")
    assert ht1["status"] == "unbekannt" and ht1["status_laut_quelle"] == "offen"
    assert ht1["nicht_im_bericht"] == "Kufsteinerland (Schneebericht)"
    # in Gebieten ohne eigenen Bericht bleibt tirol.at massgeblich
    ellmau = gebiet(site, "ellmau")["loipen"]
    assert all(l["nicht_im_bericht"] is None for l in ellmau)
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    assert index["kennzahlen"]["loipen"] > 0
