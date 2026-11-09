"""Wetter und Schnee pro Gebiet (D11, D13, U15).

Messwerte (Schneehoehe, Neuschnee, Niederschlag): DWD-Tageswerte, ZIP je Station.
Vorhersage (Temperatur, Niederschlag, Schneefall): Bright Sky, das den DWD-Vorhersagedienst
MOSMIX offen bereitstellt. Bright Sky liefert keine Schneehoehe (Recherche 09.11.2026).
Fehlende Werte bleiben None, nie 0 (D11).
"""

import io
import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.adapters.normalisierung import BERLIN
from loipen.models import Gebiet, Wetter, WetterArt, utcnow

log = logging.getLogger("loipen.wetter")

DWD_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/"
    "more_precip/recent/tageswerte_RR_{station}_akt.zip"
)
BRIGHTSKY_URL = "https://api.brightsky.dev/weather?lat={lat}&lon={lon}&date={von}&last_date={bis}&tz=Europe/Berlin"
QUELLE_DWD = "DWD Klimadaten Tageswerte"
QUELLE_VORHERSAGE = "Bright Sky (DWD MOSMIX)"
VORHERSAGE_TAGE = 8  # mindestens 7, damit am Montag das folgende Wochenende drin ist (U18)
MESSUNG_TAGE = 14


@dataclass
class Messung:
    datum: date
    niederschlag_mm: float | None = None
    schneehoehe_cm: float | None = None
    neuschnee_cm: float | None = None


@dataclass
class Vorhersage:
    datum: date
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    niederschlag_mm: float | None = None
    schneefall: bool = False


