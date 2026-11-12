"""Adapter D: Landesportal tirol.at. P14, P18, U30 (Adapterseite), Schnappschuss 12.11.2026."""

import copy

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.normalisierung import normiere_zustand
from loipen.adapters.tirolat import TirolAtAdapter, laenge_km, marker, parse_detail, slug
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher

QUELLEN = lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"]
GEBIETE = lade_yaml(CONFIG_DIR / "gebiete.yaml")["gebiete"]
Q = next(q for q in QUELLEN if q["key"] == "tirol")
KUFSTEINERLAND = {"kufstein", "thiersee", "langkampfen", "bad-haering", "schwoich", "ebbs", "niederndorf"}


def konfig(**aenderung) -> dict:
    cfg = copy.deepcopy(Q["config"])
    cfg.update(aenderung)
    cfg["gebiet_punkte"] = {g["slug"]: [g["lat"], g["lon"]] for g in GEBIETE
                            if g["slug"] in cfg["gebiete"] and g.get("lat") is not None}
    return cfg


def fetcher(ersetze=None) -> FixtureFetcher:
    return FixtureFetcher("tirol", Q["base_url"], seiten=SEITEN_QUELLEN["tirol"], ersetze=ersetze)


def lauf(uhr=0.0, **aenderung):
    f = fetcher()
    return TirolAtAdapter(uhr=lambda: uhr).run(Q["base_url"], konfig(**aenderung), f), f


@pytest.mark.req("P14", ak=1)
def test_p14_kufsteinerland_aus_echtem_schnappschuss():
    assert isinstance(ADAPTERS["tirolat"], TirolAtAdapter)
    erg, _ = lauf(details_pro_lauf=100)
    ku = {l.name: l for l in erg.loipen if l.gebiet_slug in KUFSTEINERLAND and l.laenge_km}
    # Detailseiten im Schnappschuss: KU1-KU7, HT1, SC1, EB1 -> mindestens 5 mit Name, Status und Laenge
    assert len(ku) >= 5
    l = ku["KU1 Weissach I"]
    assert (l.gebiet_slug, l.status, l.laenge_km) == ("kufstein", Status.GESCHLOSSEN, 2.5)
    assert l.schwierigkeit == Schwierigkeit.LEICHT and l.technik == Technik.BEIDES
    assert l.nachtloipe is True and l.rundkurs is True
    assert l.startpunkt == "Locherer Weg/ Hochwachtstraße"
    assert (l.lat, l.lon) == (47.57693, 12.16971)
    assert l.source_key == "addressbase_20460"
    assert l.source_url == "https://www.tirol.at/aktivitaeten/sport/langlaufen/loipen/ku1-weissach-i"
    assert ku["KU6 Morsbach I"].laenge_km == 0.7  # tirol.at schreibt "700 m"
    assert ku["EB1 Dorf-Loipe"].schwierigkeit == Schwierigkeit.MITTEL and ku["EB1 Dorf-Loipe"].gebiet_slug == "ebbs"
    assert ku["HT1 Übungs-Loipe"].technik == Technik.KLASSISCH


@pytest.mark.req("P14", ak=1)
def test_p14_stufe1_nur_kufsteinerland_kaiserwinkl_wilder_kaiser():
    erg, f = lauf(details_pro_lauf=0)
    assert len(f.abgerufen) == 2  # Liste und Filter "geoeffnet", keine Detailseite
    gebiete = {l.gebiet_slug for l in erg.loipen}
    assert gebiete <= set(Q["config"]["gebiete"])
    assert len(erg.loipen) == 61
    namen = {l.name for l in erg.loipen}
    # Skischulen und Verleih aus der Kartenliste sind keine Loipen
    assert not any("schule" in n.lower() or "Rental" in n for n in namen)
    # Bayrischzeller Loipen (in der tirol.at-Liste) und Hohe Salve liegen ausserhalb der Gebiete
    assert "Streinalm-Runde" not in namen and "Loipe Mariastein" not in namen
    assert {"Kaiserwinklloipe Schwendt", "Dorfloipe Ellmau", "VT1 See-Loipe"} <= namen


@pytest.mark.req("P14", ak=2)
@pytest.mark.req("P13", ak=1)
def test_p14_neue_region_nur_ueber_konfiguration():
    """Ein weiteres Tiroler Gebiet: nur Eintrag in gebiete und Koordinate, kein Code."""
    cfg = konfig(details_pro_lauf=0)
    cfg["gebiete"] = cfg["gebiete"] + ["seefeld"]
    cfg["gebiet_punkte"]["seefeld"] = [47.33, 11.19]
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], cfg, fetcher())
    seefeld = [l for l in erg.loipen if l.gebiet_slug == "seefeld"]
    assert len(seefeld) >= 5
    assert any("IBU" in l.name for l in seefeld)


def test_p14_ein_gebiet_ohne_koordinate_meldet_warnung():
    cfg = konfig(details_pro_lauf=0)
    cfg["gebiete"] = cfg["gebiete"] + ["irgendwo"]
    erg = TirolAtAdapter().run(Q["base_url"], cfg, fetcher())
    assert "Gebiet irgendwo ohne Koordinate in gebiete.yaml, nicht zugeordnet" in erg.warnungen


