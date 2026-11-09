"""Daten fuer die statische Seite: ein Index und je Region eine Datei mit Gebieten, Loipen,
Wetter und Strecken. Die Seite liest nur diese JSON-Dateien (B7), keine Datenbank."""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.konfig import lade_yaml
from loipen.models import Gebiet, Loipe, Quelle, Region, Status, Wetter, WetterArt, Zustand
from loipen.wetter import gebiet_position, schnee_uebersicht

BERLIN = ZoneInfo("Europe/Berlin")
VERALTET_STUNDEN = 48  # U6
HISTORIE_TAGE = 14  # U5


def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(BERLIN).isoformat(timespec="minutes") if dt else None


def _historie(zustaende: list[Zustand], heute: date) -> list[dict]:
    """Status am Ende jedes der letzten 14 Tage; Tage vor dem ersten Abruf haben keinen Eintrag."""
    verlauf = []
    for i in range(HISTORIE_TAGE - 1, -1, -1):
        tag = heute - timedelta(days=i)
        ende = datetime(tag.year, tag.month, tag.day, 23, 59, 59, tzinfo=BERLIN)
        gueltig = [z for z in zustaende if z.abgerufen_at <= ende]
        verlauf.append({"tag": tag.isoformat(), "status": gueltig[-1].status if gueltig else None})
    return verlauf


def _loipe(loipe: Loipe, zustaende: list[Zustand], quelle: Quelle, jetzt: datetime, stale_days: int) -> dict:
    z = zustaende[-1] if zustaende else None
    alter_h = (jetzt - z.zuletzt_bestaetigt_at).total_seconds() / 3600 if z else None
    # Ein Zustand, den seit stale_days Tagen niemand bestaetigt hat, gilt als unbekannt
    zu_alt = alter_h is not None and alter_h > stale_days * 24
    fehler = quelle.last_status == "fehler"
    return {
        "id": loipe.id,
        "name": loipe.name,
        "laenge_km": loipe.laenge_km,
        "schwierigkeit": loipe.schwierigkeit,
        "technik": loipe.technik,
        "nachtloipe": loipe.nachtloipe,
        "rundkurs": loipe.rundkurs,
        "lat": loipe.lat,
        "lon": loipe.lon,
        "status": Status.UNBEKANNT.value if (z is None or zu_alt) else z.status,
        "status_klassisch": z.status_klassisch if z and not zu_alt else None,
        "status_skating": z.status_skating if z and not zu_alt else None,
        "gespurt_km": z.gespurt_gesamt_km if z else None,
        "gespurt_klassisch_km": z.gespurt_klassisch_km if z else None,
        "gespurt_skating_km": z.gespurt_skating_km if z else None,
        "quelle_stand": _iso(z.quelle_aktualisiert_at) if z else None,
        "abgerufen": _iso(z.zuletzt_bestaetigt_at) if z else None,
        "veraltet": bool(z is None or fehler or (alter_h is not None and alter_h > VERALTET_STUNDEN)),
        "quelle_fehler": fehler,
        "quelle": {"name": quelle.name, "url": loipe.source_url},
        "historie": _historie(zustaende, jetzt.astimezone(BERLIN).date()),
    }


def _vorhersage(session: Session, gebiet: Gebiet, heute: date) -> list[dict]:
    zeilen = session.scalars(
        select(Wetter).where(
            Wetter.gebiet_id == gebiet.id, Wetter.art == WetterArt.VORHERSAGE.value, Wetter.datum >= heute
        ).order_by(Wetter.datum)
    ).all()
    return [
        {"datum": z.datum.isoformat(), "tmin": z.temp_min_c, "tmax": z.temp_max_c, "niederschlag_mm": z.niederschlag_mm}
        for z in zeilen
    ]


def _mitte(gebiete: list[dict]) -> list[float] | None:
    punkte = [(g["lat"], g["lon"]) for g in gebiete if g["lat"] is not None]
    if not punkte:
        return None
    return [round(sum(p[0] for p in punkte) / len(punkte), 3), round(sum(p[1] for p in punkte) / len(punkte), 3)]


