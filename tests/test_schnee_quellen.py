"""Fixture-Regressionstests der Schneequellen auf echten Schnappschuessen vom 23.11.2026 (S3, S4, S21, CLAUDE.md 10).

Schnappschuesse: tests/fixtures/schnee-2026-11-23/ (Liste und Lizenzen in quellen.md und manifest.json).
"""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from loipen.fetcher import HttpFehler
from loipen.models import LageberichtFassung, LageberichtRegion, SchneeAbruf, SchneeMesswert, SchneeStation
from loipen.schnee import caaml
from loipen.schnee.adapter import (
    bayern_stationen, caaml_url, dwd_klima, eaws_regionen, euregio_stationen, geosphere_klima, geosphere_snowgrid,
    salzburg_stationen, slf_stationen, suedtirol_stationen,
)
from loipen.schnee.konfig import lade
from loipen.schnee.sammler import Antwort, sammle_quelle

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "tests" / "fixtures" / "schnee-2026-11-23"
QUELLEN = {q.key: q for q in lade(ROOT / "config")[0]}


def antwort(pfad: str, art: str = "daten", url: str | None = None, **meta) -> Antwort:
    return Antwort(url=url or f"https://fixture/{pfad}", inhalt=(F / pfad).read_bytes(), art=art, meta=meta)


def stufen(b):
    return [(s.stufe, s.tageszeit, s.hoehe_unten, s.hoehe_oben) for s in b.stufen]


# ------------------------------------------------------------------------------------------------ Lageberichte
@pytest.mark.req("S4", ak=[3, 5])
def test_s4_zwei_hoehenbaender_an_der_waldgrenze_euregio_xml():
    berichte = caaml.lies((F / "euregio-caaml/2026-01-10_AT-07_de_CAAMLv6.xml").read_bytes())
    assert len(berichte) == 7
    b = next(b for b in berichte if "AT-07-19" in b.regionen)
    assert b.ausgabe_at == datetime(2026, 1, 10, 7, 0, tzinfo=timezone.utc)  # Morgen-Aktualisierung
    assert b.gueltig_von == datetime(2026, 1, 9, 16, 0, tzinfo=timezone.utc)
    assert stufen(b) == [("low", "ganztags", None, "treeline"), ("considerable", "ganztags", "treeline", None)]
    assert b.probleme and b.probleme[0].art


@pytest.mark.req("S4", ak=[3, 5])
def test_s4_vormittag_und_nachmittag_bayern_json_und_xml_gleich():
    j = caaml.lies((F / "bayern-caaml/vormittag-nachmittag_2026-04-23_DE-BY_de_CAAMLv6.json").read_bytes())
    x = caaml.lies((F / "bayern-caaml/vormittag-nachmittag_2026-04-23_DE-BY_de_CAAMLv6.xml").read_bytes())
    assert [stufen(b) for b in j] == [stufen(b) for b in x]
    assert stufen(j[0]) == [("low", "vormittag", None, None), ("low", "nachmittag", None, 1600),
                            ("moderate", "nachmittag", 1600, None)]
    assert sum(len(b.regionen) for b in j) == 10


@pytest.mark.req("S4", ak=5)
def test_s4_morgen_aktualisierung_salzburg_hat_eigene_ausgabezeit():
    b = caaml.lies((F / "salzburg-caaml/2026-01-10_AT-05_de_CAAMLv6.json").read_bytes())
    assert b[0].ausgabe_at == datetime(2026, 1, 10, 7, 25, 37, tzinfo=timezone.utc)


@pytest.mark.req("S4", ak=3)
@pytest.mark.parametrize("datei, berichte, regionen", [
    ("slf-caaml/activeAt_2026-01-10_caaml_de_json.json", 10, 135),
    ("aosta-caaml/aineva_latest_IT-23_de_CAAMLv6.json", 2, 26),
    ("kaernten-caaml/2026-01-10_AT-02_de_CAAMLv6.xml", 7, 69),
    ("eaws-bulletins/fruehester_2021-01-26-DE-BY.json", 6, 6),
    ("meteofrance-caaml/eaws_fruehester_2021-12-01-FR.json", 39, 39),
])
def test_s4_alle_dienste_lesbar(datei, berichte, regionen):
    b = caaml.lies((F / datei).read_bytes())
    assert len(b) == berichte and sum(len(x.regionen) for x in b) == regionen


@pytest.mark.req("S4", ak=3)
def test_s4_frankreich_stufe_nur_fuer_expositionen():
    b = caaml.lies((F / "meteofrance-caaml/eaws_fruehester_2021-12-01-FR.json").read_bytes())[0]
    assert b.stufen[0].expositionen == ["N", "NE", "E", "W", "NW"]


