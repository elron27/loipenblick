"""Adapter D: Landesportal tirol.at (Tirol Werbung, System Nefos), HTML (P14, P18, U30).

Befund der Schnappschuesse vom 12.11.2026 (tests/fixtures/tirol/2026-11-12/):
- Die Loipenliste enthaelt im Attribut data-markers eine JSON-Liste aller Tiroler Loipen
  (Name, Koordinate, Kennung addressbase_<n>). Ein Abruf reicht fuer ganz Tirol.
- Mit dem Filter addressbaseOpened=OPEN enthaelt dieselbe Liste nur die geoeffneten Loipen.
  tirol.at kennt nur geoeffnet/gesperrt und kein Praeparierdatum (Blindspot 1): eine Loipe, die
  nicht als geoeffnet gemeldet ist, gilt als geschlossen; das Datum bleibt leer (U30).
- Laenge, Schwierigkeit, Stile, Beleuchtung, Startpunkt und Tourismusverband stehen nur auf der
  Detailseite. Je Lauf werden hoechstens config["details_pro_lauf"] Detailseiten im Wechsel
  abgerufen; Stammdaten bleiben in der Datenbank, bis eine neue Seite sie aendert.
- Die GPX-Strecken liegen auf tirol.mapservices.eu und sind dort per robots.txt gesperrt (P17):
  Tiroler Loipen haben nur einen Startpunkt, keinen Streckenverlauf.

Welche Loipen uebernommen werden, steht in sources.yaml: Jede Loipe gehoert zum naechsten Gebiet
aus config["gebiete"] (Koordinaten aus gebiete.yaml, hier als config["gebiet_punkte"]), wenn es
naeher als config["radius_km"] liegt. Eine neue Region = neue Gebiete in beiden Dateien (P14 AK 2).
"""

import html as htmllib
import json
import logging
import math
import re
import time

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand, parse_zahl, slugify
from loipen.models import Status, Technik

log = logging.getLogger("loipen.adapters.tirolat")

LISTE = "/aktivitaeten/sport/langlaufen/loipen"
OFFEN_FILTER = "addressbaseOpened%5B209%5D%5B%5D=OPEN"
# Eintraege der Karte, die keine Loipen sind (Skischulen, Verleih, Geschaefte)
KEINE_LOIPE = re.compile(r"schule|rental|store|verleih|shop|sport mit style", re.I)

TECHNIK = {
    "klassisch": Technik.KLASSISCH,
    "skating": Technik.SKATING,
    "skating / klassisch": Technik.BEIDES,
    "klassisch / skating": Technik.BEIDES,
}


def slug(titel: str) -> str:
    """Adresse der Detailseite wie bei tirol.at: 'KU1 Weissach I' -> 'ku1-weissach-i'.

    Bei gleichen Namen haengt tirol.at -2, -3 an; das laesst sich nicht ableiten. Dann prueft der
    Adapter die Kennung auf der Seite und meldet eine Warnung; config["slugs"] legt den Pfad fest.
    Pfade aus den mitgelieferten Listeneintraegen (data-ident + Link) gehen vor.
    """
    return slugify(titel)


def listen_pfade(seite: str) -> dict[str, str]:
    """Kennung -> Pfad der Detailseite aus den Listeneintraegen einer Listenseite."""
    pfade = {}
    for ident, pfad in re.findall(
            r'<article class="list__article[^"]*" data-ident="([^"]+)"[\s\S]*?href="[^"]*/loipen/([^"/?#]+)"', seite):
        pfade.setdefault(ident, pfad)
    return pfade


def marker(seite: str) -> list[dict]:
    treffer = re.search(r'data-markers="([^"]*)"', seite)
    if not treffer:
        raise ValueError("tirol.at: Liste ohne data-markers, Seitenaufbau geaendert?")
    return json.loads(htmllib.unescape(treffer.group(1)))


def _abstand_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * math.cos(math.radians(a[0])))


def laenge_km(text: str) -> float | None:
    """'2,5 km' -> 2.5, '700 m' -> 0.7 (kurze Loipen gibt tirol.at in Metern an)."""
    zahl = parse_zahl(text)
    if zahl is None:
        return None
    return round(zahl / 1000, 2) if re.search(r"\d\s*m\b", text) and "km" not in text else zahl


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_detail(seite: str) -> dict:
    """Felder einer Detailseite. Fehlt ein Feld, fehlt der Schluessel."""
    d: dict = {}
    if m := re.search(r"data-openinghours-text>([^<]*)<", seite):
        d["status"] = _text(m.group(1))
    if m := re.search(r'Schwierigkeitsgrad:</span>([^<]*)<', seite):
        d["schwierigkeit"] = _text(m.group(1))
    if m := re.search(r'Streckenlänge:</span>([^<]*)<', seite):
        d["laenge_km"] = laenge_km(m.group(1))
    for feld, kopf in (("startpunkt", "Ausgangspunkt"), ("endpunkt", "Endpunkt"), ("stile", "Stile")):
        if m := re.search(rf'<h3 class="headline">{kopf}</h3><div class="text">([\s\S]*?)</div>', seite):
            d[feld] = _text(m.group(1))
    merkmale = []
    for block in re.findall(r'<section class="factsCheckmarks">([\s\S]*?)</section>', seite):
        merkmale += [_text(x) for x in re.findall(r'<li class="listItem">([\s\S]*?)</li>', block)]
    d["merkmale"] = merkmale
    if m := re.search(r"Quelle: ([^<]*)<", seite):
        d["verband"] = _text(m.group(1))
    if m := re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', seite):
        try:
            ld = json.loads(m.group(1))
            geo = ld.get("geo") or {}
            if geo.get("latitude") is not None:
                d["lat"], d["lon"] = float(geo["latitude"]), float(geo["longitude"])
            if ld.get("identifier") is not None:
                d["kennung"] = str(ld["identifier"])
            if ld.get("url"):
                d["url"] = ld["url"]
        except (ValueError, TypeError):
            pass
    return d


