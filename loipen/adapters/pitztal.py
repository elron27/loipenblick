"""Adapter Pitztal: Tourenportal Langlaufen von pitztal.com (P31, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/pitztal/2026-11-19/): Micado-Tourenportal
(Next.js). Die Liste steht serverseitig als Teaser im HTML und vollstaendig in den Daten der Seite
(self.__next_f.push), je Tour ein Objekt mit title, pageName, statusType (open/closed),
statusTypeString ("Geöffnet"), distanceString ("5,00 km"), difficultyLevel (easy/medium/difficult),
towns ([{"title": "St. Leonhard im Pitztal"}]) und den Koordinaten des Starts, wobei die Felder vertauscht
sind (latitude = 10.85, longitude = 47.06). 12 Touren je Seite, Seite 2 ueber ?page=2 (15 Loipen am
19.11.: Mandarfen und Gletscher geoeffnet, Rest geschlossen). Kein Datum.
"""

import json
import re

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.tirol_orte import gebiet, km, nacht, schluessel, setze_schwierigkeit, setze_status
from loipen.models import Status

STATUS = {"open": Status.OFFEN, "closed": Status.GESCHLOSSEN}
STUFE = {"easy": "leicht", "medium": "mittel", "difficult": "schwer"}


def _flight(html: str) -> str:
    teile = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.DOTALL)
    return "".join(json.loads(f'"{t}"') for t in teile)


def micado_touren(html: str) -> tuple[list[dict], int]:
    """Alle Tour-Objekte ({"categories": [...], ...}) aus den Seitendaten und die Seitenzahl."""
    daten = _flight(html)
    touren = []
    for m in re.finditer(r'\{"categories":\[', daten):
        tiefe = 0
        for ende in range(m.start(), len(daten)):
            if daten[ende] == "{":
                tiefe += 1
            elif daten[ende] == "}":
                tiefe -= 1
                if tiefe == 0:
                    break
        try:
            touren.append(json.loads(daten[m.start():ende + 1]))
        except json.JSONDecodeError:
            continue
    seiten = re.search(r'"totalPages":(\d+)', daten)
    return touren, int(seiten.group(1)) if seiten else 1


class PitztalAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        basis = base_url.rstrip("/")
        url = basis + config.get("pfad", "/de/tourenportal-langlaufen.html")
        gesehen: set[str] = set()
        n, seiten = 1, 1
        while n <= min(seiten, int(config.get("max_seiten", 5))):
            touren, seiten = micado_touren(fetcher.get(url if n == 1 else f"{url}?page={n}"))
            for t in touren:
                name = (t.get("title") or "").strip()
                if not name or t.get("tourObjectTypeIdentifier") not in ("crosscountry", None):
                    continue
                key = schluessel(name)
                if key in gesehen:
                    continue
                gesehen.add(key)
                ort = next((o.get("title") for o in t.get("towns") or []), None)
                d = LoipenDaten(source_key=key, name=name, source_url=basis + (t.get("pageName") or ""),
                                gebiet_slug=gebiet(name, ort, config))
                art = t.get("statusType") or ""
                roh = t.get("statusTypeString") or art
                setze_status(d, roh, STATUS.get(art)) if art in STATUS else setze_status(d, roh)
                stufe = t.get("difficultyLevel")
                setze_schwierigkeit(d, STUFE.get(stufe, stufe))
                d.laenge_km = km(t.get("distanceString"))
                # vertauscht in den Seitendaten: latitude traegt die Laenge (~10.8), longitude die Breite (~47)
                a, b = t.get("latitude"), t.get("longitude")
                if a and b:
                    d.lat, d.lon = (b, a) if a < b else (a, b)
                d.startpunkt = t.get("startPoint") or None
                d.nachtloipe = nacht(name)
                d.rohtext = f"{ort}: {art}/{roh}; {t.get('distanceString')}; {stufe}"
                ergebnis.loipen.append(d)
            n += 1
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Touren in den Seitendaten, Seitenaufbau geaendert?")
        return ergebnis
