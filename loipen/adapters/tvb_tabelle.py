"""Loipenbericht-Tabellen der Tourismusverbaende Alpbachtal und Wildschoenau (P34, E-24, nur Test).

Befund (Schnappschuesse vom 19.11.2026, tests/fixtures/alpbachtal|wildschoenau/2026-11-19/langlaufen.html):
beide Seiten laufen auf demselben Pimcore-Baukasten (valantic). Die Langlauf-Seite traegt einen Block
"pimcore_area_content-facility-table" mit einer Tabelle Status | Name | Gespurt | Ort. Der Status steht
nur als Symbol-Klasse (span.table__status--closed), die gespurten Kilometer als "0 km". Kein Datum, keine
Koordinaten, keine Laenge: die Lage kommt von tirol.at, die Zeilen dienen der Querpruefung (E-24).
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_zustand, parse_zahl

# Symbol-Klasse -> Wort fuer normiere_zustand. Bisher nur "closed" gesehen (November).
SYMBOL = {"closed": "geschlossen", "open": "geöffnet", "opened": "geöffnet", "limited": "eingeschränkt",
          "partly": "teilweise geöffnet"}


def schluessel(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-")


def _text(sel) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


class TvbTabelleAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        gebiet_map = config.get("gebiet_map", {})
        zeilen = sel.xpath("//div[contains(@class, 'facility-table')]//table//tbody/tr")
        for tr in zeilen:
            zellen = tr.xpath("./td")
            if len(zellen) < 2:
                continue
            name = _text(zellen[1])
            if not name:
                continue
            ort = _text(zellen[3]) if len(zellen) > 3 else ""
            d = LoipenDaten(source_key=schluessel(name), name=name, source_url=url,
                            gebiet_slug=gebiet_map.get(ort, config["default_gebiet"]))
            klasse = zellen[0].xpath(".//span[contains(@class, 'table__status')]/@class").get(default="")
            symbol = (re.search(r"table__status--([\w-]+)", klasse) or [None, ""])[1]
            roh = SYMBOL.get(symbol, symbol)
            d.status, bekannt = normiere_zustand(roh)
            if not bekannt:
                d.unbekannte_begriffe.append(("status", symbol))
            d.status_rohtext = roh
            if len(zellen) > 2:
                d.gespurt_gesamt_km = parse_zahl(_text(zellen[2]))
            d.startpunkt = ort or None
            d.nachtloipe = True if "nacht" in name.lower() else None
            d.rohtext = f"{symbol}; gespurt {_text(zellen[2]) if len(zellen) > 2 else '-'}; {ort}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Zeilen im Loipenbericht gefunden, Seitenaufbau geaendert?")
        return ergebnis
