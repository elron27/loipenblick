"""Adapter F: nur Stammdaten, kein Zustand (P16 AK 2), z. B. berchtesgaden.de.

Fuer Gebiete, deren Quelle Lage, Laenge und Startpunkt der Loipen nennt, aber keinen Zustand.
Je Seite aus config["seiten"] eine Loipe (ein Loipennetz): Name aus h1, Koordinate aus JSON-LD,
Distanz und Startpunkt aus den Tourendetails. Der Status bleibt "unbekannt" mit dem Hinweis, dass
die Quelle keinen Zustand meldet. Fehlende Werte stehen in config (laenge_km, stammdaten je Pfad).
"""

import json
import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import parse_zahl
from loipen.models import Status

KEIN_ZUSTAND = "Quelle meldet keinen Zustand"


class StammdatenAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        for eintrag in config.get("seiten", []):
            pfad, gebiet = eintrag["pfad"], eintrag.get("gebiet", config["default_gebiet"])
            url = base_url.rstrip("/") + pfad
            try:
                sel = Selector(fetcher.get(url))
            except Exception as e:
                ergebnis.warnungen.append(f"{pfad}: nicht lesbar ({type(e).__name__}: {e})")
                continue
            name = " ".join(t.strip() for t in sel.css("h1 ::text").getall() if t.strip())
            d = LoipenDaten(source_key=pfad.strip("/"), name=eintrag.get("name") or name, source_url=url,
                            gebiet_slug=gebiet)
            for ld in sel.xpath('//script[@type="application/ld+json"]/text()').getall():
                try:
                    geo = (json.loads(ld).get("geo") or {})
                except ValueError:
                    continue
                if geo.get("latitude") is not None:
                    d.lat, d.lon = round(float(geo["latitude"]), 5), round(float(geo["longitude"]), 5)
                    break
            distanz = sel.xpath('//span[@class="tourDetail__property__label"][normalize-space()="Distanz"]'
                                '/following-sibling::span[1]/text()').get()
            d.laenge_km = parse_zahl(distanz) if distanz else eintrag.get("laenge_km")
            start = sel.xpath('//h5[normalize-space()="Startpunkt"]/following-sibling::div//text()').getall()
            d.startpunkt = " ".join(t.strip() for t in start if t.strip()) or None
            d.status = Status.UNBEKANNT
            d.status_rohtext = KEIN_ZUSTAND
            d.rohtext = KEIN_ZUSTAND
            if not d.name:
                ergebnis.warnungen.append(f"{pfad}: kein Name gefunden")
                continue
            ergebnis.loipen.append(d)
        return ergebnis
