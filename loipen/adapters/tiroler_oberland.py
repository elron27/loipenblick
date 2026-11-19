"""Adapter Tiroler Oberland und Nauders: Seiten "Geöffnete Einrichtungen" (P31, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/tiroler-oberland/2026-11-19/), beide Seiten vom
TVB Tiroler Oberland (Pimcore, Valantic), Daten serverseitig im HTML:
- tiroler-oberland.com/de/Aktuelles/Geoeffnete-Einrichtungen: je Gruppe eine Tabelle .table-facility mit
  Ueberschrift ("Loipen Tiroler Oberland", "Loipen Nauders | Nordic3 | gebührenpflichtig",
  "Loipen Kaunertal | gebührenpflichtig", "Loipen Kaunergrat"); je Loipe span.status status--closed (title
  "Anlage closed") und der Name als Link. Keine Laenge, kein Stand.
- nauders.com/de/Aktuelles/Einrichtungen-Nauders: Abschnitt #loipen-collapse, Reiter "Alle" (die anderen
  Reiter wiederholen dieselben Zeilen), je Loipe Status-Span, Name mit Technik in Klammern
  ("Arsangsloipe (Klassisch)"), Laenge "3600 m" und Schwierigkeit als Bild blue-/red-/black-slope.svg.
  Stand der Seite: "Letztes Update : <time datetime="2026-11-19 15:40">".
Beide melden am 19.11. alles geschlossen. Statusklassen laut Legende: geöffnet, geschlossen, in Vorbereitung.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import parse_datum
from loipen.adapters.tirol_orte import gebiet, km, nacht, schluessel, setze_schwierigkeit, setze_status, technik
from loipen.models import Status

KLASSE = {"open": Status.OFFEN, "opened": Status.OFFEN, "closed": Status.GESCHLOSSEN,
          "preparation": Status.GESCHLOSSEN, "in-preparation": Status.GESCHLOSSEN}
PISTE = {"blue-slope": "leicht", "red-slope": "mittel", "black-slope": "schwer"}


def _status(d: LoipenDaten, span) -> None:
    klassen = (span.attrib.get("class") or "").split()
    art = next((k.split("--", 1)[1] for k in klassen if k.startswith("status--")), "")
    roh = span.attrib.get("title") or art
    setze_status(d, roh, KLASSE.get(art)) if art in KLASSE else setze_status(d, roh)


class TirolerOberlandAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/Aktuelles/Geoeffnete-Einrichtungen")
        html = fetcher.get(url)
        sel = Selector(html)
        stand_roh = sel.xpath("//div[contains(., 'Letztes Update')]/time/@datetime").get()
        stand = parse_datum(re.sub(r"(\d{4})-(\d\d)-(\d\d)", r"\3.\2.\1", stand_roh)) if stand_roh else None
        gruppen_aus = config.get("gruppen_auslassen", [])
        # nauders.com: nur der Reiter "Alle"; tiroler-oberland.com: alle Tabellen der Seite
        tabellen = sel.xpath("//div[contains(@id, 'pills-content-loipen-all')]//table") or sel.css(".table-facility table")
        gesehen: set[str] = set()
        for tab in tabellen:
            gruppe = " ".join(tab.css("thead th ::text").getall()).strip()
            if "loipe" not in gruppe.lower() and not tab.xpath("ancestor::*[@id='loipen-collapse']"):
                continue
            if any(w in gruppe for w in gruppen_aus):
                continue
            for zelle in tab.xpath(".//td[.//span[contains(@class, 'status--')]]"):
                span = zelle.xpath(".//span[contains(@class, 'status--')]")[0]
                name_td = zelle.xpath("following-sibling::td[1]")
                roh_name = name_td.xpath("normalize-space()").get(default="")
                if not roh_name:
                    continue
                m = re.match(r"(.*?)\s*\(([^)]*)\)\s*$", roh_name)
                name, tech = (m.group(1), m.group(2)) if m else (roh_name, "")
                name = re.sub(r"\s*\|\s*Nauders$", "", name).strip()
                key = schluessel(name)
                if key in gesehen:
                    continue
                gesehen.add(key)
                link = name_td.xpath(".//a/@href").get()
                d = LoipenDaten(source_key=key, name=name, source_url=url,
                                gebiet_slug=gebiet(name, gruppe, config))
                _status(d, span)
                d.technik = technik(tech)
                laenge = zelle.xpath("following-sibling::td[2][contains(@class, 'text-right')]").xpath("normalize-space()").get()
                d.laenge_km = km(laenge)
                bild = zelle.xpath("following-sibling::td[3]//img/@alt").get()
                setze_schwierigkeit(d, PISTE.get(bild or "", bild))
                d.quelle_aktualisiert_at = stand
                d.nachtloipe = nacht(name)
                d.rohtext = f"{gruppe}: {span.attrib.get('class')}; {roh_name}; {laenge or ''}; {link or ''}".strip()
                ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis
