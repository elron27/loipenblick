"""E-Mail-Abo und Fehlermeldungen auf dem NAS (E-18): N1, N2, N3, N6, N7, N9.

Der Webspace ist hier durch httpx.MockTransport ersetzt, SMTP durch eine Attrappe.
Der echte PHP-Teil wird in test_abo_php.py geprueft, auch zusammen mit diesem Modul.
"""

import json
from contextlib import contextmanager
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from loipen import mailabo
from loipen.ereignisse import Ereignis
from loipen.generator import abo as abo_dateien
from loipen.konfig import lade_und_abgleichen
from loipen.mailabo import AboKonfig
from loipen.models import Abonnent, Gebiet, Loipe, Quelle, Zustand

T0 = datetime(2026, 12, 20, 7, 0, tzinfo=timezone.utc)
CFG = AboKonfig(seite_url="https://loipen.example/", schluessel="s3cr3t", absender="abo@loipen.example",
                smtp_host="smtp.example")


def eintrag(id_="a" * 24, email="ski@example.org", ziele=("l:1",), ereignisse=("frisch_gespurt",)):
    return {"typ": "bestaetigt", "id": id_, "email": email, "ziele": list(ziele), "ereignisse": list(ereignisse),
            "angefragt": "2026-12-01T10:00:00+00:00", "bestaetigt": "2026-12-01T10:05:00+00:00",
            "abmelden": "b" * 32}


def ereignis(art="frisch_gespurt", loipe_id=1, gebiet="tegernsee", name="Ringseeloipe"):
    return Ereignis(art, name, gebiet, "Tegernsee", "tegernsee-region", "offen", 4.2, loipe_id)


class Webspace:
    """Attrappe von abo/export.php."""

    def __init__(self, eintraege, fehler=False):
        self.eintraege, self.fehler, self.quittungen = list(eintraege), fehler, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.fehler:
            return httpx.Response(500)
        form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
        if form.get("schluessel") != CFG.schluessel:
            return httpx.Response(403, json={"fehler": "Schluessel falsch"})
        if "quittung" in form:
            n = int(form["quittung"])
            self.quittungen.append(n)
            self.eintraege = self.eintraege[n:]
            return httpx.Response(200, json={"geloescht": n})
        return httpx.Response(200, json={"eintraege": self.eintraege, "anzahl": len(self.eintraege)})


def factory(session):
    @contextmanager
    def scope():
        yield session
        session.flush()
    return scope


@pytest.mark.req("N6", ak=1)
@pytest.mark.req("N2", ak=1)
def test_n6_bestaetigte_abos_kommen_vom_webspace(session):
    ws = Webspace([eintrag(), eintrag()])  # doppelt geklickt
    http = httpx.Client(transport=httpx.MockTransport(ws))
    abgleich, _ = mailabo.lauf_abo(factory(session), CFG, [], None, http=http, versand=lambda m: [])
    assert abgleich.neu == 1
    a = session.get(Abonnent, "a" * 24)
    assert a.email == "ski@example.org" and a.ziele == ["l:1"] and a.ereignisse == ["frisch_gespurt"]
    assert a.bestaetigt_at.isoformat() == "2026-12-01T10:05:00+00:00"
    assert ws.quittungen == [2] and ws.eintraege == []  # erst nach Uebernahme quittiert


@pytest.mark.req("N7", ak=2)
def test_n7_abmelden_loescht_die_adresse(session):
    mailabo.uebernimm(session, [eintrag()])
    erg = mailabo.uebernimm(session, [{"typ": "abgemeldet", "id": "a" * 24}])
    assert erg.abgemeldet == 1
    assert session.scalars(select(Abonnent)).all() == []


@pytest.mark.req("N6", ak=2)
def test_n6_ungueltige_eintraege_werden_ignoriert(session):
    kaputt = [eintrag(email="keine-adresse"), eintrag(ziele=("x:1",)), eintrag(ereignisse=("explodiert",)),
              {"typ": "unbekannt"}, {"typ": "abgemeldet", "id": "gibtsnicht"}]
    erg = mailabo.uebernimm(session, kaputt)
    assert erg.neu == 0 and session.scalars(select(Abonnent)).all() == []


