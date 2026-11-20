"""Streckenverlaeufe und Parkplaetze aus OpenStreetMap (P38, P39, E-29).

Die meisten Quellen nennen nur den Startpunkt einer Loipe (tirol.at sperrt die GPX-Dateien per robots.txt,
Berchtesgaden ebenso). OpenStreetMap fuehrt viele Loipen als Weg oder Route mit piste:type=nordic und
Parkplaetze mit amenity=parking. Lizenz: ODbL 1.0, Quellenvermerk "© OpenStreetMap-Mitwirkende" an der
Strecke, auf der Karte und in den Hinweisen.

Ablauf (robots.txt und Abstand wie bei den Quellen, P7):
- Loipen: Waymarked Trails Slopes (slopes.waymarkedtrails.org) wertet die OSM-Routen route=ski mit
  piste:type=nordic aus. Der Worker holt je Region einmal pro Woche die Liste der Routen (Name, ID) und nur fuer
  Routen, deren Name zu einer Loipe ohne Streckenverlauf passt, die Geometrie (einmal pro Monat).
  Die Overpass-Server antworteten vom GitHub-Runner nur mit 504 (20.11.2026), Waymarked Trails sofort.
- Parkplaetze: amenity=parking ueber Overpass (Hauptserver, sonst Ausweichserver); faellt das aus, bleibt der
  letzte Stand.
- Gespeichert wird eine verdichtete Fassung je Region in der Tabelle osm_daten.
- Beim Erzeugen der Seite ordnet strecke_fuer() die OSM-Loipen den Loipen ohne eigenen Streckenverlauf zu und
  parkplaetze_bei() sucht Parkplaetze am Loipenstart.

Zuordnung einer Strecke (nur wenn sie belegbar passt, sonst bleibt die Loipe ohne Strecke):
- Der OSM-Name passt zum Loipennamen: gleiche Woerter ohne Ortsnamen und Fuellwoerter (wie bei den Dubletten),
  ein einzelnes allgemeines Wort ("Rundloipe", "Talloipe") reicht nicht.
- Die OSM-Strecke liegt hoechstens 1,5 km vom Startpunkt der Loipe entfernt; ohne Startpunkt hoechstens 8 km
  von der Gebietsmitte.
- Nennt die Quelle eine Laenge, weicht die OSM-Strecke hoechstens um den Faktor 2 ab.
- Unbenannte OSM-Wege werden nie zugeordnet: im Loipennetz waere das geraten.

Parkplaetze: hoechstens zwei oeffentliche Parkplaetze (ohne access=private/customers/no) innerhalb von 500 m um
den Loipenstart, der naechste zuerst. Sie heissen "laut OpenStreetMap" und sind nicht von der Loipenquelle
bestaetigt. Gebuehr nur aus dem Tag fee (yes/no), sonst unbekannt.
"""

import json
import logging
import math
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.dubletten import FUELLWOERTER, schluessel, woerter
from loipen.models import OsmDaten, Region, utcnow

log = logging.getLogger("loipen.osm")

# Der Hauptserver zuerst; verbietet seine robots.txt den Abruf oder ist er nicht erreichbar, der naechste
OVERPASS_URLS = ["https://overpass-api.de/api/interpreter?data={abfrage}",
                 "https://overpass.kumi.systems/api/interpreter?data={abfrage}",
                 "https://overpass.private.coffee/api/interpreter?data={abfrage}"]
QUELLE = "OpenStreetMap"
LIZENZ = "© OpenStreetMap-Mitwirkende, ODbL 1.0"
LIZENZ_URL = "https://www.openstreetmap.org/copyright"
ALTER_TAGE = 7
RAND_GRAD = 0.03  # Rand um die Loipen einer Region (etwa 3 km)
STRECKE_NAH_KM = 1.5
STRECKE_GEBIET_KM = 8.0
LAENGE_FAKTOR = 2.0
NAME_MIN = 0.5  # Jaccard der Namenswoerter
PARK_NAH_KM = 0.5
PARK_MAX = 2
MAX_PUNKTE = 400  # je Strecke, wie bei tourinfra
# Woerter, die allein nichts unterscheiden ("Rundloipe" gibt es in jedem Ort)
ALLGEMEIN = FUELLWOERTER | {"rund", "runde", "rundkurs", "tal", "panorama", "wald", "see", "dorf", "kleine", "grosse",
                            "gross", "klein", "hunde", "schlitten", "ski", "nordic", "cross", "country", "pista", "fondo", "anello",
                            "skating", "classic", "klassik", "nacht", "flutlicht", "verbindung", "verbindungsloipe",
                            "uebungs", "uebung", "trainings", "familien", "sport", "hoehen", "skiwanderweg",
                            "loipenrunde", "langlaufrunde", "langlaufzentrum", "zentrum", "variante", "teil"}
