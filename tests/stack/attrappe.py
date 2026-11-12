"""Attrappe fuer alle Quellen und Wetterdienste im Teststack (docker-compose.test.yml).

Der Worker laeuft mit LOIPEN_UMLEITUNG=http://attrappe:8080 und fragt dann statt
https://www.tegernsee.com/langlaufen hier /www.tegernsee.com/langlaufen an. Die Attrappe liefert:

- Loipenquellen aus tests/fixtures/<quelle>/ (gleiche Zuordnung wie tests.helpers.FixtureFetcher),
  die Quelle wird ueber base_url in config/sources.yaml erkannt
- DWD-Tageswerte (ZIP) und Bright-Sky-Vorhersage im dokumentierten Format, passend zum heutigen Tag.
  Liegt eine echte Aufzeichnung unter tests/fixtures/wetter/ (aus dem Workflow "Live-Pruefung"),
  wird sie stattdessen ausgeliefert.
- /robots.txt, die alles erlaubt

Steuerung fuer den Stack-Test (Daten, keine Anweisungen an den Worker):
    GET /_steuerung?offen=1&ausfall=bayrischzell   Szenario setzen (offen: alle Loipen "geoeffnet")
    GET /_steuerung                                zuruecksetzen
    GET /_protokoll                                alle Anfragen mit User-Agent als JSON
    GET /_gesund                                   Healthcheck

Start: python -m tests.stack.attrappe [--port 8080]
"""

import argparse
import hashlib
import http.server
import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from loipen.fetcher import HttpFehler
from tests.helpers import FIXTURES, SEITEN_QUELLEN, FixtureFetcher
from tests.wetterformat import brightsky, dwd_zip

ROOT = Path(__file__).resolve().parents[2]
WETTER = FIXTURES / "wetter"
GESCHLOSSEN, OFFEN = "<strong>nicht befahrbar</strong>", "<strong>geöffnet</strong>"


class Zustand:
    def __init__(self):
        self.lock = threading.Lock()
        self.offen = False
        self.ausfall: set[str] = set()
        self.protokoll: list[dict] = []


ZUSTAND = Zustand()


def lade_quellen(config_dir: Path) -> list[tuple[str, str, str]]:
    """[(praefix 'host/pfad', key, base_url)], laengster Praefix zuerst."""
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    quellen = []
    for q in sources.get("quellen", []):
        base = q["base_url"].rstrip("/")
        t = urlsplit(base)
        quellen.append((f"{t.netloc}{t.path}", q["key"], base))
    return sorted(quellen, key=lambda x: -len(x[0]))


def _station_werte(station: str) -> int:
    return int(hashlib.sha1(station.encode()).hexdigest(), 16) % 30


def dwd_antwort(station: str, heute: date) -> bytes:
    aufnahme = WETTER / "dwd" / f"tageswerte_RR_{station}_akt.zip"
    if aufnahme.exists():
        return aufnahme.read_bytes()
    basis = _station_werte(station)
    zeilen = []
    for i in range(14, 0, -1):  # bis gestern, wie beim DWD (1 bis 2 Tage Verzug)
        tag = heute - timedelta(days=i)
        neu = 4.0 if i in (1, 2) else 0.0
        zeilen.append((tag, 2.0 if neu else 0.0, 20 + basis + (14 - i), neu))
    return dwd_zip(zeilen)


def geosphere_antwort(q: dict, heute: date) -> str:
    """klima-v2-1d im Format der echten Antwort (tests/fixtures/geosphere/), Werte je Station erfunden."""
    stationen = [s for v in q.get("station_ids", []) for s in v.split(",") if s]
    tage = [heute - timedelta(days=i) for i in range(14, 0, -1)]
    features = []
    for station in stationen:
        basis = _station_werte(station)
        sh = [20 + basis + i for i in range(len(tage))]
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [47.5, 12.2]},
                         "properties": {"station": int(station), "parameters": {
                             "rr": {"data": [2.0 if i >= 12 else -1 for i in range(len(tage))]},
                             "sh": {"data": sh}, "sh_manu": {"data": [None] * len(tage)},
                             "shneu_manu": {"data": [None] * len(tage)}}}})
    return json.dumps({"type": "FeatureCollection", "timestamps": [f"{t.isoformat()}T00:00+00:00" for t in tage],
                       "features": features})


