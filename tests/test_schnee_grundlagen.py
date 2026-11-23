"""Schneekarte: Konfiguration, Rohablage, Speichern mit Fassungen, Ausreisser, Luecken (S1, S2, S6, S7, S8, S9)."""

import gzip
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from sqlalchemy import func, select

from loipen.models import LageberichtFassung, SchneeAbruf, SchneeMesswert, SchneeRohdatei, SchneeStation
from loipen.schnee import konfig, plausibel, rohablage
from loipen.schnee.daten import BerichtDaten, Ergebnis, MesswertDaten, StationDaten, Stufe
from loipen.schnee.konfig import SchneeQuelle
from loipen.schnee.sammler import Antwort, luecken, sammle_quelle
from loipen.schnee.speicher import speichere

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 11, 23, 6, 0, tzinfo=timezone.utc)

GUELTIG = {"key": "q", "name": "Q", "adapter": "x", "lizenz": "CC BY 4.0", "namensnennung": "Q",
           "einnahmen": "ja", "geprueft_am": "2026-11-23"}


def _station(kennung="S1", hoehe=1800):
    return StationDaten(kennung=kennung, name=f"Station {kennung}", lat=47.2, lon=11.4, hoehe_m=hoehe,
                        messgroessen=["hs"])


def _hs(wert, kennung="S1", tag=T0):
    return MesswertDaten(station=kennung, zeitpunkt=tag, groesse="hs", wert=wert, einheit="cm")


# ------------------------------------------------------------------------------------------------ S6 Konfiguration
@pytest.mark.req("S6", ak=2)
def test_s6_quelle_ohne_lizenz_wird_abgelehnt():
    quellen, fehler = konfig.pruefe([{**GUELTIG, "lizenz": None}, GUELTIG | {"key": "ok"}])
    assert [q.key for q in quellen] == ["ok"]
    assert "lizenz" in fehler[0]


@pytest.mark.req("S6", ak=2)
def test_s6_einnahmen_und_erlaubnis_nur_bekannte_werte():
    _, fehler = konfig.pruefe([GUELTIG | {"einnahmen": "vielleicht"}, GUELTIG | {"key": "b", "erlaubnis": "egal"}])
    assert len(fehler) == 2
    q, _ = konfig.pruefe([GUELTIG])
    assert q[0].erlaubnis == "ausstehend"


@pytest.mark.req("S6", ak=3)
def test_s6_open_meteo_nie_erlaubt():
    _, fehler = konfig.pruefe([GUELTIG | {"url": "https://api.open-meteo.com/v1/forecast"}])
    assert "Open-Meteo" in fehler[0]


@pytest.mark.req("S6", ak=3)
def test_s6_ausgelieferte_konfiguration_ohne_open_meteo_und_vollstaendig():
    eintraege = yaml.safe_load((ROOT / "config" / "schnee.yaml").read_text(encoding="utf-8"))["quellen"]
    assert "open-meteo" not in yaml.safe_dump(eintraege).lower()
    quellen, fehler = konfig.pruefe(eintraege)
    assert not fehler
    assert len(quellen) == len(eintraege) > 0


@pytest.mark.req("S6", ak=4)
def test_s6_einnahmen_unklar_nur_in_der_testversion():
    q = SchneeQuelle(**GUELTIG | {"einnahmen": "unklar"})
    assert q.nur_test
    assert not SchneeQuelle(**GUELTIG | {"erlaubnis": "liegt_vor"}).nur_test


# ------------------------------------------------------------------------------------------------ S1/S9 Rohablage
@pytest.mark.req("S1", ak=2)
def test_s1_rohdatei_gepackt_mit_pruefsumme_und_nur_einmal(session, tmp_path):
    a = rohablage.lege_ab(session, tmp_path, "q", "https://x/a.xml", b"<a/>", "text/xml", T0)
    b = rohablage.lege_ab(session, tmp_path, "q", "https://x/a.xml", b"<a/>", "text/xml", T0)
    assert a.id == b.id and len(a.sha256) == 64
    assert gzip.decompress((tmp_path / a.pfad).read_bytes()) == b"<a/>"
    assert a.pfad.startswith("q/2026/11/23/")
    assert session.scalar(select(func.count()).select_from(SchneeRohdatei)) == 1


# ------------------------------------------------------------------------------------------------ S1/S2 Speichern
@pytest.mark.req("S1", ak=[2, 3])
def test_s1_zweiter_lauf_ohne_dubletten_geaenderter_wert_neue_fassung(session):
    erg = Ergebnis(stationen=[_station()], messwerte=[_hs(120)])
    assert speichere(session, "q", erg, jetzt=T0).werte == 1
    assert speichere(session, "q", erg, jetzt=T0).werte == 0
    speichere(session, "q", Ergebnis(stationen=[_station()], messwerte=[_hs(118)]), jetzt=T0)
    werte = session.scalars(select(SchneeMesswert).order_by(SchneeMesswert.fassung)).all()
    assert [(w.wert, w.fassung) for w in werte] == [(120, 1), (118, 2)]
    assert werte[0].einheit == "cm" and werte[0].zeitpunkt == T0


