"""Adapter P: Tourenportal von Steiermark Tourismus, Kategorie Langlauf (E-22, P30).

steiermark.com fuehrt alle steirischen Loipen im Tourenportal; der Filter tourCategory=46459526 (Langlauf)
zeigt sie mit dem Loipenstatus, den die Regionen pflegen (die Regionsseiten "Loipenbericht Ausseerland" und
"Der Loipenstatus" von Murau verlinken genau diese Liste). Befund der Schnappschuesse vom 14.11.2026
(tests/fixtures/steiermark/2026-11-14/tourenportal-langlauf-p<n>.html):
- 89 Ergebnisse ("89 Ergebnisse"), 16 je Seite, weitere Seiten ueber &page=<n>.
- Je Loipe ein section.tour-teaser: Name als Link (..._tour_<id>), Badge li.tour-teaser__badge mit
  icon-path-<zustand> und Text ("Geschlossen", "Geöffnet", "Teilweise geöffnet"), dazu Strecke ("5,0 km"),
  Start (Ort, z. B. "Bad Mitterndorf") und Schwierigkeit.
- Bekannte Badges laut CSS der Seite: icon-path-open, -partially-open, -open-not-prepared, -in-preparation,
  -closed. Teaser ohne Badge haben keine Meldung (unbekannt).
- Kein Datum, keine Koordinaten. Das Gebiet ergibt sich aus dem Startort (config["gebiet_map"]).
- Ramsau am Dachstein steht auch im tourinfra-Loipenmanager mit Stand (Rang 2); dieselbe Loipe zaehlt
  dort (D15).
"""

import html as htmllib
import re

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit
from loipen.models import Status

# Badges von steiermark.com (Klasse icon-path-<x>); der Text der Seite wird zusaetzlich gelesen.
BADGE = {"open": Status.OFFEN, "partially-open": Status.EINGESCHRAENKT, "open-not-prepared": Status.EINGESCHRAENKT,
         "in-preparation": Status.GESCHLOSSEN, "closed": Status.GESCHLOSSEN}


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _km(text: str | None) -> float | None:
    """'5,0 km' oder '5.7 km' -> 5.0 / 5.7 (parse_zahl liest den Punkt als Tausendertrenner)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*km", text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _schluessel(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-")


def _gebiet(name: str, ort: str | None, config: dict) -> str:
    karte = config.get("gebiet_map", {})
    if ort and ort in karte:
        return karte[ort]
    return next((g for wort, g in karte.items() if wort in name), config.get("default_gebiet"))


def steiermark_teaser(seite: str) -> list[dict]:
    """Je Teaser Name, Link, Badge (Klasse, Text) und die Infozeilen (Strecke, Start, Schwierigkeit)."""
    teaser = []
    for t in re.split(r'<section class="tour-teaser', seite)[1:]:
        link = re.search(r'tour-teaser__content__title">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', t, re.DOTALL)
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
            url = basis if n == 1 else f"{basis}{'&' if '?' in basis else '?'}page={n}"
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
                gebiet = _gebiet(t["name"], t.get("Start"), config)
                if gebiet is None:
                    ergebnis.warnungen.append(f"steiermark.com: Startort {t.get('Start')!r} ohne Gebiet ({t['name']})")
                    continue
                d = LoipenDaten(source_key=key, name=t["name"],
                                source_url=(base_url.rstrip("/") + href) if href.startswith("/") else href,
                                gebiet_slug=gebiet)
                if t["badge"]:
                    d.status = BADGE.get(t["badge"], Status.UNBEKANNT)
                    d.status_rohtext = t["badge_text"] or t["badge"]
                    if t["badge"] not in BADGE:
                        d.unbekannte_begriffe.append(("status", t["badge"]))
                d.laenge_km = _km(t.get("Strecke"))
                if t.get("Schwierigkeit"):
                    d.schwierigkeit, _ = normiere_schwierigkeit(t["Schwierigkeit"])
                d.startpunkt = t.get("Start")
                d.nachtloipe = True if re.search(r"nacht|flutlicht", t["name"], re.IGNORECASE) else None
                d.rohtext = "; ".join(x for x in (t["badge_text"] or "keine Meldung", t.get("Start"), t["name"]) if x)
                ergebnis.loipen.append(d)
        if erwartet and len(ergebnis.loipen) < erwartet:
            ergebnis.warnungen.append(
                f"steiermark.com: {erwartet} Ergebnisse genannt, {len(ergebnis.loipen)} gelesen (Seitenzahl erhoehen?)")
        return ergebnis
