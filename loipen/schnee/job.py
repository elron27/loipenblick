"""Einbindung der Schneekarte in den Worker (S1, S8). Laeuft getrennt vom Loipen-Lauf, damit ein Fehler hier nie die
Loipenseite verhindert und umgekehrt.

    python -m loipen.worker schnee                          alle Schneequellen jetzt einmal abrufen
    python -m loipen.worker schnee-archiv <quelle> [von] [bis]  fruehere Winter nachladen (S5)
"""

import logging
from datetime import date, datetime
from pathlib import Path

from loipen.config import get_settings
from loipen.db import session_scope
from loipen.fetcher import HoeflicherFetcher
from loipen.schnee import archiv, rohablage
from loipen.schnee.konfig import lade
from loipen.schnee.sammler import BERLIN, luecken, melde_luecken, sammle

log = logging.getLogger("loipen.schnee")
LUECKEN_STUNDE = 21  # nach dem letzten Abruf des Tages (S8)


def _fetcher(settings) -> HoeflicherFetcher:
    return HoeflicherFetcher(settings.user_agent, settings.request_delay_s, timeout_s=60, umleitung=settings.umleitung)


def quellen(settings):
    q, fehler = lade(settings.config_dir)
    for f in fehler:  # S6 AK 2: abgelehnte Quellen werden nicht abgerufen
        log.error("schnee.yaml: %s", f)
    return q


def lauf(jetzt: datetime | None = None, nur_faellige: bool = False, sender=None) -> list:
    settings = get_settings()
    jetzt = jetzt or datetime.now(BERLIN)
    qs = quellen(settings)
    wurzel = rohablage.ordner(settings.backup_dir)
    f = _fetcher(settings)
    try:
        with session_scope() as session:
            laeufe = sammle(session, qs, f, wurzel, jetzt, nur_faellige=nur_faellige)
    finally:
        f.close()
    if jetzt.astimezone(BERLIN).hour == LUECKEN_STUNDE or not nur_faellige:
        with session_scope() as session:
            befunde = luecken(session, qs, jetzt.astimezone(BERLIN).date())
        if nur_faellige:  # Zeitplan: Meldung per ntfy
            melde_luecken(befunde, sender)
        else:  # Lauf von Hand: nur ins Log
            for b in befunde:
                log.warning("Lücke: %s", b)
    return laeufe


def nachladen(key: str, von: str | None = None, bis: str | None = None) -> dict:
    settings = get_settings()
    q = next((x for x in quellen(settings) if x.key == key), None)
    if q is None:
        raise SystemExit(f"Quelle {key} nicht in config/schnee.yaml (oder ungültig)")
    f = _fetcher(settings)
    try:
        return archiv.lade_nach(session_scope, q, f, Path(rohablage.ordner(settings.backup_dir)),
                                date.fromisoformat(von) if von else None, date.fromisoformat(bis) if bis else None)
    finally:
        f.close()