@pytest.mark.req("N6", ak=3)
def test_n6_ohne_abgleich_keine_mails(session):
    mailabo.uebernimm(session, [eintrag()])
    gesendet = []
    http = httpx.Client(transport=httpx.MockTransport(Webspace([], fehler=True)))
    abgleich, n = mailabo.lauf_abo(factory(session), CFG, [ereignis()], None, http=http,
                                   versand=lambda m: gesendet.extend(m) or [None] * len(m))
    assert abgleich is None and n == 0 and gesendet == []


def test_abo_aus_ohne_konfiguration(session):
    assert mailabo.lauf_abo(factory(session), AboKonfig(), [ereignis()], None) == (None, 0)


@pytest.mark.req("N1", ak=1)
def test_n1_abo_greift_nur_fuer_eigene_loipe_und_ereignis(session):
    mailabo.uebernimm(session, [eintrag(ziele=("l:1",), ereignisse=("frisch_gespurt",))])
    a = session.get(Abonnent, "a" * 24)
    assert mailabo.passt(a, ereignis("frisch_gespurt", 1))
    assert not mailabo.passt(a, ereignis("oeffnet", 1))
    assert not mailabo.passt(a, ereignis("frisch_gespurt", 2))


@pytest.mark.req("N1", ak=2)
def test_n1_abo_auf_ein_gebiet(session):
    mailabo.uebernimm(session, [eintrag(ziele=("g:tegernsee",), ereignisse=("oeffnet", "schliesst"))])
    a = session.get(Abonnent, "a" * 24)
    assert mailabo.passt(a, ereignis("oeffnet", 77, "tegernsee"))
    assert not mailabo.passt(a, ereignis("oeffnet", 77, "bayrischzell"))


@pytest.mark.req("N3", ak=1)
def test_n3_eine_mail_je_abonnent_und_lauf(session):
    mailabo.uebernimm(session, [eintrag(ziele=("l:1", "l:2"), ereignisse=("oeffnet", "frisch_gespurt")),
                                eintrag(id_="c" * 24, email="zwei@example.org", ziele=("l:9",))])
    abonnenten = session.scalars(select(Abonnent).order_by(Abonnent.id)).all()
    mails = mailabo.mails_fuer(CFG, abonnenten,
                               [ereignis("oeffnet", 1, name="Ringseeloipe"), ereignis("frisch_gespurt", 2, name="Suttenrunde")])
    assert len(mails) == 1
    a, m = mails[0]
    assert m["To"] == "ski@example.org"
    assert m["Subject"] == "Loipenblick: 2 Neuigkeiten zu deinen Loipen"
    text = m.get_content()
    assert "Ringseeloipe" in text and "Suttenrunde" in text
    assert "https://loipen.example/#/loipe/1" in text


