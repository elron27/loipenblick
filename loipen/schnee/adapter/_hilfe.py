"""Gemeinsame Helfer der Schnee-Adapter."""

import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loipen.schnee.daten import MesswertDaten

BERLIN = ZoneInfo("Europe/Berlin")
UTC = timezone.utc


def json_aus(inhalt: bytes):
    return json.loads(inhalt.decode("utf-8-sig"))


def zahl(wert) -> float | None:
    """Zahl oder None; leere Felder, Texte und Fehlwerte (-999) sind kein Wert (D11)."""
    if wert is None or wert == "" or isinstance(wert, bool):
        return None
    try:
        z = float(wert)
    except (TypeError, ValueError):
        return None
    if z != z or z <= -999:
        return None
    return z


def tage(jetzt: datetime, zurueck: int, vor: int = 0) -> list[date]:
    heute = jetzt.astimezone(BERLIN).date()
    return [heute + timedelta(days=i) for i in range(-zurueck, vor + 1)]


def werte(station: str, zeit: datetime, eintraege: dict[str, tuple[object, str]], takt: str) -> list[MesswertDaten]:
    """eintraege: groesse -> (rohwert, einheit). Fehlende Werte fallen weg."""
    out = []
    for groesse, (roh, einheit) in eintraege.items():
        w = zahl(roh)
        if w is not None:
            out.append(MesswertDaten(station=station, zeitpunkt=zeit, groesse=groesse, wert=w, einheit=einheit,
                                     takt=takt))
    return out


def antwort(fetcher, url: str, art: str = "daten", **meta):
    """Holt eine URL. Schlaegt ein einzelner Abruf fehl (HTTP-Fehler, Verbindung), kommt eine Antwort der Art
    "fehler" zurueck: Der Sammel-Job vermerkt sie und macht mit den uebrigen Stationen weiter (B28)."""
    import httpx

    from loipen.fetcher import HttpFehler
    from loipen.schnee.sammler import Antwort
    try:
        return Antwort(url=url, inhalt=fetcher.get_bytes(url), art=art, meta=meta)
    except (HttpFehler, httpx.HTTPError) as e:
        return Antwort(url=url, inhalt=b"", art="fehler", meta={**meta, "fehler": f"{type(e).__name__}: {e}"})
