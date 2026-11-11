"""Adapter C: Loipenmanager von Chiemgau Tourismus (tourinfra), JSON (P11).

Eine Abfrage liefert alle Loipen der Region mit Status, getrennt fuer klassisch und Skating.
Der Ort steht im Feld startort und wird ueber config["gebiet_map"] einem Gebiet zugeordnet.
"""

import json
import logging
import math
import re
from urllib.parse import urljoin

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_datum
from loipen.models import Status, Technik

log = logging.getLogger("loipen.adapters.tourinfra")

TECHNIK = {
    "klassisch": Technik.KLASSISCH,
    "skating": Technik.SKATING,
    "klassisch/skating": Technik.BEIDES,
}
SCHWIERIGKEIT = {1: "leicht", 2: "mittel", 3: "schwer"}  # tourinfra: 1 blau, 2 rot, 3 schwarz


def _status(text) -> tuple[Status | None, bool]:
    if text in (None, ""):
        return None, True
    return normiere_zustand(str(text))


def _km(wert) -> float | None:
    try:
        km = float(wert)
    except (TypeError, ValueError):
        return None
    return km if km >= 0 else None  # -1 = keine Angabe


def _vereinfache(coords: list, max_punkte: int = 120) -> list[tuple[float, float]] | None:
    """Streckenverlauf auf hoechstens max_punkte Punkte ausduennen (Anfang und Ende bleiben)."""
    punkte = [(round(float(p[0]), 5), round(float(p[1]), 5)) for p in coords if len(p) >= 2]
    if len(punkte) < 2:
        return None
    if len(punkte) > max_punkte:
        schritt = (len(punkte) - 1) / (max_punkte - 1)
        punkte = [punkte[round(i * schritt)] for i in range(max_punkte)]
    return punkte


def _rundkurs(coords: list) -> bool | None:
    """U24: Rundkurs, wenn Start und Ende der Strecke unter 300 m auseinander liegen, A nach B ab 1 km."""
    punkte = [(float(p[0]), float(p[1])) for p in coords if len(p) >= 2]
    if len(punkte) < 3:
        return None
    (lat1, lon1), (lat2, lon2) = punkte[0], punkte[-1]
    abstand = math.hypot((lat1 - lat2) * 111.2, (lon1 - lon2) * 111.2 * math.cos(math.radians(lat1)))
    if abstand < 0.3:
        return True
    return False if abstand > 1.0 else None


class TourinfraAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["json_path"]
        daten = json.loads(fetcher.get(url))
        eintraege = daten.values() if isinstance(daten, dict) else daten
        gebiet_map = config.get("gebiet_map", {})

        for e in eintraege:
            name = (e.get("tourname") or "").split("|")[0].strip()
            if not name or not e.get("tid"):
                ergebnis.warnungen.append("Eintrag ohne Name oder ID uebersprungen")
                continue
            ort = (e.get("startort") or "").strip()
            gebiet = gebiet_map.get(ort, config["default_gebiet"])
            if ort not in gebiet_map:
                ergebnis.warnungen.append(f"{name}: Ort {ort!r} nicht in gebiet_map")

            d = LoipenDaten(
                source_key=str(e["tid"]),
                name=name,
                source_url=urljoin(base_url, e["link"]) if e.get("link") else base_url,
                gebiet_slug=gebiet,
            )
            d.status_rohtext = f"klassisch: {e.get('status_klassisch_text')}, skating: {e.get('status_skating_text')}"
            d.status_klassisch, ok1 = _status(e.get("status_klassisch_text"))
            d.status_skating, ok2 = _status(e.get("status_skating_text"))
            gesamt, ok3 = _status(e.get("status_text"))
            for ok, feld, roh in (
                (ok1, "status_klassisch", e.get("status_klassisch_text")),
                (ok2, "status_skating", e.get("status_skating_text")),
                (ok3, "status", e.get("status_text")),
            ):
                if not ok:
                    d.unbekannte_begriffe.append((feld, str(roh)))
            d.status = gesamt or Status.UNBEKANNT
            d.technik = TECHNIK.get((e.get("typ_text") or "").strip().lower(), Technik.UNBEKANNT)
            if d.technik == Technik.UNBEKANNT and e.get("typ_text"):
                d.unbekannte_begriffe.append(("technik", e["typ_text"]))
            schw = SCHWIERIGKEIT.get(e.get("schwierigkeit"))
            if schw:
                d.schwierigkeit, _ = normiere_schwierigkeit(schw)
            d.nachtloipe = bool(e["beleuchtet"]) if e.get("beleuchtet") is not None else None
            d.laenge_km = _km(e.get("laenge"))
            d.gespurt_klassisch_km = _km(e.get("prep_km_klassisch"))
            d.gespurt_skating_km = _km(e.get("prep_km_skating"))
            teile = [k for k in (d.gespurt_klassisch_km, d.gespurt_skating_km) if k is not None]
            d.gespurt_gesamt_km = max(teile) if teile else None
            datum = (e.get("praep_datum") or "").strip()
            if re.search(r"\d", datum):
                d.quelle_aktualisiert_at = parse_datum(datum)
                if d.quelle_aktualisiert_at is None:
                    ergebnis.warnungen.append(f"{name}: Datum {datum!r} nicht lesbar")
            coords = e.get("coords") or []
            if coords:
                d.lat, d.lon = coords[0][0], coords[0][1]
            d.verlauf = _vereinfache(coords)
            d.rundkurs = _rundkurs(coords)
            d.startpunkt = (e.get("startort_detail") or "").strip() or None
            d.rohtext = json.dumps(
                {k: e.get(k) for k in ("status_text", "status_klassisch_text", "status_skating_text",
                                       "geschlossen_typ_text", "praep_datum", "infotext", "lbedingungen")},
                ensure_ascii=False,
            )
            ergebnis.loipen.append(d)
        return ergebnis
