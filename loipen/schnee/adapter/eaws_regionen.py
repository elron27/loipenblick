"""Warnregionen der Lawinenwarndienste (E-35): EAWS-Mikroregionen als GeoJSON, Lizenz CC0.

Optionen: regionen (EAWS-Codes), url ({region}). Gespeichert wird je Mikroregion das ganze Feature mit
start_date/end_date, damit alte Berichte ihren damaligen Regionen zugeordnet bleiben.
"""

from loipen.schnee.adapter._hilfe import json_aus
from loipen.schnee.daten import Ergebnis, RegionDaten


def abrufe(q, fetcher, jetzt, session=None):
    from loipen.schnee.sammler import Antwort
    for region in q.optionen.get("regionen", []):
        url = q.optionen["url"].format(region=region)
        yield Antwort(url=url, inhalt=fetcher.get_bytes(url), art="regionen")


def verarbeite(antwort, q) -> Ergebnis:
    daten = json_aus(antwort.inhalt)
    erg = Ergebnis()
    for f in daten.get("features", []):
        p = f.get("properties") or {}
        if not p.get("id"):
            continue
        land = p["id"].split("-")[0]
        erg.regionen.append(RegionDaten(id=p["id"], name=p.get("name"), land=land, geometrie=f))
    return erg
