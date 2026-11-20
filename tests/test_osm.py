"""OpenStreetMap-Strecken und -Parkplaetze, Anreise je Loipe, Bestandsaufnahme: P36, P37, U45, D20 (E-25)."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator, osm
from loipen.bestandsaufnahme import als_markdown, lies_seite
from loipen.fetcher import HttpFehler, RobotsVerbot
from loipen.models import Gebiet, Loipe, OsmDaten, Parkplatz, Quelle, Region

JETZT = datetime(2026, 11, 20, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
STATIC = Path(generator.__file__).parent / "static"


def weg(oid, name, punkte, **tags):
    return {"type": "way", "id": oid, "tags": {"piste:type": "nordic", **({"name": name} if name else {}), **tags},
            "geometry": [{"lat": a, "lon": b} for a, b in punkte]}


def park(oid, lat, lon, typ="node", **tags):
    e = {"type": typ, "id": oid, "tags": {"amenity": "parking", **tags}}
    if typ == "node":
        e.update(lat=lat, lon=lon)
    else:
        e["center"] = {"lat": lat, "lon": lon}
    return e


# Eine Runde von etwa 4 km bei 47.60/11.70 und eine zweite, die weit weg liegt
RUNDE = [(47.600, 11.700), (47.610, 11.700), (47.610, 11.715), (47.600, 11.715), (47.600, 11.701)]
ANTWORT = {"elements": [
    weg(1, "Sonnenloipe", RUNDE),
    weg(2, None, [(47.6, 11.7), (47.61, 11.7)]),                                  # unbenannt
    weg(3, "Sonnenloipe", [(47.70, 11.90), (47.71, 11.90)]),                       # gleicher Name, 20 km weg
    weg(4, "Rundloipe", RUNDE),                                                    # nur ein allgemeines Wort
    {"type": "relation", "id": 9, "tags": {"piste:type": "nordic", "type": "route", "name": "Moosrunde"},
     "members": [{"type": "way", "geometry": [{"lat": 47.62, "lon": 11.70}, {"lat": 47.63, "lon": 11.70}]},
                 {"type": "way", "geometry": [{"lat": 47.63, "lon": 11.70}, {"lat": 47.63, "lon": 11.71}]}]},
    park(10, 47.6005, 11.7003, fee="yes", name="Parkplatz Sonnenloipe"),
    park(11, 47.6020, 11.7010, typ="way", fee="no"),
    park(12, 47.6001, 11.7001, access="private"),                                  # privat
    park(13, 47.6001, 11.7002, parking="underground"),                             # Tiefgarage
    park(14, 47.6100, 11.7300),                                                    # ueber 500 m
]}


def loipe(name, lat=47.6001, lon=11.7001, laenge=4.0):
    return {"name": name, "lat": lat, "lon": lon, "laenge_km": laenge}


GEBIET = {"name": "Testdorf", "lat": 47.605, "lon": 11.705}


@pytest.mark.req("P36", ak=2)
def test_p36_verdichten_behaelt_nur_benannte_loipen_und_oeffentliche_parkplaetze():
    d = osm.verdichte(json.dumps(ANTWORT))
    assert {l["id"] for l in d["loipen"]} == {"way/1", "way/3", "way/4", "relation/9"}
    assert len(next(l for l in d["loipen"] if l["id"] == "relation/9")["linien"]) == 2
    assert 3.5 < next(l for l in d["loipen"] if l["id"] == "way/1")["laenge_km"] < 4.5
    parks = {p["id"]: p for p in d["parkplaetze"]}
    assert set(parks) == {"node/10", "way/11", "node/14"}
    assert parks["node/10"]["gebuehr_text"] == "gebührenpflichtig laut OpenStreetMap"
    assert parks["way/11"]["gebuehr_text"] == "kostenlos laut OpenStreetMap" and parks["way/11"]["lat"] == 47.602
    assert parks["node/14"]["gebuehr_text"] is None


@pytest.mark.req("P36", ak=2)
def test_p36_zuordnung_nach_name_lage_und_laenge():
    d = osm.verdichte(ANTWORT)
    assert osm.strecke_fuer(loipe("Sonnenloipe Testdorf"), GEBIET, d["loipen"])["id"] == "way/1"
    # Name passt nicht
    assert osm.strecke_fuer(loipe("Talloipe"), GEBIET, d["loipen"]) is None
    # nur das allgemeine Wort "Rundloipe": nie
    assert osm.strecke_fuer(loipe("Rundloipe"), GEBIET, d["loipen"]) is None
    # Startpunkt 5 km entfernt
    assert osm.strecke_fuer(loipe("Sonnenloipe", lat=47.645), GEBIET, d["loipen"]) is None
    # Laenge weicht um mehr als Faktor 2 ab
    assert osm.strecke_fuer(loipe("Sonnenloipe", laenge=10), GEBIET, d["loipen"]) is None
    assert osm.strecke_fuer(loipe("Sonnenloipe", laenge=None), GEBIET, d["loipen"])["id"] == "way/1"
    # Route aus zwei Wegen
    assert osm.strecke_fuer(loipe("Moosrunde", lat=47.62, lon=11.70, laenge=2), GEBIET, d["loipen"])["id"] == "relation/9"


@pytest.mark.req("P36", ak=2)
def test_p36_ohne_startpunkt_nur_eindeutig_nahe_der_gebietsmitte():
    d = osm.verdichte(ANTWORT)
    ohne = loipe("Sonnenloipe", lat=None, lon=None)
    assert osm.strecke_fuer(ohne, GEBIET, d["loipen"])["id"] == "way/1"  # die zweite liegt 20 km weg
    weit = {"name": "Testdorf", "lat": 47.655, "lon": 11.80}  # beide Kandidaten zu weit oder fast gleich weit
    assert osm.strecke_fuer(ohne, weit, d["loipen"]) is None
    assert osm.strecke_fuer(ohne, {"name": "X", "lat": None, "lon": None}, d["loipen"]) is None


@pytest.mark.req("P37", ak=2)
def test_p37_osm_parkplaetze_bis_500_m_naechster_zuerst():
    d = osm.verdichte(ANTWORT)
    p = osm.parkplaetze_bei((47.6001, 11.7001), d["parkplaetze"])
    assert [x["name"] for x in p] == ["Parkplatz Sonnenloipe", "Parkplatz"]
    assert p[0]["entfernung_m"] < p[1]["entfernung_m"] <= 500
    assert all(x["quelle"] == "OpenStreetMap" and x["url"].startswith("https://www.openstreetmap.org/") for x in p)


OSM_FIXTURES = Path(__file__).parent / "fixtures" / "osm" / "2026-11-20"


@pytest.mark.req("P36", ak=2)
def test_p36_waymarked_trails_route_aus_echtem_schnappschuss():
    """Ringseeloipe (Gmund) aus slopes.waymarkedtrails.org, Schnappschuss vom 20.11.2026."""
    r = osm.wmt_route((OSM_FIXTURES / "wmt-relation-6850122.json").read_text(encoding="utf-8"))
    assert r["id"] == "relation/6850122" and r["namen"] == ["Ringseeloipe"] and r["laenge_km"] == 4.72
    lat, lon = r["linien"][0][0]
    assert 47.67 < lat < 47.69 and 11.74 < lon < 11.77  # Web-Mercator richtig umgerechnet
    liste = json.loads((OSM_FIXTURES / "wmt-liste-tegernsee.json").read_text(encoding="utf-8"))["results"]
    namen = [x["name"] for x in liste if x.get("group") == osm.WMT_GRUPPE_NORDISCH and x.get("name")]
    assert len(namen) == 40 and "Wallberg-Rodelbahn" not in namen  # Rodelbahn und Abfahrten fallen weg
    # echte Namenspaare aus Tegernsee, Leitzachtal, Achensee und Toblach
    assert osm.name_passt("Kloo-Ascher-Runde Bayrischzell", ["Kloo-Ascher Runde"], "Bayrischzell")
    assert osm.name_passt("Loipe Kreuth - Scharling", ["Loipe Kreuth-Scharling"], "Kreuth")
    assert not osm.name_passt("Loipe Kreuth - Scharling", ["Sonnenloipe Scharling-Oberhof"], "Kreuth")
    assert not osm.name_passt("P6 - Übungsloipe Pertisau", ["Dorfloipe Pertisau"], "Achensee")
    assert osm.name_passt("P6 - Übungsloipe Pertisau", ["Übungsloipe Pertisau"], "Achensee")
    assert not osm.name_passt("01 Toblacher Stadionrunde", ["Kleine Toblacher See Runde"], "Toblach")
    assert osm.name_passt("Verbindungsloipe Bad Wiessee", ["Verbindungsloipe Bad Wiessee"], "Bad Wiessee")
    s = osm.strecke_fuer({"name": "Sportplatzrunde (kleine Runde)", "lat": 47.70, "lon": 11.76, "laenge_km": 1.7}, GEBIET,
                         [{"id": "relation/1", "namen": ["Loipe Sportplatzrunde (große Runde)"], "laenge_km": 3.5,
                           "linien": [[[47.70, 11.76], [47.71, 11.76]]]},
                          {"id": "relation/2", "namen": ["Loipe Sportplatzrunde (kleine Runde)"], "laenge_km": 1.7,
                           "linien": [[[47.70, 11.76], [47.705, 11.76]]]}])
    assert s["id"] == "relation/2"


@pytest.mark.req("P36", ak=4)
def test_p36_abruf_routen_und_parkplaetze_mit_ausweichserver_und_wochenrhythmus(session):
    region = Region(slug="testtal", name="Testtal", land="DE", bundesland="Bayern")
    session.add(region)
    session.flush()
    g = Gebiet(slug="gmund", name="Gmund", region_id=region.id, tourist_url="https://example.org", lat=47.75, lon=11.74)
    q = Quelle(key="t", name="T", base_url="https://example.org", adapter="x", config={})
    session.add_all([g, q])
    session.flush()
    session.add(Loipe(quelle_id=q.id, gebiet_id=g.id, source_key="r", name="Ringseeloipe", lat=47.677, lon=11.758,
                      source_url="https://example.org/r"))
    session.flush()
    session.expire_all()

    class Abrufer:
        def __init__(self):
            self.urls = []
            self.aus = False

        def get(self, url):
            self.urls.append(url)
            if self.aus:
                raise HttpFehler(url, 504)
            if "/list/by_area" in url:
                return (OSM_FIXTURES / "wmt-liste-tegernsee.json").read_text(encoding="utf-8")
            if url.endswith("/details/relation/6850122"):
                return (OSM_FIXTURES / "wmt-relation-6850122.json").read_text(encoding="utf-8")
            if "overpass-api.de" in url:
                raise RobotsVerbot("robots.txt verbietet " + url)
            if "kumi" in url:  # Overpass antwortete vom Runner nur mit 504: Parkplaetze synthetisch
                return json.dumps(ANTWORT)
            raise HttpFehler(url, 404)

    a = Abrufer()
    lauf = osm.aktualisiere(session, a, jetzt=JETZT)
    assert lauf.abgerufen == ["testtal"] and not lauf.fehler
    details = [u for u in a.urls if "/details/" in u]
    assert details == ["https://slopes.waymarkedtrails.org/api/v1/details/relation/6850122"]  # nur passende Namen
    parken = [u for u in a.urls if "interpreter" in u]
    assert "overpass-api.de" in parken[0] and "kumi" in parken[1] and "amenity" in parken[1]
    daten = session.get(OsmDaten, "testtal").inhalt
    assert [o["id"] for o in daten["loipen"]] == ["relation/6850122"] and daten["parkplaetze"]
    # nach drei Tagen nicht noch einmal; nach acht Tagen wieder, die Geometrie kommt aus dem Speicher (30 Tage)
    vorher = len(a.urls)
    assert osm.aktualisiere(session, a, jetzt=JETZT + timedelta(days=3)).abgerufen == []
    assert len(a.urls) == vorher
    assert osm.aktualisiere(session, a, jetzt=JETZT + timedelta(days=8)).abgerufen == ["testtal"]
    assert not [u for u in a.urls[vorher:] if "/details/" in u]
    # faellt alles aus, bleibt der alte Stand und der Lauf geht weiter
    a.aus = True
    spaeter = osm.aktualisiere(session, a, jetzt=JETZT + timedelta(days=16))
    assert spaeter.abgerufen == [] and spaeter.fehler
    assert session.get(OsmDaten, "testtal").inhalt["loipen"]


@pytest.mark.req("P36", ak=4)
def test_p36_ein_versagender_overpass_server_wird_im_lauf_nicht_wieder_gefragt():
    class Abrufer:
        urls = []

        def get(self, url):
            self.urls.append(url)
            raise HttpFehler(url, 504)

    a, aus = Abrufer(), set()
    for bbox in ((47.0, 11.0, 47.1, 11.1), (47.2, 11.0, 47.3, 11.1)):
        with pytest.raises((HttpFehler, RuntimeError)):
            osm.hole_parkplaetze(a, bbox, aus)
    assert len(a.urls) == 3  # jeder der drei Server nur einmal


# ---------- mit der erzeugten Seite ----------

@pytest.fixture
def testseite(session, tmp_path):
    """Eine Region mit drei Loipen: eine mit eigener Strecke, eine fuer OSM, eine ohne alles; dazu eine Dublette."""
    region = Region(slug="testtal", name="Testtal", land="DE", bundesland="Bayern")
    session.add(region)
    session.flush()
    g = Gebiet(slug="testdorf", name="Testdorf", region_id=region.id, tourist_url="https://example.org",
               lat=47.605, lon=11.705)
    session.add(g)
    session.flush()
    q1 = Quelle(key="testquelle", name="Testquelle", base_url="https://example.org", adapter="x", enabled=True,
                config={"rang": 1, "strecke_hinweis": "Testquelle nennt keinen Streckenverlauf."})
    q2 = Quelle(key="nebenquelle", name="Nebenquelle", base_url="https://example.com", adapter="x", enabled=True,
                config={"rang": 5})
    session.add_all([q1, q2])
    session.flush()

    def neu(q, key, name, lat, lon, laenge=None, verlauf=None):
        l = Loipe(quelle_id=q.id, gebiet_id=g.id, source_key=key, name=name, lat=lat, lon=lon, laenge_km=laenge,
                  verlauf=verlauf, source_url="https://example.org/" + key)
        session.add(l)
        return l

    neu(q1, "sonne", "Sonnenloipe", 47.6001, 11.7001, 4.0)
    neu(q1, "leer", "Waldweg-Spur", None, None)
    neu(q1, "dub", "Bachloipe", 47.65, 11.75, 3.0)
    neu(q2, "dub", "Bachloipe", 47.6502, 11.7502, 3.0,
        verlauf={"type": "LineString", "coordinates": [[11.7502, 47.6502], [11.76, 47.66]]})
    session.add(Parkplatz(gebiet_id=g.id, name="Parkplatz Bach (von Hand)", lat=47.6505, lon=11.7505,
                          gebuehr_text="3 € pro Tag", quelle_url="https://example.org/parken"))
    session.add(OsmDaten(region_slug="testtal", bbox=[0, 0, 0, 0], inhalt=osm.verdichte(ANTWORT), abgerufen_at=JETZT))
    session.flush()
    session.expire_all()
    generator.erzeuge(session, tmp_path, JETZT)
    return tmp_path


def seite_loipen(site):
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    r = next(r for r in index["regionen"] if r["slug"] == "testtal")
    daten = json.loads((site / r["datei"]).read_text(encoding="utf-8"))
    strecken = json.loads((site / r["strecken"]).read_text(encoding="utf-8"))
    return {l["name"]: l for g in daten["gebiete"] for l in g["loipen"]}, strecken, r


@pytest.mark.req("P36", ak=1)
def test_p36_strecke_von_der_dublette(testseite):
    loipen, strecken, _ = seite_loipen(testseite)
    bach = loipen["Bachloipe"]
    assert bach["quelle"]["name"] == "Testquelle" and bach["strecke_von"] == "Nebenquelle"
    assert strecken[str(bach["id"])][0] == [47.6502, 11.7502] and bach["strecke_hinweis"] is None


@pytest.mark.req("P36", ak=[2, 3])
def test_p36_osm_strecke_in_der_seite_mit_herkunft(testseite):
    loipen, strecken, r = seite_loipen(testseite)
    sonne = loipen["Sonnenloipe"]
    assert sonne["strecke_von"] == "OpenStreetMap" and sonne["strecke_osm"]["url"] == "https://www.openstreetmap.org/way/1"
    assert strecken[str(sonne["id"])][0] == [47.6, 11.7] and r["strecken_anzahl"] == 2
    leer = loipen["Waldweg-Spur"]
    assert leer["strecke_von"] is None and str(leer["id"]) not in strecken
    assert leer["strecke_hinweis"] == "Testquelle nennt keinen Streckenverlauf."
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "nicht von ' + esc(l.quelle.name) + ' bestätigt" in js and "OpenStreetMap-Mitwirkende</a>, ODbL" in js
    hinweise = (testseite / "hinweise.html").read_text(encoding="utf-8")
    assert 'id="osm-daten"' in hinweise and "Open Database License (ODbL) 1.0" in hinweise


@pytest.mark.req("P37", ak=[1, 2, 3])
def test_p37_parkplaetze_je_loipe(testseite):
    loipen, _, _ = seite_loipen(testseite)
    bach = loipen["Bachloipe"]["parken"]  # von Hand recherchiert, 40 m vom Start: OSM wird nicht gebraucht
    assert [p["name"] for p in bach] == ["Parkplatz Bach (von Hand)"] and bach[0]["quelle"] == "hand"
    assert bach[0]["gebuehr_text"] == "3 € pro Tag" and bach[0]["entfernung_m"] < 100
    sonne = loipen["Sonnenloipe"]["parken"]  # der Handparkplatz liegt 6 km weg: OSM
    assert [p["quelle"] for p in sonne] == ["OpenStreetMap", "OpenStreetMap"]
    assert sonne[0]["name"] == "Parkplatz Sonnenloipe"
    # ohne Start und ohne Strecke: nur die Handparkplaetze des Gebiets, nie OSM
    assert [p["quelle"] for p in loipen["Waldweg-Spur"]["parken"]] == ["hand"]


@pytest.mark.req("D20", ak=[1, 2])
def test_d20_bestandsaufnahme_zaehlt_was_die_seite_zeigt(testseite):
    b = lies_seite(testseite)
    q = b.quellen["Testquelle"]
    assert (q.loipen, q.strecke, q.strecke_osm, q.strecke_dublette, q.lage, q.laenge) == (3, 2, 1, 1, 2, 2)
    assert (q.parken, q.parken_hand, q.parken_osm) == (3, 2, 1)
    assert "Nebenquelle" not in b.quellen  # die verdeckte Dublette zaehlt nicht
    md = als_markdown(b)
    assert "| Testquelle | 3 | 2 (67 %) | 1 |" in md
    assert "| Testtal | Testdorf | 3 | 1 | 0 | 1 | unbekannt | 0 |" in md


@pytest.mark.req("U45", ak=[1, 2, 3])
def test_u45_anreise_abschnitt_auf_der_loipenseite():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "function anreiseHtml(l)" in js and "miniKarte(l) + anreiseHtml(l)" in js
    assert "laut OpenStreetMap, nicht von der Loipenquelle bestätigt" in js and "vom Loipenstart" in js and "km\")" in js
    assert "noch keiner bekannt" in js and "Start der Loipe" in js
    assert "(l.parken || []).forEach" in js and "l.gebiet.parkplaetze.forEach" not in js
    assert "bei den einzelnen Loipen" in js


def test_p36_verbindungsnamen_mit_anderem_endpunkt_passen_nicht():
    """Echte Fehlzuordnungen aus der Treffergüte-Messung (Engadin, 20.11.): gleiche Seenloipe, anderer Abschnitt."""
    orte = "Maloja, Sils und Silvaplana"
    assert not osm.name_passt("009 Isola-Sils (Seenloipe)", ["Maloja-Isola"], orte)
    assert not osm.name_passt("035 Silvaplana/Surlej-Champfèrersee (Seenloipe)",
                              ["Sils - Silvaplana/Surlej (Seenloipe)"], orte)
    # gute Treffer bleiben
    assert osm.name_passt("006 Maloja-Isola (Seenloipe)", ["Maloja-Isola"], orte)
