"""Speichert die Quellseiten als Testdaten fuer die Adapter.

Nur Python-Standardbibliothek, laeuft unter Windows, macOS und Linux:

    python scripts/beispielseiten_holen.py
    python scripts/beispielseiten_holen.py --nur-schneebericht

Legt alles unter tests/fixtures/<quelle>/ ab und haelt 5 Sekunden Abstand
zwischen zwei Anfragen, wie es die robots.txt der Seiten verlangt.
"""

import re
import sys
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

# Schneebericht-Seiten aus der alten App (loipen_app/scrapy_spiders). Das sind
# eigene /a-...-Seiten mit dem Loipenstatus, nicht die Tourenseiten aus der
# Langlauf-Uebersicht. Gespeichert unter <quelle>/schneebericht/.
SCHNEEBERICHT_SEITEN = {
    "tegernsee": [
        "a-golfplatzrunde-87-km", "a-skitty-world-langlauf-parcours",
        "a-sportplatzrunde-35-km-1", "a-sportplatzrunde-17-km-schneebericht",
        "a-verbindungsloipe", "a-gasslerrunde-1", "a-oedbergrunde-1",
        "a-panoramablick-1", "a-runde-hainzenhoehe-steinberg-1",
        "a-verbindungsloipe-hainzenhoehe-steinberg",
        "a-klamm-bayerwald-glashuette-109-km-klassisch",
        "a-klamm-bayerwald-09-km-skating", "a-klamm-bayerwald-skating",
        "a-kreuth-scharling-skating-u-klassisch", "a-kreuth-wildbad-kreuth-klassisch",
        "a-nachtloipe-brunnbichl-skating-u-klassisch",
        "a-ringseeloipe-42-km-skating-u-klassisch",
        "a-rundkurs-point-skating-u-klassisch",
        "a-sonnenloipe-scharling-oberhof-skating-u-klassisch",
        "a-wildbad-kreuth-klamm-klassisch", "a-suttenrunde-1", "a-ellmaurunde-1",
        "a-glocknerwiesn-1", "a-gsotthaberrunde-1", "a-gutfelderrunde-1",
        "a-sonnenmoosrunde-1",
    ],
    "bayrischzell": [
        "a-kloo-ascher-runde-1", "a-zipflwirt-hauswies-runde-1",
        "a-bayrischzell-geitau-bayrischzell-1", "a-bayrischzell-zipflwirt-bayrischzell-1",
        "a-melkstatt-runde-2", "a-mieseben-runde-2", "a-streinalm-runde-1",
        "a-ursprungrunde", "a-nessler-runde-1",
    ],
    "fischbachau": [
        "a-point-hundham-1", "a-schreyern-runde-1", "a-hundham-kleine-uebungsrunde-1",
        "a-kleine-schreiern-runde-1", "a-lippmuehlenrunde-1", "a-zipflwirt-hauswies-runde-1",
    ],
}

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


def hole_schneeberichte() -> None:
    for key, slugs in SCHNEEBERICHT_SEITEN.items():
        print(f"{key}: {len(slugs)} Schneebericht-Seiten")
        for slug in slugs:
            try:
                html = get(f"{ATS_QUELLEN[key]}/{slug}")
                save(OUT / key / "schneebericht" / f"{slug}.html", html)
            except Exception as e:  # alte Adressen koennen inzwischen fehlen
                print(f"  {slug}: {e}")


def main() -> None:
    if "--nur-schneebericht" in sys.argv:
        hole_schneeberichte()
        print(f"\nFertig. Ordner: {OUT}")
        return
    for key, base_url in ATS_QUELLEN.items():
        hole_ats(key, base_url)
    hole_schneeberichte()
    print("sachrang: Schneebericht")
    save(OUT / "sachrang" / "schneebericht.html", get(ASCHAU_REPORT))
    print(f"\nFertig. Ordner: {OUT}")


if __name__ == "__main__":
    main()
