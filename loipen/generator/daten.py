"""Daten fuer die statische Seite: ein Index und je Region eine Datei mit Gebieten, Loipen,
Wetter und Strecken. Die Seite liest nur diese JSON-Dateien (B7), keine Datenbank."""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.adapters.stammdaten import KEIN_ZUSTAND
from loipen.dubletten import Eintrag, finde_dubletten
from loipen.konfig import lade_yaml
from loipen.models import Gebiet, Loipe, Quelle, Region, Status, Wetter, WetterArt, Zustand
from loipen.sonderloipen import sonderloipe
from loipen.wetter import gebiet_position, schnee_uebersicht

BERLIN = ZoneInfo("Europe/Berlin")
VERALTET_STUNDEN = 48  # U6
HISTORIE_TAGE = 14  # U5
LAND_REIHENFOLGE = {"DE": 0, "AT": 1, "IT": 2}


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
        # U30: die Quelle meldet keinen Praeparierzeitpunkt; die Seite zeigt dann den Abrufzeitpunkt
        "ohne_datum": bool(z and z.quelle_aktualisiert_at is None),
        # P16: die Quelle fuehrt nur Stammdaten (Berchtesgaden)
        "ohne_zustand": bool(z and z.rohtext == KEIN_ZUSTAND),
        "abgerufen": _iso(z.zuletzt_bestaetigt_at) if z else None,
        "veraltet": bool(z is None or fehler or (alter_h is not None and alter_h > VERALTET_STUNDEN)),
        "quelle_fehler": fehler,
        "quelle": {"name": quelle.name, "url": loipe.source_url},
        "historie": _historie(zustaende, jetzt.astimezone(BERLIN).date()),
        "strecke_hinweis": None if loipe.verlauf else (quelle.config or {}).get("strecke_hinweis"),
        "sonder": sonderloipe(loipe.name),  # Snowfarming, Opening, Gletscher, nur fuer Gruppen
    }


def _vorhersage(session: Session, gebiet: Gebiet, heute: date) -> list[dict]:
    zeilen = session.scalars(
        select(Wetter).where(
            Wetter.gebiet_id == gebiet.id, Wetter.art == WetterArt.VORHERSAGE.value, Wetter.datum >= heute
        ).order_by(Wetter.datum)
    ).all()
    return [
        {"datum": z.datum.isoformat(), "tmin": z.temp_min_c, "tmax": z.temp_max_c, "niederschlag_mm": z.niederschlag_mm,
         "sonne_h": z.sonne_h, "symbol": z.symbol}
        for z in zeilen
    ]


def _mitte(gebiete: list[dict]) -> list[float] | None:
    punkte = [(g["lat"], g["lon"]) for g in gebiete if g["lat"] is not None]
    if not punkte:
        return None
    return [round(sum(p[0] for p in punkte) / len(punkte), 3), round(sum(p[1] for p in punkte) / len(punkte), 3)]


