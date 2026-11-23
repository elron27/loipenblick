"""Messstationen des Lawinenwarndienstes Bayern (api-la-dok.bayern.de, aus dem Webclient, nicht dokumentiert).

Liste: /public/weatherstations/all/, Werte je Station: /public/weatherWeb/{stationId} (10-Minuten-Werte der
letzten rund 2,7 Tage). Die Hoehe steht als Text im Feld altitudeSnowheight ("Herzogstand (1575 m)").
Bedingungen: Das Impressum verlangt fuer eine Weiterverwendung die Einwilligung des LWD (Stand 23.11.2026), daher
in config/schnee.yaml einnahmen: nein, erlaubnis: nur_test. Gesammelt wird fuer die Historie (E-24, E-34).
In die Datenbank kommt nur der Wert zur vollen Stunde; die Rohdatei behaelt alle 10-Minuten-Werte (Stefan,
23.11.2026: 10-Minuten-Takt bringt fuer die Historie nichts).
Zeitangaben (TS) ohne Zone; angenommen wird UTC (letzter Wert 17:30 bei Abruf 18:37 UTC am 23.11.2026).
"""

import re
from datetime import datetime

from loipen.schnee.adapter._hilfe import UTC, antwort, json_aus, werte
from loipen.schnee.daten import Ergebnis, StationDaten

GROESSEN = {"hs": ("HS", "cm"), "ta": ("TL", "°C"), "ff": ("ff", "m/s")}
_HOEHE = re.compile(r"(\d{3,4})\s*m")


def _hoehe(text: str | None) -> int | None:
    treffer = _HOEHE.findall(text or "")
    return int(treffer[-1]) if treffer else None


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    liste_url = q.optionen["url_liste"]
    liste = fetcher.get_bytes(liste_url)
    yield Antwort(url=liste_url, inhalt=liste, art="katalog")
    for st in json_aus(liste):
        if st.get("type") == "weather" and st.get("stationId"):
            yield antwort(fetcher, q.optionen["url_werte"].format(id=st["stationId"]), station=st["stationId"])


def verarbeite(antwort, q) -> Ergebnis:
    daten = json_aus(antwort.inhalt)
    erg = Ergebnis()
    if antwort.art == "katalog":
        for st in daten:
            if st.get("type") != "weather" or not st.get("stationId"):
                continue
            pos = st.get("position") or {}
            erg.stationen.append(StationDaten(
                kennung=str(st["stationId"]), name=st.get("name") or st["stationId"], lat=pos.get("lat"),
                lon=pos.get("lng"), hoehe_m=_hoehe(st.get("altitudeSnowheight") or st.get("altitude")),
                betreiber="Lawinenwarndienst Bayern", land="DE", messgroessen=["hs", "ta", "ff"]))
        return erg
    for z in daten:
        if not z.get("TS") or not z.get("ID"):
            continue
        zeit = datetime.fromisoformat(z["TS"]).replace(tzinfo=UTC)
        if zeit.minute:
            continue
        erg.messwerte += werte(str(z["ID"]), zeit, {g: (z.get(f), e) for g, (f, e) in GROESSEN.items()}, "stunde")
    return erg
