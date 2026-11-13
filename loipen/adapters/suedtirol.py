"""Adapter L und M: Suedtirol (E-18, P23, P24).

L) Dolomiti NordicSki (www.dolomitinordicski.com), HTML, eine Seite fuer alle Mitgliedsregionen.
Befund der Schnappschuesse vom 13.11.2026 (tests/fixtures/suedtirol/2026-11-13/dolomitinordicski/):
- Die Tabelle #table-trails fuehrt 173 Loipen: Antholz, Gsies, Drei Zinnen, Osttirol, Comelico, Cortina,
  Ahrntal, Seiser Alm und Groeden. Der Regionsfilter wirkt nur im Browser (?region= liefert dieselbe Seite).
- Je Zeile: td[data-status] in fuenf Stufen (open, partially_open, open_not_prepared, closed, unknown),
  Name (manchmal mit Regionskennung "| SEISER ALM"), Hinweis als span.table_info, td[data-difficulty]
  0/1/2, Laenge ("2.62km"), max. Hoehe, Ort ("Toblach, Drei Zinnen", oft "–").
- Kein Aktualisierungsdatum, keine Koordinaten (die Karte liegt auf tirol.mapservices.eu, dort sperrt
  robots.txt). Die Lage kommt von derselben Loipe im Open Data Hub (D18, lage_von).
- Das Gebiet ergibt sich aus Ort und Name ueber config["gebiet_map"] (erster Treffer gewinnt).
  Zeilen, die zu config["auslassen"] passen (Osttirol), werden uebersprungen: dort fuehrt tirol.at, und
  Dolomiti NordicSki nennt nur einen Teil der Loipen eines Gebiets (sonst griffe P22 AK 3 falsch).

M) Open Data Hub Suedtirol (tourism.api.opendatahub.com), JSON, Lizenz CC0 je Datensatz.
Befund (tests/fixtures/suedtirol/2026-11-13/opendatahub/loipen.json):
- 272 Loipen (odhtagfilter=loipen), Daten von LTS. Start- und Zielpunkt, Tourismusverein, Stile
  (LTSTags), Beleuchtung; keine Laenge, keine Schwierigkeit, kein Streckenverlauf.
- IsOpen/IsPrepared werden von manchen Vereinen nach der Saison nicht zurueckgesetzt (im November
  7 Loipen "offen", LastChange teils Dezember 2024). Deshalb gilt "offen" nur, wenn LastChange hoechstens
  config["frisch_stunden"] alt ist; aelter heisst "unbekannt" mit der Meldung im Rohtext.
- Der Datensatz enthaelt auch Engadin, Val Muestair, Nauders und Cadore. Jede Loipe gehoert zum
  naechsten Gebiet aus config["gebiete"] im Umkreis config["radius_km"]; liegt ein Punkt aus
  config["ausschluss"] naeher (Nauders, Schweiz: andere Quellen oder spaeter), faellt sie weg. Loipen mit
  Suedtiroler Tourismusverein gehoeren immer dazu (Umkreis config["radius_verein_km"], kein Ausschluss).
"""

import html as htmllib
import json
import re
import time
from datetime import datetime, timezone

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_schwierigkeit, normiere_zustand
from loipen.adapters.tirolat import _abstand_km
from loipen.models import Schwierigkeit, Status, Technik

# ---------- L: Dolomiti NordicSki ----------

SCHWIERIGKEIT_STUFE = {"0": Schwierigkeit.LEICHT, "1": Schwierigkeit.MITTEL, "2": Schwierigkeit.SCHWER}
STATUS_WORT = {"open": "geöffnet", "partially_open": "teilweise geöffnet",
               "open_not_prepared": "geöffnet, nicht präpariert", "closed": "geschlossen", "unknown": "nicht bekannt"}


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _zahl(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)", text)
    return float(m.group(1).replace(",", ".")) if m else None


