"""Benachrichtigung einzelner Loipen: N10 Push ohne Konto, N11 kein Doppelversand, N12 Abo fuer die Merkliste.
Die Oberflaeche (Merken, Meine Loipen, Push-Block) im Browser steht in test_benachrichtigung_ui.py."""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

from loipen import generator
from loipen.benachrichtigung import (
    PushKonfig, entprelle, gueltiges_praefix, nachrichten, thema_gebiet, thema_loipe, veroeffentliche,
)
from loipen.config import Settings
from loipen.ereignisse import Ereignis
from loipen.models import Gebiet, Loipe, Meldeprotokoll, PushTag, Quelle, Region
from loipen.worker import __main__ as worker

T0 = datetime(2026, 12, 10, 7, 0, tzinfo=timezone.utc)
CFG = PushKonfig(praefix="lb-test", seite_url="https://loipen.example", max_tag=150)


@pytest.fixture
def loipen(session):
    r = Region(slug="tegernsee-tal", name="Tegernseer Tal")
    q = Quelle(key="t", adapter="x", name="Quelle T", base_url="https://t.example")
    session.add_all([r, q])
    session.flush()
    g = Gebiet(slug="kreuth", name="Kreuth", region_id=r.id, tourist_url="https://t.example")
    h = Gebiet(slug="bad-wiessee", name="Bad Wiessee", region_id=r.id, tourist_url="https://t.example")
    session.add_all([g, h])
    session.flush()
    ls = [Loipe(quelle_id=q.id, gebiet_id=(g if i < 2 else h).id, source_key=f"l{i}", name=f"Loipe {i}", source_url="https://t.example") for i in range(3)]
    session.add_all(ls)
    session.flush()
    return ls


def ev(loipe: Loipe, art: str, gebiet="kreuth", name="Kreuth") -> Ereignis:
    status = {"oeffnet": "offen", "frisch_gespurt": "offen", "schliesst": "geschlossen"}[art]
    return Ereignis(art, loipe.name, gebiet, name, "tegernsee-tal", status, 4.2, loipe.id)


# ---------- N11: kein Doppelversand ----------

@pytest.mark.req("N11", ak=1)
def test_n11_wieder_oeffnen_nach_kurzem_unbekannt_wird_nicht_erneut_gemeldet(session, loipen):
    l = loipen[0]
    assert entprelle(session, [ev(l, "oeffnet")], T0) != []
    # Quelle meldet kurz "unbekannt", danach wieder "offen": ereignisse.py erzeugt erneut "oeffnet"
    assert entprelle(session, [ev(l, "oeffnet")], T0 + timedelta(hours=5)) == []
    # nach 48 Stunden ist das eine neue Nachricht wert (z. B. lange ohne Angabe)
    assert entprelle(session, [ev(l, "oeffnet")], T0 + timedelta(hours=49)) != []


@pytest.mark.req("N11", ak=4)
def test_n11_gegenlaeufiger_wechsel_geht_immer_durch(session, loipen):
    l = loipen[0]
    entprelle(session, [ev(l, "oeffnet")], T0)
    assert [e.art for e in entprelle(session, [ev(l, "schliesst")], T0 + timedelta(hours=1))] == ["schliesst"]
    assert [e.art for e in entprelle(session, [ev(l, "oeffnet")], T0 + timedelta(hours=2))] == ["oeffnet"]
    assert entprelle(session, [ev(l, "schliesst")], T0 + timedelta(hours=3)) != []
    assert entprelle(session, [ev(l, "schliesst")], T0 + timedelta(hours=4)) == []  # doppelt: nicht noch einmal


@pytest.mark.req("N11", ak=2)
def test_n11_frisch_gespurt_hoechstens_einmal_in_18_stunden_und_nicht_gleich_nach_oeffnet(session, loipen):
    a, b = loipen[0], loipen[1]
    entprelle(session, [ev(a, "oeffnet")], T0)
    assert entprelle(session, [ev(a, "frisch_gespurt")], T0 + timedelta(hours=3)) == []
    assert entprelle(session, [ev(a, "frisch_gespurt")], T0 + timedelta(hours=19)) != []
    assert entprelle(session, [ev(b, "frisch_gespurt")], T0) != []
    assert entprelle(session, [ev(b, "frisch_gespurt")], T0 + timedelta(hours=6)) == []
    assert entprelle(session, [ev(b, "frisch_gespurt")], T0 + timedelta(hours=24)) != []
    # jede Loipe fuer sich: B haelt A nicht zurueck
    p = session.get(Meldeprotokoll, a.id)
    assert p.status_art == "oeffnet" and p.befahrbar_at == T0 + timedelta(hours=19)


