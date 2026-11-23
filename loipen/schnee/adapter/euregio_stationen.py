"""Wetterstationen der Lawinenwarndienste Tirol, Suedtirol und Trentino (avalanche.report), GeoJSON.

Jeder Lauf holt den aktuellen Stand aller Stationen (stations.geojson). Eine Zeitreihe je Station gibt es nicht,
aber stuendliche Schnappschuesse ({datum}_{HH}-00_stations.geojson); daraus laedt `archiv` fruehere Tage nach.
Werte: HS Schneehoehe (cm), HSD24 Aenderung der Schneehoehe in 24 h (cm, KEIN Neuschnee, S7), N24 Niederschlag
24 h (mm), LT/LT_MIN/LT_MAX Lufttemperatur (Grad C), WG Wind (km/h). Hoehe ist die dritte Koordinate.
"""

from datetime import date, datetime

from loipen.schnee.adapter._hilfe import json_aus, werte
from loipen.schnee.daten import Ergebnis, StationDaten

GROESSEN = {"hs": ("HS", "cm"), "hsd24": ("HSD24", "cm"), "rr24": ("N24", "mm"), "ta": ("LT", "°C"),
            "ta_min": ("LT_MIN", "°C"), "ta_max": ("LT_MAX", "°C"), "ff": ("WG", "km/h")}


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    url = q.optionen["url"]
    yield Antwort(url=url, inhalt=fetcher.get_bytes(url), art="katalog")


def archiv_urls(q, tag: date) -> list[str]:
    """Stuendliche Schnappschuesse eines frueheren Tages (Standard 6 und 18 Uhr)."""
    return [q.optionen["url_archiv"].format(datum=tag.isoformat(), stunde=f"{h:02d}")
            for h in q.optionen.get("archiv_stunden", [6])]


def verarbeite(antwort, q) -> Ergebnis:
    erg = Ergebnis()
    for f in json_aus(antwort.inhalt).get("features", []):
        p = f.get("properties") or {}
        koord = (f.get("geometry") or {}).get("coordinates") or []
        if len(koord) < 2:
            continue
        kennung = p.get("LWD-Nummer") or f.get("id")
        region = (p.get("LWD-Region") or "").split(" ")[0] or None
        hoehe = round(koord[2]) if len(koord) > 2 and koord[2] is not None else None
        groessen = [g for g, (feld, _) in GROESSEN.items() if p.get(feld) is not None]
        erg.stationen.append(StationDaten(
            kennung=str(kennung), name=p.get("name") or str(kennung), lat=koord[1], lon=koord[0], hoehe_m=hoehe,
            betreiber=p.get("operator"), land=region.split("-")[0] if region else None, warnregion=region,
            messgroessen=groessen))
        if not p.get("date"):
            continue
        zeit = datetime.fromisoformat(p["date"])
        erg.messwerte += werte(str(kennung), zeit, {g: (p.get(feld), e) for g, (feld, e) in GROESSEN.items()},
                               "stunde")
    return erg