GESPERRT = {"private", "customers", "no", "permit", "delivery"}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * math.cos(math.radians(a[0])))


def laenge_km(linien: list[list[list[float]]]) -> float:
    return sum(km(tuple(p), tuple(q)) for linie in linien for p, q in zip(linie, linie[1:]))


def abfrage(sued: float, west: float, nord: float, ost: float) -> str:
    bbox = f"{sued:.4f},{west:.4f},{nord:.4f},{ost:.4f}"
    return f'[out:json][timeout:120];nwr["amenity"="parking"]({bbox});out tags center qt;'


def urls(bbox: tuple[float, float, float, float]) -> list[str]:
    return [u.format(abfrage=quote(abfrage(*bbox))) for u in OVERPASS_URLS]


def hole_parkplaetze(fetcher, bbox: tuple[float, float, float, float], aus: set[str] | None = None) -> list[dict]:
    """Erster Overpass-Server, der antwortet und dessen robots.txt den Abruf erlaubt (P7).
    aus: Server, die in diesem Lauf schon versagt haben; sie werden nicht noch einmal gefragt, damit ein
    ueberlasteter Server (504, Zeitueberschreitung) nicht jede Region um Minuten verzoegert."""
    aus = set() if aus is None else aus
    letzter: Exception | None = None
    for u in urls(bbox):
        server = u.split("/api/")[0]
        if server in aus:
            continue
        try:
            return verdichte(fetcher.get(u))["parkplaetze"]
        except Exception as e:
            letzter = e
            aus.add(server)
            log.info("Overpass %s: %s", server, e)
    raise letzter or RuntimeError("kein Overpass-Server erreichbar")


def _ausduennen(punkte: list[list[float]], max_punkte: int) -> list[list[float]]:
    if len(punkte) <= max_punkte:
        return punkte
    schritt = (len(punkte) - 1) / (max_punkte - 1)
    return [punkte[round(i * schritt)] for i in range(max_punkte)]


def _namen(tags: dict) -> list[str]:
    namen = [tags[k] for k in ("name", "name:de", "official_name", "alt_name", "piste:name", "short_name") if tags.get(k)]
    return list(dict.fromkeys(n for roh in namen for n in roh.split(";") if n.strip()))


def _gebuehr(tags: dict) -> str | None:
    fee = (tags.get("fee") or "").lower()
    if fee in ("yes", "ja"):
        return "gebührenpflichtig laut OpenStreetMap"
    if fee in ("no", "nein"):
        return "kostenlos laut OpenStreetMap"
    return None


def verdichte(antwort: str | dict) -> dict:
    """Overpass-JSON -> {"loipen": [...], "parkplaetze": [...]} mit nur den Feldern, die die Seite braucht."""
    daten = json.loads(antwort) if isinstance(antwort, str) else antwort
    loipen, parkplaetze = [], []
    for e in daten.get("elements", []):
        tags = e.get("tags") or {}
        oid = f"{e['type']}/{e['id']}"
        if tags.get("amenity") == "parking":
            if (tags.get("access") or "").lower() in GESPERRT or tags.get("parking") == "underground":
                continue
            if e["type"] == "node":
                lat, lon = e.get("lat"), e.get("lon")
            else:
                mitte = e.get("center") or {}
                lat, lon = mitte.get("lat"), mitte.get("lon")
            if lat is None:
                continue
            parkplaetze.append({"id": oid, "name": tags.get("name"), "lat": round(lat, 6), "lon": round(lon, 6),
                                "gebuehr_text": _gebuehr(tags)})
            continue
        if tags.get("piste:type") != "nordic":
            continue
        namen = _namen(tags)
        if not namen:
            continue  # unbenannte Wege werden nie zugeordnet
        if e["type"] == "way":
            linien = [[[round(p["lat"], 5), round(p["lon"], 5)] for p in e.get("geometry") or []]]
        else:
            linien = [[[round(p["lat"], 5), round(p["lon"], 5)] for p in m.get("geometry") or []]
                      for m in e.get("members") or [] if m.get("type") == "way"]
        linien = [l for l in linien if len(l) >= 2]
        if not linien:
            continue
        loipen.append({"id": oid, "namen": namen, "linien": linien, "laenge_km": round(laenge_km(linien), 2)})
    return {"loipen": loipen, "parkplaetze": parkplaetze}


# ---------- Abruf (Worker) ----------

WMT = "https://slopes.waymarkedtrails.org/api/v1"
WMT_KACHEL_GRAD = 0.2   # Kachelgroesse der Routenliste; volle Kacheln (100 Routen) werden geviertelt
WMT_LIMIT = 100
WMT_GRUPPE_NORDISCH = 2
GEOMETRIE_TAGE = 30
_R = 20037508.34


def _nach_3857(lat: float, lon: float) -> tuple[float, float]:
    return lon * _R / 180, math.log(math.tan((90 + lat) * math.pi / 360)) * _R / math.pi


def _nach_4326(x: float, y: float) -> list[float]:
    return [round(math.atan(math.exp(y / _R * math.pi)) * 360 / math.pi - 90, 5), round(x / _R * 180, 5)]


def wmt_liste_url(sued: float, west: float, nord: float, ost: float) -> str:
    x1, y1 = _nach_3857(sued, west)
    x2, y2 = _nach_3857(nord, ost)
    return f"{WMT}/list/by_area?bbox={x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}&limit={WMT_LIMIT}"


def wmt_routen(fetcher, bbox: tuple[float, float, float, float], tiefe: int = 0) -> dict[int, str]:
    """{Relation-ID: Name} der nordischen Routen in der bbox, in Kacheln abgefragt."""
    sued, west, nord, ost = bbox
    routen: dict[int, str] = {}
    lat = sued
    while lat < nord:
        lon = west
        while lon < ost:
            kachel = (lat, lon, min(lat + WMT_KACHEL_GRAD / 2 ** tiefe, nord), min(lon + WMT_KACHEL_GRAD / 2 ** tiefe, ost))
            ergebnis = json.loads(fetcher.get(wmt_liste_url(*kachel))).get("results") or []
            if len(ergebnis) >= WMT_LIMIT and tiefe < 2:
                routen.update(wmt_routen(fetcher, kachel, tiefe + 1))
            else:
                routen.update({r["id"]: r["name"] for r in ergebnis if r.get("type") == "relation"
                               and r.get("group") == WMT_GRUPPE_NORDISCH and r.get("name")})
            lon += WMT_KACHEL_GRAD / 2 ** tiefe
        lat += WMT_KACHEL_GRAD / 2 ** tiefe
    return routen


def _geometrien(knoten) -> list[list[list[float]]]:
    """Alle LineStrings aus der verschachtelten Routenstruktur von Waymarked Trails, in [lat, lon]."""
    linien = []
    if isinstance(knoten, dict):
        g = knoten.get("geometry")
        if isinstance(g, dict) and g.get("type") == "LineString":
            linien.append([_nach_4326(x, y) for x, y in g["coordinates"]])
        for wert in knoten.values():
            if isinstance(wert, (dict, list)) and wert is not g:
                linien += _geometrien(wert)
    elif isinstance(knoten, list):
        for wert in knoten:
            linien += _geometrien(wert)
    return linien