@pytest.mark.req("U30", ak=1)
@pytest.mark.req("P14", ak=1)
def test_status_aus_filter_geoeffnet_und_ohne_datum():
    """tirol.at kennt nur geoeffnet/gesperrt und kein Praeparierdatum."""
    seite = fetcher().seite("2026-11-12/loipen_offen.html")
    alle = marker(fetcher().seite("2026-11-12/loipen.html"))
    offen = marker(seite)
    assert len(alle) == 711 and len(offen) == 11
    # Eine Kufsteiner Loipe als geoeffnet melden: dann steht sie auf "offen"
    ku1 = next(m for m in alle if m["title"] == "KU1 Weissach I")
    neu = seite.replace('data-markers="[', 'data-markers="[' + _marker_html(ku1) + ",", 1)
    f = fetcher({"aktivitaeten/sport/langlaufen/loipen?addressbaseOpened%5B209%5D%5B%5D=OPEN": neu})
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=0), f)
    l = next(l for l in erg.loipen if l.name == "KU1 Weissach I")
    assert l.status == Status.OFFEN and l.status_rohtext == "tirol.at: geöffnet"
    andere = next(l for l in erg.loipen if l.name == "KU2 Weissach II")
    assert andere.status == Status.GESCHLOSSEN and andere.status_rohtext == "tirol.at: nicht als geöffnet gemeldet"
    assert all(l.quelle_aktualisiert_at is None for l in erg.loipen)


def _marker_html(m: dict) -> str:
    import html
    import json
    return html.escape(json.dumps(m, ensure_ascii=False), quote=True)


def test_detailseiten_im_wechsel():
    """Je Lauf hoechstens details_pro_lauf Detailseiten, ueber die Laeufe alle (Blindspot 5)."""
    gesehen = set()
    for stunde in range(4):
        _, f = lauf(uhr=stunde * 3600.0, details_pro_lauf=20)
        details = [u for u in f.abgerufen if u.rsplit("/", 1)[-1] != "loipen" and "?" not in u]
        assert len(details) <= 20
        gesehen |= set(details)
    assert len(gesehen) == 61


def test_fehlende_detailseite_stoppt_den_lauf_nicht():
    erg, _ = lauf(details_pro_lauf=100)
    assert len(erg.loipen) == 61
    assert any("TS1 Mitterland Loipe: Detailseite nicht lesbar" in w for w in erg.warnungen)


def test_falsche_detailseite_wird_erkannt():
    """Gleiche Namen bekommen bei tirol.at -2, -3: die Kennung auf der Seite muss passen."""
    andere = fetcher().seite("2026-11-12/ku2-weissach-ii.html")
    f = fetcher({"aktivitaeten/sport/langlaufen/loipen/ku1-weissach-i": andere})
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=100), f)
    l = next(l for l in erg.loipen if l.name == "KU1 Weissach I")
    assert l.laenge_km is None
    assert any("KU1 Weissach I: Detailseite" in w and "config.slugs" in w for w in erg.warnungen)


def test_pfade_aus_listeneintraegen_und_slug():
    assert slug("KU1 Weissach I") == "ku1-weissach-i"
    assert slug("1,5 km IBU-Rennstrecke") == "15-km-ibu-rennstrecke"
    assert slug("1 Nordloipe  - Längenfeld") == "1-nordloipe-laengenfeld"
    assert slug("Rundloipe Gaichtpaß") == "rundloipe-gaichtpass"
    assert laenge_km("700 m") == 0.7 and laenge_km(" 27,0 km ") == 27.0


def test_detailseite_felder():
    d = parse_detail(fetcher().seite("2026-11-12/kaiserwinklloipe-schwendt.html"))
    assert d["status"] == "gesperrt" and d["verband"] == "TVB Kaiserwinkl"
    assert d["schwierigkeit"] == "schwierig" and d["laenge_km"] == 27.0
    assert d["stile"] == "skating / klassisch" and d["kennung"] == "23506"
    assert "Loipengütesiegel" in d["merkmale"]


@pytest.mark.req("P18", ak=1)
@pytest.mark.parametrize("wort, status", [
    ("gesperrt", Status.GESCHLOSSEN), ("Geöffnet", Status.OFFEN), ("teilweise geöffnet", Status.EINGESCHRAENKT),
    ("eingeschränkt befahrbar", Status.EINGESCHRAENKT), ("nur eingeschränkt befahrbar", Status.EINGESCHRAENKT),
    ("in Betrieb", Status.OFFEN),
])
def test_p18_oesterreichische_zustandswoerter(wort, status):
    assert normiere_zustand(wort) == (status, True)


@pytest.mark.req("P18", ak=1)
def test_p18_unbekanntes_wort_landet_in_der_quellenmeldung():
    seite = fetcher().seite("2026-11-12/ku1-weissach-i.html").replace(
        "data-openinghours-text>gesperrt<", "data-openinghours-text>Spur in Arbeit<")
    f = fetcher({"aktivitaeten/sport/langlaufen/loipen/ku1-weissach-i": seite})
    erg = TirolAtAdapter(uhr=lambda: 0).run(Q["base_url"], konfig(details_pro_lauf=100), f)
    l = next(l for l in erg.loipen if l.name == "KU1 Weissach I")
    assert ("status", "Spur in Arbeit") in l.unbekannte_begriffe


@pytest.mark.req("P12", ak=2)
@pytest.mark.parametrize("wort, status", [
    ("aperta", Status.OFFEN), ("chiusa", Status.GESCHLOSSEN), ("parzialmente aperta", Status.EINGESCHRAENKT),
])
def test_p12_italienische_zustandswoerter(wort, status):
    assert normiere_zustand(wort) == (status, True)
