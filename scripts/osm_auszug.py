"""D22, D24: Haltestellen, Parkplaetze und Skiverleih aus einem OpenStreetMap-Auszug, Entfernung als echte Route.

Laeuft im Workflow "Stammdaten" (Auftrag "osm") auf einem GitHub-Runner. Kein oeffentlicher Overpass- oder
Routing-Server (P39: Overpass ist vom Runner aus unbrauchbar; der OSRM-Demoserver erlaubt keine Massenabfragen):

1. Geofabrik-Auszuege der abgedeckten Laender laden und zu einer Datei mischen (osmium).
2. Je Region einen Ausschnitt um alle Loipenstarts schneiden (20 km Rand).
3. Daraus Haltestellen, Parkplaetze und Verleihe filtern (osmium tags-filter + export).
4. OSRM fuer Fussweg und Auto auf dem Ausschnitt vorbereiten (Docker, MLD) und je Gebiet eine Zeitmatrix
   zwischen Kandidaten und Loipenstarts abfragen.
5. Ergebnis als config/osm/<region>.yaml (D22 AK 1), gelesen von loipen/konfig.py.

Die Loipenstarts kommen aus einer erzeugten Seite (--seite, daten.json wie bei der Bestandsaufnahme).

    python scripts/osm_auszug.py --seite .osm/site [--region tegernsee-schliersee] [--arbeitsordner .osm-auszug]

Lizenz: ODbL 1.0, Quellenvermerk "© OpenStreetMap-Mitwirkende" (D22 AK 2).
"""

import argparse
import json
import logging
import math
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loipen.osmauszug import (  # noqa: E402
    VERLEIH_LUFT_KM,
    bbox_um,
    gebiet_ergebnis,
    kandidaten,
    lies_regionen,
    pois_aus_geojson,
    starts_je_gebiet,
)

GEOFABRIK = [
    "europe/germany/bayern-latest.osm.pbf",
    "europe/germany/baden-wuerttemberg-latest.osm.pbf",
    "europe/austria-latest.osm.pbf",
    "europe/switzerland-latest.osm.pbf",
    "europe/liechtenstein-latest.osm.pbf",
    "europe/italy/nord-est-latest.osm.pbf",
]
OSRM_BILD = "ghcr.io/project-osrm/osrm-backend:v5.27.1"
FILTER = ["nwr/highway=bus_stop", "nwr/railway=station,halt", "nwr/public_transport=platform,stop_position,station",
          "nwr/amenity=parking", "nwr/shop=ski", "nwr/rental=ski", "nwr/service:ski:rental=yes"]
ZIEL = ROOT / "config" / "osm"
log = logging.getLogger("osm_auszug")


def sh(*befehl: str, **kw) -> None:
    log.info("$ %s", " ".join(befehl))
    subprocess.run(befehl, check=True, **kw)


def lade_auszuege(ordner: Path) -> Path:
    gemischt = ordner / "alle.osm.pbf"
    if gemischt.exists():
        return gemischt
    dateien = []
    for pfad in GEOFABRIK:
        datei = ordner / pfad.rsplit("/", 1)[-1]
        if not datei.exists():
            sh("curl", "-sSfL", "--retry", "3", "-o", str(datei), f"https://download.geofabrik.de/{pfad}")
        dateien.append(str(datei))
    sh("osmium", "merge", "--overwrite", "-o", str(gemischt), *dateien)
    return gemischt


class Osrm:
    """Ein OSRM-Server je Profil fuer einen Ausschnitt, ueber Docker."""

    def __init__(self, ordner: Path, ausschnitt: Path, profil: str, port: int):
        self.port = port
        self.name = f"osrm-{profil}-{port}"
        basis = f"/data/{ausschnitt.stem.split('.')[0]}-{profil}"
        pbf = ordner / f"{ausschnitt.stem.split('.')[0]}-{profil}.osm.pbf"
        pbf.write_bytes(ausschnitt.read_bytes())
        run = ["docker", "run", "--rm", "-v", f"{ordner.resolve()}:/data", OSRM_BILD]
        sh(*run, "osrm-extract", "-p", f"/opt/{profil}.lua", f"{basis}.osm.pbf", stdout=subprocess.DEVNULL)
        sh(*run, "osrm-partition", f"{basis}.osrm", stdout=subprocess.DEVNULL)
        sh(*run, "osrm-customize", f"{basis}.osrm", stdout=subprocess.DEVNULL)
        sh("docker", "run", "-d", "--rm", "--name", self.name, "-p", f"{port}:5000", "-v",
           f"{ordner.resolve()}:/data", OSRM_BILD, "osrm-routed", "--algorithm", "mld", "--max-table-size", "10000",
           f"{basis}.osrm", stdout=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://localhost:{port}/nearest/v1/x/0,0", timeout=2)
                break
            except Exception as e:  # noqa: BLE001 - Server startet noch
                if "400" in str(e):
                    break
                time.sleep(1)

    def tabelle(self, quellen: list[tuple[float, float]], ziele: list[tuple[float, float]]) -> list[list]:
        """Dauer in Sekunden von jeder Quelle zu jedem Ziel (None = keine Verbindung)."""
        punkte = quellen + ziele
        coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in punkte)
        q = ";".join(str(i) for i in range(len(quellen)))
        z = ";".join(str(i) for i in range(len(quellen), len(punkte)))
        url = f"http://localhost:{self.port}/table/v1/x/{coords}?sources={q}&destinations={z}"
        with urllib.request.urlopen(url, timeout=120) as r:
            return json.load(r)["durations"]

    def stop(self) -> None:
        subprocess.run(["docker", "stop", self.name], check=False, stdout=subprocess.DEVNULL)


