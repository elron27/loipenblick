"""Besucherzaehler ohne Cookies (B13, E-42): PHP-Teil auf dem Webspace, Erzeugung durch das NAS,
Upload-Freigabe und Datenschutzerklaerung. Die Meldung aus der App im echten Browser steht in
test_zaehler_ui.py. Ohne PHP werden die PHP-Tests uebersprungen; der GitHub-Runner hat PHP.
"""

import json
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from loipen import generator
from loipen.config import Settings
from loipen.generator import zaehler as zaehler_vorlage
from loipen.generator.zaehler import PHP, php_json
from loipen.upload import freigegeben
from loipen.worker import __main__ as worker
from tests.helpers import lade_alle_fixtures

ohne_php = pytest.mark.skipif(shutil.which("php") is None, reason="PHP nicht installiert")
JETZT = datetime(2026, 12, 10, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
PASSWORT = "langes-test-passwort"
ZIELE = {"gebiete": {"tegernsee": "Tegernsee", "kreuth": "Kreuth"},
         "loipen": {"1": ["Ringseeloipe", "tegernsee"], "2": ["Suttenrunde", "kreuth"]}}
CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
# 10.12.2026 und 11.12.2026, jeweils mittags
TAG1, TAG2 = 1796900400, 1796986800


def zaehler_ordner(wurzel: Path, oeffentlich=True) -> Path:
    ordner = wurzel / "zaehler"
    shutil.copytree(PHP, ordner)
    (ordner / "einstellungen.php").write_text(
        php_json(zaehler_vorlage.einstellungen(PASSWORT, "https://loipen.example", oeffentlich)))
    (ordner / "ziele.php").write_text(php_json(ZIELE))
    return ordner


def php(ordner: Path, code: str) -> str:
    return subprocess.run(["php", "-r", f"require '{ordner}/_kern.php'; {code}"],
                          capture_output=True, text=True, check=True).stdout


def zaehle(ordner, seite="heute", gebiet="", loipe="", ip="203.0.113.7", ua=CHROME, zeit=TAG1) -> bool:
    return php(ordner, f"echo z_zaehle('{seite}', '{gebiet}', '{loipe}', '{ip}', '{ua}', {zeit}) ? 'ja' : 'nein';") == "ja"


def monat(ordner, m="2026-12") -> dict:
    return json.loads(php(ordner, f"echo json_encode(z_monat('{m}'), JSON_FORCE_OBJECT);") or "{}")


@contextmanager
def webspace(tmp_path: Path, oeffentlich=True):
    ordner = zaehler_ordner(tmp_path / "site", oeffentlich)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(tmp_path / "site")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        yield ordner, httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10, headers={"User-Agent": CHROME})
    finally:
        proc.terminate()
        proc.wait(5)


# ---------- PHP auf dem Webspace ----------

@ohne_php
@pytest.mark.req("B13", ak=[1, 2])
def test_b13_zaehlt_aufrufe_und_tagesbesucher_ohne_ip(tmp_path):
    o = zaehler_ordner(tmp_path)
    assert zaehle(o) and zaehle(o, "loipe", loipe="1") and zaehle(o, "gebiet", gebiet="kreuth")
    assert zaehle(o, ip="198.51.100.4")
    assert zaehle(o, ua=CHROME.replace("131", "130"))  # anderer Browser am selben Anschluss
    t = monat(o)["2026-12-10"]
    assert t["aufrufe"] == 5 and t["besucher"] == 3
    assert t["seiten"] == {"heute": 3, "loipe": 1, "gebiet": 1}
    assert t["gebiete"] == {"tegernsee": 1, "kreuth": 1}  # die Loipenseite zaehlt fuer ihr Gebiet
    assert t["loipen"] == {"1": 1}
    # Keine IP-Adresse und keine Browserkennung in irgendeiner Datei, alle Dateien gesperrt
    for datei in (o / "daten").iterdir():
        if datei.is_file() and datei.name != ".sperre":
            roh = datei.read_text()
            assert "203.0.113" not in roh and "198.51.100" not in roh and "Chrome" not in roh, datei.name
            assert roh.startswith("<?php exit; ?>"), datei.name


