"""SLF IMIS-Stationen der Schweiz (measurement-api.slf.ch, CC BY 4.0).

stations: Code, Name, Lage, Hoehe; daily-snow?period_in_days=N: Tageswerte HS und HN_1D aller Stationen.
Namensnennung: WSL-Institut fuer Schnee- und Lawinenforschung SLF, mit Link auf www.slf.ch.
"""

from datetime import datetime

from loipen.schnee.adapter._hilfe import UTC, json_aus, werte
from loipen.schnee.daten import Ergebnis, StationDaten


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    yield Antwort(url=q.optionen["url_stationen"], inhalt=fetcher.get_bytes(q.optionen["url_stationen"]),
                  art="katalog")
    url = q.optionen["url_tage"].format(tage=q.optionen.get("tage", 3))
    yield Antwort(url=url, inhalt=fetcher.get_bytes(url))


def verarbeite(antwort, q) -> Ergebnis:
    erg = Ergebnis()
    daten = json_aus(antwort.inhalt)
    if antwort.art == "katalog":
        for s in daten:
            erg.stationen.append(StationDaten(
                kennung=s["code"], name=s.get("label") or s["code"], lat=s["lat"], lon=s["lon"],
                hoehe_m=round(s["elevation"]) if s.get("elevation") is not None else None,
                betreiber="WSL-Institut für Schnee- und Lawinenforschung SLF", land="CH", messgroessen=["hs", "hn24"]))
        return erg
    for z in daten:
        zeit = datetime.fromisoformat(z["measure_date"])
        if zeit.tzinfo is None:
            zeit = zeit.replace(tzinfo=UTC)
        erg.messwerte += werte(z["station_code"], zeit, {"hs": (z.get("HS"), "cm"), "hn24": (z.get("HN_1D"), "cm")},
                               "tag")
    return erg