@pytest.mark.req("S2", ak=[1, 2])
def test_s2_station_ohne_hoehe_nicht_uebernommen_sondern_gemeldet(session):
    z = speichere(session, "q", Ergebnis(stationen=[_station("A", None), _station("B")],
                                         messwerte=[_hs(10, "A"), _hs(20, "B")]), jetzt=T0)
    assert [s.kennung for s in session.scalars(select(SchneeStation))] == ["B"]
    assert any("ohne Höhe" in w for w in z.warnungen)
    assert z.werte == 1


@pytest.mark.req("S2", ak=4)
def test_s2_verschwundene_station_wird_inaktiv_nie_geloescht(session):
    speichere(session, "q", Ergebnis(stationen=[_station("A"), _station("B")]), jetzt=T0, katalog_vollstaendig=True)
    speichere(session, "q", Ergebnis(stationen=[_station("A")]), jetzt=T0 + timedelta(days=1),
              katalog_vollstaendig=True)
    st = {s.kennung: s.aktiv for s in session.scalars(select(SchneeStation))}
    assert st == {"A": True, "B": False}


@pytest.mark.req("S4", ak=[2, 3])
def test_s4_jede_fassung_genau_einmal(session):
    def bericht(ausgabe):
        return BerichtDaten(bulletin_id="b1", ausgabe_at=ausgabe, gueltig_von=T0, gueltig_bis=T0 + timedelta(days=1),
                            regionen=["AT-07-01", "AT-07-02"], stufen=[Stufe("considerable", hoehe_unten=2000)])
    abend = T0 - timedelta(hours=13)
    assert speichere(session, "lwd", Ergebnis(berichte=[bericht(abend)]), jetzt=T0).werte == 2
    assert speichere(session, "lwd", Ergebnis(berichte=[bericht(abend)]), jetzt=T0).werte == 0
    speichere(session, "lwd", Ergebnis(berichte=[bericht(T0)]), jetzt=T0)  # Morgen-Aktualisierung
    fassungen = session.scalars(select(LageberichtFassung).order_by(LageberichtFassung.ausgabe_at)).all()
    assert [f.ausgabe_at for f in fassungen] == [abend, T0]
    assert fassungen[0].regionen[0].stufen[0] | {} == {
        "stufe": "considerable", "zahl": 3, "tageszeit": "ganztags", "hoehe_unten": 2000, "hoehe_oben": None,
        "expositionen": []}


# ------------------------------------------------------------------------------------------------ S1 Sammel-Job
class _Adapter:
    """Ersatz-Adapter: erste Antwort gut, zweite unlesbar."""

    @staticmethod
    def verarbeite(a, q):
        if a.inhalt == b"kaputt":
            raise ValueError("unlesbar")
        return Ergebnis(stationen=[_station()], messwerte=[_hs(float(a.inhalt))])


@pytest.mark.req("S1", ak=4)
def test_s1_unlesbare_antwort_bricht_quelle_nicht_ab(session, tmp_path, monkeypatch):
    monkeypatch.setattr("loipen.schnee.sammler.adapter", lambda name: _Adapter)
    q = SchneeQuelle(**GUELTIG)
    lauf = sammle_quelle(session, q, None, tmp_path, T0,
                         antworten=[Antwort("https://x/1", b"100"), Antwort("https://x/2", b"kaputt")])
    assert lauf.neu == 1 and lauf.fehler is None and lauf.warnungen
    assert session.scalar(select(func.count()).select_from(SchneeRohdatei)) == 2  # auch die unlesbare bleibt
    abruf = session.scalar(select(SchneeAbruf))
    assert (abruf.werte, abruf.stationen, abruf.tag) == (1, 1, date(2026, 11, 23))


@pytest.mark.req("S1", ak=4)
def test_s1_abruffehler_wird_protokolliert(session, tmp_path, monkeypatch):
    class Kaputt:
        @staticmethod
        def abrufe(q, f, j, s=None):
            raise ConnectionError("Server weg")
    monkeypatch.setattr("loipen.schnee.sammler.adapter", lambda name: Kaputt)
    lauf = sammle_quelle(session, SchneeQuelle(**GUELTIG), None, tmp_path, T0)
    assert "Server weg" in lauf.fehler
    assert session.scalar(select(SchneeAbruf.fehler)).startswith("ConnectionError")


