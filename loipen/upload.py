"""Upload der erzeugten Seite auf den Webspace (B8, B21, B22, B24).

Ablauf in zwei Phasen, damit Besucher nie einen halben Stand sehen:

1. Neue Daten-Dateien mit Inhalts-Hash (daten/, strecken/). Vorhandene Namen werden nicht neu
   geschrieben, weil gleicher Name gleicher Inhalt heisst.
2. Alle anderen Dateien, jeweils unter einem temporaeren Namen und dann per Umbenennen.
   daten.json, index.html und sw.js kommen ganz zum Schluss: erst jetzt sieht ein Besucher den
   neuen Stand.

Danach werden Hash-Dateien geloescht, auf die weder der neue noch der vorige Stand verweist.
Der Stand des letzten Uploads liegt als .loipen-upload.json auf dem Server (die .htaccess sperrt
versteckte Dateien). Nur das NAS baut Verbindungen auf.
"""

from __future__ import annotations

import ftplib
import hashlib
import io
import json
import logging
import posixpath
import re
import ssl
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import unquote, urlparse

log = logging.getLogger("loipen.upload")

STAND_DATEI = ".loipen-upload.json"
# B24 AK 1: nur diese Dateiarten gehen auf den Server
FREIGABE = {".html", ".css", ".js", ".json", ".png", ".svg", ".webmanifest", ".pmtiles", ".txt", ".ico"}
FREIGABE_NAMEN = {".htaccess"}
HASH_DATEI = re.compile(r"^(daten|strecken)/[^/]+\.[0-9a-f]{12}\.json$")
ZULETZT = ("daten.json", "sw.js", "index.html")  # Einstieg, in dieser Reihenfolge


class UploadFehler(Exception):
    pass


class Ziel(Protocol):
    def dateien(self) -> set[str]: ...
    def lies(self, rel: str) -> bytes | None: ...
    def schreibe(self, rel: str, inhalt: bytes) -> None: ...
    def benenne(self, von: str, nach: str) -> None: ...
    def loesche(self, rel: str) -> None: ...
    def schliesse(self) -> None: ...


@dataclass
class Ergebnis:
    hochgeladen: list[str] = field(default_factory=list)
    unveraendert: int = 0
    geloescht: list[str] = field(default_factory=list)
    ausgelassen: list[str] = field(default_factory=list)
    erzeugt: str | None = None


def freigegeben(rel: str) -> bool:
    name = posixpath.basename(rel)
    if name in FREIGABE_NAMEN:
        return True
    if any(teil.startswith(".") for teil in rel.split("/")):
        return False
    return posixpath.splitext(name)[1].lower() in FREIGABE


def _sha(inhalt: bytes) -> str:
    return hashlib.sha256(inhalt).hexdigest()


def _verweise(index: dict) -> set[str]:
    return {r[f] for r in index.get("regionen", []) for f in ("datei", "strecken") if r.get(f)}


