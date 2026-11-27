"""B34: Worker-Log als Datei und Mail bei Absturz oder Fehlern (ohne Datenbank, ohne Netz)."""

import logging
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from loipen import betriebslog
from loipen.betriebslog import Betriebslog

ROOT = Path(__file__).resolve().parent.parent
GEHEIM = "SehrGeheim-123456"


def settings(tmp_path, **kw):
    werte = dict(log_dir=str(tmp_path / "logs"), backup_dir=str(tmp_path / "backup"), fehler_mail=None,
                 waechter_mail=None, impressum_email="stefan@example.org", abo_absender=None,
                 smtp_benutzer="absender@example.org", smtp_host="smtp.example", smtp_passwort=GEHEIM,
                 fehler_mail_stunden=6, timezone="Europe/Berlin", version="abc1234", ntfy_url=None,
                 database_url="postgresql+psycopg://loipen:DbPasswort99@db:5432/loipen")
    werte.update(kw)
    return SimpleNamespace(**werte)


class Uhr:
    def __init__(self):
        self.t = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.t


@pytest.fixture
def mails():
    return []


@pytest.fixture
def betrieb(tmp_path, mails):
    b = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=Uhr(), umgebung={})
    yield b
    b.schliesse()


def text(m):
    return m.get_body(("plain",)).get_content()


def anhang(m):
    return [a.get_content() for a in m.iter_attachments()]


@pytest.mark.req("B34", ak=1)
def test_b34_log_steht_in_rotierender_datei(betrieb, tmp_path):
    betrieb.richte_ein()
    logging.getLogger("loipen.worker").info("Quelle tegernsee wird abgerufen")
    datei = tmp_path / "logs" / "worker.log"
    assert "Quelle tegernsee wird abgerufen" in datei.read_text(encoding="utf-8")
    rot = [h for h in betrieb.handler if isinstance(h, logging.handlers.RotatingFileHandler)][0]
    assert rot.maxBytes == 1_000_000 and rot.backupCount == 5


@pytest.mark.req("B34", ak=1)
def test_b34_ohne_log_dir_im_sicherungsordner(tmp_path):
    s = settings(tmp_path, log_dir=None)
    assert betriebslog.log_ordner(s) == tmp_path / "backup" / "logs"
    assert "backup/logs" in betriebslog.ordner_hinweis(s)


@pytest.mark.req("B34", ak=1)
def test_b34_compose_legt_logs_neben_die_env_und_startet_neu():
    worker = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["worker"]
    assert "./logs:/app/logs" in worker["volumes"]
    assert worker["environment"]["LOIPEN_LOG_DIR"] == "/app/logs"
    assert worker["restart"] == "unless-stopped"


@pytest.mark.req("B34", ak=1)
def test_b34_nicht_schreibbarer_ordner_stoppt_nichts(tmp_path, mails):
    (tmp_path / "datei").write_text("x")
    b = Betriebslog(settings(tmp_path, log_dir=str(tmp_path / "datei" / "logs")), mailer=mails.append,
                    jetzt=Uhr(), umgebung={})
    try:
        b.richte_ein()
        assert not b.datei_ok
        logging.getLogger("loipen.worker").error("trotzdem weiter")
        assert b.pruefe() is True  # Mail geht auch ohne Datei, nur ohne Anhang
        assert anhang(mails[0]) == []
    finally:
        b.schliesse()


@pytest.mark.req("B34", ak=2)
def test_b34_absturz_mail_mit_traceback_und_letzten_zeilen(betrieb, mails):
    betrieb.richte_ein()
    for i in range(250):
        logging.getLogger("loipen.worker").info("Zeile %d", i)
    try:
        raise RuntimeError("Datenbank weg")
    except RuntimeError as ex:
        betrieb.absturz(ex)
    assert len(mails) == 1
    m = mails[0]
    assert m["Subject"] == "Loipenblick: Worker abgestuerzt"
    assert m["To"] == "stefan@example.org" and m["From"] == "absender@example.org"
    body = text(m)
    assert "RuntimeError: Datenbank weg" in body and "Traceback" in body
    assert "Zeile 249" in body and "Zeile 30\n" not in body  # nur die letzten 200 Zeilen
    assert "Version: abc1234" in body and "Ordner logs neben der .env" in body
    assert "Zeile 0" in anhang(m)[0]  # das ganze Log haengt an


