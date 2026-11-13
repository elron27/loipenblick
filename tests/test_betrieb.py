"""Betrieb auf dem NAS: B4 (Compose, keine Secrets), B12 (Vorschau), D6 (PostgreSQL), P8, P9."""

import re
import subprocess
from datetime import date, datetime

import pytest
import yaml
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from loipen import generator
from loipen.models import Base
from loipen.zeitplan import ist_faellig, ist_saison, uhrzeiten
from tests.conftest import ROOT, TEST_DATABASE_URL


def compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


@pytest.mark.req("B4", ak=1)
def test_b4_compose_startet_db_worker_vorschau():
    services = compose()["services"]
    assert {"db", "worker", "vorschau"} <= set(services)
    assert services["worker"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"


@pytest.mark.req("B4", ak=2)
def test_b4_secrets_nur_aus_umgebung():
    services = compose()["services"]
    assert services["db"]["environment"]["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD}"
    assert services["worker"]["env_file"] == ".env"
    assert ".env" in (ROOT / ".gitignore").read_text().splitlines()


SECRET_MUSTER = [
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google-API-Schluessel
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[0-9A-Za-z]{36}"),
    re.compile(r"key=[A-Z0-9]{8}-[A-Z0-9]{8}-[A-Z0-9]{8}"),  # Outdooractive-Projektschluessel
]


@pytest.mark.req("B4", ak=2)
def test_b4_kein_secret_im_repository():
    dateien = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    funde = []
    for name in dateien:
        pfad = ROOT / name
        if not pfad.is_file() or pfad.suffix in {".png", ".jpg", ".webp"}:
            continue
        inhalt = pfad.read_text(encoding="utf-8", errors="ignore")
        funde += [f"{name}: {m.pattern}" for m in SECRET_MUSTER if m.search(inhalt)]
    assert funde == []


@pytest.mark.req("B4", ak=3)
def test_b4_image_traegt_den_commit_stand():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG LOIPEN_VERSION" in docker and "ENV LOIPEN_VERSION=${LOIPEN_VERSION}" in docker
    workflow = yaml.safe_load((ROOT / ".github/workflows/image.yml").read_text(encoding="utf-8"))
    bauen = [s for s in workflow["jobs"]["image"]["steps"] if s.get("uses", "").startswith("docker/build-push-action")]
    assert "LOIPEN_VERSION=${{ github.sha }}" in bauen[0]["with"]["build-args"]


@pytest.mark.req("B4", ak=3)
def test_b4_fusszeile_zeigt_die_version(session, tmp_path):
    sha = "1da2271790cf70e146c642f674308a58b18b1cdb"
    generator.erzeuge(session, tmp_path, datetime(2026, 11, 13, 12, 0), version=sha)
    index = yaml.safe_load((tmp_path / "daten.json").read_text(encoding="utf-8"))
    assert index["image"] == "1da2271"
    app = (tmp_path / "app.js").read_text(encoding="utf-8")
    assert '" · Version " + S.idx.image' in app
    generator.erzeuge(session, tmp_path, datetime(2026, 11, 13, 12, 0))  # ohne Version: kein Eintrag
    assert "image" not in yaml.safe_load((tmp_path / "daten.json").read_text(encoding="utf-8"))


@pytest.mark.req("B4", ak=3)
def test_b4_worker_meldet_die_version_beim_start(monkeypatch, caplog):
    from loipen.config import get_settings
    from loipen.worker import __main__ as worker

    monkeypatch.setenv("LOIPEN_VERSION", "abc1234")
    get_settings.cache_clear()
    monkeypatch.setattr(worker, "lauf", lambda *a, **k: None)
    monkeypatch.setattr(worker.BlockingScheduler, "start", lambda self: None)
    with caplog.at_level("INFO", logger="loipen.worker"):
        worker.main([])
    get_settings.cache_clear()
    assert "Loipenblick Version abc1234 startet" in caplog.text


@pytest.mark.req("B12", ak=2)
def test_b12_vorschau_zeigt_genau_den_generator_ordner():
    services = compose()["services"]
    vorschau = [v for v in services["vorschau"]["volumes"] if v.endswith(":/usr/share/nginx/html:ro")]
    worker = [v for v in services["worker"]["volumes"] if v.split(":")[1] == "/app/site"]
    assert vorschau and worker
    assert vorschau[0].split(":")[0] == worker[0].split(":")[0] == "./site"
    assert services["worker"]["environment"]["LOIPEN_SITE_DIR"] == "/app/site"


@pytest.mark.req("B12", ak=1)
def test_b12_vorschau_im_heimnetz_erreichbar():
    ports = compose()["services"]["vorschau"]["ports"]
    assert ports == ["${VORSCHAU_PORT:-8080}:80"]


@pytest.mark.req("B12")
def test_b12_generator_schreibt_startseite(session, tmp_path):
    dateien = generator.erzeuge(session, tmp_path, datetime(2026, 11, 9, 12, 0))
    assert {"index.html", "daten.json", "app.js", "app.css"} <= {d.name for d in dateien}
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "ohne Gewähr" in html
    assert not list(tmp_path.rglob(".tmp-*"))


@pytest.mark.req("D6", ak=1)
def test_d6_tests_laufen_gegen_postgresql(session):
    assert session.bind.dialect.name == "postgresql"
    assert session.execute(text("select 1")).scalar() == 1


@pytest.mark.req("D6")
def test_d6_migration_ergibt_das_modell(engine):
    """Leere Datenbank -> alembic upgrade head -> Schema gleich dem Modell."""
    name = "loipen_migration_test"
    admin = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
        conn.execute(text(f"CREATE DATABASE {name}"))
    url = admin.url.set(database=name)
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "migrations"))
        cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
        command.upgrade(cfg, "head")
        mig = create_engine(url)
        with mig.connect() as conn:
            unterschiede = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        mig.dispose()
        assert unterschiede == []
    finally:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
        admin.dispose()


@pytest.mark.req("P8", ak=1)
def test_p8_saison_dreimal_taeglich():
    assert uhrzeiten(date(2027, 1, 15)) == [7, 12, 17]
    assert ist_faellig(datetime(2027, 1, 15, 12, 0))
    assert not ist_faellig(datetime(2027, 1, 15, 9, 0))


@pytest.mark.req("P8", ak=2)
def test_p8_ausserhalb_hoechstens_einmal():
    assert len(uhrzeiten(date(2027, 7, 15))) <= 1
    assert len(uhrzeiten(date(2027, 7, 15), {"nebensaison_uhrzeiten": [6, 8, 20]})) == 1


@pytest.mark.req("P8", ak=3)
def test_p8_zeiten_und_grenzen_aus_konfiguration():
    plan = {"saison": {"von": "12-15", "bis": "03-15"}, "saison_uhrzeiten": [6, 18]}
    assert ist_saison(date(2027, 1, 1), plan)
    assert not ist_saison(date(2026, 12, 1), plan)
    assert uhrzeiten(date(2027, 1, 1), plan) == [6, 18]


@pytest.mark.req("P9", ak=2)
def test_p9_tests_laufen_bei_jedem_pull_request():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8"))
    ausloeser = wf.get("on") or wf.get(True)  # YAML liest "on" als True
    assert "pull_request" in ausloeser
    schritte = " ".join(str(s.get("run", "")) for s in wf["jobs"]["pytest"]["steps"])
    assert "pytest" in schritte
