"""Wetterstationen der Provinz Bozen (geoservices.buergernetz.bz.it/services/meteo/v1), Lizenz CC0.

stations: alle Stationen mit Hoehe (ALT), sensors?sensor_code=X: der neueste Wert je Station. Die alte Domain
daten.buergernetz.bz.it gibt seit 2026 404. robots.txt der alten Domain: Crawl-Delay 10.
Zeitangaben enden auf CET (z. B. 2026-11-23T19:30:00CET) und werden als Mitteleuropaeische Zeit gelesen.
"""

from datetime import datetime

from loipen.schnee.adapter._hilfe import BERLIN, antwort, json_aus, zahl
from loipen.schnee.daten import Ergebnis, MesswertDaten, StationDaten

SENSOREN = {"HS": ("hs", "cm"), "LT": ("ta", "°C"), "N": ("rr", "mm")}


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    url = q.optionen["url_stationen"]
    yield Antwort(url=url, inhalt=fetcher.get_bytes(url), art="katalog")
    for code in q.optionen.get("sensoren", ["HS", "LT"]):
        yield antwort(fetcher, q.optionen["url_sensor"].format(sensor=code))


def _zeit(text: str) -> datetime:
    text = text.strip()
    for zone in ("CEST", "CET"):
        if text.endswith(zone):
            return datetime.fromisoformat(text[: -len(zone)]).replace(tzinfo=BERLIN)
    return datetime.fromisoformat(text)


def verarbeite(antwort, q) -> Ergebnis:
    daten = json_aus(antwort.inhalt)
    erg = Ergebnis()
    if antwort.art == "katalog":
        for f in daten.get("features", []):
            p = f.get("properties") or {}
            if not p.get("SCODE") or p.get("LAT") is None:
                continue
            erg.stationen.append(StationDaten(
                kennung=p["SCODE"], name=p.get("NAME_D") or p["SCODE"], lat=p["LAT"], lon=p["LONG"],
                hoehe_m=round(p["ALT"]) if p.get("ALT") is not None else None,
                betreiber="Wetterdienst Südtirol", land="IT"))
        return erg
    for z in daten:
        groesse, einheit = SENSOREN.get(z.get("TYPE"), (None, None))
        w = zahl(z.get("VALUE"))
        if groesse and w is not None and z.get("DATE") and z.get("SCODE"):
            erg.messwerte.append(MesswertDaten(station=z["SCODE"], zeitpunkt=_zeit(z["DATE"]), groesse=groesse,
                                               wert=w, einheit=z.get("UNIT") or einheit, takt="stunde"))
    return erg