def name_und_kennung(roh: str) -> tuple[str, str | None]:
    """'6 Wolfsbühl | SEISER ALM' -> ('6 Wolfsbühl', 'SEISER ALM').

    Nur ein Teil in Grossbuchstaben hinter dem letzten '|' ist eine Regionskennung; sonst gehoert er zum
    Namen ('Talloipe | Sonnenloipe (Nr.2)', 'Saltria - Monte Pana | Teilstück SEISER ALM' bleibt Teilstück).
    """
    name = re.sub(r"\s+", " ", roh).strip()
    if "|" in name:
        vorn, hinten = name.rsplit("|", 1)
        hinten = hinten.strip()
        kennung = re.sub(r"^Teilstück\s+", "", hinten)
        if kennung and kennung == kennung.upper() and re.search(r"[A-ZÄÖÜ]{3}", kennung):
            teil = " (Teilstück)" if hinten != kennung else ""
            return vorn.strip() + teil, kennung
    return name, None


def lese_tabelle(seite: str) -> list[dict]:
    """Zeilen der Loipentabelle als dicts mit status, name, kennung, hinweis, stufe, laenge, hoehe, ort, karte."""
    tabelle = re.search(r'<table[^>]*id="table-trails"[\s\S]*?<tbody>([\s\S]*?)</tbody>', seite)
    if not tabelle:
        raise ValueError("Dolomiti NordicSki: Tabelle #table-trails fehlt, Seitenaufbau geaendert?")
    zeilen = []
    for tr in re.findall(r"<tr>([\s\S]*?)</tr>", tabelle.group(1)):
        tds = re.findall(r"<td([^>]*)>([\s\S]*?)</td>", tr)
        if len(tds) < 6:
            continue
        status = re.search(r'data-status="([^"]*)"', tds[0][0])
        stufe = re.search(r'data-difficulty="([^"]*)"', tds[2][0])
        zelle = tds[1][1]
        hinweis = re.search(r'class="table_info"[\s\S]*?title="([^"]*)"', zelle)
        name, kennung = name_und_kennung(_text(zelle.split('<span class="table_info"')[0]))
        karte = re.search(r'href="(https://maps\.dolomitinordicski\.com[^"]*)"', tr)
        ort = _text(tds[5][1])
        zeilen.append({
            "status": status.group(1) if status else "",
            "name": name,
            "kennung": kennung,
            "hinweis": htmllib.unescape(hinweis.group(1)).strip() if hinweis else None,
            "stufe": stufe.group(1) if stufe else None,
            "stufe_text": _text(tds[2][1]),
            "laenge_km": _zahl(_text(tds[3][1])),
            "hoehe_m": _zahl(_text(tds[4][1])),
            "ort": None if ort in ("", "–", "-") else ort,
            "karte": karte.group(1) if karte else None,
        })
    return zeilen


def _passt(muster: str, text: str) -> bool:
    return re.search(rf"(?<![\wÄÖÜäöü]){re.escape(muster)}", text, re.I) is not None


class DolomitiNordicSkiAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        url = base_url.rstrip("/") + config["pfad"]
        zeilen = lese_tabelle(fetcher.get(url))
        gebiet_map: dict[str, str] = config.get("gebiet_map") or {}
        auslassen = config.get("auslassen") or []
        ohne_gebiet = []
        gesehen: dict[str, int] = {}
        for z in zeilen:
            # Ort zuerst (genauer), dann Regionskennung und Name
            texte = [t for t in (z["ort"], z["kennung"], z["name"]) if t]
            if any(_passt(m, t) for m in auslassen for t in texte):
                continue
            gebiet = next((slug for t in texte for m, slug in gebiet_map.items() if _passt(m, t)), None)
            if gebiet is None:
                ohne_gebiet.append(z["name"])
                continue
            # Kennung der Quelle: die Loipennummer der Karte; gleiche Namen kommen in mehreren Regionen vor
            kennung = re.search(r"/(\d+)$", z["karte"] or "")
            key = f"dns_{kennung.group(1)}" if kennung else f"dns_{gebiet}_{z['name']}"
            gesehen[key] = gesehen.get(key, 0) + 1
            if gesehen[key] > 1:
                key = f"{key}_{gesehen[key]}"
            name = z["name"]
            # Namen wie im Open Data Hub, damit dieselbe Loipe erkannt wird (D15): "Südtirol Arena" = Biathlonzentrum
            for alt, neu in (config.get("namen_ersatz") or {}).items():
                name = name.replace(alt, neu)
            d = LoipenDaten(source_key=key, name=name, source_url=url, gebiet_slug=gebiet)
            d.status, bekannt = normiere_zustand(z["status"])
            if not bekannt:
                d.unbekannte_begriffe.append(("status", z["status"]))
            d.status_rohtext = "Dolomiti NordicSki: " + STATUS_WORT.get(z["status"], z["status"])
            if z["stufe"] in SCHWIERIGKEIT_STUFE:
                d.schwierigkeit = SCHWIERIGKEIT_STUFE[z["stufe"]]
            elif z["stufe_text"]:
                d.schwierigkeit, bekannt = normiere_schwierigkeit(z["stufe_text"])
                if not bekannt:
                    d.unbekannte_begriffe.append(("schwierigkeit", z["stufe_text"]))
            d.laenge_km = z["laenge_km"]
            if z["hinweis"] and re.search(r"nur skating", z["hinweis"], re.I):
                d.technik = Technik.SKATING if "keine spuren" in z["hinweis"].lower() else Technik.UNBEKANNT
            d.nachtloipe = True if re.search(r"nachtloipe|beleuchtet", f"{z['name']} {z['hinweis'] or ''}", re.I) else None
            d.startpunkt = z["ort"]
            d.rohtext = json.dumps({"status": z["status"], "hinweis": z["hinweis"], "ort": z["ort"],
                                    "hoehe_max_m": z["hoehe_m"], "karte": z["karte"]}, ensure_ascii=False)
            ergebnis.loipen.append(d)
        if ohne_gebiet:
            ergebnis.warnungen.append(
                f"Dolomiti NordicSki: {len(ohne_gebiet)} Loipen ohne Gebiet (gebiet_map ergaenzen): "
                + ", ".join(ohne_gebiet[:10]))
        return ergebnis


# ---------- M: Open Data Hub Suedtirol ----------

TECHNIK_TAG = {"klassisch und skating": Technik.BEIDES, "klassisch": Technik.KLASSISCH, "skating": Technik.SKATING}
ODH_LISTE = "https://www.suedtirol.info/de/erleben/winter/langlaufen/loipen"


