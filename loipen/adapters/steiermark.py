"""Adapter P und Q: Loipenberichte der Steiermark, HTML (E-22, P30, P31).

Schladming-Dachstein (P30, www.schladming-dachstein.at/de/aktivitaeten/langlaufen/geoeffnete-loipen),
Befund des Schnappschusses vom 14.11.2026 (tests/fixtures/schladming/2026-11-14/geoeffnete-loipen.html):
- Reiter je Teilregion (a#<id>-tab mit Namen, div.tab-pane#<id>), darin eine Tabelle mit einer Zeile je Loipe.
  Der Reiter "all" (Uebersicht) wiederholt nur einzelne Loipen und wird uebersprungen.
- Je Zeile: td.bike-tour__status mit Symbol und aria-label "geöffnet" | "teilweise geöffnet" | "gesperrt"
  (leer = keine Meldung), Name als Link auf die Tourenseite, Langlauftechnik, Laenge ("5.7 km"),
  Hoehenmeter und ein optionaler Hinweistext ("Weitere Infos").
- Kopfzeile je Reiter "3/25" = offene / alle Loipen. Kein Datum, keine Koordinaten.
- Ramsau am Dachstein steht auch im tourinfra-Loipenmanager mit Stand (Rang 2); der Reiter wird ueber
  config["gruppen_auslassen"] uebersprungen, damit dieselbe Loipe nicht zweimal mit anderem Namen auftaucht.

steiermark.com (P31), Loipenbericht einer Region, z. B. Ausseerland
(/de/Ausseerland-Salzkammergut/Region/Winterfrische/Langlaufen/Loipenbericht-Ausseerland, ?page=2):
- Liste section.tour-teaser (Daten aus dem Tourenportal von Steiermark Tourismus): Name als Link
  (..._tour_<id>), Badge li.tour-teaser__badge mit icon-path-<zustand> und Text ("Geschlossen"),
  dazu Strecke ("5,0 km"), Start (Ort) und Schwierigkeit. Kein Datum, keine Koordinaten.
- Bekannte Badges laut CSS der Seite: icon-path-open, -partially-open, -open-not-prepared,
  -in-preparation, -closed. Teaser ohne Badge haben keine Meldung (unbekannt).
- Weitere Seiten ueber ?page=<n>; "<n> Ergebnisse" nennt die Gesamtzahl.
"""

import html as htmllib
import re

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand
from loipen.models import Status, Technik

