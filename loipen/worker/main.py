"""Worker-Container: gleicht beim Start die Quellen ab und ruft sie nach Zeitplan ab.

Schritt 1 enthaelt nur Abgleich und Zeitplan. Die Adapter kommen in Schritt 2 und 3.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from loipen.adapters import ADAPTERS
from loipen.config import get_settings
from loipen.db import session_scope
from loipen.models import Quelle
from loipen.sources import load_sources_file, sync_sources

log = logging.getLogger("loipen.worker")


def in_season(now: datetime) -> bool:
    settings = get_settings()
    return (
        now.month in settings.season_months
        and settings.season_start_h <= now.hour < settings.season_end_h
    )


def run_all() -> None:
    with session_scope() as session:
        quellen = session.scalars(select(Quelle).where(Quelle.enabled)).all()
        for quelle in quellen:
            if quelle.adapter not in ADAPTERS:
                log.warning("Kein Adapter '%s' fuer Quelle %s", quelle.adapter, quelle.key)
                continue
            log.info("Quelle %s wuerde jetzt abgerufen", quelle.key)


def tick() -> None:
    """Stuendlich aufgerufen. Ausserhalb der Saison nur einmal am Tag um 8 Uhr."""
    now = datetime.now(ZoneInfo(get_settings().timezone))
    if in_season(now) or now.hour == 8:
        run_all()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    with session_scope() as session:
        sync_sources(session, load_sources_file(settings.sources_file))
    log.info("Quellen abgeglichen")

    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(tick, "cron", minute=5)
    scheduler.start()


if __name__ == "__main__":
    main()
