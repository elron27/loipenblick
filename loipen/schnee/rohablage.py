"""Rohdateien der Schneequellen (S1 AK 2, S9): gepackt im Ordner <backup_dir>/schnee-roh, damit Hyper Backup sie
mitsichert. Pfad: <quelle>/<JJJJ>/<MM>/<TT>/<sha256>.gz. Gleicher Inhalt wird nur einmal abgelegt."""

import gzip
import hashlib
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import SchneeRohdatei, utcnow


def ordner(backup_dir: str | Path) -> Path:
    return Path(backup_dir) / "schnee-roh"


def lege_ab(session: Session, wurzel: Path, quelle: str, url: str, inhalt: bytes,
            content_type: str | None = None, jetzt: datetime | None = None) -> SchneeRohdatei:
    jetzt = jetzt or utcnow()
    sha = hashlib.sha256(inhalt).hexdigest()
    vorhanden = session.scalar(select(SchneeRohdatei).where(SchneeRohdatei.sha256 == sha))
    if vorhanden:
        return vorhanden
    rel = Path(quelle) / f"{jetzt:%Y}" / f"{jetzt:%m}" / f"{jetzt:%d}" / f"{sha}.gz"
    ziel = wurzel / rel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(inhalt, mtime=0))
    tmp.replace(ziel)
    datei = SchneeRohdatei(quelle=quelle, url=url[:1000], sha256=sha, pfad=rel.as_posix(), groesse=len(inhalt),
                           content_type=content_type, abgerufen_at=jetzt)
    session.add(datei)
    session.flush()
    return datei


def lies(wurzel: Path, datei: SchneeRohdatei) -> bytes:
    return gzip.decompress((wurzel / datei.pfad).read_bytes())
