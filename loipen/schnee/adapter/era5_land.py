"""ERA5-Land (Copernicus Climate Change Service, CC BY 4.0): Schneefall und Schneehoehe flaechig fuer den
ganzen Alpenraum (S26, E-38), zusammengefasst je Warnregion.

Abruf ueber die API des Climate Data Store (Paket cdsapi). Zugang: kostenloses Konto, Schluessel als CDSAPI_KEY in
der .env auf dem NAS (CDSAPI_URL ist https://cds.climate.copernicus.eu/api), und einmal auf der Seite des
Datensatzes die Nutzungsbedingungen annehmen. Der Schluessel steht nie im Repo.

Abgefragt wird je Kalendermonat nur der Zeitpunkt 00:00 UTC jedes Tages:
- snowfall (sf) ist in ERA5-Land ab 00 UTC aufsummiert; der Wert um 00 UTC des Tages D ist die Summe des Vortags.
  Gespeichert wird er deshalb unter D - 1, in mm Wasseraequivalent (m * 1000).
- snow_depth (sde) ist ein Augenblickswert; der Wert um 00 UTC von D ist die Schneehoehe am Ende von D - 1, in cm.
Die Werte kommen mit rund 5 Tagen Verzug. ERA5T-Vorabwerte koennen spaeter leicht abweichen; bei Modellwerten
bleibt der erste gespeicherte Wert stehen (Rohdatei bleibt zum Neulesen).

Je Warnregion werden Mittel, Minimum und Maximum ueber alle Zellen gebildet, deren Mittelpunkt in der Region liegt
(Raster 0,1 Grad, rund 9 km). Hat eine kleine Region keinen Zellmittelpunkt, zaehlt die Zelle, die ihrem Mittelpunkt
am naechsten liegt. hoehe_von = GANZE_REGION (-1): ueber alle Hoehen; Hoehenbaender folgen mit S10.
Die Umrisse kommen aus der Tabelle warnregionen (Quelle eaws-regionen), alte Fassungen (end_date) zaehlen nicht.
"""

import calendar
import json
import math
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse

from loipen.schnee.daten import Ergebnis, ModellwertDaten

GANZE_REGION = -1
DATENSATZ = "reanalysis-era5-land"
GROESSEN = {"sf": ("snowfall", 1000.0), "hs": ("snow_depth", 100.0)}  # groesse -> (Variable, Faktor auf mm bzw. cm)
_KURZ = {"snowfall": "sf", "snow_depth": "sde"}


# ----------------------------------------------------------------------------------------------- Anfragen
def anfrage(q, jahr: int, monat: int, tage: list[int]) -> dict:
    return {
        "variable": [GROESSEN[g][0] for g in q.optionen.get("groessen", ["sf", "hs"])],
        "year": f"{jahr}", "month": f"{monat:02d}", "day": [f"{t:02d}" for t in tage], "time": ["00:00"],
        "area": q.optionen.get("flaeche", [48.5, 4.5, 43.0, 17.5]),  # Nord, West, Sued, Ost
        "data_format": "netcdf", "download_format": "unarchived",
    }


def url(anfrage_: dict) -> str:
    """Eindeutiger Name einer Anfrage fuer die Rohablage und das Ueberspringen beim Nachladen."""
    return f"cds://{DATENSATZ}?" + urlencode({"anfrage": json.dumps(anfrage_, sort_keys=True)})


def anfrage_aus(url_: str) -> tuple[str, dict]:
    u = urlparse(url_)
    return u.netloc, json.loads(parse_qs(u.query)["anfrage"][0])


def monate(von: date, bis: date):
    """(jahr, monat, tage) fuer die Abfragezeitpunkte von..bis (beide eingeschlossen), monatsweise."""
    tag = von
    while tag <= bis:
        ende = min(bis, date(tag.year, tag.month, calendar.monthrange(tag.year, tag.month)[1]))
        yield tag.year, tag.month, list(range(tag.day, ende.day + 1))
        tag = ende + timedelta(days=1)


def cds_holen(url_: str) -> bytes:  # pragma: no cover - echter Abruf nur auf dem NAS
    import tempfile

    import cdsapi
    datensatz, a = anfrage_aus(url_)
    with tempfile.NamedTemporaryFile(suffix=".nc") as f:
        cdsapi.Client(quiet=True, progress=False).retrieve(datensatz, a, f.name)
        return open(f.name, "rb").read()


def hole(fetcher, url_: str, art: str = "daten", session=None, **meta):
    """Holt eine Anfrage (Tests geben einen Fetcher mit Methode cds). Fehler werden zur Antwort der Art "fehler"."""
    from loipen.schnee.sammler import Antwort
    holer = getattr(fetcher, "cds", None) or cds_holen
    meta = {**meta, "regionen": regionen(session)}
    try:
        return Antwort(url=url_, inhalt=holer(url_), art=art, content_type="application/x-netcdf", meta=meta)
    except Exception as e:  # noqa: BLE001 - cdsapi wirft eigene und requests-Fehler
        return Antwort(url=url_, inhalt=b"", art="fehler", meta={**meta, "fehler": f"{type(e).__name__}: {e}"})


def abrufe(q, fetcher, jetzt: datetime, session=None):
    """Taeglich: das Fenster heute - (verzug + fenster) bis heute - verzug, damit ein ausgefallener Tag nachkommt."""
    heute = jetzt.date()
    bis = heute - timedelta(days=q.optionen.get("verzug_tage", 5))
    von = bis - timedelta(days=q.optionen.get("fenster_tage", 7))
    for jahr, monat, tage in monate(von, bis):
        yield hole(fetcher, url(anfrage(q, jahr, monat, tage)), session=session)


