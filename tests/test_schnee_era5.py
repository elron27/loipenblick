"""ERA5-Land je Warnregion (S26, E-38).

Achtung: Die NetCDF-Datei wird hier im Aufbau der CDS-Antwort (valid_time, latitude, longitude, sf, sde) erzeugt,
weil es noch keinen echten Schnappschuss gibt (Abruf braucht ein CDS-Konto). Sobald Stefans Konto steht, kommt ein
echter Schnappschuss nach tests/fixtures/ und dieser Test liest zusaetzlich ihn (CLAUDE.md 10).
Die Warnregionen sind echte EAWS-Umrisse vom 23.11.2026.
"""

from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import netCDF4
import numpy as np
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loipen.models import SchneeModellwert, SchneeRohdatei
from loipen.schnee.adapter import eaws_regionen, era5_land
from loipen.schnee.konfig import lade
from loipen.schnee.sammler import Antwort, sammle_quelle
from loipen.schnee.speicher import speichere

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "tests" / "fixtures" / "schnee-2026-11-23"
Q = {q.key: q for q in lade(ROOT / "config")[0]}["era5-land"]
INNSBRUCK = (47.27, 11.40)  # liegt in einer Tiroler Mikroregion


def netcdf(tage: list[date], schnee_m: float = 0.012, hoehe_m: float = 0.55) -> bytes:
    """Raster 0,1 Grad ueber Tirol und Bayern, absteigende Breiten wie bei CDS; oestlich 11,0 Grad faellt Schnee."""
    lats = np.round(np.arange(48.0, 46.6, -0.1), 1)
    lons = np.round(np.arange(10.0, 13.1, 0.1), 1)
    ds = netCDF4.Dataset("x.nc", "w", memory=1024)
    ds.createDimension("valid_time", len(tage))
    ds.createDimension("latitude", len(lats))
    ds.createDimension("longitude", len(lons))
    t = ds.createVariable("valid_time", "i8", ("valid_time",))
    t.units, t.calendar = "seconds since 1970-01-01", "proleptic_gregorian"
    t[:] = [int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()) for d in tage]
    ds.createVariable("latitude", "f8", ("latitude",))[:] = lats
    ds.createVariable("longitude", "f8", ("longitude",))[:] = lons
    sf = ds.createVariable("sf", "f4", ("valid_time", "latitude", "longitude"), fill_value=np.float32(np.nan))
    sde = ds.createVariable("sde", "f4", ("valid_time", "latitude", "longitude"), fill_value=np.float32(np.nan))
    feld = np.where(lons[None, :] >= 11.0, schnee_m, 0.0) * np.ones((len(lats), 1))
    sf[:] = np.stack([feld * (k + 1) for k in range(len(tage))])
    sde[:] = np.full((len(tage), len(lats), len(lons)), hoehe_m)
    sf[0, 0, 0] = np.nan  # Meer oder fehlende Zelle
    return bytes(ds.close())


def regionen_aus_fixture() -> list[dict]:
    out = []
    for r in ("AT-07", "DE-BY"):
        erg = eaws_regionen.verarbeite(Antwort(url="x", inhalt=(F / f"eaws-regions/{r}_micro-regions.geojson.json")
                                               .read_bytes()), Q)
        out += [{"id": x.id, "polygone": era5_land._polygone(x.geometrie["geometry"])} for x in erg.regionen
                if not x.geometrie["properties"].get("end_date")]
    return out


def region_von(punkt, regionen):
    lat, lon = punkt
    return next(r["id"] for r in regionen if era5_land.im_polygon(lon, lat, r["polygone"]))


@pytest.mark.req("S26", ak=[1, 3])
def test_s26_anfrage_je_monat_nur_00_utc_und_eindeutige_url():
    assert list(era5_land.monate(date(2026, 11, 28), date(2026, 12, 2))) == [(2026, 11, [28, 29, 30]),
                                                                            (2026, 12, [1, 2])]
    a = era5_land.anfrage(Q, 2026, 12, [1, 2])
    assert a["time"] == ["00:00"] and a["variable"] == ["snowfall", "snow_depth"] and a["area"][0] == 48.5
    url = era5_land.url(a)
    assert era5_land.anfrage_aus(url) == ("reanalysis-era5-land", a)
    assert era5_land.archiv_urls(Q, date(2021, 12, 2)) == []
    [monat] = era5_land.archiv_urls(Q, date(2021, 12, 1))
    assert era5_land.anfrage_aus(monat)[1]["day"][-1] == "31"


@pytest.mark.req("S26", ak=2)
def test_s26_schneefall_je_warnregion_vortag_mm_und_cm():
    regionen = regionen_aus_fixture()
    tirol = region_von(INNSBRUCK, regionen)
    a = Antwort(url="cds://x", inhalt=netcdf([date(2026, 12, 2), date(2026, 12, 3)]), meta={"regionen": regionen})
    erg = era5_land.verarbeite(a, Q)
    sf = {(m.warnregion, m.datum): m for m in erg.modellwerte if m.groesse == "sf"}
    m = sf[(tirol, date(2026, 12, 1))]  # Wert um 00 UTC am 2.12. = Summe des 1.12.
    assert m.hoehe_von == era5_land.GANZE_REGION and m.zellen >= 1
    assert m.maximum == pytest.approx(12.0) and 0 <= m.minimum <= m.mittel <= m.maximum  # 0,012 m = 12 mm
    assert sf[(tirol, date(2026, 12, 2))].maximum == pytest.approx(24.0)
    hs = next(x for x in erg.modellwerte if x.groesse == "hs" and x.warnregion == tirol)
    assert hs.mittel == pytest.approx(55.0)  # 0,55 m in cm
    ids = {x.warnregion for x in erg.modellwerte}
    assert any(i.startswith("DE-BY") for i in ids) and any(i.startswith("AT-07") for i in ids)
    # jede Region im Raster bekommt einen Wert, auch die kleinen ohne Zellmittelpunkt
    im_raster = [r for r in regionen if 46.7 <= np.mean([p[1] for poly in r["polygone"] for p in poly[0]]) <= 48.0
                 and 10.0 <= np.mean([p[0] for poly in r["polygone"] for p in poly[0]]) <= 13.0]
    assert {r["id"] for r in im_raster} <= ids


@pytest.mark.req("S26", ak=1)
def test_s26_ohne_warnregionen_nur_rohdatei_und_hinweis():
    erg = era5_land.verarbeite(Antwort(url="cds://x", inhalt=netcdf([date(2026, 12, 2)])), Q)
    assert not erg.modellwerte and "eaws-regionen" in erg.warnungen[0]


class _Cds:
    """Antwortet wie die CDS-API mit einem Raster fuer genau die angefragten Tage."""

    def __init__(self):
        self.anfragen = []

    def cds(self, url):
        a = era5_land.anfrage_aus(url)[1]
        self.anfragen.append(a)
        return netcdf([date(int(a["year"]), int(a["month"]), int(t)) for t in a["day"]])


def _regionen_in_db(session):
    for r in ("AT-07", "DE-BY"):
        erg = eaws_regionen.verarbeite(Antwort(url="x", inhalt=(F / f"eaws-regions/{r}_micro-regions.geojson.json")
                                               .read_bytes()), Q)
        speichere(session, "eaws-regionen", erg)
    session.flush()


@pytest.mark.req("S26", ak=[1, 2])
def test_s26_lauf_speichert_rohdatei_und_werte_einmal(session, tmp_path):
    _regionen_in_db(session)
    cds = _Cds()
    jetzt = datetime(2026, 11, 23, 8, 0, tzinfo=timezone.utc)
    lauf = sammle_quelle(session, Q, cds, tmp_path, jetzt)
    assert lauf.fehler is None and lauf.neu > 0
    assert cds.anfragen[0]["day"] == [f"{d:02d}" for d in range(11, 19)]  # heute - 5 - 7 bis heute - 5
    assert session.scalar(select(func.count()).select_from(SchneeRohdatei)) == 1
    n = session.scalar(select(func.count()).select_from(SchneeModellwert))
    nochmal = sammle_quelle(session, Q, cds, tmp_path, jetzt)
    assert nochmal.neu == 0 and session.scalar(select(func.count()).select_from(SchneeModellwert)) == n


@pytest.mark.req("S26", ak=3)
@pytest.mark.req("S5", ak=1)
def test_s26_archiv_monatsweise_und_fortsetzbar(engine, tmp_path):
    from loipen.schnee.archiv import lade_nach
    cds = _Cds()
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
        with scope() as s:
            _regionen_in_db(s)
        stand = lade_nach(scope, Q, cds, tmp_path, date(2020, 11, 1), date(2021, 1, 31), schlafen=lambda _: None)
        assert stand["abrufe"] == 3 and [a["month"] for a in cds.anfragen] == ["11", "12", "01"]
        assert stand["neu"] > 0
        nochmal = lade_nach(scope, Q, cds, tmp_path, date(2020, 11, 1), date(2021, 1, 31), schlafen=lambda _: None)
        assert nochmal["abrufe"] == 0 and nochmal["uebersprungen"] == 3
        trans.rollback()