def wmt_route(text: str) -> dict | None:
    """Details einer Route -> {"id", "namen", "linien", "laenge_km"} wie bei verdichte()."""
    d = json.loads(text)
    if d.get("type") != "relation" or "route" not in d:
        return None
    linien = [l for l in _geometrien(d["route"]) if len(l) >= 2]
    if not linien:
        return None
    namen = _namen(d.get("tags") or {}) or ([d["name"]] if d.get("name") else [])
    laenge = (d["route"].get("length") or 0) / 1000 or laenge_km(linien)
    return {"id": f"relation/{d['id']}", "namen": namen, "linien": linien, "laenge_km": round(laenge, 2)}


def region_bbox(region: Region) -> tuple[float, float, float, float] | None:
    punkte = [(l.lat, l.lon) for g in region.gebiete for l in g.loipen if l.active and l.lat is not None]
    punkte += [(g.lat, g.lon) for g in region.gebiete if g.lat is not None]
    if not punkte:
        return None
    return (min(p[0] for p in punkte) - RAND_GRAD, min(p[1] for p in punkte) - RAND_GRAD,
            max(p[0] for p in punkte) + RAND_GRAD, max(p[1] for p in punkte) + RAND_GRAD)


@dataclass
class OsmLauf:
    abgerufen: list[str] = field(default_factory=list)
    fehler: list[str] = field(default_factory=list)


def _gesucht(region: Region, auch_mit_strecke: bool = False) -> list[tuple[str, str]]:
    """(Loipenname, Gebietsname) aller aktiven Loipen der Region ohne eigenen Streckenverlauf."""
    return [(l.name, g.name) for g in region.gebiete for l in g.loipen
            if l.active and (auch_mit_strecke or not l.verlauf)]


def aktualisiere(session: Session, fetcher, jetzt: datetime | None = None, hoechstens: int = 12,
                 auch_mit_strecke: bool = False) -> OsmLauf:
    """Holt die Regionen, deren OSM-Daten fehlen oder aelter als eine Woche sind (aelteste zuerst).
    hoechstens begrenzt die Regionen je Lauf, damit sich die Last ueber die Laeufe verteilt.
    auch_mit_strecke holt auch Routen zu Loipen mit eigener Strecke (nur fuer vergleiche() im OSM-Abgleich)."""
    jetzt = jetzt or utcnow()
    lauf = OsmLauf()
    overpass_aus: set[str] = set()
    vorhanden = {d.region_slug: d for d in session.scalars(select(OsmDaten))}
    faellig = []
    for region in session.scalars(select(Region)):
        bbox = region_bbox(region)
        if bbox is None or not _gesucht(region, auch_mit_strecke):
            continue
        d = vorhanden.get(region.slug)
        bbox = tuple(round(x, 4) for x in bbox)
        if d is None or d.abgerufen_at < jetzt - timedelta(days=ALTER_TAGE) or d.bbox != list(bbox):
            faellig.append((d.abgerufen_at if d else datetime.min.replace(tzinfo=jetzt.tzinfo), region, bbox))
    for _, region, bbox in sorted(faellig, key=lambda x: x[0])[:hoechstens]:
        d = vorhanden.get(region.slug)
        alt = (d.inhalt if d else None) or {}
        alte_loipen = {o["id"]: o for o in alt.get("loipen", [])
                       if o.get("geholt") and o["geholt"] >= (jetzt - timedelta(days=GEOMETRIE_TAGE)).isoformat()}
        try:
            routen = wmt_routen(fetcher, bbox)
        except Exception as e:  # OSM darf den Lauf nie verhindern
            lauf.fehler.append(f"{region.slug}: Routenliste: {e}")
            log.warning("Waymarked Trails fuer %s nicht abrufbar: %s", region.slug, e)
            continue
        gesucht = _gesucht(region, auch_mit_strecke)
        loipen = []
        for rid, name in sorted(routen.items()):
            if not any(name_passt(n, [name], ort) for n, ort in gesucht):
                continue  # nur Routen holen, die zu einer Loipe ohne Strecke passen koennen
            oid = f"relation/{rid}"
            if oid in alte_loipen:
                loipen.append(alte_loipen[oid])
                continue
            try:
                route = wmt_route(fetcher.get(f"{WMT}/details/relation/{rid}"))
            except Exception as e:
                lauf.fehler.append(f"{region.slug}: Route {rid}: {e}")
                continue
            if route:
                loipen.append({**route, "geholt": jetzt.isoformat()})
        try:
            parkplaetze = hole_parkplaetze(fetcher, bbox, overpass_aus)
        except Exception as e:
            lauf.fehler.append(f"{region.slug}: Parkplaetze: {e}")
            parkplaetze = alt.get("parkplaetze", [])
        d = d or OsmDaten(region_slug=region.slug)
        d.bbox, d.abgerufen_at = list(bbox), jetzt
        d.inhalt = {"loipen": loipen, "parkplaetze": parkplaetze, "routen": len(routen)}
        session.add(d)
        lauf.abgerufen.append(region.slug)
    session.flush()
    return lauf


