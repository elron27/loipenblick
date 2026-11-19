"""Loipenstatus des Tourismusverbands Wilder Kaiser (P34, E-24, nur Test).

Befund (tests/fixtures/wilderkaiser/2026-11-19/langlaufen.html, /de/langlaufen-am-wilden-kaiser.html):
Next.js-Seite, die Liste "Geoeffnete Loipen" steht serverseitig gerendert im HTML. Je Loipe ein
div.*_tourSelectionItem mit div.*_state (data-state="closed", Text "Geschlossen"), Titel-Link auf
/de/tours/<slug>.html, Ort (*_townsString), Stil-Symbolen (icon-tourism-classic|skating) und Laenge
("1,30 km" oder "900,00 m"). Die Klassen tragen einen wechselnden Praefix, daher nur Endungen pruefen.
Kein Datum, keine Koordinaten: die Lage kommt von tirol.at.
"""

from urllib.parse import urljoin

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_zustand, parse_zahl
from loipen.adapters.tvb_tabelle import SYMBOL, _text, schluessel
from loipen.models import Technik


def _klasse(endung: str) -> str:
    return f"contains(concat(@class, ' '), '_{endung} ')"


class WilderKaiserAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/langlaufen-am-wilden-kaiser.html")
        sel = Selector(fetcher.get(url))
        gebiet_map = config.get("gebiet_map", {})
        gesehen: set[str] = set()
        for el in sel.xpath(f"//div[{_klasse('tourSelectionItem')}]"):
            link = el.xpath(f"./a[{_klasse('title')}]")
            name = _text(link) if link else ""
            if not name:
                continue
            href = link.attrib.get("href", "")
            key = href.rsplit("/", 1)[-1].removesuffix(".html") or schluessel(name)
            if key in gesehen:
                continue
            gesehen.add(key)
            ort = _text(el.xpath(f"./p[{_klasse('townsString')}]"))
            d = LoipenDaten(source_key=key, name=name, source_url=urljoin(url, href) if href else url,
                            gebiet_slug=gebiet_map.get(ort, config["default_gebiet"]))
            zustand = el.xpath(f"./div[{_klasse('state')}]")
            roh = _text(zustand) or SYMBOL.get(zustand.attrib.get("data-state", "") if zustand else "", "")
            d.status, bekannt = normiere_zustand(roh)
            if not bekannt:
                d.unbekannte_begriffe.append(("status", roh))
            d.status_rohtext = roh
            symbole = " ".join(el.xpath(f"./div[{_klasse('attributes')}]//i/@class").getall())
            klassisch, skating = "tourism-classic" in symbole, "tourism-skating" in symbole
            d.technik = (Technik.BEIDES if klassisch and skating else Technik.KLASSISCH if klassisch
                         else Technik.SKATING if skating else Technik.UNBEKANNT)
            laenge = _text(el.xpath(f"./p[{_klasse('distanceString')}]"))
            zahl = parse_zahl(laenge)
            if zahl is not None:
                d.laenge_km = round(zahl / 1000, 2) if laenge.rstrip().endswith(" m") else zahl
            d.startpunkt = ort or None
            d.nachtloipe = True if "nacht" in name.lower() else None
            d.rohtext = f"{roh}; {ort}; {laenge}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis
