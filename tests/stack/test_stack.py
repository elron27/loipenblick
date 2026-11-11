"""Ende-zu-Ende im Docker-Teststack (docs/testumgebung.md): alles, was bisher erst am NAS sichtbar war.

Laeuft nur mit LOIPEN_TESTSTACK=1 gegen einen laufenden Stack, sonst uebersprungen:
    python scripts/teststack.py
Die Tests bauen aufeinander auf (Reihenfolge der Datei) und pruefen den echten Worker-Container:
Migrationen auf leerer Datenbank, Start-Lauf, statische Seite ueber nginx, Wetter, Push an ntfy,
Betriebsmeldung bei Ausfall, Sicherung und Wiederherstellung, Neustart ohne Datenverlust.
Quellen und Wetter kommen aus der Attrappe (Fixtures, Wetter im dokumentierten Format).
"""

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENV_DATEI = ROOT / "tests" / "stack" / "stack.env"
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.test.yml",
           "--env-file", str(ENV_DATEI)]

pytestmark = pytest.mark.skipif(os.environ.get("LOIPEN_TESTSTACK") != "1",
                                reason="nur im Teststack (python scripts/teststack.py)")


def _env() -> dict[str, str]:
    werte = {}
    for zeile in ENV_DATEI.read_text(encoding="utf-8").splitlines():
        if zeile.strip() and not zeile.startswith("#"):
            k, _, v = zeile.partition("=")
            werte[k.strip()] = v.strip()
    return werte


ENV = _env()
VORSCHAU = f"http://localhost:{ENV['VORSCHAU_PORT']}"
ATTRAPPE = f"http://localhost:{ENV['ATTRAPPE_PORT']}"
NTFY = f"http://localhost:{ENV['NTFY_PORT']}"
THEMA = ENV["LOIPEN_NTFY_URL"].rstrip("/").rsplit("/", 1)[-1]
QUELLEN = {"tegernsee": 26, "bayrischzell": 9, "fischbachau": 7, "sachrang": 4, "chiemgau": 69}
TABELLEN = ["quellen", "regionen", "gebiete", "loipen", "zustaende", "wetter", "parkplaetze"]