# ---------- Zuordnung (Generator) ----------

def _woerter(name: str, orte: str) -> set[str]:
    return {w for w in woerter(name, orte) if len(w) >= 3}


def _widerspruch(a: str, b: str) -> bool:
    """Beide Namen haben ein eigenes unterscheidendes Wort, das der andere nicht hat, auch mit Ortsnamen gezaehlt:
    "Isola-Sils" ist nicht "Maloja-Isola", "Sportplatzrunde (kleine Runde)" nicht "(grosse Runde)".
    Aehnlich geschriebene Woerter ("Bayrischzell"/"Bayerischzell") zaehlen als gleich."""
    wa = {w for w in woerter(a) if len(w) >= 3} - (ALLGEMEIN - {"kleine", "grosse", "klein", "gross"})
    wb = {w for w in woerter(b) if len(w) >= 3} - (ALLGEMEIN - {"kleine", "grosse", "klein", "gross"})
    nur_a = {x for x in wa - wb if not any(SequenceMatcher(None, x, y).ratio() >= 0.8 for y in wb)}
    nur_b = {y for y in wb - wa if not any(SequenceMatcher(None, x, y).ratio() >= 0.8 for x in wa)}
    return bool(nur_a and nur_b)


def name_wert(loipe: str, osm_namen: list[str], orte: str) -> float:
    """Aehnlichkeit 0..1 zwischen Loipenname und dem besten OSM-Namen: Anteil gemeinsamer Woerter (Jaccard) ohne
    Ortsnamen, Fuellwoerter, Nummern und Laengen. Gemeinsam muss mindestens ein unterscheidendes Wort sein
    ("Kleine Toblacher See Runde" ist nicht "Toblacher Stadionrunde", "Dorfloipe Pertisau" nicht
    "Uebungsloipe Pertisau"). Bleibt ohne Ortsnamen nichts uebrig, zaehlt nur der gleiche ganze Name."""
    a = _woerter(loipe, orte)
    bester = 0.0
    for n in osm_namen:
        b = _woerter(n, orte)
        if not a or not b:
            if schluessel(loipe) and schluessel(loipe) == schluessel(n):
                bester = max(bester, 1.0)
            continue
        gemeinsam = a & b
        if not gemeinsam - ALLGEMEIN or _widerspruch(loipe, n):
            continue
        bester = max(bester, len(gemeinsam) / len(a | b))
    return bester


def name_passt(loipe: str, osm_namen: list[str], orte: str) -> bool:
    return name_wert(loipe, osm_namen, orte) >= NAME_MIN


def _abstand_zur_linie(punkt: tuple[float, float], linien: list[list[list[float]]]) -> float:
    return min(km(punkt, tuple(p)) for linie in linien for p in linie)


