"""Adapter Serfaus-Fiss-Ladis: Langlaufseite und Skigebietsstatus (P31, E-24).

Befund der Schnappschuesse vom 19.11.2026 (tests/fixtures/serfaus-fiss-ladis/2026-11-19/), Daten serverseitig im HTML:
- /de/winterurlaub/skigebiet-und-winteraktivitaeten/langlaufen: 10 Loipen L1-L10 als .tour-teaser mit
  Name (h3), Schwierigkeit, Status (.tour-teaser__status, "geschlossen"), Hoehenmeter und Laenge ("1 km").
- /de/winterurlaub/skigebietsstatus-und-pistenplan, Reiter #nav-crosscountry: Tabelle Status | Loipen |
  Typ ("Langlaufen Klassisch & Skating") | Schwierigkeitsgrad. Laut Seite alle fuenf Minuten aktualisiert,
  aber ohne Zeitstempel.
Der Status kommt aus der Statustabelle (fehlt sie, aus der Langlaufseite), Laenge aus der Langlaufseite,
Technik aus der Statustabelle. Ohne Datum und ohne Koordinaten.
"""

from parsel import Selector

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.tirol_orte import gebiet, km, nacht, schluessel, setze_schwierigkeit, setze_status, technik


class SerfausAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        basis = base_url.rstrip("/")
        liste_url = basis + config.get("pfad", "/de/winterurlaub/skigebiet-und-winteraktivitaeten/langlaufen")
        status_url = basis + config.get("status_pfad", "/de/winterurlaub/skigebietsstatus-und-pistenplan")
        loipen: dict[str, LoipenDaten] = {}
        for t in Selector(fetcher.get(liste_url)).css(".tour-teaser"):
            name = t.css(".tour-teaser__title::text").get(default="").strip()
            if not name or "Langlaufen" not in t.css(".tour-teaser__badge::text").getall():
                continue
            d = LoipenDaten(source_key=schluessel(name), name=name, source_url=liste_url,
                            gebiet_slug=gebiet(name, None, config))
            setze_status(d, t.css(".tour-teaser__status span:not(.icon)::text").get(default="").strip())
            setze_schwierigkeit(d, t.css(".tour-teaser__difficulty span:not(.tour-teaser__difficulty-dot)::text").get())
            werte = [w.strip() for w in t.css(".row .col-6 > span:not(.icon)::text").getall()]
            d.laenge_km = next((km(w) for w in werte if w.endswith("km")), None)
            d.nachtloipe = nacht(name)
            d.rohtext = f"Liste: {d.status_rohtext}; {werte}"
            loipen[d.source_key] = d
        try:
            zeilen = Selector(fetcher.get(status_url)).css("#nav-crosscountry table tbody tr")
        except Exception as e:
            zeilen = []
            ergebnis.warnungen.append(f"Statustabelle nicht lesbar: {e}")
        for z in zeilen:
            zellen = [z_.xpath("normalize-space()").get(default="") for z_ in z.css("td")]
            if len(zellen) < 4 or not zellen[1]:
                continue
            key = schluessel(zellen[1])
            d = loipen.get(key)
            if d is None:
                d = loipen[key] = LoipenDaten(source_key=key, name=zellen[1], source_url=status_url,
                                              gebiet_slug=gebiet(zellen[1], None, config))
                d.nachtloipe = nacht(zellen[1])
                setze_schwierigkeit(d, zellen[3])
            d.unbekannte_begriffe = [b for b in d.unbekannte_begriffe if b[0] != "status"]
            setze_status(d, zellen[0])
            d.technik = technik(zellen[2])
            d.rohtext = f"{d.rohtext or ''} Status: {zellen}".strip()
        ergebnis.loipen = list(loipen.values())
        if not ergebnis.loipen:
            ergebnis.warnungen.append("Keine Loipen gefunden, Seitenaufbau geaendert?")
        return ergebnis