# ------------------------------------------------------------------------------------------------ S8 Luecken
@pytest.mark.req("S8", ak=[1, 3])
def test_s8_tag_ohne_werte_und_einbruch_der_stationen(session):
    q = SchneeQuelle(**GUELTIG)
    for i in range(7):
        session.add(SchneeAbruf(quelle="q", zeit=T0, tag=date(2026, 11, 15 + i), werte=100, stationen=50))
    session.add(SchneeAbruf(quelle="q", zeit=T0, tag=date(2026, 11, 22), werte=60, stationen=30))
    session.add(SchneeAbruf(quelle="q", zeit=T0, tag=date(2026, 11, 23), werte=0, stationen=0, fehler="x"))
    session.flush()
    assert luecken(session, [q], date(2026, 11, 21)) == []
    assert "nur 30 Stationen statt üblich 50" in luecken(session, [q], date(2026, 11, 22))[0]
    assert "keine Werte" in luecken(session, [q], date(2026, 11, 23))[0]


# ------------------------------------------------------------------------------------------------ S7 Ausreisser
def _reihe(werte, rr=None, ta=None):
    start = date(2026, 1, 1)
    return [plausibel.Tag(start + timedelta(days=i), hs=w, rr=(rr or {}).get(i), ta_max=(ta or {}).get(i))
            for i, w in enumerate(werte)]


@pytest.mark.req("S7", ak=[1, 2, 4])
def test_s7_negativ_und_sprung_ohne_niederschlag():
    befund = plausibel.pruefe(_reihe([50, -3, 50, 120, 60, 130], rr={5: 12}))
    assert befund == {date(2026, 1, 2): "negativ", date(2026, 1, 4): "sprung"}


@pytest.mark.req("S7", ak=[2, 4])
def test_s7_warm_sensor_misst_gras():
    befund = plausibel.pruefe(_reihe([20, 20, 21, 19], ta={0: 18, 1: 19, 2: 17, 3: 10}), automatisch=False)
    assert befund == {date(2026, 1, 3): "warm"}


@pytest.mark.req("S7", ak=[2, 4])
def test_s7_eingefrorener_automatischer_wert():
    reihe = _reihe([80] * 10 + [81])
    assert plausibel.pruefe(reihe) == {date(2026, 1, 10): "eingefroren"}
    assert plausibel.pruefe(reihe, automatisch=False) == {}
    assert plausibel.pruefe(_reihe([0] * 12)) == {}  # schneefreie Wiese ist nicht verdaechtig


@pytest.mark.req("S7", ak=3)
def test_s7_neuschnee_wird_nie_aus_der_differenz_berechnet():
    quelltext = (ROOT / "loipen" / "schnee" / "plausibel.py").read_text(encoding="utf-8")
    assert "hn24" not in quelltext.split('"""', 2)[2]


@pytest.mark.req("S8", ak=1)
def test_s8_luecke_wird_per_push_gemeldet():
    gesendet = []
    from loipen.schnee.sammler import melde_luecken
    melde_luecken(["Q: am 23.11.2026 keine Werte"], lambda t, x: gesendet.append((t, x)))
    melde_luecken([], lambda t, x: gesendet.append((t, x)))
    assert gesendet == [("Loipenblick Schneekarte: Lücke beim Sammeln", "Q: am 23.11.2026 keine Werte")]


@pytest.mark.req("S1", ak=1)
def test_s1_zeitplan_je_quelle_ganzjaehrig():
    from loipen.schnee.sammler import ist_faellig
    q = SchneeQuelle(**GUELTIG, uhrzeiten=[8, 18])
    sommer = datetime(2026, 7, 15, 6, 20, tzinfo=timezone.utc)  # 8:20 Ortszeit im Juli
    assert ist_faellig(q, sommer) and not ist_faellig(q, sommer + timedelta(hours=1))
    montags = SchneeQuelle(**GUELTIG, uhrzeiten=[5], optionen={"wochentage": [0]})
    assert ist_faellig(montags, datetime(2026, 11, 23, 4, 20, tzinfo=timezone.utc))
    assert not ist_faellig(montags, datetime(2026, 11, 24, 4, 20, tzinfo=timezone.utc))


@pytest.mark.req("S1", ak=1)
def test_s1_worker_plant_den_sammel_job():
    quelltext = (ROOT / "loipen" / "worker" / "__main__.py").read_text(encoding="utf-8")
    assert 'scheduler.add_job(schnee_tick, "cron", minute=20' in quelltext


@pytest.mark.req("S6", ak=[1, 5])
def test_s6_lizenztabelle_aktuell_und_vollstaendig():
    from loipen.schnee.doku import tabelle
    erzeugt = tabelle(ROOT / "config")
    assert (ROOT / "docs" / "schneekarte-quellen.md").read_text(encoding="utf-8") == erzeugt, \
        "docs/schneekarte-quellen.md neu erzeugen: python -m loipen.schnee.doku"
    quellen, _ = konfig.lade(ROOT / "config")
    assert all(q.lizenz_url and q.namensnennung and q.geprueft_am for q in quellen)
