"""Statische Website (E-10). Schritt 1: Platzhalterseite und daten.json.

Der Generator schreibt nach settings.site_dir. Genau dieser Ordner wird im Heimnetz
vom Container "vorschau" ausgeliefert und spaeter unveraendert hochgeladen (B12).
"""

import json
import os
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loipen.models import Gebiet, Loipe

HINWEIS = "Alle Angaben ohne Gewähr. Quelle und Stand stehen bei jedem Wert."


def _schreibe(ziel: Path, inhalt: str) -> None:
    """Schreibt atomar, damit nginx nie eine halbe Datei ausliefert."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ziel.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(inhalt)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ziel)


def erzeuge(session: Session, site_dir: str | Path, jetzt: datetime | None = None) -> list[Path]:
    site = Path(site_dir)
    jetzt = jetzt or datetime.now(ZoneInfo("Europe/Berlin"))
    anzahl_gebiete = session.scalar(select(func.count()).select_from(Gebiet)) or 0
    anzahl_loipen = session.scalar(select(func.count()).select_from(Loipe)) or 0
    stand = jetzt.strftime("%d.%m.%Y %H:%M")

    daten = {
        "erzeugt": jetzt.isoformat(),
        "gebiete": anzahl_gebiete,
        "loipen": anzahl_loipen,
    }
    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Loipenblick</title>
</head>
<body>
<main>
<h1>Loipenblick</h1>
<p>Vorschau im Heimnetz. Noch keine Loipendaten, die Adapter kommen im nächsten Schritt.</p>
<p>{anzahl_gebiete} Gebiete, {anzahl_loipen} Loipen. Stand {escape(stand)}.</p>
</main>
<footer><p>{escape(HINWEIS)}</p></footer>
</body>
</html>
"""
    dateien = [site / "index.html", site / "daten.json"]
    _schreibe(dateien[0], html)
    _schreibe(dateien[1], json.dumps(daten, ensure_ascii=False, indent=1))
    return dateien
