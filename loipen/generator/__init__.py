"""Statische Website (E-10, B7).

Der Generator schreibt nach settings.site_dir: die App (HTML, JS, CSS, PWA-Dateien) aus
loipen/generator/static und die Daten als JSON (Index, je Region eine Datei, je Region die
Strecken). Genau dieser Ordner wird im Heimnetz vom Container "vorschau" ausgeliefert und
spaeter unveraendert auf einen Webspace hochgeladen (B12).
"""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.generator.daten import baue
from loipen.generator.icons import png_icon
from loipen.konfig import CONFIG_DIR
from loipen.models import Quelle

STATIC = Path(__file__).parent / "static"
VORLAGEN = Path(__file__).parent / "vorlagen"
OSM_KACHELN = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap-Mitwirkende</a>'
HASH_LAENGE = 12
HINWEIS = "Alle Angaben ohne Gewähr. Quelle und Stand stehen bei jedem Wert."


def _schreibe(ziel: Path, inhalt: str | bytes) -> None:
    """Schreibt atomar, damit nginx nie eine halbe Datei ausliefert."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ziel.parent, prefix=".tmp-")
    with os.fdopen(fd, "wb") as f:
        f.write(inhalt.encode("utf-8") if isinstance(inhalt, str) else inhalt)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ziel)


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def hash_name(ordner: str, slug: str, inhalt: str) -> str:
    """B21: Dateiname mit Inhalts-Hash. Gleiche Daten ergeben den gleichen Namen."""
    h = hashlib.sha256(inhalt.encode("utf-8")).hexdigest()[:HASH_LAENGE]
    return f"{ordner}/{slug}.{h}.json"


def _host(url: str | None) -> str:
    from urllib.parse import urlparse
    return urlparse(url).hostname or "" if url else ""


def rechtliches_fehlt(r: dict) -> list[str]:
    """B6 AK 3: Was im Impressum noch fehlt. Leer heisst: vollstaendig."""
    return [feld for feld, wert in (("Name", r.get("name")), ("Anschrift", r.get("anschrift")),
                                    ("E-Mail", r.get("email"))) if not wert]


def erzeuge(
    session: Session,
    site_dir: str | Path,
    jetzt: datetime | None = None,
    config_dir: str | Path | None = None,
    stale_days: int = 7,
    rechtliches: dict | None = None,
    oeffentlich: bool = False,
    kacheln: dict | None = None,
    abo_dateien: dict[str, bytes] | None = None,
) -> list[Path]:
    """Schreibt die Seite. rechtliches: name, anschrift (Zeilen mit "|" getrennt), email, hoster,
    log_tage, datenschutz_html. kacheln: url, attribution, fremd (B23).
    abo_dateien: Ordner abo/ fuer E-Mail-Abo und Meldungen (E-18), siehe generator/abo.py."""
    site = Path(site_dir)
    jetzt = jetzt or datetime.now(ZoneInfo("Europe/Berlin"))
    daten = baue(session, jetzt, Path(config_dir) if config_dir else CONFIG_DIR, stale_days)
    stand = jetzt.astimezone(ZoneInfo("Europe/Berlin")).strftime("%Y%m%d%H%M")
    r = dict(rechtliches or {})
    kacheln = kacheln or {"url": OSM_KACHELN, "attribution": OSM_ATTRIBUTION, "fremd": True}

    geschrieben: list[Path] = []

    def schreibe(rel: str, inhalt: str | bytes) -> None:
        _schreibe(site / rel, inhalt)
        geschrieben.append(site / rel)

    # B21: zuerst die Daten mit Inhalts-Hash, der Index (daten.json) verweist erst danach auf sie
    index = daten["index"]
    for eintrag in index["regionen"]:
        slug = eintrag["slug"]
        for feld, ordner, inhalt in (("datei", "daten", _json(daten["regionen"][slug])),
                                     ("strecken", "strecken", _json(daten["strecken"][slug]))):
            eintrag[feld] = hash_name(ordner, slug, inhalt)
            schreibe(eintrag[feld], inhalt)
    index["kacheln"] = kacheln
    index["abo"] = bool(abo_dateien)  # N5: Formulare nur, wenn der Webspace sie annimmt

    for quelle in sorted(STATIC.rglob("*")):
        if quelle.is_file():
            rel = quelle.relative_to(STATIC).as_posix()
            inhalt = quelle.read_bytes()
            if rel in ("index.html", "sw.js"):
                inhalt = inhalt.replace(b"__STAND__", stand.encode())  # neue Version -> Cache erneuern
                if rel == "index.html" and not oeffentlich:
                    inhalt = inhalt.replace(b"<title>", b'<meta name="robots" content="noindex, nofollow">\n<title>', 1)
            schreibe(rel, inhalt)
    schreibe("icon-192.png", png_icon(192))
    schreibe("icon-512.png", png_icon(512))

    # B6, B16, B25, B24: Textseiten, Server-Konfiguration, robots.txt
    env = Environment(loader=FileSystemLoader(VORLAGEN), autoescape=select_autoescape(["j2"]),
                      trim_blocks=True, lstrip_blocks=True)
    anschrift = [z.strip() for z in (r.get("anschrift") or "").split("|") if z.strip()]
    quellen = [{"name": q.name, "url": q.base_url, "host": _host(q.base_url)}
               for q in session.scalars(select(Quelle).where(Quelle.enabled).order_by(Quelle.name))]
    werte = {"name": r.get("name"), "anschrift": anschrift, "email": r.get("email"), "hoster": r.get("hoster"),
             "log_tage": r.get("log_tage") or 7, "statistik_logs": bool(r.get("statistik_logs")),
             "kacheln_fremd": kacheln.get("fremd", True), "quellen": quellen,
             "fehlt": rechtliches_fehlt(r), "abo": bool(abo_dateien),
             "eigener_text": Markup(r["datenschutz_html"]) if r.get("datenschutz_html") else None}
    for name, titel, base in (("impressum", "Impressum", None), ("datenschutz", "Datenschutz", None),
                              ("hinweise", "Hinweise und Betreiber", None), ("404", "Nicht gefunden", "/")):
        inhalt = Markup(env.get_template(f"{name}.html.j2").render(**werte))
        schreibe(f"{name}.html", env.get_template("seite.html.j2").render(
            titel=titel, inhalt=inhalt, stand=stand, oeffentlich=oeffentlich, base=base))
    bild_hosts = [f"https://{_host(kacheln['url'])}"] if kacheln.get("fremd", True) else []
    schreibe(".htaccess", env.get_template("htaccess.j2").render(oeffentlich=oeffentlich, bild_hosts=bild_hosts))
    if abo_dateien:
        for rel, inhalt in abo_dateien.items():
            schreibe(rel, inhalt)
    elif (site / "abo").is_dir():
        shutil.rmtree(site / "abo")  # Abo abgeschaltet: keine verwaisten Skripte in der Vorschau
    schreibe("robots.txt", "User-agent: *\n" + ("Allow: /\n" if oeffentlich else "Disallow: /\n"))

    schreibe("daten.json", _json(index))  # zuletzt: erst jetzt sieht die Vorschau den neuen Stand

    # Dateien frueherer Laeufe, die es nicht mehr gibt (alte Hash-Namen, entfernte Regionen), aufraeumen
    for unterordner in ("daten", "strecken"):
        for datei in (site / unterordner).glob("*.json"):
            if datei not in geschrieben:
                datei.unlink()
    return geschrieben
