"""Statische Website (E-10, B7).

Der Generator schreibt nach settings.site_dir: die App (HTML, JS, CSS, PWA-Dateien) aus
loipen/generator/static und die Daten als JSON (Index, je Region eine Datei, je Region die
Strecken). Genau dieser Ordner wird im Heimnetz vom Container "vorschau" ausgeliefert und
spaeter unveraendert auf einen Webspace hochgeladen (B12).
"""

import hashlib
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.generator import seiten as seiten_mod
from loipen.generator.daten import baue, sichtbar
from loipen.generator.icons import png_icon
from loipen.konfig import CONFIG_DIR
from loipen.models import Quelle
from loipen.statistik import baue_statistik, beispiel_statistik

STATIC = Path(__file__).parent / "static"
VORLAGEN = Path(__file__).parent / "vorlagen"
OSM_KACHELN = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap-Mitwirkende</a>'
HASH_LAENGE = 12
log = logging.getLogger(__name__)
HINWEIS = "Alle Angaben ohne Gewähr. Quelle und Stand stehen bei jedem Wert."

# B30 AK 5: Kopfzeile der Testversion (LOIPEN_OEFFENTLICH=false)
TESTBAND = ('<p class="testband" id="testband" role="note"><b>Testversion, nur Test, nicht öffentlich.</b> Hier stehen auch Gebiete, die die öffentliche Seite nicht zeigt.</p>')


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


def app_version() -> str:
    """U41: Version der App aus dem Inhalt ihrer Dateien. Sie aendert sich nur, wenn sich App, Vorlagen
    oder Symbole aendern, nicht bei jedem Datenstand. So laedt das Handy die App nicht stuendlich neu."""
    h = hashlib.sha256()
    for ordner in (STATIC, VORLAGEN, Path(__file__).with_name("icons.py")):
        for datei in sorted(ordner.rglob("*")) if ordner.is_dir() else [ordner]:
            if datei.is_file():
                h.update(datei.relative_to(STATIC.parent).as_posix().encode())
                h.update(datei.read_bytes())
    return h.hexdigest()[:HASH_LAENGE]


def rechtliches_fehlt(r: dict) -> list[str]:
    """B6 AK 3: Was im Impressum noch fehlt. Leer heisst: vollstaendig."""
    return [feld for feld, wert in (("Name", r.get("name")), ("Anschrift", r.get("anschrift")),
                                    ("E-Mail", r.get("email"))) if not wert]


SPENDEN_ANBIETER = (("paypal.me", "PayPal"), ("paypal.com", "PayPal"), ("buymeacoffee.com", "Buy Me a Coffee"),
                    ("ko-fi.com", "Ko-fi"), ("liberapay.com", "Liberapay"))


