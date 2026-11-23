"""Messstationen des Lawinenwarndienstes Salzburg (www.salzburg.gv.at/lawine/Station.js).

Die Datei ist JavaScript (`stationData = {...}`) mit den aktuellen Werten je Station, eine Zeitreihe gibt es nicht.
Deshalb wird sie bei jedem Lauf gespeichert. Zeitpunkt der Schneehoehe: hsEnd (Millisekunden seit 1970).
Bedingungen: "Copyright Land Salzburg, sämtliche Rechte vorbehalten" (Impressum, 23.11.2026), daher einnahmen: nein,
erlaubnis: nur_test. Viele Stationen gehoeren GeoSphere und kommen dort offen (Quelle geosphere-klima).
"""

import json
from datetime import datetime

from loipen.schnee.adapter._hilfe import UTC, werte
from loipen.schnee.daten import Ergebnis, StationDaten

GROESSEN = {"hs": ("HS", "cm"), "hsd24": ("HSD24", "cm"), "rr24": ("N24", "mm"), "ta": ("LT", "°C"),
            "ta_min": ("LT_MIN", "°C"), "ta_max": ("LT_MAX", "°C"), "ff": ("WG", "km/h")}


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    url = q.optionen["url"]
    yield Antwort(url=url, inhalt=fetcher.get_bytes(url), art="katalog")


def _daten(inhalt: bytes) -> dict:
    text = inhalt.decode("utf-8-sig")
    start, ende = text.index("{"), text.rindex("}")
    return json.loads(text[start:ende + 1])


def verarbeite(antwort, q) -> Ergebnis:
    erg = Ergebnis()
    for region, stationen in _daten(antwort.inhalt).items():
        regid = region.split(" ")[0]
        for st in stationen:
            kennung = str(st.get("id") or st.get("name"))
            md = st.get("measuredData") or {}
            v = md.get("values") or {}
            erg.stationen.append(StationDaten(
                kennung=kennung, name=st.get("title") or st.get("name") or kennung, lat=st.get("latitude"),
                lon=st.get("longitude"), hoehe_m=round(st["altitude"]) if st.get("altitude") else None,
                betreiber="Lawinenwarndienst Salzburg", land="AT", warnregion=regid,
                messgroessen=[g for g, (f, _) in GROESSEN.items() if v.get(f) is not None]))
            ende = md.get("hsEnd") or md.get("windEnd")
            if not ende:
                continue
            zeit = datetime.fromtimestamp(ende / 1000, UTC)
            erg.messwerte += werte(kennung, zeit, {g: (v.get(f), e) for g, (f, e) in GROESSEN.items()}, "stunde")
    return erg
