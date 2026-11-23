"""GeoSphere Austria, Klima-Tageswerte klima-v2-1d (CC BY 4.0), wie D17, aber fuer alle aktiven Stationen ab
`min_hoehe` Metern (Standard 700).

Metadaten (Stationen mit Hoehe) bei jedem Lauf, Werte der letzten `tage` Tage (Standard 7) in Paketen von
`paket` Stationen je Anfrage. Grenze der API: 5 Anfragen je Sekunde, 240 je Stunde.
Werte: sh (Schneehoehe automatisch, cm), sh_manu (von Hand, cm), shneu_manu (Neuschnee von Hand, cm),
rr (Niederschlag, mm), tlmin/tlmax (Grad C). -1 heisst bei Handmessungen "kein Schnee/keine Messung" und ist kein Wert.
"""

import csv
import io
from datetime import datetime, timedelta

from loipen.schnee.adapter._hilfe import antwort, json_aus, zahl
from loipen.schnee.daten import Ergebnis, MesswertDaten, StationDaten

PARAMETER = {"sh": ("hs", "cm", "automatisch"), "sh_manu": ("hs", "cm", "hand"), "shneu_manu": ("hn24", "cm", "hand"),
             "rr": ("rr", "mm", None), "tlmin": ("ta_min", "°C", None), "tlmax": ("ta_max", "°C", None)}


def _stationen(meta: dict, min_hoehe: int) -> list[dict]:
    return [s for s in meta.get("stations", []) if s.get("is_active") and (s.get("altitude") or 0) >= min_hoehe]


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    o = q.optionen
    meta_roh = fetcher.get_bytes(o["url_meta"])
    yield Antwort(url=o["url_meta"], inhalt=meta_roh, art="katalog")
    ids = [str(s["id"]) for s in _stationen(json_aus(meta_roh), o.get("min_hoehe", 700))]
    bis = jetzt.date()
    von = bis - timedelta(days=o.get("tage", 7))
    paket = o.get("paket", 50)
    for i in range(0, len(ids), paket):
        url = o["url_daten"].format(parameter=",".join(PARAMETER), ids=",".join(ids[i:i + paket]),
                                    von=von.isoformat(), bis=bis.isoformat())
        yield antwort(fetcher, url)


def verarbeite(antwort, q) -> Ergebnis:
    erg = Ergebnis()
    if antwort.art == "katalog":
        for s in _stationen(json_aus(antwort.inhalt), q.optionen.get("min_hoehe", 700)):
            erg.stationen.append(StationDaten(
                kennung=str(s["id"]), name=s.get("name") or str(s["id"]), lat=s["lat"], lon=s["lon"],
                hoehe_m=round(s["altitude"]) if s.get("altitude") is not None else None,
                betreiber="GeoSphere Austria", land="AT", messgroessen=["hs", "hn24", "rr", "ta_min", "ta_max"]))
        return erg
    for zeile in csv.DictReader(io.StringIO(antwort.inhalt.decode("utf-8-sig"))):
        zeit = datetime.fromisoformat(zeile["time"])
        for feld, (groesse, einheit, art) in PARAMETER.items():
            w = zahl(zeile.get(feld))
            if w is None or (art == "hand" and w < 0):
                continue
            # Hand- und Automatenmessung der Schneehoehe sind zwei Groessen, damit keine die andere ueberschreibt
            g = "hs_hand" if feld == "sh_manu" else groesse
            erg.messwerte.append(MesswertDaten(station=zeile["station"], zeitpunkt=zeit, groesse=g, wert=w,
                                               einheit=einheit))
    return erg
