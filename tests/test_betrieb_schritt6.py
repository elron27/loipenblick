"""Schritt 6: Zeitplan (B3), Dump (B14), Alarme (N1, N4), Ueberwachung (B2), Kosten (B9)."""

import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from sqlalchemy import select

from loipen.ablauf import rufe_quelle_ab
from loipen.ereignisse import (
    Ereignis, benachrichtige, betriebsmeldung, erkenne, lade_abos, ntfy_sender, passt, pruefe_abos,
)
from loipen.konfig import lade_und_abgleichen, lade_yaml
from loipen.models import Loipe, Quelle, Zustand
from loipen.sicherung import aufraeumen, dump, sichere
from tests.conftest import ROOT, TEST_DATABASE_URL
from tests.helpers import FixtureFetcher

T0 = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
RINGSEE = "a-ringseeloipe-42-km-skating-u-klassisch"


# ---------- B2 ----------

@pytest.fixture
def db(session):
    lade_und_abgleichen(session)
    return session


def abrufen(session, key, zeit=T0, **kw):
    q = session.scalar(select(Quelle).where(Quelle.key == key))
    return rufe_quelle_ab(session, q, FixtureFetcher(key, q.base_url, **kw), zeit)


@pytest.mark.req("B2", ak=1)
def test_b2_dauer_je_quelle_wird_gespeichert(db):
    abrufen(db, "bayrischzell")
    q = db.scalar(select(Quelle).where(Quelle.key == "bayrischzell"))
    assert q.last_dauer_s is not None and q.last_dauer_s >= 0


@pytest.mark.req("B2", ak=2)
def test_b2_null_loipen_geben_warnung_und_meldung(db):
    q = db.scalar(select(Quelle).where(Quelle.key == "bayrischzell"))
    abrufen(db, "bayrischzell")
    assert q.last_status == "ok"

    class Leer:
        def get(self, url):
            return "<html></html>"

    lauf = rufe_quelle_ab(db, q, Leer(), T0 + timedelta(hours=1))
    assert q.last_status == "warnung" and "0 Loipen" in q.last_error
    assert betriebsmeldung(q.key, lauf.status_vorher, lauf.status, q.last_error)


def test_betriebsmeldung_nur_beim_wechsel():
    assert betriebsmeldung("x", "ok", "ok", None) is None
    assert betriebsmeldung("x", "fehler", "fehler", "a") is None  # nicht bei jedem Lauf erneut
    assert betriebsmeldung("x", "ok", "fehler", "kaputt")[0].endswith("meldet fehler")
    assert "läuft wieder" in betriebsmeldung("x", "fehler", "ok", None)[0]


# ---------- N1 ----------

def zustand(status, km=None, quelle_at=None):
    return Zustand(status=status, gespurt_gesamt_km=km, quelle_aktualisiert_at=quelle_at)


def test_erkenne_ereignisse():
    assert erkenne(None, zustand("offen")) is None  # erster Abruf loest nichts aus
    assert erkenne(zustand("geschlossen"), zustand("offen")) == "oeffnet"
    assert erkenne(zustand("unbekannt"), zustand("eingeschraenkt")) == "oeffnet"
    assert erkenne(zustand("offen"), zustand("geschlossen")) == "schliesst"
    assert erkenne(zustand("offen", 5), zustand("offen", 8)) == "frisch_gespurt"
    assert erkenne(zustand("offen", 5, T0), zustand("offen", 5, T0 + timedelta(hours=3))) == "frisch_gespurt"
    assert erkenne(zustand("offen", 5, T0), zustand("offen", 5, T0)) is None
    assert erkenne(zustand("geschlossen"), zustand("geschlossen")) is None
    assert erkenne(zustand("offen", 8), zustand("offen", 5)) is None  # weniger gespurt ist kein Ereignis


def e(art, loipe="Ringseeloipe", gebiet="kreuth", region="tegernsee"):
    return Ereignis(art, loipe, gebiet, gebiet.title(), region, "offen", 8.4)


