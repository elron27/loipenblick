"""Adapter N: Schneebericht von Schweiz Tourismus (snow.myswitzerland.com), HTML, eine Seite je Ort (E-20, P29).

Befund der Schnappschuesse vom 13.11.2026 (tests/fixtures/schweiz/2026-11-13/myswitzerland/):
- Die Liste /schneebericht/langlauf/?p=1..5 fuehrt 126 Langlauforte, 30 je Seite. Die Seitenlinks der
  Liste tragen ?noidx=, das robots.txt sperrt; ?p=<n> ohne noidx ist erlaubt.
- Je Ort eine Seite /schneebericht/<ort>-<id>/ mit dem Abschnitt article#langlauf. Darin:
  * Eintraege mit Symbol facility_icons/42xx (Daten von infosnow.ch): eine Zeile je Technik,
    Tooltip "Typ: Klassisch | Skating | Klassisch und Skating | Hundeloipe ..., Zustand: <Wort>,
    <offen>/<gesamt> km offen", dazu span.QuickStatus open|closed|noinfo.
  * Eintraege mit Link auf schweizmobil.ch: ueberregionale Routen ("Rottenloipe 640") mit "Status: k.A."
    meist ohne Meldung; sie werden nicht uebernommen (doppelt zu den Ortsloipen, keine Laenge).
  * "Letzte Aktualisierung: 13.11.2026, 08:00" (Ortszeit) gilt fuer die ganze Seite.
- Keine Koordinate je Loipe; die Seite nennt nur den Ort (AreaMap-Link lat/lng). Die Lage der Loipe ist
  daher die Gebietsmitte (wie bei Dolomiti NordicSki ohne ODH-Treffer).
- Hundeloipen werden uebersprungen. Klassisch und Skating derselben Loipe werden zusammengefuehrt.
"""

import html as htmllib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import normiere_zustand
from loipen.models import Status, Technik

ZUERICH = ZoneInfo("Europe/Zurich")
SCHNELL = {"open": Status.OFFEN, "closed": Status.GESCHLOSSEN, "noinfo": Status.UNBEKANNT}
TYP = {"klassisch": Technik.KLASSISCH, "skating": Technik.SKATING, "klassisch und skating": Technik.BEIDES,
       "classic": Technik.KLASSISCH, "classic and skating": Technik.BEIDES,
       "keine angaben": Technik.UNBEKANNT}


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def abschnitt_langlauf(seite: str) -> str | None:
    i = seite.find('id="langlauf"')
    if i < 0:
        i = seite.find('id="crosscountry"')  # englische Fassung der Seite
    if i < 0:
        return None
    j = seite.find("<article", i)
    return seite[i:j if j > 0 else len(seite)]


def stand(seite: str) -> datetime | None:
    m = re.search(r"(?:Letzte Aktualisierung|Last update):\s*(\d{1,2})\.(\d{1,2})\.(\d{4}),\s*(\d{1,2}):(\d{2})", seite)
    if not m:
        return None
    t, mo, j, h, mi = (int(x) for x in m.groups())
    return datetime(j, mo, t, h, mi, tzinfo=ZUERICH)


def ort_daten(seite: str) -> dict:
    """Name, Region, Lage und Hoehe des Ortes (fuer gebiete.yaml, scripts/schweiz_gebiete.py)."""
    name = re.search(r'tooltip_u1">\s*<div class="t-base t-bold">([^<]*)</div>\s*<div class="t-xs">([^<]*)<', seite)
    lage = re.search(r"lat:(-?\d+\.\d+);lng:(-?\d+\.\d+)", seite)
    hoehe = re.search(r"Schneehöhe im Ort <span>auf (\d+) m", seite)
    return {
        "name": htmllib.unescape(name.group(1)).strip() if name else None,
        "region": htmllib.unescape(name.group(2)).strip() if name else None,
        "lat": round(float(lage.group(1)), 4) if lage else None,
        "lon": round(float(lage.group(2)), 4) if lage else None,
        "hoehe_m": int(hoehe.group(1)) if hoehe else None,
    }


