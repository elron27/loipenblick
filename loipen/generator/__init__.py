"""Statische Website (E-10, B7).

Der Generator schreibt nach settings.site_dir: die App (HTML, JS, CSS, PWA-Dateien) aus
loipen/generator/static und die Daten als JSON (Index, je Region eine Datei, je Region die
Strecken). Genau dieser Ordner wird im Heimnetz vom Container "vorschau" ausgeliefert und
spaeter unveraendert auf einen Webspace hochgeladen (B12).
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from loipen.generator.daten import baue
from loipen.generator.icons import png_icon
from loipen.konfig import CONFIG_DIR

STATIC = Path(__file__).parent / "static"
HINWEIS = "Alle Angaben ohne Gewähr. Quelle und Stand stehen bei jedem Wert."


def _schreibe(ziel: Path, inhalt: str | bytes) -> None:
    """Schreibt atomar, damit nginx nie eine halbe Datei ausliefert."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ziel.parent, prefix=".tmp-")
    with os.fdopen(fd, "wb") as f:
        f.write(inhalt.encode("utf-8") if isinstance(inhalt, str) else inhalt)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ziel)


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def erzeuge(
    session: Session,
    site_dir: str | Path,
    jetzt: datetime | None = None,
    config_dir: str | Path | None = None,
    stale_days: int = 7,
) -> list[Path]:
    site = Path(site_dir)
    jetzt = jetzt or datetime.now(ZoneInfo("Europe/Berlin"))
    daten = baue(session, jetzt, Path(config_dir) if config_dir else CONFIG_DIR, stale_days)
    stand = jetzt.astimezone(ZoneInfo("Europe/Berlin")).strftime("%Y%m%d%H%M")

    geschrieben: list[Path] = []

    def schreibe(rel: str, inhalt: str | bytes) -> None:
        _schreibe(site / rel, inhalt)
        geschrieben.append(site / rel)

    for quelle in sorted(STATIC.rglob("*")):
        if quelle.is_file():
            rel = quelle.relative_to(STATIC).as_posix()
            inhalt = quelle.read_bytes()
            if rel in ("index.html", "sw.js"):
                inhalt = inhalt.replace(b"__STAND__", stand.encode())  # neue Version -> Cache erneuern
            schreibe(rel, inhalt)
    schreibe("icon-192.png", png_icon(192))
    schreibe("icon-512.png", png_icon(512))
    schreibe("daten.json", _json(daten["index"]))
    for slug, region in daten["regionen"].items():
        schreibe(f"daten/{slug}.json", _json(region))
        schreibe(f"strecken/{slug}.json", _json(daten["strecken"][slug]))

    # Dateien frueherer Laeufe, die es nicht mehr gibt (z. B. eine entfernte Region), aufraeumen
    for unterordner in ("daten", "strecken"):
        for datei in (site / unterordner).glob("*.json"):
            if datei not in geschrieben:
                datei.unlink()
    return geschrieben