def _zeit(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        # .NET schreibt sieben Nachkommastellen; Python liest hoechstens sechs
        text = re.sub(r"(\.\d{6})\d+", r"\1", text)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _punkt(eintrag: dict, art: str) -> tuple[float, float] | None:
    p = (eintrag.get("GpsPoints") or {}).get(art)
    if not p or not p.get("Latitude") or not p.get("Longitude"):
        return None
    return float(p["Latitude"]), float(p["Longitude"])


def odh_name(eintrag: dict) -> str:
    titel = ((eintrag.get("Detail") or {}).get("de") or {}).get("Title") or eintrag.get("Shortname") or ""
    return re.sub(r"\s+", " ", titel).strip()


def odh_verein(eintrag: dict) -> str | None:
    return (((eintrag.get("LocationInfo") or {}).get("TvInfo") or {}).get("Name") or {}).get("de")


class OpenDataHubAdapter:
    def __init__(self, uhr=time.time):
        self._uhr = uhr

    def _eintraege(self, url: str, fetcher: Fetcher) -> list[dict]:
        alle: list[dict] = []
        for _ in range(10):  # hoechstens 10 Seiten; mit pagesize=400 reicht eine
            daten = json.loads(fetcher.get(url))
            if not isinstance(daten, dict) or "Items" not in daten:
                raise ValueError("Open Data Hub: Antwort ohne Items, Schnittstelle geaendert?")
            alle += daten["Items"]
            url = daten.get("NextPage")
            if not url:
                break
        return alle

    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        jetzt = datetime.fromtimestamp(self._uhr(), tz=timezone.utc)
        frisch_h = float(config.get("frisch_stunden", 48))
        punkte = {s: tuple(p) for s, p in (config.get("gebiet_punkte") or {}).items()}
        erlaubt = [s for s in config.get("gebiete", []) if s in punkte]
        ausschluss = [(a["name"], (float(a["lat"]), float(a["lon"]))) for a in config.get("ausschluss") or []]
        radius = float(config.get("radius_km", 12))
        radius_verein = float(config.get("radius_verein_km", radius))
        verein_map: dict[str, str] = config.get("verein_map") or {}
        weglassen = re.compile(config["auslassen_muster"]) if config.get("auslassen_muster") else None

        for e in self._eintraege(base_url.rstrip("/") + config["pfad"], fetcher):
            name = odh_name(e)
            pos = _punkt(e, "startingpoint") or _punkt(e, "position")
            if not name or not pos or e.get("Active") is False or (weglassen and weglassen.search(name)):
                continue
            verein = odh_verein(e)
            naechstes = min(erlaubt, key=lambda s: _abstand_km(pos, punkte[s]), default=None)
            if naechstes is None:
                continue
            abstand = _abstand_km(pos, punkte[naechstes])
            # Der Tourismusverein bestimmt das Gebiet, wenn bekannt: Startpunkte liegen oft am Rand
            # (Gsieser Loipe startet in Welsberg, die Val-Fonda-Runde suedlich von Toblach)
            if verein in verein_map:
                naechstes, abstand = verein_map[verein], 0.0
            # Mit Suedtiroler Tourismusverein gehoert die Loipe sicher dazu (weiterer Umkreis, kein Ausschluss);
            # ohne Verein liegt sie oft jenseits der Grenze (Engadin, Nauders, Cadore)
            if verein:
                if abstand > radius_verein:
                    continue
            elif abstand > radius or any(_abstand_km(pos, p) < abstand for _, p in ausschluss):
                continue
            kontakt = ((e.get("ContactInfos") or {}).get("de") or {})
            d = LoipenDaten(source_key=e["Id"], name=name, source_url=kontakt.get("Url") or ODH_LISTE,
                            gebiet_slug=naechstes)
            d.lat, d.lon = pos
            ziel = _punkt(e, "arrivalpoint")
            if ziel:
                d.rundkurs = _abstand_km(pos, ziel) < 0.1
            tags = {t.get("Id") for t in e.get("LTSTags") or []}
            d.technik = next((t for k, t in TECHNIK_TAG.items() if k in tags), Technik.UNBEKANNT)
            d.nachtloipe = e.get("IsWithLigth")
            geaendert = _zeit(e.get("LastChange"))
            d.quelle_aktualisiert_at = geaendert
            frisch = geaendert is not None and (jetzt - geaendert).total_seconds() <= frisch_h * 3600
            stand = geaendert.strftime("%d.%m.%Y") if geaendert else "ohne Datum"
            if e.get("IsOpen"):
                if frisch:
                    d.status = Status.OFFEN
                    d.status_rohtext = f"Open Data Hub: geöffnet{' und präpariert' if e.get('IsPrepared') else ''}"
                else:
                    d.status = Status.UNBEKANNT
                    d.status_rohtext = f"Open Data Hub: geöffnet, aber zuletzt am {stand} geändert (unbestätigt)"
            else:
                d.status = Status.GESCHLOSSEN
                d.status_rohtext = "Open Data Hub: nicht geöffnet"
            d.startpunkt = kontakt.get("Area") or verein
            d.rohtext = json.dumps({"status": d.status_rohtext, "IsOpen": e.get("IsOpen"),
                                    "IsPrepared": e.get("IsPrepared"), "LastChange": e.get("LastChange"),
                                    "verein": verein,
                                    "lizenz": (e.get("LicenseInfo") or {}).get("License")}, ensure_ascii=False)
            ergebnis.loipen.append(d)
        return ergebnis