@pytest.mark.req("S4", ak=4)
def test_s4_altes_format_oder_leere_datei_bricht_nicht_ab():
    assert caaml.lies((F / "eaws-bulletins/fruehester_2021-01-25-AT-05.xml").read_bytes()) == []  # CAAML v5
    assert caaml.lies(b'{"bulletins": [{"bulletinID": "x", "neuesFeld": 1}]}') == []


@pytest.mark.req("S4", ak=3)
def test_s4_euregio_sammelbericht_nur_eigene_regionen_und_link():
    q = QUELLEN["euregio"]
    erg = caaml_url.verarbeite(antwort("euregio-caaml/2026-04-20_EUREGIO_de_CAAMLv6.json"), q)
    regionen = {r for b in erg.berichte for r in b.regionen}
    assert regionen and all(r.startswith(("AT-07", "IT-32-BZ", "IT-32-TN")) for r in regionen)
    assert erg.berichte[0].link == "https://avalanche.report/bulletin/2026-04-20"


class _Fetcher:
    """Liefert Fixtures fuer bekannte URLs, sonst 404."""

    def __init__(self, karte: dict[str, str]):
        self.karte, self.abgerufen = karte, []

    def get_bytes(self, url):
        self.abgerufen.append(url)
        if url in self.karte:
            return (F / self.karte[url]).read_bytes()
        raise HttpFehler(url, 404)


@pytest.mark.req("S4", ak=[1, 2])
@pytest.mark.req("S1", ak=[2, 3])
def test_s4_lauf_speichert_fassung_einmal_und_404_ist_kein_fehler(session, tmp_path):
    q = QUELLEN["lawinen-warnung-eu"]
    jetzt = datetime(2026, 1, 10, 11, 0, tzinfo=timezone.utc)
    f = _Fetcher({"https://static.lawinen-warnung.eu/bulletins/2026-01-10/2026-01-10_AT-05_de_CAAMLv6.json":
                  "salzburg-caaml/2026-01-10_AT-05_de_CAAMLv6.json",
                  "https://static.lawinen-warnung.eu/bulletins/2026-01-10/2026-01-10_DE-BY_de_CAAMLv6.json":
                  "bayern-caaml/2026-01-10_DE-BY_de_CAAMLv6.json"})
    lauf = sammle_quelle(session, q, f, tmp_path, jetzt)
    assert lauf.fehler is None and lauf.neu > 0
    assert "https://static.lawinen-warnung.eu/bulletins/2026-01-11/2026-01-11_DE-BY_de_CAAMLv6.json" in f.abgerufen
    zweiter = sammle_quelle(session, q, f, tmp_path, jetzt)
    assert zweiter.neu == 0 and zweiter.werte == lauf.werte
    regionen = {r for (r,) in session.execute(select(LageberichtRegion.warnregion))}
    assert any(r.startswith("AT-05") for r in regionen) and any(r.startswith("DE-BY") for r in regionen)
    assert session.scalar(select(func.count()).select_from(LageberichtFassung)) == 4 + len(
        caaml.lies((F / "bayern-caaml/2026-01-10_DE-BY_de_CAAMLv6.json").read_bytes()))


@pytest.mark.req("S5", ak=[2, 3])
def test_s5_archiv_nachladen_fortsetzbar_und_als_nachgeladen_markiert(engine, tmp_path):
    from contextlib import contextmanager

    from sqlalchemy.orm import Session

    from loipen.schnee.archiv import lade_nach, tage
    q = QUELLEN["eaws-archiv"]
    f = _Fetcher({"https://static.avalanche.report/eaws_bulletins/2021-01-26/2021-01-26-DE-BY.json":
                  "eaws-bulletins/fruehester_2021-01-26-DE-BY.json"})
    with engine.connect() as conn:
        trans = conn.begin()

        @contextmanager
        def scope():
            s = Session(bind=conn, join_transaction_mode="create_savepoint")
            try:
                yield s
                s.commit()
            finally:
                s.close()
        pausen = []
        stand = lade_nach(scope, q, f, tmp_path, date(2021, 1, 25), date(2021, 1, 26), schlafen=pausen.append)
        assert stand["neu"] == 6 and stand["ohne_bericht"] == 2 * len(q.optionen["regionen"]) - 1
        assert pausen and all(p >= 1.0 for p in pausen)  # hoechstens eine Anfrage je Sekunde
        with scope() as s:
            assert s.scalars(select(LageberichtFassung.nachgeladen)).all() == [True] * 6
            assert s.scalar(select(func.count()).select_from(SchneeAbruf)) == 0  # S8 bleibt unberuehrt
        f.abgerufen.clear()
        nochmal = lade_nach(scope, q, f, tmp_path, date(2021, 1, 26), date(2021, 1, 26), schlafen=pausen.append)
        assert nochmal["uebersprungen"] == 1 and nochmal["neu"] == 0
        trans.rollback()
    assert tage(date(2021, 5, 30), date(2021, 11, 2)) == [date(2021, 5, 30), date(2021, 5, 31), date(2021, 11, 1),
                                                         date(2021, 11, 2)]


