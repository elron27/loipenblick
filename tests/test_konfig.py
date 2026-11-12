"""Quellen und Gebiete als Konfiguration: P2."""

import shutil

import pytest
import yaml
from sqlalchemy import func, select

from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml, pruefe
from loipen.models import Gebiet, Quelle


@pytest.mark.req("P2", ak=1)
def test_p2_alle_quellen_aus_sources_yaml(session):
    lade_und_abgleichen(session)
    sources = lade_yaml(CONFIG_DIR / "sources.yaml")
    keys = {q["key"] for q in sources["quellen"]}
    assert set(session.scalars(select(Quelle.key))) == keys
    assert {"tegernsee", "bayrischzell", "fischbachau", "sachrang"} <= keys


@pytest.mark.req("P2", ak=2)
def test_p2_neuer_eintrag_ohne_codeaenderung(session, tmp_path):
    shutil.copytree(CONFIG_DIR, tmp_path, dirs_exist_ok=True)
    lade_und_abgleichen(session, tmp_path)

    sources = lade_yaml(tmp_path / "sources.yaml")
    sources["quellen"].append({
        "key": "schliersee",
        "adapter": "ats",
        "name": "Schliersee (Test)",
        "base_url": "https://www.schliersee.example/",
        "nutzung": {"robots": "erlaubt", "robots_geprueft": "2026-11-12", "nutzungsbedingungen_geprueft": None},
        "config": {"default_gebiet": "fischbachau"},
    })
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump(sources, allow_unicode=True), encoding="utf-8")
    lade_und_abgleichen(session, tmp_path)

    neu = session.scalar(select(Quelle).where(Quelle.key == "schliersee"))
    assert neu.adapter == "ats"
    assert neu.base_url == "https://www.schliersee.example"
    assert neu.config["zeitplan"]["saison_uhrzeiten"] == [7, 12, 17]


@pytest.mark.req("P2")
def test_p2_abgleich_ist_wiederholbar(session):
    lade_und_abgleichen(session)
    lade_und_abgleichen(session)
    gebiete = lade_yaml(CONFIG_DIR / "gebiete.yaml")
    assert session.scalar(select(func.count()).select_from(Gebiet)) == len(gebiete["gebiete"])


@pytest.mark.req("P2")
def test_p2_konfiguration_ist_widerspruchsfrei():
    assert pruefe(lade_yaml(CONFIG_DIR / "sources.yaml"), lade_yaml(CONFIG_DIR / "gebiete.yaml")) == []


@pytest.mark.req("P2")
def test_p2_fehler_werden_gemeldet():
    sources = {"quellen": [{"key": "x", "adapter": "ats", "name": "x", "base_url": "https://x",
                            "config": {"default_gebiet": "gibtsnicht"}}]}
    gebiete = {"regionen": [{"slug": "r", "name": "R"}],
               "gebiete": [{"slug": "a", "name": "A", "region": "r", "tourist_url": "https://a",
                            "nachbarn": ["b"], "parkplaetze": [{"name": "P"}]}]}
    fehler = "\n".join(pruefe(sources, gebiete))
    assert "gibtsnicht" in fehler
    assert "unbekannter Nachbar b" in fehler
    assert "Parkplatz ohne Name oder Koordinaten" in fehler