def baue(session: Session, jetzt: datetime, config_dir: Path, stale_days: int = 7) -> dict:
    """Gibt {"index": ..., "regionen": {slug: {...}}, "strecken": {slug: {...}}} zurueck."""
    heute = jetzt.astimezone(BERLIN).date()
    zustaende: dict[int, list[Zustand]] = {}
    for z in session.scalars(select(Zustand).order_by(Zustand.abgerufen_at, Zustand.id)):
        zustaende.setdefault(z.loipe_id, []).append(z)

    regionen: dict[str, dict] = {}
    strecken: dict[str, dict] = {}
    kennzahl = {s.value: 0 for s in Status}
    veraltet = 0
    gesamt = 0
    for region in session.scalars(select(Region).order_by(Region.name)):
        gebiete = []
        verlaeufe: dict[str, list] = {}
        for g in sorted(region.gebiete, key=lambda x: x.name):
            pos = gebiet_position(g)
            loipen = []
            for l in sorted(g.loipen, key=lambda x: x.name):
                if not l.active:
                    continue
                d = _loipe(l, zustaende.get(l.id, []), l.quelle, jetzt, stale_days)
                loipen.append(d)
                kennzahl[d["status"]] += 1
                veraltet += d["veraltet"]
                gesamt += 1
                if l.verlauf:
                    # Strecken getrennt, damit die Startseite klein bleibt; [lat, lon]
                    verlaeufe[str(l.id)] = [[lat, lon] for lon, lat in l.verlauf["coordinates"]]
            schnee = schnee_uebersicht(session, g)
            gebiete.append({
                "slug": g.slug,
                "name": g.name,
                "lat": pos[0] if pos else None,
                "lon": pos[1] if pos else None,
                "hoehe_m": g.hoehe_m,
                "tourist_url": g.tourist_url,
                "nachbarn": sorted(n.slug for n in g.nachbarn),
                "loipengebuehr": {"eur": g.loipengebuehr_eur, "text": g.loipengebuehr_text, "url": g.loipengebuehr_url},
                "parkplaetze": [
                    {"name": p.name, "lat": p.lat, "lon": p.lon, "gebuehr_eur_tag": p.gebuehr_eur_tag,
                     "gebuehr_text": p.gebuehr_text, "url": p.quelle_url, "geschaetzt": p.koordinate_geschaetzt}
                    for p in sorted(g.parkplaetze, key=lambda x: x.name)
                ],
                "haltestellen": g.haltestellen or [],
                "schnee": {**schnee, "messtag": schnee["messtag"].isoformat() if schnee["messtag"] else None},
                "vorhersage": _vorhersage(session, g, heute),
                "loipen": loipen,
            })
        regionen[region.slug] = {"region": {"slug": region.slug, "name": region.name}, "gebiete": gebiete}
        strecken[region.slug] = verlaeufe

    orte_yaml = lade_yaml(config_dir / "orte.yaml") if (config_dir / "orte.yaml").exists() else {}
    orte = orte_yaml.get("orte", [])
    standard = orte_yaml.get("standard")
    index = {
        "version": 1,
        "erzeugt": jetzt.astimezone(BERLIN).isoformat(timespec="minutes"),
        "regionen": [
            {"slug": s, "name": r["region"]["name"], "gebiete": len(r["gebiete"]),
             "mitte": _mitte(r["gebiete"]),
             "datei": f"daten/{s}.json", "strecken": f"strecken/{s}.json"}
            for s, r in regionen.items()
        ],
        "orte": orte,
        "standardort": standard,
        "quellen": [
            {"key": q.key, "name": q.name, "status": q.last_status, "letzter_lauf": _iso(q.last_run_at),
             "anzahl": q.last_count, "dauer_s": q.last_dauer_s, "fehler": q.last_error}
            for q in session.scalars(select(Quelle).order_by(Quelle.key))
        ],
        "kennzahlen": {"loipen": gesamt, "gebiete": sum(len(r["gebiete"]) for r in regionen.values()),
                       "veraltet": veraltet, **kennzahl},
    }
    return {"index": index, "regionen": regionen, "strecken": strecken}
