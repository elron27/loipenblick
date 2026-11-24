"""B32: Saisonpruefung der Handangaben. Ruft jede Quell-URL einmal ab (hoeflich, mit Pause) und schreibt einen
Bericht als Markdown, den der Workflow "Saisonpruefung" als GitHub-Issue oeffnet.

    python scripts/saisonpruefung.py --ausgabe saisonpruefung.md
"""

import argparse
import logging
import os
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loipen import saison  # noqa: E402

log = logging.getLogger("saisonpruefung")


def abrufen(url: str, agent: str) -> tuple[int | None, str | None]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": agent})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001 - Netzfehler zaehlt als nicht erreichbar
        return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ausgabe", type=Path, default=Path("saisonpruefung.md"))
    ap.add_argument("--ohne-abruf", action="store_true", help="nur die Liste, keine Seiten abrufen")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    agent = os.environ.get("LOIPEN_USER_AGENT", "LoipenBot/0.1 (+https://github.com/elron27/loipenblick)")
    pause = float(os.environ.get("LOIPEN_REQUEST_DELAY_S", "3"))
    heute = date.today()
    angaben = saison.lade(ROOT / "config")
    seiten: dict[str, tuple[int | None, str | None]] = {}
    for a in angaben:
        if a.url and not args.ohne_abruf and a.url not in seiten:
            seiten[a.url] = abrufen(a.url, agent)
            time.sleep(pause)
        status, text = seiten.get(a.url, (200, None)) if a.url else (None, None)
        a.befund = saison.pruefe(a, status, text, heute)
    args.ausgabe.write_text(saison.bericht(angaben, heute), encoding="utf-8")
    log.info("%d Handangaben, %d mit Befund", len(angaben), sum(1 for a in angaben if a.befund))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
