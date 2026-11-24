"""D23: Hoehe der Loipen mit Streckenverlauf aus dem Copernicus-Hoehenmodell GLO-30 berechnen.

Laeuft im Workflow "Stammdaten" (Auftrag "hoehe") nach dem Aufbau der Seite aus den Schnappschuessen. Liest die
Streckenverlaeufe der erzeugten Seite (--seite, strecken/*.json), ordnet sie ueber die Datenbank des Laufs
(LOIPEN_DATABASE_URL) Quelle und source_key zu und liest die Hoehen aus den Kacheln im offenen AWS-Bucket
(kein Konto noetig). Ergebnis: config/stammdaten/hoehe.yaml mit herkunft "berechnet" (D21), nur wenn der
Abgleich mit den Hoehenmetern laut Quelle (config/stammdaten/tourinfra.yaml) besteht (D23 AK 2).

    python scripts/hoehe_dem.py --seite .stamm/site
"""

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loipen import hoehe  # noqa: E402

ZIEL = ROOT / "config" / "stammdaten" / "hoehe.yaml"
log = logging.getLogger("hoehe_dem")


class Hoehenmodell:
    def __init__(self):
        import rasterio  # nur im Workflow installiert
        self.rasterio = rasterio
        self.offen: dict[str, object] = {}

    def hoehen(self, punkte: list[tuple[float, float]]) -> list[float | None]:
        werte: list[float | None] = []
        for lat, lon in punkte:
            url = hoehe.kachel(lat, lon)
            ds = self.offen.get(url)
            if ds is None:
                try:
                    ds = self.rasterio.open(url)
                except Exception:  # Kachel fehlt (Meer) oder Netzfehler
                    ds = False
                self.offen[url] = ds
            if not ds:
                werte.append(None)
                continue
            wert = next(ds.sample([(lon, lat)]))[0]
            werte.append(float(wert) if wert is not None else None)
        return werte


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seite", type=Path, required=True)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from loipen.models import Loipe

    index = json.loads((args.seite / "daten.json").read_text(encoding="utf-8"))
    strecken: dict[int, list] = {}
    for r in index["regionen"]:
        pfad = args.seite / r["strecken"]
        if pfad.exists():
            for lid, linie in json.loads(pfad.read_text(encoding="utf-8")).items():
                strecken[int(lid)] = linie
    quelle_hm = {}
    td = ROOT / "config" / "stammdaten" / "tourinfra.yaml"
    if td.exists():
        for q, loipen in ((yaml.safe_load(td.read_text(encoding="utf-8")) or {}).get("quellen") or {}).items():
            for sk, w in (loipen or {}).items():
                if w.get("hoehenmeter"):
                    quelle_hm[(q, str(sk))] = w["hoehenmeter"]

    modell = Hoehenmodell()
    ergebnis: dict[str, dict] = {}
    vergleich = []
    engine = create_engine(os.environ["LOIPEN_DATABASE_URL"])
    with Session(engine) as s:
        loipen = {l.id: l for l in s.scalars(select(Loipe).where(Loipe.id.in_(list(strecken))))}
        for lid, linie in strecken.items():
            l = loipen.get(lid)
            if l is None:
                continue
            teile = linie if linie and isinstance(linie[0][0], list) else [linie]
            hoehen: list[float | None] = []
            for teil in teile:
                hoehen += modell.hoehen(hoehe.verdichte([(p[0], p[1]) for p in teil]))
            k = hoehe.kennzahlen(hoehen)
            if not k:
                continue
            schluessel = (l.quelle.key, l.source_key)
            if schluessel in quelle_hm:
                vergleich.append((k["hoehenmeter"], quelle_hm[schluessel]))
            ergebnis.setdefault(l.quelle.key, {})[l.source_key] = {**k, "url": hoehe.QUELLENANGABE,
                                                                   "geprueft_am": date.today().isoformat()}
    ok, abw = hoehe.freigabe(vergleich)
    log.info("Hoehe berechnet fuer %d Loipen; Abgleich an %d Loipen, Median-Abweichung %s",
             sum(len(v) for v in ergebnis.values()), len(vergleich), f"{abw:.0%}" if abw is not None else "-")
    if not ok:
        log.error("Abgleich nicht bestanden (D23 AK 2): nichts uebernommen")
        return 0
    ZIEL.write_text(
        "# D23: Hoehe aus dem Copernicus DEM GLO-30, erzeugt von scripts/hoehe_dem.py (herkunft berechnet, D21).\n"
        f"# Abgleich mit den Hoehenmetern laut Quelle: {len(vergleich)} Loipen, Median-Abweichung {abw:.0%}.\n"
        + yaml.safe_dump({"herkunft": "berechnet", "quellen": ergebnis}, allow_unicode=True, sort_keys=True, width=120),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
