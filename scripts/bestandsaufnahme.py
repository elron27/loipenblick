"""Bestandsaufnahme Strecken und Parkinfos (D20) aus einer erzeugten Seite.

    python scripts/bestandsaufnahme.py --seite site --ausgabe docs/bestandsaufnahme-strecken-parken.md

--seite: Ordner mit daten.json (auf dem NAS der Ordner der Vorschau, im Workflow das Artefakt live-seite).
Ohne --ausgabe wird die Tabelle nur ausgegeben.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loipen.bestandsaufnahme import als_markdown, lies_seite  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seite", type=Path, default=Path("site"))
    ap.add_argument("--ausgabe", type=Path)
    ap.add_argument("--hinweis", default="", help="Satz zur Herkunft der Daten, steht unter der Überschrift")
    args = ap.parse_args()
    text = als_markdown(lies_seite(args.seite), hinweis=args.hinweis)
    if args.ausgabe:
        args.ausgabe.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
