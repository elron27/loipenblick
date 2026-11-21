"""Wintersportbericht im Tramino-Baukasten, wie ihn Oberstdorf und Wertach zeigen (P38, Allgaeu, nur Test).

Befund (Schnappschuesse vom 20.11.2026, tests/fixtures/oberstdorf|wertach/2026-11-20/):
- Beide Orte nutzen das Tramino-CMS mit dem Modul "Wintersportbericht". Die Loipen stehen in einer Tabelle
  unter einer Ueberschrift "Loipen" (h4 in Oberstdorf, h2 in Wertach). Je Zeile ein Status-Symbol
  (img .../gfx/wsb/<symbol>.png), der Name als Link auf die Loipenseite, darunter grau ein Hinweis.
- Symbole laut Legende auf der Oberstdorfer Seite: offen = befahrbar, teilweise = bedingt befahrbar,
  zu = nicht befahrbar (nicht praepariert, zu wenig Schnee), achtung = Lawinensperre, keine = keine Angaben.
- Laenge: Oberstdorf in der letzten Spalte ("6,5 km"), Wertach nur im Hinweis ("ca. 5,8 km, mittel").
- Stand: Oberstdorf im Block "Infrastruktur" (div.stand "Stand: 10.11.2026 08:30 Uhr"), Wertach im
  Kopf ("Stand: 02.04.2026", der Bericht ruht bis zum Saisonstart). Keine Koordinaten.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_datum, parse_zahl, slugify
from loipen.models import Technik

SYMBOL = {"offen": "geöffnet", "teilweise": "teilweise geöffnet", "zu": "geschlossen",
          "achtung": "gesperrt", "keine": "keine angabe"}


def _text(sel) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


def technik(text: str) -> Technik:
    t = text.lower()
    k = "klassisch" in t
    s = "skating" in t or "freie" in t
    return Technik.BEIDES if k and s else Technik.KLASSISCH if k else Technik.SKATING if s else Technik.UNBEKANNT


class TraminoWsbAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        kopf = sel.xpath("//*[self::h2 or self::h3 or self::h4][normalize-space()='Loipen']")
        if not kopf:
            ergebnis.warnungen.append("Keine Loipen-Tabelle im Wintersportbericht gefunden, Seitenaufbau geaendert?")
            return ergebnis
        tabelle = kopf[0].xpath("following::table[1]")
        stand_text = (sel.css("#wege .stand::text").get() or sel.xpath(
            "//p[strong[starts-with(normalize-space(), 'Stand:')]]//text()").get() or "")
        stand = parse_datum(stand_text)
        gebiet_map = config.get("gebiet_map", {})
        for tr in tabelle.xpath(".//tr[td]"):
            zellen = tr.xpath("./td")
            if len(zellen) < 2:
                continue
            name = _text(zellen[1].xpath("./a")) if zellen[1].xpath("./a") else _text(zellen[1])
            if not name:
                continue
            hinweis = _text(zellen[1].xpath("./span"))
            src = zellen[0].xpath(".//img/@src").get(default="")
            symbol = (re.search(r"/wsb/(\w+)\.png", src) or [None, ""])[1]
            roh = SYMBOL.get(symbol, symbol)
            link = zellen[1].xpath("./a/@href").get()
            d = LoipenDaten(source_key=slugify(name), name=name, source_url=(link or url).strip(),
                            gebiet_slug=config["default_gebiet"])
            for teil, slug in gebiet_map.items():
                if teil.lower() in name.lower():
                    d.gebiet_slug = slug
            d.status, bekannt = normiere_zustand(roh)
            if not bekannt and symbol != "keine":
                d.unbekannte_begriffe.append(("status", symbol))
            d.status_rohtext = roh
            laenge = _text(zellen[2]) if len(zellen) > 2 else ""
            km = re.search(r"(\d+(?:,\d+)?)\s*km", laenge or hinweis)
            d.laenge_km = parse_zahl(km.group(1)) if km else None
            d.technik = technik(f"{name} {hinweis}")
            stufe = re.search(r"\b(leicht|mittel|schwer)\b", hinweis.lower())
            if stufe:
                d.schwierigkeit, _ = normiere_schwierigkeit(stufe.group(1))
            d.nachtloipe = True if "nacht" in name.lower() else None
            d.quelle_aktualisiert_at = stand
            d.rohtext = f"{symbol}; {hinweis}".strip("; ")
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Zeilen in der Loipen-Tabelle gefunden, Seitenaufbau geaendert?")
        return ergebnis