def region_auswerten(ordner: Path, alle: Path, region: str, gebiete: list[dict], port: int) -> dict:
    starts = starts_je_gebiet(gebiete)
    punkte = [p for s in starts.values() for p in s]
    if not punkte:
        return {}
    sued, west, nord, ost = bbox_um(punkte, VERLEIH_LUFT_KM + 2)
    ausschnitt = ordner / f"{region}.osm.pbf"
    sh("osmium", "extract", "--overwrite", "-s", "smart", "-b", f"{west},{sued},{ost},{nord}", "-o",
       str(ausschnitt), str(alle))
    gefiltert = ordner / f"{region}-pois.osm.pbf"
    sh("osmium", "tags-filter", "--overwrite", "-o", str(gefiltert), str(ausschnitt), *FILTER)
    geojson = ordner / f"{region}-pois.geojson"
    sh("osmium", "export", "--overwrite", "-f", "geojsonseq", "-o", str(geojson), str(gefiltert))
    pois = pois_aus_geojson(geojson.read_text(encoding="utf-8"))
    fuss = Osrm(ordner, ausschnitt, "foot", port)
    auto = Osrm(ordner, ausschnitt, "car", port + 1)
    try:
        ergebnis = {}
        for slug, start in starts.items():
            k = kandidaten(start, pois)
            zeiten = {}
            if k["haltestellen"]:
                zeiten["fuss_halt"] = fuss.tabelle([p["lage"] for p in k["haltestellen"]], start)
            if k["parkplaetze"]:
                zeiten["fuss_park"] = fuss.tabelle([p["lage"] for p in k["parkplaetze"]], start)
            if k["verleih"]:
                zeiten["auto_verleih"] = auto.tabelle([p["lage"] for p in k["verleih"]], start)
                zeiten["fuss_verleih"] = fuss.tabelle([p["lage"] for p in k["verleih"]], start)
            ergebnis[slug] = gebiet_ergebnis(k, zeiten)
        return ergebnis
    finally:
        fuss.stop()
        auto.stop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seite", type=Path, required=True)
    ap.add_argument("--region", action="append")
    ap.add_argument("--arbeitsordner", type=Path, default=Path(".osm-auszug"))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.arbeitsordner.mkdir(parents=True, exist_ok=True)
    seite = lies_regionen(args.seite)
    alle = lade_auszuege(args.arbeitsordner)
    ZIEL.mkdir(parents=True, exist_ok=True)
    heute = date.today().isoformat()
    port = 5100
    for region, gebiete in sorted(seite.items()):
        if args.region and region not in args.region:
            continue
        try:
            ergebnis = region_auswerten(args.arbeitsordner, alle, region, gebiete, port)
        except Exception:  # eine Region darf die anderen nicht stoppen
            log.exception("Region %s fehlgeschlagen", region)
            continue
        inhalt = {"quelle": "© OpenStreetMap-Mitwirkende, ODbL 1.0", "stand": heute, "gebiete": ergebnis}
        (ZIEL / f"{region}.yaml").write_text(
            "# D22/D24: erzeugt von scripts/osm_auszug.py, nicht von Hand aendern (Handangaben in gebiete.yaml)\n"
            + yaml.safe_dump(inhalt, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        log.info("%s: %d Gebiete, %d Haltestellen, %d Verleihe", region, len(ergebnis),
                 sum(len(g["haltestellen"]) for g in ergebnis.values()),
                 sum(len(g["verleih"]) for g in ergebnis.values()))
        port += 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
