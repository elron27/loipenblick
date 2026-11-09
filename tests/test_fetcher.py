"""Ruecksichtsvoll abrufen: P7."""

import httpx
import pytest

from loipen.fetcher import HoeflicherFetcher, HttpFehler, RobotsVerbot

UA = "LoipenBot/0.1 (privat; kontakt@example.com)"
ROBOTS = "User-agent: *\nCrawl-delay: 5\nDisallow: /intern\n"


class Uhr:
    """Falsche Uhr: sleep() spult sie vor, damit die Tests nicht warten."""

    def __init__(self):
        self.t = 1000.0
        self.pausen: list[float] = []

    def zeit(self):
        return self.t

    def schlafen(self, s):
        self.pausen.append(s)
        self.t += s


def bauen(handler, delay_s=0.0):
    uhr = Uhr()
    anfragen: list[httpx.Request] = []

    def wrapper(request):
        anfragen.append(request)
        return handler(request)

    f = HoeflicherFetcher(UA, delay_s, transport=httpx.MockTransport(wrapper), sleep=uhr.schlafen, clock=uhr.zeit)
    return f, uhr, anfragen


def standard(request):
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text=ROBOTS)
    return httpx.Response(200, text=f"seite {request.url.path}")


@pytest.mark.req("P7", ak=1)
def test_p7_abstand_zwischen_zwei_anfragen_derselben_domain():
    f, uhr, anfragen = bauen(standard, delay_s=0.0)  # der Crawl-delay der robots.txt (5 s) gilt trotzdem
    f.get("https://www.beispiel.de/a")
    f.get("https://www.beispiel.de/b")
    f.get("https://www.beispiel.de/c")
    assert sum(uhr.pausen) >= 10  # zwei Pausen zu je mindestens 5 s zwischen drei Seiten
    assert all(p >= 4.99 for p in uhr.pausen[1:])
    assert [a.url.path for a in anfragen] == ["/robots.txt", "/a", "/b", "/c"]


@pytest.mark.req("P7", ak=1)
def test_p7_einstellung_gilt_wenn_sie_groesser_ist_als_der_crawl_delay():
    f, uhr, _ = bauen(standard, delay_s=8.0)
    f.get("https://www.beispiel.de/a")
    f.get("https://www.beispiel.de/b")
    assert max(uhr.pausen) >= 8.0


@pytest.mark.req("P7", ak=1)
def test_p7_andere_domain_wartet_nicht_auf_die_erste():
    f, uhr, _ = bauen(standard, delay_s=5.0)
    f.get("https://www.eins.de/a")
    vorher = sum(uhr.pausen)
    f.get("https://www.zwei.de/a")
    # nur der Abstand zwischen robots.txt und Seite der zweiten Domain, nicht der der ersten
    assert sum(uhr.pausen) - vorher == pytest.approx(5.0)


@pytest.mark.req("P7", ak=2)
def test_p7_durch_robots_gesperrte_url_wird_nicht_abgerufen():
    f, _, anfragen = bauen(standard)
    with pytest.raises(RobotsVerbot):
        f.get("https://www.beispiel.de/intern/geheim")
    assert "/intern/geheim" not in [a.url.path for a in anfragen]


@pytest.mark.req("P7", ak=2)
def test_p7_robots_verbietet_alles_bei_403():
    f, _, anfragen = bauen(lambda r: httpx.Response(403))
    with pytest.raises(RobotsVerbot):
        f.get("https://www.beispiel.de/a")
    assert len(anfragen) == 1  # nur robots.txt


@pytest.mark.req("P7", ak=3)
def test_p7_jede_anfrage_traegt_user_agent_mit_kontakt():
    f, _, anfragen = bauen(standard)
    f.get("https://www.beispiel.de/a")
    assert anfragen and all(a.headers["user-agent"] == UA for a in anfragen)
    assert "@" in UA


@pytest.mark.req("P7")
def test_p7_etag_wird_wiederverwendet():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS)
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, text="inhalt", headers={"ETag": '"v1"'})

    f, _, anfragen = bauen(handler)
    assert f.get("https://www.beispiel.de/a") == "inhalt"
    assert f.get("https://www.beispiel.de/a") == "inhalt"  # 304: aus dem Cache
    assert anfragen[-1].headers["if-none-match"] == '"v1"'


@pytest.mark.req("P7")
def test_p7_fehlerstatus_wird_gemeldet():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)  # keine robots.txt = alles erlaubt
        return httpx.Response(404)

    f, _, _ = bauen(handler)
    with pytest.raises(HttpFehler) as e:
        f.get("https://www.beispiel.de/weg")
    assert e.value.status == 404