@pytest.mark.req("N1", ak=1)
def test_n1_abo_gilt_nur_fuer_diese_loipe_und_dieses_ereignis():
    abo = {"name": "a", "loipen": ["Ringseeloipe"], "ereignisse": ["frisch_gespurt"]}
    assert passt(abo, e("frisch_gespurt"))
    assert not passt(abo, e("oeffnet"))
    assert not passt(abo, e("schliesst"))
    assert not passt(abo, e("frisch_gespurt", loipe="Rundkurs Point"))
    gesendet = []
    ereignisse = [e("frisch_gespurt"), e("oeffnet"), e("frisch_gespurt", loipe="Rundkurs Point"),
                  e("schliesst", loipe="Andere", gebiet="sachrang", region="chiemgau")]
    n = benachrichtige([abo], ereignisse, lambda t, x: gesendet.append((t, x)))
    assert n == 1 and len(gesendet) == 1
    assert gesendet[0][1].count("\n") == 0 and "Ringseeloipe" in gesendet[0][1] and "frisch gespurt" in gesendet[0][1]


@pytest.mark.req("N1", ak=1)
def test_n1_abo_auf_gebiet_und_region_und_ohne_ereignisliste():
    assert passt({"gebiete": ["kreuth"]}, e("oeffnet"))
    assert passt({"regionen": ["tegernsee"]}, e("schliesst"))
    assert not passt({"regionen": ["chiemgau"]}, e("schliesst"))
    assert not passt({"gebiete": ["kreuth"], "ereignisse": ["oeffnet"]}, e("schliesst"))


def test_abo_pruefung_findet_tippfehler():
    gebiete = lade_yaml(ROOT / "config" / "gebiete.yaml")
    assert pruefe_abos([{"name": "ok", "gebiete": ["kreuth"], "ereignisse": ["oeffnet"]}], gebiete) == []
    fehler = pruefe_abos([{"name": "x", "gebiete": ["krueth"], "ereignisse": ["blub"]}, {"name": "leer"}], gebiete)
    assert len(fehler) == 3
    assert lade_abos(ROOT / "config") == []  # ausgelieferte Datei hat keine Abos


@pytest.mark.req("N1", ak=1)
def test_n1_ende_zu_ende_aus_zwei_abrufen(db):
    """Loipe geschlossen -> offen: nur das Abo auf diese Loipe meldet sich."""
    abrufen(db, "tegernsee")
    q = db.scalar(select(Quelle).where(Quelle.key == "tegernsee"))
    seite = FixtureFetcher("tegernsee", q.base_url).seite(f"schneebericht/{RINGSEE}.html")
    offen = seite.replace("<strong>nicht befahrbar</strong>", "<strong>geöffnet</strong>")
    lauf = abrufen(db, "tegernsee", T0 + timedelta(days=40), ersetze={RINGSEE: offen})
    assert [x.art for x in lauf.ereignisse] == ["oeffnet"]
    gesendet = []
    abos = [{"name": "ring", "loipen": ["Ringseeloipe"], "ereignisse": ["oeffnet"]},
            {"name": "andere", "loipen": ["Rundkurs Point"]},
            {"name": "spaeter", "loipen": ["Ringseeloipe"], "ereignisse": ["schliesst"]}]
    assert benachrichtige(abos, lauf.ereignisse, lambda t, x: gesendet.append(x)) == 1


# ---------- N4 ----------

@pytest.mark.req("N4", ak=1)
def test_n4_ntfy_sendet_json_an_das_thema():
    import httpx
    gesehen = []

    def handler(request):
        gesehen.append(request)
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sender = ntfy_sender("https://ntfy.sh/mein-thema", client)
    sender("Titel", "Text")
    import json
    r = gesehen[0]
    assert str(r.url) == "https://ntfy.sh"
    assert json.loads(r.content) == {"topic": "mein-thema", "title": "Titel", "message": "Text", "tags": ["ski"]}
    assert ntfy_sender(None) is None and ntfy_sender("https://ntfy.sh/") is None


@pytest.mark.req("N4", ak=1)
def test_n4_fehler_beim_versand_stoppt_nichts_und_wird_wiederholt():
    versuche = []

    def sender(t, x):
        versuche.append(1)
        if len(versuche) == 1:
            raise ConnectionError("kurz weg")

    assert benachrichtige([{"name": "a", "gebiete": ["kreuth"]}], [e("oeffnet")], sender) == 1
    assert len(versuche) == 2

    def immer_kaputt(t, x):
        raise ConnectionError("weg")

    assert benachrichtige([{"name": "a", "gebiete": ["kreuth"]}], [e("oeffnet")], immer_kaputt) == 0
    assert benachrichtige([{"name": "a", "gebiete": ["kreuth"]}], [e("oeffnet")], None) == 0


# ---------- B14 ----------

