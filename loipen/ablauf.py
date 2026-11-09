"""Eine Quelle abrufen und das Ergebnis speichern: Stammdaten, Zustand, Historie, Monitoring."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.adapters import ADAPTERS
from loipen.adapters.base import Fetcher, LoipenDaten
from loipen.models import Gebiet, Loipe, Quelle, Schwierigkeit, Technik, utcnow
from loipen.zustand import speichere_zustand

log = logging.getLogger("loipen.ablauf")


@dataclass
class QuellenLauf:
    quelle: str
    gefunden: int = 0
    neu: int = 0
    geaendert: int = 0
    fehler: str | None = None
    warnungen: list[str] = field(default_factory=list)


def _stammdaten(loipe: Loipe, d: LoipenDaten) -> None:
    """Uebernimmt, was die Quelle liefert. Ein leerer Wert ueberschreibt nie einen bekannten."""
    loipe.name = d.name
    loipe.source_url = d.source_url
    for feld in ("laenge_km", "lat", "lon", "nachtloipe", "rundkurs"):
        wert = getattr(d, feld)
        if wert is not None:
            setattr(loipe, feld, wert)
    if d.technik != Technik.UNBEKANNT:
        loipe.technik = d.technik.value
    if d.schwierigkeit != Schwierigkeit.UNBEKANNT:
        loipe.schwierigkeit = d.schwierigkeit.value
    if d.verlauf:
        # GeoJSON LineString, Koordinaten als [lon, lat]
        loipe.verlauf = {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in d.verlauf]}
    loipe.active = True


def rufe_quelle_ab(
    session: Session, quelle: Quelle, fetcher: Fetcher, jetzt: datetime | None = None
) -> QuellenLauf:
    jetzt = jetzt or utcnow()
    lauf = QuellenLauf(quelle=quelle.key)
    adapter = ADAPTERS.get(quelle.adapter)
    if adapter is None:
        lauf.fehler = f"kein Adapter '{quelle.adapter}'"
        _monitoring(quelle, lauf, jetzt, 0.0)
        return lauf

    start = time.monotonic()
    try:
        ergebnis = adapter.run(quelle.base_url, quelle.config, fetcher)
    except Exception as e:  # eine kaputte Quelle darf die anderen nicht stoppen
        log.exception("Quelle %s fehlgeschlagen", quelle.key)
        lauf.fehler = f"{type(e).__name__}: {e}"
        _monitoring(quelle, lauf, jetzt, time.monotonic() - start)
        return lauf

    lauf.warnungen = list(ergebnis.warnungen)
    gebiete = {g.slug: g for g in session.scalars(select(Gebiet))}
    for d in ergebnis.loipen:
        gebiet = gebiete.get(d.gebiet_slug)
        if gebiet is None:
            lauf.warnungen.append(f"{d.name}: unbekanntes Gebiet {d.gebiet_slug}")
            continue
        lauf.gefunden += 1
        loipe = session.scalar(
            select(Loipe).where(Loipe.quelle_id == quelle.id, Loipe.source_key == d.source_key)
        )
        if loipe is None:
            loipe = Loipe(quelle=quelle, source_key=d.source_key, name=d.name, source_url=d.source_url)
            session.add(loipe)
        loipe.gebiet = gebiet
        _stammdaten(loipe, d)
        session.flush()

        for feld, roh in d.unbekannte_begriffe:
            log.warning(
                "Unbekannter Quelltext in Quelle %s, Loipe %s: Feld %s, Rohtext %r",
                quelle.key, d.name, feld, roh,
            )
        _, neu = speichere_zustand(
            session,
            loipe,
            {
                "status": d.status,
                "status_klassisch": d.status_klassisch.value if d.status_klassisch else None,
                "status_skating": d.status_skating.value if d.status_skating else None,
                "gespurt_klassisch_km": d.gespurt_klassisch_km,
                "gespurt_skating_km": d.gespurt_skating_km,
                "gespurt_gesamt_km": d.gespurt_gesamt_km,
                "schneehoehe_cm": d.schneehoehe_cm,
                "quelle_aktualisiert_at": d.quelle_aktualisiert_at,
                "rohtext": d.rohtext or d.status_rohtext,
            },
            jetzt,
        )
        lauf.neu += neu
    _monitoring(quelle, lauf, jetzt, time.monotonic() - start)
    return lauf


def _monitoring(quelle: Quelle, lauf: QuellenLauf, jetzt: datetime, dauer_s: float) -> None:
    """Letzter Lauf, Anzahl und Fehler pro Quelle (B2)."""
    quelle.last_run_at = jetzt
    quelle.last_count = lauf.gefunden
    if lauf.fehler:
        quelle.last_status = "fehler"
        quelle.last_error = lauf.fehler
    elif lauf.gefunden == 0:
        quelle.last_status = "warnung"
        quelle.last_error = "Quelle lieferte 0 Loipen"
    else:
        quelle.last_status = "warnung" if lauf.warnungen else "ok"
        quelle.last_error = "; ".join(lauf.warnungen) or None
