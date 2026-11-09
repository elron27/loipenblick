"""Taegliche Datenbanksicherung mit pg_dump und Aufraeumen alter Dumps (B14)."""

import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger("loipen.sicherung")

PREFIX = "loipen-"
SUFFIX = ".dump"


def _pg_args(database_url: str) -> tuple[list[str], dict]:
    """Zerlegt die SQLAlchemy-URL; das Passwort geht ueber die Umgebung, nie ueber die Kommandozeile."""
    u = urlsplit(database_url.replace("postgresql+psycopg", "postgresql"))
    args = ["-h", u.hostname or "localhost", "-p", str(u.port or 5432), "-U", u.username or "postgres",
            "-d", (u.path or "/").lstrip("/")]
    env = dict(os.environ)
    if u.password:
        env["PGPASSWORD"] = u.password
    return args, env


def dump(database_url: str, ziel_dir: str | Path, jetzt: datetime) -> Path:
    """Schreibt loipen-JJJJMMTT-HHMM.dump im Custom-Format (pg_restore). Bei Fehler bleibt keine Teildatei."""
    ziel_dir = Path(ziel_dir)
    ziel_dir.mkdir(parents=True, exist_ok=True)
    ziel = ziel_dir / f"{PREFIX}{jetzt:%Y%m%d-%H%M}{SUFFIX}"
    tmp = ziel.with_suffix(".tmp")
    args, env = _pg_args(database_url)
    try:
        subprocess.run(["pg_dump", "-Fc", "-f", str(tmp), *args], check=True, env=env,
                       capture_output=True, timeout=600)
        if tmp.stat().st_size == 0:
            raise RuntimeError("Dump ist leer")
        tmp.replace(ziel)
    finally:
        tmp.unlink(missing_ok=True)
    return ziel


def aufraeumen(ziel_dir: str | Path, jetzt: datetime, behalten_tage: int = 30) -> list[Path]:
    """Loescht Dumps, die aelter als behalten_tage sind. Andere Dateien bleiben unberuehrt."""
    grenze = jetzt.replace(tzinfo=None) - timedelta(days=behalten_tage)
    geloescht = []
    for f in Path(ziel_dir).glob(f"{PREFIX}*{SUFFIX}"):
        try:
            zeit = datetime.strptime(f.name[len(PREFIX):-len(SUFFIX)], "%Y%m%d-%H%M")
        except ValueError:
            continue
        if zeit < grenze:
            f.unlink()
            geloescht.append(f)
    return geloescht


def sichere(database_url: str, ziel_dir: str | Path, jetzt: datetime, behalten_tage: int = 30) -> Path:
    ziel = dump(database_url, ziel_dir, jetzt)
    for f in aufraeumen(ziel_dir, jetzt, behalten_tage):
        log.info("Alter Dump geloescht: %s", f.name)
    return ziel
