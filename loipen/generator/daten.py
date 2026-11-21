"""Daten fuer die statische Seite: ein Index und je Region eine Datei mit Gebieten, Loipen,
Wetter und Strecken. Die Seite liest nur diese JSON-Dateien (B7), keine Datenbank."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.adapters.stammdaten import KEIN_ZUSTAND
from loipen.dubletten import Eintrag, finde_dubletten
from loipen.konfig import ausgeblendet, lade_yaml
from loipen import osm, plausibel
from loipen.models import Gebiet, Loipe, Quelle, Region, Status, Wetter, WetterArt, Zustand
from loipen.sonderloipen import sonderloipe
from loipen.wetter import gebiet_position, schnee_uebersicht

BERLIN = ZoneInfo("Europe/Berlin")
VERALTET_STUNDEN = 48  # U6
HISTORIE_TAGE = 14  # U5
UEBERREGIONAL_AB_RANG = 3  # P22 AK 3: ab diesem Rang ist eine Quelle ein ueberregionales Portal
LAND_REIHENFOLGE = {"DE": 0, "AT": 1, "IT": 2, "CH": 3, "LI": 4}


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
        # U43 AK 4: ein Loipennetz, fuer das die Quelle nur "x von y Loipen offen" meldet (P28)
        "netz": _netz(z.rohtext) if z else None,
    }


def _netz(rohtext: str | None) -> dict | None:
    """{"offen": x, "alle": y} aus dem Rohtext eines Loipennetzes (NLW-Wintersportbericht), sonst None."""
    if not rohtext or not rohtext.startswith("{"):
        return None
    try:
        roh = json.loads(rohtext)
    except ValueError:
        return None
    if not isinstance(roh, dict) or not isinstance(roh.get("offen"), int) or not isinstance(roh.get("alle"), int):
        return None
    if roh["alle"] <= 0 or not 0 <= roh["offen"] <= roh["alle"]:
        return None
    return {"offen": roh["offen"], "alle": roh["alle"]}


HAND_PARK_NAH_KM = 1.5  # P39 AK 1: recherchierter Parkplatz des Gebiets, der zur Loipe gehoert


def _parken(d: dict, punkte: list | None, gebiet: Gebiet, osm_parkplaetze: list[dict]) -> list[dict]:
    """P39: Parkplaetze an dieser Loipe, der naechste zuerst. Von Hand recherchierte (config/gebiete.yaml) gehen vor;
    nur wenn keiner in der Naehe liegt, kommen oeffentliche Parkplaetze aus OpenStreetMap am Loipenstart dazu."""
    start = None
    if punkte:
        erster = punkte[0][0] if isinstance(punkte[0][0], list) else punkte[0]
        start = (erster[0], erster[1])
    if d["lat"] is not None:
        start = (d["lat"], d["lon"])
    hand = []
    for p in gebiet.parkplaetze:
        abstand = osm.km(start, (p.lat, p.lon)) if start else None
        if abstand is None or abstand <= HAND_PARK_NAH_KM:
            hand.append((abstand if abstand is not None else 0, {
                "name": p.name, "lat": p.lat, "lon": p.lon, "gebuehr_eur_tag": p.gebuehr_eur_tag,
                "gebuehr_text": p.gebuehr_text, "url": p.quelle_url, "geschaetzt": p.koordinate_geschaetzt,
                "entfernung_m": int(round(abstand * 1000, -1)) if abstand is not None else None, "quelle": "hand"}))
    if hand:
        return [p for _, p in sorted(hand, key=lambda x: x[0])]
    return osm.parkplaetze_bei(start, osm_parkplaetze) if start else []


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


def sichtbar(quelle: Quelle, oeffentlich: bool) -> bool:
    """Eine Quelle ohne Zustimmung (erlaubnis nur_test) erscheint nur in der Testversion (docs/kontaktliste.md).
    Eine abgelehnte Quelle (B30) erscheint nie, auch wenn noch alte Daten in der Datenbank liegen."""
    erlaubnis = (quelle.config or {}).get("erlaubnis")
    return (quelle.enabled and erlaubnis != "abgelehnt"
            and not (oeffentlich and erlaubnis == "nur_test"))


def baue(session: Session, jetzt: datetime, config_dir: Path, stale_days: int = 7, oeffentlich: bool = False) -> dict:
    """Gibt {"index": ..., "regionen": {slug: {...}}, "strecken": {slug: {...}}, "verdeckt": {id: fuehrend}} zurueck.
    "verdeckt" (Dubletten) braucht die Saisonstatistik fuer den Quellenvergleich (U39)."""
    heute = jetzt.astimezone(BERLIN).date()
    zustaende: dict[int, list[Zustand]] = {}
    for z in session.scalars(select(Zustand).order_by(Zustand.abgerufen_at, Zustand.id)):
        zustaende.setdefault(z.loipe_id, []).append(z)

    # D15: Dubletten ueber Quellen hinweg einmal zeigen, bei der fuehrenden Quelle
    # B16 AK 2: eine abgeschaltete Quelle verschwindet von der Seite
    # B30 AK 3: ausgeblendete Gebiete und Loipen fehlen in beiden Versionen, gleich von welcher Quelle
    gebiete_aus, loipen_aus = ausgeblendet(
        lade_yaml(config_dir / "gebiete.yaml") if (config_dir / "gebiete.yaml").exists() else {})

    def gezeigt(l: Loipe) -> bool:
        return (sichtbar(l.quelle, oeffentlich) and l.gebiet.slug not in gebiete_aus
                and (l.gebiet.slug, l.name) not in loipen_aus)
    aktive = [l for l in session.scalars(select(Loipe).join(Quelle).where(Loipe.active, Quelle.enabled))
              if gezeigt(l)]
    verdeckt = finde_dubletten([
        Eintrag(l.id, l.name, l.quelle.key, int((l.quelle.config or {}).get("rang", 10)), l.gebiet.slug, l.gebiet.name,
                l.lat, l.lon, l.gebiet.region.slug if l.gebiet.region else "")
        for l in aktive])
    auch_bei: dict[int, list[dict]] = {}
    widerspruch: dict[int, list[str]] = {}  # D19 AK 3: oertliche Berichte, die die Loipe geschlossen melden
    ohne_schnee: dict[int, list[str]] = {}  # E-24: Ortsseiten, die an der Loipe 0 cm Schnee melden
    lage: dict[int, tuple[float, float]] = {}
    laenge: dict[int, tuple[float, str]] = {}
    strecke: dict[int, tuple[dict, str]] = {}  # P40: Streckenverlauf einer verdeckten Quelle
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
        # P40 AK 1: ebenso der Streckenverlauf
        if v.verlauf and fuehrend not in strecke:
            strecke[fuehrend] = (v.verlauf, v.quelle.name)
        vcfg = v.quelle.config or {}
        quer = bool(vcfg.get("querpruefung"))  # E-24: Ortsseite, die nur zum Gegenpruefen dient
        if (eintrag["status"] == Status.GESCHLOSSEN.value
                and (quer or int(vcfg.get("rang", 10)) <= plausibel.OERTLICH_BIS_RANG)
                and v.quelle.name not in widerspruch.get(fuehrend, [])):
            widerspruch.setdefault(fuehrend, []).append(v.quelle.name)
        if (quer and zv and zv[-1].schneehoehe_cm == 0
                and v.quelle.name not in ohne_schnee.get(fuehrend, [])):
            ohne_schnee.setdefault(fuehrend, []).append(v.quelle.name)
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
    unplausibel: list[int] = []
    osm_daten = osm.lade(session)
    # D16: nach Land (Deutschland zuerst), Bundesland und Region geordnet
    for region in sorted(session.scalars(select(Region)),
                         key=lambda r: (LAND_REIHENFOLGE.get(r.land, 9), r.bundesland or "", r.name)):
        if region.gebiete and all(g.slug in gebiete_aus for g in region.gebiete):
            continue  # B30 AK 3: Region ganz ausgeblendet
        gebiete = []
        verlaeufe: dict[str, list] = {}
        osm_region = osm_daten.get(region.slug) or {}
        for g in sorted(region.gebiete, key=lambda x: x.name):
            if g.slug in gebiete_aus:
                continue
            pos = gebiet_position(g)
            schnee = schnee_uebersicht(session, g)
            vorhersage = _vorhersage(session, g, heute)
            tmax_heute = next((v["tmax"] for v in vorhersage if v["datum"] == heute.isoformat()), None)
            loipen = []
            for l in sorted(g.loipen, key=lambda x: x.name):
                if not l.active or not gezeigt(l) or l.id in verdeckt:
                    continue
                d = _loipe(l, zustaende.get(l.id, []), l.quelle, jetzt, stale_days)
                d["auch_bei"] = auch_bei.get(l.id, [])
                b = bericht.get(l.gebiet_id)
                d["nicht_im_bericht"] = None
                # Nur ueberregionale Quellen (Rang ab 3, z. B. tirol.at) werden so zurueckgestuft; zwei oertliche
                # Berichte desselben Verbands (Seefeld: tourinfra Rang 1, Loipenbericht Rang 2) gelten beide.
                if (b is not None and b.id != l.quelle_id and rang(l) >= UEBERREGIONAL_AB_RANG
                        and rang(l) > int((b.config or {}).get("rang", 10))):
                    d["nicht_im_bericht"] = b.name
                    if d["status"] in (Status.OFFEN.value, Status.EINGESCHRAENKT.value):
                        d["status_laut_quelle"] = d["status"]
                        d["status"] = Status.UNBEKANNT.value
                # D19, E-23: offensichtliche Fehlmeldungen erscheinen geschlossen, mit Grund
                zl = zustaende.get(l.id) or []
                if d["status"] in plausibel.BEFAHRBAR and plausibel.anwenden(d, plausibel.gruende(
                        zl[-1] if zl else None, d["status"], d["sonder"], schnee if schnee["messtag"] else None,
                        tmax_heute, widerspruch.get(l.id, []), jetzt, ohne_schnee.get(l.id, []))):
                    unplausibel.append(l.id)
                if d["lat"] is None and l.id in lage:
                    d["lat"], d["lon"] = lage[l.id]
                    d["lage_von"] = auch_bei[l.id][0]["quelle"] if auch_bei.get(l.id) else None
                if d["laenge_km"] is None and l.id in laenge:
                    d["laenge_km"], d["laenge_von"] = laenge[l.id]
                d["strecke_von"] = None
                if l.verlauf:
                    # Strecken getrennt, damit die Startseite klein bleibt; [lat, lon]
                    verlaeufe[str(l.id)] = [[lat, lon] for lon, lat in l.verlauf["coordinates"]]
                elif l.id in strecke:
                    verlauf, von = strecke[l.id]
                    verlaeufe[str(l.id)] = [[lat, lon] for lon, lat in verlauf["coordinates"]]
                    d["strecke_von"], d["strecke_hinweis"] = von, None
                else:
                    # P40 AK 2: benannte OSM-Loipe, die nach Name, Lage und Laenge passt; mehrteilig als Liste von Linien
                    o = osm.strecke_fuer(d, {"name": g.name, "lat": pos[0] if pos else None,
                                             "lon": pos[1] if pos else None}, osm_region.get("loipen", []))
                    if o:
                        linien = osm.linien_fuer_seite(o["linien"])
                        verlaeufe[str(l.id)] = linien[0] if len(linien) == 1 else linien
                        d["strecke_von"], d["strecke_hinweis"] = osm.QUELLE, None
                        d["strecke_osm"] = {"name": o["namen"][0], "url": f"https://www.openstreetmap.org/{o['id']}",
                                            "laenge_km": o["laenge_km"]}
                        if d["lat"] is None:
                            d["lat"], d["lon"] = linien[0][0]
                            d["lage_von"] = osm.QUELLE
                d["parken"] = _parken(d, verlaeufe.get(str(l.id)), g, osm_region.get("parkplaetze", []))
                loipen.append(d)
                kennzahl[d["status"]] += 1
                veraltet += d["veraltet"]
                gesamt += 1
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
                "nachbarn": sorted(n.slug for n in g.nachbarn if n.slug not in gebiete_aus),
                "loipengebuehr": {"eur": g.loipengebuehr_eur, "text": g.loipengebuehr_text, "url": g.loipengebuehr_url},
                "parkplaetze": [
                    {"name": p.name, "lat": p.lat, "lon": p.lon, "gebuehr_eur_tag": p.gebuehr_eur_tag,
                     "gebuehr_text": p.gebuehr_text, "url": p.quelle_url, "geschaetzt": p.koordinate_geschaetzt}
                    for p in sorted(g.parkplaetze, key=lambda x: x.name)
                ],
                "haltestellen": g.haltestellen or [],
                "schnee": {**schnee, "messtag": schnee["messtag"].isoformat() if schnee["messtag"] else None},
                "vorhersage": vorhersage,
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
            if (q.config or {}).get("erlaubnis") != "abgelehnt"
            and not (oeffentlich and (q.config or {}).get("erlaubnis") == "nur_test")
        ],
        "abdeckung": abdeckung,
        # Quellen ohne Zustimmung, die nur die Testversion zeigt (docs/kontaktliste.md)
        "nur_test": [] if oeffentlich else sorted(
            q.key for q in session.scalars(select(Quelle).where(Quelle.enabled))
            if (q.config or {}).get("erlaubnis") == "nur_test"),
        "dubletten": len(verdeckt),
        "kennzahlen": {"loipen": gesamt, "gebiete": sum(len(r["gebiete"]) for r in regionen.values()),
                       "veraltet": veraltet, "unplausibel": len(unplausibel), **kennzahl},
    }
    return {"index": index, "regionen": regionen, "strecken": strecken, "verdeckt": verdeckt,
            "unplausibel": unplausibel}