@pytest.mark.req("B34", ak=2)
def test_b34_empfaenger_reihenfolge(tmp_path):
    b = Betriebslog(settings(tmp_path, fehler_mail="f@example.org", waechter_mail="w@example.org"), umgebung={})
    assert b.an == "f@example.org"
    b = Betriebslog(settings(tmp_path, waechter_mail="w@example.org"), umgebung={})
    assert b.an == "w@example.org"
    b = Betriebslog(settings(tmp_path, abo_absender="abo@example.org"), umgebung={})
    assert b.an == "stefan@example.org" and b.absender == "abo@example.org"


@pytest.mark.req("B34", ak=2)
def test_b34_worker_main_meldet_absturz_und_beendet_mit_fehler(monkeypatch, tmp_path, mails):
    from loipen.config import get_settings
    from loipen.worker import __main__ as worker

    monkeypatch.setenv("LOIPEN_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOIPEN_SMTP_HOST", "smtp.example")
    monkeypatch.setenv("LOIPEN_IMPRESSUM_EMAIL", "stefan@example.org")
    get_settings.cache_clear()

    def kaputt(argv, betrieb=None):
        raise MemoryError("kein Speicher")
    monkeypatch.setattr(worker, "befehl", kaputt)
    vorher = signal.getsignal(signal.SIGTERM)
    try:
        with pytest.raises(MemoryError):
            worker.main([], mailer=mails.append, sender=False)
    finally:
        get_settings.cache_clear()
    assert len(mails) == 1 and "MemoryError: kein Speicher" in text(mails[0])
    assert not (tmp_path / "logs" / "worker.laeuft").exists()  # gemeldet, also beim Neustart keine zweite Mail
    assert signal.getsignal(signal.SIGTERM) == vorher


@pytest.mark.req("B34", ak=3)
def test_b34_harter_abbruch_wird_beim_naechsten_start_gemeldet(tmp_path, mails):
    uhr = Uhr()
    erster = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=uhr, umgebung={}).richte_ein()
    logging.getLogger("loipen.worker").info("Quelle tirol wird abgerufen")
    marke = tmp_path / "logs" / "worker.laeuft"
    assert marke.exists()
    # Speicher voll: der Prozess wird ohne Python-Fehler beendet, schliesse() laeuft nie
    for h in erster.handler:
        logging.getLogger().removeHandler(h)
        h.close()
    zweiter = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=uhr, umgebung={})
    try:
        zweiter.richte_ein()
        assert len(mails) == 1
        assert mails[0]["Subject"] == "Loipenblick: Worker wurde hart beendet"
        assert "Quelle tirol wird abgerufen" in text(mails[0]) and "Arbeitsspeicher" in text(mails[0])
        assert marke.exists()  # neue Marke fuer diesen Lauf
    finally:
        zweiter.schliesse()
    assert not marke.exists()


@pytest.mark.req("B34", ak=3)
def test_b34_sauberes_stoppen_ohne_mail(monkeypatch, tmp_path, mails):
    from loipen.config import get_settings
    from loipen.worker import __main__ as worker

    monkeypatch.setenv("LOIPEN_LOG_DIR", str(tmp_path / "logs"))
    get_settings.cache_clear()

    def docker_stop(argv, betrieb=None):
        worker._beenden(signal.SIGTERM, None)
    monkeypatch.setattr(worker, "befehl", docker_stop)
    try:
        with pytest.raises(SystemExit):
            worker.main([], mailer=mails.append, sender=False)
    finally:
        get_settings.cache_clear()
    assert mails == [] and not (tmp_path / "logs" / "worker.laeuft").exists()


@pytest.mark.req("B34", ak=4)
def test_b34_fehler_gesammelt_und_hoechstens_alle_6_stunden(tmp_path, mails):
    uhr = Uhr()
    b = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=uhr, umgebung={}).richte_ein()
    try:
        w = logging.getLogger("loipen.ablauf")
        assert b.pruefe() is False and mails == []  # ohne Fehler keine Mail
        w.error("Quelle a fehlgeschlagen")
        w.error("Quelle b fehlgeschlagen")
        assert b.pruefe() is True
        assert mails[0]["Subject"] == "Loipenblick: Fehler im Worker (2)"
        assert "Quelle a fehlgeschlagen" in text(mails[0]) and "Quelle b" in text(mails[0])
        uhr.t += timedelta(hours=1)
        w.error("Quelle c fehlgeschlagen")
        assert b.pruefe() is False and len(mails) == 1  # zurueckgehalten, aber gemerkt
        uhr.t += timedelta(hours=5)
        assert b.pruefe() is True
        fehlerteil = text(mails[1]).split("---------- Letzte")[0]
        assert "Quelle c" in fehlerteil and "Quelle a" not in fehlerteil
    finally:
        b.schliesse()


@pytest.mark.req("B34", ak=4)
def test_b34_fehler_mail_abschaltbar(tmp_path, mails):
    b = Betriebslog(settings(tmp_path, fehler_mail_stunden=0), mailer=mails.append, jetzt=Uhr(),
                    umgebung={}).richte_ein()
    try:
        logging.getLogger("loipen.ablauf").error("Fehler")
        assert b.pruefe() is False and mails == []
    finally:
        b.schliesse()


@pytest.mark.req("B34", ak=4)
def test_b34_absturz_mails_ueber_neustarts_begrenzt(tmp_path, mails):
    uhr = Uhr()
    for _ in range(3):  # Absturz-Schleife: Docker startet dreimal hintereinander neu
        b = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=uhr, umgebung={}).richte_ein()
        b.absturz(RuntimeError("immer wieder"))
        b.schliesse()
        uhr.t += timedelta(minutes=5)
    assert len(mails) == 1
    uhr.t += timedelta(minutes=30)
    b = Betriebslog(settings(tmp_path), mailer=mails.append, jetzt=uhr, umgebung={}).richte_ein()
    b.absturz(RuntimeError("immer wieder"))
    b.schliesse()
    assert len(mails) == 2


@pytest.mark.req("B34", ak=5)
def test_b34_mailfehler_stoppt_den_worker_nie(tmp_path, caplog):
    def smtp_kaputt(m):
        raise OSError(f"Login fehlgeschlagen mit {GEHEIM}")
    b = Betriebslog(settings(tmp_path), mailer=smtp_kaputt, jetzt=Uhr(), umgebung={}).richte_ein()
    try:
        b.absturz(RuntimeError("x"))  # wirft nicht
        logging.getLogger("loipen.ablauf").error("Fehler")
        assert b.pruefe() is False
        assert "nicht gesendet" in (tmp_path / "logs" / "worker.log").read_text(encoding="utf-8")
        assert GEHEIM not in (tmp_path / "logs" / "worker.log").read_text(encoding="utf-8")
    finally:
        b.schliesse()


@pytest.mark.req("B34", ak=5)
def test_b34_ohne_smtp_nur_datei(tmp_path):
    b = Betriebslog(settings(tmp_path, smtp_host=None), mailer=betriebslog.smtp_mailer(
        settings(tmp_path, smtp_host=None)), jetzt=Uhr(), umgebung={}).richte_ein()
    try:
        b.absturz(RuntimeError("ohne Mail"))
        assert "RuntimeError: ohne Mail" in (tmp_path / "logs" / "worker.log").read_text(encoding="utf-8")
    finally:
        b.schliesse()