needs_pg = pytest.mark.skipif(shutil.which("pg_dump") is None, reason="pg_dump fehlt")


@needs_pg
@pytest.mark.req("B14", ak=1)
def test_b14_dump_entsteht_und_alte_werden_geloescht(tmp_path):
    jetzt = datetime(2026, 11, 9, 3, 30)
    for tage in (0, 29, 31, 90):
        (tmp_path / f"loipen-{jetzt - timedelta(days=tage):%Y%m%d-%H%M}.dump").write_bytes(b"x")
    (tmp_path / "notizen.txt").write_text("bleibt")
    ziel = sichere(TEST_DATABASE_URL, tmp_path, jetzt)
    assert ziel.name == "loipen-20261109-0330.dump" and ziel.stat().st_size > 100
    namen = sorted(p.name for p in tmp_path.iterdir())
    assert "notizen.txt" in namen
    assert not any("20260810" in n or "20260911" in n for n in namen)  # 90 und 31 Tage
    assert any("20261011" in n for n in namen)  # 29 Tage bleiben


def test_b14_aufraeumen_ignoriert_fremde_dateien(tmp_path):
    (tmp_path / "loipen-kaputt.dump").write_bytes(b"x")
    (tmp_path / "anderes.dump").write_bytes(b"x")
    assert aufraeumen(tmp_path, datetime(2026, 11, 9)) == []


@needs_pg
@pytest.mark.req("B14", ak=3)
def test_b14_wiederherstellung_aus_dump(engine, tmp_path):
    """Dump der Testdatenbank, Restore in eine frische Datenbank, Daten sind gleich."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    # eigene, wirklich committende Sitzung: pg_dump sieht nur Festgeschriebenes
    session = Session(engine)
    try:
        lade_und_abgleichen(session)
        abrufen(session, "bayrischzell")
        session.commit()
        ziel = dump(TEST_DATABASE_URL, tmp_path, datetime(2026, 11, 9, 3, 30))
        basis = TEST_DATABASE_URL.rsplit("/", 1)[0]
        admin = create_engine(basis + "/postgres", isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            c.execute(text("DROP DATABASE IF EXISTS loipen_restore_test"))
            c.execute(text("CREATE DATABASE loipen_restore_test"))
        u = basis.replace("postgresql+psycopg://", "")
        cred, host = u.split("@")
        user, pw = cred.split(":")
        env = {"PGPASSWORD": pw, "PATH": "/usr/bin:/bin"}
        subprocess.run(["pg_restore", "-h", host.split(":")[0], "-p", host.split(":")[1] if ":" in host else "5432",
                        "-U", user, "-d", "loipen_restore_test", str(ziel)], check=True, env=env, capture_output=True)
        neu = create_engine(basis + "/loipen_restore_test")
        with neu.connect() as c:
            n = c.execute(text("select count(*) from loipen")).scalar()
        assert n == 9
        neu.dispose()
        with admin.connect() as c:
            c.execute(text("DROP DATABASE loipen_restore_test"))
    finally:
        session.close()
        with engine.begin() as c:
            names = c.execute(text("select tablename from pg_tables where schemaname='public'")).scalars().all()
            c.execute(text("truncate " + ",".join(f'"{n}"' for n in names) + " restart identity cascade"))


# ---------- B3 ----------

@pytest.mark.req("B3", ak=1)
def test_b3_zeitplan_laeuft_im_worker_ohne_dsm_aufgabe():
    quelltext = (ROOT / "loipen" / "worker" / "__main__.py").read_text(encoding="utf-8")
    assert "BlockingScheduler" in quelltext and 'add_job(tick, "cron", minute=0)' in quelltext
    assert 'add_job(sicherung, "cron"' in quelltext
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert compose["services"]["worker"]["restart"] in ("unless-stopped", "always")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["python", "-m", "loipen.worker"]' in dockerfile
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Taskplaner" in readme and "nicht" in readme


# ---------- B9 ----------

@pytest.mark.req("B9", ak=1)
def test_b9_kostenuebersicht_bleibt_unter_60_euro_im_jahr():
    kosten = yaml.safe_load((ROOT / "config" / "kosten.yaml").read_text(encoding="utf-8"))
    summe = sum(p["eur_pro_jahr"] for p in kosten["posten"])
    assert summe <= 60, f"{summe} EUR im Jahr"
    assert any(p["name"].lower().startswith("webspace") for p in kosten["posten"])