def _zahl(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        wert = float(text)
    except ValueError:
        return None
    return None if wert <= -999 else wert  # DWD: -999 = fehlt


def parse_dwd_tageswerte(inhalt: bytes) -> list[Messung]:
    """ZIP mit produkt_*.txt -> Messungen. Spalten RS, SH_TAG, NSH_TAG, Trenner ';'."""
    with zipfile.ZipFile(io.BytesIO(inhalt)) as z:
        name = next((n for n in z.namelist() if n.startswith("produkt_") and n.endswith(".txt")), None)
        if name is None:
            raise ValueError("ZIP enthaelt keine produkt_*.txt")
        zeilen = z.read(name).decode("latin-1").splitlines()
    kopf = [c.strip() for c in zeilen[0].split(";")]
    for pflicht in ("MESS_DATUM", "SH_TAG", "NSH_TAG", "RS"):
        if pflicht not in kopf:
            raise ValueError(f"Spalte {pflicht} fehlt im DWD-Produkt")
    i = {c: kopf.index(c) for c in ("MESS_DATUM", "SH_TAG", "NSH_TAG", "RS")}
    ergebnis = []
    for zeile in zeilen[1:]:
        teile = zeile.split(";")
        if len(teile) < len(kopf) - 1 or not teile[i["MESS_DATUM"]].strip():
            continue
        d = datetime.strptime(teile[i["MESS_DATUM"]].strip(), "%Y%m%d").date()
        ergebnis.append(
            Messung(d, _zahl(teile[i["RS"]]), _zahl(teile[i["SH_TAG"]]), _zahl(teile[i["NSH_TAG"]]))
        )
    return sorted(ergebnis, key=lambda m: m.datum)


def parse_brightsky(text: str) -> list[Vorhersage]:
    """Stuendliche Werte -> je Tag (Europe/Berlin) Tiefst-/Hoechsttemperatur, Niederschlag, Schneefall."""
    tage: dict[date, list[dict]] = {}
    for eintrag in json.loads(text).get("weather", []):
        zeit = datetime.fromisoformat(eintrag["timestamp"]).astimezone(BERLIN)
        tage.setdefault(zeit.date(), []).append(eintrag)
    ergebnis = []
    for tag, eintraege in sorted(tage.items()):
        temp = [e["temperature"] for e in eintraege if e.get("temperature") is not None]
        nied = [e["precipitation"] for e in eintraege if e.get("precipitation") is not None]
        ergebnis.append(
            Vorhersage(
                tag,
                min(temp) if temp else None,
                max(temp) if temp else None,
                round(sum(nied), 1) if nied else None,
                any(e.get("condition") == "snow" or e.get("icon") == "snow" for e in eintraege),
            )
        )
    return ergebnis


def neuschnee_summen(messungen: list[Messung]) -> dict[int, float | None]:
    """Neuschnee der letzten 24, 48 und 72 Stunden bis zum letzten Messtag. Luecke -> None."""
    if not messungen:
        return {24: None, 48: None, 72: None}
    nach_tag = {m.datum: m for m in messungen}
    letzter = max(nach_tag)
    ergebnis: dict[int, float | None] = {}
    for stunden in (24, 48, 72):
        werte = [
            nach_tag[letzter - timedelta(days=t)].neuschnee_cm if (letzter - timedelta(days=t)) in nach_tag else None
            for t in range(stunden // 24)
        ]
        ergebnis[stunden] = None if None in werte else round(sum(werte), 1)
    return ergebnis


def gebiet_position(gebiet: Gebiet) -> tuple[float, float] | None:
    """Mitte des Gebiets: eingetragene Koordinate, sonst Mittel der Loipenstarts, sonst der Parkplaetze."""
    if gebiet.lat is not None and gebiet.lon is not None:
        return gebiet.lat, gebiet.lon
    for punkte in (
        [(l.lat, l.lon) for l in gebiet.loipen if l.lat is not None and l.lon is not None],
        [(p.lat, p.lon) for p in gebiet.parkplaetze],
    ):
        if punkte:
            return round(mean(p[0] for p in punkte), 4), round(mean(p[1] for p in punkte), 4)
    return None


@dataclass
class WetterLauf:
    messungen: int = 0
    vorhersagen: int = 0
    warnungen: list[str] = field(default_factory=list)


def _speichere(session: Session, gebiet: Gebiet, art: WetterArt, datum: date, werte: dict, station: str | None,
               quelle: str, jetzt: datetime) -> None:
    zeile = session.scalar(
        select(Wetter).where(Wetter.gebiet_id == gebiet.id, Wetter.datum == datum, Wetter.art == art.value)
    )
    if zeile is None:
        zeile = Wetter(gebiet_id=gebiet.id, datum=datum, art=art.value, quelle=quelle)
        session.add(zeile)
    for k, v in werte.items():
        setattr(zeile, k, v)
    zeile.station_id = station
    zeile.quelle = quelle
    zeile.abgerufen_at = jetzt


def aktualisiere_wetter(session: Session, fetcher, jetzt: datetime | None = None, tage: int = MESSUNG_TAGE) -> WetterLauf:
    """Holt Messwerte je Station und Vorhersage je Gebiet. Ein Fehler stoppt nie die anderen Quellen."""
    jetzt = jetzt or utcnow()
    heute = jetzt.astimezone(BERLIN).date()
    lauf = WetterLauf()
    gebiete = session.scalars(select(Gebiet)).all()

    cache: dict[str, list[Messung] | None] = {}
    for g in gebiete:
        station = g.wetterstation_id
        if not station:
            continue
        if station not in cache:
            try:
                cache[station] = parse_dwd_tageswerte(fetcher.get_bytes(DWD_URL.format(station=station)))
            except Exception as e:  # Netz, ZIP oder Format
                cache[station] = None
                lauf.warnungen.append(f"DWD-Station {station}: {type(e).__name__}: {e}")
        for m in cache[station] or []:
            if m.datum >= heute - timedelta(days=tage):
                _speichere(session, g, WetterArt.MESSUNG, m.datum, {
                    "niederschlag_mm": m.niederschlag_mm, "schneehoehe_cm": m.schneehoehe_cm,
                    "neuschnee_cm": m.neuschnee_cm}, station, QUELLE_DWD, jetzt)
                lauf.messungen += 1

    for g in gebiete:
        pos = gebiet_position(g)
        if pos is None:
            lauf.warnungen.append(f"Gebiet {g.slug}: keine Position, keine Vorhersage")
            continue
        url = BRIGHTSKY_URL.format(lat=pos[0], lon=pos[1], von=heute.isoformat(),
                                   bis=(heute + timedelta(days=VORHERSAGE_TAGE - 1)).isoformat())
        try:
            vorhersagen = parse_brightsky(fetcher.get(url))
        except Exception as e:
            lauf.warnungen.append(f"Vorhersage {g.slug}: {type(e).__name__}: {e}")
            continue
        for v in vorhersagen:
            _speichere(session, g, WetterArt.VORHERSAGE, v.datum, {
                "temp_min_c": v.temp_min_c, "temp_max_c": v.temp_max_c, "niederschlag_mm": v.niederschlag_mm,
                # Schneefall laut Vorhersage; Menge liefert Bright Sky nicht
                "neuschnee_cm": None}, None, QUELLE_VORHERSAGE, jetzt)
            lauf.vorhersagen += 1
    session.flush()
    return lauf


def schnee_uebersicht(session: Session, gebiet: Gebiet) -> dict:
    """Aktuelle Schneehoehe und Neuschnee 24/48/72 h mit Messtag, Station und Quelle (D11)."""
    zeilen = session.scalars(
        select(Wetter).where(Wetter.gebiet_id == gebiet.id, Wetter.art == WetterArt.MESSUNG.value)
        .order_by(Wetter.datum.desc()).limit(3)
    ).all()
    messungen = [Messung(z.datum, z.niederschlag_mm, z.schneehoehe_cm, z.neuschnee_cm) for z in zeilen]
    summen = neuschnee_summen(messungen)
    letzte = zeilen[0] if zeilen else None
    return {
        "messtag": letzte.datum if letzte else None,
        "schneehoehe_cm": letzte.schneehoehe_cm if letzte else None,
        "neuschnee_24h_cm": summen[24], "neuschnee_48h_cm": summen[48], "neuschnee_72h_cm": summen[72],
        "station_id": letzte.station_id if letzte else None,
        "station_name": gebiet.wetterstation_name,
        "quelle": letzte.quelle if letzte else None,
    }
