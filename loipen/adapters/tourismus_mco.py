"""Adapter: Loipenlisten der Tiroler Tourismusverbaende auf dem Next.js-Tourenportal (P32, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/hall-wattens/2026-11-19/,
tests/fixtures/silberregion-karwendel/2026-11-19/):
- hall-wattens.at/de/langlaufen.html und silberregion-karwendel.com/de/langlaufen.html laufen auf
  demselben Baukasten (Medien von tourism.<domain>, CSS-Modul-Klassen mit wechselnden Namen).
- Die Seiten liefern die Loipen als JSON im React-Server-Strom (self.__next_f.push([1, "..."])):
  je Loipe ein Objekt mit objectType "tour", title, statusType (open/closed), pageName,
  latitude/longitude, difficultyLevel (easy/medium/hard) und distance (Meter, Hall-Wattens) bzw.
  distanceString ("1,50 km", Karwendel). Karwendel vertauscht latitude und longitude.
- Kein Praeparierdatum, kein Stand der Meldung. Karwendel fuehrt einen Eintrag "TEST Loipe" ohne Status.
Gelesen wird das JSON, nicht das HTML, weil die Klassennamen bei jedem Neubau der Seite wechseln.
"""

import json
import re

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_zahl
from loipen.models import Schwierigkeit

_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
SCHWIERIGKEIT = {"easy": Schwierigkeit.LEICHT, "medium": Schwierigkeit.MITTEL, "hard": Schwierigkeit.SCHWER}


def touren(html: str) -> list[dict]:
    """Alle Tour-Objekte mit statusType aus dem Server-Strom, je id einmal."""
    strom = "".join(json.loads(f'"{teil}"') for teil in _PUSH.findall(html))
    dec = json.JSONDecoder()
    gefunden: dict = {}
    for m in re.finditer(r'"statusType":"', strom):
        pos = start = m.start()
        for _ in range(400):
            start = strom.rfind("{", 0, start)
            if start < 0:
                break
            try:
                obj, ende = dec.raw_decode(strom, start)
            except ValueError:
                continue
            if ende > pos and isinstance(obj, dict) and "statusType" in obj:
                if obj.get("objectType", "tour") == "tour" and obj.get("title"):
                    gefunden.setdefault(obj.get("id") or obj["title"], obj)
                break
    return list(gefunden.values())


def _lage(obj: dict) -> tuple[float | None, float | None]:
    lat, lon = obj.get("latitude"), obj.get("longitude")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None, None
    # Alpenraum: Breite um 47, Laenge um 11; vertauschte Angaben (Karwendel) zuruecktauschen
    return (lon, lat) if lat < lon else (lat, lon)


class TourismusMcoAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        basis = base_url.rstrip("/")
        url = basis + config["pfad"]
        karte = config.get("gebiet_map", {})
        for obj in touren(fetcher.get(url)):
            name = re.sub(r"\s+", " ", obj["title"]).strip()
            if name.lower().startswith("test "):
                continue
            orte = [t.get("title", "") for t in obj.get("towns") or []]
            gebiet = next((karte[o] for o in reversed(orte) if o in karte),
                          next((g for wort, g in karte.items() if wort in name), config["default_gebiet"]))
            seite = obj.get("pageName") or ""
            d = LoipenDaten(source_key=seite.rsplit("/", 1)[-1].removesuffix(".html") or name,
                            name=name, source_url=basis + seite if seite.startswith("/") else url,
                            gebiet_slug=gebiet, startpunkt=obj.get("startPoint") or (orte[0] if orte else None))
            roh = obj.get("statusTypeString") or obj.get("statusType") or ""
            d.status, bekannt = normiere_zustand(obj.get("statusType"))
            if not bekannt:
                d.unbekannte_begriffe.append(("status", roh))
            d.status_rohtext = roh or None
            stufe = obj.get("difficultyLevel")
            if stufe in SCHWIERIGKEIT:
                d.schwierigkeit = SCHWIERIGKEIT[stufe]
            elif stufe:
                d.schwierigkeit, ok = normiere_schwierigkeit(stufe)
                if not ok:
                    d.unbekannte_begriffe.append(("schwierigkeit", stufe))
            if isinstance(obj.get("distance"), (int, float)):
                d.laenge_km = round(obj["distance"] / 1000, 1)
            elif obj.get("distanceString"):
                d.laenge_km = parse_zahl(obj["distanceString"])
            d.lat, d.lon = _lage(obj)
            d.rundkurs = obj.get("roundTrip")
            d.rohtext = f"{roh}; {obj.get('interfaceIdentifier')}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen im Server-Strom der Seite gefunden, Seitenaufbau geaendert?")
        return ergebnis


__all__ = ["TourismusMcoAdapter", "touren"]
