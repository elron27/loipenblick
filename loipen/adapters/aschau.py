"""Adapter B: Schneebericht-Seite von aschau.de, z. B. /schneebericht-sachrang (P1).

Die Seite enthaelt Artikel je Bereich (Alpin, Langlauf, Huetten ...). Gelesen wird nur der
Artikel mit der Ueberschrift "Langlauf". Je Loipe stehen dort Name, Zustand und
"gespurt: x km von Gesamtkilometer: y km". Laenge und Koordinaten kommen aus den Stammdaten der
Konfiguration, weil die Seite sie nicht liefert (aus der alten App uebernommen).
"""

import logging
import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import (
    normiere_schwierigkeit,
    normiere_zustand,
    parse_datum,
    parse_zahl,
)
from loipen.models import Schwierigkeit

log = logging.getLogger("loipen.adapters.aschau")

_GESPURT = re.compile(r"gespurt:\s*([\d.,]+)\s*km(?:\s*von\s*Gesamtkilometer:\s*([\d.,]+)\s*km)?", re.I)


def _text(sel: Selector) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


def slug(name: str) -> str:
    name = name.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        name = name.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def lese_schneebericht(html: str) -> dict:
    sel = Selector(text=html)
    stand = _text(sel.css("span.snowReport__header__summary"))
    loipen = []
    for art in sel.css("article.snowInfoList__element"):
        if _text(art.css("h3")).lower() != "langlauf":
            continue
        for zeile in art.css(".snowInfoList__element__data"):
            name = _text(zeile.css("h4")).rstrip(":").strip()
            if not name:
                continue
            absaetze = [_text(p) for p in zeile.css("p")]
            gespurt = gesamt = None
            for p in absaetze:
                m = _GESPURT.search(p)
                if m:
                    gespurt, gesamt = parse_zahl(m.group(1)), parse_zahl(m.group(2))
            loipen.append(
                {
                    "name": name,
                    "zustand": _text(zeile.css(".snowInfoList__element__data__line__state em")),
                    "gespurt_km": gespurt,
                    "gesamt_km": gesamt,
                    "text": " ".join(absaetze),
                }
            )
    return {"stand": stand, "loipen": loipen}


class AschauAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["report_path"]
        seite = lese_schneebericht(fetcher.get(url))
        stand = parse_datum(seite["stand"])
        stammdaten = config.get("stammdaten", {})
        if not seite["loipen"]:
            ergebnis.warnungen.append("Kein Langlauf-Bereich auf der Seite gefunden")

        for l in seite["loipen"]:
            fest = stammdaten.get(l["name"], {})
            d = LoipenDaten(
                source_key=slug(l["name"]),
                name=l["name"],
                source_url=url,
                gebiet_slug=config["default_gebiet"],
            )
            d.status, bekannt = normiere_zustand(l["zustand"])
            d.status_rohtext = f"Zustand: {l['zustand']}"
            if not bekannt:
                d.unbekannte_begriffe.append(("zustand", l["zustand"]))
            d.rohtext = f"{l['name']}: {l['zustand']} | {l['text']} | Stand: {seite['stand']}"
            d.quelle_aktualisiert_at = stand
            d.gespurt_gesamt_km = l["gespurt_km"]
            d.laenge_km = l["gesamt_km"] if l["gesamt_km"] is not None else fest.get("laenge_km")
            d.nachtloipe = fest.get("nachtloipe", True if "flutlicht" in l["text"].lower() else None)
            d.lat, d.lon = fest.get("lat"), fest.get("lon")
            d.rundkurs = fest.get("rundkurs")  # U24: steht in der Konfiguration
            if "schwierigkeit" in fest:
                d.schwierigkeit, bekannt = normiere_schwierigkeit(fest["schwierigkeit"])
                if not bekannt:
                    d.unbekannte_begriffe.append(("schwierigkeit", fest["schwierigkeit"]))
            if l["name"] not in stammdaten:
                log.info("Keine Stammdaten fuer %s in der Konfiguration", l["name"])
            ergebnis.loipen.append(d)
        return ergebnis
