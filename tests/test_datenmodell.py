"""Datenmodell gegen PostgreSQL: D1, D2, D3, D4, D7, D8."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Float, Integer, func, inspect, select
from sqlalchemy.exc import IntegrityError

from loipen.konfig import lade_und_abgleichen
from loipen.models import Gebiet, Loipe, Parkplatz, Quelle, Status, Zustand
from loipen.zustand import speichere_zustand

T0 = datetime(2026, 12, 20, 7, 0, tzinfo=timezone.utc)


@pytest.fixture
def konfig(session):
    lade_und_abgleichen(session)
    return session


def neue_loipe(session, quelle_key, gebiet_slug, source_key, name, **werte):
    quelle = session.scalar(select(Quelle).where(Quelle.key == quelle_key))
    gebiet = session.scalar(select(Gebiet).where(Gebiet.slug == gebiet_slug))
    loipe = Loipe(
        quelle=quelle,
        gebiet=gebiet,
        source_key=source_key,
        name=name,
        source_url=f"{quelle.base_url}/{source_key}",
        **werte,
    )
    session.add(loipe)
    session.flush()
    return loipe


@pytest.mark.req("D1", ak=1)
def test_d1_gleichnamige_loipen_sind_getrennt(konfig):
    a = neue_loipe(konfig, "bayrischzell", "bayrischzell", "a-zipflwirt-hauswies-runde-1", "Hauswies-Runde")
    b = neue_loipe(konfig, "fischbachau", "fischbachau", "a-zipflwirt-hauswies-runde-1", "Hauswies-Runde")
    assert a.id != b.id
    assert konfig.scalar(select(func.count()).select_from(Loipe).where(Loipe.name == "Hauswies-Runde")) == 2


@pytest.mark.req("D1")
def test_d1_gleiche_quelle_und_id_nur_einmal(konfig):
    neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    with pytest.raises(IntegrityError):
        neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe doppelt")


@pytest.mark.req("D1")
def test_d1_hierarchie_region_gebiet_loipe(konfig):
    loipe = neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    assert loipe.gebiet.slug == "kreuth"
    assert loipe.gebiet.region.slug == "tegernseer-tal"


@pytest.mark.req("D2", ak=[1, 2])
def test_d2_zahlen_und_koordinaten_in_eigenen_feldern(konfig):
    spalten = {c.name: c.type for c in inspect(Loipe).columns}
    assert isinstance(spalten["laenge_km"], Float)
    assert isinstance(spalten["hoehe_m"], Integer)
    assert isinstance(spalten["lat"], Float) and isinstance(spalten["lon"], Float)
    loipe = neue_loipe(
        konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe", laenge_km=8.4, hoehe_m=770, lat=47.64, lon=11.74
    )
    konfig.expire(loipe)
    assert loipe.laenge_km == 8.4 and loipe.hoehe_m == 770
    assert (loipe.lat, loipe.lon) == (47.64, 11.74)


@pytest.mark.req("D2")
def test_d2_alle_stammdaten_vorhanden():
    spalten = {c.name for c in inspect(Loipe).columns}
    pflicht = {"name", "laenge_km", "technik", "schwierigkeit", "nachtloipe", "hoehe_m", "lat", "lon",
               "verlauf", "gebuehr_text", "hund_erlaubt"}
    assert pflicht <= spalten


@pytest.mark.req("D3", ak=1)
def test_d3_nur_vier_status(konfig):
    loipe = neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    assert {s.value for s in Status} == {"offen", "eingeschraenkt", "geschlossen", "unbekannt"}
    with pytest.raises(ValueError):
        speichere_zustand(konfig, loipe, {"status": "super"}, T0)


@pytest.mark.req("D3", ak=[2, 3])
def test_d3_zeiten_getrennt_und_rohtext(konfig):
    loipe = neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    praepariert = datetime(2026, 12, 20, 5, 30, tzinfo=timezone.utc)
    z, neu = speichere_zustand(
        konfig, loipe,
        {"status": Status.OFFEN, "quelle_aktualisiert_at": praepariert, "rohtext": "Loipenzustand: geöffnet",
         "gespurt_klassisch_km": 8.4, "gespurt_skating_km": 8.4},
        T0,
    )
    konfig.expire(z)
    assert neu
    assert z.quelle_aktualisiert_at == praepariert
    assert z.abgerufen_at == T0
    assert z.rohtext == "Loipenzustand: geöffnet"


@pytest.mark.req("D4", ak=1)
def test_d4_gleicher_zustand_keine_neue_zeile(konfig):
    loipe = neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    werte = {"status": Status.OFFEN, "rohtext": "geöffnet", "gespurt_gesamt_km": 8.4}
    erster, neu1 = speichere_zustand(konfig, loipe, werte, T0)
    zweiter, neu2 = speichere_zustand(konfig, loipe, werte, T0 + timedelta(hours=5))
    assert neu1 and not neu2
    assert erster.id == zweiter.id
    assert zweiter.zuletzt_bestaetigt_at == T0 + timedelta(hours=5)
    assert konfig.scalar(select(func.count()).select_from(Zustand).where(Zustand.loipe_id == loipe.id)) == 1


@pytest.mark.req("D4")
def test_d4_aenderung_gibt_neue_zeile(konfig):
    loipe = neue_loipe(konfig, "tegernsee", "kreuth", "a-ringsee", "Ringseeloipe")
    speichere_zustand(konfig, loipe, {"status": Status.GESCHLOSSEN, "rohtext": "nicht befahrbar"}, T0)
    _, neu = speichere_zustand(konfig, loipe, {"status": Status.OFFEN, "rohtext": "geöffnet"}, T0 + timedelta(days=1))
    assert neu
    assert konfig.scalar(select(func.count()).select_from(Zustand).where(Zustand.loipe_id == loipe.id)) == 2


@pytest.mark.req("D7", ak=[1, 2])
def test_d7_loipe_gehoert_zu_genau_einem_gebiet(konfig):
    spalte = inspect(Loipe).columns["gebiet_id"]
    assert not spalte.nullable
    for gebiet in konfig.scalars(select(Gebiet)):
        assert gebiet.tourist_url.startswith("https://"), gebiet.slug


@pytest.mark.req("D7")
def test_d7_nachbargebiete(konfig):
    bayrischzell = konfig.scalar(select(Gebiet).where(Gebiet.slug == "bayrischzell"))
    assert [g.slug for g in bayrischzell.nachbarn] == ["fischbachau"]


@pytest.mark.req("D8", ak=1)
def test_d8_parkplatz_hat_name_und_koordinaten(konfig):
    gebiet = konfig.scalar(select(Gebiet).where(Gebiet.slug == "sachrang"))
    konfig.add(Parkplatz(gebiet=gebiet, name="Wanderparkplatz Sachrang", lat=47.70, lon=12.26))
    konfig.flush()
    spalten = inspect(Parkplatz).columns
    assert not spalten["name"].nullable and not spalten["lat"].nullable and not spalten["lon"].nullable


@pytest.mark.req("D8", ak=2)
def test_d8_fehlende_gebuehr_ist_unbekannt_nicht_kostenlos(konfig):
    gebiet = konfig.scalar(select(Gebiet).where(Gebiet.slug == "sachrang"))
    park = Parkplatz(gebiet=gebiet, name="Ohne Angabe", lat=47.70, lon=12.26)
    konfig.add(park)
    konfig.flush()
    konfig.expire(park)
    assert park.gebuehr_eur_tag is None  # None = unbekannt; 0.0 hiesse kostenlos
    fischbachau = konfig.scalar(select(Gebiet).where(Gebiet.slug == "fischbachau"))
    assert fischbachau.loipengebuehr_eur is None
    bayrischzell = konfig.scalar(select(Gebiet).where(Gebiet.slug == "bayrischzell"))
    assert bayrischzell.loipengebuehr_eur == 7.0
