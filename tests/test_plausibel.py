"""Plausibilitaetspruefung offener Meldungen: D19 (E-23, N-39).

Die Werte stammen aus der Ist-Analyse der Testseite vom 19.11.2026: Ginzling Loipe (nur tirol.at, ohne
Datum, Station Mayrhofen 0 cm, bis +8 Grad), Samnaun L1 (Schneebericht vom 15.10.), Ramsau Stadionloipe
(tourinfra mit gespurten Kilometern), SnowFactory Loipe Seefeld (Snowfarming)."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from loipen import generator
from loipen.ereignisse import Ereignis
from loipen.generator.daten import baue
from loipen.konfig import CONFIG_DIR
from loipen.models import Gebiet, Loipe, Quelle, Region, Status, Wetter, WetterArt, Zustand
from loipen.plausibel import gruende
from loipen.worker.__main__ import ohne_unplausible

BERLIN = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 11, 19, 12, 12, tzinfo=BERLIN)
HEUTE = JETZT.date()
STATIC = Path(generator.__file__).parent / "static"


class Welt:
    def __init__(self, session):
        self.s = session
        self.region = Region(slug="test-region", name="Testregion", land="AT", bundesland="Tirol")
        session.add(self.region)
        self.quellen: dict[str, Quelle] = {}

    def quelle(self, key: str, rang: int) -> Quelle:
        if key not in self.quellen:
            q = Quelle(key=key, adapter="test", name=f"Quelle {key}", base_url=f"https://{key}.example",
                       config={"rang": rang}, last_status="ok")
            self.s.add(q)
            self.quellen[key] = q
        return self.quellen[key]

    def gebiet(self, slug: str, schnee_cm: float | None = 0.0, messtag: date | None = HEUTE,
               tmax: float | None = 8.3, station: str = "Mayrhofen") -> Gebiet:
        g = Gebiet(slug=slug, name=slug.title(), region=self.region, tourist_url="https://example.org",
                   lat=47.1, lon=11.8, hoehe_m=630, wetterstation_id="61", wetterstation_name=station)
        self.s.add(g)
        self.s.flush()
        if messtag is not None:
            for i in range(3):
                self.s.add(Wetter(gebiet_id=g.id, datum=messtag - timedelta(days=i), art=WetterArt.MESSUNG.value,
                                  schneehoehe_cm=schnee_cm, neuschnee_cm=0.0, niederschlag_mm=1.0,
                                  station_id="61", quelle="GeoSphere Austria (CC BY 4.0)"))
        self.s.add(Wetter(gebiet_id=g.id, datum=HEUTE, art=WetterArt.VORHERSAGE.value, temp_min_c=2.8,
                          temp_max_c=tmax, niederschlag_mm=1.5, quelle="Bright Sky"))
        return g

    def loipe(self, gebiet: Gebiet, name: str, quelle: str = "tirol", rang: int = 3, status: str = "offen",
              stand: datetime | None = None, km: float | None = None, lat: float = 47.0994) -> Loipe:
        l = Loipe(quelle=self.quelle(quelle, rang), gebiet=gebiet, source_key=f"{quelle}-{name}", name=name,
                  source_url=f"https://{quelle}.example/{name}", lat=lat, lon=11.80993)
        self.s.add(l)
        self.s.flush()
        self.s.add(Zustand(loipe_id=l.id, status=status, quelle_aktualisiert_at=stand, gespurt_gesamt_km=km,
                           status_klassisch=status if km else None,
                           abgerufen_at=JETZT - timedelta(minutes=40), zuletzt_bestaetigt_at=JETZT - timedelta(minutes=40)))
        self.s.flush()
        return l


def loipen_nach_name(daten: dict) -> dict[str, dict]:
    return {l["name"]: l for r in daten["regionen"].values() for g in r["gebiete"] for l in g["loipen"]}


@pytest.mark.req("D19", ak=1)
def test_d19_offen_ohne_beleg_bei_0_cm_wird_geschlossen(session):
    w = Welt(session)
    g = w.gebiet("mayrhofen")
    w.loipe(g, "Langlaufen: Ginzling Loipe")
    daten = baue(session, JETZT, CONFIG_DIR)
    l = loipen_nach_name(daten)["Langlaufen: Ginzling Loipe"]
    assert l["status"] == Status.GESCHLOSSEN.value
    assert l["status_laut_quelle"] == Status.OFFEN.value
    assert l["unplausibel"] == ["Station Mayrhofen misst am 19.11. 0 cm Schnee, kein Neuschnee in 72 Stunden, heute bis +8 °C"]
    assert daten["index"]["kennzahlen"]["unplausibel"] == 1
    assert daten["index"]["kennzahlen"]["offen"] == 0


@pytest.mark.req("D19", ak=1)
@pytest.mark.parametrize("name, quelle, rang, stand, km, schnee_cm", [
    ("SnowFactory Loipe Seefeld", "seefeld", 2, None, None, 0.0),  # Snowfarming: technischer Schnee
    ("Opening Loipe Sedlsee small", "tirol", 3, None, None, 0.0),
    ("Stadionloipe", "ramsau", 1, None, 2.0, 0.0),  # gespurte Kilometer belegen die Meldung
    ("Rundkurs Point", "tegernsee", 1, JETZT - timedelta(hours=5), None, 0.0),  # frischer eigener Stand
    ("Holzgau Runde 1", "tirol", 3, None, None, 12.0),  # Station misst Schnee
])
def test_d19_belegte_oder_sonderloipen_bleiben_offen(session, name, quelle, rang, stand, km, schnee_cm):
    w = Welt(session)
    g = w.gebiet("gebiet", schnee_cm=schnee_cm)
    w.loipe(g, name, quelle, rang, stand=stand, km=km)
    l = loipen_nach_name(baue(session, JETZT, CONFIG_DIR))[name]
    assert l["status"] == Status.OFFEN.value
    assert "unplausibel" not in l


@pytest.mark.req("D19", ak=1)
def test_d19_alte_schneemessung_sagt_nichts_ueber_heute(session):
    w = Welt(session)
    g = w.gebiet("vals", messtag=HEUTE - timedelta(days=5))
    w.loipe(g, "Loipe Vals")
    assert loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["Loipe Vals"]["status"] == Status.OFFEN.value


@pytest.mark.req("D19", ak=2)
def test_d19_meldung_aelter_als_7_tage_wird_geschlossen(session):
    w = Welt(session)
    g = w.gebiet("samnaun", schnee_cm=None, messtag=None)  # Schweiz: keine Schneedaten
    w.loipe(g, "L1 Samnaun Dorf (2 km)", "myswitzerland", 2,
            stand=datetime(2026, 10, 15, 15, 5, tzinfo=BERLIN), km=1.5)
    l = loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["L1 Samnaun Dorf (2 km)"]
    assert l["status"] == Status.GESCHLOSSEN.value
    assert l["status_klassisch"] == Status.GESCHLOSSEN.value
    assert l["unplausibel"] == ["Die Meldung der Quelle ist vom 15.10.2026, älter als 7 Tage"]


@pytest.mark.req("D19", ak=3)
def test_d19_oertlicher_bericht_meldet_geschlossen(session):
    w = Welt(session)
    g = w.gebiet("seefeld", schnee_cm=None, messtag=None)
    w.loipe(g, "Wildmoosloipe", "seefeld-tourinfra", 1, stand=JETZT - timedelta(hours=2), km=3.0)
    w.loipe(g, "Wildmoosloipe", "seefeld", 2, status="geschlossen", stand=JETZT - timedelta(hours=1))
    l = loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["Wildmoosloipe"]
    assert l["status"] == Status.GESCHLOSSEN.value
    assert l["unplausibel"] == ["Der Loipenbericht vor Ort (Quelle seefeld) meldet sie geschlossen"]


@pytest.mark.req("D19", ak=3)
def test_d19_landesportal_geschlossen_widerspricht_nicht(session):
    """tirol.at meldet fast alles als "nicht geöffnet"; das ist kein Widerspruch zu einem oertlichen Bericht."""
    w = Welt(session)
    g = w.gebiet("leutasch", schnee_cm=None, messtag=None)
    w.loipe(g, "A2 Snowfarmingloipe", "seefeld-tourinfra", 1, stand=JETZT - timedelta(hours=2), km=2.8)
    w.loipe(g, "A2 Snowfarmingloipe", "tirol", 3, status="geschlossen")
    assert loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["A2 Snowfarmingloipe"]["status"] == Status.OFFEN.value


@pytest.mark.req("D19", ak=6)
def test_d19_ohne_schneedaten_greift_die_schneeregel_nicht(session):
    w = Welt(session)
    g = w.gebiet("malbun", schnee_cm=None, messtag=None)
    w.loipe(g, "Loipennetz Malbun und Steg", "myswitzerland", 2)
    assert loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["Loipennetz Malbun und Steg"]["status"] == "offen"


@pytest.mark.req("D19", ak=1)
def test_d19_geschlossene_meldung_wird_nicht_geprueft():
    assert gruende(None, "offen", None, None, None, [], JETZT) == []
    z = Zustand(status="geschlossen")
    assert gruende(z, "geschlossen", None, {"messtag": HEUTE, "schneehoehe_cm": 0.0}, 9.0, ["X"], JETZT) == []


@pytest.mark.req("D19", ak=4)
def test_d19_seite_zeigt_meldung_und_grund(session, tmp_path):
    w = Welt(session)
    g = w.gebiet("mayrhofen")
    w.loipe(g, "Langlaufen: Ginzling Loipe")
    menge: set[int] = set()
    generator.erzeuge(session, tmp_path, JETZT, unplausibel=menge)
    assert len(menge) == 1
    index = json.loads((tmp_path / "daten.json").read_text(encoding="utf-8"))
    assert index["kennzahlen"]["unplausibel"] == 1
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'id="unplausibel"' in js and "plausiBadge(l)" in js
    assert "Wir zeigen sie deshalb geschlossen" in js


@pytest.mark.req("D19", ak=5)
def test_d19_push_und_abo_melden_unplausible_oeffnung_nicht():
    e = [Ereignis("oeffnet", "Ginzling", "mayrhofen", "Mayrhofen", "zillertal", "offen", loipe_id=1),
         Ereignis("frisch_gespurt", "Ginzling", "mayrhofen", "Mayrhofen", "zillertal", "offen", loipe_id=1),
         Ereignis("schliesst", "Ginzling", "mayrhofen", "Mayrhofen", "zillertal", "geschlossen", loipe_id=1),
         Ereignis("oeffnet", "Stadionloipe", "ramsau", "Ramsau", "schladming", "offen", loipe_id=2)]
    rest = ohne_unplausible(e, {1})
    assert [(x.art, x.loipe_id) for x in rest] == [("schliesst", 1), ("oeffnet", 2)]
