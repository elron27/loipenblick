"""Adapter E: langlaufdorf.at (Faistenau und Hintersee bei Salzburg), HTML (P16).

Die Startseite zeigt je Loipe "<gespurt> von <gesamt> km" und "Zuletzt aktualisiert: TT.MM.JJJJ hh:mm".
Die Seite ist mit einem Baukasten gebaut, der Bloecke fuer Handy und Desktop doppelt fuehrt und
alte Bloecke nur versteckt (Klassen sppb-hidden-md/-lg/-sm/-xs zugleich). Versteckte Bloecke
werden uebersprungen, sonst stuenden Zahlen vergangener Winter auf der Seite (Schnappschuss 12.11.2026).
Status: 0 km gespurt = geschlossen, teilweise gespurt = eingeschraenkt, alles gespurt = offen.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import parse_datum, parse_zahl, slugify
from loipen.models import Status

VERSTECKT = ("sppb-hidden-md", "sppb-hidden-lg", "sppb-hidden-sm", "sppb-hidden-xs")
ZEILE = re.compile(r"^(?P<name>.+?)\s+(?P<gespurt>\d+(?:[.,]\d+)?)\s+von\s+(?P<gesamt>\d+(?:[.,]\d+)?)\s*km$")


def _versteckt(el) -> bool:
    for klasse in el.xpath("ancestor-or-self::*/@class").getall():
        if all(v in klasse.split() for v in VERSTECKT):
            return True
    return False


def bloecke(seite: str) -> list[str]:
    """Sichtbare Textbloecke der Seite, je Block ein bereinigter Text."""
    texte = []
    for el in Selector(seite).xpath('//div[contains(@class,"sppb-addon-content")]'):
        if el.xpath('.//div[contains(@class,"sppb-addon-content")]') or _versteckt(el):
            continue
        t = " ".join(x.strip() for x in el.xpath(".//text()[not(ancestor::style)]").getall() if x.strip())
        if t:
            texte.append(re.sub(r"\s+", " ", t))
    return texte


class LanglaufdorfAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/")
        texte = bloecke(fetcher.get(url))
        stand = next((parse_datum(t) for t in texte if t.startswith("Zuletzt aktualisiert")), None)
        if stand is None:
            ergebnis.warnungen.append("Kein Datum 'Zuletzt aktualisiert' gefunden")
        gesehen: set[str] = set()
        gebiet_map = config.get("gebiet_map", {})
        for t in texte:
            m = ZEILE.match(t)
            if not m:
                continue
            name = m["name"].strip()
            if name in gesehen:  # Handy- und Desktop-Block zeigen dieselbe Zeile
                continue
            gesehen.add(name)
            gespurt, gesamt = parse_zahl(m["gespurt"]), parse_zahl(m["gesamt"])
            gebiet = next((g for wort, g in gebiet_map.items() if wort in name), config["default_gebiet"])
            d = LoipenDaten(source_key=slugify(name), name=name, source_url=url, gebiet_slug=gebiet)
            d.laenge_km, d.gespurt_gesamt_km = gesamt, gespurt
            d.status = (Status.GESCHLOSSEN if not gespurt else Status.OFFEN if gespurt >= gesamt
                        else Status.EINGESCHRAENKT)
            d.status_rohtext = f"{m['gespurt']} von {m['gesamt']} km"
            d.quelle_aktualisiert_at = stand
            stamm = (config.get("stammdaten") or {}).get(name) or {}
            for feld in ("lat", "lon", "nachtloipe", "rundkurs"):
                if feld in stamm:
                    setattr(d, feld, stamm[feld])
            d.rohtext = t
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Zeile 'x von y km' gefunden, Seitenaufbau geaendert?")
        return ergebnis
