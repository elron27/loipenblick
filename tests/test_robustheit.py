"""Robuster Abruf nach dem Worker-Log vom 20.11.2026: B28 (Aussetzer, Teilergebnisse, Wetter ohne Quelle,
0 Loipen als Warnung) und B29 (tote Detailseiten, verschwundene Loipen).

Schnappschuesse: tests/fixtures/tirol/2026-11-20/
(bichlachrunde leitet auf eine Wandertour um, miesbergloipe 404), tests/fixtures/tegernsee/2026-11-20/
(robots.txt mit Crawl-delay 5, Schneebericht-Seiten unveraendert).
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select

from loipen.ablauf import VERSCHWUNDEN_STUNDEN, rufe_quelle_ab
from loipen.adapters import ADAPTERS
from loipen.adapters.ats import AtsAdapter, lese_statusseite
from loipen.adapters.base import AdapterErgebnis, LoipenDaten
from loipen.adapters.tirolat import TOTE_DETAILS_TAGE, TirolAtAdapter
from loipen.fetcher import HoeflicherFetcher, HttpFehler
from loipen.konfig import CONFIG_DIR, lade_und_abgleichen, lade_yaml
from loipen.models import Gebiet, Loipe, Quelle, Status, Technik
from loipen.wetter import aktualisiere_wetter
from loipen.zustand import letzter_zustand
from tests.helpers import FIXTURES, SEITEN_QUELLEN, FixtureFetcher
from tests.test_fetcher import UA, Uhr
from tests import test_adapter_tirol as tirol

BERLIN = ZoneInfo("Europe/Berlin")
T0 = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
ROBOTS_TEGERNSEE = (FIXTURES / "tegernsee" / "2026-11-20" / "robots.txt").read_text(encoding="utf-8")


def fetcher_mit(handler, delay_s=5.0):
    uhr = Uhr()
    anfragen: list[str] = []

    def wrapper(request):
        anfragen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_TEGERNSEE)
        return handler(request, sum(1 for p in anfragen if p == request.url.path))

    f = HoeflicherFetcher(UA, delay_s, transport=httpx.MockTransport(wrapper), sleep=uhr.schlafen, clock=uhr.zeit)
    return f, uhr, anfragen


# --- B28 AK 1: Wiederholung bei Aussetzern ---------------------------------------------------------------

@pytest.mark.req("B28", ak=1)
def test_b28_verbindungsabbruch_wird_mit_wartezeit_wiederholt():
    def handler(request, n):
        if n == 1:  # wie im Log: ruhende Keep-Alive-Verbindung, der Server schliesst ohne Antwort
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=request)
        return httpx.Response(200, text="ok")

    f, uhr, anfragen = fetcher_mit(handler)
    assert f.get("https://www.tegernsee.com/a-ringseeloipe-42-km-skating-u-klassisch") == "ok"
    assert anfragen.count("/a-ringseeloipe-42-km-skating-u-klassisch") == 2
    # Crawl-delay 5 der robots.txt: erst 2x Abstand warten, nicht sofort nachhaken
    assert max(uhr.pausen) >= 10


@pytest.mark.req("B28", ak=1)
def test_b28_nach_drei_versuchen_kommt_der_fehler_zum_aufrufer():
    def handler(request, n):
        raise httpx.ConnectError("Verbindung abgelehnt", request=request)

    f, uhr, anfragen = fetcher_mit(handler)
    with pytest.raises(httpx.ConnectError):
        f.get("https://www.tegernsee.com/langlaufen")
    assert anfragen.count("/langlaufen") == 3
    assert sorted(uhr.pausen)[-2:] == [10.0, 20.0]  # Wartezeit verdoppelt sich


@pytest.mark.req("B28", ak=1)
def test_b28_503_mit_retry_after_wird_wiederholt_404_nicht():
    def handler(request, n):
        if request.url.path == "/weg":
            return httpx.Response(404)
        if n == 1:
            return httpx.Response(503, headers={"Retry-After": "30"})
        return httpx.Response(200, text="wieder da")

    f, uhr, anfragen = fetcher_mit(handler)
    assert f.get("https://www.tegernsee.com/x") == "wieder da"
    assert 30.0 in uhr.pausen
    with pytest.raises(HttpFehler):
        f.get("https://www.tegernsee.com/weg")
    assert anfragen.count("/weg") == 1


@pytest.mark.req("B28", ak=1)
def test_b28_taktung_entspricht_dem_crawl_delay_von_tegernsee():
    assert "Crawl-delay: 5" in ROBOTS_TEGERNSEE
    f, uhr, _ = fetcher_mit(lambda r, n: httpx.Response(200, text="ok"), delay_s=5.0)
    f.get("https://www.tegernsee.com/a")
    assert f.abstand_fuer("https://www.tegernsee.com") == 5.0
    # die Schneebericht-Seiten haben sich nicht geaendert (Schnappschuss 20.11.2026)
    seite = lese_statusseite((FIXTURES / "tegernsee" / "2026-11-20" /
                              "a-ringseeloipe-42-km-skating-u-klassisch.html").read_text(encoding="utf-8"))
    assert seite["infos"]["Loipenzustand"] == "nicht befahrbar"


# --- B28 AK 2: Teilergebnisse statt Totalausfall -----------------------------------------------------------

class AbbruchFetcher(FixtureFetcher):
    """Wie im Log: nach einigen Seiten bricht eine Verbindung ab (auch nach den Wiederholungen)."""

    def __init__(self, *a, kaputt: str, **kw):
        super().__init__(*a, **kw)
        self.kaputt = kaputt

    def get(self, url: str) -> str:
        if url.endswith(self.kaputt):
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return super().get(url)


@pytest.fixture
def db(session):
    lade_und_abgleichen(session)
    return session


def _quelle(session, key) -> Quelle:
    return session.scalar(select(Quelle).where(Quelle.key == key))


@pytest.mark.req("B28", ak=2)
def test_b28_abbruch_einer_seite_verwirft_die_quelle_nicht(db):
    q = _quelle(db, "tegernsee")
    rufe_quelle_ab(db, q, FixtureFetcher("tegernsee", q.base_url), T0)
    ring = db.scalar(select(Loipe).where(Loipe.source_key == "a-ringseeloipe"))
    vorher = letzter_zustand(db, ring)

    kaputt = "a-ringseeloipe-42-km-skating-u-klassisch"
    lauf = rufe_quelle_ab(db, q, AbbruchFetcher("tegernsee", q.base_url, kaputt=kaputt), T0 + timedelta(hours=5))
    assert lauf.fehler is None
    assert lauf.gefunden >= 20  # alle anderen Loipen kommen an
    assert lauf.status == "warnung"
    assert any(kaputt in w and "RemoteProtocolError" in w for w in lauf.warnungen)
    assert any("Nur ein Teil der Seiten" in w for w in lauf.warnungen)
    # die Loipe ohne Seite behaelt ihren letzten Zustand und bleibt sichtbar
    db.refresh(ring)
    assert ring.active and letzter_zustand(db, ring).id == vorher.id


@pytest.mark.req("B28", ak=2)
def test_b28_ohne_erste_listenseite_faellt_die_quelle_aus_und_behaelt_alles(db):
    q = _quelle(db, "tegernsee")
    rufe_quelle_ab(db, q, FixtureFetcher("tegernsee", q.base_url), T0)
    anzahl = len(db.scalars(select(Loipe).where(Loipe.quelle_id == q.id, Loipe.active)).all())
    lauf = rufe_quelle_ab(db, q, AbbruchFetcher("tegernsee", q.base_url, kaputt="/langlaufen"), T0 + timedelta(days=3))
    assert lauf.fehler and "RemoteProtocolError" in lauf.fehler and lauf.status == "fehler"
    assert len(db.scalars(select(Loipe).where(Loipe.quelle_id == q.id, Loipe.active)).all()) == anzahl


def test_ats_teilergebnis_ohne_datenbank():
    q = next(x for x in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if x["key"] == "tegernsee")
    erg = AtsAdapter().run(q["base_url"], q["config"],
                           AbbruchFetcher("tegernsee", q["base_url"], kaputt="a-rundkurs-point-skating-u-klassisch"))
    assert not erg.vollstaendig and erg.loipen


# --- B28 AK 3: Wetter haengt nicht am Abruf einer Quelle -------------------------------------------------

@pytest.mark.req("B28", ak=3)
def test_b28_jedes_gebiet_hat_eine_eigene_koordinate():
    gebiete = lade_yaml(CONFIG_DIR / "gebiete.yaml")["gebiete"]
    ohne = [g["slug"] for g in gebiete if g.get("lat") is None or g.get("lon") is None]
    assert ohne == []


class NurVorhersage:
    def __init__(self):
        self.urls: list[str] = []

    def get(self, url):
        self.urls.append(url)
        if "brightsky" in url:
            return (FIXTURES / "brightsky" / next(p.name for p in (FIXTURES / "brightsky").iterdir()
                                                  if p.suffix == ".json")).read_text(encoding="utf-8")
        raise HttpFehler(url, 503)

    def get_bytes(self, url):
        raise HttpFehler(url, 503)


@pytest.mark.req("B28", ak=3)
def test_b28_tegernsee_bekommt_vorhersage_ohne_eine_einzige_loipe(db):
    tegernsee = db.scalar(select(Gebiet).where(Gebiet.slug == "tegernsee"))
    assert not tegernsee.loipen  # wie am 20.11. auf dem NAS: die Quelle fiel aus
    f = NurVorhersage()
    lauf = aktualisiere_wetter(db, f, T0)
    assert not any("tegernsee: keine Position" in w for w in lauf.warnungen)
    assert any("lat=47.711" in u for u in f.urls)


# --- B28 AK 4: 0 Loipen trotz HTTP 200 -----------------------------------------------------------------
# (Am 20.11. lieferte achensee.com so 0 Loipen. Achensee Tourismus hat der Nutzung am selben Tag widersprochen;
# die Quelle wird abgeschaltet, deshalb gibt es fuer sie hier keinen Schnappschuss und keine Anpassung.)

@pytest.mark.req("B28", ak=4)
def test_b28_null_loipen_trotz_http_200_ist_eine_warnung(db):
    q = _quelle(db, "kufsteinerland")
    leer = "<html><body><div class='skidataCrossCountry'><h3>Kufstein</h3></div></body></html>"
    lauf = rufe_quelle_ab(db, q, FixtureFetcher("kufsteinerland", q.base_url,
                                                ersetze={"de/schneebericht.html": leer}), T0)
    assert lauf.fehler is None and lauf.gefunden == 0
    assert lauf.status == "warnung"
    assert q.last_error == "Quelle lieferte 0 Loipen"


# --- B29: tote Detailseiten und verschwundene Loipen --------------------------------------------------

def _pfad(erg, name):
    l = next(l for l in erg.loipen if l.name == name)
    return l.source_url.split("://", 1)[1].split("/", 1)[1]


@pytest.mark.req("B29", ak=1)
def test_b29_404_detailseite_wird_eine_woche_ausgesetzt():
    adapter = TirolAtAdapter(uhr=lambda: jetzt[0])
    jetzt = [0.0]
    f = tirol.fetcher()
    erg = adapter.run(tirol.Q["base_url"], tirol.konfig(details_pro_lauf=1000), f)
    tot = [w for w in erg.warnungen if "Detailseiten nicht gefunden (404)" in w]
    assert len(tot) == 1  # eine Sammelwarnung statt einer je Seite
    erste = len(f.abgerufen)

    f2 = tirol.fetcher()
    jetzt[0] = 86400.0  # ein Tag spaeter: die 404-Seiten werden nicht erneut abgerufen
    erg2 = adapter.run(tirol.Q["base_url"], tirol.konfig(details_pro_lauf=1000), f2)
    assert len(f2.abgerufen) < erste
    assert not any("Detailseiten nicht gefunden" in w for w in erg2.warnungen)
    assert len(erg2.loipen) == len(erg.loipen)  # die Loipen selbst bleiben mit Status aus der Liste

    f3 = tirol.fetcher()
    jetzt[0] = (TOTE_DETAILS_TAGE + 1) * 86400.0  # nach einer Woche: neuer Versuch
    adapter.run(tirol.Q["base_url"], tirol.konfig(details_pro_lauf=1000), f3)
    assert len(f3.abgerufen) == erste


@pytest.mark.req("B29", ak=1)
def test_b29_404_seiten_verbrauchen_nicht_das_kontingent(db):
    """Loipen ohne Laenge kommen zuerst dran; tote Seiten duerfen diese Plaetze nicht jedes Mal belegen."""
    adapter = TirolAtAdapter(uhr=lambda: 0.0)
    cfg = tirol.konfig(details_pro_lauf=20)
    cfg["_mit_laenge"] = set()
    f = tirol.fetcher()
    adapter.run(tirol.Q["base_url"], cfg, f)
    erste = set(f.abgerufen)
    f2 = tirol.fetcher()
    adapter.run(tirol.Q["base_url"], cfg, f2)
    tote = [u for u in f.abgerufen if u in erste and u not in f2.abgerufen]
    assert tote  # dieselben 404-Seiten wurden im zweiten Lauf ausgelassen ...
    assert len(f2.abgerufen) >= len(f.abgerufen) - len(tote)


@pytest.mark.req("B29", ak=2)
def test_b29_umleitung_auf_wandertour_wird_nicht_uebernommen():
    adapter = TirolAtAdapter(uhr=lambda: 0.0)
    erg, _ = tirol.lauf(details_pro_lauf=1000)
    name = "KU1 Weissach I"
    pfad = _pfad(erg, name)
    wandern = (FIXTURES / "tirol" / "2026-11-20" / "bichlachrunde.html").read_text(encoding="utf-8")
    f = FixtureFetcher("tirol", tirol.Q["base_url"], seiten=SEITEN_QUELLEN["tirol"], ersetze={pfad: wandern})
    erg2 = adapter.run(tirol.Q["base_url"], tirol.konfig(details_pro_lauf=1000), f)
    l = next(l for l in erg2.loipen if l.name == name)
    assert "wandertouren" not in l.source_url and l.laenge_km != 10.5
    assert any(f"{name}: Detailseite leitet auf" in w and "keine Loipe mehr" in w for w in erg2.warnungen)
    assert l.status in (Status.OFFEN, Status.GESCHLOSSEN)  # Status kommt weiter aus der Kartenliste


class EinfacherAdapter:
    def __init__(self, namen, vollstaendig=True):
        self.namen, self.vollstaendig = namen, vollstaendig

    def run(self, base_url, config, fetcher):
        erg = AdapterErgebnis(vollstaendig=self.vollstaendig)
        for n in self.namen:
            d = LoipenDaten(source_key=n, name=n, source_url=f"{base_url}/{n}", gebiet_slug="tegernsee")
            d.status = Status.GESCHLOSSEN
            erg.loipen.append(d)
        return erg


@pytest.fixture
def testquelle(db, monkeypatch):
    q = _quelle(db, "tegernsee")

    def lauf(namen, zeit, vollstaendig=True):
        monkeypatch.setitem(ADAPTERS, q.adapter, EinfacherAdapter(namen, vollstaendig))
        return rufe_quelle_ab(db, q, None, zeit)

    return q, lauf


def _aktiv(db, q):
    return {l.name for l in db.scalars(select(Loipe).where(Loipe.quelle_id == q.id, Loipe.active))}


@pytest.mark.req("B29", ak=3)
def test_b29_verschwundene_loipe_wird_nach_48_stunden_ausgeblendet(db, testquelle):
    q, lauf = testquelle
    alle = ["a", "b", "c", "d"]
    lauf(alle, T0)
    lauf(alle[:3], T0 + timedelta(hours=12))
    assert _aktiv(db, q) == set(alle)  # ein einzelner fehlender Lauf blendet nichts aus
    r = lauf(alle[:3], T0 + timedelta(hours=VERSCHWUNDEN_STUNDEN + 1))
    assert _aktiv(db, q) == {"a", "b", "c"} and r.ausgeblendet == ["d"]
    lauf(alle, T0 + timedelta(hours=VERSCHWUNDEN_STUNDEN + 5))
    assert _aktiv(db, q) == set(alle)  # meldet die Quelle sie wieder, ist sie sofort zurueck


@pytest.mark.req("B29", ak=3)
def test_b29_teillauf_oder_einbruch_blendet_nichts_aus(db, testquelle):
    q, lauf = testquelle
    alle = ["a", "b", "c", "d"]
    lauf(alle, T0)
    spaeter = T0 + timedelta(days=5)
    lauf(["a", "b", "c"], spaeter, vollstaendig=False)  # Teilergebnis nach Netzfehler (B28)
    assert _aktiv(db, q) == set(alle)
    lauf(["a"], spaeter + timedelta(hours=1))  # weniger als die Haelfte: eher kaputte Seite (B26)
    assert _aktiv(db, q) == set(alle)