def compose(*args: str, eingabe: bytes | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([*COMPOSE, *args], cwd=ROOT, input=eingabe, capture_output=True, timeout=timeout,
                          check=True)


def worker(*args: str) -> str:
    return compose("exec", "-T", "worker", "python", "-m", "loipen.worker", *args).stdout.decode()


def http_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def http_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8")


def psql(sql: str, db: str = "loipen") -> str:
    return compose("exec", "-T", "db", "psql", "-U", ENV["POSTGRES_USER"], "-d", db, "-tAc", sql).stdout.decode().strip()


def anzahlen(db: str = "loipen") -> dict[str, int]:
    return {t: int(psql(f"SELECT count(*) FROM {t}", db)) for t in TABELLEN}


def ntfy_nachrichten() -> list[dict]:
    with urllib.request.urlopen(f"{NTFY}/{THEMA}/json?poll=1&since=all", timeout=10) as r:
        zeilen = r.read().decode("utf-8").splitlines()
    return [m for m in map(json.loads, zeilen) if m.get("event") == "message"]


def steuere(**szenario: str) -> None:
    query = "&".join(f"{k}={v}" for k, v in szenario.items())
    http_json(f"{ATTRAPPE}/_steuerung?{query}")


def warte_auf_startlauf(timeout_s: int = 180) -> None:
    """Der Worker laeuft beim Start einmal durch; erst danach ist der Stand fuer die Tests stabil."""
    ende = time.monotonic() + timeout_s
    while time.monotonic() < ende:
        logs = compose("logs", "worker").stdout.decode()
        if "Scheduler started" in logs:
            return
        time.sleep(2)
    pytest.fail("Worker hat den Start-Lauf nicht beendet:\n" + compose("logs", "worker").stdout.decode()[-3000:])


@pytest.fixture(scope="module", autouse=True)
def stack_bereit():
    steuere()
    warte_auf_startlauf()


@pytest.mark.req("B4", ak=1)
def test_migrationen_laufen_auf_leerer_datenbank():
    assert psql("SELECT version_num FROM alembic_version")
    status = compose("ps", "-a", "--format", "{{.Service}} {{.State}} {{.ExitCode}}").stdout.decode()
    assert "migrate exited 0" in status


@pytest.mark.req("B3", ak=1)
def test_start_lauf_holt_alle_quellen_und_erzeugt_die_seite():
    index = http_json(f"{VORSCHAU}/daten.json")
    quellen = {q["key"]: q for q in index["quellen"]}
    assert set(quellen) == set(QUELLEN)
    for key, anzahl in QUELLEN.items():
        assert quellen[key]["anzahl"] == anzahl, key
        assert quellen[key]["status"] in ("ok", "warnung"), quellen[key]
    assert index["kennzahlen"]["loipen"] == sum(QUELLEN.values())
    for region in index["regionen"]:
        daten = http_json(f"{VORSCHAU}/{region['datei']}")
        assert daten["gebiete"], region["slug"]
        http_json(f"{VORSCHAU}/{region['strecken']}")
    html = http_text(f"{VORSCHAU}/")
    assert "__STAND__" not in html and "<html" in html.lower()


@pytest.mark.req("D11", ak=1)
def test_wetter_landet_mit_quelle_in_der_seite():
    index = http_json(f"{VORSCHAU}/daten.json")
    gebiete = [g for r in index["regionen"] for g in http_json(f"{VORSCHAU}/{r['datei']}")["gebiete"]]
    import yaml

    mit_station = {g["slug"] for g in yaml.safe_load((ROOT / "config" / "gebiete.yaml").read_text(encoding="utf-8"))["gebiete"]
                   if g.get("wetterstation")}
    mit_schnee = [g for g in gebiete if g["schnee"]["schneehoehe_cm"] is not None]
    assert {g["slug"] for g in mit_schnee} == mit_station
    mit_position = [g for g in gebiete if g["lat"] is not None]
    assert mit_position and all(len(g["vorhersage"]) >= 7 for g in mit_position)
    assert all(g["schnee"]["quelle"] for g in mit_schnee)


@pytest.mark.req("P7", ak=3)
def test_alle_abrufe_mit_user_agent_und_robots():
    protokoll = http_json(f"{ATTRAPPE}/_protokoll")
    assert protokoll, "der Worker hat nichts abgerufen"
    assert {a["user_agent"] for a in protokoll} == {ENV["LOIPEN_USER_AGENT"]}
    assert any(a["pfad"] == "/robots.txt" for a in protokoll)


@pytest.mark.req("N1")
@pytest.mark.req("N4", ak=1)
@pytest.mark.req("B2", ak=1)
def test_push_bei_oeffnung_und_bei_ausfall_einer_quelle():
    vorher = len(ntfy_nachrichten())
    steuere(offen="1", ausfall="bayrischzell")
    worker("lauf")
    neu = ntfy_nachrichten()[vorher:]
    texte = [f"{m.get('title')}: {m.get('message')}" for m in neu]
    assert any("Ringseeloipe" in t and "befahrbar" in t for t in texte), texte
    assert any("Quelle bayrischzell meldet fehler" in t for t in texte), texte
    # nur das Abo auf Kreuth meldet sich: keine Loipe aus einem anderen Gebiet in der Nachricht
    assert not any("Golfplatzrunde" in t for t in texte), texte
    index = http_json(f"{VORSCHAU}/daten.json")
    assert {q["key"]: q["status"] for q in index["quellen"]}["bayrischzell"] == "fehler"
    assert index["kennzahlen"]["offen"] > 0

    vorher = len(ntfy_nachrichten())
    steuere()  # Quelle wieder da, Loipen wieder zu
    worker("lauf")
    texte = [f"{m.get('title')}: {m.get('message')}" for m in ntfy_nachrichten()[vorher:]]
    assert any("Quelle bayrischzell läuft wieder" in t for t in texte), texte
    assert any("geschlossen" in t for t in texte), texte


@pytest.mark.req("B14", ak=3)
def test_sicherung_und_wiederherstellung_im_container():
    worker("sicherung")
    dumps = sorted((ROOT / ".teststack" / "backup").glob("loipen-*.dump"))
    assert dumps, "kein Dump im Backup-Ordner"
    dump = dumps[-1]
    assert dump.stat().st_size > 1000

    user = ENV["POSTGRES_USER"]
    compose("exec", "-T", "db", "dropdb", "-U", user, "--if-exists", "loipen_restore")
    compose("exec", "-T", "db", "createdb", "-U", user, "loipen_restore")
    compose("exec", "-T", "db", "pg_restore", "-U", user, "-d", "loipen_restore", "--no-owner",
            eingabe=dump.read_bytes())
    assert anzahlen("loipen_restore") == anzahlen("loipen")
    assert psql("SELECT version_num FROM alembic_version", "loipen_restore") == psql("SELECT version_num FROM alembic_version")


@pytest.mark.req("B4", ak=1)
def test_neustart_und_update_behalten_die_daten():
    """Wie 'docker compose pull && docker compose up -d' auf dem NAS: Container neu, Daten bleiben."""
    vorher = anzahlen()
    compose("up", "-d", "--no-build", "--force-recreate", "--wait", "db", "worker", timeout=300)
    warte_auf_startlauf()
    nachher = anzahlen()
    assert nachher["loipen"] == vorher["loipen"]  # keine doppelten Loipen nach dem Neustart
    assert nachher["zustaende"] >= vorher["zustaende"]
    assert http_json(f"{VORSCHAU}/daten.json")["kennzahlen"]["loipen"] == sum(QUELLEN.values())


def test_bildschirmfotos_der_vorschau():
    """Fotos von Desktop und Handy fuer das CI-Artefakt; prueft, dass die Seite ohne JS-Fehler laedt."""
    sync_api = pytest.importorskip("playwright.sync_api")
    ziel = ROOT / ".teststack" / "screenshots"
    ziel.mkdir(parents=True, exist_ok=True)
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            try:
                browser = p.chromium.launch(executable_path=os.environ.get("LOIPEN_CHROMIUM", "/opt/pw-browsers/chromium"))
            except Exception:
                pytest.skip("kein Chromium verfuegbar")
        for name, opts in {"desktop": {"viewport": {"width": 1440, "height": 900}},
                           "handy": {**p.devices["Pixel 7"]}}.items():
            seite = browser.new_page(**opts)
            fehler = []
            seite.on("pageerror", lambda e: fehler.append(str(e)))
            seite.goto(VORSCHAU + "/", wait_until="networkidle")
            seite.screenshot(path=str(ziel / f"vorschau-{name}.png"), full_page=True)
            assert not fehler, fehler
            seite.close()
        browser.close()
