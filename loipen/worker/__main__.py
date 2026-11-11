"""Worker-Container: Konfiguration abgleichen, Quellen abrufen, Seite erzeugen.

    python -m loipen.worker          Zeitplan starten (Standard im Container, B3)
    python -m loipen.worker sicherung  Datenbank sofort sichern (B14)
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
from loipen.ablauf import rufe_quelle_ab
from loipen.config import get_settings
from loipen.db import session_scope
from loipen.ereignisse import (
    benachrichtige, betriebsmeldung, lade_abos, ntfy_sender, pruefe_abos,
)
from loipen.fetcher import HoeflicherFetcher
from loipen.konfig import lade_und_abgleichen, lade_yaml
from loipen.models import Quelle, utcnow
from loipen.sicherung import sichere
from loipen.wetter import aktualisiere_wetter
from loipen.zeitplan import ist_faellig

log = logging.getLogger("loipen.worker")

# Ein Fetcher fuer die Lebensdauer des Workers, damit der ETag-Cache zwischen den Laeufen bleibt (P7)
_fetcher: HoeflicherFetcher | None = None


def fetcher() -> HoeflicherFetcher:
    global _fetcher
    if _fetcher is None:
        settings = get_settings()
        _fetcher = HoeflicherFetcher(settings.user_agent, settings.request_delay_s, umleitung=settings.umleitung)
    return _fetcher


def lauf(nur_faellige: datetime | None = None, abrufer=None, sender=None) -> None:
    """Ein Lauf. Mit nur_faellige werden nur Quellen abgerufen, deren Zeitplan passt."""
    settings = get_settings()
    sender = sender or ntfy_sender(settings.ntfy_url)
    ereignisse, meldungen = [], []
    with session_scope() as session:
        # Konfiguration bei jedem Lauf neu lesen: neue Quellen ohne Neustart (P2)
        lade_und_abgleichen(session, Path(settings.config_dir))
        quellen = session.scalars(select(Quelle).where(Quelle.enabled)).all()
        for quelle in quellen:
            if nur_faellige and not ist_faellig(nur_faellige, quelle.config.get("zeitplan")):
                continue
            log.info("Quelle %s wird abgerufen", quelle.key)
            ergebnis = rufe_quelle_ab(session, quelle, abrufer or fetcher())
            ereignisse += ergebnis.ereignisse
            meldung = betriebsmeldung(quelle.key, ergebnis.status_vorher, ergebnis.status, quelle.last_error)
            if meldung:
                meldungen.append(meldung)
            log.info(
                "Quelle %s: %d Loipen, %d neue Zustaende%s",
                quelle.key, ergebnis.gefunden, ergebnis.neu,
                f", Fehler: {ergebnis.fehler}" if ergebnis.fehler else "",
            )
        try:
            wetter = aktualisiere_wetter(session, abrufer or fetcher())
            log.info("Wetter: %d Messwerte, %d Vorhersagewerte", wetter.messungen, wetter.vorhersagen)
            for w in wetter.warnungen:
                log.warning("Wetter: %s", w)
        except Exception:  # Wetter darf den Lauf nie verhindern
            log.exception("Wetter-Aktualisierung fehlgeschlagen")
        generator.erzeuge(session, settings.site_dir, config_dir=settings.config_dir, stale_days=settings.stale_days)
    log.info("Seite erzeugt in %s", settings.site_dir)
    _melde(settings, sender, ereignisse, meldungen)


def _melde(settings, sender, ereignisse, meldungen) -> None:
    """Push nach dem Commit, damit ein Versandfehler nie Daten gefaehrdet (N4)."""
    try:
        cfg = Path(settings.config_dir)
        abos = lade_abos(cfg)
        for f in pruefe_abos(abos, lade_yaml(cfg / "gebiete.yaml")):
            log.warning("abos.yaml: %s", f)
        n = benachrichtige(abos, ereignisse, sender)
        if sender:
            for titel, text in meldungen:
                sender(titel, text)
        log.info("%d Ereignisse, %d Alarme gesendet", len(ereignisse), n)
    except Exception:
        log.exception("Benachrichtigung fehlgeschlagen")


def sicherung() -> None:
    settings = get_settings()
    try:
        ziel = sichere(settings.database_url, settings.backup_dir, utcnow())
        log.info("Sicherung geschrieben: %s", ziel)
    except Exception:
        log.exception("Sicherung fehlgeschlagen")
        sender = ntfy_sender(settings.ntfy_url)
        if sender:
            try:
                sender("Loipenblick: Sicherung fehlgeschlagen", "Siehe Log des Worker-Containers.")
            except Exception:
                log.exception("Meldung ueber fehlgeschlagene Sicherung nicht gesendet")


def tick() -> None:
    lauf(nur_faellige=datetime.now(ZoneInfo(get_settings().timezone)))


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if argv[:1] == ["lauf"]:
        lauf()
        return
    if argv[:1] == ["sicherung"]:
        sicherung()
        return
    lauf()  # beim Start einmal, damit die Vorschau sofort etwas zeigt
    scheduler = BlockingScheduler(timezone=get_settings().timezone)
    scheduler.add_job(tick, "cron", minute=0)
    scheduler.add_job(sicherung, "cron", hour=3, minute=30)  # taeglich, B14
    scheduler.start()


if __name__ == "__main__":
    main(sys.argv[1:])
