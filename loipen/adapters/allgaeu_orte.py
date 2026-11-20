"""Loipenberichte weiterer Allgaeuer Ortsseiten (P36, nur Test): Kleinwalsertal, Fuessen, Hoernerdoerfer.

Befund (Schnappschuesse vom 20.11.2026):
- Kleinwalsertal (kleinwalsertal.com/de/kleinwalsertal-live/bergsportbericht-kleinwalsertal/loipen-aktiv-...):
  Liste li.area--status-report--item, Name in div.h6 (z. B. "Schwarzwasserloipe: Egg-Runde [kl]"), Status als
  Text (span ...-status-text "Geschlossen") und Klasse icon--closed. [kl] = klassisch, [sk] = Skating.
  Laenge und Schwierigkeit stehen nur im Info-Fenster je Loipe (/de/reportObjectModal/<nr>), das der Adapter
  nicht abruft. Kein Stand, keine Koordinate.
- Fuessen (fuessen.de/outdoor/aktiver-winter/langlauf/): Block "Aktuelle Loipen-Info" mit je einem Absatz
  "<Name> (<Kuerzel>) <Status>", z. B. "Weissensee-Loipen (W1, W2) geschlossen". Kein Stand, keine Laenge.
- Hoernerdoerfer: hoernerdoerfer.de bettet den Schneebericht von Intermaps ein
  (sdds4.intermaps.com/hoernerdoerfer_srm/hoernerdoerfer.aspx). Abschnitt "Loipen - Klassisch & Skating",
  je Ort ein h3, je Loipe div.list-item mit Status-Symbol icon_set/<nr>.png, Name und Laenge
  (span.item-right "1,70 km"). Legende im Fuss: 169 offen, 94 geschlossen. Stand im Kopf
  ("Letzte Aktualisierung: 20.11.2026 - 08:01"). Intermaps nur in der Testversion (P17-Ausnahme).
- Isny (isny.de/freizeit-urlaub/wintersport/schneehoehen-loipenbericht.html, Tramino): je Loipe div.wsbbox mit
  span.status[data-state] ("closed"), Name als a.title, Hinweis in p ("Nur Skatingloipe am 3.2. frisch gespurt."),
  Zeilen Laenge (m), Technik, Schwierigkeit (einfach/mittel/schwer), Zustand, Zuletzt gespurt (im November leer).
  Isny und Maierhoefen gehoeren zum selben Netz.
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_datum, parse_zahl, slugify
from loipen.models import Technik


def _text(sel) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


def _technik_kuerzel(name: str) -> Technik:
    k = re.search(r"\[([^\]]+)\]", name)
    teile = k.group(1).lower() if k else ""
    kl, sk = "kl" in teile, "sk" in teile
    return Technik.BEIDES if kl and sk else Technik.KLASSISCH if kl else Technik.SKATING if sk else Technik.UNBEKANNT


def _status(d: LoipenDaten, roh: str) -> None:
    d.status, bekannt = normiere_zustand(roh)
    if roh and not bekannt:
        d.unbekannte_begriffe.append(("status", roh))
    d.status_rohtext = roh or None


class KleinwalsertalAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        gesehen = set()
        for li in sel.css("li.area--status-report--item"):
            art = _text(li.css(".area--status-report--item-info"))
            if art and art.lower() != "loipe":
                continue
            kopf = li.css(".area--status-report--item-name .h6")
            name = re.sub(r"\s+", " ", " ".join(kopf.xpath("./text()").getall())).strip()
            if not name:
                continue
            roh = _text(kopf.css(".area--status-report--item-status-text")) or (
                li.css(".area--status-report--item-status i::attr(aria-label)").get(default="")
                .replace("Status:", "").strip())
            modal = li.css("button::attr(hx-get)").get(default="")
            nummer = (re.search(r"/(\d+)$", modal) or [None, None])[1]
            schluessel = f"kwt-{nummer}" if nummer else slugify(name)
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            d = LoipenDaten(source_key=schluessel, name=name, source_url=url, gebiet_slug=config["default_gebiet"])
            _status(d, roh)
            d.technik = _technik_kuerzel(name)
            netz = name.split(":")[0] if ":" in name else None
            d.startpunkt = netz
            d.rohtext = f"{roh}; {name}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen im Bergsportbericht gefunden, Seitenaufbau geaendert?")
        return ergebnis


_FUESSEN_ZEILE = re.compile(r"^(?P<name>.+?)\s*\((?P<kuerzel>[^)]+)\)\s*(?P<status>.+)$")


class FuessenAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        block = sel.xpath("//h3[normalize-space()='Aktuelle Loipen-Info']/ancestor::div[contains(@class,"
                          "'contentelement-inner')][1]//div[contains(@class,'contentelement-text')]//p")
        gebiet_map = config.get("gebiet_map", {})
        for p in block:
            zeile = _text(p)
            m = _FUESSEN_ZEILE.match(zeile)
            if not m:
                if zeile:
                    ergebnis.warnungen.append(f"Zeile nicht verstanden: {zeile}")
                continue
            name, kuerzel, roh = m.group("name").strip(), m.group("kuerzel").strip(), m.group("status").strip()
            d = LoipenDaten(source_key=slugify(kuerzel), name=f"{name} ({kuerzel})", source_url=url,
                            gebiet_slug=config["default_gebiet"])
            for teil, slug in gebiet_map.items():
                if teil.lower() in name.lower():
                    d.gebiet_slug = slug
            _status(d, roh)
            d.rohtext = zeile
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Aktuelle Loipen-Info gefunden, Seitenaufbau geaendert?")
        return ergebnis


class IntermapsListeAdapter:
    """Schneebericht von Intermaps im Listen-Layout (srm), z. B. Hoernerdoerfer."""

    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        legende = {}
        for img in sel.css(".footer-legend img"):
            nr = (re.search(r"/(\d+)\.png", img.attrib.get("src", "")) or [None, None])[1]
            text = img.xpath("following-sibling::span[1]/text()").get(default="").strip()
            if nr and text:
                legende[nr] = text
        stand = parse_datum((sel.css(".last-act::text").get() or "").replace(" - ", " "))
        gebiet_map = config.get("gebiet_map", {})
        for kopf in sel.xpath("//div[contains(@class,'section-heading')][h2[starts-with(normalize-space(), 'Loipen')]]"):
            h2 = _text(kopf.xpath("./h2"))
            liste = kopf.xpath("following-sibling::div[contains(@class,'list')][1]")
            ort = ""
            for knoten in liste.xpath("./h3 | ./div[contains(@class,'list-item')]"):
                if knoten.root.tag == "h3":
                    ort = _text(knoten)
                    continue
                name = _text(knoten.xpath("./span[not(contains(@class,'item-right'))]"))
                if not name:
                    continue
                nr = (re.search(r"icon_set/(\d+)\.png", knoten.xpath("./img[1]/@src").get(default="")) or [None, ""])[1]
                roh = legende.get(nr, nr)
                d = LoipenDaten(source_key=slugify(f"{ort} {name}"), name=name, source_url=url,
                                gebiet_slug=gebiet_map.get(ort, config["default_gebiet"]))
                _status(d, roh)
                d.laenge_km = parse_zahl(_text(knoten.xpath("./span[contains(@class,'item-right')]")))
                d.technik = Technik.BEIDES if "klassisch & skating" in h2.lower() else (
                    Technik.KLASSISCH if "klassisch" in h2.lower() else Technik.UNBEKANNT)
                d.startpunkt = ort or None
                d.nachtloipe = True if "flutlicht" in name.lower() or "nacht" in name.lower() else None
                d.quelle_aktualisiert_at = stand
                d.rohtext = f"{nr} {roh}; {ort}"
                ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Kein Loipen-Abschnitt im Intermaps-Bericht gefunden, Seitenaufbau geaendert?")
        return ergebnis


def _zeile(box, titel: str) -> str:
    return _text(box.xpath(f".//div[contains(@class,'line')][starts-with(normalize-space(), '{titel}')]/span"))


class TraminoBoxAdapter:
    """Loipenbericht als Kaesten (div.wsbbox), z. B. Isny."""

    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        gebiet_map = config.get("gebiet_map", {})
        for box in sel.css("div.wsbbox"):
            name = _text(box.css("a.title"))
            if not name:
                continue
            roh = box.css("span.status::attr(data-state)").get(default="") or _text(box.css("span.status"))
            d = LoipenDaten(source_key=slugify(name), name=name, source_url=url, gebiet_slug=config["default_gebiet"])
            for teil, slug in gebiet_map.items():
                if teil.lower() in name.lower():
                    d.gebiet_slug = slug
            _status(d, roh)
            meter = parse_zahl(_zeile(box, "Länge"))
            d.laenge_km = round(meter / 1000, 1) if meter else None
            tech = _zeile(box, "Technik").lower()
            d.technik = (Technik.BEIDES if "klassisch" in tech and "skating" in tech else Technik.KLASSISCH
                         if "klassisch" in tech else Technik.SKATING if "skating" in tech else Technik.UNBEKANNT)
            stufe = _zeile(box, "Schwierigkeit")
            d.schwierigkeit, bekannt = normiere_schwierigkeit("leicht" if stufe == "einfach" else stufe)
            if stufe and not bekannt:
                d.unbekannte_begriffe.append(("schwierigkeit", stufe))
            d.quelle_aktualisiert_at = parse_datum(_zeile(box, "Zuletzt gespurt"))
            hinweis = _text(box.xpath("./p"))
            d.rohtext = f"{roh}; {hinweis}".strip("; ")
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen-Kaesten gefunden, Seitenaufbau geaendert?")
        return ergebnis