def brightsky_antwort(von: date, bis: date) -> str:
    tage = {}
    tag = von
    while tag <= bis:
        schnee = tag.toordinal() % 3 == 0
        tage[tag] = [(-6.0 + h * 0.4, 0.2 if schnee and h in (3, 4, 5) else 0.0, "snow" if schnee and h in (3, 4, 5) else "dry")
                     for h in range(24)]
        tag += timedelta(days=1)
    return brightsky(tage)


class Attrappe(http.server.BaseHTTPRequestHandler):
    quellen: list[tuple[str, str, str]] = []

    def log_message(self, fmt, *args):  # das Protokoll steht unter /_protokoll
        pass

    def _sende(self, status: int, inhalt: bytes | str, typ: str = "text/html; charset=utf-8") -> None:
        daten = inhalt.encode("utf-8") if isinstance(inhalt, str) else inhalt
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def do_GET(self):  # noqa: N802
        t = urlsplit(self.path)
        if t.path == "/_gesund":
            return self._sende(200, "ok", "text/plain")
        if t.path == "/_protokoll":
            with ZUSTAND.lock:
                return self._sende(200, json.dumps(ZUSTAND.protokoll), "application/json")
        if t.path == "/_steuerung":
            q = parse_qs(t.query)
            with ZUSTAND.lock:
                ZUSTAND.offen = q.get("offen", ["0"])[0] == "1"
                ZUSTAND.ausfall = {k for v in q.get("ausfall", []) for k in v.split(",") if k}
                return self._sende(200, json.dumps({"offen": ZUSTAND.offen, "ausfall": sorted(ZUSTAND.ausfall)}),
                                   "application/json")

        with ZUSTAND.lock:
            ZUSTAND.protokoll.append({"pfad": self.path, "user_agent": self.headers.get("User-Agent")})
        if t.path == "/robots.txt":
            return self._sende(200, "User-agent: *\nAllow: /\n", "text/plain")

        host, _, rest = t.path.lstrip("/").partition("/")
        heute = datetime.now().date()
        if host == "opendata.dwd.de":
            station = rest.rsplit("tageswerte_RR_", 1)[-1].split("_akt.zip")[0]
            return self._sende(200, dwd_antwort(station, heute), "application/zip")
        if host == "dataset.api.hub.geosphere.at":
            return self._sende(200, geosphere_antwort(parse_qs(t.query), heute), "application/json")
        if host == "api.brightsky.dev":
            q = parse_qs(t.query)
            von = date.fromisoformat(q.get("date", [heute.isoformat()])[0][:10])
            bis = date.fromisoformat(q.get("last_date", [(heute + timedelta(days=7)).isoformat()])[0][:10])
            return self._sende(200, brightsky_antwort(von, bis), "application/json")

        voll = t.path.lstrip("/")
        for praefix, key, base in self.quellen:
            if voll == praefix or voll.startswith(praefix + "/"):
                if key in ZUSTAND.ausfall:
                    return self._sende(503, "Attrappe: Ausfall simuliert", "text/plain")
                url = "https://" + voll + (f"?{t.query}" if t.query else "")
                try:
                    text = FixtureFetcher(key, base, seiten=SEITEN_QUELLEN.get(key)).get(url)
                except HttpFehler:
                    return self._sende(404, "nicht in den Fixtures", "text/plain")
                if ZUSTAND.offen:
                    text = text.replace(GESCHLOSSEN, OFFEN)
                typ = "application/json" if text.lstrip().startswith(("{", "[")) else "text/html; charset=utf-8"
                return self._sende(200, text, typ)
        return self._sende(404, f"Attrappe kennt {host} nicht", "text/plain")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--config", type=Path, default=ROOT / "config")
    args = ap.parse_args()
    Attrappe.quellen = lade_quellen(args.config)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), Attrappe)
    print(f"Attrappe auf Port {args.port}, Quellen: {', '.join(k for _, k, _ in Attrappe.quellen)}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
