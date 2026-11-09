from pathlib import Path

from sqlalchemy import func, select

from loipen.models import Gebiet, Quelle
from loipen.sources import load_sources_file, sync_sources

SOURCES = Path(__file__).parent.parent / "config" / "sources.yaml"


def test_sources_file_is_consistent():
    data = load_sources_file(SOURCES)
    slugs = {g["slug"] for g in data["gebiete"]}
    for q in data["quellen"]:
        assert q["config"]["default_gebiet"] in slugs, q["key"]
        for slug in q["config"].get("gebiet_map", {}).values():
            assert slug in slugs, (q["key"], slug)


def test_sync_is_idempotent(session):
    data = load_sources_file(SOURCES)
    sync_sources(session, data)
    session.commit()
    sync_sources(session, data)
    session.commit()

    assert session.scalar(select(func.count()).select_from(Gebiet)) == len(data["gebiete"])
    assert session.scalar(select(func.count()).select_from(Quelle)) == len(data["quellen"])
    tegernsee = session.scalar(select(Quelle).where(Quelle.key == "tegernsee"))
    assert tegernsee.adapter == "ats"
    assert tegernsee.base_url == "https://www.tegernsee.com"
