"""Live-Pruefung: echte Quellen und echte Wetterdienste abrufen, Ergebnis pruefen, Antworten aufzeichnen.

Laeuft im Workflow "Live-Pruefung" (.github/workflows/live.yml) auf einem GitHub-Runner, der anders als
die Cloud-Umgebung ins Netz darf, oder lokal:

    LOIPEN_DATABASE_URL=postgresql+psycopg://loipen:loipen@localhost:5432/loipen_live \
        python scripts/live_pruefung.py --ausgabe .live

Ablauf wie ein Worker-Lauf (hoeflicher Abruf mit robots.txt und Abstand, P7), aber mit Bericht:
- je Quelle Anzahl Loipen, Fehler, Warnungen, unbekannte Begriffe
- Wetter: DWD-Messwerte und Bright-Sky-Vorhersage werden mit den echten Antworten geparst
- jede Antwort landet unter <ausgabe>/aufnahme/ (Fixture-Schnappschuss, CLAUDE.md Regel 10),
  DWD-ZIPs zusaetzlich unter <ausgabe>/aufnahme/wetter/dwd/ (Format der Attrappe im Teststack)
- die erzeugte Seite unter <ausgabe>/site/ (zum Anschauen ohne NAS)
- Bericht als Markdown nach <ausgabe>/bericht.md und, im Workflow, in die Job-Zusammenfassung

Exit-Code 1, wenn eine Quelle ausfaellt oder 0 Loipen liefert oder das Wetter nicht geparst werden kann.
Die Datenbank sollte eine eigene, leere sein (Migrationen vorher: alembic upgrade head).
"""

import argparse
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from loipen import generator  # noqa: E402
from loipen.ablauf import rufe_quelle_ab  # noqa: E402
from loipen.config import get_settings  # noqa: E402
from loipen.db import session_scope  # noqa: E402
from loipen.fetcher import HoeflicherFetcher  # noqa: E402
from loipen.konfig import lade_und_abgleichen  # noqa: E402
from loipen.models import Quelle  # noqa: E402
from loipen.wetter import aktualisiere_wetter  # noqa: E402


class Aufzeichner:
    """Leitet an den echten Fetcher weiter und speichert jede Antwort."""

    def __init__(self, fetcher: HoeflicherFetcher, ziel: Path):
        self.fetcher, self.ziel = fetcher, ziel
        self.anzahl = 0

    def _datei(self, url: str) -> Path:
        t = urlsplit(url)
        # flach, wie die Fixtures: /langlaufen/1 -> langlaufen_1 (sonst kollidiert es mit /langlaufen)
        name = t.path.strip("/").replace("/", "_") or "index"
        if t.query:
            name += "__" + re.sub(r"[^A-Za-z0-9._-]+", "_", t.query)
        return self.ziel / t.netloc / name

    def _speichere(self, url: str, inhalt: bytes) -> None:
        datei = self._datei(url)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(inhalt)
        self.anzahl += 1
        name = urlsplit(url).path.rsplit("/", 1)[-1]
        if name.startswith("tageswerte_RR_") and name.endswith(".zip"):
            dwd = self.ziel / "wetter" / "dwd" / name
            dwd.parent.mkdir(parents=True, exist_ok=True)
            dwd.write_bytes(inhalt)

    def get(self, url: str) -> str:
        text = self.fetcher.get(url)
        self._speichere(url, text.encode("utf-8"))
        return text

    def get_bytes(self, url: str) -> bytes:
        inhalt = self.fetcher.get_bytes(url)
        self._speichere(url, inhalt)
        return inhalt


class Sammler(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.meldungen: list[str] = []

    def emit(self, record):
        self.meldungen.append(record.getMessage())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ausgabe", type=Path, default=Path(".live"))
    ap.add_argument("--quelle", action="append", help="nur diese Quelle(n), Standard: alle")
    ap.add_argument("--ohne-wetter", action="store_true")
    ap.add_argument("--erlaube-umleitung", action="store_true", help="nur um das Skript gegen die Attrappe zu testen")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    sammler = Sammler()
    logging.getLogger("loipen").addHandler(sammler)

    settings = get_settings()
    if settings.umleitung and not args.erlaube_umleitung:
        print("LOIPEN_UMLEITUNG ist gesetzt, die Live-Pruefung braucht die echten Quellen.", file=sys.stderr)
        return 2
    ausgabe = args.ausgabe
    aufnahme = ausgabe / "aufnahme"
    fetcher = Aufzeichner(HoeflicherFetcher(settings.user_agent, settings.request_delay_s, umleitung=settings.umleitung), aufnahme)

    zeilen = [f"# Live-Prüfung {date.today():%d.%m.%Y}", "",
              "| Quelle | Loipen | Status | Fehler / Warnungen |", "| --- | ---: | --- | --- |"]
    probleme: list[str] = []
    with session_scope() as session:
        lade_und_abgleichen(session, Path(settings.config_dir))
        quellen = session.scalars(select(Quelle).where(Quelle.enabled).order_by(Quelle.key)).all()
        for q in quellen:
            if args.quelle and q.key not in args.quelle:
                continue
            lauf = rufe_quelle_ab(session, q, fetcher)
            text = lauf.fehler or "; ".join(lauf.warnungen)[:300] or ""
            zeilen.append(f"| {q.key} | {lauf.gefunden} | {lauf.status} | {text} |")
            if lauf.fehler or lauf.gefunden == 0:
                probleme.append(f"Quelle {q.key}: {lauf.fehler or '0 Loipen'}")
        if not args.ohne_wetter:
            wetter = aktualisiere_wetter(session, fetcher)
            zeilen += ["", f"**Wetter:** {wetter.messungen} DWD-Messwerte, {wetter.vorhersagen} Vorhersagewerte (Bright Sky)."]
            zeilen += [f"- {w}" for w in wetter.warnungen]
            if wetter.messungen == 0:
                probleme.append("Wetter: keine DWD-Messwerte geparst")
            if wetter.vorhersagen == 0:
                probleme.append("Wetter: keine Vorhersage geparst")
        generator.erzeuge(session, ausgabe / "site", config_dir=settings.config_dir, stale_days=settings.stale_days)

    unbekannt = sorted({m for m in sammler.meldungen if m.startswith("Unbekannter Quelltext")})
    if unbekannt:
        zeilen += ["", "**Unbekannte Begriffe** (Normalisierung ergänzen):"] + [f"- {m}" for m in unbekannt[:50]]
    zeilen += ["", f"{fetcher.anzahl} Antworten aufgezeichnet (Artefakt `live-aufnahme`), Seite im Artefakt `live-seite`."]
    zeilen += ["", "**Ergebnis:** " + ("alles in Ordnung" if not probleme else "Probleme:")] + [f"- {p}" for p in probleme]

    bericht = "\n".join(zeilen) + "\n"
    ausgabe.mkdir(parents=True, exist_ok=True)
    (ausgabe / "bericht.md").write_text(bericht, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(bericht)
    print(bericht)
    return 1 if probleme else 0


if __name__ == "__main__":
    sys.exit(main())
