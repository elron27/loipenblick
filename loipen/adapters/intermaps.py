"""Adapter intermaps: Wintersportbericht der Tiroler Zugspitz Arena bei Intermaps, nur Testversion (P33, E-24).

Stefan am 19.11.2026: Die Zugspitz Arena zeigt ihren Loipenstatus nur ueber das eingebettete
Intermaps-Fenster; fuer die Testversion darf es gelesen werden (Ausnahme zu P17, nur mit
erlaubnis nur_test). Vor dem Livegang wird der Tourismusverband gefragt (docs/kontaktliste.md).

Befund des Schnappschusses vom 19.11.2026 (tests/fixtures/zugspitzarena/2026-11-19/snowreport.html):
- Kopf: "letzte Aktualisierung: 19.11.2026 13:20" und eine Tabelle SCHNEEHOEHE TAL/MITTE/BERG ("- cm" =
  keine Meldung).
- Abschnitt "Langlaufloipen" (h4) mit je Loipe einem div: Status-Bild images/icons/open.png, closed.png
  oder inprep.png ("in Vorbereitung"), Schwierigkeit als div.difficulty-easy/-medium/-hard und
  "<Ort> <Name> <Nummer> (leicht ) 1.4 km" als span.
- Keine Koordinaten; die Lage kommt ueber die Dubletten-Erkennung von tirol.at.
Gebiet ueber das erste Wort (Ort) aus config["gebiet_map"], sonst default_gebiet mit Warnung.
Die Schneehoehe Tal gilt fuer alle Loipen des Berichts, wenn sie als Zahl gemeldet ist.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import parse_datum
from loipen.adapters.tirolat import slug
from loipen.models import Schwierigkeit, Status

STATUS_BILD = {"open": (Status.OFFEN, "offen"), "closed": (Status.GESCHLOSSEN, "geschlossen"),
               # in Vorbereitung = heute noch nicht befahrbar
               "inprep": (Status.GESCHLOSSEN, "in Vorbereitung")}
SCHWIERIGKEIT = {"easy": Schwierigkeit.LEICHT, "medium": Schwierigkeit.MITTEL, "hard": Schwierigkeit.SCHWER,
                 "difficult": Schwierigkeit.SCHWER}
ZEILE = re.compile(r"^(?P<name>.*?)\s*\((?P<schw>[^)]*)\)\s*(?P<km>\d+(?:[.,]\d+)?)\s*km\s*$")


def _text(sel) -> str:
    return re.sub(r"\s+", " ", sel.xpath("normalize-space()").get(default="")).strip()


def schneehoehe_tal(sel: Selector) -> int | None:
    """'TAL - cm' -> None (keine Meldung), 'TAL 15 cm' -> 15."""
    zelle = sel.xpath("//td[span[normalize-space()='TAL']]")[:1]
    treffer = re.search(r"TAL\s*(\d+)\s*cm", _text(zelle)) if zelle else None
    return int(treffer.group(1)) if treffer else None


class IntermapsSchneeberichtAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        kopf = _text(sel.xpath("//b[contains(., 'letzte Aktualisierung')]/.."))
        stand = parse_datum(kopf)
        if stand is None:
            ergebnis.warnungen.append("Kein Stand (letzte Aktualisierung) gefunden")
        tal = schneehoehe_tal(sel)
        abschnitt = sel.xpath("//h4[normalize-space()='Langlaufloipen']/following-sibling::div[1]")
        gesehen: set[str] = set()
        for zeile in abschnitt.xpath("./div"):
            text = _text(zeile.css("span"))
            m = ZEILE.match(text)
            name = m.group("name").strip() if m else text
            if not name:
                continue
            key = slug(name)
            if key in gesehen:
                continue
            gesehen.add(key)
            ort = name.split()[0].split("-")[0]
            gebiet = (config.get("gebiet_map") or {}).get(ort)
            if gebiet is None:
                gebiet = config["default_gebiet"]
                ergebnis.warnungen.append(f"Loipe {name!r}: Ort {ort!r} ohne Gebiet, Standardgebiet {gebiet}")
            d = LoipenDaten(source_key=key, name=name, source_url=url, gebiet_slug=gebiet)
            bild = zeile.xpath("./img/@src").get(default="")
            art = re.search(r"/(\w+)\.png$", bild)
            if art and art.group(1) in STATUS_BILD:
                d.status, d.status_rohtext = STATUS_BILD[art.group(1)]
            else:
                d.unbekannte_begriffe.append(("status", bild))
            klasse = " ".join(zeile.css("div.difficulty-icon::attr(class)").getall())
            schw = re.search(r"difficulty-(easy|medium|hard|difficult)\b", klasse)
            if schw and schw.group(1) in SCHWIERIGKEIT:
                d.schwierigkeit = SCHWIERIGKEIT[schw.group(1)]
            if m:
                d.laenge_km = float(m.group("km").replace(",", "."))
            d.quelle_aktualisiert_at = stand
            d.schneehoehe_cm = tal
            d.rohtext = f"{d.status_rohtext or bild}; {text}; Stand {kopf}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Langlaufloipen im Bericht gefunden, Seitenaufbau geaendert?")
        return ergebnis