def baue(session: Session, jetzt: datetime, config_dir: Path, stale_days: int = 7) -> dict:
    """Gibt {"index": ..., "regionen": {slug: {...}}, "strecken": {slug: {...}}, "verdeckt": {id: fuehrend}} zurueck.
    "verdeckt" (Dubletten) braucht die Saisonstatistik fuer den Quellenvergleich (U39)."""
    heute = jetzt.astimezone(BERLIN).date()
    zustaende: dict[int, list[Zustand]] = {}
    for z in session.scalars(select(Zustand).order_by(Zustand.abgerufen_at, Zustand.id)):
        zustaende.setdefault(z.loipe_id, []).append(z)

    # D15: Dubletten ueber Quellen hinweg einmal zeigen, bei der fuehrenden Quelle
    # B16 AK 2: eine abgeschaltete Quelle verschwindet von der Seite
    aktive = [l for l in session.scalars(select(Loipe).join(Quelle).where(Loipe.active, Quelle.enabled))]
    verdeckt = finde_dubletten([
        Eintrag(l.id, l.name, l.quelle.key, int((l.quelle.config or {}).get("rang", 10)), l.gebiet.slug, l.gebiet.name,
                l.lat, l.lon, l.gebiet.region.slug if l.gebiet.region else "")
        for l in aktive])
    auch_bei: dict[int, list[dict]] = {}
    lage: dict[int, tuple[float, float]] = {}
    laenge: dict[int, tuple[float, str]] = {}
    nach_id = {l.id: l for l in aktive}
    for versteckt, fuehrend in sorted(verdeckt.items()):
        v = nach_id[versteckt]
        if v.quelle_id == nach_id[fuehrend].quelle_id:
            continue  # Doppeleintrag derselben Quelle: nur verdecken, nicht als "auch bei" nennen
        # D18: der Status der verdeckten Quelle, damit die Seite eine Abweichung zeigen kann
        zv = zustaende.get(versteckt) or []
        eintrag = {"quelle": v.quelle.name, "name": v.name, "url": v.source_url,
                   "status": zv[-1].status if zv else None}
        # D18: fuehrt eine Quelle ohne Koordinaten (Seefeld), kommt die Lage von der verdeckten Loipe
        if v.lat is not None and fuehrend not in lage:
            lage[fuehrend] = (v.lat, v.lon)
        # ebenso die Laenge, wenn die fuehrende Quelle keine nennt (13.11.2026)
        if v.laenge_km is not None and fuehrend not in laenge:
            laenge[fuehrend] = (v.laenge_km, v.quelle.name)
        liste = auch_bei.setdefault(fuehrend, [])
        # tirol.at-Doppeleintraege einer Loipe nur einmal nennen; ein "offen" zaehlt fuer die Abweichung
        gleich = next((a for a in liste if a["quelle"] == eintrag["quelle"] and a["name"] == eintrag["name"]), None)
        if gleich is None:
            liste.append(eintrag)
        elif eintrag["status"] in (Status.OFFEN.value, Status.EINGESCHRAENKT.value):
            gleich["status"] = eintrag["status"]

    # P22 AK 3: Fuehrt in einem Gebiet ein oertlicher Loipenbericht (kleinerer Rang), gilt er dort als
    # massgeblich. Loipen, die nur eine nachrangige Quelle (tirol.at) nennt, bekommen einen Hinweis; meldet
    # diese sie als offen, zeigt die Seite "unbekannt", weil der Bericht des Verbands sie nicht fuehrt.
    def rang(l: Loipe) -> int:
        return int((l.quelle.config or {}).get("rang", 10))
    bericht: dict[int, Quelle] = {}
    for l in aktive:
        if l.id in verdeckt:
            continue
        b = bericht.get(l.gebiet_id)
        if b is None or rang(l) < int((b.config or {}).get("rang", 10)):
            bericht[l.gebiet_id] = l.quelle

    regionen: dict[str, dict] = {}
    strecken: dict[str, dict] = {}
    abdeckung: list[dict] = []
    kennzahl = {s.value: 0 for s in Status}
    veraltet = 0
    gesamt = 0
    # D16: nach Land (Deutschland zuerst), Bundesland und Region geordnet
    for region in sorted(session.scalars(select(Region)),
                         key=lambda r: (LAND_REIHENFOLGE.get(r.land, 9), r.bundesland or "", r.name)):
        gebiete = []
        verlaeufe: dict[str, list] = {}
        for g in sorted(region.gebiete, key=lambda x: x.name):
            pos = gebiet_position(g)
            loipen = []
            for l in sorted(g.loipen, key=lambda x: x.name):
                if not l.active or not l.quelle.enabled or l.id in verdeckt:
                    continue
                d = _loipe(l, zustaende.get(l.id, []), l.quelle, jetzt, stale_days)
                d["auch_bei"] = auch_bei.get(l.id, [])
                b = bericht.get(l.gebiet_id)
                d["nicht_im_bericht"] = None
                if b is not None and b.id != l.quelle_id and rang(l) > int((b.config or {}).get("rang", 10)):
                    d["nicht_im_bericht"] = b.name
                    if d["status"] in (Status.OFFEN.value, Status.EINGESCHRAENKT.value):
                        d["status_laut_quelle"] = d["status"]
                        d["status"] = Status.UNBEKANNT.value
                if d["lat"] is None and l.id in lage:
                    d["lat"], d["lon"] = lage[l.id]
                    d["lage_von"] = auch_bei[l.id][0]["quelle"] if auch_bei.get(l.id) else None
                if d["laenge_km"] is None and l.id in laenge:
                    d["laenge_km"], d["laenge_von"] = laenge[l.id]
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
                "namen": g.namen or {},
                "land": region.land,
                "bundesland": region.bundesland,
                "grenzinfo": g.grenzinfo,
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
        regionen[region.slug] = {"region": {"slug": region.slug, "name": region.name, "land": region.land,
                                            "bundesland": region.bundesland}, "gebiete": gebiete}
        # P13 AK 2: Anbindungsstand je Region
        mit_zustand = sum(1 for g in gebiete if any(not l["ohne_zustand"] for l in g["loipen"]))
        nur_stamm = sum(1 for g in gebiete if g["loipen"] and all(l["ohne_zustand"] for l in g["loipen"]))
        abdeckung.append({"region": region.name, "land": region.land, "bundesland": region.bundesland,
                          "gebiete": len(gebiete), "angebunden": mit_zustand, "nur_stammdaten": nur_stamm,
                          "ohne_quelle": len(gebiete) - mit_zustand - nur_stamm})
        strecken[region.slug] = verlaeufe

    orte_yaml = lade_yaml(config_dir / "orte.yaml") if (config_dir / "orte.yaml").exists() else {}
    orte = orte_yaml.get("orte", [])
    standard = orte_yaml.get("standard")
    index = {
        "version": 1,
        "erzeugt": jetzt.astimezone(BERLIN).isoformat(timespec="minutes"),
        "regionen": [
            {"slug": s, "name": r["region"]["name"], "land": r["region"]["land"],
             "bundesland": r["region"]["bundesland"], "gebiete": len(r["gebiete"]),
             "mitte": _mitte(r["gebiete"]),
             "datei": f"daten/{s}.json", "strecken": f"strecken/{s}.json",
             # U32/P21: die Karte laedt die Strecken aller Regionen, die welche haben
             "strecken_anzahl": len(strecken[s])}
            for s, r in regionen.items()
        ],
        "orte": orte,
        "standardort": standard,
        "quellen": [
            {"key": q.key, "name": q.name, "status": q.last_status, "letzter_lauf": _iso(q.last_run_at),
             "anzahl": q.last_count, "dauer_s": q.last_dauer_s, "fehler": q.last_error}
            for q in session.scalars(select(Quelle).order_by(Quelle.key))
        ],
        "abdeckung": abdeckung,
        "dubletten": len(verdeckt),
        "kennzahlen": {"loipen": gesamt, "gebiete": sum(len(r["gebiete"]) for r in regionen.values()),
                       "veraltet": veraltet, **kennzahl},
    }
    return {"index": index, "regionen": regionen, "strecken": strecken, "verdeckt": verdeckt}
