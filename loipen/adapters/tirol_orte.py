"""Gemeinsame Helfer fuer die Tiroler Ortsseiten zur Querpruefung von tirol.at (E-24, P31).

Die Ortsseiten der Tourismusverbaende laufen auf verschiedenen Systemen (Pimcore/Valantic, Micado,
Outdooractive-Einbindung), melden aber alle nur offen/geschlossen je Loipe. Sie haben rang 4 und
querpruefung: true; tirol.at bleibt fuehrend.
"""

import html as htmllib
import re

from loipen.adapters.base import LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand
from loipen.models import Status, Technik


def text(fragment: str | None) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def km(roh: str | None) -> float | None:
    """'5,52 km' -> 5.52, '5.5 km' -> 5.5, '656 m' -> 0.656, '3600 m' -> 3.6."""
    roh = (roh or "").replace("\xa0", " ")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*km", roh)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:\.\d{3})*)\s*m\b", roh)
    return round(int(m.group(1).replace(".", "")) / 1000, 3) if m else None


def schluessel(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-")


def gebiet(name: str, ort: str | None, config: dict) -> str | None:
    """Ort (oder ein Wort im Namen bzw. in der Ortsangabe) -> Gebiet laut config["gebiet_map"], sonst default_gebiet."""
    karte = config.get("gebiet_map", {})
    if ort and ort in karte:
        return karte[ort]
    treffer = next((g for wort, g in karte.items() if wort in name or (ort and wort in ort)), None)
    return treffer or config.get("default_gebiet")


def setze_status(d: LoipenDaten, roh: str, status: Status | None = None) -> None:
    """Status aus festem Wert (CSS-Klasse) oder aus dem Wort der Seite; Unbekanntes wird gemeldet (P5)."""
    d.status_rohtext = roh
    if status is not None:
        d.status = status
        return
    d.status, bekannt = normiere_zustand(roh)
    if not bekannt:
        d.unbekannte_begriffe.append(("status", roh))


def setze_schwierigkeit(d: LoipenDaten, roh: str | None) -> None:
    if not roh:
        return
    d.schwierigkeit, bekannt = normiere_schwierigkeit(roh)
    if not bekannt:
        d.unbekannte_begriffe.append(("schwierigkeit", roh))


def technik(roh: str | None) -> Technik:
    """'Klassisch, Skating', 'Klassisch & Skating', 'Skating', 'klassisch' -> Technik."""
    t = (roh or "").lower()
    k, s = "klass" in t, "skat" in t
    return Technik.BEIDES if k and s else Technik.KLASSISCH if k else Technik.SKATING if s else Technik.UNBEKANNT


def nacht(name: str) -> bool | None:
    n = name.lower()
    return True if "nacht" in n or "beleuchtet" in n else None