def archiv_urls(q, tag: date) -> list[str]:
    """S5: ein Abruf je Monat (am ersten Saisontag des Monats), begrenzt auf heute - verzug."""
    if tag.day != 1:
        return []
    grenze = date.today() - timedelta(days=q.optionen.get("verzug_tage", 5))
    ende = min(grenze, date(tag.year, tag.month, calendar.monthrange(tag.year, tag.month)[1]))
    if ende < tag:
        return []
    return [url(anfrage(q, tag.year, tag.month, list(range(1, ende.day + 1))))]


# ----------------------------------------------------------------------------------------------- Regionen
def regionen(session) -> list[dict]:
    """[{id, polygone}] aus der Tabelle warnregionen; polygone = Liste von Ringlisten [[(lon, lat), ...], ...]."""
    if session is None:
        return []
    from sqlalchemy import select

    from loipen.models import Warnregion
    heute = date.today().isoformat()
    out = []
    for rid, geo in session.execute(select(Warnregion.id, Warnregion.geometrie)):
        if not geo:
            continue
        ende = (geo.get("properties") or {}).get("end_date")
        if ende and str(ende) < heute:
            continue
        polygone = _polygone(geo.get("geometry") or geo)
        if polygone:
            out.append({"id": rid, "polygone": polygone})
    return out


def _polygone(g: dict) -> list:
    if g.get("type") == "Polygon":
        return [g["coordinates"]]
    if g.get("type") == "MultiPolygon":
        return g["coordinates"]
    return []


def _im_ring(x: float, y: float, ring) -> bool:
    drin = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            drin = not drin
        j = i
    return drin


def im_polygon(x: float, y: float, polygone) -> bool:
    for poly in polygone:
        if poly and _im_ring(x, y, poly[0]) and not any(_im_ring(x, y, loch) for loch in poly[1:]):
            return True
    return False


def zellen_je_region(lats, lons, regionen_: list[dict]) -> dict[str, list[tuple[int, int]]]:
    """Index (i_lat, i_lon) der Zellen je Region; ohne Zellmittelpunkt die naechste Zelle zum Mittelpunkt."""
    out = {}
    for r in regionen_:
        punkte = [p for poly in r["polygone"] for p in poly[0]]
        if not punkte:
            continue
        xmin, xmax = min(p[0] for p in punkte), max(p[0] for p in punkte)
        ymin, ymax = min(p[1] for p in punkte), max(p[1] for p in punkte)
        ii = [i for i, la in enumerate(lats) if ymin <= la <= ymax]
        jj = [j for j, lo in enumerate(lons) if xmin <= lo <= xmax]
        treffer = [(i, j) for i in ii for j in jj if im_polygon(lons[j], lats[i], r["polygone"])]
        if not treffer:
            cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
            if not (lats[-1] <= cy <= lats[0] or lats[0] <= cy <= lats[-1]) or not (
                    min(lons) <= cx <= max(lons)):
                continue  # Region liegt ausserhalb der Flaeche
            i = min(range(len(lats)), key=lambda k: abs(lats[k] - cy))
            j = min(range(len(lons)), key=lambda k: abs(lons[k] - cx))
            treffer = [(i, j)]
        out[r["id"]] = treffer
    return out


# ----------------------------------------------------------------------------------------------- Lesen
def _zeiten(ds) -> list[datetime]:
    import netCDF4
    v = ds.variables["valid_time"] if "valid_time" in ds.variables else ds.variables["time"]
    return [datetime(t.year, t.month, t.day, t.hour, tzinfo=timezone.utc) for t in
            netCDF4.num2date(v[:], v.units, getattr(v, "calendar", "standard"))]


def verarbeite(antwort, q) -> Ergebnis:
    import netCDF4
    import numpy as np
    erg = Ergebnis()
    regionen_ = antwort.meta.get("regionen") or []
    if not regionen_:
        erg.warnungen.append("ERA5-Land: keine Warnregionen in der Datenbank, nur Rohdatei abgelegt "
                             "(zuerst Quelle eaws-regionen laufen lassen)")
        return erg
    with netCDF4.Dataset("era5land.nc", mode="r", memory=antwort.inhalt) as ds:
        lats = [float(x) for x in ds.variables["latitude"][:]]
        lons = [float(x) for x in ds.variables["longitude"][:]]
        zuordnung = zellen_je_region(lats, lons, regionen_)
        zeiten = _zeiten(ds)
        for groesse, (variable, faktor) in GROESSEN.items():
            kurz = _KURZ[variable]
            if kurz not in ds.variables:
                continue
            feld = np.ma.filled(ds.variables[kurz][:].astype(float), np.nan)  # (zeit, lat, lon)
            for k, zeit in enumerate(zeiten):
                datum = zeit.date() - timedelta(days=1)
                for rid, zellen in zuordnung.items():
                    werte = [feld[k, i, j] * faktor for i, j in zellen]
                    werte = [max(w, 0.0) for w in werte if not math.isnan(w)]  # Meer und Rundung unter 0
                    if not werte:
                        continue
                    erg.modellwerte.append(ModellwertDaten(
                        warnregion=rid, hoehe_von=GANZE_REGION, datum=datum, groesse=groesse,
                        mittel=round(sum(werte) / len(werte), 2), minimum=round(min(werte), 2),
                        maximum=round(max(werte), 2), zellen=len(werte)))
    return erg
