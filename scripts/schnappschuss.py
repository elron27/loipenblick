"""Schnappschuesse neuer Quellen als Fixtures holen (CLAUDE.md Regel 10, B19).

Liest scripts/schnappschuss.txt: je Zeile "<zielpfad> <url>" (zielpfad relativ zum Repo).
Prueft vor jedem Abruf die robots.txt des Hosts (P7, P17) und haelt 5 s Abstand je Host.
Nur Standardbibliothek. Laeuft im Workflow "Schnappschuss" auf einem GitHub-Runner, weil die
Cloud-Sitzung die Quellen nicht immer erreicht, oder lokal:

    python scripts/schnappschuss.py
Ergebnis: Dateien unter den Zielpfaden und ein Protokoll in tests/fixtures/schnappschuss-protokoll.txt.
"""

import os
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
LISTE = ROOT / "scripts" / "schnappschuss.txt"
PROTOKOLL = ROOT / "tests" / "fixtures" / "schnappschuss-protokoll.txt"
UA = os.environ.get("LOIPEN_USER_AGENT") or "LoipenBot/0.1 (+https://github.com/elron27/loipenblick)"
DELAY_S = 5


def holen(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "de"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""
    except (urllib.error.URLError, OSError) as e:
        # Nicht erreichbarer Host oder Zeitueberschreitung: protokollieren statt den ganzen Lauf abbrechen.
        return 0, f"FEHLER {e}".encode()


def main() -> int:
    robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
    letzter: dict[str, float] = {}
    zeilen = []
    for roh in LISTE.read_text(encoding="utf-8").splitlines():
        roh = roh.strip()
        if not roh or roh.startswith("#"):
            continue
        ziel, url = roh.split(None, 1)
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))

        def warte():
            rest = DELAY_S - (time.monotonic() - letzter.get(host, -1e9))
            if rest > 0:
                time.sleep(rest)
            letzter[host] = time.monotonic()

        if host not in robots:
            warte()
            status, inhalt = holen(host + "/robots.txt")
            p = urllib.robotparser.RobotFileParser()
            if status == 0:
                p.disallow_all = True
                zeilen.append(f"NICHT ERREICHBAR {host}: {inhalt.decode()}")
                print(zeilen[-1], flush=True)
                robots[host] = p
                continue
            if status in (401, 403):
                p.disallow_all = True
            elif status >= 400:
                p.allow_all = True
            else:
                p.parse(inhalt.decode("utf-8", "replace").splitlines())
            robots[host] = p
            datei = ROOT / Path(ziel).parent / "robots.txt"
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_bytes(inhalt)
            zeilen.append(f"{status} {host}/robots.txt")
        if not robots[host].can_fetch(UA, url):
            if not robots[host].disallow_all or (ROOT / Path(ziel).parent / "robots.txt").exists():
                zeilen.append(f"ROBOTS-VERBOT {url}")
            else:
                zeilen.append(f"UEBERSPRUNGEN {url}")
            continue
        warte()
        status, inhalt = holen(url)
        if status == 0:
            zeilen.append(f"{inhalt.decode()} {url}")
            print(zeilen[-1], flush=True)
            continue
        datei = ROOT / ziel
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(inhalt)
        zeilen.append(f"{status} {len(inhalt):>8} {ziel} {url}")
        print(zeilen[-1], flush=True)
    PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
    stand = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with PROTOKOLL.open("a", encoding="utf-8") as f:
        f.write(f"# Lauf {stand}, User-Agent {UA}\n" + "\n".join(zeilen) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