@pytest.mark.req("N2", ak=2)
def test_n2_mail_hat_abmeldelink_mit_token(session):
    mailabo.uebernimm(session, [eintrag()])
    a = session.get(Abonnent, "a" * 24)
    m = mailabo.baue_mail(CFG, a, [ereignis()])
    link = f"https://loipen.example/abo/abmelden.php?id={'a' * 24}&t={'b' * 32}"
    assert link in m.get_content()
    assert m["List-Unsubscribe"] == f"<{link}>"
    assert m["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "ski@example.org" not in link  # Abmelden nie nur mit der Adresse


@pytest.mark.req("N3", ak=2)
def test_n3_versand_ueber_eine_smtp_verbindung(monkeypatch, session):
    verbindungen = []

    class FakeSMTP:
        def __init__(self, host, port, timeout, context):
            self.gesendet, self.login_daten = [], None
            verbindungen.append(self)
            assert (host, port) == ("smtp.example", 465)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, u, p):
            self.login_daten = (u, p)

        def send_message(self, m):
            if m["To"] == "kaputt@example.org":
                raise mailabo.smtplib.SMTPRecipientsRefused({m["To"]: (550, b"unbekannt")})
            self.gesendet.append(m["To"])

    monkeypatch.setattr(mailabo.smtplib, "SMTP_SSL", FakeSMTP)
    cfg = AboKonfig(**{**CFG.__dict__, "smtp_benutzer": "abo", "smtp_passwort": "pw"})
    mailabo.uebernimm(session, [eintrag(), eintrag(id_="c" * 24, email="kaputt@example.org")])
    n = mailabo.versende(session, cfg, [ereignis()], mailabo.smtp_versand(cfg), T0)
    assert n == 1 and len(verbindungen) == 1
    assert verbindungen[0].gesendet == ["ski@example.org"] and verbindungen[0].login_daten == ("abo", "pw")
    assert session.get(Abonnent, "a" * 24).letzte_mail_at == T0
    assert session.get(Abonnent, "c" * 24).letzte_mail_at is None


@pytest.mark.req("N9", ak=2)
def test_n9_meldung_geht_als_push_und_aendert_keinen_status(session):
    lade_und_abgleichen(session)
    quelle = session.scalar(select(Quelle).where(Quelle.key == "bayrischzell"))
    gebiet = session.scalar(select(Gebiet).where(Gebiet.slug == "bayrischzell"))
    loipe = Loipe(quelle=quelle, gebiet=gebiet, source_key="x", name="Testloipe", source_url="https://x")
    session.add(loipe)
    session.flush()
    session.add(Zustand(loipe=loipe, status="offen", abgerufen_at=T0, zuletzt_bestaetigt_at=T0))
    session.flush()
    meldung = {"typ": "meldung", "ziel": f"l:{loipe.id}", "name": "Testloipe (Bayrischzell)", "art": "geschlossen",
               "text": "Seit gestern gesperrt, Forstarbeiten", "kontakt": "", "zeit": "2026-12-20T08:00:00+00:00"}
    pushes = []
    http = httpx.Client(transport=httpx.MockTransport(Webspace([meldung])))
    abgleich, _ = mailabo.lauf_abo(factory(session), CFG, [], lambda t, x: pushes.append((t, x)), http=http,
                                   versand=lambda m: [])
    assert len(abgleich.meldungen) == 1
    assert pushes[0][0] == "Loipenblick: Meldung zu Testloipe (Bayrischzell)"
    assert "in Wirklichkeit geschlossen" in pushes[0][1] and "Forstarbeiten" in pushes[0][1]
    assert [z.status for z in session.scalars(select(Zustand).where(Zustand.loipe_id == loipe.id))] == ["offen"]


@pytest.mark.req("N5", ak=3)
def test_n5_ohne_konfiguration_kein_abo_ordner(session):
    assert abo_dateien.dateien(session, AboKonfig()) == {}


@pytest.mark.req("N7", ak=3)
def test_n7_einstellungen_ohne_geheimnisse(session):
    lade_und_abgleichen(session)
    d = abo_dateien.dateien(session, CFG, meldungen_an="kontakt@loipen.example")
    einst = d["abo/einstellungen.php"].decode()
    assert "s3cr3t" not in einst
    import hashlib
    assert hashlib.sha256(b"s3cr3t").hexdigest() in einst
    assert {"abo/anmelden.php", "abo/bestaetigen.php", "abo/abmelden.php", "abo/melden.php", "abo/export.php",
            "abo/.htaccess", "abo/daten/.htaccess", "abo/ziele.php"} <= set(d)
    assert "'g:bayrischzell' => 'Alle Loipen im Gebiet" in d["abo/ziele.php"].decode()


def test_php_str_escaping():
    assert abo_dateien.php_str("O'Brien \\ Loipe") == "'O\\'Brien \\\\ Loipe'"
