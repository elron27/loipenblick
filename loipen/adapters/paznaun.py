"""Adapter Paznaun-Ischgl: "Geöffnete Anlagen", Typ Langlauf (P31, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/paznaun/2026-11-19/): ischgl.com (TVB Paznaun-Ischgl,
Pimcore/Valantic) laedt die Liste nach, und zwar von derselben Seite mit &ajax=1. Die Antwort ist JSON
{"success": true, "html": "<Fragment>"}; je Loipe ein .facilities-accordion-item mit
- Status-Symbol facilities-accordion-item__status-icon--open|--closed,
- Nummer ("L.1", "S-B1") neben der Schwierigkeit (status--easy, title "Leicht"), Name in h5,
- Infofeldern (headline/value): Start, Ziel, Höhendifferenz, Länge ("5.5 km"), Schwierigkeit, Status
  ("Geschlossen"), Cross-Country-Stil ("Klassisch, Skating").
Die Seite selbst nennt "Letztes Update 19.11.2026, 15:40 Uhr" (zweiter Abruf, ohne ajax).
22 Loipen in Ischgl, Mathon, Galtür, Wirl, Bielerhöhe und Samnaun; Samnaun (Schweiz) meldet
snow.myswitzerland.com und wird ausgelassen (config["auslassen"]). robots.txt sperrt ajaxRequestType, nicht ajax.
"""

import json
import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import parse_datum
from loipen.adapters.tirol_orte import gebiet, km, nacht, schluessel, setze_schwierigkeit, setze_status, technik
from loipen.models import Status

SYMBOL = {"open": Status.OFFEN, "closed": Status.GESCHLOSSEN}
STUFE = {"easy": "leicht", "medium": "mittel", "difficult": "schwer"}


class PaznaunAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        seite = base_url.rstrip("/") + config.get("pfad", "/de/winter/silvretta-arena/geoeffnete-anlagen?type=cross-country")
        url = seite + "&sorting=status-desc&ajax=1"
        antwort = json.loads(fetcher.get(url))
        stand = None
        try:
            kopf = Selector(fetcher.get(seite)).xpath("normalize-space(//*[contains(text(), 'Letztes Update')])").get()
            stand = parse_datum(kopf)
        except Exception as e:  # der Stand ist Beiwerk, die Liste zaehlt
            ergebnis.warnungen.append(f"Stand der Seite nicht lesbar: {e}")
        auslassen = config.get("auslassen", [])
        for item in Selector(antwort.get("html", "")).css(".facilities-accordion-item"):
            name = item.css("h5::text").get(default="").strip()
            nummer = item.css(".facilities-accordion-grid__typ > span:not(.status)::text").get(default="").strip()
            if not name:
                continue
            info = {i.css(".facilities-accordion-info-grid__headline::text").get(default="").strip():
                    " ".join(i.css(".facilities-accordion-info-grid__value ::text").getall()).strip()
                    for i in item.css(".facilities-accordion-info-grid__item")}
            start = info.get("Start", "")
            if any(w in name or w in start for w in auslassen):
                continue
            voll = f"{nummer} {name}".strip()
            d = LoipenDaten(source_key=schluessel(voll), name=voll, source_url=seite,
                            gebiet_slug=gebiet(name, start.split(",")[0].strip(), config))
            klasse = item.css(".facilities-accordion-item__status-icon::attr(class)").get(default="")
            symbol = next((k.rsplit("--", 1)[1] for k in klasse.split() if "__status-icon--" in k), "")
            roh = info.get("Status") or symbol
            setze_status(d, roh, SYMBOL.get(symbol)) if symbol in SYMBOL else setze_status(d, roh)
            # unuebersetzte Schwierigkeit "facility.overview.difficulty.difficult" (L.10 Bielerhoehe)
            stufe = item.css(".facilities-accordion-grid__typ .status::attr(title)").get(default="")
            setze_schwierigkeit(d, STUFE.get(stufe.rsplit(".", 1)[-1], stufe))
            d.laenge_km = km(info.get("Länge"))
            d.technik = technik(info.get("Cross-Country-Stil"))
            d.startpunkt = start or None
            d.quelle_aktualisiert_at = stand
            d.nachtloipe = nacht(name) or (True if "beleucht" in item.get().lower() else None)
            d.rohtext = f"{symbol}; {info}"
            ergebnis.loipen.append(d)
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen in der Anlagenliste, Seitenaufbau geaendert?")
        return ergebnis
