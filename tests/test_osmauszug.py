"""OSM-Auszug: Haltestellen, Parkplaetze, Skiverleih mit Weg- und Fahrzeit (D22, D24).

Die Auswertung ist ohne Runner testbar: osmium-Export (GeoJSON-Seq) und OSRM-Zeitmatrix werden nachgebildet.
"""

import json

import pytest

from loipen import osmauszug as oa

START = [(47.6705, 12.0130)]  # Bayrischzell, Loipenstart Ortsmitte


def feature(oid: str, lat: float, lon: float, **tags) -> str:
    return "\x1e" + json.dumps({"type": "Feature", "id": oid, "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                "properties": tags})


GEOJSON = "\n".join([
    feature("node/1", 47.6757, 12.0110, railway="halt", name="Bayrischzell", public_transport="station"),
    feature("node/2", 47.6710, 12.0140, highway="bus_stop", name="Bayrischzell, Rathaus"),
    feature("node/3", 47.6712, 12.0141, highway="bus_stop", name="Bayrischzell, Rathaus"),  # Gegenrichtung
    feature("node/4", 47.6900, 12.0500, highway="bus_stop", name="Weit weg"),  # ueber 3 km Luftlinie
    feature("node/5", 47.6708, 12.0133, highway="bus_stop"),  # ohne Name
    feature("way/6", 47.6702, 12.0125, amenity="parking", name="Parkplatz Sportalm", fee="yes"),
    feature("way/7", 47.6703, 12.0126, amenity="parking", access="private"),
    feature("node/8", 47.6720, 12.0150, shop="ski", name="Sport Mustermann", **{"service:ski:rental": "yes"}),
    feature("node/9", 47.7400, 11.9000, shop="ski", name="Skihaus Tal"),
    feature("node/10", 47.6710, 12.0150, amenity="bench"),
])


@pytest.mark.req("D22", ak=1)
def test_d22_objekte_aus_dem_export():
    pois = oa.pois_aus_geojson(GEOJSON)
    arten = {p["url"].rsplit("/", 1)[-1] if p["url"] else None: p["art"] for p in pois}
    assert arten["1"] == "haltestelle_bahn" and arten["2"] == "haltestelle_bus"
    assert arten["6"] == "parkplatz" and "7" not in arten  # privat
    assert arten["8"] == "verleih" and arten["9"] == "skigeschaeft" and "10" not in arten


@pytest.mark.req("D24", ak=1)
def test_d24_vorauswahl_per_luftlinie():
    k = oa.kandidaten(START, oa.pois_aus_geojson(GEOJSON))
    assert [p["name"] for p in k["haltestellen"]] == ["Bayrischzell", "Bayrischzell, Rathaus", "Bayrischzell, Rathaus"]
    assert [p["name"] for p in k["parkplaetze"]] == ["Parkplatz Sportalm"]
    assert [p["name"] for p in k["verleih"]] == ["Sport Mustermann", "Skihaus Tal"]


@pytest.mark.req("D24", ak=[3, 4])
def test_d24_anzeige_nach_weg_und_fahrzeit():
    k = oa.kandidaten(START, oa.pois_aus_geojson(GEOJSON))
    zeiten = {
        "fuss_halt": [[540], [120], [150]],          # Sekunden zum Loipenstart
        "fuss_park": [[60]],
        "auto_verleih": [[90], [1500]],              # Skihaus Tal: 25 min Fahrt, faellt weg
        "fuss_verleih": [[300], [None]],
    }
    e = oa.gebiet_ergebnis(k, zeiten)
    assert [(h["name"], h["fuss_min"], h["art"]) for h in e["haltestellen"]] == [
        ("Bayrischzell, Rathaus", 2, "Bus"), ("Bayrischzell", 9, "Bahn")]  # je Name nur die naechste
    assert e["parkplaetze"][0]["gebuehr_text"] == "kostenpflichtig laut OpenStreetMap"
    assert e["parkplaetze"][0]["id"] == "way/6"
    assert len(e["verleih"]) == 1
    v = e["verleih"][0]
    assert (v["name"], v["auto_min"], v["fuss_min"], v["verleih_bestaetigt"]) == ("Sport Mustermann", 2, 5, True)
    zeiten["fuss_halt"] = [[1500], [1500], [1500]]
    assert oa.gebiet_ergebnis(k, zeiten)["haltestellen"] == []  # ueber 20 Minuten Fussweg


@pytest.mark.req("D22", ak=3)
def test_d22_handangaben_gehen_vor():
    hand = [{"name": "Bayrischzell", "art": "Bahn", "lat": 47.675704, "lon": 12.010998}]
    osm = [{"name": "Bayrischzell", "lat": 47.6757, "lon": 12.0110, "fuss_min": 9, "herkunft": "osm"},
           {"name": "Bahnhof Bayrischzell", "lat": 47.67571, "lon": 12.01101, "herkunft": "osm"},  # 1 m daneben
           {"name": "Rathaus", "lat": 47.6710, "lon": 12.0140, "fuss_min": 2, "herkunft": "osm"}]
    zusammen = oa.zusammen(hand, osm)
    assert [(h["name"], h["herkunft"]) for h in zusammen] == [("Bayrischzell", "hand"), ("Rathaus", "osm")]


def test_starts_je_gebiet_fasst_nahe_starts_zusammen():
    gebiete = [{"slug": "a", "lat": 47.0, "lon": 12.0, "loipen": [{"lat": 47.1, "lon": 12.1}, {"lat": 47.1003, "lon": 12.1},
                                                                  {"lat": None, "lon": None}]},
               {"slug": "b", "lat": 47.5, "lon": 12.5, "loipen": []}, {"slug": "c", "lat": None, "lon": None, "loipen": []}]
    assert oa.starts_je_gebiet(gebiete) == {"a": [(47.1, 12.1)], "b": [(47.5, 12.5)]}


@pytest.mark.req("D22")
def test_d22_parkplatz_als_flaeche_und_punkt_zaehlt_einmal_und_ids_werden_links():
    from loipen.osmauszug import ohne_doppelte_parkplaetze, pois_aus_geojson

    p = [{"lat": 47.671048, "lon": 12.015101, "fuss_min": 1}, {"lat": 47.671083, "lon": 12.015064, "fuss_min": 1},
         {"lat": 47.6871, "lon": 11.959522, "fuss_min": 2}]
    assert len(ohne_doppelte_parkplaetze(p)) == 2
    zeile = '{"type":"Feature","id":"w42","geometry":{"type":"Point","coordinates":[12.0,47.6]},"properties":{"amenity":"parking"}}'
    assert pois_aus_geojson(zeile)[0]["url"] == "https://www.openstreetmap.org/way/42"
