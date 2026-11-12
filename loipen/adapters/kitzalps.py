"""Adapter G: Loipenstatus der Kitzbueheler Alpen, HTML (P15).

Eine Seite (/de/bri/aktuelles/loipen-status.html) fuehrt alle vier Regionen: Brixental, Hohe Salve,
Pillerseetal, St. Johann in Tirol. Je Region eine Ueberschrift und darunter Zeilen mit Name, Laenge,
Stilen und Status ("Gesperrt", "Geoeffnet", ...). Kein Datum und keine Koordinaten: Dubletten mit
tirol.at erkennt der Generator am Namen im selben Gebiet (D15). Region -> Gebiet ueber
config["regionen"] (Wort in der Ueberschrift), einzelne Orte im Namen ueber config["gebiet_map"].
"""

import re
from urllib.parse import urljoin

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_zustand, parse_zahl
from loipen.models import Technik


class KitzAlpsAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        regionen = config.get("regionen", {})
        gebiet_map = config.get("gebiet_map", {})
        region = None
        for el in sel.xpath('//h1|//h2|//h3|//div[@class="row"][div[contains(@class,"column name")]]'):
            if el.root.tag in ("h1", "h2", "h3"):
                kopf = " ".join(el.xpath(".//text()").getall())
                treffer = next((g for wort, g in regionen.items() if wort in kopf), None)
                if treffer:
                    region = treffer
                continue
            link = el.css(".column.name a")
            name = (link.attrib.get("title") or link.xpath("normalize-space()").get() or "").strip()
            if not name:
                continue
            gebiet = next((g for wort, g in gebiet_map.items() if wort in name), region or config["default_gebiet"])
            href = link.attrib.get("href")
            d = LoipenDaten(source_key=(href or name).rsplit("/", 1)[-1].removesuffix(".html"), name=name,
                            source_url=urljoin(url, href) if href else url, gebiet_slug=gebiet)
            d.laenge_km = parse_zahl(el.css(".info .distance::text").get())
            stile = {s.strip(" ,").lower() for s in el.css(".info .value::text").getall()}
            d.technik = (Technik.BEIDES if {"skating", "klassisch"} <= stile else Technik.SKATING if "skating" in stile
                         else Technik.KLASSISCH if "klassisch" in stile else Technik.UNBEKANNT)
            roh = el.css(".column.state span::text").get(default="").strip()
            d.status, bekannt = normiere_zustand(roh)
            if not bekannt:
                d.unbekannte_begriffe.append(("status", roh))
            d.status_rohtext = roh
            d.rohtext = f"{roh}; {', '.join(sorted(stile))}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis
