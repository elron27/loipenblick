"""Allgaeu ueber die Seiten der Gemeinden und Tourismusaemter (P38, E-27, nur Test).

Schnappschuesse vom 20.11.2026 (Workflow Schnappschuss, Runden 23 bis 26, Recherche unter
tests/fixtures/recherche-2026-11-20/). Am 20.11. war im ganzen Allgaeu alles geschlossen; nur das
Nordic Zentrum Oberstdorf meldete die Schnee-Depot-Loipe als teilweise befahrbar.
Nicht angebunden (Befund in docs/kontaktliste.md Abschnitt 4): loipen-allgaeu.de (robots-Sperre,
Sammeldienst), Bad Hindelang, allgaeu.de, Scheidegg (Status nur ueber ein Browser-Widget mit Schluessel),
Oberstaufen, Nesselwang (kein Status).
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.allgaeu_orte import FuessenAdapter, IntermapsListeAdapter, KleinwalsertalAdapter, TraminoBoxAdapter
from loipen.adapters.eopoi import EoPoiAdapter
from loipen.adapters.normalisierung import BERLIN
from loipen import osm
from loipen.adapters.tramino_wsb import TraminoWsbAdapter
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import FixtureFetcher
from tests.test_lokale_quellen import quelle

STAND = "2026-11-20"
ALLGAEU = ("oberstdorf", "wertach", "pfronten", "kleinwalsertal", "fuessen", "isny", "hoernerdoerfer")
NEUE_GEBIETE = {"oberstdorf", "hoernerdoerfer", "balderschwang", "wertach", "pfronten", "fuessen", "isny",
                "kleinwalsertal"}
FIX = Path(__file__).resolve().parent / "fixtures"


def lauf(key: str, adapter, ersetze: dict | None = None):
    q = quelle(key)
    return adapter.run(q["base_url"], q["config"], FixtureFetcher(key, q["base_url"], stand=STAND, ersetze=ersetze))


def leer(key: str, adapter, html: str):
    q = quelle(key)
    return lauf(key, adapter, ersetze={q["config"]["pfad"].strip("/"): html})


@pytest.mark.req("P38", ak=1)
def test_p38_oberstdorf_wintersportbericht():
    r = lauf("oberstdorf", TraminoWsbAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 14
    nordic = r.loipen[0]
    assert (nordic.name, nordic.status, nordic.laenge_km) == ("Nordic Zentrum (C)", Status.EINGESCHRAENKT, 10.0)
    assert "Schnee-Depot-Loipe ist präpariert" in nordic.rohtext
    assert nordic.source_url == "https://www.oberstdorf.de/winter/langlaufen/wm-loipen.html"
    assert {l.status for l in r.loipen[1:]} == {Status.GESCHLOSSEN}
    spiel = next(l for l in r.loipen if l.name == "Spielmannsau (D)")
    assert spiel.laenge_km == 13.0 and spiel.source_key == "spielmannsau-d"
    assert {l.quelle_aktualisiert_at for l in r.loipen} == {datetime(2026, 11, 10, 8, 30, tzinfo=BERLIN)}
    assert next(l for l in r.loipen if l.name == "Nachtloipe Nordic Zentrum").nachtloipe is True
    assert {l.gebiet_slug for l in r.loipen} == {"oberstdorf"}
    assert all(not l.unbekannte_begriffe for l in r.loipen)


@pytest.mark.req("P38", ak=1)
def test_p38_wertach_laenge_technik_schwierigkeit_aus_dem_hinweis():
    r = lauf("wertach", TraminoWsbAdapter())
    assert r.warnungen == []
    assert [l.name for l in r.loipen] == ["Rund- und Nachtloipe Klassisch und Skating", "Kolpingloipe",
                                          "Grüntenseeloipe"]
    rund, kolping, gruenten = r.loipen
    assert (rund.laenge_km, rund.technik, rund.schwierigkeit, rund.nachtloipe) == (
        1.9, Technik.BEIDES, Schwierigkeit.LEICHT, True)
    assert (kolping.laenge_km, kolping.schwierigkeit) == (5.8, Schwierigkeit.MITTEL)
    assert gruenten.laenge_km == 15.0
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    assert {l.quelle_aktualisiert_at for l in r.loipen} == {datetime(2026, 4, 2, tzinfo=BERLIN)}


@pytest.mark.req("P38", ak=1)
def test_p38_isny_kaesten_mit_laenge_in_metern():
    r = lauf("isny", TraminoBoxAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 12
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    gschwend = next(l for l in r.loipen if l.name == "Gschwendloipe")
    assert (gschwend.laenge_km, gschwend.technik, gschwend.schwierigkeit) == (5.4, Technik.BEIDES, Schwierigkeit.MITTEL)
    assert "am 3.2. frisch gespurt" in gschwend.rohtext
    stadion = next(l for l in r.loipen if l.name == "Langlaufstadion")
    assert stadion.schwierigkeit == Schwierigkeit.LEICHT  # "einfach"
    assert next(l for l in r.loipen if l.name == "Schweineburgloipe").schwierigkeit == Schwierigkeit.SCHWER
    assert {l.gebiet_slug for l in r.loipen} == {"isny"}
    assert all(l.quelle_aktualisiert_at is None for l in r.loipen)  # "Zuletzt gespurt" ist im November leer


@pytest.mark.req("P38", ak=2)
def test_p38_pfronten_eo_poi_daten_aus_dem_html():
    r = lauf("pfronten", EoPoiAdapter())
    assert r.warnungen == []
    namen = [l.name for l in r.loipen]
    assert len(namen) == 10 and "Rundloipe Weißbach" in namen
    assert not any("Winterwander" in n or "Rodel" in n or "Skizentrum" == n for n in namen)
    weiss = next(l for l in r.loipen if l.name == "Rundloipe Weißbach")
    assert weiss.status == Status.GESCHLOSSEN
    assert (weiss.laenge_km, weiss.technik, weiss.schwierigkeit) == (1.3, Technik.BEIDES, Schwierigkeit.LEICHT)
    assert weiss.quelle_aktualisiert_at == datetime(2026, 2, 20, tzinfo=BERLIN)  # zuletzt praepariert
    assert (weiss.lat, weiss.lon) == (47.591014, 10.54607)
    assert weiss.startpunkt == "Wanderparkplatz Röfleuten"
    assert weiss.source_url == ("https://www.pfronten.de/aktiv/winterurlaub-im-allgaeu/wintersportbericht/"
                                "detail-winter/rundloipe-weissbach/")
    fallmuehle = next(l for l in r.loipen if l.name == "Talloipe zur Fallmühle")
    assert fallmuehle.quelle_aktualisiert_at is None and fallmuehle.schwierigkeit == Schwierigkeit.UNBEKANNT
    assert {l.gebiet_slug for l in r.loipen} == {"pfronten"}


@pytest.mark.req("P38", ak=3)
def test_p38_kleinwalsertal_status_und_technik():
    r = lauf("kleinwalsertal", KleinwalsertalAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 19
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    egg = next(l for l in r.loipen if l.name == "Schwarzwasserloipe: Egg-Runde [kl]")
    assert (egg.technik, egg.startpunkt, egg.source_key) == (Technik.KLASSISCH, "Schwarzwasserloipe", "kwt-7647")
    assert next(l for l in r.loipen if l.source_key == "kwt-7629").technik == Technik.BEIDES
    # gleiche Runde in zwei Techniken bleibt getrennt (eigene Nummer)
    assert len([l for l in r.loipen if l.name.startswith("Steinbockloipe: Weiher-Runde")]) == 2
    assert {l.gebiet_slug for l in r.loipen} == {"kleinwalsertal"}


@pytest.mark.req("P38", ak=3)
def test_p38_fuessen_loipengruppen():
    r = lauf("fuessen", FuessenAdapter())
    assert r.warnungen == []
    assert [(l.name, l.source_key, l.status) for l in r.loipen] == [
        ("Füssen-Loipe (F1)", "f1", Status.GESCHLOSSEN),
        ("Weißensee-Loipen (W1, W2)", "w1-w2", Status.GESCHLOSSEN),
        ("Hopfen-Loipen (H1, H2)", "h1-h2", Status.GESCHLOSSEN)]


@pytest.mark.req("P38", ak=3)
def test_p38_hoernerdoerfer_intermaps_liste_mit_orten():
    r = lauf("hoernerdoerfer", IntermapsListeAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 26
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    assert {l.startpunkt for l in r.loipen} == {"Balderschwang", "Obermaiselstein", "Fischen", "Bolsterlang",
                                                "Ofterschwang"}
    grenz = next(l for l in r.loipen if l.name == "Grenzland-Loipe nach Hittisau")
    assert (grenz.gebiet_slug, grenz.laenge_km, grenz.technik) == ("balderschwang", 41.0, Technik.BEIDES)
    assert next(l for l in r.loipen if l.name == "Sonnenalp-Loipe").gebiet_slug == "hoernerdoerfer"
    assert next(l for l in r.loipen if l.name == "Flutlichtloipe am Sportplatz").nachtloipe is True
    # dieselbe Loipe unter zwei Orten (Langenwanger Loipe) bekommt je Ort einen eigenen Schluessel
    assert len({l.source_key for l in r.loipen}) == 26
    assert {l.quelle_aktualisiert_at for l in r.loipen} == {datetime(2026, 11, 20, 8, 1, tzinfo=BERLIN)}


@pytest.mark.req("P38", ak=[1, 3])
def test_p38_unbekanntes_symbol_und_leere_seite():
    t = ('<h4>Loipen</h4><table><tr><th></th><th>Name</th></tr>'
         '<tr><td><img src="https://tramino.s3.amazonaws.com/gfx/wsb/neu.png"></td><td><a href="/x">Testloipe</a></td>'
         '<td class="lastcol">3 km</td></tr></table>')
    r = leer("oberstdorf", TraminoWsbAdapter(), t)
    assert r.loipen[0].status == Status.UNBEKANNT and r.loipen[0].unbekannte_begriffe == [("status", "neu")]
    for key, adapter in [("oberstdorf", TraminoWsbAdapter()), ("wertach", TraminoWsbAdapter()),
                         ("isny", TraminoBoxAdapter()), ("pfronten", EoPoiAdapter()),
                         ("kleinwalsertal", KleinwalsertalAdapter()), ("fuessen", FuessenAdapter()),
                         ("hoernerdoerfer", IntermapsListeAdapter())]:
        r = leer(key, adapter, "<html><body>Neu</body></html>")
        assert r.loipen == [] and "Seitenaufbau" in r.warnungen[0], key


@pytest.mark.req("P38", ak=4)
def test_p38_quellen_ortsseiten_nur_test():
    for key in ALLGAEU:
        q = quelle(key)
        assert q["adapter"] in ADAPTERS, key
        assert (q["art"], q["rang"], q["nutzung"]["erlaubnis"]) == ("ortsseite", 2, "nur_test"), key
        assert q["schliesst"] and not q.get("querpruefung"), key
        assert (FIX / key / STAND).is_dir(), key
    assert quelle("hoernerdoerfer")["nutzung"]["p17_ausnahme"]
    assert set(quelle("hoernerdoerfer")["schliesst"]) == {"hoernerdoerfer", "balderschwang"}
    alle = lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"]
    assert not any("loipen-allgaeu" in q["base_url"] for q in alle)


@pytest.mark.req("P38", ak=4)
def test_p38_neue_gebiete_mit_lage_region_und_wetterstation():
    y = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    g = {x["slug"]: x for x in y["gebiete"]}
    r = {x["slug"]: x for x in y["regionen"]}
    dwd = (FIX / "recherche-2026-11-20" / "dwd" / "RR_Tageswerte_Beschreibung_Stationen-allgaeu.txt").read_text(
        encoding="latin-1")
    aktiv = {z.split()[0] for z in dwd.splitlines()[2:] if z.strip() and z.split()[2] >= "20261101"}
    geo = json.loads((FIX / "geosphere" / "2026-11-12" / "klima-v2-1d_allgaeu.json").read_text())
    mit_schnee = {str(f["properties"]["station"]) for f in geo["features"]
                  if any(v is not None for v in f["properties"]["parameters"]["sh"]["data"])}
    for slug in NEUE_GEBIETE:
        x = g[slug]
        assert x["lat"] and x["lon"] and x["hoehe_m"] and x["tourist_url"].startswith("https://"), slug
        reg = r[x["region"]]
        assert reg["land"] in ("DE", "AT") and reg["bundesland"], slug
        st = x["wetterstation"]
        if reg["land"] == "AT":
            assert st["dienst"] == "geosphere" and st["id"] in mit_schnee, slug
        else:
            assert "dienst" not in st and st["id"] in aktiv, slug
    assert r[g["isny"]["region"]]["bundesland"] == "Baden-Württemberg"
    assert r[g["kleinwalsertal"]["region"]]["bundesland"] == "Vorarlberg"


@pytest.mark.req("P40", ak=1)
def test_p38_osm_strecken_fuer_isny_und_kleinwalsertal():
    """Der OSM-Abgleich vom 20.11.2026 kennt die Allgaeu-Regionen; Isny und Kleinwalsertal bekommen Strecken."""
    gebiete = {g["slug"]: g for g in lade_yaml(CONFIG_DIR / "gebiete.yaml")["gebiete"]}

    def treffer(key, adapter, region):
        daten = json.loads((FIX / "osm" / f"{region}.json").read_text(encoding="utf-8"))["loipen"]
        paare = {}
        for l in lauf(key, adapter).loipen:
            s = osm.strecke_fuer({"name": l.name, "lat": l.lat, "lon": l.lon, "laenge_km": l.laenge_km},
                                 gebiete[l.gebiet_slug], daten)
            if s:
                paare[l.name] = s["namen"][0]
        return paare

    isny = treffer("isny", TraminoBoxAdapter(), "wuerttembergisches-allgaeu")
    assert isny["Gschwendloipe"] == "Gschwendloipe" and isny["Lengersauloipe"] == "Lengersauloipe"
    assert len(isny) >= 4
    kwt = treffer("kleinwalsertal", KleinwalsertalAdapter(), "kleinwalsertal")
    assert kwt["Steinbockloipe: Ahorn-Runde [kl]"] == "Steinbock Loipe - Ahorn"
