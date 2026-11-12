"""Testumgebung ohne NAS (docs/testumgebung.md): Umleitung im Fetcher und Attrappe.

Der grosse Ende-zu-Ende-Test im Docker-Stack steht in tests/stack/. Hier laeuft dasselbe ohne Docker:
echter HoeflicherFetcher mit Umleitung -> Attrappe auf localhost -> Adapter, Wetter, Datenbank.
"""

import http.server
import threading
import urllib.error
import urllib.request

import httpx
import pytest
from sqlalchemy import func, select

from loipen.ablauf import rufe_quelle_ab
from loipen.fetcher import HoeflicherFetcher
from loipen.konfig import CONFIG_DIR, lade_und_abgleichen
from loipen.models import Loipe, Quelle, Wetter
from loipen.wetter import aktualisiere_wetter
from tests.stack import attrappe


def test_umleitung_schreibt_jede_url_auf_den_testserver_um():
    gesehen = []

    def handler(request):
        gesehen.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nAllow: /\n" if request.url.path == "/robots.txt" else "ok")

    f = HoeflicherFetcher("UA", 0, transport=httpx.MockTransport(handler), umleitung="http://attrappe:8080/")
    assert f.get("https://www.tegernsee.com/langlaufen/1") == "ok"
    f.get_bytes("https://module.tourinfra.com/chiemgau/inc/ajax.php?ajaxtype=getLoipenmanager")
    assert gesehen == [
        "http://attrappe:8080/robots.txt",
        "http://attrappe:8080/www.tegernsee.com/langlaufen/1",
        "http://attrappe:8080/module.tourinfra.com/chiemgau/inc/ajax.php?ajaxtype=getLoipenmanager",
    ]


def test_ohne_umleitung_bleibt_die_url_unveraendert():
    assert HoeflicherFetcher("UA", 0).ziel("https://www.aschau.de/x?y=1") == "https://www.aschau.de/x?y=1"


@pytest.fixture(scope="module")
def server():
    attrappe.Attrappe.quellen = attrappe.lade_quellen(CONFIG_DIR)
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), attrappe.Attrappe)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def test_attrappe_kennt_alle_quellen_und_simuliert_ausfall(server):
    assert _get(f"{server}/www.tegernsee.com/langlaufen")[0] == 200
    assert _get(f"{server}/www.aschau.de/schneebericht-sachrang")[0] == 200
    assert _get(f"{server}/module.tourinfra.com/chiemgau/inc/ajax.php?ajaxtype=getLoipenmanager")[0] == 200
    assert _get(f"{server}/www.unbekannt.de/x")[0] == 404
    _get(f"{server}/_steuerung?ausfall=sachrang&offen=1")
    try:
        assert _get(f"{server}/www.aschau.de/schneebericht-sachrang")[0] == 503
        seite = _get(f"{server}/www.tegernsee.com/a-ringseeloipe-42-km-skating-u-klassisch")[1]
        assert attrappe.OFFEN in seite and attrappe.GESCHLOSSEN not in seite
    finally:
        _get(f"{server}/_steuerung")


def test_worker_ablauf_gegen_die_attrappe(session, server):
    """Wie ein Worker-Lauf im Teststack: alle Quellen und das Wetter ueber HTTP aus der Attrappe."""
    lade_und_abgleichen(session)
    f = HoeflicherFetcher("LoipenBot-Test", 0, umleitung=server)
    for q in session.scalars(select(Quelle).order_by(Quelle.key)).all():
        lauf = rufe_quelle_ab(session, q, f)
        assert lauf.fehler is None and lauf.gefunden > 0, q.key
    wetter = aktualisiere_wetter(session, f)
    assert wetter.messungen > 0 and wetter.vorhersagen > 0
    assert session.scalar(select(func.count()).select_from(Loipe)) == 26 + 9 + 7 + 4 + 69 + 61 + 71 + 5 + 6  # + tirol, kitzbueheler-alpen, langlaufdorf, berchtesgaden
    assert session.scalar(select(func.count()).select_from(Wetter)) == wetter.messungen + wetter.vorhersagen
