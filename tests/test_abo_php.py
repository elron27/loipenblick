"""PHP-Teil des E-Mail-Abos auf dem Webspace (E-18): N2, N5, N6, N7, N8, N9.

Startet die Skripte mit dem eingebauten PHP-Server. mail() schreibt ueber sendmail_path in eine
Datei statt zu versenden. Ohne PHP (z. B. auf dem NAS) werden die Tests uebersprungen; der
GitHub-Runner hat PHP.
"""

import os
import re
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from loipen import mailabo
from loipen.generator.abo import PHP, php_array
from loipen.mailabo import AboKonfig

pytestmark = pytest.mark.skipif(shutil.which("php") is None, reason="PHP nicht installiert")

SCHLUESSEL = "test-schluessel-123"
ZIELE = {"l:1": "Ringseeloipe (Tegernsee)", "l:2": "Suttenrunde (Tegernsee)", "g:tegernsee": "Alle Loipen im Gebiet Tegernsee"}
JSON = {"Accept": "application/json"}


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Webspace:
    def __init__(self, wurzel: Path, port: int):
        self.wurzel, self.port = wurzel, port
        self.url = f"http://127.0.0.1:{port}"
        self.mails = wurzel.parent / "mails.txt"
        self.http = httpx.Client(base_url=self.url, timeout=10)

    def post(self, pfad, daten, json=True, **kw):
        return self.http.post(pfad, data=daten, headers=JSON if json else {}, **kw)

    def mail_liste(self) -> list[str]:
        if not self.mails.exists():
            return []
        return [m for m in self.mails.read_text(encoding="utf-8").split("----ENDE----\n") if m.strip()]

    def bestaetigungslink(self) -> str:
        return re.search(r"http://127\.0\.0\.1:\d+/abo/bestaetigen\.php\?t=\S+", self.mail_liste()[-1]).group(0)

    def export(self):
        return self.post("/abo/export.php", {"schluessel": SCHLUESSEL}, json=False).json()

    def anmelden(self, email="ski@example.org", ziele=("l:1",), ereignisse=("oeffnet",), **extra):
        daten = {"email": email, "einwilligung": "ja", "ziel[]": list(ziele), "ereignis[]": list(ereignisse), **extra}
        return self.post("/abo/anmelden.php", daten)

    def php(self, code: str) -> str:
        """PHP-Code mit geladenem Kern ausfuehren (fuer abgelaufene Links)."""
        return subprocess.run(["php", "-r", f"require '{self.wurzel}/abo/_kern.php'; {code}"],
                              capture_output=True, text=True, check=True).stdout


