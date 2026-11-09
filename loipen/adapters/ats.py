"""Adapter A: Tourismus-System von tegernsee.com, bayrischzell.de und fischbachau.de (P1, P3).

Aufbau des Systems:
- Die Seite "Langlaufen" (mit Blaettern: /langlaufen/1, /langlaufen/2 ...) listet die Touren
  mit Stammdaten: Schwierigkeit, Distanz, Startpunkt, Rundtour. Daraus werden die Loipen
  entdeckt. Nicht-Loipen (Kegelbahn, Minigolf, Lama-Wanderung) stehen nicht in dieser Liste.
- Den Status liefern eigene Schneebericht-Seiten (/a-<name>-<n>) mit Loipenzustand, gespurten
  Kilometern und Stand. Sie sind von der Liste aus nicht verlinkt; ihre Adressen stehen als Daten
  in config/sources.yaml (statusseiten) und werden ueber den Namen den Touren zugeordnet.

Alle drei Orte laufen mit demselben Code, nur die Konfiguration unterscheidet sich.
"""

import logging
import re
from urllib.parse import urljoin, urlsplit

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import (
    normiere_schwierigkeit,
    normiere_zustand,
    parse_datum,
    parse_ja_nein,
    parse_zahl,
)
from loipen.fetcher import HttpFehler
from loipen.models import Technik

log = logging.getLogger("loipen.adapters.ats")

MAX_SEITEN = 20  # Schutz gegen endloses Blaettern
_BLAETTERN = re.compile(r"/langlaufen/(\d+)")
_STOPPWOERTER = {"loipe", "skatingloipe", "klassisch", "skating", "u", "und", "km"}


def _text(sel: Selector) -> str:
    return re.sub(r"\s+", " ", " ".join(sel.xpath(".//text()").getall())).strip()


def _slug(url: str) -> str:
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]


def namen_schluessel(name: str, ortswoerter: frozenset[str] = frozenset()) -> frozenset[str]:
    """Vergleichsschluessel fuer Namen: ohne Klammern, Zahlen, Fuellwoerter und Ortsnamen.

    'Ringseeloipe (4,2 km Skating u. klassisch)' und 'Ringseeloipe' ergeben dasselbe,
    'Nessler-Runde Bayrischzell' und 'Nessler Runde' auch.
    """
    name = re.sub(r"\([^)]*\)", " ", name.lower())
    name = name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    woerter = re.findall(r"[a-z]+", name)
    return frozenset(w for w in woerter if w not in _STOPPWOERTER and w not in ortswoerter)


def finde_gebiet(texte: list[str | None], gebiet_map: dict[str, str], default: str) -> str:
    """Ortsname in Startpunkt, Name oder Adresse -> Gebiet. Laengere Ortsnamen zuerst."""
    for text in texte:
        if not text:
            continue
        for ort in sorted(gebiet_map, key=len, reverse=True):
            if ort.lower() in text.lower():
                return gebiet_map[ort]
    return default


def lese_liste(html: str, base_url: str) -> tuple[list[dict], list[str]]:
    """Touren und Blaetter-Links einer Langlaufen-Seite."""
    sel = Selector(text=html)
    touren = []
    for art in sel.css("article.list_element, article.mapList__element"):
        link = art.css("h3 a::attr(href)").get()
        if not link:
            continue
        infos = {}
        for el in art.css(".listElement__infos__element"):
            label = " ".join(el.xpath("./text()").getall()).strip().rstrip(":").strip()
            infos[label] = (el.css("strong::text").get() or "").strip()
        zustaende = [_text(e) for e in art.css(".listElement__states__element")]
        lat, lng = art.attrib.get("data-js_lat"), art.attrib.get("data-js_lng")
        touren.append(
            {
                "url": urljoin(base_url + "/", link),
                "slug": _slug(link),
                "name": _text(art.css("h3 a")),
                "schwierigkeit": infos.get("Schwierigkeit"),
                "laenge_km": parse_zahl(infos.get("Distanz")),
                "startpunkt": infos.get("Startpunkt"),
                "rundkurs": True if "Rundtour" in zustaende else (False if "von A nach B" in zustaende else None),
                "lat": float(lat) if lat else None,
                "lon": float(lng) if lng else None,
            }
        )
    seiten = sorted({int(n) for n in _BLAETTERN.findall(" ".join(sel.css("a::attr(href)").getall()))})
    return touren, [str(n) for n in seiten]