def strecke_fuer(loipe: dict, gebiet: dict, osm_loipen: list[dict]) -> dict | None:
    """Die passende OSM-Strecke fuer eine Loipe der Seite (dict aus daten._loipe) oder None.
    Unter mehreren passenden gewinnt der aehnlichste Name, dann die passendere Laenge, dann die kleinere Entfernung."""
    orte = gebiet.get("name") or ""
    start = (loipe["lat"], loipe["lon"]) if loipe.get("lat") is not None else None
    mitte = (gebiet["lat"], gebiet["lon"]) if gebiet.get("lat") is not None else None
    if start is None and mitte is None:
        return None
    kandidaten = []
    for o in osm_loipen:
        wert = name_wert(loipe["name"], o["namen"], orte)
        if wert < NAME_MIN:
            continue
        abstand = _abstand_zur_linie(start or mitte, o["linien"])
        if abstand > (STRECKE_NAH_KM if start else STRECKE_GEBIET_KM):
            continue
        abweichung = 0.0
        if loipe.get("laenge_km") and o["laenge_km"]:
            verhaeltnis = o["laenge_km"] / loipe["laenge_km"]
            if not (1 / LAENGE_FAKTOR <= verhaeltnis <= LAENGE_FAKTOR):
                continue
            abweichung = abs(math.log(verhaeltnis))
        kandidaten.append(((-wert, round(abweichung, 1), abstand), o))
    if not kandidaten:
        return None
    kandidaten.sort(key=lambda x: x[0])
    if not start and len(kandidaten) > 1 and kandidaten[1][0][:2] == kandidaten[0][0][:2] \
            and kandidaten[1][0][2] - kandidaten[0][0][2] < 1.0:
        return None  # ohne Startpunkt zwei gleich gute, aehnlich nahe Kandidaten: nicht raten
    return kandidaten[0][1]


def parkplaetze_bei(punkt: tuple[float, float], osm_parkplaetze: list[dict]) -> list[dict]:
    nah = sorted(((km(punkt, (p["lat"], p["lon"])), p) for p in osm_parkplaetze), key=lambda x: x[0])
    return [{"name": p["name"] or "Parkplatz", "lat": p["lat"], "lon": p["lon"], "gebuehr_text": p["gebuehr_text"],
             "entfernung_m": int(round(a * 1000, -1)), "quelle": QUELLE,
             "url": f"https://www.openstreetmap.org/{p['id']}"}
            for a, p in nah if a <= PARK_NAH_KM][:PARK_MAX]


def linien_fuer_seite(linien: list[list[list[float]]]) -> list[list[list[float]]]:
    gesamt = sum(len(l) for l in linien)
    if gesamt <= MAX_PUNKTE:
        return linien
    return [_ausduennen(l, max(2, round(MAX_PUNKTE * len(l) / gesamt))) for l in linien]


@dataclass
class Vergleich:
    geprueft: int = 0
    zugeordnet: int = 0
    richtig: int = 0
    falsch: list[str] = field(default_factory=list)


def vergleiche(session: Session, nah_km: float = 0.3) -> Vergleich:
    """Treffergüte (P38): Loipen mit eigener Strecke (tourinfra) so zuordnen, als haetten sie keine, und pruefen,
    ob die OSM-Strecke auf der eigenen liegt (mittlerer Abstand der OSM-Punkte unter nah_km)."""
    from loipen.models import Loipe  # noqa: PLC0415
    from loipen.wetter import gebiet_position  # noqa: PLC0415

    daten = lade(session)
    v = Vergleich()
    for l in session.scalars(select(Loipe).where(Loipe.active, Loipe.verlauf.is_not(None))):
        region = l.gebiet.region.slug if l.gebiet.region else ""
        if region not in daten:
            continue
        v.geprueft += 1
        pos = gebiet_position(l.gebiet)
        o = strecke_fuer({"name": l.name, "lat": l.lat, "lon": l.lon, "laenge_km": l.laenge_km},
                         {"name": l.gebiet.name, "lat": pos[0] if pos else None, "lon": pos[1] if pos else None},
                         daten[region].get("loipen", []))
        if not o:
            continue
        v.zugeordnet += 1
        eigen = [[[lat, lon] for lon, lat in l.verlauf["coordinates"]]]
        punkte = [p for linie in o["linien"] for p in linie]
        mittel = sum(_abstand_zur_linie(tuple(p), eigen) for p in punkte) / len(punkte)
        if mittel <= nah_km:
            v.richtig += 1
        else:
            v.falsch.append(f"{l.name} ({l.quelle.key}) -> {o['namen'][0]} ({o['id']}), {mittel:.2f} km daneben")
    return v


def lade(session: Session) -> dict[str, dict]:
    return {d.region_slug: d.inhalt for d in session.scalars(select(OsmDaten))}