# ------------------------------------------------------------------------------------------------ Regionen
@pytest.mark.req("S2", ak=1)
def test_e35_warnregionen_mit_umriss_und_gueltigkeit(session):
    erg = eaws_regionen.verarbeite(antwort("eaws-regions/DE-BY_micro-regions.geojson.json"), QUELLEN["eaws-regionen"])
    assert len(erg.regionen) == 13 and erg.regionen[0].land == "DE"
    alt = next(r for r in erg.regionen if r.id == "DE-BY-50")
    assert alt.geometrie["properties"]["end_date"] == "2021-10-01"


# ------------------------------------------------------------------------------------------------ Stationen
@pytest.mark.req("S3", ak=[1, 2])
@pytest.mark.req("S2", ak=1)
def test_s3_euregio_stationen_mit_hoehe_und_region():
    erg = euregio_stationen.verarbeite(antwort("euregio-stationen/stations.geojson", "katalog"),
                                       QUELLEN["euregio-stationen"])
    assert len(erg.stationen) == 355
    st = next(s for s in erg.stationen if s.kennung == "SRET2")
    assert (st.name, st.hoehe_m, st.warnregion, st.land) == ("Rettenbachferner", 2970, "AT-07-20", "AT")
    hs = next(m for m in erg.messwerte if m.station == "SRET2" and m.groesse == "hs")
    assert (hs.wert, hs.einheit, hs.zeitpunkt.isoformat()) == (71.3, "cm", "2026-11-23T19:10:00+01:00")
    assert not any(m.groesse == "hn24" for m in erg.messwerte)  # HSD24 ist eine Differenz, kein Neuschnee (S7)
    assert sum(1 for m in erg.messwerte if m.groesse == "hs") == 224


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_bayern_hoehe_aus_text_und_zehnminutenwerte():
    q = QUELLEN["bayern-stationen"]
    kat = bayern_stationen.verarbeite(antwort("bayern-stationen/api-la-dok_weatherstations_all.json", "katalog"), q)
    assert len(kat.stationen) == 20
    herzog = next(s for s in kat.stationen if s.kennung == "15")
    assert herzog.hoehe_m == 1575 and herzog.name == "Herzogstand"
    werte = bayern_stationen.verarbeite(antwort("bayern-stationen/weatherWeb_3_Zugspitze.json"), q).messwerte
    hs = [m for m in werte if m.groesse == "hs"]
    assert len(hs) == 234 and hs[0].wert == 41 and hs[0].station == "3"


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_salzburg_aktuelle_werte_aus_javascript():
    erg = salzburg_stationen.verarbeite(antwort("salzburg-stationen/Station.js", "katalog"),
                                        QUELLEN["salzburg-stationen"])
    assert len(erg.stationen) == 91
    kat = next(s for s in erg.stationen if s.kennung == "109671")
    assert (kat.hoehe_m, kat.warnregion) == (1635, "AT-05-01")
    hs = next(m for m in erg.messwerte if m.station == "109671" and m.groesse == "hs")
    assert hs.wert == 3.0 and hs.zeitpunkt.tzinfo is not None


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_suedtirol_stationen_und_neueste_schneehoehe():
    q = QUELLEN["suedtirol-stationen"]
    kat = suedtirol_stationen.verarbeite(antwort("suedtirol-stationen/geoservices_meteo_v1_stations.json", "katalog"), q)
    assert len(kat.stationen) == 230
    werte = suedtirol_stationen.verarbeite(antwort("suedtirol-stationen/geoservices_meteo_v1_sensors_HS.json"), q)
    madritsch = next(m for m in werte.messwerte if m.station == "06090SF")
    assert madritsch.wert == 24.0 and madritsch.zeitpunkt.isoformat() == "2026-11-23T19:30:00+01:00"


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_geosphere_hand_und_automat_getrennt_minus_eins_ist_kein_wert():
    q = QUELLEN["geosphere-klima"]
    kat = geosphere_klima.verarbeite(antwort("geosphere-klima/klima-v2-1d_metadata.json", "katalog"), q)
    assert len(kat.stationen) == 204 and all(s.hoehe_m >= 700 for s in kat.stationen)
    werte = geosphere_klima.verarbeite(
        antwort("geosphere-klima/klima-v2-1d_sh_shneu_manu_213-196-82_2026-11-16_2026-11-23.csv"), q).messwerte
    sonnblick = [(m.zeitpunkt.date().isoformat(), m.groesse, m.wert) for m in werte if m.station == "213"]
    assert ("2026-11-16", "hs", 35.0) in sonnblick and ("2026-11-16", "hs_hand", 34.0) in sonnblick
    assert not [m for m in werte if m.station == "82" and m.groesse == "hn24" and m.wert < 0]
    assert not [m for m in werte if m.station == "196"]  # Patscherkofel misst keinen Schnee


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_dwd_zugspitze_plattform_und_neuschnee_berchtesgaden():
    q = QUELLEN["dwd-klima"]
    zug = dwd_klima.verarbeite(antwort("dwd-klima/tageswerte_KL_20278_akt.zip",
                                       url=q.optionen["url_kl"].format(id="20278")), q)
    assert (zug.stationen[0].name, zug.stationen[0].hoehe_m) == ("Zugspitze_Plattform", 2956)
    hs = {m.zeitpunkt.date(): m.wert for m in zug.messwerte if m.groesse == "hs"}
    assert hs[date(2026, 11, 22)] == 75 and hs[date(2026, 11, 21)] == 70
    assert len(hs) <= 14
    bgd = dwd_klima.verarbeite(antwort("dwd-klima/tageswerte_RR_06190_akt.zip",
                                       url=q.optionen["url_rr"].format(id="06190")), q)
    assert bgd.stationen[0].messart == "hand"
    assert {m.groesse for m in bgd.messwerte} >= {"rr", "hs", "hn24"}