TECHNIK = {"klassisch": Technik.KLASSISCH, "skating": Technik.SKATING, "klassisch & skating": Technik.BEIDES}
# Badges von steiermark.com (Klasse icon-path-<x>); der Text der Seite wird zusaetzlich gelesen.
BADGE = {"open": Status.OFFEN, "partially-open": Status.EINGESCHRAENKT, "open-not-prepared": Status.EINGESCHRAENKT,
         "in-preparation": Status.GESCHLOSSEN, "closed": Status.GESCHLOSSEN}


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _km(text: str | None) -> float | None:
    """'5.7 km' (Schladming, Punkt) oder '5,0 km' (steiermark.com, Komma) -> 5.7 / 5.0."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*km", text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _schluessel(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-")


def _gebiet(name: str, ort: str | None, config: dict) -> str:
    karte = config.get("gebiet_map", {})
    if ort and ort in karte:
        return karte[ort]
    return next((g for wort, g in karte.items() if wort in name), config["default_gebiet"])


def _status(d: LoipenDaten, roh: str) -> None:
    if not roh:
        d.status = Status.UNBEKANNT
        return
    d.status, bekannt = normiere_zustand(roh)
    if not bekannt:
        d.unbekannte_begriffe.append(("status", roh))
    d.status_rohtext = roh


def schladming_reiter(seite: str) -> list[tuple[str, str]]:
    """[(Name des Reiters, HTML des Reiters)] ohne die Uebersicht."""
    namen = {a: _text(b) for a, b in re.findall(r'id="(\w+)-tab"\s+href="#\w+".*?>(.*?)</a>', seite, re.S)}
    start = [(m.start(), m.group(1)) for m in re.finditer(r'class="tab-pane[^"]*"\s+id="(\w+)"', seite)]
    reiter = []
    for i, (pos, rid) in enumerate(start):
        ende = start[i + 1][0] if i + 1 < len(start) else len(seite)
        if rid != "all":
            reiter.append((namen.get(rid, rid), seite[pos:ende]))
    return reiter


class SchladmingDachsteinAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        url = base_url.rstrip("/") + config.get("pfad", "/de/aktivitaeten/langlaufen/geoeffnete-loipen")
        return self.run_seite(fetcher.get(url), url, config, base_url)

    def run_seite(self, seite: str, url: str, config: dict, base_url: str = "") -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        auslassen = set(config.get("gruppen_auslassen", []))
        reiter = schladming_reiter(seite)
        if not reiter:
            ergebnis.warnungen.append("Schladming-Dachstein: keine Reiter mit Loipen gefunden, Seitenaufbau geaendert?")
            return ergebnis
        gesehen: set[str] = set()
        for gruppe, teil in reiter:
            if gruppe in auslassen:
                continue
            zaehler = re.search(r"<h5[^>]*>\s*(\d+)\s*/\s*(\d+)\s*</h5>", teil)
            zeilen = re.split(r'<tr class="table-area__table-row[^"]*">', teil)[1:]
            if zaehler and int(zaehler.group(2)) != len(zeilen):
                ergebnis.warnungen.append(
                    f"Schladming-Dachstein: {gruppe} nennt {zaehler.group(2)} Loipen, gelesen {len(zeilen)}")
            for z in zeilen:
                link = re.search(r'<a href="([^"]+)"[^>]*title-link[^>]*>(.*?)</a>', z, re.S)
                if not link:
                    continue
                name = _text(link.group(2))
                key = _schluessel(name)
                if key in gesehen:
                    continue
                gesehen.add(key)
                feld = {_text(a): _text(b) for a, b in re.findall(
                    r'item-label">(.*?)</span>\s*<span class="table-area__table-item-content">(.*?)</span>', z, re.S)}
                symbol = re.search(r'bike-tour__status">(.*?)</td>', z, re.S)
                roh = ""
                if symbol:
                    m = re.search(r'aria-label="([^"]+)"', symbol.group(1))
                    roh = m.group(1) if m else ""
                hinweis = re.search(r'popover-content__wrapper">(.*?)</div>', z, re.S)
                ziel = link.group(1)
                d = LoipenDaten(source_key=key, name=name,
                                source_url=(base_url.rstrip("/") + ziel) if ziel.startswith("/") else ziel,
                                gebiet_slug=config.get("gruppen", {}).get(gruppe) or _gebiet(name, None, config))
                _status(d, roh)
                d.technik = TECHNIK.get(feld.get("Langlauftechnik", "").lower(), Technik.UNBEKANNT)
                d.laenge_km = _km(feld.get("Länge"))
                d.nachtloipe = True if re.search(r"nacht", name, re.I) else None
                text = _text(hinweis.group(1)) if hinweis else ""
                d.rohtext = "; ".join(x for x in (gruppe, roh or "keine Meldung", text) if x)
                ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Schladming-Dachstein: keine Loipenzeilen gefunden, Seitenaufbau geaendert?")
        return ergebnis


def steiermark_teaser(seite: str) -> list[dict]:
    """Je Teaser Name, Link, Badge (Klasse, Text) und die Infozeilen (Strecke, Start, Schwierigkeit)."""
    teaser = []
    for t in re.split(r'<section class="tour-teaser', seite)[1:]:
        link = re.search(r'tour-teaser__content__title">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', t, re.S)
        if not link:
            continue
        badge = re.search(r'icon-path-([a-z-]+)[^>]*></span>\s*<span>([^<]*)</span>', t)
        info = {a.strip(): _text(b) for a, b in re.findall(
            r'info-item__title d-block fz-sm">([^<]*)</span>\s*<span[^>]*></span>([^<]*)<', t)}
        teaser.append({"name": _text(link.group(2)), "href": link.group(1),
                       "badge": badge.group(1) if badge else None,
                       "badge_text": _text(badge.group(2)) if badge else "", **info})
    return teaser


class SteiermarkLoipenberichtAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        gesehen: set[str] = set()
        erwartet = None
        basis = base_url.rstrip("/") + config["pfad"]
        for n in range(1, int(config.get("seiten", 1)) + 1):
            url = basis if n == 1 else f"{basis}?page={n}"
            seite = fetcher.get(url)
            teaser = steiermark_teaser(seite)
            if n == 1:
                gesamt = re.search(r"(\d+)\s+Ergebnisse", seite)
                erwartet = int(gesamt.group(1)) if gesamt else None
            if not teaser:
                if n == 1:
                    ergebnis.warnungen.append("steiermark.com: keine Loipen in der Liste, Seitenaufbau geaendert?")
                break
            for t in teaser:
                key = _schluessel(t["name"])
                if key in gesehen:
                    continue
                gesehen.add(key)
                href = t["href"]
                d = LoipenDaten(source_key=key, name=t["name"],
                                source_url=(base_url.rstrip("/") + href) if href.startswith("/") else href,
                                gebiet_slug=_gebiet(t["name"], t.get("Start"), config))
                if t["badge"]:
                    d.status = BADGE.get(t["badge"], Status.UNBEKANNT)
                    d.status_rohtext = t["badge_text"] or t["badge"]
                    if t["badge"] not in BADGE:
                        d.unbekannte_begriffe.append(("status", t["badge"]))
                d.laenge_km = _km(t.get("Strecke"))
                if t.get("Schwierigkeit"):
                    d.schwierigkeit, _ = normiere_schwierigkeit(t["Schwierigkeit"])
                d.startpunkt = t.get("Start")
                d.nachtloipe = True if re.search(r"nacht|flutlicht", t["name"], re.I) else None
                d.rohtext = "; ".join(x for x in (t["badge_text"] or "keine Meldung", t.get("Start"), t["name"]) if x)
                ergebnis.loipen.append(d)
        if erwartet and len(ergebnis.loipen) < erwartet:
            ergebnis.warnungen.append(
                f"steiermark.com: {erwartet} Ergebnisse genannt, {len(ergebnis.loipen)} gelesen (Seitenzahl erhoehen?)")
        return ergebnis
