"""Quellen-Waechter (B26): Fehler, 0 Loipen und Einbruch erkennen, kurze Stoerungen abwarten,
erinnern, Entwarnung, neuer Normalwert, Versand per Push und Mail."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from loipen import waechter
from loipen.ablauf import rufe_quelle_ab
from loipen.konfig import lade_und_abgleichen
from loipen.models import Abrufprotokoll, Quelle
from loipen.waechter import Meldung, baue_mail, melde, pruefe
from loipen.worker import __main__ as worker
from tests.helpers import FixtureFetcher

T0 = datetime(2026, 12, 5, 7, 0, tzinfo=timezone.utc)
H = timedelta(hours=5)  # Abstand zwischen zwei Abrufen


@pytest.fixture
def quelle(session):
    q = Quelle(key="testquelle", adapter="ats", name="Testquelle", base_url="https://test.example", config={})
    session.add(q)
    session.flush()
    return q


def laeufe(session, q, anzahlen, start=T0, status="ok", fehler=None):
    """Mehrere Abrufe hintereinander; gibt die Meldungen zurueck (None = keine)."""
    meldungen = []
    for i, n in enumerate(anzahlen):
        st = status if n is not None else "fehler"
        q.last_error = fehler if st == "fehler" else ("Quelle lieferte 0 Loipen" if n == 0 else None)
        meldungen.append(pruefe(session, q, n or 0, st, q.last_error, 1.0, start + i * H))
    return meldungen


def normal(session, q, n=20, mal=5, start=T0 - 30 * H):
    assert laeufe(session, q, [n] * mal, start=start) == [None] * mal


@pytest.mark.req("B26", ak=1)
def test_b26_null_loipen_nach_zwei_abrufen_alarm(session, quelle):
    normal(session, quelle)
    erste, zweite = laeufe(session, quelle, [0, 0])
    assert erste is None  # einmal 0 kann ein Aussetzer sein
    assert zweite.art == "alarm" and zweite.befund == "leer" and zweite.ueblich == 20
    assert zweite.seit == T0 and quelle.waechter_alarm == "leer"
    assert "liefert 0 Loipen" in zweite.titel and "Testquelle" in zweite.titel


@pytest.mark.req("B26", ak=1)
def test_b26_einbruch_unter_haelfte(session, quelle):
    normal(session, quelle, n=40)
    assert laeufe(session, quelle, [25, 22]) == [None, None]  # weniger, aber nicht unter der Haelfte
    m = laeufe(session, quelle, [12, 11], start=T0 + 2 * H)[1]
    assert m.art == "alarm" and m.befund == "einbruch"
    assert "nur 11 statt üblich 40" in m.text


@pytest.mark.req("B26", ak=1)
def test_b26_kleine_quelle_kein_einbruch(session, quelle):
    """Eine Quelle mit 3 Loipen schwankt schnell um die Haelfte: dort zaehlt nur 0."""
    normal(session, quelle, n=3)
    assert laeufe(session, quelle, [1, 1, 1]) == [None, None, None]


@pytest.mark.req("B26", ak=1)
def test_b26_fehler_wird_gemeldet_mit_text(session, quelle):
    normal(session, quelle)
    m = laeufe(session, quelle, [None, None], fehler="HttpFehler: 404")[1]
    assert m.befund == "fehler" and "HttpFehler: 404" in m.text


@pytest.mark.req("B26", ak=2)
def test_b26_kurze_stoerung_ohne_alarm(session, quelle):
    normal(session, quelle)
    assert laeufe(session, quelle, [None, 20, 0, 20]) == [None] * 4
    assert quelle.waechter_alarm is None


@pytest.mark.req("B26", ak=3)
def test_b26_erinnern_hoechstens_einmal_am_tag_dann_entwarnung(session, quelle):
    normal(session, quelle)
    ms = laeufe(session, quelle, [0] * 7)  # 7 Abrufe im Abstand von 5 h = 30 h
    arten = [m.art if m else None for m in ms]
    assert arten == [None, "alarm", None, None, None, None, "erinnerung"]
    ende = laeufe(session, quelle, [19], start=T0 + 7 * H)[0]
    assert ende.art == "entwarnung" and "läuft wieder" in ende.titel and "Wieder 19 Loipen" in ende.text
    assert quelle.waechter_alarm is None and quelle.waechter_seit is None


@pytest.mark.req("B26", ak=3)
def test_b26_wechsel_der_art_wird_gemeldet(session, quelle):
    normal(session, quelle)
    laeufe(session, quelle, [0, 0])
    m = laeufe(session, quelle, [None], start=T0 + 2 * H, fehler="ValueError: kaputt")[0]
    assert m.art == "wechsel" and m.befund == "fehler" and quelle.waechter_seit == T0


@pytest.mark.req("B26", ak=3)
def test_b26_grundwert_bleibt_trotz_langer_stoerung(session, quelle):
    """Auffaellige Abrufe zaehlen nicht zum ueblichen Wert, sonst wuerde der Alarm still verschwinden."""
    normal(session, quelle, n=40)
    laeufe(session, quelle, [10] * 12)
    assert waechter.grundwert(session, quelle) == 40
    assert quelle.waechter_alarm == "einbruch"


@pytest.mark.req("B26", ak=4)
def test_b26_neuer_normalwert_nach_einer_woche(session, quelle):
    normal(session, quelle, n=40)
    tage = timedelta(days=1)
    laeufe(session, quelle, [15, 15])
    for tag in range(1, 7):
        laeufe(session, quelle, [15], start=T0 + tag * tage)
    assert quelle.waechter_alarm == "einbruch"
    m = laeufe(session, quelle, [15], start=T0 + 7 * tage)[0]
    assert m.art == "neu_normal" and "gilt ab jetzt als normal" in m.text
    assert quelle.waechter_alarm is None and waechter.grundwert(session, quelle) == 15
    assert laeufe(session, quelle, [15], start=T0 + 8 * tage) == [None]


@pytest.mark.req("B26", ak=4)
def test_b26_je_quelle_abschaltbar_und_schwellen(session, quelle):
    quelle.config = {"waechter": {"aus": True}}
    normal(session, quelle)
    assert laeufe(session, quelle, [0, 0, 0]) == [None] * 3
    quelle.config = {"waechter": {"bestaetigen": 1, "einbruch_anteil": 0.8}}
    m = laeufe(session, quelle, [15], start=T0 + 3 * H)[0]
    assert m.art == "alarm" and m.befund == "einbruch"


@pytest.mark.req("B26", ak=4)
def test_b26_schwellen_aus_sources_yaml(session):
    lade_und_abgleichen(session)
    q = session.scalar(select(Quelle).where(Quelle.key == "bayrischzell"))
    assert q.config["waechter"]["bestaetigen"] == 2 and q.config["waechter"]["einbruch_anteil"] == 0.5


@pytest.mark.req("B26", ak=5)
def test_b26_jeder_abruf_im_protokoll(session):
    """Echte Adapter mit Fixture: jeder Abruf landet im Protokoll, kaputte Seite zweimal -> Alarm."""
    lade_und_abgleichen(session)
    q = session.scalar(select(Quelle).where(Quelle.key == "bayrischzell"))

    class Leer:
        def get(self, url):
            return "<html><body>Seite umgebaut</body></html>"

    for i in range(3):
        lauf = rufe_quelle_ab(session, q, FixtureFetcher("bayrischzell", q.base_url), T0 + i * H)
        assert lauf.gefunden > 0 and lauf.waechter is None
    ueblich = lauf.gefunden
    l1 = rufe_quelle_ab(session, q, Leer(), T0 + 3 * H)
    l2 = rufe_quelle_ab(session, q, Leer(), T0 + 4 * H)
    assert l1.waechter is None and l2.waechter.art == "alarm" and l2.waechter.ueblich == ueblich
    zeilen = session.scalars(select(Abrufprotokoll).where(Abrufprotokoll.quelle_id == q.id)
                             .order_by(Abrufprotokoll.zeit)).all()
    assert [z.anzahl for z in zeilen] == [ueblich] * 3 + [0, 0]
    assert [z.befund for z in zeilen] == [None] * 3 + ["leer", "leer"]
    assert all(z.dauer_s is not None for z in zeilen)
    assert session.scalar(select(func.count()).select_from(Abrufprotokoll)) == 5


def meldung(art="alarm", befund="leer"):
    return Meldung(art, "bayrischzell", "Bayrischzell", "https://www.bayrischzell.de", befund, 0, 13, T0,
                   "Quelle lieferte 0 Loipen")


@pytest.mark.req("B26", ak=5)
def test_b26_mail_nennt_quelle_und_was_zu_tun_ist(session):
    m = baue_mail([meldung(), meldung("entwarnung", None)], "stefan@example.org", "abo@example.org")
    text = m.get_content()
    assert m["To"] == "stefan@example.org" and "abo@example.org" in m["From"]
    assert m["Subject"] == "Quellen-Wächter: 1 Quellen gestört"
    assert "https://www.bayrischzell.de" in text and "Fixture-Test" in text and "Schnappschuss" in text
    nur_gut = baue_mail([meldung("entwarnung", None)], "s@example.org", "a@example.org")
    assert "läuft wieder" in nur_gut["Subject"] and "Was tun" not in nur_gut.get_content()


@pytest.mark.req("B26", ak=5)
def test_b26_push_und_mail_unabhaengig(session):
    pushes, mails = [], []

    def push_kaputt(titel, text):
        raise RuntimeError("ntfy weg")

    erg = melde([meldung(), meldung()], push_kaputt, mails.append, "s@example.org", "a@example.org")
    assert erg == {"push": 0, "mail": 1} and len(mails) == 1  # eine Mail fuer alle Meldungen
    erg = melde([meldung()], lambda t, x: pushes.append(t), None, None, None)
    assert erg == {"push": 1, "mail": 0} and pushes == [meldung().titel]
    assert melde([], pushes.append, mails.append, "s", "a") == {"push": 0, "mail": 0}


@pytest.mark.req("B26", ak=5)
def test_b26_worker_schickt_an_impressum_adresse_ohne_eigene(monkeypatch):
    gesendet = []
    settings = SimpleNamespace(waechter_mail=None, impressum_email="stefan@example.org", abo_absender=None,
                               smtp_host="smtp.example", oeffentliche_url=None, abo_schluessel=None,
                               seitenname="Loipenblick", smtp_port=465, smtp_benutzer=None,
                               smtp_passwort=None, smtp_starttls=False)
    monkeypatch.setattr(worker, "smtp_versand", lambda cfg: (lambda mails: gesendet.extend(mails) or [None]))
    erg = worker.melde_waechter(settings, None, [meldung()])
    assert erg["mail"] == 1 and gesendet[0]["To"] == "stefan@example.org"
