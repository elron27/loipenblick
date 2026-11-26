"""Eigene Seiten je Gebiet und Loipe fuer Suchmaschinen (B17, E-44).

Die App zeigt alles hinter "#/", und Google behandelt alles hinter der Raute als eine Seite. Darum
schreibt der Generator zusaetzlich zur App statische HTML-Seiten mit dem Inhalt schon im HTML:

- /gebiete/                  Uebersicht aller Gebiete nach Land und Region
- /<gebiet>/                 Loipen eines Gebiets mit Zustand, Parken, Nachbargebieten und Quellen
- /<gebiet>/<loipe>/         eine Loipe mit Zustand, Stammdaten, Parken und Quelle

Dazu sitemap.xml, robots.txt mit Regeln fuer KI-Crawler und den IndexNow-Schluessel. Die Seiten laden
kein JavaScript; fuer Karte, Wetter und Benachrichtigung verlinken sie in die App ("/#/loipe/<id>").

Adressen bestehen aus Namen, nicht aus Datenbank-Nummern, damit sie ueber Abrufe gleich bleiben
(B17 AK 2). Eine entfallene Loipe leitet die .htaccess auf ihr Gebiet weiter (B17 AK 7).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape
from zoneinfo import ZoneInfo

from loipen.details import MERKMALE

BERLIN = ZoneInfo("Europe/Berlin")
LAND = {"DE": "Deutschland", "AT": "Österreich", "IT": "Italien", "CH": "Schweiz", "LI": "Liechtenstein"}
WORT = {"offen": "Offen", "eingeschraenkt": "Eingeschränkt", "geschlossen": "Geschlossen", "unbekannt": "Unbekannt"}
TECHNIK = {"klassisch": "klassisch", "skating": "Skating", "beides": "klassisch und Skating"}
STAND_DATEI = ".seiten-stand.json"  # versteckt: wird nicht hochgeladen (upload.freigegeben)

# Ordner und Dateien der App: ein Gebiet mit diesem Namen bekommt die Endung "-loipen"
RESERVIERT = {"daten", "strecken", "statistik", "vendor", "abo", "zaehler", "gebiete", "loipen", "karte",
              "heute", "meine", "abdeckung", "index", "sitemap", "robots", "impressum", "datenschutz",
              "hinweise", "404", "icon", "app", "sw", "manifest", "well-known"}

# B17 AK 5: KI-Crawler, die fuer Training sammeln. Die Quellen haben uns das Anzeigen erlaubt, nicht das
# Weitergeben an Trainingsdaten. Such-Bots (Googlebot, Bingbot, OAI-SearchBot, PerplexityBot) bleiben erlaubt.
TRAININGS_BOTS = ("GPTBot", "Google-Extended", "CCBot", "ClaudeBot", "anthropic-ai", "Applebot-Extended",
                  "Bytespider", "meta-externalagent", "cohere-training-data-crawler", "Diffbot")

# B17 AK 4: eine Loipenseite kommt in den Index, wenn sie neben dem Namen genug eigene Angaben hat.
# Sonst gilt sie als duenne Massenseite: noindex, nicht in der Sitemap, aber ueber das Gebiet erreichbar.
MIN_ANGABEN = 3


def slug(text: str) -> str:
    """Sprechender Adressteil: Kleinbuchstaben, Umlaute ausgeschrieben, sonst nur a-z, 0-9 und "-"."""
    t = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:80].rstrip("-") or "loipe"


def gebiet_pfad(gebiet_slug: str) -> str:
    s = slug(gebiet_slug)
    return f"{s}-loipen" if s in RESERVIERT else s


def angaben(l: dict) -> int:
    """Wie viele eigene Angaben eine Loipe neben Name und Status hat (B17 AK 4)."""
    d = l.get("details") or {}
    return sum((
        l.get("laenge_km") is not None,
        l.get("technik") not in (None, "unbekannt"),
        l.get("schwierigkeit") not in (None, "unbekannt"),
        any(d.get(f) is not None for f in ("hoehenmeter", "hoechster_punkt_m", "tiefster_punkt_m")),
        d.get("dauer_min") is not None,
        bool(d.get("merkmale")) or l.get("nachtloipe") is True,
        bool(l.get("parken")),
        l.get("lat") is not None,
    ))


def indexierbar(l: dict) -> bool:
    return l.get("laenge_km") is not None and angaben(l) >= MIN_ANGABEN + 1 and not l.get("nur_test")


def adressen(regionen: dict) -> tuple[dict[str, str], dict[int, str]]:
    """Pfade ohne fuehrenden Schraegstrich, mit Schraegstrich am Ende: "tegernsee/", "tegernsee/ellmaurunde/".
    Gleichnamige Loipen eines Gebiets bekommen -2, -3 ... in der Reihenfolge ihrer Nummer."""
    gebiete: dict[str, str] = {}
    loipen: dict[int, str] = {}
    vergeben: set[str] = set()
    for r in regionen.values():
        for g in r["gebiete"]:
            p = gebiet_pfad(g["slug"])
            basis, n = p, 2
            while p in vergeben:
                p, n = f"{basis}-{n}", n + 1
            vergeben.add(p)
            gebiete[g["slug"]] = p + "/"
            im_gebiet: set[str] = set()
            for l in sorted(g["loipen"], key=lambda x: (slug(x["name"]), x["id"])):
                s = slug(l["name"])
                basis, n = s, 2
                while s in im_gebiet:
                    s, n = f"{basis}-{n}", n + 1
                im_gebiet.add(s)
                loipen[l["id"]] = f"{p}/{s}/"
    return gebiete, loipen


def _zahl(x: float | None, n: int = 1) -> str:
    return "" if x is None else f"{x:.{n}f}".replace(".", ",")


def _datum(iso: str | None, mit_zeit: bool = True) -> str | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso).astimezone(BERLIN)
    return dt.strftime("%d.%m.%Y, %H:%M Uhr") if mit_zeit else dt.strftime("%d.%m.%Y")


def stand_text(l: dict) -> str:
    """Stand, wie ihn die Quelle meldet. Ohne Datum der Quelle nur der Tag des Abrufs, damit sich die Seite
    nicht bei jedem Lauf aendert (B17 AK 9: nur echte Aenderungen werden neu hochgeladen)."""
    if l.get("quelle_stand"):
        return f"Stand laut Quelle: {_datum(l['quelle_stand'])}"
    if l.get("abgerufen"):
        return f"Abgerufen am {_datum(l['abgerufen'], mit_zeit=False)}"
    return "Noch kein Stand"


def fakten(l: dict) -> list[tuple[str, str]]:
    d = l.get("details") or {}
    f = []
    if l.get("laenge_km") is not None:
        f.append(("Länge", f"{_zahl(l['laenge_km'])} km"))
    if l.get("technik") in TECHNIK:
        f.append(("Technik", TECHNIK[l["technik"]]))
    if l.get("schwierigkeit") not in (None, "unbekannt"):
        f.append(("Schwierigkeit", l["schwierigkeit"]))
    if d.get("hoehenmeter") is not None:
        f.append(("Höhenmeter", f"{d['hoehenmeter']} m"))
    if d.get("hoechster_punkt_m") is not None:
        f.append(("Höchster Punkt", f"{d['hoechster_punkt_m']} m"))
    if d.get("tiefster_punkt_m") is not None:
        f.append(("Tiefster Punkt", f"{d['tiefster_punkt_m']} m"))
    if d.get("dauer_min") is not None:
        h, m = divmod(int(d["dauer_min"]), 60)
        f.append(("Dauer", f"{h} h {m:02d} min" if h else f"{m} min"))
    if l.get("rundkurs") is not None:
        f.append(("Rundkurs", "ja" if l["rundkurs"] else "nein"))
    if l.get("nachtloipe") is not None:
        f.append(("Flutlicht", "ja" if l["nachtloipe"] else "nein"))
    return f


def merkmale(l: dict) -> list[str]:
    d = l.get("details") or {}
    return [MERKMALE.get(m, m) for m in d.get("merkmale") or []]


def _gebiet_satz(g: dict, region: dict) -> str:
    """Kurzer eigener Absatz je Gebiet aus vorhandenen Daten (kein Fuelltext)."""
    loipen = g["loipen"]
    km = sum(l["laenge_km"] for l in loipen if l.get("laenge_km"))
    ort = region["name"] + (f", {region['bundesland']}" if region.get("bundesland") else "")
    teile = [f"{g['name']} liegt in der Region {ort} ({LAND.get(region['land'], region['land'])})"
             + (f" auf etwa {g['hoehe_m']} m Höhe" if g.get("hoehe_m") else "") + "."]
    anzahl = f"{len(loipen)} Loipe" + ("n" if len(loipen) != 1 else "")
    teile.append(f"Loipenblick führt hier {anzahl}" + (f" mit zusammen rund {_zahl(km, 0)} km" if km else "") + ".")
    klassisch = sum(1 for l in loipen if l.get("technik") in ("klassisch", "beides"))
    skating = sum(1 for l in loipen if l.get("technik") in ("skating", "beides"))
    if klassisch or skating:
        teile.append(f"{klassisch} davon sind klassisch gespurt, {skating} für Skating.")
    extra = []
    if any(l.get("nachtloipe") for l in loipen):
        extra.append("eine Nachtloipe mit Flutlicht")
    if any("hundeloipe" in ((l.get("details") or {}).get("merkmale") or []) for l in loipen):
        extra.append("Loipen, auf denen Hunde erlaubt sind")
    if extra:
        teile.append("Es gibt " + " und ".join(extra) + ".")
    return " ".join(teile)


def _jsonld(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _krumen(basis: str | None, teile: list[tuple[str, str]]) -> str | None:
    """B17 AK 6: BreadcrumbList; nur mit oeffentlicher Adresse, weil schema.org absolute Adressen braucht."""
    if not basis:
        return None
    return _jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": basis + "/" + pfad}
        for i, (name, pfad) in enumerate(teile)]})


def _ort(basis: str | None, name: str, pfad: str, lat, lon, enthalten_in: str | None = None) -> str | None:
    if not basis:
        return None
    o = {"@context": "https://schema.org", "@type": "Place", "name": name, "url": basis + "/" + pfad}
    if lat is not None and lon is not None:
        o["geo"] = {"@type": "GeoCoordinates", "latitude": round(lat, 5), "longitude": round(lon, 5)}
    if enthalten_in:
        o["containedInPlace"] = {"@type": "Place", "name": enthalten_in}
    return _jsonld(o)


def baue_seiten(daten: dict, basis: str | None) -> list[dict]:
    """Alle Seiten als Liste von {pfad, vorlage, werte, titel, beschreibung, index}.
    pfad ohne fuehrenden Schraegstrich, z. B. "tegernsee/ellmaurunde/"."""
    basis = basis.rstrip("/") if basis else None
    g_pfad, l_pfad = adressen(daten["regionen"])
    alle_gebiete = {g["slug"]: g for r in daten["regionen"].values() for g in r["gebiete"]}
    seiten = []

    laender: dict[str, list] = {}
    for r in daten["regionen"].values():
        gebiete = [{"name": g["name"], "pfad": g_pfad[g["slug"]], "loipen": len(g["loipen"]),
                    "km": _zahl(sum(l["laenge_km"] for l in g["loipen"] if l.get("laenge_km")), 0)}
                   for g in r["gebiete"] if g["loipen"]]
        if gebiete:
            laender.setdefault(LAND.get(r["region"]["land"], r["region"]["land"]), []).append(
                {"name": r["region"]["name"], "bundesland": r["region"].get("bundesland"), "gebiete": gebiete})
    anzahl_gebiete = sum(len(r["gebiete"]) for rs in laender.values() for r in rs)
    seiten.append({
        "pfad": "gebiete/", "vorlage": "uebersicht.html.j2", "index": True,
        "titel": "Alle Langlaufgebiete und Loipen | Loipenblick",
        "h1": "Alle Langlaufgebiete",
        "beschreibung": (f"{anzahl_gebiete} Langlaufgebiete in Bayern, Tirol, Salzburg, Südtirol und der Schweiz "
                         "mit Loipenzustand, Länge, Parken und Quelle, täglich aktualisiert."),
        "werte": {"laender": laender},
        "jsonld": [x for x in (_krumen(basis, [("Loipenblick", ""), ("Alle Gebiete", "gebiete/")]),) if x],
    })

    for r in daten["regionen"].values():
        region = r["region"]
        for g in r["gebiete"]:
            if not g["loipen"]:
                continue
            gp = g_pfad[g["slug"]]
            loipen = sorted(g["loipen"], key=lambda l: (
                {"offen": 0, "eingeschraenkt": 1, "unbekannt": 2, "geschlossen": 3}.get(l["status"], 9), l["name"]))
            offen = sum(1 for l in loipen if l["status"] in ("offen", "eingeschraenkt"))
            quellen = []
            for l in loipen:  # B17 AK 8 / B31: jede Quelle mit Link
                q = l["quelle"]
                if q["name"] not in [x["name"] for x in quellen]:
                    quellen.append({"name": q["name"], "url": q.get("url")})
            staende = [l["quelle_stand"] for l in loipen if l.get("quelle_stand")]
            seiten.append({
                "pfad": gp, "vorlage": "gebiet.html.j2", "index": not g.get("nur_test"),
                "titel": f"Loipen {g['name']}: Zustand heute | Loipenblick",
                "h1": f"Loipen in {g['name']}",
                "beschreibung": (f"{len(loipen)} Loipen in {g['name']} ({region['name']}): welche offen sind, "
                                 "Länge, Technik, Parken und Loipengebühr. Täglich aktualisiert, mit Quelle."),
                "werte": {
                    "g": g, "region": region, "land": LAND.get(region["land"], region["land"]),
                    "satz": _gebiet_satz(g, region), "offen": offen, "app": f"#/gebiet/{g['slug']}",
                    "stand": _datum(max(staende)) if staende else None,
                    "loipen": [{"l": l, "pfad": l_pfad[l["id"]], "wort": WORT.get(l["status"], l["status"]),
                                "technik": TECHNIK.get(l.get("technik")), "km": _zahl(l.get("laenge_km"))}
                               for l in loipen],
                    "nachbarn": [{"name": alle_gebiete[n]["name"], "pfad": g_pfad[n]} for n in g.get("nachbarn") or []
                                 if n in alle_gebiete and alle_gebiete[n]["loipen"]],
                    "quellen": quellen,
                    "gebuehr": g.get("loipengebuehr") or {},
                },
                "jsonld": [x for x in (
                    _krumen(basis, [("Loipenblick", ""), ("Alle Gebiete", "gebiete/"), (g["name"], gp)]),
                    _ort(basis, g["name"], gp, g.get("lat"), g.get("lon"), region["name"])) if x],
            })
            for l in loipen:
                lp = l_pfad[l["id"]]
                fk = fakten(l)
                kurz = ", ".join(w for k, w in fk[:3] if k in ("Länge", "Technik", "Schwierigkeit"))
                seiten.append({
                    "pfad": lp, "vorlage": "loipe.html.j2", "index": indexierbar(l) and not g.get("nur_test"),
                    "titel": f"{l['name']} ({g['name']}): Loipe offen? | Loipenblick",
                    "h1": l["name"],
                    "beschreibung": (f"{l['name']} in {g['name']}" + (f": {kurz}" if kurz else "")
                                     + f". Täglich aktualisierter Zustand laut {l['quelle']['name']}, "
                                       "dazu Parken und Strecke."),
                    "werte": {
                        "l": l, "g": g, "gpfad": gp, "region": region, "wort": WORT.get(l["status"], l["status"]),
                        "stand": stand_text(l), "fakten": fk, "merkmale": merkmale(l), "app": f"#/loipe/{l['id']}",
                        "geschwister": [{"name": x["name"], "pfad": l_pfad[x["id"]],
                                         "wort": WORT.get(x["status"], x["status"]), "status": x["status"]}
                                        for x in loipen if x["id"] != l["id"]][:12],
                        "gebuehr": g.get("loipengebuehr") or {},
                    },
                    "jsonld": [x for x in (
                        _krumen(basis, [("Loipenblick", ""), ("Alle Gebiete", "gebiete/"), (g["name"], gp),
                                        (l["name"], lp)]),
                        _ort(basis, l["name"], lp, l.get("lat"), l.get("lon"), g["name"])) if x],
                })
    return seiten


def lastmod(alter_stand: dict, inhalte: dict[str, str], heute: str) -> dict[str, list]:
    """B17 AK 3: echtes Aenderungsdatum je Seite. Gleicher Inhalt behaelt das alte Datum."""
    neu = {}
    for pfad, html in inhalte.items():
        h = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
        alt = alter_stand.get(pfad)
        neu[pfad] = alt if alt and alt[0] == h else [h, heute]
    return neu


def sitemap(basis: str, eintraege: list[tuple[str, str]]) -> str:
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pfad, datum in eintraege:
        zeilen.append(f"  <url><loc>{xml_escape(basis.rstrip('/') + '/' + pfad)}</loc><lastmod>{datum}</lastmod></url>")
    zeilen.append("</urlset>")
    return "\n".join(zeilen) + "\n"


def robots(oeffentlich: bool, basis: str | None) -> str:
    """B17 AK 5. Die Testversion sperrt alles (B25)."""
    if not oeffentlich:
        return "User-agent: *\nDisallow: /\n"
    teile = ["# Suchmaschinen und KI-Suchen sind willkommen. Sammeln fuer KI-Training nicht: die Loipendaten",
             "# stammen von Tourismusverbaenden, die nur das Anzeigen mit Quellenangabe erlaubt haben.", ""]
    teile += [f"User-agent: {b}" for b in TRAININGS_BOTS] + ["Disallow: /", ""]
    teile += ["User-agent: *", "Allow: /", "Disallow: /abo/", "Disallow: /zaehler/"]
    if basis:
        teile += ["", f"Sitemap: {basis.rstrip('/')}/sitemap.xml"]
    return "\n".join(teile) + "\n"


def indexnow_schluessel(basis: str) -> str:
    """B17 AK 10: IndexNow-Schluessel aus der Adresse. Er ist kein Geheimnis (liegt oeffentlich als Datei),
    er zeigt nur, dass Meldungen fuer diese Domain von ihr selbst kommen."""
    return hashlib.sha256(("loipenblick-indexnow|" + basis.rstrip("/")).encode()).hexdigest()[:32]
