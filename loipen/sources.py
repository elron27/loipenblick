"""Laedt config/sources.yaml und gleicht Gebiete und Quellen mit der Datenbank ab."""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import Gebiet, Quelle


def load_sources_file(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sync_sources(session: Session, data: dict) -> None:
    """Legt Gebiete und Quellen an oder aktualisiert sie. Loescht nichts."""
    for g in data.get("gebiete", []):
        gebiet = session.scalar(select(Gebiet).where(Gebiet.slug == g["slug"]))
        if gebiet is None:
            gebiet = Gebiet(slug=g["slug"])
            session.add(gebiet)
        gebiet.name = g["name"]
        gebiet.region = g["region"]
        gebiet.lat = g.get("lat")
        gebiet.lon = g.get("lon")
        gebiet.tourist_url = g.get("tourist_url")

    for q in data.get("quellen", []):
        quelle = session.scalar(select(Quelle).where(Quelle.key == q["key"]))
        if quelle is None:
            quelle = Quelle(key=q["key"])
            session.add(quelle)
        quelle.adapter = q["adapter"]
        quelle.name = q["name"]
        quelle.base_url = q["base_url"].rstrip("/")
        quelle.config = q.get("config", {})
        quelle.enabled = q.get("enabled", True)
