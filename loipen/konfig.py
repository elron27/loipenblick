"""Konfiguration als Daten (P2): config/sources.yaml und config/gebiete.yaml.

Beide Dateien werden bei jedem Lauf neu gelesen und mit der Datenbank abgeglichen.
Der Abgleich legt an und aktualisiert, er loescht nichts: Historie bleibt erhalten.
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import Gebiet, Herkunft, Parkplatz, Quelle, Region

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def lade_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def pruefe(sources: dict, gebiete: dict) -> list[str]:
    """Findet Widersprueche zwischen den beiden Dateien, bevor etwas gespeichert wird."""
    fehler: list[str] = []
    regionen = {r["slug"] for r in gebiete.get("regionen", [])}
    slugs = [g["slug"] for g in gebiete.get("gebiete", [])]
    if len(slugs) != len(set(slugs)):
        fehler.append("gebiete.yaml: ein Gebiet-Slug kommt doppelt vor")
    for g in gebiete.get("gebiete", []):
        if g.get("region") not in regionen:
            fehler.append(f"Gebiet {g['slug']}: unbekannte Region {g.get('region')}")
        if not g.get("tourist_url"):
            fehler.append(f"Gebiet {g['slug']}: tourist_url fehlt")
        for n in g.get("nachbarn", []):
            if n not in slugs:
                fehler.append(f"Gebiet {g['slug']}: unbekannter Nachbar {n}")
        for p in g.get("parkplaetze", []):
            if p.get("lat") is None or p.get("lon") is None or not p.get("name"):
                fehler.append(f"Gebiet {g['slug']}: Parkplatz ohne Name oder Koordinaten")
    keys = [q["key"] for q in sources.get("quellen", [])]
    if len(keys) != len(set(keys)):
        fehler.append("sources.yaml: ein Quellen-Key kommt doppelt vor")
    for q in sources.get("quellen", []):
        cfg = q.get("config", {})
        # P17: jede Quelle nennt, wann robots.txt und Nutzungsbedingungen geprueft wurden
        nutzung = q.get("nutzung") or {}
        for feld in ("robots_geprueft", "nutzungsbedingungen_geprueft"):
            if feld not in nutzung:
                fehler.append(f"Quelle {q['key']}: nutzung.{feld} fehlt")
        if str(nutzung.get("robots", "erlaubt")) != "erlaubt":
            fehler.append(f"Quelle {q['key']}: robots.txt erlaubt den Abruf nicht")
        # P20: eine Ortsseite nur, wenn sie ein Gebiet ohne andere Quelle schliesst
        if q.get("art") == "ortsseite" and not q.get("schliesst"):
            fehler.append(f"Quelle {q['key']}: Ortsseite ohne Angabe, welches Gebiet sie schliesst")
        for slug in q.get("schliesst") or []:
            if slug not in slugs:
                fehler.append(f"Quelle {q['key']}: schliesst unbekanntes Gebiet {slug}")
        for slug in cfg.get("gebiete", []):
            if slug not in slugs:
                fehler.append(f"Quelle {q['key']}: gebiete nennt unbekanntes Gebiet {slug}")
        if cfg.get("default_gebiet") not in slugs:
            fehler.append(f"Quelle {q['key']}: unbekanntes default_gebiet {cfg.get('default_gebiet')}")
        for slug in cfg.get("gebiet_map", {}).values():
            if slug not in slugs:
                fehler.append(f"Quelle {q['key']}: gebiet_map nennt unbekanntes Gebiet {slug}")
    return fehler


def _get_or_new(session: Session, model, **key):
    obj = session.scalar(select(model).filter_by(**key))
    if obj is None:
        obj = model(**key)
        session.add(obj)
    return obj


def abgleichen(session: Session, sources: dict, gebiete: dict) -> None:
    """Legt Regionen, Gebiete, Parkplaetze und Quellen an oder aktualisiert sie."""
    fehler = pruefe(sources, gebiete)
    if fehler:
        raise ValueError("Konfiguration fehlerhaft:\n" + "\n".join(fehler))

    regionen: dict[str, Region] = {}
    for r in gebiete.get("regionen", []):
        region = _get_or_new(session, Region, slug=r["slug"])
        region.name = r["name"]
        region.land = r.get("land", "DE")
        region.bundesland = r.get("bundesland")
        regionen[r["slug"]] = region

    alle: dict[str, Gebiet] = {}
    for g in gebiete.get("gebiete", []):
        gebiet = _get_or_new(session, Gebiet, slug=g["slug"])
        gebiet.name = g["name"]
        gebiet.region = regionen[g["region"]]
        gebiet.tourist_url = g["tourist_url"]
        gebiet.lat = g.get("lat")
        gebiet.lon = g.get("lon")
        gebuehr = g.get("loipengebuehr") or {}
        gebiet.loipengebuehr_eur = gebuehr.get("eur")
        gebiet.loipengebuehr_text = gebuehr.get("text")
        gebiet.loipengebuehr_url = gebuehr.get("url")
        gebiet.haltestellen = g.get("haltestellen", [])
        station = g.get("wetterstation") or {}
        gebiet.hoehe_m = g.get("hoehe_m")
        gebiet.wetterstation_id = station.get("id")
        gebiet.wetterstation_name = station.get("name")
        gebiet.wetterdienst = station.get("dienst")
        gebiet.namen = g.get("namen") or None
        gebiet.grenzinfo = g.get("grenzinfo")
        alle[g["slug"]] = gebiet
    session.flush()

    for g in gebiete.get("gebiete", []):
        gebiet = alle[g["slug"]]
        gebiet.nachbarn = [alle[n] for n in g.get("nachbarn", [])]
        for p in g.get("parkplaetze", []):
            park = _get_or_new(session, Parkplatz, gebiet_id=gebiet.id, name=p["name"])
            park.lat = p["lat"]
            park.lon = p["lon"]
            park.gebuehr_eur_tag = p.get("gebuehr_eur_tag")
            park.gebuehr_text = p.get("gebuehr_text")
            park.quelle_url = p.get("url")
            park.herkunft = Herkunft.HAND
            park.koordinate_geschaetzt = bool(p.get("koordinate_geschaetzt", False))

    standard_zeitplan = sources.get("zeitplan", {})
    standard_waechter = sources.get("waechter", {})
    for q in sources.get("quellen", []):
        quelle = _get_or_new(session, Quelle, key=q["key"])
        quelle.adapter = q["adapter"]
        quelle.name = q["name"]
        quelle.base_url = q["base_url"].rstrip("/")
        config = dict(q.get("config", {}))
        config["zeitplan"] = {**standard_zeitplan, **q.get("zeitplan", {})}
        # B26: Schwellen des Quellen-Waechters, je Quelle ueberschreibbar
        config["waechter"] = {**standard_waechter, **(q.get("waechter") or {})}
        # D15: Rang der Quelle bei Dubletten (1 = fuehrend), Standard 10
        config["rang"] = int(q.get("rang", 10))
        # U36: warum Loipen dieser Quelle keinen Streckenverlauf haben (steht auf der Loipenseite)
        if q.get("strecke_hinweis"):
            config["strecke_hinweis"] = q["strecke_hinweis"]
        if "gebiete" in config:
            # Adapter, die nach Koordinaten zuordnen (tirol.at), bekommen die Gebietsmitten aus gebiete.yaml
            config["gebiet_punkte"] = {
                g["slug"]: [g["lat"], g["lon"]] for g in gebiete.get("gebiete", [])
                if g["slug"] in config["gebiete"] and g.get("lat") is not None}
        quelle.config = config
        quelle.enabled = q.get("enabled", True)
    session.flush()


def lade_und_abgleichen(session: Session, config_dir: Path = CONFIG_DIR) -> None:
    abgleichen(
        session,
        lade_yaml(config_dir / "sources.yaml"),
        lade_yaml(config_dir / "gebiete.yaml"),
    )
