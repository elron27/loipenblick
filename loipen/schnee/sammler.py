"""Taeglicher Sammel-Job der Schneekarte (S1, E-34) und Luecken-Alarm (S8).

Jede Quelle aus config/schnee.yaml hat einen Adapter (loipen/schnee/adapter/<name>.py) mit
    abrufe(quelle, fetcher, jetzt) -> Iterable[Antwort]      holt die Rohantworten
    verarbeite(antwort, quelle) -> Ergebnis                    liest eine Rohantwort (ohne Netz, fuer Fixture-Tests)
Jede Antwort wird zuerst unveraendert abgelegt, dann gelesen und gespeichert. Faellt eine Quelle aus, laufen die
anderen weiter (S1 AK 4); jede Quelle laeuft in einem eigenen Savepoint.
"""

import importlib
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loipen.models import SchneeAbruf, utcnow
from loipen.schnee import rohablage
from loipen.schnee.daten import Ergebnis
from loipen.schnee.konfig import SchneeQuelle
from loipen.schnee.speicher import speichere

log = logging.getLogger("loipen.schnee")
BERLIN = ZoneInfo("Europe/Berlin")
EINBRUCH = 0.8  # S8 AK 1: Alarm, wenn die Zahl der Stationen um mehr als 20 % faellt


@dataclass
class Antwort:
    url: str
    inhalt: bytes
    art: str = "daten"  # daten, katalog (vollstaendige Stationsliste), regionen, archiv
    content_type: str | None = None
    meta: dict = field(default_factory=dict)  # z. B. Datum eines Archivtags


@dataclass
class Lauf:
    quelle: str
    werte: int = 0
    neu: int = 0
    stationen: int = 0
    teilfehler: int = 0
    fehler: str | None = None
    warnungen: list[str] = field(default_factory=list)


def adapter(name: str):
    return importlib.import_module(f"loipen.schnee.adapter.{name}")


def zaehle(erg: Ergebnis) -> int:
    return (len(erg.messwerte) + sum(len(b.regionen) for b in erg.berichte) + len(erg.modellwerte)
            + len(erg.regionen))


def sammle_quelle(session: Session, q: SchneeQuelle, fetcher, wurzel: Path, jetzt: datetime,
                  antworten: Iterable[Antwort] | None = None, nachgeladen: bool = False,
                  protokoll: bool = True) -> Lauf:
    """protokoll=False beim Nachladen (S5), damit Archivtage den Luecken-Alarm (S8) nicht verfaelschen."""
    lauf = Lauf(q.key)
    t0 = time.monotonic()
    mod = adapter(q.adapter)
    try:  # Teilergebnisse bleiben (B28): jede Antwort in einem eigenen Savepoint
        for a in (antworten if antworten is not None else mod.abrufe(q, fetcher, jetzt, session)):
            if a.art == "fehler":  # ein einzelner Abruf ging nicht, die uebrigen laufen weiter
                lauf.warnungen.append(f"{a.url}: {a.meta.get('fehler')}"[:500])
                lauf.teilfehler += 1
                continue
            try:
                with session.begin_nested():
                    roh = rohablage.lege_ab(session, wurzel, q.key, a.url, a.inhalt, a.content_type, jetzt)
                    erg = mod.verarbeite(a, q)
                    z = speichere(session, q.key, erg, roh, jetzt, nachgeladen=nachgeladen,
                                  katalog_vollstaendig=a.art == "katalog")
            except Exception as e:  # eine unlesbare Antwort bricht die Quelle nicht ab
                lauf.warnungen.append(f"{a.url}: {type(e).__name__}: {e}"[:500])
                log.exception("Schnee %s: %s nicht lesbar", q.key, a.url)
                with session.begin_nested():  # Rohdatei trotzdem behalten, damit sie spaeter neu gelesen werden kann
                    rohablage.lege_ab(session, wurzel, q.key, a.url, a.inhalt, a.content_type, jetzt)
                continue
            lauf.werte += zaehle(erg)
            lauf.neu += z.werte
            lauf.stationen = max(lauf.stationen, z.stationen)
            lauf.warnungen += z.warnungen
    except Exception as e:
        lauf.fehler = f"{type(e).__name__}: {e}"[:2000]
        log.exception("Schnee %s fehlgeschlagen", q.key)
    if lauf.teilfehler and not lauf.fehler:
        lauf.fehler = f"{lauf.teilfehler} Abrufe fehlgeschlagen, Rest gespeichert: {lauf.warnungen[0]}"[:2000]
    if protokoll:
        session.add(SchneeAbruf(quelle=q.key, zeit=jetzt, tag=jetzt.astimezone(BERLIN).date(), werte=lauf.werte,
                                neu=lauf.neu, stationen=lauf.stationen, fehler=lauf.fehler,
                                dauer_s=round(time.monotonic() - t0, 2)))
        session.flush()
    for w in lauf.warnungen[:20]:
        log.warning("Schnee %s: %s", q.key, w)
    log.info("Schnee %s: %d Werte gelesen, %d neu, %d Stationen%s", q.key, lauf.werte, lauf.neu, lauf.stationen,
             f", Fehler: {lauf.fehler}" if lauf.fehler else "")
    return lauf


def ist_faellig(q: SchneeQuelle, jetzt: datetime) -> bool:
    ort = jetzt.astimezone(BERLIN)
    wochentage = q.optionen.get("wochentage")  # 0 = Montag
    return ort.hour in q.uhrzeiten and (not wochentage or ort.weekday() in wochentage)


def sammle(session: Session, quellen: list[SchneeQuelle], fetcher, wurzel: Path, jetzt: datetime | None = None,
           nur_faellige: bool = False) -> list[Lauf]:
    jetzt = jetzt or utcnow()
    return [sammle_quelle(session, q, fetcher, wurzel, jetzt) for q in quellen
            if q.enabled and (not nur_faellige or ist_faellig(q, jetzt))]


def luecken(session: Session, quellen: list[SchneeQuelle], tag: date) -> list[str]:
    """S8: Befunde fuer einen Tag. Aufruf nach dem letzten Abruf des Tages."""
    befunde = []
    for q in quellen:
        if not q.enabled:
            continue
        heute = session.execute(select(func.coalesce(func.sum(SchneeAbruf.werte), 0),
                                       func.coalesce(func.max(SchneeAbruf.stationen), 0), func.count())
                                .where(SchneeAbruf.quelle == q.key, SchneeAbruf.tag == tag)).one()
        werte, stationen, abrufe = heute
        if abrufe and not werte:
            befunde.append(f"{q.name}: am {tag:%d.%m.%Y} keine Werte")
            continue
        frueher = session.scalars(
            select(func.max(SchneeAbruf.stationen)).where(
                SchneeAbruf.quelle == q.key, SchneeAbruf.tag < tag, SchneeAbruf.tag >= tag - timedelta(days=7),
                SchneeAbruf.stationen > 0).group_by(SchneeAbruf.tag)).all()
        if stationen and frueher and stationen < EINBRUCH * median(frueher):
            befunde.append(f"{q.name}: nur {stationen} Stationen statt üblich {int(median(frueher))}")
    return befunde


def melde_luecken(befunde: list[str], sender: Callable[[str, str], None] | None) -> None:
    if not befunde:
        return
    log.warning("Schneekarte, Lücken: %s", "; ".join(befunde))
    if sender:
        try:
            sender("Loipenblick Schneekarte: Lücke beim Sammeln", "\n".join(befunde))
        except Exception:
            log.exception("Lücken-Meldung nicht gesendet")
