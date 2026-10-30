"""Speichert die Quellseiten als Testdaten fuer die Adapter.

Nur Python-Standardbibliothek, laeuft unter Windows, macOS und Linux:

    python scripts/beispielseiten_holen.py

Legt alles unter tests/fixtures/<quelle>/ ab und haelt 5 Sekunden Abstand
zwischen zwei Anfragen, wie es die robots.txt der Seiten verlangt.
"""

import re
import time
import urllib.request
from pathlib import Path

USER_AGENT = "LoipenBot/0.1 (privat, Testdaten)"
DELAY_S = 5
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

ATS_QUELLEN = {
    "tegernsee": "https://www.tegernsee.com",
    "bayrischzell": "https://www.bayrischzell.de",
    "fischbachau": "https://www.fischbachau.de",
}
ASCHAU_REPORT = "https://www.aschau.de/schneebericht-sachrang"

LOIPEN_LINK = re.compile(r'href="(?:https://www\.[a-z-]+\.(?:de|com))?(/a-[a-z0-9-]+)"')


def get(url: str) -> str:
    time.sleep(DELAY_S)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def save(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"  gespeichert: {path.relative_to(OUT)}")


def hole_ats(key: str, base_url: str) -> None:
    print(f"{key}: Uebersicht")
    slugs: list[str] = []
    seite = 0
    while True:
        url = f"{base_url}/langlaufen" + (f"/{seite}" if seite else "")
        try:
            html = get(url)
        except Exception as e:  # letzte Seite liefert meist 404
            print(f"  {url}: {e}")
            break
        neu = [s for s in dict.fromkeys(LOIPEN_LINK.findall(html)) if s not in slugs]
        if not neu:
            break
        save(OUT / key / f"langlaufen_{seite}.html", html)
        slugs.extend(neu)
        seite += 1

    print(f"{key}: {len(slugs)} Loipenseiten")
    for slug in slugs:
        try:
            save(OUT / key / "loipen" / f"{slug.lstrip('/')}.html", get(base_url + slug))
        except Exception as e:
            print(f"  {slug}: {e}")


def main() -> None:
    for key, base_url in ATS_QUELLEN.items():
        hole_ats(key, base_url)
    print("sachrang: Schneebericht")
    save(OUT / "sachrang" / "schneebericht.html", get(ASCHAU_REPORT))
    print(f"\nFertig. Ordner: {OUT}")


if __name__ == "__main__":
    main()
