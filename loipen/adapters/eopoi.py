"""Wintersportbericht im eo-POI-Widget (eberl online), wie ihn Pfronten zeigt (P36, Allgaeu, nur Test).

Befund (Schnappschuss vom 20.11.2026, tests/fixtures/pfronten/2026-11-20/liste-winter.html):
- pfronten.de/aktiv/winterurlaub-im-allgaeu/wintersportbericht/liste-winter/ liefert die Liste schon im HTML
  mit: div.eopoi-app-widget-initial-data enthaelt ein JSON-Objekt {"0": {...}, "1": {...}} mit allen Anlagen
  (Lifte, Winterwanderwege, Rodelbahnen, Loipen). Die Loipen tragen unter state.trackType "classic",
  "skating" oder "classicAndSkating"; Wanderwege haben dort einen leeren Text.
- Je Loipe: state.state ("open"/"closed"), state.lastDateGroomed (UTC, Mitternacht Ortszeit),
  state.length in Metern, state.difficulty (easy/intermediate/difficult), geo.lat/lng = Einstieg.
- Der Widget-Schluessel fuer die Schnittstelle poi3.api.eberl-online.net steht ebenfalls in der Seite;
  der Adapter nutzt ihn nicht, er liest nur das ausgelieferte HTML.
Andere Allgaeuer Seiten (allgaeu.de, Bad Hindelang, Scheidegg) laden dasselbe Widget erst im Browser
nach; dort steht nichts im HTML.
"""

import html
import json
import re
from datetime import datetime

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import BERLIN, normiere_zustand, slugify
from loipen.models import Schwierigkeit, Technik

TECHNIK = {"classic": Technik.KLASSISCH, "skating": Technik.SKATING, "classicandskating": Technik.BEIDES}
SCHWIERIGKEIT = {"easy": Schwierigkeit.LEICHT, "intermediate": Schwierigkeit.MITTEL,
                 "difficult": Schwierigkeit.SCHWER}


def _zeitpunkt(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(BERLIN)
    except ValueError:
        return None


class EoPoiAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        sel = Selector(fetcher.get(url))
        daten = {}
        for roh in sel.css("div.eopoi-app-widget-initial-data::text").getall():
            try:
                teil = json.loads(html.unescape(roh.strip()))
            except ValueError:
                ergebnis.warnungen.append("eo-POI-Daten nicht lesbar, Seitenaufbau geaendert?")
                continue
            if isinstance(teil, dict):
                daten.update(teil)
        ziel = config.get("detail_pfad")
        gesehen = set()
        for eintrag in daten.values():
            st = eintrag.get("state") if isinstance(eintrag, dict) else None
            if not isinstance(st, dict) or not st.get("trackType"):
                continue
            name = (eintrag.get("title") or "").strip()
            if not name or eintrag.get("_id") in gesehen:
                continue
            gesehen.add(eintrag.get("_id"))
            slug = eintrag.get("slug") or slugify(name)
            d = LoipenDaten(source_key=slug, name=name, gebiet_slug=config["default_gebiet"],
                            source_url=base_url.rstrip("/") + ziel.replace("xxxSLUGxxx", slug) if ziel else url)
            roh_status = st.get("state") or ""
            d.status, bekannt = normiere_zustand(roh_status)
            if roh_status and not bekannt:
                d.unbekannte_begriffe.append(("status", roh_status))
            d.status_rohtext = roh_status or None
            d.technik = TECHNIK.get(st["trackType"].lower(), Technik.UNBEKANNT)
            d.schwierigkeit = SCHWIERIGKEIT.get(st.get("difficulty") or "", Schwierigkeit.UNBEKANNT)
            if st.get("length"):
                d.laenge_km = round(st["length"] / 1000, 1)
            d.quelle_aktualisiert_at = _zeitpunkt(st.get("lastDateGroomed"))
            geo = eintrag.get("geo") or {}
            if geo.get("lat") and geo.get("lng"):
                d.lat, d.lon = float(geo["lat"]), float(geo["lng"])
            start = ((eintrag.get("route") or {}).get("description") or {}).get("startingPointDescr")
            d.startpunkt = start or None
            d.nachtloipe = True if st.get("floodlightAt") or "nacht" in name.lower() else None
            info = re.sub(r"<[^>]+>", " ", st.get("stateInfo") or "").strip()
            d.rohtext = f"{roh_status}; praepariert {st.get('lastDateGroomed') or '-'}; {info}".strip("; ")
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen in den eo-POI-Daten gefunden, Seitenaufbau geaendert?")
        return ergebnis