def spenden(url: str | None) -> dict | None:
    """U46/E-28: Spendenlink aus LOIPEN_SPENDEN_URL. Nur https-Adressen, sonst nichts (mit Warnung im Log)."""
    url = (url or "").strip()
    if not url:
        return None
    teile = urlparse(url)
    if teile.scheme != "https" or not teile.hostname or any(z in url for z in "\"<>'` \t\r\n"):
        log.warning("LOIPEN_SPENDEN_URL ist keine gueltige https-Adresse, kein Spendenlink: %r", url)
        return None
    host = teile.hostname.lower().removeprefix("www.")
    anbieter = next((name for domain, name in SPENDEN_ANBIETER if host == domain or host.endswith("." + domain)), host)
    return {"url": url, "anbieter": anbieter}


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
    version: str | None = None,
    unplausibel: set[int] | None = None,
    push: dict | None = None,
    zaehler_dateien: dict[str, bytes] | None = None,
    basis_url: str | None = None,
) -> list[Path]:
    """Schreibt die Seite. rechtliches: name, anschrift (Zeilen mit "|" getrennt), email, hoster,
    log_tage, datenschutz_html, spenden_url. kacheln: url, attribution, fremd (B23).
    abo_dateien: Ordner abo/ fuer E-Mail-Abo und Meldungen (E-18), siehe generator/abo.py.
    unplausibel: wird mit den Loipen gefuellt, deren Offen-Meldung unplausibel ist (D19 AK 5).
    push: server und praefix der oeffentlichen ntfy-Themen (N10), sonst kein Push-Hinweis auf der Seite.
    zaehler_dateien: Ordner zaehler/ fuer den Besucherzaehler (B13, E-42), siehe generator/zaehler.py.
    basis_url: oeffentliche Adresse (LOIPEN_OEFFENTLICHE_URL) fuer Canonical, Sitemap und IndexNow (B17)."""
    site = Path(site_dir)
    jetzt = jetzt or datetime.now(ZoneInfo("Europe/Berlin"))
    daten = baue(session, jetzt, Path(config_dir) if config_dir else CONFIG_DIR, stale_days, oeffentlich=oeffentlich)
    if unplausibel is not None:
        unplausibel.update(daten["unplausibel"])
    stand = app_version()
    basis = basis_url.rstrip("/") if basis_url else None
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
    spende = spenden(r.get("spenden_url"))
    if spende:  # U46 AK 1: ohne Adresse kein Eintrag, die App zeigt dann nichts
        index["spenden"] = spende
    index["abo"] = bool(abo_dateien)  # N5: Formulare nur, wenn der Webspace sie annimmt
    index["push"] = push or None  # N10: ntfy-Themen je Loipe und Gebiet
    index["zaehler"] = bool(zaehler_dateien)  # B13: die App meldet Aufrufe nur, wenn der Webspace sie zaehlt
    if version:  # B4: Stand des Images in der Fusszeile, damit ein Update am NAS pruefbar ist
        index["image"] = version[:7] if len(version) == 40 else version

    # U19, U37-U39: Saisonstatistik und erfundener Beispielwinter, ebenfalls mit Inhalts-Hash
    index["statistik"] = {}
    for feld, inhalt in (("datei", _json(baue_statistik(session, daten, jetzt))),
                         ("beispiel", _json(beispiel_statistik(session, daten, jetzt)))):
        index["statistik"][feld] = hash_name("statistik", "statistik" if feld == "datei" else "beispiel", inhalt)
        schreibe(index["statistik"][feld], inhalt)

    for quelle in sorted(STATIC.rglob("*")):
        if quelle.is_file():
            rel = quelle.relative_to(STATIC).as_posix()
            inhalt = quelle.read_bytes()
            if rel in ("index.html", "sw.js"):
                inhalt = inhalt.replace(b"__STAND__", stand.encode())  # neue App-Version -> Cache erneuern
                if rel == "index.html" and not oeffentlich:
                    inhalt = inhalt.replace(b"<title>", b'<meta name="robots" content="noindex, nofollow">\n<title>', 1)
                    # B30 AK 5: sichtbarer Hinweis, dass dies die Testversion ist
                    inhalt = inhalt.replace(b'<header class="top">', TESTBAND.encode() + b'\n<header class="top">', 1)
                if rel == "index.html" and basis:  # B17 AK 6: Startseite mit Canonical und WebSite-Angabe
                    kopf = (f'<link rel="canonical" href="{basis}/">\n<script type="application/ld+json">'
                            + seiten_mod._jsonld({"@context": "https://schema.org", "@type": "WebSite",
                                                  "name": "Loipenblick", "url": basis + "/", "inLanguage": "de"})
                            + "</script>\n</head>")
                    inhalt = inhalt.replace(b"</head>", kopf.encode(), 1)
            schreibe(rel, inhalt)
    schreibe("icon-192.png", png_icon(192))
    schreibe("icon-512.png", png_icon(512))
    schreibe("icon-maskable-512.png", png_icon(512, rand=0.14))  # U40: Android schneidet rund zu
    schreibe("icon-180.png", png_icon(180))  # U40: iPhone (apple-touch-icon)

    # B6, B16, B25, B24: Textseiten, Server-Konfiguration, robots.txt
    env = Environment(loader=FileSystemLoader(VORLAGEN), autoescape=select_autoescape(["j2"]),
                      trim_blocks=True, lstrip_blocks=True)
    anschrift = [z.strip() for z in (r.get("anschrift") or "").split("|") if z.strip()]
    quellen = [{"name": q.name, "url": q.base_url, "host": _host(q.base_url)}
               for q in session.scalars(select(Quelle).where(Quelle.enabled).order_by(Quelle.name))
               if sichtbar(q, oeffentlich)]
    werte = {"name": r.get("name"), "anschrift": anschrift, "email": r.get("email"), "hoster": r.get("hoster"),
             "log_tage": r.get("log_tage") or 7, "statistik_logs": bool(r.get("statistik_logs")),
             "kacheln_fremd": kacheln.get("fremd", True), "quellen": quellen,
             "fehlt": rechtliches_fehlt(r), "abo": bool(abo_dateien), "spenden": spende,
             "push": push or None, "zaehler": bool(zaehler_dateien),
             "eigener_text": Markup(r["datenschutz_html"]) if r.get("datenschutz_html") else None}
    for name, titel, base in (("impressum", "Impressum", None), ("datenschutz", "Datenschutz", None),
                              ("hinweise", "Hinweise und Betreiber", None), ("404", "Nicht gefunden", "/")):
        inhalt = Markup(env.get_template(f"{name}.html.j2").render(**werte))
        schreibe(f"{name}.html", env.get_template("seite.html.j2").render(
            titel=titel, inhalt=inhalt, stand=stand, oeffentlich=oeffentlich, base=base, spenden=spende,
            testband=Markup(TESTBAND)))
    bild_hosts = [f"https://{_host(kacheln['url'])}"] if kacheln.get("fremd", True) else []
    schreibe(".htaccess", env.get_template("htaccess.j2").render(oeffentlich=oeffentlich, bild_hosts=bild_hosts))
    if abo_dateien:
        for rel, inhalt in abo_dateien.items():
            schreibe(rel, inhalt)
    elif (site / "abo").is_dir():
        shutil.rmtree(site / "abo")  # Abo abgeschaltet: keine verwaisten Skripte in der Vorschau
    if zaehler_dateien:
        for rel, inhalt in zaehler_dateien.items():
            schreibe(rel, inhalt)
    elif (site / "zaehler").is_dir():
        shutil.rmtree(site / "zaehler")
    # B17: eigene Seiten je Gebiet und Loipe, Sitemap, robots.txt, IndexNow-Schluessel
    alter_stand = {}
    if (site / seiten_mod.STAND_DATEI).exists():
        try:
            alter_stand = json.loads((site / seiten_mod.STAND_DATEI).read_text(encoding="utf-8"))
        except ValueError:
            alter_stand = {}
    inhalte: dict[str, str] = {}
    indexiert: list[str] = []
    fehlerhafte = 0
    for s in seiten_mod.baue_seiten(daten, basis):
        try:
            inhalt = Markup(env.get_template(s["vorlage"]).render(**s["werte"]))
        except Exception:  # B34: eine kaputte Einzelseite darf weder den Lauf noch die Startseite verhindern
            fehlerhafte += 1
            if fehlerhafte <= 3:
                log.exception("Seite %s nicht erzeugt, die alte bleibt stehen", s["pfad"])
            alt = site / s["pfad"] / "index.html"
            if alt.is_file():
                inhalte[s["pfad"]] = alt.read_text(encoding="utf-8")
                if s["index"]:
                    indexiert.append(s["pfad"])
            continue
        krumen = [("Loipenblick", "./#/"), ("Alle Gebiete", "gebiete/")]
        if s["vorlage"] == "gebiet.html.j2":
            krumen.append((s["werte"]["g"]["name"], s["pfad"]))
        elif s["vorlage"] == "loipe.html.j2":
            krumen += [(s["werte"]["g"]["name"], s["werte"]["gpfad"]), (s["h1"], s["pfad"])]
        else:
            krumen = krumen[:1] + [("Alle Gebiete", s["pfad"])]
        html = env.get_template("seite.html.j2").render(
            titel=s["h1"], kopf_titel=s["titel"], beschreibung=s["beschreibung"], inhalt=inhalt, stand=stand,
            oeffentlich=oeffentlich, base="/", spenden=spende, testband=Markup(TESTBAND), krumen=krumen,
            robots=None if s["index"] else "noindex, follow", seitenart="einzelseite",
            canonical=f"{basis}/{s['pfad']}" if basis and s["index"] else None,
            jsonld=[Markup(j) for j in s["jsonld"]])
        schreibe(s["pfad"] + "index.html", html)
        inhalte[s["pfad"]] = html
        if s["index"]:
            indexiert.append(s["pfad"])
    if fehlerhafte:
        log.error("%d Einzelseiten nicht erzeugt (Fehler in der Vorlage)", fehlerhafte)
    neuer_stand = seiten_mod.lastmod(alter_stand, inhalte, jetzt.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat())
    for pfad in set(alter_stand) - set(neuer_stand):  # entfallene Seiten auch in der Vorschau entfernen
        alt = site / pfad / "index.html"
        if alt.is_file():
            alt.unlink()
            try:
                alt.parent.rmdir()
                alt.parent.parent.rmdir() if pfad.count("/") > 1 else None
            except OSError:
                pass
    _schreibe(site / seiten_mod.STAND_DATEI, _json(neuer_stand))
    if basis:
        heute = jetzt.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat()
        start = [("", heute)]  # Startseite aendert sich mit jedem Stand
        schreibe("sitemap.xml", seiten_mod.sitemap(basis, start + [(p, neuer_stand[p][1]) for p in indexiert]))
        if oeffentlich:
            schluessel = seiten_mod.indexnow_schluessel(basis)
            schreibe(f"{schluessel}.txt", schluessel)
    elif (site / "sitemap.xml").exists():
        (site / "sitemap.xml").unlink()
    schreibe("robots.txt", seiten_mod.robots(oeffentlich, basis))

    schreibe("daten.json", _json(index))  # zuletzt: erst jetzt sieht die Vorschau den neuen Stand

    # Dateien frueherer Laeufe, die es nicht mehr gibt (alte Hash-Namen, entfernte Regionen), aufraeumen
    for unterordner in ("daten", "strecken", "statistik"):
        for datei in (site / unterordner).glob("*.json"):
            if datei not in geschrieben:
                datei.unlink()
    return geschrieben