@pytest.mark.req("N11", ak=3)
def test_n11_worker_entprellt_vor_allen_kanaelen():
    """Im Worker steht das Entprellen nach dem Plausibilitaetsfilter und vor _melde (Push, Mail, oeffentlicher Push)."""
    import inspect
    quelltext = inspect.getsource(worker.lauf)
    filter_pos = quelltext.index("ohne_unplausible(ereignisse")
    entprell_pos = quelltext.index("entprelle(session, ereignisse)")
    melde_pos = quelltext.index("_melde(settings, sender, ereignisse")
    assert filter_pos < entprell_pos < melde_pos


# ---------- N10: oeffentlicher Push ueber ntfy ----------

@pytest.mark.req("N10", ak=2)
def test_n10_je_thema_eine_nachricht_gebiet_buendelt(loipen):
    a, b, c = loipen
    liste = nachrichten(CFG, [ev(a, "oeffnet"), ev(b, "oeffnet"), ev(c, "schliesst", "bad-wiessee", "Bad Wiessee")])
    themen = [n.thema for n in liste]
    assert themen[:2] == ["lb-test-g-kreuth", "lb-test-g-bad-wiessee"]  # Gebiete zuerst
    assert sorted(themen[2:]) == sorted([f"lb-test-l{a.id}", f"lb-test-l{b.id}", f"lb-test-l{c.id}"])
    assert len(set(themen)) == len(themen)
    kreuth = liste[0]
    assert kreuth.titel == "Kreuth: 2 Neuigkeiten" and "Loipe 0 (Kreuth) ist jetzt befahrbar" in kreuth.text
    assert "Loipe 2" not in kreuth.text  # anderes Gebiet
    lp = [n for n in liste if n.thema == f"lb-test-l{a.id}"][0]
    assert lp.klick == f"https://loipen.example/#/loipe/{a.id}" and "ohne Gewähr" in lp.text


@pytest.mark.req("N10", ak=2)
def test_n10_zwei_ereignisse_einer_loipe_in_einem_lauf_ergeben_eine_nachricht(loipen):
    a = loipen[0]
    liste = nachrichten(CFG, [ev(a, "oeffnet"), ev(a, "frisch_gespurt")])
    lp = [n for n in liste if n.thema == f"lb-test-l{a.id}"]
    assert len(lp) == 1 and "befahrbar" in lp[0].text and "frisch gespurt" in lp[0].text
    assert lp[0].text.count("ohne Gewähr") == 1


@pytest.mark.req("N10", ak=1)
def test_n10_themen_sind_fuer_ntfy_gueltig():
    assert thema_loipe("lb-x", 17) == "lb-x-l17"
    assert thema_gebiet("lb-x", "st.-johann in tirol") == "lb-x-g-st--johann-in-tirol"
    assert len(thema_gebiet("lb-x", "a" * 100)) == 64
    assert gueltiges_praefix("loipenblick-x7q") == "loipenblick-x7q"
    for falsch in (None, "", "ab", "mit leer", "ä-umlaut", "x" * 41):
        assert gueltiges_praefix(falsch) is None


@pytest.mark.req("N10", ak=3)
def test_n10_tagesgrenze_gebiete_zuerst_und_eine_meldung_an_den_betreiber(session, loipen):
    a, b, c = loipen
    cfg = PushKonfig(praefix="lb-test", max_tag=3)
    gesendet, betreiber = [], []
    ereignisse = [ev(a, "oeffnet"), ev(b, "oeffnet"), ev(c, "oeffnet", "bad-wiessee", "Bad Wiessee")]
    n = veroeffentliche(session, cfg, ereignisse, gesendet.append, lambda t, x: betreiber.append(t), T0)
    assert n == 3 and [m.thema for m in gesendet][:2] == ["lb-test-g-kreuth", "lb-test-g-bad-wiessee"]
    assert betreiber == ["Loipenblick: Push-Tagesgrenze erreicht"]
    # spaeter am selben Tag: nichts mehr, und keine zweite Meldung an den Betreiber
    assert veroeffentliche(session, cfg, ereignisse, gesendet.append, lambda t, x: betreiber.append(t),
                           T0 + timedelta(hours=3)) == 0
    assert len(betreiber) == 1
    # am naechsten Tag (deutsche Zeit) zaehlt es neu
    assert veroeffentliche(session, cfg, ereignisse[:1], gesendet.append, None, T0 + timedelta(days=1)) == 2
    assert session.get(PushTag, (T0 + timedelta(days=1)).date()).anzahl == 2


