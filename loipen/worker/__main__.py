"""Worker-Container: Konfiguration abgleichen, Quellen abrufen, Seite erzeugen.

    python -m loipen.worker          Zeitplan starten (Standard im Container, B3)
    python -m loipen.worker lauf     einmal alle Quellen abrufen und die Seite erzeugen
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from loipen import generator
from loipen.adapters import ADAPTERS
from loipen.config import get_settings
from loipen.db import session_scope
from loipen.konfig import lade_und_abgleichen
from loipen.models import Quelle
from loipen.zeitplan import ist_faellig

log = logging.getLogger("loipen.worker")


def lauf(nur_faellige: datetime | None = None) -> None:
    """Ein Lauf. Mit nur_faellige werden nur Quellen abgerufen, deren Zeitplan passt."""
    settings = get_settings()
    with session_scope() as session:
        # Konfiguration bei jedem Lauf neu lesen: neue Quellen ohne Neustart (P2)
        lade_und_abgleichen(session, Path(settings.config_dir))
        quellen = session.scalars(select(Quelle).where(Quelle.enabled)).all()
        for quelle in quellen:
            if nur_faellige and not ist_faellig(nur_faellige, quelle.config.get("zeitplan")):
                continue
            adapter = ADAPTERS.get(quelle.adapter)
            if adapter is None:
                log.warning("Noch kein Adapter '%s' fuer Quelle %s", quelle.adapter, quelle.key)
                continue
            log.info("Quelle %s wird abgerufen", quelle.key)
        generator.erzeuge(session, settings.site_dir)
    log.info("Seite erzeugt in %s", settings.site_dir)


def tick() -> None:
    lauf(nur_faellige=datetime.now(ZoneInfo(get_settings().timezone)))


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if argv[:1] == ["lauf"]:
        lauf()
        return
    lauf()  # beim Start einmal, damit die Vorschau sofort etwas zeigt
    scheduler = BlockingScheduler(timezone=get_settings().timezone)
    scheduler.add_job(tick, "cron", minute=0)
    scheduler.start()


if __name__ == "__main__":
    main(sys.argv[1:])
