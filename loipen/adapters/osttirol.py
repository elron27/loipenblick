"""Adapter osttirol: Loipenliste von Osttirol Tourismus (osttirol.com), Querpruefung nur fuer die Testversion
(P33, E-24, Stand 19.11.2026).

Befund des Schnappschusses vom 19.11.2026 (tests/fixtures/osttirol/2026-11-19/alle-loipen.html):
- Eine Seite (/aktiv-outdoor/langlaufen-und-biathlon/alle-loipen) fuehrt alle 59 Loipen Osttirols als
  div.gsmap-list-item mit data-gsid (stabile Nummer), Name mit Link auf die Detailseite, Kaesten
  "Streckenlaenge", "Beschneit", "Schwierigkeit" und dem Status als div.intermaps-status
  ("Status: geschlossen", Klasse closed). Eine Loipe hat keinen Status (Verbindung Promenadenloipe und Talblickloipe Kals).
- Kein Datum, keine Schneehoehe, keine Koordinaten in der Liste. Die Lage kommt ueber die Dubletten-
  erkennung von tirol.at.
- Der Ort steht nur bei einem Teil der Loipen im Namen ("Sonnenloipe Sillian"). Das Gebiet kommt daher
  aus config["gebiet_map"] (Wort im Namen -> Gebiet), fuer die uebrigen aus config["gebiet_je_loipe"]
  (Schluessel -> Gebiet). Was beides nicht trifft, bekommt default_gebiet und eine Warnung, damit eine neue
  Loipe auffaellt.
- Der Loipenzustandsbericht von Osttirol liegt bei Intermaps (sdds4.intermaps.com). Intermaps wird nach P17
  nicht abgerufen; diese Seite ist die eigene Seite des Tourismusverbands.
"""

import re
from urllib.parse import urljoin

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand

PFAD = "/aktiv-outdoor/langlaufen-und-biathlon/alle-loipen"


def _text(sel) -> str:
    return re.sub(r"\s+", " ", sel.xpath("normalize-space()").get(default="")).strip()


def kaesten(item) -> dict[str, str]:
    """{'Streckenlänge': '0.6 km', 'Beschneit': 'Nein', 'Schwierigkeit': 'Leicht'}; leere Werte fehlen."""
    werte = {}
    for kasten in item.css(".gsmap-list-item-box-inner"):
        label = _text(kasten.css(".gsmap-list-item-box-label"))
        wert = _text(kasten.css(".gsmap-list-item-box-value"))
        if label and wert:
            werte[label] = wert
    return werte


def km(text: str) -> float | None:
    """'0.6 km' -> 0.6, '11.2 km' -> 11.2, '23 km' -> 23.0 (Punkt als Dezimaltrenner, anders als parse_zahl)."""
    treffer = re.search(r"\d+(?:[.,]\d+)?", text or "")
    return float(treffer.group(0).replace(",", ".")) if treffer else None


def gebiet_fuer(name: str, key: str, config: dict) -> str | None:
    je_loipe = config.get("gebiet_je_loipe") or {}
    if key in je_loipe:
        return je_loipe[key]
    for wort, gebiet in (config.get("gebiet_map") or {}).items():
        if re.search(rf"\b{re.escape(wort)}", name, re.IGNORECASE):
            return gebiet
    return None


class OsttirolAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", PFAD)
        sel = Selector(fetcher.get(url))
        gesehen: set[str] = set()
        for item in sel.css("div.gsmap-list-item"):
            link = item.css(".gsmap-list-item-title a")[:1]
            name = _text(link)
            href = link.attrib.get("href") if link else None
            if not name or not href:
                continue
            key = item.attrib.get("data-gsid") or href.rstrip("/").rsplit("/", 1)[-1]
            if key in gesehen:
                continue
            gesehen.add(key)
            gebiet = gebiet_fuer(name, key, config)
            if gebiet is None:
                gebiet = config["default_gebiet"]
                ergebnis.warnungen.append(f"Loipe {name!r} ({key}) ohne Gebiet, Standardgebiet {gebiet}")
            d = LoipenDaten(source_key=key, name=name, source_url=urljoin(url, href), gebiet_slug=gebiet)
            roh = _text(item.css(".intermaps-status"))
            wort = re.sub(r"^Status:\s*", "", roh)
            if wort:
                d.status, bekannt = normiere_zustand(wort)
                if not bekannt:
                    d.unbekannte_begriffe.append(("status", wort))
                d.status_rohtext = wort
            werte = kaesten(item)
            if "Streckenlänge" in werte:
                d.laenge_km = km(werte["Streckenlänge"])
            if "Schwierigkeit" in werte:
                d.schwierigkeit, ok = normiere_schwierigkeit(werte["Schwierigkeit"])
                if not ok:
                    d.unbekannte_begriffe.append(("schwierigkeit", werte["Schwierigkeit"]))
            d.nachtloipe = True if re.search(r"beleuchtet|nachtloipe", name, re.IGNORECASE) else None
            d.rohtext = "; ".join([roh or "ohne Status", *(f"{k}: {v}" for k, v in werte.items())])
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen in der Liste gefunden, Seitenaufbau geaendert?")
        return ergebnis
