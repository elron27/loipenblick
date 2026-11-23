"""DWD Climate Data Center, Tageswerte (CC BY 4.0, Namensnennung Deutscher Wetterdienst).

Stationen aus der Konfiguration (Bayerische Alpen und Vorland). Je Station ein ZIP:
  kl/recent/tageswerte_KL_{id}_akt.zip            SHK_TAG (Schneehoehe), TXK/TNK (Temperatur), RSK (Niederschlag)
  more_precip/recent/tageswerte_RR_{id}_akt.zip   SH_TAG (Schneehoehe), NSH_TAG (Neuschnee), RS (Niederschlag)
Name, Hoehe und Lage stehen in Metadaten_Geographie_{id}.txt im ZIP (letzte Zeile = aktueller Standort).
Fehlwert -999. Daten bis gestern; recent umfasst rund 500 Tage, also auch den Rest des letzten Winters.
"""

import csv
import io
import zipfile
from datetime import date, datetime

from loipen.schnee.adapter._hilfe import BERLIN, antwort, zahl
from loipen.schnee.daten import Ergebnis, MesswertDaten, StationDaten

SPALTEN = {"SHK_TAG": ("hs", "cm"), "SH_TAG": ("hs", "cm"), "NSH_TAG": ("hn24", "cm"), "RSK": ("rr", "mm"),
           "RS": ("rr", "mm"), "TXK": ("ta_max", "°C"), "TNK": ("ta_min", "°C")}


def abrufe(q, fetcher, jetzt, session=None):
    for art, ids in (("kl", q.optionen.get("kl", [])), ("rr", q.optionen.get("rr", []))):
        for sid in ids:
            url = q.optionen[f"url_{art}"].format(id=f"{int(sid):05d}")
            yield antwort(fetcher, url, art=art)


def _lies(z: zipfile.ZipFile, anfang: str) -> list[dict]:
    name = next(n for n in z.namelist() if n.startswith(anfang))
    text = z.read(name).decode("latin-1")
    return list(csv.DictReader(io.StringIO(text), delimiter=";", skipinitialspace=True))


def verarbeite(antwort, q) -> Ergebnis:
    erg = Ergebnis()
    tage_zurueck = q.optionen.get("tage", 14)
    with zipfile.ZipFile(io.BytesIO(antwort.inhalt)) as z:
        geo = _lies(z, "Metadaten_Geographie")[-1]
        geo = {k.strip(): (v or "").strip() for k, v in geo.items() if k}
        sid = str(int(geo["Stations_id"]))
        erg.stationen.append(StationDaten(
            kennung=sid, name=geo["Stationsname"], lat=float(geo["Geogr.Breite"]), lon=float(geo["Geogr.Laenge"]),
            hoehe_m=round(float(geo["Stationshoehe"])), betreiber="Deutscher Wetterdienst", land="DE",
            messart="hand" if "_RR_" in antwort.url else "automatisch"))
        zeilen = _lies(z, "produkt_")
    letzte = zeilen[-tage_zurueck:] if tage_zurueck else zeilen
    for zeile in letzte:
        zeile = {k.strip(): (v or "").strip() for k, v in zeile.items() if k}
        tag = datetime.strptime(zeile["MESS_DATUM"], "%Y%m%d").replace(hour=7, tzinfo=BERLIN)
        for spalte, (groesse, einheit) in SPALTEN.items():
            w = zahl(zeile.get(spalte))
            if w is not None:
                erg.messwerte.append(MesswertDaten(station=sid, zeitpunkt=tag, groesse=groesse, wert=w,
                                                   einheit=einheit))
    return erg