@pytest.mark.req("B34", ak=5)
def test_b34_push_beim_absturz_wenn_eingerichtet(tmp_path, mails):
    pushes = []
    b = Betriebslog(settings(tmp_path), mailer=mails.append, sender=lambda t, x: pushes.append((t, x)),
                    jetzt=Uhr(), umgebung={}).richte_ein()
    try:
        b.absturz(RuntimeError("x"))
    finally:
        b.schliesse()
    assert pushes and pushes[0][0] == "Loipenblick: Worker abgestuerzt" and "logs" in pushes[0][1]


@pytest.mark.req("B34", ak=6)
def test_b34_geheimnisse_geschwaerzt(tmp_path, mails):
    umgebung = {"CDSAPI_KEY": "cds-schluessel-abcdef", "POSTGRES_PASSWORD": "loipen", "TZ": "Europe/Berlin"}
    s = settings(tmp_path, upload_passwort="FtpPasswort42", ntfy_url="https://ntfy.sh/geheimes-thema-xyz")
    b = Betriebslog(s, mailer=mails.append, jetzt=Uhr(), umgebung=umgebung).richte_ein()
    try:
        w = logging.getLogger("loipen.upload")
        w.error("Upload: Login mit FtpPasswort42 abgelehnt, %s", s.database_url)
        w.error("CDS: Schluessel cds-schluessel-abcdef ungueltig, Push an https://ntfy.sh/geheimes-thema-xyz")
        w.error("ftps://loipentest:Klartext77@ftp.example/www")
        w.info("loipen.worker bleibt lesbar")  # kurze Werte wie "loipen" werden nicht ersetzt
        b.absturz(RuntimeError(f"smtp {GEHEIM}"))
        b.pruefe()
    finally:
        b.schliesse()
    datei = (tmp_path / "logs" / "worker.log").read_text(encoding="utf-8")
    alles = datei + "".join(text(m) + "".join(anhang(m)) for m in mails)
    for geheim in (GEHEIM, "FtpPasswort42", "DbPasswort99", "cds-schluessel-abcdef", "geheimes-thema-xyz",
                   "Klartext77"):
        assert geheim not in alles
    assert "loipentest:***@" in datei and "loipen.worker bleibt lesbar" in datei


@pytest.mark.req("B34", ak=7)
def test_b34_fehler_im_ersten_lauf_beendet_den_worker_nicht(monkeypatch, tmp_path, mails):
    from loipen.config import get_settings
    from loipen.worker import __main__ as worker

    monkeypatch.setenv("LOIPEN_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOIPEN_IMPRESSUM_EMAIL", "stefan@example.org")
    get_settings.cache_clear()
    gestartet, jobs = [], []

    class Zeitplan:
        def __init__(self, **kw):
            pass

        def add_job(self, fn, *a, **kw):
            jobs.append(fn)

        def start(self):
            gestartet.append(True)
            for fn in jobs:  # jeder Job schlaegt fehl, der Zeitplan laeuft weiter
                fn()

    def lauf_kaputt(*a, **k):
        raise ConnectionError("Datenbank noch nicht bereit")
    monkeypatch.setattr(worker, "lauf", lauf_kaputt)
    monkeypatch.setattr(worker, "tick", lauf_kaputt)
    monkeypatch.setattr(worker, "schnee_tick", lauf_kaputt)
    monkeypatch.setattr(worker, "sicherung", lauf_kaputt)
    b = Betriebslog(get_settings(), mailer=mails.append, jetzt=Uhr(), umgebung={}).richte_ein()
    try:
        worker.starte(b, scheduler_klasse=Zeitplan)
    finally:
        b.schliesse()
        get_settings.cache_clear()
    assert gestartet and len(jobs) == 3
    assert len(mails) == 1 and "Datenbank noch nicht bereit" in text(mails[0])  # Fehler-Mail, kein Absturz
