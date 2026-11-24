"""Adapter C: Loipenmanager von tourinfra, JSON (P11): Chiemgau Tourismus und Tannheimer Tal (D18).

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


def _name(tourname: str) -> str:
    """'Nr. 2 Rundloipe Vilsalpsee - 12,5 km' -> 'Nr. 2 Rundloipe Vilsalpsee'; Chiemgau trennt die Laenge mit '|'."""
    name = tourname.split("|")[0].replace("_", " ")  # Seefeld: "A2_Snowfarmingloipe"
    name = re.sub(r"\s+-\s*\d+(?:[.,]\d+)?\s*km\s*$", "", name)
    return re.sub(r"\s+", " ", name).strip()


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


def _cm(wert) -> int | None:
    """Schneehoehe in cm; leer und 0 (Vorgabewert des Loipenmanagers) gelten als unbekannt (P41 AK 4)."""
    try:
        cm = int(float(str(wert).replace(",", ".")))
    except (TypeError, ValueError):
        return None
    return cm if cm > 0 else None


def _hinweis(e: dict) -> str | None:
    """P41 AK 2: infotext und bzustandinfo des Betreibers, ohne Leerwerte und Testeintraege."""
    teile = []
    for feld in ("infotext", "bzustandinfo"):
        text = re.sub(r"\s+", " ", str(e.get(feld) or "")).strip()
        if text and text.lower() not in {"testeintrag", "test", "none"} and text not in teile:
            teile.append(text)
    return " · ".join(teile) or None


def _einstiege(e: dict) -> list[dict] | None:
    """P41 AK 6: weitere Einstiege (startort_alternativ) mit Ort, Detail und Lage, falls angegeben."""
    liste = []
    for s in e.get("startort_alternativ") or []:
        if not isinstance(s, dict):
            continue
        ort = (s.get("startort") or "").strip()
        detail = (s.get("startort_detail") or "").strip()
        if not ort and not detail:
            continue
        eintrag = {"ort": ort or None, "detail": detail or None}
        try:
            eintrag["lat"], eintrag["lon"] = round(float(s["lat"]), 5), round(float(s["long"]), 5)
        except (KeyError, TypeError, ValueError):
            pass
        liste.append(eintrag)
    return liste or None


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
            if not isinstance(e, dict):
                ergebnis.warnungen.append("Eintrag ohne Felder uebersprungen")
                continue
            if "tid" not in e and "anzk" in e:
                continue  # Summenzeile des Loipenmanagers (km und Anzahl je Status), keine Loipe
            name = _name(e.get("tourname") or "")
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
            # P41 AK 1: Praeparierdatum, sonst Datum der letzten Aenderung ("13.11.2026 / 14:45")
            for feld in ("praep_datum", "datum"):
                datum = (e.get(feld) or "").strip()
                if re.search(r"\d", datum):
                    d.quelle_aktualisiert_at = parse_datum(datum)
                    if d.quelle_aktualisiert_at is None:
                        ergebnis.warnungen.append(f"{name}: Datum {datum!r} nicht lesbar")
                    break
            # P41: Hinweis, Sperrgrund, Schneehoehen, Hund, Kunstschnee, Einstiege, Loipengebiet.
            # B33: redakt (Name des Fahrers oder Redakteurs) wird nie uebernommen.
            d.hinweis = _hinweis(e)
            grund = (e.get("sperr_typ_name") or "").strip()
            if grund and grund.lower() != "unbekannt" and d.status == Status.GESCHLOSSEN:
                d.sperrgrund = grund
            d.schneehoehe_cm = _cm(e.get("sht"))
            d.schneehoehe_berg_cm = _cm(e.get("shh"))
            if isinstance(e.get("hundeloipe"), bool):
                d.hund_erlaubt = e["hundeloipe"]
            if isinstance(e.get("kunstschnee"), bool):
                d.kunstschnee = e["kunstschnee"]
            d.einstiege = _einstiege(e)
            d.loipengebiet = re.sub(r"\s+", " ", (e.get("sportareal_name") or "")).strip() or None
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


# ---------------------------------------------------------------------------------------------------------------
# P42: Detailseite einer Loipe (details.php), einmal je Loipe gelesen. Nur Fakten, keine Beschreibung (E-40).

_DETAIL_ZAHL = {
    "hoehenmeter": r'icon-hoehenmeter"></i>\s*Höhenmeter\s*([\d.]+)\s*hm',
    "tiefster_punkt_m": r'icon-Tiefpunkt1"></i>\s*Tiefpunkt\s*([\d.]+)\s*m',
    "hoechster_punkt_m": r'icon-Hochpunkt1"></i>\s*Hochpunkt\s*([\d.]+)\s*m',
}


def _ganzzahl(text: str) -> int | None:
    try:
        return int(text.replace(".", ""))
    except ValueError:
        return None


def parse_details(seite: str, startort: str | None = None) -> dict:
    """Fakten einer tourinfra-Detailseite (P42 AK 2). Fehlt eine Angabe, fehlt der Schluessel.

    Gibt zusaetzlich "unbekannte_merkmale" zurueck (Badges, die nicht auf die feste Liste passen)."""
    from html import unescape

    from loipen.details import merkmale_aus

    d: dict = {}
    if m := re.search(r'icon-dauer"></i>\s*Dauer\s*(\d+):(\d\d)\s*h', seite):
        minuten = int(m.group(1)) * 60 + int(m.group(2))
        if minuten > 0:  # "00:00 h" = keine Angabe
            d["dauer_min"] = minuten
    for feld, muster in _DETAIL_ZAHL.items():
        if m := re.search(muster, seite):
            wert = _ganzzahl(m.group(1))
            if wert is not None and (wert > 0 or feld == "hoehenmeter"):
                d[feld] = wert
    badges = [unescape(b).strip() for b in re.findall(r"class='badge badge-light mr-1'>([^<]*)<", seite)]
    # Ortsnamen stehen als Badge mit dabei ("Reit im Winkl") und sind kein Merkmal
    ort = (startort or "").strip().lower()
    badges = [b for b in badges if b and b.lower() != ort]
    merkmale, unbekannt = merkmale_aus(badges)
    if merkmale:
        d["merkmale"] = merkmale
    if unbekannt:
        d["unbekannte_merkmale"] = unbekannt
    webcams = []
    for url, inhalt in re.findall(
            r'<a href="(https://www\.webcams\.travel/webcam/\d+)"[^>]*>[\s\S]*?<figcaption[^>]*>([\s\S]*?)</figcaption>',
            seite):
        name = re.sub(r"\s+", " ", unescape(re.split(r"<br\s*/?>", inhalt)[0])).strip()
        if url not in {w["url"] for w in webcams}:
            webcams.append({"name": name or "Webcam", "url": url})
    if webcams:
        d["webcams"] = webcams[:4]  # die naechsten zuerst; weiter entfernte helpen nicht
    return d