def lese_statusseite(html: str) -> dict | None:
    """Felder einer Schneebericht-Seite. None, wenn die Seite keinen Loipenzustand enthaelt."""
    sel = Selector(text=html)
    infos: dict[str, str] = {}
    zeilen = []
    for el in sel.css(".textBlock__infos__element"):
        label = " ".join(el.xpath("./text()").getall()).strip().rstrip(":").strip()
        wert = (el.css("strong::text").get() or "").strip()
        infos[label] = wert
        zeilen.append(f"{label}: {wert}")
    if "Loipenzustand" not in infos:
        return None
    aktualisiert = _text(sel.css("p.updated"))
    if aktualisiert:
        zeilen.append(aktualisiert)
    lat, lng = sel.css("figure.contactMap__map::attr(data-js_lat)").get(), sel.css(
        "figure.contactMap__map::attr(data-js_lng)"
    ).get()
    return {
        "name": _text(sel.css("h1")),
        "infos": infos,
        "aktualisiert": aktualisiert,
        "ort": (sel.css("[itemprop=addressLocality]::text").get() or "").strip(),
        "lat": float(lat) if lat else None,
        "lon": float(lng) if lng else None,
        "rohtext": " | ".join(zeilen),
    }


def technik_aus(titel: str, klassisch_km: float | None, skating_km: float | None) -> Technik:
    """'(4,2 km Skating u. klassisch)' -> beides, '(10,9 km klassisch)' -> klassisch."""
    t = titel.lower()
    skating, klassisch = "skating" in t, "klassisch" in t
    if skating and klassisch:
        return Technik.BEIDES
    if skating:
        return Technik.SKATING
    if klassisch:
        return Technik.KLASSISCH
    return Technik.UNBEKANNT


class AtsAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        base_url = base_url.rstrip("/")
        default = config["default_gebiet"]
        gebiet_map = config.get("gebiet_map", {})

        touren = self._entdecke(base_url, config.get("list_path", "/langlaufen"), fetcher)
        status = self._lade_statusseiten(base_url, config.get("statusseiten", []), fetcher, ergebnis)

        # Status den Touren ueber den Namen zuordnen; Ortsnamen zaehlen dabei nicht
        ortswoerter = frozenset(
            w for text in [*gebiet_map, default.replace("-", " ")] for w in namen_schluessel(text)
        )
        je_schluessel: dict[frozenset, list[str]] = {}
        for slug, seite in status.items():
            je_schluessel.setdefault(namen_schluessel(seite["name"], ortswoerter), []).append(slug)

        benutzt: set[str] = set()
        for tour in touren:
            kandidaten = [
                s
                for s in je_schluessel.get(namen_schluessel(tour["name"], ortswoerter), [])
                if s not in benutzt
            ]
            seite = None
            if len(kandidaten) > 1 and tour["laenge_km"] is not None:
                # gleicher Name, mehrere Seiten (z. B. 'Sportplatzrunde'): die Laenge entscheidet,
                # zuerst die im Titel, dann die Gesamtlaenge auf der Seite
                laenge = tour["laenge_km"]
                passend = [s for s in kandidaten if self._laenge_im_titel(status[s]["name"]) == laenge]
                passend = passend or [
                    s for s in kandidaten if parse_zahl(status[s]["infos"].get("Loipenlänge gesamt")) == laenge
                ]
                kandidaten = passend or kandidaten
            if kandidaten:
                slug = kandidaten[0]
                benutzt.add(slug)
                seite = status[slug]
            ergebnis.loipen.append(
                self._baue(tour["url"], tour["slug"], tour, seite, gebiet_map, default)
            )

        # Status-Seiten ohne Tour in der Liste: Loipe aus den Daten der Seite
        for slug, seite in status.items():
            if slug in benutzt:
                continue
            log.info("Schneebericht-Seite %s (%s) hat keine Tour in der Liste", slug, seite["name"])
            ergebnis.loipen.append(self._baue(f"{base_url}/{slug}", slug, None, seite, gebiet_map, default))
        return ergebnis

    @staticmethod
    def _laenge_im_titel(titel: str) -> float | None:
        m = re.search(r"\(([\d,\.]+)\s*km", titel)
        return parse_zahl(m.group(1)) if m else None

    def _entdecke(self, base_url: str, list_path: str, fetcher: Fetcher) -> list[dict]:
        touren: dict[str, dict] = {}
        offen = ["0"]
        besucht: set[str] = set()
        while offen and len(besucht) < MAX_SEITEN:
            seite = offen.pop(0)
            if seite in besucht:
                continue
            besucht.add(seite)
            url = f"{base_url}{list_path}" + (f"/{seite}" if seite != "0" else "")
            neu, weitere = lese_liste(fetcher.get(url), base_url)
            for t in neu:
                touren.setdefault(t["slug"], t)
            offen += [s for s in weitere if s not in besucht]
        return list(touren.values())

    def _lade_statusseiten(self, base_url, slugs, fetcher, ergebnis) -> dict[str, dict]:
        gelesen = {}
        for slug in slugs:
            try:
                seite = lese_statusseite(fetcher.get(f"{base_url}/{slug}"))
            except HttpFehler as e:
                ergebnis.warnungen.append(f"Schneebericht-Seite {slug}: HTTP {e.status}")
                continue
            if seite is None:
                ergebnis.warnungen.append(f"Schneebericht-Seite {slug}: kein Loipenzustand gefunden")
                continue
            gelesen[slug] = seite
        return gelesen

    def _baue(self, url, key, tour, seite, gebiet_map, default) -> LoipenDaten:
        name = (tour or {}).get("name") or seite["name"]
        d = LoipenDaten(
            source_key=key,
            name=name,
            source_url=url,
            gebiet_slug=finde_gebiet(
                [(tour or {}).get("startpunkt"), name, (seite or {}).get("ort")], gebiet_map, default
            ),
        )
        if tour:
            d.rundkurs = tour["rundkurs"]
            d.laenge_km = tour["laenge_km"]
            d.startpunkt = tour["startpunkt"]
            d.lat, d.lon = tour["lat"], tour["lon"]
            d.schwierigkeit, bekannt = normiere_schwierigkeit(tour["schwierigkeit"])
            if not bekannt:
                d.unbekannte_begriffe.append(("schwierigkeit", tour["schwierigkeit"] or ""))
        if seite is None:
            return d  # Status bleibt unbekannt

        infos = seite["infos"]
        d.status, bekannt = normiere_zustand(infos.get("Loipenzustand"))
        d.status_rohtext = f"Loipenzustand: {infos.get('Loipenzustand', '')}"
        if not bekannt:
            d.unbekannte_begriffe.append(("zustand", d.status_rohtext))
        d.rohtext = seite["rohtext"]
        d.quelle_aktualisiert_at = parse_datum(seite["aktualisiert"])
        d.gespurt_gesamt_km = parse_zahl(infos.get("Loipenlänge gesamt gespurt"))
        d.gespurt_klassisch_km = parse_zahl(infos.get("Loipenlänge klassisch gespurt"))
        d.gespurt_skating_km = parse_zahl(infos.get("Loipenlänge Skating gespurt"))
        d.technik = technik_aus(seite["name"], d.gespurt_klassisch_km, d.gespurt_skating_km)
        d.nachtloipe = parse_ja_nein(infos.get("Nachtloipe"))
        if tour is None:
            d.laenge_km = parse_zahl(infos.get("Loipenlänge gesamt"))
            d.lat, d.lon = seite["lat"], seite["lon"]
            d.schwierigkeit, bekannt = normiere_schwierigkeit(infos.get("Schwierigkeitsgrad"))
            if not bekannt:
                d.unbekannte_begriffe.append(("schwierigkeit", infos.get("Schwierigkeitsgrad", "")))
        elif d.schwierigkeit.value == "unbekannt":
            d.schwierigkeit, _ = normiere_schwierigkeit(infos.get("Schwierigkeitsgrad"))
        if d.lat is None:
            d.lat, d.lon = seite["lat"], seite["lon"]
        return d