@pytest.mark.req("S3", ak=[1, 2])
def test_s3_slf_imis_tageswerte():
    q = QUELLEN["slf-stationen"]
    kat = slf_stationen.verarbeite(antwort("slf-stationen/imis_stations.json", "katalog"), q)
    assert len(kat.stationen) == 207
    dav = next(s for s in kat.stationen if s.kennung == "DAV2")
    assert dav.hoehe_m == 2558
    werte = slf_stationen.verarbeite(antwort("slf-stationen/imis_daily-snow_7d.json"), q).messwerte
    ade = [(m.groesse, m.wert) for m in werte if m.station == "ADE2" and m.zeitpunkt.date() == date(2026, 11, 23)]
    assert ade == [("hs", 55.0), ("hn24", 33.8)]


@pytest.mark.req("S10", ak=1)
def test_s10_snowgrid_in_cm_als_modell():
    q = QUELLEN["geosphere-snowgrid"]
    erg = geosphere_snowgrid.verarbeite(
        antwort("geosphere-snowgrid/snowgrid_cl-v2-1d-1km_2026-11-22_bbox_innsbruck.geojson",
                punkte=[{"kennung": "gebiet:test", "name": "Test", "lat": 47.15, "lon": 11.26, "hoehe": 1500}]), q)
    assert erg.stationen[0].messart == "modell" and erg.stationen[0].hoehe_m == 1500
    assert erg.messwerte[0].wert == 9.0 and erg.messwerte[0].einheit == "cm"


@pytest.mark.req("S3", ak=4)
def test_s3_jedes_land_mindestens_fuenf_stationen_ueber_1500_m():
    hoch = {}
    for key, datei, mod in [("euregio-stationen", "euregio-stationen/stations.geojson", euregio_stationen),
                            ("bayern-stationen", "bayern-stationen/api-la-dok_weatherstations_all.json",
                             bayern_stationen),
                            ("suedtirol-stationen", "suedtirol-stationen/geoservices_meteo_v1_stations.json",
                             suedtirol_stationen),
                            ("salzburg-stationen", "salzburg-stationen/Station.js", salzburg_stationen)]:
        for s in mod.verarbeite(antwort(datei, "katalog"), QUELLEN[key]).stationen:
            if (s.hoehe_m or 0) > 1500:
                hoch.setdefault(s.land, set()).add(s.kennung)
    assert all(len(hoch.get(land, ())) >= 5 for land in ("DE", "AT", "IT")), {k: len(v) for k, v in hoch.items()}


@pytest.mark.req("S1", ak=[1, 2])
def test_s1_katalog_und_werte_einer_quelle_im_lauf(session, tmp_path):
    q = QUELLEN["bayern-stationen"]
    f = _Fetcher({q.optionen["url_liste"]: "bayern-stationen/api-la-dok_weatherstations_all.json",
                  q.optionen["url_werte"].format(id="3"): "bayern-stationen/weatherWeb_3_Zugspitze.json"})
    lauf = sammle_quelle(session, q, f, tmp_path, datetime(2026, 11, 23, 18, tzinfo=timezone.utc))
    # 19 Stationen liefern im Fixture-Fetcher 404: die Quelle meldet den Fehler, die Zugspitze ist gespeichert
    assert session.scalar(select(func.count()).select_from(SchneeStation)) == 20
    assert session.scalar(select(func.count()).select_from(SchneeMesswert)) > 200
    assert lauf.fehler is not None
