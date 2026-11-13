"""Livegang (docs/livegang.md): Upload in zwei Phasen, Textseiten, Server-Konfiguration."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from loipen import generator
from loipen.models import Quelle
from loipen.upload import (
    FREIGABE, OrdnerZiel, UploadFehler, freigegeben, lade_hoch, oeffne_ziel, pruefe_oeffentlich,
    upload_meldung, veroeffentliche,
)
from loipen.worker import __main__ as worker
from tests.helpers import lade_alle_fixtures

BERLIN = ZoneInfo("Europe/Berlin")
JETZT = datetime(2026, 12, 10, 8, 0, tzinfo=BERLIN)
RECHT = {"name": "Erika Muster", "anschrift": "Musterweg 1|83700 Rottach-Egern", "email": "kontakt@example.org",
         "hoster": "Beispiel Hosting GmbH"}


@pytest.fixture
def site(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    ziel = tmp_path / "site"
    generator.erzeuge(session, ziel, JETZT, rechtliches=RECHT)
    return ziel


def lies(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


class Einstellungen:
    upload_url = "file:///unbenutzt"
    upload_passwort = None
    upload_schluessel = None
    upload_known_hosts = None
    oeffentliche_url = None
    upload_wartezeiten_s = "0,0"
    heartbeat_url = None


class Abbruch(OrdnerZiel):
    """Bricht nach n Schreibvorgaengen ab, wie eine abgerissene Verbindung."""

    def __init__(self, ordner, n):
        super().__init__(ordner)
        self.n = n

    def schreibe(self, rel, inhalt):
        if self.n == 0:
            raise ConnectionError("Verbindung abgebrochen")
        self.n -= 1
        super().schreibe(rel, inhalt)


# ---------- Generator ----------

@pytest.mark.req("B21")
def test_b21_daten_dateien_tragen_inhalts_hash_und_index_verweist_darauf(site):
    index = lies(site / "daten.json")
    for r in index["regionen"]:
        assert r["datei"].startswith(f"daten/{r['slug']}.") and len(r["datei"].split(".")[-2]) == 12
        assert (site / r["datei"]).exists() and (site / r["strecken"]).exists()
    # keine Dateien ohne Hash mehr im Datenordner
    assert all(len(p.name.split(".")) == 3 for p in (site / "daten").glob("*.json"))


@pytest.mark.req("B21")
def test_b21_gleiche_daten_gleicher_name_alte_hashes_lokal_weg(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    generator.erzeuge(session, tmp_path, JETZT)
    vorher = sorted(p.name for p in (tmp_path / "daten").glob("*.json"))
    generator.erzeuge(session, tmp_path, JETZT)
    assert sorted(p.name for p in (tmp_path / "daten").glob("*.json")) == vorher


@pytest.mark.req("B6", ak=[3, 4])
def test_b6_impressum_und_datenschutz_aus_der_konfiguration(site):
    impressum = (site / "impressum.html").read_text(encoding="utf-8")
    assert "Erika Muster" in impressum and "Musterweg 1<br>83700 Rottach-Egern" in impressum
    assert "§ 18 Abs. 1 MStV" in impressum and "kontakt@example.org" in impressum
    ds = (site / "datenschutz.html").read_text(encoding="utf-8")
    for wort in ("Server-Protokolle", "Beispiel Hosting GmbH", "Karte", "Standort", "localStorage",
                 "Links zu anderen Seiten", "beschweren", "Auftragsverarbeitung"):
        assert wort in ds, wort


@pytest.mark.req("B6", ak=3)
def test_b6_ohne_angaben_meldet_das_impressum_was_fehlt(session, tmp_path):
    generator.erzeuge(session, tmp_path, JETZT)
    assert "noch nicht ausgefüllt" in (tmp_path / "impressum.html").read_text(encoding="utf-8")
    assert generator.rechtliches_fehlt({}) == ["Name", "Anschrift", "E-Mail"]
    assert generator.rechtliches_fehlt(RECHT) == []


def test_b6_eigener_datenschutztext_ersetzt_die_vorlage(session, tmp_path):
    generator.erzeuge(session, tmp_path, JETZT, rechtliches={**RECHT, "datenschutz_html": "<p>Mein Text</p>"})
    ds = (tmp_path / "datenschutz.html").read_text(encoding="utf-8")
    assert "<p>Mein Text</p>" in ds and "Server-Protokolle" not in ds


@pytest.mark.req("B6", ak=5)
def test_b6_quellenvermerke_der_wetterdienste(site):
    h = (site / "hinweise.html").read_text(encoding="utf-8")
    assert "Quelle: Deutscher Wetterdienst" in h
    assert "Datenquelle: GeoSphere Austria - <a href=\"https://data.hub.geosphere.at\"" in h


@pytest.mark.req("B25", ak=2)
def test_b25_hinweise_nennen_die_vier_punkte(site):
    h = (site / "hinweise.html").read_text(encoding="utf-8")
    for punkt in ("Der Status kann veraltet sein", "Vor Ort gilt die Beschilderung", "Benutzung auf eigene Gefahr",
                  "Loipengebühren beachten"):
        assert punkt in h


@pytest.mark.req("B16", ak=1)
def test_b16_seite_fuer_betreiber_listet_quellen_mit_link(session, site):
    h = (site / "hinweise.html").read_text(encoding="utf-8")
    assert "Für Gemeinden und Loipenbetreiber" in h and "kontakt@example.org" in h
    for q in session.scalars(select(Quelle).where(Quelle.enabled)):
        assert q.name in h and q.base_url in h


@pytest.mark.req("B16", ak=2)
def test_b16_abgeschaltete_quelle_verschwindet_von_der_seite(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    tegernsee = session.scalar(select(Quelle).where(Quelle.key == "tegernsee"))
    tegernsee.enabled = False
    session.flush()
    generator.erzeuge(session, tmp_path, JETZT)
    index = lies(tmp_path / "daten.json")
    quellen = {l["quelle"]["name"] for r in index["regionen"] for g in lies(tmp_path / r["datei"])["gebiete"]
               for l in g["loipen"]}
    assert tegernsee.name not in quellen and quellen
    assert tegernsee.name not in (tmp_path / "hinweise.html").read_text(encoding="utf-8")


@pytest.mark.req("B24", ak=3)
@pytest.mark.req("B20", ak=2)
def test_b24_htaccess_mit_https_sicherheits_und_cache_headern(site):
    h = (site / ".htaccess").read_text(encoding="utf-8")
    for teil in ("RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]", "Strict-Transport-Security",
                 "Content-Security-Policy \"default-src 'self'", "X-Content-Type-Options \"nosniff\"",
                 "Referrer-Policy \"strict-origin-when-cross-origin\"", "immutable", "ErrorDocument 404 /404.html",
                 "Options -Indexes", "img-src 'self' data: https://tile.openstreetmap.org"):
        assert teil in h, teil
    assert (site / "404.html").exists()


def test_vor_der_freigabe_nicht_fuer_suchmaschinen(session, tmp_path):
    generator.erzeuge(session, tmp_path / "test", JETZT)
    assert (tmp_path / "test/robots.txt").read_text() == "User-agent: *\nDisallow: /\n"
    assert 'name="robots" content="noindex' in (tmp_path / "test/index.html").read_text(encoding="utf-8")
    assert "X-Robots-Tag" in (tmp_path / "test/.htaccess").read_text(encoding="utf-8")
    generator.erzeuge(session, tmp_path / "live", JETZT, oeffentlich=True)
    assert "Allow: /" in (tmp_path / "live/robots.txt").read_text()
    assert "noindex" not in (tmp_path / "live/index.html").read_text(encoding="utf-8")
    assert "X-Robots-Tag" not in (tmp_path / "live/.htaccess").read_text(encoding="utf-8")


def test_b23_eigene_kacheln_ohne_fremden_host_in_der_csp(session, tmp_path):
    generator.erzeuge(session, tmp_path, JETZT, kacheln={"url": "kacheln/{z}/{x}/{y}.png", "attribution": "OSM",
                                                         "fremd": False})
    assert lies(tmp_path / "daten.json")["kacheln"]["fremd"] is False
    assert "img-src 'self' data:;" in (tmp_path / ".htaccess").read_text(encoding="utf-8")


# ---------- Upload ----------

@pytest.mark.req("B24", ak=[1, 2])
def test_b24_nur_freigegebene_dateien_gehen_hoch(site, tmp_path):
    (site / ".env").write_text("LOIPEN_UPLOAD_PASSWORT=geheim")
    (site / "loipen-20261210.dump").write_bytes(b"x")
    (site / ".tmp-rest").write_text("x")
    server = tmp_path / "server"
    erg = lade_hoch(site, OrdnerZiel(server))
    oben = {p.relative_to(server).as_posix() for p in server.rglob("*") if p.is_file()}
    assert ".env" not in oben and "loipen-20261210.dump" not in oben and ".tmp-rest" not in oben
    assert {".env", "loipen-20261210.dump", ".tmp-rest"} <= set(erg.ausgelassen)
    assert ".htaccess" in oben and "index.html" in oben
    assert all(freigegeben(r) for r in oben if r != ".loipen-upload.json")
    # kein Rohtext der Quellen in den Daten
    for p in (site / "daten").glob("*.json"):
        assert '"rohtext"' not in p.read_text(encoding="utf-8")
    assert ".dump" not in FREIGABE


@pytest.mark.req("B21", ak=[1, 4])
def test_b21_abbruch_in_phase_1_laesst_den_alten_stand_vollstaendig(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    site = tmp_path / "site"
    server = tmp_path / "server"
    generator.erzeuge(session, site, JETZT)
    lade_hoch(site, OrdnerZiel(server))
    alt_index = (server / "daten.json").read_bytes()
    # neuer Stand mit anderen Daten
    generator.erzeuge(session, site, datetime(2026, 12, 12, 8, 0, tzinfo=BERLIN))
    assert (site / "daten.json").read_bytes() != alt_index
    with pytest.raises(ConnectionError):
        lade_hoch(site, Abbruch(server, n=1))
    # der Server zeigt weiter den alten Stand, und alles, worauf er verweist, ist da
    assert (server / "daten.json").read_bytes() == alt_index
    alt = json.loads(alt_index)
    for r in alt["regionen"]:
        assert (server / r["datei"]).exists() and (server / r["strecken"]).exists()
    # der naechste Lauf holt den Upload nach
    erg = lade_hoch(site, OrdnerZiel(server))
    assert (server / "daten.json").read_bytes() == (site / "daten.json").read_bytes()
    # Einstieg zuletzt; index.html und sw.js aendern sich nur mit der App (U38), nicht mit den Daten
    einstieg = [d for d in erg.hochgeladen if d in ("daten.json", "sw.js", "index.html")]
    assert erg.hochgeladen[-len(einstieg):] == einstieg and einstieg[0] == "daten.json"


@pytest.mark.req("B21")
def test_b21_aufraeumen_behaelt_den_vorigen_stand(session, tmp_path):
    lade_alle_fixtures(session, JETZT)
    site, server = tmp_path / "site", tmp_path / "server"
    staende = []
    for tag in (10, 11, 12):
        generator.erzeuge(session, site, datetime(2026, 12, tag, 8, 0, tzinfo=BERLIN))
        lade_hoch(site, OrdnerZiel(server))
        staende.append({r["datei"] for r in lies(site / "daten.json")["regionen"]})
    oben = {p.relative_to(server).as_posix() for p in (server / "daten").glob("*.json")}
    assert staende[2] | staende[1] <= {f"daten/{n.split('/')[-1]}" for n in oben}
    assert not (staende[0] - staende[1] - staende[2]) & oben


@pytest.mark.req("B21")
def test_b21_unveraenderte_dateien_werden_nicht_neu_geschickt(site, tmp_path):
    server = OrdnerZiel(tmp_path / "server")
    erst = lade_hoch(site, server)
    zweit = lade_hoch(site, server)
    assert len(erst.hochgeladen) > 10 and zweit.hochgeladen == [] and zweit.unveraendert == len(erst.hochgeladen)


@pytest.mark.req("B21", ak=2)
def test_b21_pruefung_ueber_die_oeffentliche_adresse(site):
    erzeugt = lies(site / "daten.json")["erzeugt"]
    pruefe_oeffentlich("https://loipen.example", erzeugt, lambda u: (site / "daten.json").read_bytes())
    with pytest.raises(UploadFehler, match="erwartet"):
        pruefe_oeffentlich("https://loipen.example", "2026-01-01T00:00+01:00",
                           lambda u: (site / "daten.json").read_bytes())


@pytest.mark.req("B21", ak=3)
@pytest.mark.req("B22", ak=1)
def test_b21_drei_versuche_dann_fehler_und_heartbeat_nur_bei_erfolg(site, tmp_path):
    ping, pausen = [], []
    s = Einstellungen()
    s.heartbeat_url = "https://hc-ping.example/geheim"
    versuche = []

    def kaputt(*a):
        versuche.append(1)
        raise ConnectionError("Server weg")
    with pytest.raises(UploadFehler, match="3 Versuchen"):
        veroeffentliche(s, site, oeffne=kaputt, schlafe=pausen.append, ping=ping.append)
    assert len(versuche) == 3 and pausen == [0, 0] and ping == []

    veroeffentliche(s, site, oeffne=lambda *a: OrdnerZiel(tmp_path / "server"), schlafe=pausen.append,
                    ping=ping.append)
    assert ping == ["https://hc-ping.example/geheim"]


@pytest.mark.req("B21", ak=3)
def test_b21_push_nur_beim_wechsel(tmp_path):
    datei = tmp_path / "upload-status.json"
    assert upload_meldung(datei, True, None) is None
    assert upload_meldung(datei, False, "weg")[0] == "Loipenblick: Upload fehlgeschlagen"
    assert upload_meldung(datei, False, "weg") is None
    assert upload_meldung(datei, True, None)[0] == "Loipenblick: Upload wieder in Ordnung"


@pytest.mark.req("B8", ak=3)
def test_b8_sftp_braucht_bekannten_server_und_zugang_kommt_aus_der_env(tmp_path):
    with pytest.raises(UploadFehler, match="known_hosts"):
        oeffne_ziel("sftp://loipen@webspace.example/html", "pw", None, str(tmp_path / "fehlt"))
    with pytest.raises(UploadFehler, match="Unbekanntes"):
        oeffne_ziel("ftp://loipen@webspace.example/html")
    env = Path(__file__).resolve().parent.parent / ".env.example"
    text = env.read_text(encoding="utf-8")
    assert "LOIPEN_UPLOAD_URL=\n" in text and "LOIPEN_UPLOAD_PASSWORT=\n" in text


@pytest.mark.req("B6", ak=3)
def test_b6_ohne_impressum_kein_upload(tmp_path, monkeypatch):
    s = Einstellungen()
    s.backup_dir = str(tmp_path)
    s.site_dir = str(tmp_path / "site")
    s.impressum_name = s.impressum_anschrift = s.impressum_email = s.hoster = s.datenschutz_datei = None
    s.log_tage = 7
    gerufen = []
    monkeypatch.setattr(worker, "veroeffentliche", lambda *a, **k: gerufen.append(1))
    titel, text = worker.hochladen(s)
    assert gerufen == [] and "Impressum unvollständig" in text
    s.impressum_name, s.impressum_anschrift, s.impressum_email = "Erika Muster", "Musterweg 1", "a@example.org"
    assert worker.hochladen(s)[0] == "Loipenblick: Upload wieder in Ordnung" and gerufen == [1]
