"""Auffindbarkeit (B17, E-44): eigene Seiten je Gebiet und Loipe, Sitemap, robots.txt, IndexNow."""

from markupsafe import escape as e
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from loipen import generator
from loipen.generator import seiten
from loipen.upload import (
    OrdnerZiel, geaenderte_seiten, lade_hoch, melde_indexnow, veroeffentliche,
)
from tests.helpers import lade_alle_fixtures

BERLIN = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 12, 10, 8, 0, tzinfo=BERLIN)
BASIS = "https://loipen-blick.de"
RECHT = {"name": "Erika Muster", "anschrift": "Musterweg 1|83700 Rottach-Egern", "email": "kontakt@example.org",
         "hoster": "Beispiel Hosting GmbH"}


@pytest.fixture
def live(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    ziel = tmp_path / "live"
    generator.erzeuge(session, ziel, JETZT, rechtliches=RECHT, oeffentlich=True, basis_url=BASIS)
    if os.environ.get("LOIPEN_SEO_AUSGABE"):  # zum Ansehen: Seite in einen festen Ordner kopieren
        shutil.copytree(ziel, os.environ["LOIPEN_SEO_AUSGABE"], dirs_exist_ok=True)
    return session, ziel


def daten(site: Path) -> list[dict]:
    idx = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    return [json.loads((site / r["datei"]).read_text(encoding="utf-8")) for r in idx["regionen"]]


def html(site: Path, pfad: str) -> str:
    return (site / pfad / "index.html").read_text(encoding="utf-8")


def test_slug_und_reservierte_namen():
    assert seiten.slug("Loipe Kreuth – Wildbad Kreuth") == "loipe-kreuth-wildbad-kreuth"
    assert seiten.slug("Gößweinstein Höhenloipe") == "goessweinstein-hoehenloipe"
    assert seiten.slug("Rundkurs (3,5 km)") == "rundkurs-3-5-km"
    assert seiten.gebiet_pfad("statistik") == "statistik-loipen"  # kein Zusammenstoss mit Ordnern der App
    assert seiten.gebiet_pfad("tegernsee") == "tegernsee"


@pytest.mark.req("B17", ak=[1, 2, 6, 8])
def test_b17_seite_je_gebiet_und_loipe_mit_inhalt_im_html(live):
    _, site = live
    regionen = daten(site)
    gebiete = [g for r in regionen for g in r["gebiete"] if g["loipen"]]
    g_pfad, l_pfad = seiten.adressen({r["region"]["slug"]: r for r in regionen})
    assert len(set(l_pfad.values())) == len(l_pfad)  # AK 2: jede Adresse einmal
    titel = set()
    for g in gebiete:
        h = html(site, g_pfad[g["slug"]])
        assert f"<h1>Loipen in {e(g['name'])}</h1>" in h
        t = re.search(r"<title>([^<]+)</title>", h).group(1)
        assert t not in titel, t  # AK 1: eigener Titel
        titel.add(t)
        assert 'name="description"' in h
        assert f'href="{BASIS}/{g_pfad[g["slug"]]}"' in h  # AK 6: Canonical
        assert '"@type":"BreadcrumbList"' in h
        for l in g["loipen"]:
            assert f'href="{l_pfad[l["id"]]}"' in h  # interne Links Gebiet -> Loipe
        # AK 8: jede Quelle mit Link
        for q in {l["quelle"]["name"] for l in g["loipen"]}:
            assert e(q) in h
        assert "<script src" not in h  # AK 1: ohne JavaScript lesbar
    # eine Loipe im Detail: Status, Laenge und Quelle stehen im ausgelieferten HTML
    l = next(l for g in gebiete for l in g["loipen"] if l.get("laenge_km") and l["quelle"].get("url"))
    h = html(site, l_pfad[l["id"]])
    assert e(l["name"]) in h
    assert seiten.WORT[l["status"]] in h
    assert seiten._zahl(l["laenge_km"]) + " km" in h
    assert e(l["quelle"]["url"]) in h
    assert f'href="./#/loipe/{l["id"]}"' in h  # in die App mit Karte und Benachrichtigung
    # Uebersicht verlinkt alle Gebiete, Start- und Textseiten verlinken die Uebersicht
    ueb = html(site, "gebiete/")
    assert all(f'href="{g_pfad[g["slug"]]}"' in ueb for g in gebiete)
    assert 'href="gebiete/"' in (site / "index.html").read_text(encoding="utf-8")
    assert 'href="gebiete/"' in (site / "impressum.html").read_text(encoding="utf-8")
    start = (site / "index.html").read_text(encoding="utf-8")
    assert f'<link rel="canonical" href="{BASIS}/">' in start and '"@type":"WebSite"' in start


@pytest.mark.req("B17", ak=[2, 3, 7, 9])
def test_b17_adressen_bleiben_gleich_und_nur_aenderungen_gehen_hoch(live, tmp_path):
    session, site = live
    karte1 = (site / "sitemap.xml").read_text(encoding="utf-8")
    ziel = OrdnerZiel(tmp_path / "server")
    lade_hoch(site, ziel)
    # zweiter Lauf am naechsten Tag mit denselben Daten: gleiche Adressen, gleiches lastmod, nichts Neues
    generator.erzeuge(session, site, JETZT + timedelta(days=1), rechtliches=RECHT, oeffentlich=True, basis_url=BASIS)
    karte2 = (site / "sitemap.xml").read_text(encoding="utf-8")
    weg = lambda k: re.sub(r"<url><loc>https://loipen-blick.de/</loc><lastmod>[^<]+</lastmod></url>", "", k)  # noqa: E731
    assert weg(karte1) == weg(karte2)  # AK 3: lastmod nur bei echter Aenderung
    erg = lade_hoch(site, ziel)
    assert not [r for r in erg.hochgeladen if r.endswith("/index.html")]  # AK 9
    # AK 7: Seite einer entfallenen Loipe verschwindet auf dem Server, .htaccess leitet auf das Gebiet weiter
    stand = json.loads((site / seiten.STAND_DATEI).read_text(encoding="utf-8"))
    loipe = next(p for p in stand if p.count("/") == 2)
    alt = tmp_path / "server" / loipe / "index.html"
    assert alt.exists()
    (site / loipe / "index.html").unlink()
    erg = lade_hoch(site, ziel)
    assert loipe + "index.html" in erg.geloescht and not alt.exists()
    ht = (site / ".htaccess").read_text(encoding="utf-8")
    assert "RewriteRule ^([a-z0-9-]+)/([a-z0-9-]+)/?$ /$1/ [R=301,L]" in ht


@pytest.mark.req("B17", ak=[3, 4, 5])
def test_b17_sitemap_robots_und_duenne_seiten(live):
    _, site = live
    regionen = daten(site)
    g_pfad, l_pfad = seiten.adressen({r["region"]["slug"]: r for r in regionen})
    karte = (site / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", karte)
    assert f"{BASIS}/" in locs and f"{BASIS}/gebiete/" in locs
    mit = {g["slug"] for r in regionen for g in r["gebiete"] if g["loipen"]}
    assert all(f"{BASIS}/{p}" in locs for g, p in g_pfad.items() if g in mit)  # AK 3: alle Gebiete
    loipen = [l for r in regionen for g in r["gebiete"] for l in g["loipen"]]
    duenn = [l for l in loipen if not seiten.indexierbar(l)]
    voll = [l for l in loipen if seiten.indexierbar(l)]
    assert duenn and voll  # in den Fixtures gibt es beides
    for l in voll:
        assert f"{BASIS}/{l_pfad[l['id']]}" in locs
    for l in duenn:  # AK 4: noindex, nicht in der Sitemap, aber erreichbar
        assert f"{BASIS}/{l_pfad[l['id']]}" not in locs
        h = html(site, l_pfad[l["id"]])
        assert '<meta name="robots" content="noindex, follow">' in h and 'rel="canonical"' not in h
    robots = (site / "robots.txt").read_text(encoding="utf-8")
    assert f"Sitemap: {BASIS}/sitemap.xml" in robots
    blocks = robots.split("\n\n")
    training = next(b for b in blocks if "User-agent: GPTBot" in b)
    assert "Disallow: /" in training and "User-agent: ClaudeBot" in training and "Google-Extended" in training
    alle = next(b for b in blocks if "User-agent: *" in b)
    assert "Allow: /" in alle  # AK 5: Such-Bots (auch OAI-SearchBot, PerplexityBot) duerfen
    assert "OAI-SearchBot" not in training and "PerplexityBot" not in training


@pytest.mark.req("B17", ak=[8])
def test_b17_testversion_ohne_index_und_ohne_gesperrte_quellen(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    test, live = tmp_path / "test", tmp_path / "live"
    generator.erzeuge(session, test, JETZT, rechtliches=RECHT, oeffentlich=False, basis_url="https://test.loipen-blick.de")
    generator.erzeuge(session, live, JETZT, rechtliches=RECHT, oeffentlich=True, basis_url=BASIS)
    assert (test / "robots.txt").read_text() == "User-agent: *\nDisallow: /\n"
    seite = next(p for p in test.glob("*/index.html") if p.parent.name != "gebiete")
    assert '<meta name="robots" content="noindex, nofollow">' in seite.read_text(encoding="utf-8")
    assert not list(test.glob("*.txt")) or {p.name for p in test.glob("*.txt")} == {"robots.txt"}  # kein IndexNow
    # nur_test-Gebiete (Achensee, E-43) gibt es auf der oeffentlichen Seite nicht, auch nicht in der Sitemap
    test_gebiete = {g["slug"] for r in daten(test) for g in r["gebiete"] if g.get("nur_test")}
    live_gebiete = {g["slug"] for r in daten(live) for g in r["gebiete"]}
    karte = (live / "sitemap.xml").read_text(encoding="utf-8")
    for s in test_gebiete:
        assert s not in live_gebiete
        assert not (live / seiten.gebiet_pfad(s) / "index.html").exists()
        assert f"/{seiten.gebiet_pfad(s)}/" not in karte


@pytest.mark.req("B17", ak=[10])
def test_b17_indexnow_meldet_nur_geaenderte_indexierte_seiten(live, tmp_path):
    _, site = live
    schluessel = seiten.indexnow_schluessel(BASIS)
    assert (site / f"{schluessel}.txt").read_text() == schluessel

    class E:
        upload_url = f"file://{tmp_path / 'server'}"
        upload_passwort = upload_schluessel = upload_known_hosts = heartbeat_url = None
        upload_wartezeiten_s = "0"
        oeffentliche_url = BASIS
        oeffentlich = True

    gesendet = []
    veroeffentliche(E, site, pruefe=lambda *a: None, indexnow=lambda url, d: gesendet.append((url, d)))
    assert len(gesendet) == 1
    url, d = gesendet[0]
    assert url == "https://api.indexnow.org/indexnow" and d["host"] == "loipen-blick.de" and d["key"] == schluessel
    assert d["keyLocation"] == f"{BASIS}/{schluessel}.txt"
    locs = set(re.findall(r"<loc>([^<]+)</loc>", (site / "sitemap.xml").read_text(encoding="utf-8")))
    assert set(d["urlList"]) <= locs and f"{BASIS}/gebiete/" in d["urlList"]
    # zweiter Upload ohne Aenderung: keine Meldung; ein Fehler bei IndexNow stoert den Upload nicht
    gesendet.clear()
    veroeffentliche(E, site, pruefe=lambda *a: None, indexnow=lambda url, d: gesendet.append(d))
    assert gesendet == []

    def kaputt(url, d):
        raise RuntimeError("offline")
    melde_indexnow(BASIS, [], kaputt)  # leere Liste: gar kein Aufruf
    (site / "gebiete" / "index.html").write_text("<p>neu</p>", encoding="utf-8")
    veroeffentliche(E, site, pruefe=lambda *a: None, indexnow=kaputt)  # wirft nicht


@pytest.mark.req("B17", ak=[9])
def test_b17_langsamer_upload_warnt(live, tmp_path, monkeypatch):
    _, site = live
    zeiten = iter([0.0, 400.0])

    class E:
        upload_url = f"file://{tmp_path / 'server'}"
        upload_passwort = upload_schluessel = upload_known_hosts = heartbeat_url = None
        upload_wartezeiten_s = "0"
        oeffentliche_url = None
        oeffentlich = False

    # direkt am Logger mitschreiben: andere Tests stellen die Log-Weitergabe um, caplog sieht dann nichts
    warnungen = []
    monkeypatch.setattr("loipen.upload.log.warning", lambda msg, *a: warnungen.append(msg % a))
    veroeffentliche(E, site, pruefe=lambda *a: None, uhr=lambda: next(zeiten))
    assert any("länger als 300 s" in w for w in warnungen)
    assert geaenderte_seiten(site, type("Erg", (), {"hochgeladen": []})(), BASIS) == []