class TirolAtAdapter:
    def __init__(self, uhr=time.time):
        self._uhr = uhr

    def _auswahl(self, n: int, je_lauf: int) -> range:
        """Welche Detailseiten in diesem Lauf drankommen: Bloecke im Wechsel nach Stunde."""
        if n == 0 or je_lauf <= 0:
            return range(0)
        bloecke = math.ceil(n / je_lauf)
        block = int(self._uhr() // 3600) % bloecke
        return range(block * je_lauf, min(n, (block + 1) * je_lauf))

    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        basis = base_url.rstrip("/")
        liste_url = basis + config.get("liste_pfad", LISTE)
        liste = fetcher.get(liste_url)
        offen_seite = fetcher.get(f"{liste_url}?{config.get('offen_filter', OFFEN_FILTER)}")
        alle = marker(liste)
        offen = {m["ident"] for m in marker(offen_seite)}
        bekannte_pfade = {**listen_pfade(liste), **listen_pfade(offen_seite), **(config.get("slugs") or {})}

        punkte = {s: tuple(p) for s, p in (config.get("gebiet_punkte") or {}).items()}
        erlaubt = [s for s in config.get("gebiete", []) if s in punkte]
        for s in config.get("gebiete", []):
            if s not in punkte:
                ergebnis.warnungen.append(f"Gebiet {s} ohne Koordinate in gebiete.yaml, nicht zugeordnet")
        radius = float(config.get("radius_km", 5))

        gewaehlt: list[tuple[dict, str]] = []
        for m in alle:
            titel = re.sub(r"\s+", " ", m.get("title") or "").strip()
            if not titel or not m.get("ident") or not m.get("latlng"):
                continue
            if not (m.get("icon") or {}).get("id", "").startswith("ski-langlauf") or KEINE_LOIPE.search(titel):
                continue
            pos = (float(m["latlng"][0]), float(m["latlng"][1]))
            naechstes = min(erlaubt, key=lambda s: _abstand_km(pos, punkte[s]), default=None)
            if naechstes and _abstand_km(pos, punkte[naechstes]) <= radius:
                gewaehlt.append(({**m, "title": titel}, naechstes))
        gewaehlt.sort(key=lambda x: x[0]["ident"])

        details = set(self._auswahl(len(gewaehlt), int(config.get("details_pro_lauf", 20))))
        for i, (m, gebiet) in enumerate(gewaehlt):
            pfad = bekannte_pfade.get(m["ident"]) or slug(m["title"])
            url = f"{basis}{config.get('liste_pfad', LISTE)}/{pfad}"
            d = LoipenDaten(source_key=m["ident"], name=m["title"], source_url=url, gebiet_slug=gebiet)
            d.lat, d.lon = float(m["latlng"][0]), float(m["latlng"][1])
            ist_offen = m["ident"] in offen
            d.status = Status.OFFEN if ist_offen else Status.GESCHLOSSEN
            d.status_rohtext = "tirol.at: geöffnet" if ist_offen else "tirol.at: nicht als geöffnet gemeldet"
            if i in details:
                try:
                    self._detail(d, fetcher.get(url), ergebnis)
                except Exception as e:  # eine fehlende Detailseite stoppt die anderen nicht
                    ergebnis.warnungen.append(f"{m['title']}: Detailseite nicht lesbar ({type(e).__name__}: {e})")
            ergebnis.loipen.append(d)
        return ergebnis

    @staticmethod
    def _detail(d: LoipenDaten, seite: str, ergebnis: AdapterErgebnis) -> None:
        f = parse_detail(seite)
        if f.get("kennung") and f"addressbase_{f['kennung']}" != d.source_key:
            ergebnis.warnungen.append(
                f"{d.name}: Detailseite {d.source_url} gehoert zu addressbase_{f['kennung']}, "
                "Pfad in config.slugs eintragen")
            return
        if "status" in f:
            _, bekannt = normiere_zustand(f["status"])
            if not bekannt:
                d.unbekannte_begriffe.append(("status", f["status"]))
        if f.get("schwierigkeit"):
            d.schwierigkeit, bekannt = normiere_schwierigkeit(f["schwierigkeit"])
            if not bekannt:
                d.unbekannte_begriffe.append(("schwierigkeit", f["schwierigkeit"]))
        d.laenge_km = f.get("laenge_km")
        if f.get("stile"):
            d.technik = TECHNIK.get(f["stile"].lower(), Technik.UNBEKANNT)
            if d.technik == Technik.UNBEKANNT:
                d.unbekannte_begriffe.append(("technik", f["stile"]))
        d.nachtloipe = "Beleuchtet" in f["merkmale"]
        if f.get("startpunkt"):
            d.startpunkt = f["startpunkt"]
            if f.get("endpunkt"):
                d.rundkurs = f["endpunkt"] == f["startpunkt"] or None
        if "lat" in f:
            d.lat, d.lon = f["lat"], f["lon"]
        if f.get("url"):
            d.source_url = f["url"]
        d.rohtext = json.dumps({k: f.get(k) for k in ("status", "verband", "merkmale")}, ensure_ascii=False)
