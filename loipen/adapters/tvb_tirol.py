"""Adapter I, J, K: Loipenberichte Tiroler Tourismusverbaende, HTML (P22).

Befund der Schnappschuesse vom 13.11.2026 (tests/fixtures/recherche-tirol/2026-11-13/):

Achensee (contwise-Schneebericht, /de/live/schneebericht/):
- je Ort ein Block mit h3 und Zeitstempel ("13.11.2026 09:16"), darin die Aktivitaet
  data-filter="crosscountry" mit einer Zeile je Loipe: Status-Symbol (span.red / span.yellow /
  span.green), Schwierigkeit als title, Name ("A3 - Ortsloipe Achenkirch"), je Technik
  "0 / 10 km geöffnet" mit title "Klassisch" bzw. "Skaten".

Kufsteinerland (Skidata-Schneebericht, /de/schneebericht.html, Abschnitt .skidataCrossCountry):
- je Ort ein Block mit h3, Zeilen .entry (.name, .length "2500 m", .state stateN) und
  "Letztes Update am 11.11.2026 14:08:48". Was stateN heisst, steht im CSS der Seite selbst
  (.state1:after {content: "geöffnet";}); der Adapter liest die Zuordnung von dort.
- Die Seite fuehrt auch Bayrischzell und den Kaiserwinkl; config["orte_auslassen"] und
  config["regionen"] grenzen ein.

Kaiserwinkl (/de/langlaufen-tirol/geoeffnete-loipen.html):
- Liste aus CSS-Modul-Klassen: State_state... mit Text ("Geschlossen", gelb = bedingt nutzbar),
  danach Name ("Hochauloipe - Kössen Nr. 2"), Laenge ("9000 m") und Hoehenmeter.
  Ein Zeitstempel fuer die ganze Liste ("Zuletzt aktualisiert am 13.11.2026, 09:15 Uhr").

Alle drei nennen kein Praeparierdatum und keine Koordinaten. Der Zeitstempel ist der Stand der
Meldung (quelle_aktualisiert_at); die Lage uebernimmt der Generator von der passenden tirol.at-Loipe.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_datum, parse_zahl
from loipen.adapters.seefeld import _km
from loipen.models import Status, Technik

FARBE = {"red": "geschlossen", "yellow": "eingeschränkt", "orange": "eingeschränkt", "green": "geöffnet"}


def _text(sel) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


def _schluessel(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-")


def _gebiet(name: str, ort: str | None, config: dict) -> str:
    karte = config.get("gebiet_map", {})
    if ort and ort in karte:
        return karte[ort]
    return next((g for wort, g in karte.items() if wort in name), config["default_gebiet"])


def _status(d: LoipenDaten, roh: str) -> None:
    d.status, bekannt = normiere_zustand(roh)
    if not bekannt:
        d.unbekannte_begriffe.append(("status", roh))
    d.status_rohtext = roh


class AchenseeAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/live/schneebericht/")
        sel = Selector(fetcher.get(url))
        for block in sel.css(".jsSnowreportBody"):
            ort = block.css("h3::text").get(default="").strip()
            stand = parse_datum(block.xpath(".//div[contains(@class, '__head__date')]/text()").get())
            zeilen = block.xpath(".//*[@data-filter='crosscountry']/div[contains(concat(@class, ' '), '__activity__item ')]")
            for z in zeilen:
                kopf = z.css(".jsSnowreportHead")
                name = kopf.xpath(".//div[@class='p-2'][normalize-space()][last()]/text()").get(default="").strip()
                if not name:
                    continue
                d = LoipenDaten(source_key=_schluessel(f"{ort}-{name}"), name=name, source_url=url,
                                gebiet_slug=_gebiet(name, ort, config))
                farbe = kopf.xpath(".//span[i]/@class").get(default="").split()
                roh = next((FARBE[f] for f in farbe if f in FARBE), " ".join(farbe))
                _status(d, roh)
                schw = kopf.xpath(".//span[contains(@class, 'difficulty')]/@title").get()
                if schw:
                    d.schwierigkeit, ok = normiere_schwierigkeit(schw)
                    if not ok:
                        d.unbekannte_begriffe.append(("schwierigkeit", schw))
                je_technik = {}
                for sp in kopf.xpath(".//span[@title='Klassisch' or @title='Skaten']"):
                    werte = sp.xpath("following-sibling::span[1]/text()").get(default="")
                    # "0 / 4.5 km geöffnet": Dezimalpunkt, nicht Tausender
                    teile = [_km(t.strip().replace(".", ",") + " km") if t.strip() else None
                             for t in werte.replace("km geöffnet", "").split("/")]
                    je_technik[sp.attrib["title"]] = (teile + [None, None])[:2]
                k, s = je_technik.get("Klassisch"), je_technik.get("Skaten")
                d.technik = (Technik.BEIDES if k and s else Technik.KLASSISCH if k
                             else Technik.SKATING if s else Technik.UNBEKANNT)
                if k:
                    d.gespurt_klassisch_km = k[0]
                if s:
                    d.gespurt_skating_km = s[0]
                d.laenge_km = max([x[1] for x in (k, s) if x and x[1] is not None], default=None)
                d.quelle_aktualisiert_at = stand
                d.nachtloipe = True if "nacht" in name.lower() else None
                d.rohtext = f"{ort} ({stand}): {roh}; {je_technik}"
                ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis


def _zustaende_aus_css(html: str) -> dict[str, str]:
    """'.state1:after {content: "geöffnet";}' -> {"state1": "geöffnet"}"""
    return dict(re.findall(r'\.(state\d+):after\s*\{\s*content:\s*"([^"]+)"', html))


class SkidataAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/schneebericht.html")
        html = fetcher.get(url)
        zustaende = _zustaende_aus_css(html)
        sel = Selector(html)
        regionen = set(config.get("regionen", []))
        auslassen = set(config.get("orte_auslassen", []))
        for region in sel.css(".skidataCrossCountry > div"):
            klassen = set(region.attrib.get("class", "").split())
            if regionen and not regionen & klassen:
                continue
            for block in region.xpath("./div[div[@class='headline']]"):
                ort = block.css("h3::text").get(default="").strip()
                if ort in auslassen:
                    continue
                stand = parse_datum(block.css(".footer::text").get())
                for e in block.css(".entry"):
                    name = e.css(".name::text").get(default="").strip()
                    if not name:
                        continue
                    d = LoipenDaten(source_key=_schluessel(f"{ort}-{name}"), name=name, source_url=url,
                                    gebiet_slug=_gebiet(name, ort, config))
                    klasse = next((k for k in e.css(".state::attr(class)").get(default="").split()
                                   if re.fullmatch(r"state\d+", k)), "")
                    _status(d, zustaende.get(klasse, klasse))
                    laenge = e.css(".length::text").get(default="")
                    d.laenge_km = _km(laenge) if parse_zahl(laenge) is not None else None
                    d.quelle_aktualisiert_at = stand
                    d.nachtloipe = True if "beleuchtet" in name.lower() or "nacht" in name.lower() else None
                    d.rohtext = f"{ort} ({stand}): {klasse}={zustaende.get(klasse)}; {laenge}"
                    ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis


class KaiserwinklAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config.get("pfad", "/de/langlaufen-tirol/geoeffnete-loipen.html")
        sel = Selector(fetcher.get(url))
        stand = parse_datum(" ".join(sel.xpath("//div[starts-with(@class, 'Footer_footer')]//text()").getall()))
        for st in sel.xpath("//div[starts-with(@class, 'State_state')]"):
            folgen = st.xpath("following-sibling::div[position() <= 4]")
            if not folgen or not folgen[0].attrib.get("class", "").startswith("Title_title"):
                continue
            name = _text(folgen[0])
            if not name:
                continue
            d = LoipenDaten(source_key=_schluessel(name), name=name, source_url=url,
                            gebiet_slug=_gebiet(name, None, config))
            roh = st.xpath(".//p/text()").get(default="").strip()
            if not roh:
                symbol = st.xpath(".//i/@class").get(default="")
                roh = "eingeschränkt" if "Limited" in symbol or "Yellow" in symbol else symbol
            _status(d, roh)
            werte = [_text(f) for f in folgen[1:4]]
            laengen = [w for w in werte if re.fullmatch(r"[\d.,]+\s*k?m", w)]
            if laengen:
                d.laenge_km = _km(laengen[0])
            d.quelle_aktualisiert_at = stand
            d.nachtloipe = True if "nacht" in name.lower() else None
            d.rohtext = f"{roh}; {werte}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis


__all__ = ["AchenseeAdapter", "SkidataAdapter", "KaiserwinklAdapter", "Status"]