@ohne_php
@pytest.mark.req("B13", ak=2)
def test_b13_pruefwerte_verfallen_am_naechsten_tag(tmp_path):
    o = zaehler_ordner(tmp_path)
    zaehle(o)
    heute1 = json.loads((o / "daten" / "heute.php").read_text().split("\n", 1)[1])
    assert heute1["tag"] == "2026-12-10" and len(heute1["besucher"]) == 1
    zaehle(o, zeit=TAG2)
    heute2 = json.loads((o / "daten" / "heute.php").read_text().split("\n", 1)[1])
    assert heute2["tag"] == "2026-12-11" and heute2["salz"] != heute1["salz"]
    assert set(heute2["besucher"]).isdisjoint(heute1["besucher"])  # Tage lassen sich nicht verbinden
    m = monat(o)
    assert m["2026-12-10"]["besucher"] == 1 and m["2026-12-11"]["besucher"] == 1


@ohne_php
@pytest.mark.req("B13", ak=4)
def test_b13_bots_und_unbekannte_werte_zaehlen_nicht(tmp_path):
    o = zaehler_ordner(tmp_path)
    for ua in ("", "Googlebot/2.1 (+http://www.google.com/bot.html)", "curl/8.5.0", "python-httpx/0.27",
               "Mozilla/5.0 HeadlessChrome/131.0", "UptimeRobot/2.0", "Mozilla/5.0 (compatible; AhrefsBot/7.0)"):
        assert not zaehle(o, ua=ua), ua
    assert not zaehle(o, seite="admin")
    assert zaehle(o, "gebiet", gebiet="gibtsnicht") and zaehle(o, "loipe", loipe="999")
    t = monat(o)["2026-12-10"]
    assert t["aufrufe"] == 2 and t["gebiete"] == {} and t["loipen"] == {}