def lese_loipen(seite: str) -> list[dict]:
    """Zeilen der Ortsloipen: name, typ, zustand, schnell, offen_km, gesamt_km (eine Zeile je Technik)."""
    teil = abschnitt_langlauf(seite)
    if teil is None:
        return []
    zeilen = []
    for item in re.findall(r'<li class="StatusTable--item">([\s\S]*?)</li>', teil):
        if "facility_icons/42" not in item or "schweizmobil" in item:
            continue
        titel = re.search(r'StatusTable--title">([\s\S]*?)<(?:span|button)', item)
        tip = re.search(r'Tooltip--hidden"[^>]*>([\s\S]*?)</div>', item)
        schnell = re.search(r"QuickStatus (\w+)", item)
        info = _text((tip.group(1) if tip else "").replace("<br>", "|"))
        felder = {k.strip().lower(): v.strip() for k, v in
                  (t.split(":", 1) for t in info.split("|") if ":" in t)}
        km = re.search(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?) km (?:offen|open)", info)
        zeilen.append({
            "name": re.sub(r"\s+", " ", _text(titel.group(1) if titel else "")).strip(),
            "typ": felder.get("typ") or felder.get("type", ""),
            "zustand": felder.get("zustand") or felder.get("conditions") or felder.get("condition", ""),
            "schnell": schnell.group(1) if schnell else "",
            "offen_km": float(km.group(1)) if km else None,
            "gesamt_km": float(km.group(2)) if km else None,
        })
    return zeilen


def lese_netz(seite: str) -> list[dict]:
    """Summen des Ortes (QuickFacts "Loipe klassisch 0.0/35.0 km Zustand geschlossen"), je Technik eine Zeile
    im selben Format wie lese_loipen. Gebraucht, wenn der Ort keine einzelnen Loipen meldet."""
    teil = abschnitt_langlauf(seite) or ""
    zeilen = []
    for titel in re.findall(r'QuickFactsCollection--title">([\s\S]*?)</div>\s*</div>', teil):
        roh = re.search(r'QuickStatus (\w+)', titel)
        t = _text(titel)
        m = re.match(r"(?:Loipe|Trail|Cross-country)\s+(klassisch|skating|classic)\s+(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?) km"
                     r"\s+(?:Zustand|Conditions?)\s*(.*)$", t, re.I)
        if not m:
            continue
        zeilen.append({"name": None, "typ": "Klassisch" if m.group(1).lower() != "skating" else "Skating",
                       "zustand": m.group(4).strip(), "schnell": roh.group(1) if roh else "",
                       "offen_km": float(m.group(2)), "gesamt_km": float(m.group(3))})
    return zeilen


def _status(zeile: dict) -> tuple[Status, bool]:
    """Zustandswort zuerst ("gut", "geschlossen"), sonst das Symbol der Zeile."""
    wort = zeile["zustand"]
    if wort:
        status, bekannt = normiere_zustand(wort)
        if bekannt:
            return status, True
    return SCHNELL.get(zeile["schnell"], Status.UNBEKANNT), not wort


def _gesamt(teile: list[Status]) -> Status:
    if Status.OFFEN in teile:
        return Status.OFFEN
    if Status.EINGESCHRAENKT in teile:
        return Status.EINGESCHRAENKT
    if teile and all(s == Status.GESCHLOSSEN for s in teile):
        return Status.GESCHLOSSEN
    return Status.GESCHLOSSEN if Status.GESCHLOSSEN in teile else Status.UNBEKANNT


class MySwitzerlandAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        # Zwei Ortsseiten koennen dieselben Loipen melden (Andermatt-Oberalp-Sedrun und Sedrun-Oberalp-Andermatt):
        # je Gebiet und Name zaehlt die Meldung mit dem juengeren Stand
        gesehen: dict[tuple[str, str], LoipenDaten] = {}
        for ort in config["orte"]:
            url = base_url.rstrip("/") + ort["pfad"]
            try:
                seite = fetcher.get(url)
            except Exception as e:  # ein Ort darf ausfallen, die anderen laufen weiter
                ergebnis.warnungen.append(f"Schweiz Tourismus {ort['pfad']}: {e}")
                continue
            if abschnitt_langlauf(seite) is None:
                ergebnis.warnungen.append(f"Schweiz Tourismus {ort['pfad']}: Abschnitt Langlauf fehlt")
                continue
            zeit = stand(seite)
            loipen: dict[str, dict] = {}
            for z in lese_loipen(seite):
                if not z["name"] or re.search(r"hunde|dog", z["typ"], re.I):
                    continue
                loipen.setdefault(z["name"], {"zeilen": []})["zeilen"].append(z)
            if not loipen:
                # Ort ohne einzelne Loipen: eine Zeile fuer das ganze Loipennetz (Summe des Ortes)
                netz = [z for z in lese_netz(seite) if z["gesamt_km"]]
                if netz:
                    loipen[f"Loipennetz {ort.get('name') or ort_daten(seite)['name']}"] = {"zeilen": netz}
            schnee = re.search(r"Schneehöhe im Ort <span>[^<]*</span></th>\s*<td>\s*(\d+) cm", seite)
            id_ort = re.search(r"-(\d+)/?$", ort["pfad"].rstrip("/"))
            for name, eintrag in loipen.items():
                d = LoipenDaten(source_key=f"mys_{id_ort.group(1) if id_ort else ort['gebiet']}_{name}",
                                name=name, source_url=url, gebiet_slug=ort["gebiet"])
                techniken, teile, roh = set(), [], []
                for z in eintrag["zeilen"]:
                    status, bekannt = _status(z)
                    if not bekannt:
                        d.unbekannte_begriffe.append(("status", z["zustand"]))
                    typ = TYP.get(z["typ"].lower(), Technik.UNBEKANNT)
                    if typ == Technik.UNBEKANNT and z["typ"].lower() not in TYP:
                        d.unbekannte_begriffe.append(("technik", z["typ"]))
                    techniken.add(typ)
                    teile.append(status)
                    if typ in (Technik.KLASSISCH, Technik.BEIDES):
                        d.status_klassisch = status
                        d.gespurt_klassisch_km = z["offen_km"]
                    if typ in (Technik.SKATING, Technik.BEIDES):
                        d.status_skating = status
                        d.gespurt_skating_km = z["offen_km"]
                    if z["gesamt_km"]:
                        d.laenge_km = max(d.laenge_km or 0, z["gesamt_km"])
                    roh.append(f"{z['typ'] or 'Loipe'}: {z['zustand'] or z['schnell']}")
                if Technik.BEIDES in techniken or {Technik.KLASSISCH, Technik.SKATING} <= techniken:
                    d.technik = Technik.BEIDES
                elif len(techniken) == 1:
                    d.technik = techniken.pop()
                d.status = _gesamt(teile)
                km = [k for k in (d.gespurt_klassisch_km, d.gespurt_skating_km) if k is not None]
                d.gespurt_gesamt_km = max(km) if km else None
                d.quelle_aktualisiert_at = zeit
                d.status_rohtext = "Schweiz Tourismus: " + ", ".join(roh)
                d.schneehoehe_cm = int(schnee.group(1)) if schnee else None
                d.nachtloipe = True if re.search(r"nacht|beleuchtet", name, re.I) else None
                d.rohtext = json.dumps({"zeilen": eintrag["zeilen"], "stand": zeit.isoformat() if zeit else None},
                                       ensure_ascii=False)
                alt = gesehen.get((ort["gebiet"], name))
                if alt is not None:
                    if (alt.quelle_aktualisiert_at or datetime.min.replace(tzinfo=ZUERICH)) >= (
                            zeit or datetime.min.replace(tzinfo=ZUERICH)):
                        continue
                    ergebnis.loipen.remove(alt)
                gesehen[(ort["gebiet"], name)] = d
                ergebnis.loipen.append(d)
        return ergebnis
