"""Adapter A fuer das Tourismus-System von Tegernsee, Bayrischzell und Fischbachau.

Tests gegen gespeicherte Seiten (tests/fixtures, Stand 09.11.2026): P1, P3, P5, P6, P9.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.ats import AtsAdapter, lese_liste, lese_statusseite, namen_schluessel
from loipen.konfig import lade_yaml, CONFIG_DIR
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import FixtureFetcher

QUELLEN = {q["key"]: q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"]}
BERLIN = ZoneInfo("Europe/Berlin")


def lauf(key, ersetze=None):
    q = QUELLEN[key]
    fetcher = FixtureFetcher(key, q["base_url"], ersetze)
    return AtsAdapter().run(q["base_url"], q["config"], fetcher), fetcher


@pytest.fixture(scope="module")
def ergebnisse():
    return {key: lauf(key)[0] for key in ("tegernsee", "bayrischzell", "fischbachau")}


def nach_key(ergebnis):
    return {l.source_key: l for l in ergebnis.loipen}


@pytest.mark.req("P1", ak=1)
def test_p1_ein_adapter_fuer_drei_orte(ergebnisse):
    assert {QUELLEN[k]["adapter"] for k in ergebnisse} == {"ats"}
    assert isinstance(ADAPTERS["ats"], AtsAdapter)
    assert len(ergebnisse["tegernsee"].loipen) == 26
    assert len(ergebnisse["bayrischzell"].loipen) == 9
    assert len(ergebnisse["fischbachau"].loipen) == 7
    assert all(e.warnungen == [] for e in ergebnisse.values())


@pytest.mark.req("P1", ak=2)
def test_p1_weiterer_ort_nur_per_konfiguration():
    """Ein weiterer Eintrag mit demselben System: andere URL, derselbe Code."""
    neu = {"default_gebiet": "bayrischzell", "statusseiten": QUELLEN["bayrischzell"]["config"]["statusseiten"]}
    fetcher = FixtureFetcher("bayrischzell", "https://www.schliersee.example")
    ergebnis = AtsAdapter().run("https://www.schliersee.example", neu, fetcher)
    assert len(ergebnis.loipen) == 9
    assert {l.gebiet_slug for l in ergebnis.loipen} == {"bayrischzell"}
    assert any(a.startswith("https://www.schliersee.example/langlaufen") for a in fetcher.abgerufen)


@pytest.mark.req("P3", ak=1)
def test_p3_loipen_aus_der_langlaufen_seite_mit_blaettern():
    q = QUELLEN["tegernsee"]
    fetcher = FixtureFetcher("tegernsee", q["base_url"])
    ergebnis = AtsAdapter().run(q["base_url"], {**q["config"], "statusseiten": []}, fetcher)
    assert len(ergebnis.loipen) == 19  # 10 auf Seite 0, 9 auf Seite 1
    assert "https://www.tegernsee.com/langlaufen/1" in fetcher.abgerufen
    assert {l.status for l in ergebnis.loipen} == {Status.UNBEKANNT}  # ohne Schneebericht kein Status


@pytest.mark.req("P3", ak=1)
def test_p3_blaettern_endet_und_laeuft_nicht_im_kreis():
    q = QUELLEN["tegernsee"]
    fetcher = FixtureFetcher("tegernsee", q["base_url"])
    AtsAdapter().run(q["base_url"], {**q["config"], "statusseiten": []}, fetcher)
    listen = [u for u in fetcher.abgerufen if "/langlaufen" in u]
    assert len(listen) == len(set(listen)) == 2


@pytest.mark.req("P3", ak=2)
def test_p3_geaenderte_adresse_wird_ohne_codeaenderung_gefunden():
    """Die Quelle benennt /a-golfplatzrunde in /a-golfplatzrunde-87-km um: die Loipe bleibt auffindbar."""
    q = QUELLEN["tegernsee"]
    fetcher = FixtureFetcher("tegernsee", q["base_url"])
    liste = fetcher.seite("langlaufen_1.html").replace("a-golfplatzrunde", "a-golfplatzrunde-87-km")
    ergebnis, _ = lauf("tegernsee", {"langlaufen/1": liste})
    loipen = nach_key(ergebnis)
    assert "a-golfplatzrunde-87-km" in loipen and "a-golfplatzrunde" not in loipen
    golf = loipen["a-golfplatzrunde-87-km"]
    assert golf.name == "Golfplatzrunde" and golf.laenge_km == 8.7
    assert golf.status == Status.GESCHLOSSEN  # der Schneebericht wird weiter zugeordnet


@pytest.mark.req("P3")
def test_p3_nicht_loipen_werden_ignoriert(ergebnisse):
    """Kegelbahn, Minigolf, Lama-Wanderung, Eislaufplatz stehen im Menue, nicht in der Loipenliste."""
    alle = " ".join(l.source_key for e in ergebnisse.values() for l in e.loipen)
    for fremd in ("kegelbahn", "minigolf", "lama", "eislaufplatz", "tischtennis", "padel", "tennisclub", "jod-schwefelbad"):
        assert fremd not in alle


@pytest.mark.req("P3")
def test_p3_fehlende_schneebericht_seite_ist_eine_warnung_kein_abbruch():
    q = QUELLEN["bayrischzell"]
    seiten = q["config"]["statusseiten"]
    config = {**q["config"], "statusseiten": [*seiten, "a-gibt-es-nicht"]}
    fetcher = FixtureFetcher("bayrischzell", q["base_url"])
    ergebnis = AtsAdapter().run(q["base_url"], config, fetcher)
    assert len(ergebnis.loipen) == 9
    assert any("a-gibt-es-nicht" in w and "404" in w for w in ergebnis.warnungen)


@pytest.mark.req("P9", ak=1)
def test_p9_stammdaten_aus_der_liste(ergebnisse):
    ring = nach_key(ergebnisse["tegernsee"])["a-ringseeloipe"]
    assert (ring.name, ring.laenge_km, ring.schwierigkeit, ring.rundkurs) == ("Ringseeloipe", 4.2, Schwierigkeit.MITTEL, True)
    assert ring.startpunkt == "Kreuth-Oberhof" and ring.gebiet_slug == "kreuth"
    assert (ring.lat, ring.lon) == (47.68, 11.7581)
    assert ring.technik == Technik.BEIDES
    verbindung = nach_key(ergebnisse["tegernsee"])["a-verbindungsloipe-bad-wiessee"]
    assert verbindung.rundkurs is False  # "von A nach B"


@pytest.mark.req("P9", ak=1)
def test_p9_schneebericht_felder(ergebnisse):
    ring = nach_key(ergebnisse["tegernsee"])["a-ringseeloipe"]
    assert ring.status == Status.GESCHLOSSEN
    assert ring.status_rohtext == "Loipenzustand: nicht befahrbar"
    assert (ring.gespurt_gesamt_km, ring.gespurt_klassisch_km, ring.gespurt_skating_km) == (8.4, 8.4, 8.4)
    assert ring.quelle_aktualisiert_at == datetime(2026, 3, 15, 8, 47, tzinfo=BERLIN)
    assert ring.nachtloipe is False
    assert "Loipenzustand: nicht befahrbar" in ring.rohtext and "15.03.26" in ring.rohtext


@pytest.mark.req("P9", ak=1)
def test_p9_eigenheit_titel_4_2_km_aber_8_4_km_gespurt(ergebnisse):
    """Die Quelle nennt 4,2 km im Titel und 8,4 km gespurt: beide Werte bleiben getrennt erhalten."""
    ring = nach_key(ergebnisse["tegernsee"])["a-ringseeloipe"]
    assert ring.laenge_km == 4.2 and ring.gespurt_gesamt_km == 8.4


@pytest.mark.req("P9", ak=1)
def test_p9_nachtloipe_und_technik(ergebnisse):
    nacht = nach_key(ergebnisse["tegernsee"])["a-nachtloipe-brunnbichl"]
    assert nacht.nachtloipe is True and nacht.technik == Technik.BEIDES
    skating = nach_key(ergebnisse["tegernsee"])["a-skatingloipe-klamm-bayerwald-26-km"]
    assert skating.technik == Technik.SKATING and skating.laenge_km == 2.6
    assert skating.quelle_aktualisiert_at == datetime(2026, 5, 27, 17, 13, tzinfo=BERLIN)  # Sommerzeit


@pytest.mark.req("P9", ak=1)
def test_p9_gleichnamige_titel_werden_richtig_zugeordnet(ergebnisse):
    """Drei Seiten heissen 'Klamm - Bayerwald', eine 'Sportplatzrunde': Laenge und Technik entscheiden."""
    t = nach_key(ergebnisse["tegernsee"])
    assert t["a-skatingloipe-klamm-bayerwald-09-km"].gespurt_gesamt_km == 1.0  # Seite rundet 0,9 km auf 1,0 km
    assert t["a-skatingloipe-klamm-bayerwald-26-km"].gespurt_gesamt_km == 2.6
    assert t["a-loipe-klamm-bayerwald-glashuette"].laenge_km == 10.9
    assert t["a-sportplatzrunde-bad-wiessee"].laenge_km == 3.5
    assert t["a-sportplatzrunde-17-km-schneebericht"].laenge_km == 1.7  # kleine Runde, nur im Schneebericht


@pytest.mark.req("P9", ak=1)
def test_p9_gebiete_aus_startpunkt_und_adresse(ergebnisse):
    t = nach_key(ergebnisse["tegernsee"])
    assert t["a-suttenrunde"].gebiet_slug == "rottach-egern"
    assert t["a-golfplatzrunde"].gebiet_slug == "bad-wiessee"
    assert t["a-loipe-wildbad-kreuth-klamm"].gebiet_slug == "kreuth"
    assert t["a-gasslerrunde-1"].gebiet_slug == "gmund"  # nur im Schneebericht, Ort aus der Adresse
    assert {l.gebiet_slug for l in ergebnisse["bayrischzell"].loipen} == {"bayrischzell"}


@pytest.mark.req("P9", ak=1)
def test_p9_bayrischzell_und_fischbachau(ergebnisse):
    b = nach_key(ergebnisse["bayrischzell"])
    assert b["a-kloo-ascher-runde"].laenge_km == 9.0
    assert b["a-kloo-ascher-runde"].status == Status.GESCHLOSSEN  # Schneebericht "Kloo-Ascher Runde" gefunden
    assert b["a-kloo-ascher-runde"].quelle_aktualisiert_at == datetime(2026, 4, 2, 9, 4, tzinfo=BERLIN)
    f = nach_key(ergebnisse["fischbachau"])
    assert f["a-point-hundham"].laenge_km == 17.5 and f["a-point-hundham"].schwierigkeit == Schwierigkeit.SCHWER
    assert (f["a-point-hundham"].lat, f["a-point-hundham"].lon) == (47.723935, 11.948608)  # aus der Kartenliste
    assert f["a-kleine-runde-hundham"].status == Status.UNBEKANNT  # kein Schneebericht bekannt


@pytest.mark.req("P9", ak=1)
def test_p9_abgeleitete_saisonseite_offen_und_bedingt():
    """Kopie einer echten Seite mit geaendertem Zustand: so sieht eine offene Loipe wahrscheinlich aus.

    ACHTUNG: abgeleitet, nicht echt. Im Dezember durch echte Seiten ersetzen (siehe Testkonzept).
    """
    q = QUELLEN["tegernsee"]
    seite = FixtureFetcher("tegernsee", q["base_url"]).seite(
        "schneebericht/a-ringseeloipe-42-km-skating-u-klassisch.html"
    )
    offen = seite.replace("<strong>nicht befahrbar</strong>", "<strong>geöffnet</strong>").replace(
        "15.03.26 um 08:47", "20.12.26 um 06:30"
    )
    bedingt = seite.replace("<strong>nicht befahrbar</strong>", "<strong>bedingt befahrbar</strong>")
    unsinn = seite.replace("<strong>nicht befahrbar</strong>", "<strong>Pulverschnee deluxe</strong>")
    for html, status in ((offen, Status.OFFEN), (bedingt, Status.EINGESCHRAENKT), (unsinn, Status.UNBEKANNT)):
        ergebnis, _ = lauf("tegernsee", {"a-ringseeloipe-42-km-skating-u-klassisch": html})
        ring = nach_key(ergebnis)["a-ringseeloipe"]
        assert ring.status == status
    assert nach_key(lauf("tegernsee", {"a-ringseeloipe-42-km-skating-u-klassisch": offen})[0])[
        "a-ringseeloipe"
    ].quelle_aktualisiert_at == datetime(2026, 12, 20, 6, 30, tzinfo=BERLIN)
    ring = nach_key(lauf("tegernsee", {"a-ringseeloipe-42-km-skating-u-klassisch": unsinn})[0])["a-ringseeloipe"]
    assert ring.unbekannte_begriffe == [("zustand", "Loipenzustand: Pulverschnee deluxe")]


@pytest.mark.req("P9")
def test_p9_namensschluessel():
    orte = frozenset({"bayrischzell"})
    assert namen_schluessel("Ringseeloipe (4,2 km Skating u. klassisch)") == namen_schluessel("Ringseeloipe")
    assert namen_schluessel("Nessler-Runde Bayrischzell", orte) == namen_schluessel("Nessler Runde", orte)
    assert namen_schluessel("Klamm - Bayerwald (0,9 km Skating)") == namen_schluessel("Skatingloipe Klamm - Bayerwald 0,9 km")


@pytest.mark.req("P9")
def test_p9_seite_ohne_loipenzustand_wird_nicht_als_loipe_gelesen():
    q = QUELLEN["tegernsee"]
    kegel = FixtureFetcher("bayrischzell", "https://www.bayrischzell.de").seite("loipen/a-kegelbahn.html")
    assert lese_statusseite(kegel) is None
    assert lese_liste(kegel, "https://www.bayrischzell.de") == ([], [])
