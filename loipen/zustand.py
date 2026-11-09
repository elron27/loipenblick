"""Zustaende speichern, Historie nur bei Aenderung (D3, D4)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import Loipe, Status, Zustand, utcnow

# Felder, deren Aenderung einen neuen Historieneintrag ausloest. Der Rohtext gehoert dazu,
# damit eine geaenderte Formulierung der Quelle fuer die Fehleranalyse erhalten bleibt.
VERGLEICHSFELDER = (
    "status",
    "status_klassisch",
    "status_skating",
    "gespurt_klassisch_km",
    "gespurt_skating_km",
    "gespurt_gesamt_km",
    "schneehoehe_cm",
    "quelle_aktualisiert_at",
    "rohtext",
)


def letzter_zustand(session: Session, loipe: Loipe) -> Zustand | None:
    return session.scalar(
        select(Zustand)
        .where(Zustand.loipe_id == loipe.id)
        .order_by(Zustand.abgerufen_at.desc(), Zustand.id.desc())
        .limit(1)
    )


def speichere_zustand(
    session: Session, loipe: Loipe, werte: dict, jetzt: datetime | None = None
) -> tuple[Zustand, bool]:
    """Speichert einen Abruf. Gibt (Zustand, neu) zurueck.

    Ist alles gleich wie beim letzten Abruf, wird nur zuletzt_bestaetigt_at fortgeschrieben.
    """
    jetzt = jetzt or utcnow()
    werte = dict(werte)
    status = werte.get("status", Status.UNBEKANNT)
    werte["status"] = Status(status).value  # nur die vier erlaubten Werte (D3)

    alt = letzter_zustand(session, loipe)
    if alt is not None and all(getattr(alt, f) == werte.get(f) for f in VERGLEICHSFELDER):
        alt.zuletzt_bestaetigt_at = jetzt
        return alt, False

    neu = Zustand(loipe=loipe, abgerufen_at=jetzt, zuletzt_bestaetigt_at=jetzt)
    for f in VERGLEICHSFELDER:
        setattr(neu, f, werte.get(f))
    session.add(neu)
    session.flush()
    return neu, True

