"""Adapter Oetztal: Loipen-Detailseiten von oetztal.com (P31, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/oetztal/2026-11-19/):
- /de/live-infos/loipenstatus und /de/aktivitaeten/winter/langlaufen/loipenangebot laden die Liste per
  JavaScript (im HTML steht keine Loipe, keine offene Schnittstelle ausser dem Outdooractive-Schluessel der
  Seite, den wir nicht verwenden).
- Jede Loipe hat eine Detailseite /de/aktivitaeten/alle-routen-touren/<name>.r-<outdooractive-id> mit
  serverseitigem Status (div.opening-hours__text "Geschlossen", Punkt color--status-closed), Ort
  (.detail-page-route-tour__location), Schwierigkeit (tag bg-color--oa-easy "Leicht") und Laenge (Kachel
  "Länge": "656 m" / "4,86 km"). "Aktualisiert am" ist das Bearbeitungsdatum der Seite, kein Stand der Meldung.
- Die Detailseiten stehen in der Sitemap /sitemap.xml -> sitemap.tours_6.xml; 22 deutsche URLs mit
  "loipe" oder "langlauf" im Pfad (config["muster"]). Abgerufen werden hoechstens config["max_touren"].
Kein Datum, keine Koordinaten (die Lage kommt von tirol.at).
"""

import re

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.tirol_orte import gebiet, km, nacht, schluessel, setze_schwierigkeit, setze_status, technik
from loipen.models import Status

PUNKT = {"open": Status.OFFEN, "opened": Status.OFFEN, "closed": Status.GESCHLOSSEN}


def tour_urls(fetcher: Fetcher, basis: str, config: dict) -> list[str]:
    index = fetcher.get(basis + "/sitemap.xml")
    touren = next((u for u in re.findall(r"<loc>([^<]+)</loc>", index) if "sitemap.tours" in u), None)
    if not touren:
        return []
    muster = re.compile(config.get("muster", r"/de/aktivitaeten/alle-routen-touren/[^<]*(?:loipe|langlauf)[^<]*\.r-\d+"))
    urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", fetcher.get(touren.replace("&amp;", "&"))) if muster.search(u)]
    return list(dict.fromkeys(urls))


class OetztalAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        basis = base_url.rstrip("/")
        urls = tour_urls(fetcher, basis, config)
        if not urls:
            ergebnis.warnungen.append("Keine Loipen in der Tourensitemap, Seitenaufbau geaendert?")
            return ergebnis
        for url in urls[: int(config.get("max_touren", 30))]:
            try:
                sel = Selector(fetcher.get(url))
            except Exception as e:  # eine fehlende Detailseite haelt den Lauf nicht auf
                ergebnis.warnungen.append(f"{url}: {e}")
                continue
            name = sel.css("h1.detail-page__header::text").get(default="").strip()
            if not name:
                ergebnis.warnungen.append(f"{url}: keine Ueberschrift")
                continue
            ort = sel.css(".detail-page-route-tour__location .feature__text-main::text").get(default="").strip()
            tour_id = re.search(r"\.r-(\d+)", url).group(1)
            d = LoipenDaten(source_key=f"oa-{tour_id}", name=name, source_url=url,
                            gebiet_slug=gebiet(name, ort, config))
            oh = sel.css(".detail-page-route-tour__opening-hours")
            punkt = oh.css(".opening-hours__status::attr(class)").get(default="")
            art = next((k.split("--status-", 1)[1] for k in punkt.split() if "--status-" in k), "")
            roh = oh.css(".opening-hours__text::text").get(default="").strip() or art
            setze_status(d, roh, PUNKT.get(art)) if art in PUNKT else setze_status(d, roh)
            stufe = sel.xpath("//div[contains(@class, 'tag--small') and contains(@class, 'bg-color--oa-')]"
                              "/span[@class='tag__text']/text()").get()
            setze_schwierigkeit(d, stufe)
            kacheln = {k.css(".fst--bodytext--small::text").get(default="").strip():
                       k.css(".live-info-tile__title::text").get(default="").strip()
                       for k in sel.css(".detail-page-route-tour__live-info-tile")}
            d.laenge_km = km(kacheln.get("Länge"))
            tags = [t.strip().lower() for t in sel.css(".tag--small .tag__text::text").getall()]
            d.technik = technik(" ".join(t for t in tags if t in ("klassisch", "skating")))
            d.nachtloipe = nacht(name)
            d.rohtext = f"{ort}: {art}/{roh}; {kacheln.get('Länge')}; {stufe}; {tags}"
            ergebnis.loipen.append(d)
        return ergebnis