def lade_hoch(site_dir: str | Path, ziel: Ziel) -> Ergebnis:
    """Laedt site_dir nach ziel. Wirft bei einem Fehler; der alte Stand bleibt dann vollstaendig."""
    site = Path(site_dir)
    erg = Ergebnis()
    lokal: dict[str, bytes] = {}
    for p in sorted(site.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(site).as_posix()
        if freigegeben(rel):
            lokal[rel] = p.read_bytes()
        else:
            erg.ausgelassen.append(rel)
    if "daten.json" not in lokal or "index.html" not in lokal:
        raise UploadFehler("Im Seitenordner fehlen daten.json oder index.html, nichts hochgeladen.")
    index = json.loads(lokal["daten.json"])
    erg.erzeugt = index.get("erzeugt")
    fehlende = _verweise(index) - lokal.keys()
    if fehlende:
        raise UploadFehler(f"daten.json verweist auf fehlende Dateien: {sorted(fehlende)[:3]}")

    vorher_roh = ziel.lies(STAND_DATEI)
    vorher = json.loads(vorher_roh) if vorher_roh else {"dateien": {}, "verweise": []}
    auf_server = ziel.dateien()

    # Phase 1: Hash-Dateien, die es auf dem Server noch nicht gibt
    for rel, inhalt in lokal.items():
        if HASH_DATEI.match(rel):
            if rel in auf_server:
                erg.unveraendert += 1
                continue
            ziel.schreibe(rel, inhalt)
            erg.hochgeladen.append(rel)

    # Phase 2: alles andere per temporaerem Namen und Umbenennen, der Einstieg zuletzt
    rest = [r for r in lokal if not HASH_DATEI.match(r) and r not in ZULETZT]
    for rel in rest + [r for r in ZULETZT if r in lokal]:
        inhalt = lokal[rel]
        if vorher["dateien"].get(rel) == _sha(inhalt) and rel in auf_server:
            erg.unveraendert += 1
            continue
        kopf, name = posixpath.split(rel)
        tmp = posixpath.join(kopf, f".tmp-{name}")
        ziel.schreibe(tmp, inhalt)
        ziel.benenne(tmp, rel)
        erg.hochgeladen.append(rel)

    # Stand merken, dann aufraeumen: alte Hash-Dateien des vorletzten Stands und fruehere Reste
    behalten = _verweise(index) | set(vorher.get("verweise", []))
    stand = {"erzeugt": erg.erzeugt, "verweise": sorted(_verweise(index)),
             "dateien": {r: _sha(i) for r, i in lokal.items() if not HASH_DATEI.match(r)}}
    ziel.schreibe(".tmp-" + STAND_DATEI, json.dumps(stand, ensure_ascii=False).encode())
    ziel.benenne(".tmp-" + STAND_DATEI, STAND_DATEI)
    for rel in sorted(ziel.dateien()):
        if HASH_DATEI.match(rel) and rel not in behalten:
            ziel.loesche(rel)
            erg.geloescht.append(rel)
    return erg


def pruefe_oeffentlich(url: str, erzeugt: str | None, abruf: Callable[[str], bytes] | None = None) -> None:
    """B21 AK 2: daten.json ueber die oeffentliche Adresse holen und den Stand vergleichen."""
    if abruf is None:
        import httpx

        def abruf(u: str) -> bytes:
            r = httpx.get(u, timeout=30, headers={"Cache-Control": "no-cache"}, follow_redirects=True)
            r.raise_for_status()
            return r.content
    roh = abruf(url.rstrip("/") + f"/daten.json?pruefung={int(time.time())}")
    online = json.loads(roh).get("erzeugt")
    if online != erzeugt:
        raise UploadFehler(f"Öffentliche Seite zeigt Stand {online}, erwartet {erzeugt}.")


# ---------- Ziele ----------

class OrdnerZiel:
    """Ein lokaler Ordner als Ziel: fuer Tests und fuer ein eingebundenes Netzlaufwerk."""

    def __init__(self, ordner: str | Path):
        self.ordner = Path(ordner)
        self.ordner.mkdir(parents=True, exist_ok=True)

    def dateien(self) -> set[str]:
        return {p.relative_to(self.ordner).as_posix() for p in self.ordner.rglob("*") if p.is_file()}

    def lies(self, rel):
        p = self.ordner / rel
        return p.read_bytes() if p.exists() else None

    def schreibe(self, rel, inhalt):
        p = self.ordner / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(inhalt)

    def benenne(self, von, nach):
        (self.ordner / von).replace(self.ordner / nach)

    def loesche(self, rel):
        (self.ordner / rel).unlink(missing_ok=True)

    def schliesse(self):
        pass


class SftpZiel:
    """SFTP mit Passwort oder Schluessel. Der Server muss in known_hosts stehen (kein blindes Vertrauen)."""

    def __init__(self, host, port, benutzer, pfad, passwort=None, schluessel=None, known_hosts=None):
        import paramiko

        self.pfad = pfad.rstrip("/") or "."
        self.client = paramiko.SSHClient()
        if not known_hosts or not Path(known_hosts).exists():
            raise UploadFehler("SFTP braucht eine known_hosts-Datei mit dem Fingerabdruck des Servers "
                               "(LOIPEN_UPLOAD_KNOWN_HOSTS).")
        self.client.load_host_keys(known_hosts)
        self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        self.client.connect(host, port=port, username=benutzer, password=passwort, key_filename=schluessel,
                            timeout=30, allow_agent=False, look_for_keys=False)
        self.sftp = self.client.open_sftp()
        self._ordner: set[str] = set()

    def _abs(self, rel):
        return posixpath.join(self.pfad, rel)

    def dateien(self) -> set[str]:
        import stat
        gefunden, offen = set(), [""]
        while offen:
            rel = offen.pop()
            for e in self.sftp.listdir_attr(self._abs(rel) if rel else self.pfad):
                r = posixpath.join(rel, e.filename) if rel else e.filename
                if stat.S_ISDIR(e.st_mode or 0):
                    offen.append(r)
                else:
                    gefunden.add(r)
        return gefunden

    def lies(self, rel):
        try:
            with self.sftp.open(self._abs(rel), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _mkdirs(self, rel_ordner):
        teile, aktuell = [t for t in rel_ordner.split("/") if t], self.pfad
        for t in teile:
            aktuell = posixpath.join(aktuell, t)
            if aktuell in self._ordner:
                continue
            try:
                self.sftp.stat(aktuell)
            except FileNotFoundError:
                self.sftp.mkdir(aktuell)
            self._ordner.add(aktuell)

    def schreibe(self, rel, inhalt):
        self._mkdirs(posixpath.dirname(rel))
        self.sftp.putfo(io.BytesIO(inhalt), self._abs(rel))

    def benenne(self, von, nach):
        self.sftp.posix_rename(self._abs(von), self._abs(nach))  # ersetzt atomar

    def loesche(self, rel):
        self.sftp.remove(self._abs(rel))

    def schliesse(self):
        self.client.close()


class FtpsZiel:
    """FTP ueber TLS (explizit), fuer Webspace ohne SSH. Umbenennen ersetzt je nach Server nicht,
    darum wird das Ziel vorher geloescht; die Luecke ist eine einzelne Datei lang."""

    def __init__(self, host, port, benutzer, pfad, passwort):
        self.ftp = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=60)
        self.ftp.connect(host, port or 21)
        self.ftp.login(benutzer, passwort or "")
        self.ftp.prot_p()
        self.pfad = pfad.rstrip("/") or "."

    def _abs(self, rel):
        return posixpath.join(self.pfad, rel)

    def dateien(self) -> set[str]:
        gefunden, offen = set(), [""]
        while offen:
            rel = offen.pop()
            for name, fakten in self.ftp.mlsd(self._abs(rel) if rel else self.pfad, facts=["type"]):
                if name in (".", ".."):
                    continue
                r = posixpath.join(rel, name) if rel else name
                (offen.append(r) if fakten.get("type") == "dir" else gefunden.add(r))
        return gefunden

    def lies(self, rel):
        puffer = io.BytesIO()
        try:
            self.ftp.retrbinary("RETR " + self._abs(rel), puffer.write)
        except ftplib.error_perm:
            return None
        return puffer.getvalue()

    def schreibe(self, rel, inhalt):
        aktuell = self.pfad
        for t in [t for t in posixpath.dirname(rel).split("/") if t]:
            aktuell = posixpath.join(aktuell, t)
            try:
                self.ftp.mkd(aktuell)
            except ftplib.error_perm:
                pass
        self.ftp.storbinary("STOR " + self._abs(rel), io.BytesIO(inhalt))

    def benenne(self, von, nach):
        try:
            self.ftp.rename(self._abs(von), self._abs(nach))
        except ftplib.error_perm:
            self.ftp.delete(self._abs(nach))
            self.ftp.rename(self._abs(von), self._abs(nach))

    def loesche(self, rel):
        self.ftp.delete(self._abs(rel))

    def schliesse(self):
        try:
            self.ftp.quit()
        except Exception:
            self.ftp.close()


def oeffne_ziel(url: str, passwort: str | None = None, schluessel: str | None = None,
                known_hosts: str | None = None) -> Ziel:
    u = urlparse(url)
    pfad = unquote(u.path) or "."
    if u.scheme == "sftp":
        return SftpZiel(u.hostname, u.port or 22, unquote(u.username or ""), pfad, passwort, schluessel, known_hosts)
    if u.scheme == "ftps":
        return FtpsZiel(u.hostname, u.port or 21, unquote(u.username or ""), pfad, passwort)
    if u.scheme == "file":
        return OrdnerZiel(pfad)
    raise UploadFehler(f"Unbekanntes Upload-Ziel {u.scheme!r}: erlaubt sind sftp://, ftps:// und file://")


def veroeffentliche(settings, site_dir, oeffne=oeffne_ziel, pruefe=pruefe_oeffentlich,
                    schlafe=time.sleep, ping: Callable[[str], None] | None = None) -> Ergebnis:
    """Bis zu drei Versuche (B21 AK 3), danach UploadFehler. Nach Erfolg der Heartbeat (B22)."""
    wartezeiten = [int(w) for w in str(settings.upload_wartezeiten_s).split(",") if w.strip()]
    letzter: Exception | None = None
    for versuch in range(len(wartezeiten) + 1):
        ziel = None
        try:
            ziel = oeffne(settings.upload_url, settings.upload_passwort, settings.upload_schluessel,
                          settings.upload_known_hosts)
            erg = lade_hoch(site_dir, ziel)
            if settings.oeffentliche_url:
                pruefe(settings.oeffentliche_url, erg.erzeugt)
            log.info("Upload fertig: %d Dateien neu, %d unverändert, %d gelöscht",
                     len(erg.hochgeladen), erg.unveraendert, len(erg.geloescht))
            if settings.heartbeat_url:
                try:
                    (ping or _ping)(settings.heartbeat_url)
                except Exception:
                    log.exception("Heartbeat nicht erreichbar")
            return erg
        except Exception as e:  # Netz, Anmeldung, Pruefung: alles zaehlt als Fehlversuch
            letzter = e
            log.warning("Upload Versuch %d fehlgeschlagen: %s", versuch + 1, e)
            if versuch < len(wartezeiten):
                schlafe(wartezeiten[versuch])
        finally:
            if ziel is not None:
                try:
                    ziel.schliesse()
                except Exception:
                    pass
    raise UploadFehler(f"Upload nach {len(wartezeiten) + 1} Versuchen fehlgeschlagen: {letzter}")


def _ping(url: str) -> None:
    import httpx
    httpx.get(url, timeout=15).raise_for_status()


def upload_meldung(status_datei: Path, ok: bool, fehler: str | None) -> tuple[str, str] | None:
    """Push nur beim Wechsel zwischen ok und Fehler, wie bei den Quellen (B2)."""
    vorher = None
    if status_datei.exists():
        try:
            vorher = json.loads(status_datei.read_text(encoding="utf-8")).get("ok")
        except ValueError:
            vorher = None
    status_datei.parent.mkdir(parents=True, exist_ok=True)
    status_datei.write_text(json.dumps({"ok": ok, "fehler": fehler, "zeit": time.time()}), encoding="utf-8")
    if not ok and vorher is not False:
        return ("Loipenblick: Upload fehlgeschlagen", f"Die öffentliche Seite zeigt weiter den alten Stand. {fehler}")
    if ok and vorher is False:
        return ("Loipenblick: Upload wieder in Ordnung", "Die öffentliche Seite ist wieder aktuell.")
    return None