@contextmanager
def webspace_starten(tmp_path: Path, meldungen_an="kontakt@loipen.example"):
    wurzel = tmp_path / "site"
    shutil.copytree(PHP, wurzel / "abo")
    port = _freier_port()
    einst = {"seitenname": "Loipenblick", "seite_url": f"http://127.0.0.1:{port}", "absender": "abo@loipen.example",
             "schluessel_sha256": __import__("hashlib").sha256(SCHLUESSEL.encode()).hexdigest(),
             "datenschutz": "datenschutz.html", "meldungen_an": meldungen_an, "datenordner": ""}
    (wurzel / "abo" / "einstellungen.php").write_text(php_array(einst))
    (wurzel / "abo" / "ziele.php").write_text(php_array(ZIELE))
    sendmail = tmp_path / "sendmail.sh"
    sendmail.write_text(f"#!/bin/sh\ncat >> '{tmp_path}/mails.txt'\necho '----ENDE----' >> '{tmp_path}/mails.txt'\n")
    sendmail.chmod(0o755)
    proc = subprocess.Popen(["php", "-d", f"sendmail_path={sendmail}", "-S", f"127.0.0.1:{port}", "-t", str(wurzel)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        yield Webspace(wurzel, port)
    finally:
        proc.terminate()
        proc.wait(5)


@pytest.fixture
def ws(tmp_path):
    with webspace_starten(tmp_path) as w:
        yield w


@pytest.mark.req("N2", ak=1)
@pytest.mark.req("N7", ak=1)
def test_n2_abo_erst_nach_bestaetigung_aktiv(ws):
    r = ws.anmelden(ziele=("l:1", "g:tegernsee"), ereignisse=("oeffnet", "frisch_gespurt"))
    assert r.status_code == 200 and r.json()["titel"] == "Fast geschafft"
    mail = ws.mail_liste()[0]
    assert "To: ski@example.org" in mail
    assert "Ringseeloipe (Tegernsee)" in mail and "Alle Loipen im Gebiet Tegernsee" in mail
    assert "öffnet, frisch gespurt" in mail
    # N7: Vor der Bestaetigung liegt nichts auf dem Webspace, auch die Adresse nicht im Link
    assert ws.export() == {"eintraege": [], "anzahl": 0}
    link = ws.bestaetigungslink()
    assert "ski" not in link and "example" not in link.split("?")[1]
    for datei in (ws.wurzel / "abo" / "daten").glob("*.php"):
        assert "ski@example.org" not in datei.read_text()

    # Aufruf per GET (z. B. Virenscanner) bestaetigt noch nicht
    seite = ws.http.get(link)
    assert seite.status_code == 200 and "Abo bestätigen" in seite.text and "ski@example.org" in seite.text
    assert ws.export()["anzahl"] == 0

    token = link.split("t=", 1)[1]
    r = ws.post("/abo/bestaetigen.php", {"t": token})
    assert r.json()["titel"] == "Abo ist aktiv"
    e = ws.export()["eintraege"]
    assert len(e) == 1 and e[0]["typ"] == "bestaetigt" and e[0]["email"] == "ski@example.org"
    assert e[0]["ziele"] == ["l:1", "g:tegernsee"] and e[0]["ereignisse"] == ["oeffnet", "frisch_gespurt"]
    # Doppelklick ergibt dieselbe ID
    ws.post("/abo/bestaetigen.php", {"t": token})
    ids = {x["id"] for x in ws.export()["eintraege"]}
    assert len(ids) == 1


@pytest.mark.req("N2", ak=3)
def test_n2_link_laeuft_nach_48_stunden_ab(ws):
    alt = ws.php("echo abo_versiegeln(['e'=>'a@b.de','z'=>['l:1'],'a'=>['oeffnet'],'t'=>time()-49*3600]);")
    r = ws.post("/abo/bestaetigen.php", {"t": alt})
    assert r.status_code == 410
    r = ws.post("/abo/bestaetigen.php", {"t": alt[:-3] + "AAA"})
    assert r.status_code == 400  # veraendert
    assert ws.export()["anzahl"] == 0


@pytest.mark.req("N2", ak=2)
def test_n2_abmelden_nur_mit_token(ws):
    ws.anmelden()
    ws.post("/abo/bestaetigen.php", {"t": ws.bestaetigungslink().split("t=", 1)[1]})
    e = ws.export()["eintraege"][0]
    assert ws.post("/abo/abmelden.php", {"id": e["id"], "t": "0" * 32}).status_code == 400
    assert ws.post("/abo/abmelden.php", {"id": e["id"]}).status_code == 400
    # GET zeigt nur den Knopf
    seite = ws.http.get("/abo/abmelden.php", params={"id": e["id"], "t": e["abmelden"]})
    assert "Abmelden" in seite.text and ws.export()["anzahl"] == 1
    # One-Click aus dem Mailprogramm (RFC 8058): POST an die Link-Adresse
    r = ws.http.post(f"/abo/abmelden.php?id={e['id']}&t={e['abmelden']}", content="List-Unsubscribe=One-Click",
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200 and "Abgemeldet" in r.text
    assert ws.export()["eintraege"][-1] == {**ws.export()["eintraege"][-1], "typ": "abgemeldet", "id": e["id"]}


@pytest.mark.req("N5", ak=2)
def test_n5_eingaben_werden_geprueft(ws):
    assert ws.anmelden(email="kein-mail").status_code == 400
    assert ws.anmelden(email="a@b.de\r\nBcc: x@y.de").status_code == 400
    assert ws.anmelden(ziele=("l:999",)).status_code == 400  # unbekannte Loipe
    assert ws.anmelden(ereignisse=("explodiert",)).status_code == 400
    r = ws.post("/abo/anmelden.php", {"email": "a@b.de", "ziel[]": ["l:1"], "ereignis[]": ["oeffnet"]})
    assert r.status_code == 400 and "Einwilligung" in r.json()["titel"]
    assert ws.http.get("/abo/anmelden.php").status_code == 405
    assert ws.mail_liste() == []


@pytest.mark.req("N8", ak=1)
def test_n8_honigtopf_verschickt_nichts(ws):
    r = ws.anmelden(webseite="http://spam.example")
    assert r.status_code == 200 and r.json()["titel"] == "Fast geschafft"
    assert ws.mail_liste() == []


@pytest.mark.req("N8", ak=2)
def test_n8_begrenzung_je_adresse_und_anschluss(ws):
    for _ in range(3):
        ws.anmelden(email="opfer@example.org")
    r = ws.anmelden(email="opfer@example.org")
    assert r.status_code == 200  # verraet nicht, dass die Adresse begrenzt ist
    assert len(ws.mail_liste()) == 3
    ws.anmelden(email="noch-eine@example.org")
    r = ws.anmelden(email="dritte@example.org")
    assert r.status_code == 429  # 5 Anmeldungen je Anschluss und Stunde
    limits = (ws.wurzel / "abo" / "daten" / "limits.php").read_text()
    assert "opfer" not in limits and "127.0.0.1" not in limits


@pytest.mark.req("N8", ak=3)
def test_n8_daten_sind_von_aussen_nicht_lesbar(ws):
    ws.anmelden()
    ws.post("/abo/bestaetigen.php", {"t": ws.bestaetigungslink().split("t=", 1)[1]})
    for name in ("warteschlange", "geheimnis", "limits"):
        r = ws.http.get(f"/abo/daten/{name}.php")
        assert "ski@example.org" not in r.text and len(r.text) < 10
    for name in ("_kern", "einstellungen", "ziele"):
        assert ws.http.get(f"/abo/{name}.php").text == ""
    htaccess = (ws.wurzel / "abo" / ".htaccess").read_text()
    assert "Require all denied" in htaccess and "(anmelden|bestaetigen|abmelden|melden|export)" in htaccess
    assert "Require all denied" in (ws.wurzel / "abo" / "daten" / ".htaccess").read_text()


@pytest.mark.req("N6", ak=4)
def test_n6_export_nur_mit_schluessel_und_quittung(ws):
    assert ws.post("/abo/export.php", {"schluessel": "falsch"}, json=False).status_code == 403
    assert ws.http.get("/abo/export.php").status_code == 405
    ws.anmelden()
    ws.post("/abo/bestaetigen.php", {"t": ws.bestaetigungslink().split("t=", 1)[1]})
    assert ws.export()["anzahl"] == 1
    r = ws.post("/abo/export.php", {"schluessel": SCHLUESSEL, "quittung": "1"}, json=False).json()
    assert r == {"geloescht": 1, "rest": 0}
    assert ws.export()["anzahl"] == 0
    assert "ski@example.org" not in (ws.wurzel / "abo" / "daten" / "warteschlange.php").read_text()


@pytest.mark.req("N9", ak=1)
def test_n9_meldung_geht_an_den_betreiber(ws):
    r = ws.post("/abo/melden.php", {"ziel": "l:2", "art": "geschlossen", "text": "Gesperrt wegen Forstarbeiten",
                                    "email": "hinweis@example.org"})
    assert r.status_code == 200 and "Danke" in r.json()["titel"]
    mail = ws.mail_liste()[0]
    assert "To: kontakt@loipen.example" in mail and "Reply-To: hinweis@example.org" in mail
    assert "Suttenrunde (Tegernsee)" in mail and "in Wirklichkeit geschlossen" in mail and "Forstarbeiten" in mail
    e = ws.export()["eintraege"][0]
    assert e["typ"] == "meldung" and e["ziel"] == "l:2" and e["art"] == "geschlossen"
    # ohne Adresse geht es auch
    assert ws.post("/abo/melden.php", {"ziel": "l:1", "art": "offen"}).status_code == 200
    assert ws.post("/abo/melden.php", {"ziel": "g:tegernsee", "art": "offen"}).status_code == 400
    assert ws.post("/abo/melden.php", {"ziel": "l:1", "art": "quatsch"}).status_code == 400
    assert ws.post("/abo/melden.php", {"ziel": "l:1", "art": "offen", "webseite": "x"}).status_code == 200
    assert len(ws.export()["eintraege"]) == 2  # Honigtopf nicht gespeichert


@pytest.mark.req("N9", ak=3)
def test_n9_meldetext_wird_gekuerzt(ws):
    ws.post("/abo/melden.php", {"ziel": "l:1", "art": "sonstiges", "text": "x" * 2000 + "\x07"})
    assert len(ws.export()["eintraege"][0]["text"]) == 500


@pytest.mark.req("N6", ak=5)
def test_n6_durchgehend_vom_formular_bis_zur_mail(ws, session):
    """Anmelden und bestaetigen am PHP-Webspace, Abgleich und Versand vom NAS-Modul."""
    ws.anmelden(ziele=("l:1",), ereignisse=("oeffnet",))
    ws.post("/abo/bestaetigen.php", {"t": ws.bestaetigungslink().split("t=", 1)[1]})
    cfg = AboKonfig(seite_url=ws.url, schluessel=SCHLUESSEL, absender="abo@loipen.example")
    gesendet = []

    @contextmanager
    def scope():
        yield session
        session.flush()

    from loipen.ereignisse import Ereignis
    e = Ereignis("oeffnet", "Ringseeloipe", "tegernsee", "Tegernsee", "r", "offen", None, 1)
    abgleich, n = mailabo.lauf_abo(scope, cfg, [e], None, http=httpx.Client(timeout=10),
                                   versand=lambda ms: gesendet.extend(ms) or [None] * len(ms))
    assert abgleich.neu == 1 and n == 1
    assert ws.export()["anzahl"] == 0  # quittiert
    link = re.search(r"Abmelden: (\S+)", gesendet[0].get_content()).group(1)
    assert ws.http.post(link).status_code == 200  # Link aus der Mail funktioniert am Webspace
    abgleich, n = mailabo.lauf_abo(scope, cfg, [e], None, http=httpx.Client(timeout=10), versand=lambda ms: [None] * len(ms))
    assert abgleich.abgemeldet == 1 and n == 0
