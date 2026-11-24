"""Mehr Daten je Loipe: tourinfra-Zusatzfelder (P41), keine Personendaten (B33), Stammdaten mit Herkunft (D21).

Fixtures: Loipenmanager-Schnappschuesse aller tourinfra-Quellen (Chiemgau 09.11., die anderen 13.11.2026).
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from sqlalchemy import select

from loipen.ablauf import rufe_quelle_ab
from loipen.adapters.tourinfra import TourinfraAdapter
from loipen.details import MERKMALE, lade_stammdaten, merkmale_aus, uebernimm_stammdaten
from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml
from loipen.models import Loipe, Quelle, Status
from loipen.zustand import letzter_zustand
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher

BERLIN = ZoneInfo("Europe/Berlin")
QUELLEN = {q["key"]: q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["adapter"] == "tourinfra"}
JSON_PFAD = "inc/ajax.php?ajaxtype=getLoipenmanager"


def fetcher(key: str, ersetze=None) -> FixtureFetcher:
    return FixtureFetcher(key, QUELLEN[key]["base_url"], ersetze=ersetze, seiten=SEITEN_QUELLEN[key])


def lauf(key: str, daten=None):
    ersetze = {JSON_PFAD: json.dumps(daten)} if daten is not None else None
    q = QUELLEN[key]
    return TourinfraAdapter().run(q["base_url"], q["config"], fetcher(key, ersetze))


def loipe(key: str, tid: str, daten=None):
    return next(l for l in lauf(key, daten).loipen if l.source_key == tid)


def roh(key: str) -> list[dict]:
    f = fetcher(key)
    text = f.get(QUELLEN[key]["base_url"] + QUELLEN[key]["config"]["json_path"])
    d = json.loads(text)
    return [e for e in (d.values() if isinstance(d, dict) else d) if isinstance(e, dict)]


def test_alle_tourinfra_quellen_haben_einen_schnappschuss():
    assert set(QUELLEN) == {"chiemgau", "tannheimer", "seefeld-tourinfra", "engadin", "davos-klosters",
                            "goms", "gastein", "ramsau"}
    for key in QUELLEN:
        assert lauf(key).loipen, key


@pytest.mark.req("P41", ak=1)
def test_p41_datum_der_letzten_aenderung_wenn_kein_praeparierdatum():
    erg = lauf("davos-klosters")
    mit_stand = [l for l in erg.loipen if l.quelle_aktualisiert_at]
    assert len(mit_stand) == 5  # 31 von 36 Eintraegen haben datum "-"
    eintrag = next(e for e in roh("davos-klosters") if e.get("datum", "").startswith("13.11.2026 / 14:45"))
    l = next(l for l in erg.loipen if l.source_key == str(eintrag["tid"]))
    assert l.quelle_aktualisiert_at == datetime(2026, 11, 13, 14, 45, tzinfo=BERLIN)
    # Alle Engadiner Loipen haben jetzt einen Stand, vorher keine (praep_datum immer "---")
    assert all(l.quelle_aktualisiert_at for l in lauf("engadin").loipen)


@pytest.mark.req("P41", ak=1)
def test_p41_praeparierdatum_geht_vor():
    daten = roh("tannheimer")
    daten[0]["praep_datum"] = "24.11.2026 / 06:10"
    daten[0]["datum"] = "20.11.2026 / 18:00"
    l = loipe("tannheimer", str(daten[0]["tid"]), daten)
    assert l.quelle_aktualisiert_at == datetime(2026, 11, 24, 6, 10, tzinfo=BERLIN)
    daten[0]["praep_datum"], daten[0]["datum"] = "---", "-"
    assert loipe("tannheimer", str(daten[0]["tid"]), daten).quelle_aktualisiert_at is None


@pytest.mark.req("P41", ak=2)
def test_p41_hinweis_des_betreibers():
    hinweise = {l.name: l.hinweis for l in lauf("chiemgau").loipen if l.hinweis}
    assert hinweise["Inzell Dorfloipe"] == "teilweise Wasser auf der Loipe"
    assert hinweise["Hinterwössen Runde"] == "Einstieg Wanderparkplatz Taubensee"
    assert len(hinweise) == 15
    goms = [l.hinweis for l in lauf("goms").loipen if l.hinweis]
    assert "Schneemangel, kann nicht mehr präpariert werden" in goms
    daten = roh("engadin")
    test = next(e for e in daten if e.get("bzustandinfo") == "Testeintrag")
    assert loipe("engadin", str(test["tid"]), daten).hinweis is None  # Testeintrag zaehlt nicht


@pytest.mark.req("P41", ak=3)
def test_p41_sperrgrund_ausser_unbekannt():
    erg = lauf("chiemgau")
    l = next(l for l in erg.loipen if l.source_key == "45988")
    assert l.status == Status.GESCHLOSSEN and l.sperrgrund == "Saisonvorbereitung"
    gruende = {l.sperrgrund for l in erg.loipen}
    assert "Unbekannt" not in gruende and "Saisonende" in gruende
    daten = roh("chiemgau")
    e = next(e for e in daten if str(e.get("tid")) == "45988")
    e["status_text"] = e["status_klassisch_text"] = e["status_skating_text"] = "Geöffnet"
    assert loipe("chiemgau", "45988", daten).sperrgrund is None  # offen: kein Sperrgrund


@pytest.mark.req("P41", ak=4)
def test_p41_schneehoehe_berg_und_tal():
    daten = roh("davos-klosters")
    daten[0]["sht"], daten[0]["shh"] = "35", "60"
    l = loipe("davos-klosters", str(daten[0]["tid"]), daten)
    assert (l.schneehoehe_cm, l.schneehoehe_berg_cm) == (35, 60)
    # leer, None und 0 (Vorgabewert) sind unbekannt
    assert all(l.schneehoehe_cm is None and l.schneehoehe_berg_cm is None for l in lauf("engadin").loipen)


@pytest.mark.req("P41", ak=5)
def test_p41_hund_und_kunstschnee():
    davos = lauf("davos-klosters").loipen
    assert sum(1 for l in davos if l.hund_erlaubt) == 5
    assert sum(1 for l in davos if l.kunstschnee) == 4
    assert all(l.hund_erlaubt is False for l in lauf("goms").loipen)


@pytest.mark.req("P41", ak=6)
def test_p41_einstiege_und_loipengebiet():
    goms = lauf("goms").loipen
    mit = [l for l in goms if l.einstiege]
    assert len(mit) == 36
    e = mit[0].einstiege[0]
    assert e["ort"] and "lat" in e and "lon" in e
    l = next(l for l in lauf("chiemgau").loipen if l.source_key == "45988")
    assert l.loipengebiet == "Loipengebiet Winklmoosalm"


@pytest.mark.req("B33", ak=[1, 2])
def test_b33_redakt_nie_im_ergebnis():
    for key in QUELLEN:
        namen = {str(e.get("redakt") or "").strip() for e in roh(key)} - {"", "System"}
        for l in lauf(key).loipen:
            text = json.dumps(l.__dict__, default=str, ensure_ascii=False)
            assert "redakt" not in text, key
            for name in namen:
                assert name not in text, (key, name)


@pytest.mark.req("P41")
def test_p41_lauf_speichert_neue_felder(session):
    lade_und_abgleichen(session)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "chiemgau"))
    rufe_quelle_ab(session, quelle, fetcher("chiemgau"))
    l = session.scalar(select(Loipe).where(Loipe.quelle_id == quelle.id, Loipe.source_key == "45988"))
    assert l.loipengebiet == "Loipengebiet Winklmoosalm" and l.kunstschnee is False
    z = letzter_zustand(session, l)
    assert z.sperrgrund == "Saisonvorbereitung"
    inzell = session.scalar(select(Loipe).where(Loipe.quelle_id == quelle.id, Loipe.name == "Inzell Dorfloipe"))
    assert letzter_zustand(session, inzell).hinweis == "teilweise Wasser auf der Loipe"


@pytest.mark.req("D21", ak=2)
def test_d21_merkmale_aus_fester_liste():
    gefunden, unbekannt = merkmale_aus(["Einkehrmöglichkeit", "Kostenfrei", "Familientauglich", "Highlight Tour",
                                        "Höhenloipe (Großteil über 1000m)", "Mit Bergbahn/Lift erreichbar",
                                        "Schneesicher", "Panoramablick wie nie"])
    assert gefunden == ["einkehr", "kostenlos", "familientauglich", "hoehenloipe", "bergbahn", "schneesicher"]
    assert unbekannt == ["Panoramablick wie nie"]
    assert set(gefunden) <= set(MERKMALE)


@pytest.mark.req("D21", ak=[1, 3])
def test_d21_handangabe_geht_vor():
    l = Loipe(name="x", source_key="1", source_url="u")
    assert uebernimm_stammdaten(l, {"hoehenmeter": 120, "merkmale": ["einkehr", "quatsch"]}, "berechnet",
                                "https://dem", "2026-11-24") == ["hoehenmeter", "merkmale"]
    assert l.merkmale == ["einkehr"]
    assert l.herkunft["hoehenmeter"] == {"herkunft": "berechnet", "url": "https://dem", "geprueft_am": "2026-11-24"}
    uebernimm_stammdaten(l, {"hoehenmeter": 109}, "quelle", "https://q")
    assert l.hoehenmeter == 109  # Quelle vor berechnet
    uebernimm_stammdaten(l, {"hoehenmeter": 100}, "hand", "https://gemeinde")
    assert uebernimm_stammdaten(l, {"hoehenmeter": 109}, "quelle", "https://q") == []
    assert l.hoehenmeter == 100 and l.herkunft["hoehenmeter"]["herkunft"] == "hand"
    with pytest.raises(ValueError):
        uebernimm_stammdaten(l, {"hoehenmeter": 1}, "geraten")


@pytest.mark.req("D21", ak=4)
def test_d21_stammdaten_aus_yaml(session, tmp_path: Path):
    lade_und_abgleichen(session)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "chiemgau"))
    rufe_quelle_ab(session, quelle, fetcher("chiemgau"))
    (tmp_path / "test.yaml").write_text(yaml.safe_dump({"quellen": {"chiemgau": {"45988": {
        "hoehenmeter": 109, "dauer_min": 80, "merkmale": ["einkehr", "bergbahn"],
        "url": "https://module.tourinfra.com/chiemgau/details.php?id=45988", "geprueft_am": "2026-11-24"}}}}),
        encoding="utf-8")
    assert lade_stammdaten(session, tmp_path) == 1
    l = session.scalar(select(Loipe).where(Loipe.quelle_id == quelle.id, Loipe.source_key == "45988"))
    assert (l.hoehenmeter, l.dauer_min, l.merkmale) == (109, 80, ["einkehr", "bergbahn"])
    assert l.herkunft["dauer_min"]["herkunft"] == "quelle"
    assert lade_stammdaten(session, tmp_path / "fehlt") == 0


# --- P42: Detailseiten (Schnappschuss 24.11.2026) -------------------------------------------------------------

from loipen.adapters.tourinfra import parse_details  # noqa: E402

DETAILS = Path(__file__).parent / "fixtures" / "recherche-2026-11-24" / "tourinfra"


def detail(name: str, startort: str | None = None) -> dict:
    return parse_details((DETAILS / name).read_text(encoding="utf-8"), startort)


@pytest.mark.req("P42", ak=2)
def test_p42_fakten_der_detailseite():
    d = detail("chiemgau-details-45988.html", "Reit im Winkl                    ")
    assert (d["dauer_min"], d["hoehenmeter"], d["tiefster_punkt_m"], d["hoechster_punkt_m"]) == (80, 109, 1117, 1192)
    assert d["merkmale"] == ["einkehr", "kostenlos", "familientauglich", "hoehenloipe", "bergbahn", "schneesicher"]
    assert "unbekannte_merkmale" not in d  # Ortsname und "Highlight Tour" sind keine Merkmale
    assert d["webcams"][0] == {"name": "Reit im Winkl: Dürrnbachhornweg - Winklmoosalm",
                               "url": "https://www.webcams.travel/webcam/1431329412"}
    assert len(d["webcams"]) == 4
    t = detail("tannheimer-details-155767.html")
    assert (t["dauer_min"], t["hoehenmeter"]) == (270, 430) and "webcams" not in t and "merkmale" not in t


@pytest.mark.req("P42", ak=2)
def test_p42_dauer_null_ist_keine_angabe_und_keine_beschreibung():
    d = detail("engadin-details-210056.html")
    assert "dauer_min" not in d and d["hoehenmeter"] == 88
    for name in DETAILS.glob("*details*.html"):
        werte = json.dumps(parse_details(name.read_text(encoding="utf-8")), ensure_ascii=False)
        assert "Beschreibung" not in werte and "Winklmoos-Alm führt" not in werte  # E-40: kein Fliesstext


@pytest.mark.req("P42", ak=[1, 3, 4])
def test_p42_skript_haelt_abstand_und_holt_nur_neue(monkeypatch, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("tourinfra_details",
                                                  Path(__file__).parent.parent / "scripts" / "tourinfra_details.py")
    skript = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skript)
    monkeypatch.setattr(skript, "ZIEL", tmp_path / "tourinfra.yaml")
    abrufe: list[str] = []
    seite = (DETAILS / "tannheimer-details-155767.html").read_text(encoding="utf-8")
    liste = (Path(__file__).parent / "fixtures" / "tannheimer" / "2026-11-13" / "loipenmanager.json").read_text()

    class Fetcher:
        def __init__(self, ua, delay_s):
            assert delay_s >= 5  # AK 1
        def get(self, url):
            abrufe.append(url)
            return liste if "ajax.php" in url else seite
        def close(self):
            pass

    monkeypatch.setattr(skript, "HoeflicherFetcher", Fetcher)
    monkeypatch.setattr(sys, "argv", ["x", "--quelle", "tannheimer"])
    assert skript.main() == 0
    daten = yaml.safe_load((tmp_path / "tourinfra.yaml").read_text(encoding="utf-8"))
    assert daten["herkunft"] == "quelle"
    eintrag = daten["quellen"]["tannheimer"]["155767"]
    assert eintrag["hoehenmeter"] == 430 and eintrag["url"].endswith("details.php?id=155767")  # AK 3
    assert eintrag["geprueft_am"]
    erste = len(abrufe)
    assert erste == 1 + 21
    assert skript.main() == 0
    assert len(abrufe) == erste + 1  # AK 4: nur der Loipenmanager, keine Detailseite noch einmal


import sys  # noqa: E402
