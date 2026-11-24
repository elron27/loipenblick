"""P42: Detailseiten aller tourinfra-Loipen einmal auslesen und als Stammdaten ablegen.

Liest den Loipenmanager jeder tourinfra-Quelle aus config/sources.yaml (abgelehnte Quellen nie, B30), dann
details.php je Loipe mit HoeflicherFetcher (robots.txt, mindestens 5 s Abstand je Host, P7). Ergebnis:
config/stammdaten/tourinfra.yaml. Loipen, die schon einen Eintrag haben, werden nicht noch einmal abgerufen
(P42 AK 4), ausser mit --alle.

Nur Fakten (Dauer, Hoehenmeter, Tief- und Hochpunkt, Merkmale, Webcam-Links), keine Beschreibung (E-40).
Laeuft im Workflow "Stammdaten" auf einem GitHub-Runner, weil die Cloud-Umgebung tourinfra nicht erreicht:

    python scripts/tourinfra_details.py [--quelle engadin] [--alle] [--max 50]
"""

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loipen.adapters.tourinfra import parse_details  # noqa: E402
from loipen.fetcher import HoeflicherFetcher  # noqa: E402
from loipen.konfig import lade_yaml  # noqa: E402

ZIEL = ROOT / "config" / "stammdaten" / "tourinfra.yaml"
KOPF = (
    "# P42/D21: Stammdaten der tourinfra-Loipen aus den Detailseiten (details.php), erzeugt von\n"
    "# scripts/tourinfra_details.py. Nur Fakten, keine Beschreibungstexte (E-40). Von Hand nicht aendern:\n"
    "# Handangaben gehoeren nach config/stammdaten/hand.yaml (sie gehen vor, D21 AK 3).\n"
)

log = logging.getLogger("tourinfra_details")


def lade_bestand() -> dict:
    if ZIEL.exists():
        return (yaml.safe_load(ZIEL.read_text(encoding="utf-8")) or {}).get("quellen") or {}
    return {}


def schreibe(bestand: dict) -> None:
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    inhalt = {"herkunft": "quelle", "quellen": {k: dict(sorted(v.items())) for k, v in sorted(bestand.items())}}
    ZIEL.write_text(KOPF + yaml.safe_dump(inhalt, allow_unicode=True, sort_keys=False, width=120),
                    encoding="utf-8")


def eintraege(fetcher: HoeflicherFetcher, q: dict) -> list[dict]:
    daten = json.loads(fetcher.get(q["base_url"].rstrip("/") + q["config"]["json_path"]))
    liste = daten.values() if isinstance(daten, dict) else daten
    return [e for e in liste if isinstance(e, dict) and e.get("tid") and e.get("link")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quelle", action="append", help="nur diese Quelle(n)")
    ap.add_argument("--alle", action="store_true", help="auch Loipen mit Eintrag neu lesen")
    ap.add_argument("--max", type=int, default=0, help="hoechstens so viele Detailseiten je Lauf (0 = alle)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    quellen = [q for q in lade_yaml(ROOT / "config" / "sources.yaml")["quellen"]
               if q["adapter"] == "tourinfra" and (q.get("nutzung") or {}).get("erlaubnis") != "abgelehnt"
               and (not args.quelle or q["key"] in args.quelle)]
    ua = os.environ.get("LOIPEN_USER_AGENT") or "LoipenBot/0.1 (+https://github.com/elron27/loipenblick)"
    fetcher = HoeflicherFetcher(ua, delay_s=max(5.0, float(os.environ.get("LOIPEN_REQUEST_DELAY_S", "5"))))
    bestand = lade_bestand()
    heute = date.today().isoformat()
    abgerufen = fehler = 0
    unbekannt: dict[str, int] = {}
    try:
        for q in quellen:
            vorhanden = bestand.setdefault(q["key"], {})
            try:
                liste = eintraege(fetcher, q)
            except Exception as e:  # eine Quelle darf die anderen nicht stoppen
                log.error("%s: Loipenmanager nicht lesbar: %s", q["key"], e)
                fehler += 1
                continue
            for e in liste:
                tid = str(e["tid"])
                if tid in vorhanden and not args.alle:
                    continue
                if args.max and abgerufen >= args.max:
                    break
                url = urljoin(q["base_url"].rstrip("/") + "/", e["link"])
                try:
                    werte = parse_details(fetcher.get(url), e.get("startort"))
                except Exception as ex:
                    log.warning("%s %s: %s", q["key"], tid, ex)
                    fehler += 1
                    continue
                abgerufen += 1
                for b in werte.pop("unbekannte_merkmale", []):
                    unbekannt[b] = unbekannt.get(b, 0) + 1
                vorhanden[tid] = {**werte, "url": url, "geprueft_am": heute}
            schreibe(bestand)  # nach jeder Quelle sichern
            log.info("%s: %d Loipen mit Stammdaten", q["key"], len(vorhanden))
    finally:
        fetcher.close()
    schreibe(bestand)
    log.info("Detailseiten gelesen: %d, Fehler: %d", abgerufen, fehler)
    if unbekannt:
        log.info("Unbekannte Merkmale: %s", ", ".join(f"{k} ({v})" for k, v in sorted(unbekannt.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
