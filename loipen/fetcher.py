"""Ruecksichtsvoll abrufen (P7): robots.txt beachten, Abstand pro Domain, eigener
User-Agent mit Kontakt, Cache per ETag und Last-Modified.

Aussetzer (B28): Bricht die Verbindung ab (z. B. "Server disconnected without sending a response", wenn der
Server eine ruhende Keep-Alive-Verbindung schliesst), laeuft die Zeit ab oder antwortet der Server mit 429/502/503/504,
wird die Seite bis zu WIEDERHOLUNGEN-mal erneut geholt. Die Wartezeit verdoppelt sich (2x, 4x der Abstand je Domain),
Retry-After wird beachtet (hoechstens MAX_WARTEN_S).

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

WIEDERHOLUNGEN = 2  # also hoechstens 3 Versuche je Seite
WIEDERHOLEN_BEI = frozenset({429, 502, 503, 504})
MAX_WARTEN_S = 120.0


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
        wiederholungen: int = WIEDERHOLUNGEN,
    ):
        self.umleitung = umleitung.rstrip("/") if umleitung else None
        if self.umleitung:
            log.warning("Testbetrieb: alle Abrufe gehen an %s statt an die echten Quellen", self.umleitung)
        self.user_agent = user_agent
        self.delay_s = delay_s
        self.wiederholungen = wiederholungen
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
                antwort = self._senden(f"{host}/robots.txt")
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

    def _wartezeit(self, url: str, versuch: int, antwort: httpx.Response | None) -> float:
        """2x, dann 4x der Abstand der Domain (mindestens 1 s), bei Retry-After dessen Wert."""
        warten = max(self.abstand_fuer(self._host(url)), 1.0) * 2 ** (versuch + 1)
        nach = antwort.headers.get("Retry-After") if antwort is not None else None
        if nach and nach.strip().isdigit():
            warten = max(warten, float(nach))
        return min(warten, MAX_WARTEN_S)

    def _senden(self, url: str, kopf: dict[str, str] | None = None) -> httpx.Response:
        """Ein GET mit Wiederholung bei Aussetzern (B28). Der letzte Fehler geht an den Aufrufer."""
        versuch = 0
        while True:
            try:
                antwort = self._client.get(url, headers=kopf)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                if versuch >= self.wiederholungen:
                    raise
                warten = self._wartezeit(url, versuch, None)
                log.warning("%s: %s, neuer Versuch in %.0f s", url, type(e).__name__, warten)
            else:
                if antwort.status_code not in WIEDERHOLEN_BEI or versuch >= self.wiederholungen:
                    return antwort
                warten = self._wartezeit(url, versuch, antwort)
                log.warning("%s: HTTP %d, neuer Versuch in %.0f s", url, antwort.status_code, warten)
            versuch += 1
            self._sleep(warten)
            self._letzter_abruf[self._host(url)] = self._clock()

    def get_bytes(self, url: str) -> bytes:
        """Wie get, aber fuer Binaerdateien (z. B. ZIP vom DWD). Ohne Cache."""
        url = self.ziel(url)
        self._vorbereiten(url)
        antwort = self._senden(url)
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

        antwort = self._senden(url, kopf)
        if antwort.status_code == 304 and zwischen:
            return zwischen[2]
        if antwort.status_code >= 400:
            raise HttpFehler(url, antwort.status_code)
        text = antwort.text
        etag, modified = antwort.headers.get("ETag"), antwort.headers.get("Last-Modified")
        if etag or modified:
            self._cache[url] = (etag, modified, text)
        return text
