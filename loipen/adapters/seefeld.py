"""Adapter H: Loipenbericht der Olympiaregion Seefeld, HTML (D18).

Befund des Schnappschusses vom 13.11.2026 (tests/fixtures/seefeld/2026-11-13/loipenbericht.html):
- Eine Seite (/de/loipenbericht.html) fuehrt alle Loipen von Seefeld, Leutasch, Moesern, Buchen,
  Scharnitz und Reith, je Gruppe eine h2-Ueberschrift und darunter Zeilen mit Status ("Geöffnet",
  "Geschlossen"), Name mit Link auf die Tourenseite, Stil-Symbolen (klassisch, skating),
  Schwierigkeit und "gespurt / gesamt" ("0 m / 2,80 km").
- Genauer als tirol.at sind die gespurten Kilometer. Ein Praeparierdatum und Koordinaten gibt es
  nicht; die Lage uebernimmt der Generator von der passenden tirol.at-Loipe (D18).
- Die Klassen sind CSS-Module mit wechselndem Vorsatz ("-ECo6W_state"); gesucht wird daher nur nach
  der Endung (_state, _label, _link, _difficulty, _textRight).
Gruppe -> Gebiet ueber config["gruppen"], Ort im Namen ueber config["gebiet_map"]. Gruppen unter
config["auslassen"] (z. B. die barrierefreien Varianten, die dieselben Loipen noch einmal nennen)
werden uebersprungen.
"""

import re
from urllib.parse import urljoin

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_zahl
from loipen.models import Technik

ENDET = "contains(concat(@class, ' '), '{0} ')"


def _km(text: str) -> float | None:
    """'2,80 km' -> 2.8, '500 m' -> 0.5, '0 m' -> 0.0."""
    zahl = parse_zahl(text)
    if zahl is None:
        return None
    return round(zahl / 1000, 2) if re.search(r"\d\s*m\b", text) and "km" not in text else zahl


def laengen(text: str) -> tuple[float | None, float | None]:
    """'0 m / 2,80 km' -> (0.0, 2.8): gespurt, gesamt. Ohne Schraegstrich nur gespurt."""
    teile = [t.strip() for t in (text or "").split("/")]
    gespurt = _km(teile[0]) if teile and teile[0] else None
    gesamt = _km(teile[1]) if len(teile) > 1 else None
    return gespurt, gesamt


class SeefeldAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/loipenbericht.html")
        sel = Selector(fetcher.get(url))
        gruppen = config.get("gruppen", {})
        auslassen = set(config.get("auslassen", []))
        gebiet_map = config.get("gebiet_map", {})
        gruppe = None
        gesehen: set[str] = set()
        zeilen = sel.xpath(
            "//main//h2 | //main//div[" + ENDET.format("_state") + "][not(contains(@class, 'Legend'))]")
        for el in zeilen:
            if el.root.tag == "h2":
                gruppe = el.xpath("normalize-space()").get()
                if gruppe not in gruppen and gruppe not in auslassen:
                    ergebnis.warnungen.append(f"Gruppe {gruppe!r} nicht in config.gruppen, Standardgebiet")
                continue
            if gruppe in auslassen:
                continue
            roh = el.xpath(".//p[" + ENDET.format("_label") + "]/text()").get(default="").strip()
            # Die Felder der Zeile folgen als Geschwister bis zum naechsten Status
            folgen = el.xpath("following-sibling::div[position() <= 4]")
            link = folgen.xpath(".//a[" + ENDET.format("_link") + "]")[:1]
            name = re.sub(r"\s+", " ", link.xpath("normalize-space()").get(default="")).strip()
            href = link.attrib.get("href") if link else None
            if not name or not href:
                continue
            key = href.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")
            if key in gesehen:
                continue
            gesehen.add(key)
            gebiet = next((g for wort, g in gebiet_map.items() if wort in name),
                          gruppen.get(gruppe, config["default_gebiet"]))
            d = LoipenDaten(source_key=key, name=name, source_url=urljoin(url, href), gebiet_slug=gebiet)
            d.status, bekannt = normiere_zustand(roh)
            if not bekannt:
                d.unbekannte_begriffe.append(("status", roh))
            d.status_rohtext = roh
            symbole = " ".join(folgen.xpath(".//i/@class").getall()[:4])
            klassisch, skating = "cross-country-classic" in symbole, "cross-country-skating" in symbole
            d.technik = (Technik.BEIDES if klassisch and skating else Technik.KLASSISCH if klassisch
                         else Technik.SKATING if skating else Technik.UNBEKANNT)
            schw = folgen.xpath("descendant-or-self::div[" + ENDET.format("_difficulty") + "]//p/text()").get(default="").strip()
            if schw:
                d.schwierigkeit, ok = normiere_schwierigkeit(schw)
                if not ok:
                    d.unbekannte_begriffe.append(("schwierigkeit", schw))
            laenge = folgen.xpath("descendant-or-self::div[" + ENDET.format("_textRight") + "]/p/text()").get(default="")
            d.gespurt_gesamt_km, d.laenge_km = laengen(laenge)
            d.nachtloipe = True if "nachtloipe" in name.lower() else None
            d.rohtext = f"{gruppe}: {roh}; {laenge.strip()}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis
