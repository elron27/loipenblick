"""D22, D24: Auswertung eines OSM-Auszugs fuer Haltestellen, Parkplaetze und Skiverleih (ohne Netzzugriff).

Das Skript scripts/osm_auszug.py schneidet den Auszug, filtert die Objekte und fragt OSRM; die Regeln stehen hier,
damit sie ohne Runner testbar sind:

- Kandidaten per Luftlinie vorsortieren: Haltestellen bis 3 km, Parkplaetze bis 1 km, Verleih bis 20 km vom
  naechsten Loipenstart (D24 AK 1).
- Angezeigt werden Haltestellen mit hoechstens 20 Minuten Fussweg zum naechsten Loipenstart (D24 AK 3), je Name
  nur die naechste (Bahnsteige beider Richtungen), hoechstens drei.
- Verleihe mit hoechstens 15 Minuten Autofahrt (D24 AK 4), unter 10 Minuten Fussweg zusaetzlich mit Fussweg,
  hoechstens drei. shop=ski ohne Verleih-Tag gilt als "Skigeschaeft, Verleih nicht bestaetigt".
- Parkplaetze mit hoechstens 10 Minuten Fussweg, oeffentlich (ohne access=private/customers/no), hoechstens drei.
"""

import json
import math
from pathlib import Path

HALTESTELLE_LUFT_KM = 3.0
PARKPLATZ_LUFT_KM = 1.0
VERLEIH_LUFT_KM = 20.0
HALTESTELLE_MAX_MIN = 20
PARKPLATZ_MAX_MIN = 10
VERLEIH_AUTO_MAX_MIN = 15
VERLEIH_FUSS_MIN = 10
HOECHSTENS = 3
START_ABSTAND_KM = 0.1  # Loipenstarts naeher beieinander gelten als ein Start


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dlat = (a[0] - b[0]) * 111.2
    dlon = (a[1] - b[1]) * 111.2 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dlat, dlon)


def bbox_um(punkte: list[tuple[float, float]], rand_km: float) -> tuple[float, float, float, float]:
    lats = [p[0] for p in punkte]
    lons = [p[1] for p in punkte]
    dlat = rand_km / 111.2
    dlon = rand_km / (111.2 * math.cos(math.radians(sum(lats) / len(lats))))
    return min(lats) - dlat, min(lons) - dlon, max(lats) + dlat, max(lons) + dlon


def lies_regionen(site: Path) -> dict[str, list[dict]]:
    """Gebiete je Region aus einer erzeugten Seite (daten.json + daten/<region>.json)."""
    site = Path(site)
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    regionen = {}
    for r in index["regionen"]:
        daten = json.loads((site / r["datei"]).read_text(encoding="utf-8"))
        slug = r.get("slug") or (daten.get("region") or {}).get("slug") or Path(r["datei"]).stem
        regionen[slug] = daten["gebiete"]
    return regionen


def starts_je_gebiet(gebiete: list[dict]) -> dict[str, list[tuple[float, float]]]:
    """Loipenstarts je Gebiet (zusammengefasst, wenn naeher als 100 m); ohne Loipenstart die Gebietsmitte."""
    starts = {}
    for g in gebiete:
        punkte: list[tuple[float, float]] = []
        for l in g.get("loipen") or []:
            if l.get("lat") is None or l.get("lon") is None:
                continue
            p = (round(float(l["lat"]), 5), round(float(l["lon"]), 5))
            if all(km(p, q) >= START_ABSTAND_KM for q in punkte):
                punkte.append(p)
        if not punkte and g.get("lat") is not None and g.get("lon") is not None:
            punkte = [(float(g["lat"]), float(g["lon"]))]
        if punkte:
            starts[g["slug"]] = punkte
    return starts


def _mitte(geometrie: dict) -> tuple[float, float] | None:
    typ, c = geometrie.get("type"), geometrie.get("coordinates")
    if typ == "Point":
        return float(c[1]), float(c[0])
    flach: list = []

    def sammle(x):
        if x and isinstance(x[0], (int, float)):
            flach.append(x)
        else:
            for y in x:
                sammle(y)
    sammle(c or [])
    if not flach:
        return None
    return sum(p[1] for p in flach) / len(flach), sum(p[0] for p in flach) / len(flach)


def art_von(tags: dict) -> str | None:
    """haltestelle_bahn, haltestelle_bus, parkplatz, verleih, skigeschaeft oder None."""
    if tags.get("railway") in ("station", "halt") or tags.get("train") == "yes":
        if tags.get("railway") in ("station", "halt") or tags.get("public_transport"):
            return "haltestelle_bahn"
    if tags.get("highway") == "bus_stop" or tags.get("bus") == "yes" or tags.get("public_transport") in (
            "platform", "stop_position", "station"):
        if tags.get("railway") not in ("station", "halt") and tags.get("aerialway") is None:
            return "haltestelle_bus"
    if tags.get("amenity") == "parking":
        if tags.get("access") in ("private", "customers", "no") or tags.get("parking") in ("underground",):
            return None
        return "parkplatz"
    if tags.get("rental") == "ski" or "ski" in (tags.get("rental") or "").split(";") \
            or tags.get("service:ski:rental") == "yes":
        return "verleih"
    if tags.get("shop") == "ski":
        return "skigeschaeft"
    return None


def pois_aus_geojson(text: str) -> list[dict]:
    """GeoJSON-Seq von osmium export -> [{art, name, lage, url, tags}]."""
    pois = []
    for zeile in text.splitlines():
        zeile = zeile.strip().lstrip("\x1e")
        if not zeile:
            continue
        f = json.loads(zeile)
        tags = f.get("properties") or {}
        art = art_von(tags)
        lage = _mitte(f.get("geometry") or {})
        if art is None or lage is None:
            continue
        osm_id = str(f.get("id") or tags.get("@id") or "")
        url = None
        if "/" in osm_id:
            url = f"https://www.openstreetmap.org/{osm_id}"
        pois.append({"art": art, "name": (tags.get("name") or "").strip() or None, "lage": lage, "url": url,
                     "website": tags.get("website") or tags.get("contact:website"), "fee": tags.get("fee")})
    return pois


def kandidaten(starts: list[tuple[float, float]], pois: list[dict]) -> dict[str, list[dict]]:
    def naechster(p):
        return min(km(p["lage"], s) for s in starts)
    k = {"haltestellen": [], "parkplaetze": [], "verleih": []}
    for p in pois:
        d = naechster(p)
        if p["art"].startswith("haltestelle") and d <= HALTESTELLE_LUFT_KM and p["name"]:
            k["haltestellen"].append(p)
        elif p["art"] == "parkplatz" and d <= PARKPLATZ_LUFT_KM:
            k["parkplaetze"].append(p)
        elif p["art"] in ("verleih", "skigeschaeft") and d <= VERLEIH_LUFT_KM:
            k["verleih"].append(p)
    return k


def _minuten(zeile: list | None) -> int | None:
    werte = [s for s in (zeile or []) if s is not None]
    return math.ceil(min(werte) / 60) if werte else None


def gebiet_ergebnis(k: dict[str, list[dict]], zeiten: dict[str, list[list]]) -> dict[str, list[dict]]:
    """Waehlt aus den Kandidaten mit den OSRM-Zeiten (Sekunden je Kandidat und Loipenstart) die Anzeige."""
    halt = []
    for p, zeile in zip(k["haltestellen"], zeiten.get("fuss_halt") or []):
        m = _minuten(zeile)
        if m is not None and m <= HALTESTELLE_MAX_MIN:
            halt.append({"name": p["name"], "art": "Bahn" if p["art"] == "haltestelle_bahn" else "Bus",
                         "lat": round(p["lage"][0], 6), "lon": round(p["lage"][1], 6), "url": p["url"],
                         "fuss_min": m, "herkunft": "osm"})
    halt.sort(key=lambda h: (h["fuss_min"], h["art"] != "Bahn"))
    gesehen, haltestellen = set(), []
    for h in halt:
        if h["name"].lower() in gesehen:
            continue
        gesehen.add(h["name"].lower())
        haltestellen.append(h)

    parken = []
    for p, zeile in zip(k["parkplaetze"], zeiten.get("fuss_park") or []):
        m = _minuten(zeile)
        if m is not None and m <= PARKPLATZ_MAX_MIN:
            gebuehr = {"yes": "kostenpflichtig laut OpenStreetMap", "no": "kostenlos laut OpenStreetMap"}.get(p["fee"])
            parken.append({"id": (p["url"] or "").replace("https://www.openstreetmap.org/", "") or None,
                           "name": p["name"], "lat": round(p["lage"][0], 6),
                           "lon": round(p["lage"][1], 6), "url": p["url"], "fuss_min": m, "gebuehr_text": gebuehr,
                           "herkunft": "osm"})
    parken.sort(key=lambda x: x["fuss_min"])

    verleih = []
    auto = zeiten.get("auto_verleih") or []
    fuss = zeiten.get("fuss_verleih") or []
    for i, p in enumerate(k["verleih"]):
        a = _minuten(auto[i] if i < len(auto) else None)
        f = _minuten(fuss[i] if i < len(fuss) else None)
        if a is None or a > VERLEIH_AUTO_MAX_MIN:
            continue
        eintrag = {"name": p["name"] or "Skiverleih", "lat": round(p["lage"][0], 6), "lon": round(p["lage"][1], 6),
                   "url": p["website"] or p["url"], "osm": p["url"], "auto_min": a,
                   "verleih_bestaetigt": p["art"] == "verleih", "herkunft": "osm"}
        if f is not None and f < VERLEIH_FUSS_MIN:
            eintrag["fuss_min"] = f
        verleih.append(eintrag)
    verleih.sort(key=lambda v: (not v["verleih_bestaetigt"], v["auto_min"]))
    return {"haltestellen": haltestellen[:HOECHSTENS], "parkplaetze": parken[:HOECHSTENS],
            "verleih": verleih[:HOECHSTENS]}


# ---------- Einlesen (Worker, loipen/konfig.py und Generator) ----------

def lade(config_dir: Path) -> dict[str, dict]:
    """config/osm/*.yaml -> {gebiet_slug: {haltestellen, parkplaetze, verleih}}."""
    import yaml

    ergebnis: dict[str, dict] = {}
    ordner = Path(config_dir) / "osm"
    if not ordner.is_dir():
        return ergebnis
    for pfad in sorted(ordner.glob("*.yaml")):
        inhalt = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        for slug, werte in (inhalt.get("gebiete") or {}).items():
            ergebnis[slug] = werte or {}
    return ergebnis


def _gleich(a: dict, b: dict) -> bool:
    if a.get("name") and b.get("name") and a["name"].lower() == b["name"].lower():
        return True
    if None in (a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")):
        return False
    return km((a["lat"], a["lon"]), (b["lat"], b["lon"])) < 0.15


def zusammen(hand: list[dict] | None, osm: list[dict] | None) -> list[dict]:
    """D22 AK 3: Handangaben zuerst; OSM-Eintraege nur, wenn kein Handeintrag gleichen Namens oder in 150 m Naehe."""
    liste = [dict(h, herkunft=h.get("herkunft", "hand")) for h in (hand or [])]
    for o in osm or []:
        if not any(_gleich(h, o) for h in liste):
            liste.append(o)
    return liste
