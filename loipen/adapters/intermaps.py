"""Adapter: Wintersportbericht von Intermaps (SDDS), wie ihn Innsbruck Tourismus einbettet (P32, E-24).

Befund des Schnappschusses vom 19.11.2026 (tests/fixtures/innsbruck/2026-11-19/):
- innsbruck.info/skifahren/service/schneebericht.html bettet per iframe
  sdds4.intermaps.com/innsbruck_new/lebensraum_innsbruck.aspx?lang=de ein; die Seite ist reines HTML.
- Kopf: "Letzte Aktualisierung 19.11.2026 15:46:31" (Stand der ganzen Meldung).
- Abschnitt div.row.infrastructure mit h2 "Langlaufloipen (0 von 40 geöffnet)". Darin abwechselnd ein
  Ortsblock (b = Ort, Telefon, Temperatur) und je Loipe div.object mit Status-Symbol (img .../<nr>.png)
  und span = Name, z. B. "Rundloipe Gries (klassisch & skating)".
- Was die Symbolnummer heisst, steht in der Legende derselben Seite (169 offen, 94 geschlossen,
  126 in Vorbereitung, 412 offen (nicht frisch präpariert)); der Adapter liest die Zuordnung von dort.
Keine Laenge, keine Koordinate, kein Praeparierdatum je Loipe.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_zustand, parse_datum
from loipen.models import Status, Technik

# Legendenwoerter, die die allgemeine Tabelle (normalisierung.ZUSTAND) nicht kennt
LEGENDE = {
    "in vorbereitung": Status.GESCHLOSSEN,
    "offen (nicht frisch präpariert)": Status.EINGESCHRAENKT,
}


def _symbol(src: str) -> str:
    treffer = re.search(r"/(\d+)\.png", src or "")
    return treffer.group(1) if treffer else ""


def _schluessel(text: str) -> str:
    text = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def legende(sel: Selector) -> dict[str, str]:
    """{"169": "offen", "94": "geschlossen", ...} aus dem Legendenblock."""
    karte = {}
    for img in sel.css(".legend img"):
        text = img.xpath("following-sibling::text()[1]").get(default="").strip()
        if text:
            karte[_symbol(img.attrib.get("src", ""))] = text
    return karte


def technik(name: str) -> Technik:
    n = name.lower()
    k, s = "klassisch" in n, "skating" in n
    return Technik.BEIDES if k and s else Technik.KLASSISCH if k else Technik.SKATING if s else Technik.UNBEKANNT


class IntermapsAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        kopf = " ".join(sel.css(".header-title ::text").getall())
        treffer = re.search(r"Aktualisierung\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})", kopf)
        stand = parse_datum(f"{treffer.group(1)} {treffer.group(2)}") if treffer else None
        symbole = legende(sel)
        gebiet_map = config.get("gebiet_map", {})
        for abschnitt in sel.css("div.infrastructure"):
            if not abschnitt.css("h2::text").get(default="").strip().startswith("Langlaufloipen"):
                continue
            ort = None
            for block in abschnitt.css(".cols-3 > div"):
                if "object" not in block.attrib.get("class", "").split():
                    ort = block.css("b::text").get(default="").strip() or ort
                    continue
                name = re.sub(r"\s+", " ", block.css("span::text").get(default="")).strip()
                if not name:
                    continue
                d = LoipenDaten(source_key=_schluessel(f"{ort}-{name}"), name=name, source_url=url,
                                gebiet_slug=gebiet_map.get(ort, config["default_gebiet"]), startpunkt=ort)
                roh = symbole.get(_symbol(block.css("img::attr(src)").get()), "")
                d.status, bekannt = normiere_zustand(roh) if roh else (Status.UNBEKANNT, False)
                if not bekannt:
                    d.status = LEGENDE.get(roh.lower(), Status.UNBEKANNT)
                    if roh.lower() not in LEGENDE:
                        d.unbekannte_begriffe.append(("status", roh or "Symbol ohne Legende"))
                d.status_rohtext = roh or None
                d.technik = technik(name)
                d.nachtloipe = True if "nacht" in name.lower() else None
                d.quelle_aktualisiert_at = stand
                d.rohtext = f"{ort} ({stand}): {roh}"
                ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Langlaufloipen im Intermaps-Bericht gefunden, Seitenaufbau geaendert?")
        if stand is None:
            ergebnis.warnungen.append("Kein Stand 'Letzte Aktualisierung' im Intermaps-Bericht gefunden")
        return ergebnis


__all__ = ["IntermapsAdapter"]