@ohne_php
@pytest.mark.req("B13", ak=[2, 4])
def test_b13_meldung_per_http_ohne_cookie(tmp_path):
    with webspace(tmp_path) as (o, http):
        r = http.post("/zaehler/z.php", data={"s": "karte"}, headers={"Sec-Fetch-Site": "same-origin"})
        assert r.status_code == 204 and "set-cookie" not in r.headers and r.content == b""
        # fremde Seiten koennen nicht mitzaehlen, GET zaehlt nicht
        assert http.post("/zaehler/z.php", data={"s": "karte"}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 204
        assert http.get("/zaehler/z.php?s=karte").status_code == 204
        tage = monat(o, datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m"))
        assert sum(t["aufrufe"] for t in tage.values()) == 1
        # Datendateien liefern nichts aus, auch ohne .htaccess (eingebauter PHP-Server)
        for datei in (o / "daten").glob("*.php"):
            assert http.get(f"/zaehler/daten/{datei.name}").text == ""


@ohne_php
@pytest.mark.req("B13", ak=[1, 5])
def test_b13_auswertung_nur_mit_passwort(tmp_path):
    with webspace(tmp_path) as (o, http):
        zaehle(o, "loipe", loipe="2", zeit=int(time.time()))
        zaehle(o, "gebiet", gebiet="tegernsee", ip="198.51.100.4", zeit=int(time.time()))
        r = http.get("/zaehler/auswertung.php")
        assert r.status_code == 200 and 'id="anmeldung"' in r.text and 'id="summen"' not in r.text
        assert "set-cookie" not in r.headers and "noindex" in r.headers["x-robots-tag"]
        assert "Testseite" not in r.text

        falsch = http.post("/zaehler/auswertung.php", data={"passwort": "falsch"})
        assert "Das Passwort stimmt nicht" in falsch.text and 'id="summen"' not in falsch.text

        r = http.post("/zaehler/auswertung.php", data={"passwort": PASSWORT})
        assert 'id="summen"' in r.text and "set-cookie" not in r.headers
        assert "Kreuth" in r.text and "Tegernsee" in r.text and "Suttenrunde (Kreuth)" in r.text
        assert r.text.count("<b>2</b>") >= 2  # 2 Besucher, 2 Aufrufe
        assert PASSWORT not in r.text
        sitzung = r.text.split('name="sitzung" value="')[1].split('"')[0]
        # Monatswahl mit der Sitzung aus dem Formular, ohne Passwort
        r2 = http.post("/zaehler/auswertung.php", data={"sitzung": sitzung, "monat": "2020-01"})
        assert 'id="summen"' in r2.text
        r3 = http.post("/zaehler/auswertung.php", data={"sitzung": "1." + "0" * 64})
        assert "abgelaufen" in r3.text and 'id="summen"' not in r3.text


@ohne_php
@pytest.mark.req("B13", ak=5)
def test_b13_falsche_passwoerter_werden_begrenzt(tmp_path):
    with webspace(tmp_path) as (o, http):
        for _ in range(5):
            http.post("/zaehler/auswertung.php", data={"passwort": "raten"})
        r = http.post("/zaehler/auswertung.php", data={"passwort": PASSWORT})
        assert "Zu viele falsche Versuche" in r.text and 'id="summen"' not in r.text
        assert PASSWORT not in (o / "daten" / "login.php").read_text()


@ohne_php
@pytest.mark.req("B13", ak=6)
def test_b13_testseite_ist_gekennzeichnet(tmp_path):
    with webspace(tmp_path, oeffentlich=False) as (_, http):
        assert "Testseite" in http.get("/zaehler/auswertung.php").text


# ---------- Erzeugung auf dem NAS ----------

@pytest.mark.req("B13", ak=[6, 7])
def test_b13_ohne_passwort_kein_zaehler(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    for pw in (None, "", "zu-kurz"):
        assert zaehler_vorlage.dateien(session, pw) == {}
    generator.erzeuge(session, tmp_path, JETZT)
    assert json.loads((tmp_path / "daten.json").read_text())["zaehler"] is False
    assert not (tmp_path / "zaehler").exists()
    assert "Besucherzähler" not in (tmp_path / "datenschutz.html").read_text(encoding="utf-8")


@pytest.mark.req("B13", ak=[5, 6, 7])
def test_b13_mit_passwort_zaehler_ordner_und_datenschutz(session, tmp_path):
    lade_alle_fixtures(session, JETZT, mit_wetter=False)
    settings = Settings(zaehler_passwort=PASSWORT, oeffentliche_url="https://loipen.example", oeffentlich=True,
                        _env_file=None)
    dateien = worker.zaehler_dateien(session, settings)
    generator.erzeuge(session, tmp_path, JETZT, zaehler_dateien=dateien)
    assert json.loads((tmp_path / "daten.json").read_text())["zaehler"] is True
    for name in ("_kern.php", "z.php", "auswertung.php", "auswertung.js", "einstellungen.php", "ziele.php"):
        assert (tmp_path / "zaehler" / name).exists(), name
    einst = (tmp_path / "zaehler" / "einstellungen.php").read_text()
    assert PASSWORT not in einst and "passwort_pbkdf2" in einst
    # gleiche Einstellungen bei jedem Lauf, damit der Upload nicht jedes Mal neu schreibt
    assert worker.zaehler_dateien(session, settings)["zaehler/einstellungen.php"] == dateien["zaehler/einstellungen.php"]
    ziele = (tmp_path / "zaehler" / "ziele.php").read_text(encoding="utf-8")
    assert '\\"kreuth\\"' in ziele or '"kreuth"' in ziele
    text = (tmp_path / "datenschutz.html").read_text(encoding="utf-8")
    for teil in ("Besucherzähler", "keine Cookies", "jeden Tag neu", "nicht gespeichert", "Art. 6 Abs. 1 lit. f DSGVO",
                 "von der du kommst", "ohne Suchbegriffe", "Art des Geräts"):
        assert teil in text, teil
    assert "RewriteRule ^zaehler/daten/ - [F]" in (tmp_path / ".htaccess").read_text()
    # wird der Zaehler abgeschaltet, verschwindet der Ordner
    generator.erzeuge(session, tmp_path, JETZT)
    assert not (tmp_path / "zaehler").exists()


@ohne_php
@pytest.mark.req("B13", ak=5)
def test_b13_passwort_aus_python_passt_zu_php(tmp_path):
    o = zaehler_ordner(tmp_path)
    assert php(o, f"echo z_passwort_ok('{PASSWORT}') ? 'ja' : 'nein';") == "ja"
    assert php(o, "echo z_passwort_ok('falsch') ? 'ja' : 'nein';") == "nein"


@pytest.mark.req("B13", ak=5)
def test_b13_upload_nimmt_skripte_aber_nie_daten():
    for rel in ("zaehler/z.php", "zaehler/_kern.php", "zaehler/auswertung.php", "zaehler/auswertung.js",
                "zaehler/einstellungen.php", "zaehler/ziele.php"):
        assert freigegeben(rel), rel
    for rel in ("zaehler/daten/heute.php", "zaehler/daten/monat-2026-12.php", "zaehler/daten/.sperre",
                "zaehler/.tmp-x", "andere/x.php"):
        assert not freigegeben(rel), rel


@ohne_php
@pytest.mark.req("B13", ak=8)
def test_b13_herkunft_und_geraet_beim_einstieg(tmp_path):
    o = zaehler_ordner(tmp_path)

    def einstieg(herkunft, geraet, ip):
        return php(o, f"echo z_zaehle('heute', '', '', '{ip}', '{CHROME}', {TAG1}, "
                      f"['herkunft' => '{herkunft}', 'geraet' => '{geraet}']) ? 'ja' : 'nein';") == "ja"

    assert einstieg("www.google.de", "handy", "10.0.0.1") and einstieg("google.at", "pc", "10.0.0.2")
    assert einstieg("www.bergfex.at", "tablet", "10.0.0.3") and einstieg("", "app", "10.0.0.4")
    assert einstieg("forum.example.org", "toaster", "10.0.0.5") and einstieg("app", "handy", "10.0.0.6")
    assert einstieg("<script>", "pc", "10.0.0.7")
    assert zaehle(o, "karte")  # kein Einstieg: weder Herkunft noch Geraet
    t = monat(o)["2026-12-10"]
    assert t["einstiege"] == 7 and t["aufrufe"] == 8
    assert t["herkunft"] == {"Google": 2, "bergfex": 1, "direkt": 1, "forum.example.org": 1,
                             "App oder Mailprogramm": 1, "andere": 1}
    assert t["geraete"] == {"handy": 2, "pc": 2, "tablet": 1, "app": 1}  # "toaster" verworfen


@ohne_php
@pytest.mark.req("B13", ak=8)
def test_b13_herkunft_per_http_und_in_der_auswertung(tmp_path):
    with webspace(tmp_path) as (o, http):
        kopf = {"Sec-Fetch-Site": "same-origin"}
        http.post("/zaehler/z.php", data={"s": "heute", "e": "1", "r": "www.google.com", "d": "handy"}, headers=kopf)
        http.post("/zaehler/z.php", data={"s": "karte", "r": "spam.example"}, headers=kopf)  # ohne e: keine Herkunft
        r = http.post("/zaehler/auswertung.php", data={"passwort": PASSWORT})
        assert "Woher die Besucher kommen" in r.text and "Google" in r.text and "Handy" in r.text
        assert "spam.example" not in r.text