@pytest.mark.req("N10", ak=3)
def test_n10_fehler_beim_senden_stoppt_die_anderen_nicht(session, loipen):
    a, b, _ = loipen
    gesendet = []

    def senden(n):
        if n.thema.endswith("-g-kreuth"):
            raise RuntimeError("Netz weg")
        gesendet.append(n.thema)

    assert veroeffentliche(session, CFG, [ev(a, "oeffnet"), ev(b, "oeffnet")], senden, None, T0) == 2
    assert len(gesendet) == 2


@pytest.mark.req("N10", ak=2)
def test_n10_ntfy_aufruf_mit_klick_und_token():
    import httpx

    from loipen.benachrichtigung import Nachricht, ntfy_senden
    anfragen = []

    def antwort(request):
        anfragen.append(request)
        return httpx.Response(200, json={"id": "x"})

    client = httpx.Client(transport=httpx.MockTransport(antwort))
    cfg = PushKonfig(praefix="lb-test", server="https://ntfy.example/", token="tk")
    ntfy_senden(cfg, client)(Nachricht("lb-test-l1", "Loipe 1", "Text", "https://loipen.example/#/loipe/1"))
    r = anfragen[0]
    assert str(r.url) == "https://ntfy.example" or str(r.url) == "https://ntfy.example/"
    assert r.headers["Authorization"] == "Bearer tk"
    body = json.loads(r.content)
    assert body["topic"] == "lb-test-l1" and body["click"].endswith("#/loipe/1") and body["tags"] == ["ski"]


@pytest.mark.req("N10", ak=4)
def test_n10_ohne_praefix_kein_push_und_kein_hinweis(session, tmp_path, loipen):
    assert nachrichten(PushKonfig(), [ev(loipen[0], "oeffnet")]) == []
    assert PushKonfig().fuer_seite() is None
    generator.erzeuge(session, tmp_path, T0)
    assert json.loads((tmp_path / "daten.json").read_text())["push"] is None
    assert "ntfy" not in (tmp_path / "datenschutz.html").read_text(encoding="utf-8")


@pytest.mark.req("N10", ak=5)
def test_n10_seite_und_datenschutz_mit_push(session, tmp_path):
    generator.erzeuge(session, tmp_path, T0, push=CFG.fuer_seite())
    assert json.loads((tmp_path / "daten.json").read_text())["push"] == {"server": "https://ntfy.sh", "praefix": "lb-test"}
    text = (tmp_path / "datenschutz.html").read_text(encoding="utf-8")
    for teil in ("Push-Benachrichtigung mit ntfy", "kein Konto", "Die Seite lädt nichts von ntfy",
                 "Thema in der App löschst", "Art. 6 Abs. 1 lit. a DSGVO", "Meine Loipen"):
        assert teil in text, teil
    # die Seite selbst bindet nichts von ntfy ein (nur Links nach dem Klick)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "ntfy" not in html
    htaccess = (tmp_path / ".htaccess").read_text(encoding="utf-8")
    assert "ntfy" not in htaccess


@pytest.mark.req("N10", ak=2)
def test_n10_worker_schickt_push_nach_dem_mail_abo(session, loipen, tmp_path, monkeypatch):
    (tmp_path / "gebiete.yaml").write_text("gebiete: []\nregionen: []\n", encoding="utf-8")
    s = Settings(config_dir=str(tmp_path), push_praefix="lb-test", oeffentliche_url="https://loipen.example")

    @contextmanager
    def scope():
        yield session

    gesendet = []
    monkeypatch.setattr(worker, "session_scope", scope)
    monkeypatch.setattr(worker, "push_veroeffentliche",
                        lambda sess, cfg, ereignisse, betreiber=None: gesendet.append((cfg.praefix, len(ereignisse))) or 1)
    worker._melde(s, None, [ev(loipen[0], "oeffnet")], [])
    assert gesendet == [("lb-test", 1)]
    gesendet.clear()
    worker._melde(Settings(config_dir=str(tmp_path)), None, [ev(loipen[0], "oeffnet")], [])
    assert gesendet == []  # ohne Praefix aus


@pytest.mark.req("N10", ak=1)
def test_n10_einstellungen_in_env_beispiel():
    from tests.conftest import ROOT
    beispiel = (ROOT / ".env.example").read_text(encoding="utf-8")
    for name in ("LOIPEN_PUSH_PRAEFIX", "LOIPEN_PUSH_MAX_TAG"):
        assert name in beispiel, name
