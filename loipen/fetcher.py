"""Ruecksichtsvoll abrufen (P7): robots.txt beachten, Abstand pro Domain, eigener
User-Agent mit Kontakt, Cache per ETag und Last-Modified.

Testbetrieb: Mit `umleitung` (LOIPEN_UMLEITUNG, z. B. http://attrappe:8080) gehen alle Abrufe an
diesen Server statt ins Netz, aus https://host/pfad?q wird <umleitung>/host/pfad?q. So laeuft der
ganze Stack in der CI gegen die gespeicherten Beispielseiten (tests/stack, docs/testumgebung.md).
"""

import logging
import time
import urllib.robotparser
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

log = logging.getLogger("loipen.fetcher")


class RobotsVerbot(Exception):
    """robots.txt verbietet den Abruf; die URL wird nicht angefragt."""


class HttpFehler(Exception):
    def __init__(self, url: str, status: int):
        super().__init__(f"{url}: HTTP {status}")
        self.url = url
        self.status = status


class HoeflicherFetcher:
    def __init__(
        self,
        user_agent: str,
        delay_s: float = 5.0,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        timeout_s: float = 30.0,
        umleitung: str | None = None,
    ):
        self.umleitung = umleitung.rstrip("/") if umleitung else None
        if self.umleitung:
            log.warning("Testbetrieb: alle Abrufe gehen an %s statt an die echten Quellen", self.umleitung)
        self.user_agent = user_agent
        self.delay_s = delay_s
        self._sleep = sleep
        self._clock = clock
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            transport=transport,
            timeout=timeout_s,
            follow_redirects=True,
        )
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._letzter_abruf: dict[str, float] = {}
        # url -> (etag, last_modified, text)
        self._cache: dict[str, tuple[str | None, str | None, str]] = {}

    def close(self) -> None:
        self._client.close()

    def ziel(self, url: str) -> str:
        """Die URL, die wirklich abgerufen wird (ohne Umleitung unveraendert)."""
        if not self.umleitung:
            return url
        t = urlsplit(url)
        return f"{self.umleitung}/{t.netloc}{t.path or '/'}" + (f"?{t.query}" if t.query else "")

    @staticmethod
    def _host(url: str) -> str:
        teile = urlsplit(url)
        return f"{teile.scheme}://{teile.netloc}"

    def _warte(self, host: str, abstand: float) -> None:
        letzter = self._letzter_abruf.get(host)
        if letzter is not None:
            rest = abstand - (self._clock() - letzter)
            if rest > 0:
                self._sleep(rest)
        self._letzter_abruf[host] = self._clock()

    def _robots_fuer(self, host: str) -> urllib.robotparser.RobotFileParser | None:
        if host not in self._robots:
            self._warte(host, self.delay_s)
            parser = urllib.robotparser.RobotFileParser()
            try:
                antwort = self._client.get(f"{host}/robots.txt")
            except httpx.HTTPError as e:
                log.warning("robots.txt von %s nicht lesbar: %s", host, e)
                parser = None
            else:
                if antwort.status_code in (401, 403):
                    parser.disallow_all = True
                elif antwort.status_code >= 400:
                    parser.allow_all = True
                else:
                    parser.parse(antwort.text.splitlines())
            self._robots[host] = parser
        return self._robots[host]

    def abstand_fuer(self, host: str) -> float:
        """Der groessere Wert aus Einstellung und Crawl-delay der robots.txt."""
        parser = self._robots.get(host)
        crawl = parser.crawl_delay(self.user_agent) if parser else None
        return max(self.delay_s, float(crawl)) if crawl else self.delay_s

    def _vorbereiten(self, url: str) -> None:
        """robots.txt pruefen und den Abstand pro Domain einhalten."""
        host = self._host(url)
        robots = self._robots_fuer(host)
        if robots is not None and not robots.can_fetch(self.user_agent, url):
            raise RobotsVerbot(f"robots.txt verbietet {url}")
        self._warte(host, self.abstand_fuer(host))

    def get_bytes(self, url: str) -> bytes:
        """Wie get, aber fuer Binaerdateien (z. B. ZIP vom DWD). Ohne Cache."""
        url = self.ziel(url)
        self._vorbereiten(url)
        antwort = self._client.get(url)
        if antwort.status_code >= 400:
            raise HttpFehler(url, antwort.status_code)
        return antwort.content

    def get(self, url: str) -> str:
        url = self.ziel(url)
        self._vorbereiten(url)
        kopf: dict[str, str] = {}
        zwischen = self._cache.get(url)
        if zwischen:
            etag, modified, _ = zwischen
            if etag:
                kopf["If-None-Match"] = etag
            if modified:
                kopf["If-Modified-Since"] = modified

        antwort = self._client.get(url, headers=kopf)
        if antwort.status_code == 304 and zwischen:
            return zwischen[2]
        if antwort.status_code >= 400:
            raise HttpFehler(url, antwort.status_code)
        text = antwort.text
        etag, modified = antwort.headers.get("ETag"), antwort.headers.get("Last-Modified")
        if etag or modified:
            self._cache[url] = (etag, modified, text)
        return text
