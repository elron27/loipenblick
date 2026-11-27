"""B34: Worker-Log als Datei im Datenordner und Mail bei Absturz oder Fehlern.

- Das Log geht wie bisher in das Protokoll des Containers und zusaetzlich in eine rotierende Datei
  ``worker.log`` (je 1 MB, 5 alte Dateien). Ordner: LOIPEN_LOG_DIR, sonst ``logs`` im Sicherungsordner.
- Stuerzt der Worker ab, geht eine Mail mit Traceback, den letzten 200 Zeilen und dem Log als Anhang an
  LOIPEN_FEHLER_MAIL (sonst LOIPEN_WAECHTER_MAIL, sonst Impressum-Adresse), ueber den SMTP-Zugang aus E-18.
- Endet der Worker ohne Python-Fehler (Speicher voll, Stromausfall), merkt er das beim naechsten Start an der
  Marke ``worker.laeuft`` und schickt die letzten Zeilen des vorigen Laufs.
- Fehler im Log (ERROR) werden nach jedem Job gesammelt gemeldet, hoechstens alle LOIPEN_FEHLER_MAIL_STUNDEN.
- Absturz-Mails hoechstens alle 30 Minuten, auch ueber Neustarts hinweg (Zustand in ``mailstatus.json``).
- Passwoerter, Schluessel und Zugangsdaten in Adressen werden in Datei, Container-Log und Mail geschwaerzt.
- Nichts davon darf den Worker selbst stoppen: Jeder Fehler beim Schreiben oder Senden wird nur geloggt.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
import traceback
from collections import deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

log = logging.getLogger("loipen.betrieb")

DATEI = "worker.log"
MARKE = "worker.laeuft"
STATUS = "mailstatus.json"
ZEILEN = 200
DATEI_GROESSE = 1_000_000
DATEI_ANZAHL = 5
ABSTURZ_ABSTAND = timedelta(minutes=30)
MAX_FEHLERZEILEN = 50
MIN_GEHEIM = 8  # kurze Werte wie "loipen" wuerden sonst normale Woerter im Log zerstoeren
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

_GEHEIM_NAME = re.compile(r"passwort|password|schluessel|secret|token|key|pass$", re.I)
_URL_ZUGANG = re.compile(r"(?P<schema>[a-z][a-z0-9+.-]*://)(?P<benutzer>[^:/@\s]+):(?P<pw>[^@\s/]+)@", re.I)


def geheimnisse(settings, umgebung: dict | None = None) -> list[str]:
    """Werte, die nie in Log oder Mail stehen duerfen: alle Felder und Umgebungsvariablen mit Passwort,
    Schluessel, Token oder Key im Namen, dazu die ntfy- und Heartbeat-Adresse (das Thema ist geheim)."""
    werte = set()
    felder = getattr(settings, "model_dump", None)
    daten = felder() if felder else dict(vars(settings))
    for name, wert in daten.items():
        if isinstance(wert, str) and (_GEHEIM_NAME.search(name) or name in ("ntfy_url", "heartbeat_url")):
            werte.add(wert)
    for name, wert in (os.environ if umgebung is None else umgebung).items():
        if _GEHEIM_NAME.search(name) and isinstance(wert, str):
            werte.add(wert)
    return sorted((w for w in werte if len(w) >= MIN_GEHEIM), key=len, reverse=True)


def schwaerze(text: str, geheim: list[str]) -> str:
    text = _URL_ZUGANG.sub(lambda m: f"{m['schema']}{m['benutzer']}:***@", text)
    for w in geheim:
        text = text.replace(w, "***")
    return text


class _Formatter(logging.Formatter):
    def __init__(self, geheim: list[str]):
        super().__init__(FORMAT)
        self.geheim = geheim

    def format(self, record):
        return schwaerze(super().format(record), self.geheim)


class _Puffer(logging.Handler):
    """Haelt die letzten Zeilen fuer die Mail und sammelt Fehler seit der letzten Fehler-Mail."""

    def __init__(self, zeilen: int = ZEILEN):
        super().__init__(logging.INFO)
        self.zeilen: deque[str] = deque(maxlen=zeilen)
        self.fehler: list[str] = []
        self.fehler_anzahl = 0

    def emit(self, record):
        try:
            text = self.format(record)
        except Exception:  # pragma: no cover - logging selbst darf nie stoeren
            return
        self.zeilen.extend(text.splitlines() or [""])
        if record.levelno >= logging.ERROR and record.name != log.name:
            self.fehler_anzahl += 1
            if len(self.fehler) < MAX_FEHLERZEILEN:
                self.fehler.append(text)


def log_ordner(settings) -> Path:
    return Path(settings.log_dir) if getattr(settings, "log_dir", None) else Path(settings.backup_dir) / "logs"


def ordner_hinweis(settings) -> str:
    if getattr(settings, "log_dir", None):
        return "Ordner logs neben der .env und docker-compose.yml, Datei worker.log"
    return "Ordner backup/logs (bzw. der Sicherungsordner aus BACKUP_DIR), Datei worker.log"


def smtp_mailer(settings) -> Callable[[EmailMessage], None] | None:
    if not getattr(settings, "smtp_host", None):
        return None
    from loipen.mailabo import AboKonfig, smtp_versand
    versand = smtp_versand(AboKonfig.aus_settings(settings))

    def senden(m: EmailMessage) -> None:
        fehler = versand([m])[0]
        if fehler:
            raise fehler
    return senden


class Betriebslog:
    def __init__(self, settings, mailer: Callable[[EmailMessage], None] | None = None,
                 sender: Callable[[str, str], None] | None = None, jetzt: Callable[[], datetime] | None = None,
                 umgebung: dict | None = None):
        self.settings = settings
        self.ordner = log_ordner(settings)
        self.mailer = mailer
        self.sender = sender
        self.jetzt = jetzt or (lambda: datetime.now(timezone.utc))
        self.geheim = geheimnisse(settings, umgebung)
        self.an = (getattr(settings, "fehler_mail", None) or getattr(settings, "waechter_mail", None)
                   or getattr(settings, "impressum_email", None))
        benutzer = getattr(settings, "smtp_benutzer", None) or ""
        self.absender = getattr(settings, "abo_absender", None) or (benutzer if "@" in benutzer else None) or self.an
        self.fehler_abstand = timedelta(hours=float(getattr(settings, "fehler_mail_stunden", 6) or 0))
        self.puffer = _Puffer()
        self.handler: list[logging.Handler] = []
        self.datei_ok = False
        self._marke_gesetzt = False

    # ------------------------------------------------------------------------------------------- Einrichten
    def richte_ein(self, marke: bool = True) -> "Betriebslog":
        """Logging einrichten. Mit marke wird ein harter Abbruch des vorigen Laufs erkannt und gemeldet."""
        formatter = _Formatter(self.geheim)
        wurzel = logging.getLogger()
        wurzel.setLevel(logging.INFO)
        konsole = logging.StreamHandler(sys.stdout)
        self.puffer.setFormatter(formatter)
        konsole.setFormatter(formatter)
        self.handler = [konsole, self.puffer]
        voriger_lauf = None
        try:
            self.ordner.mkdir(parents=True, exist_ok=True)
            if marke and (self.ordner / MARKE).exists():
                voriger_lauf = self._letzte_zeilen()
            datei = logging.handlers.RotatingFileHandler(self.ordner / DATEI, maxBytes=DATEI_GROESSE,
                                                         backupCount=DATEI_ANZAHL, encoding="utf-8")
            datei.setFormatter(formatter)
            self.handler.append(datei)
            self.datei_ok = True
        except OSError as ex:
            datei_fehler = ex
        else:
            datei_fehler = None
        for h in self.handler:
            wurzel.addHandler(h)
        if datei_fehler:
            log.warning("Logdatei in %s nicht moeglich (%s), Log nur im Container-Protokoll", self.ordner,
                        datei_fehler)
        if voriger_lauf is not None:
            log.warning("Der vorige Worker-Lauf endete ohne Abmeldung (hart beendet)")
            self._melde_absturz("Worker wurde hart beendet",
                                "Der vorige Lauf des Workers endete ohne Python-Fehlermeldung. Haeufige Ursachen: "
                                "Arbeitsspeicher des NAS voll, Stromausfall oder Neustart des NAS ohne sauberes "
                                "Herunterfahren. Docker hat ihn neu gestartet.", None, voriger_lauf)
        if marke and self.datei_ok:
            try:
                (self.ordner / MARKE).write_text(f"{self._ortszeit()} Version {self._version()}\n", encoding="utf-8")
                self._marke_gesetzt = True
            except OSError:
                log.warning("Marke %s nicht schreibbar", self.ordner / MARKE)
        return self

    def schliesse(self) -> None:
        """Sauberes Ende (auch nach einem Absturz, wenn die Mail raus ist): Marke weg, Handler ab."""
        if self._marke_gesetzt:
            try:
                (self.ordner / MARKE).unlink(missing_ok=True)
            except OSError:
                pass
            self._marke_gesetzt = False
        wurzel = logging.getLogger()
        for h in self.handler:
            wurzel.removeHandler(h)
            try:
                h.close()
            except Exception:  # pragma: no cover
                pass
        self.handler = []

    # ------------------------------------------------------------------------------------------- Melden
    def absturz(self, ex: BaseException) -> None:
        """Aufrufen im except-Block um den ganzen Worker. Wirft nie."""
        try:
            tb = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            log.critical("Worker abgestuerzt:\n%s", tb.rstrip())
            self._melde_absturz("Worker abgestuerzt",
                                "Der Worker ist mit einem Fehler beendet worden. Docker startet ihn von selbst neu "
                                "(restart: unless-stopped).", tb, list(self.puffer.zeilen))
        except Exception:  # pragma: no cover - letzte Sicherung
            pass

    def pruefe(self) -> bool:
        """Nach jedem Job: gesammelte Fehler melden, hoechstens alle fehler_abstand. Wirft nie."""
        try:
            if not self.puffer.fehler_anzahl or self.fehler_abstand <= timedelta(0):
                return False
            if not self._faellig("fehler", self.fehler_abstand):
                return False
            anzahl, fehler = self.puffer.fehler_anzahl, list(self.puffer.fehler)
            text = (f"Im Worker sind seit der letzten Meldung {anzahl} Fehler aufgetreten. Er laeuft weiter.\n"
                    f"Die naechste Fehler-Mail kommt fruehestens in {self._stunden()} Stunden.")
            gesendet = self._sende(f"Fehler im Worker ({anzahl})", text, "\n\n".join(fehler),
                                   list(self.puffer.zeilen), "fehler")
            if gesendet:
                self.puffer.fehler.clear()
                self.puffer.fehler_anzahl = 0
            return gesendet
        except Exception:
            log.exception("Fehler-Mail nicht moeglich")
            return False

    # ------------------------------------------------------------------------------------------- intern
    def _melde_absturz(self, titel: str, text: str, tb: str | None, zeilen: list[str]) -> None:
        if not self._faellig("absturz", ABSTURZ_ABSTAND):
            log.info("Absturz-Mail zurueckgehalten (hoechstens eine je %d Minuten)",
                     ABSTURZ_ABSTAND.total_seconds() // 60)
            return
        self._sende(titel, text, tb, zeilen, "absturz")
        if self.sender:
            try:
                self.sender(f"Loipenblick: {titel}", f"Log: {ordner_hinweis(self.settings)}.")
            except Exception:
                log.exception("Push ueber den Absturz nicht gesendet")

    def _sende(self, titel: str, text: str, fehler: str | None, zeilen: list[str], art: str) -> bool:
        if not (self.mailer and self.an and self.absender):
            log.info("%s: keine Mail (SMTP oder Empfaenger fehlt), Log steht in %s", titel, self.ordner / DATEI)
            return False
        try:
            m = self._baue(titel, text, fehler, zeilen)
            self.mailer(m)
        except Exception as ex:
            log.warning("Mail '%s' nicht gesendet: %s", titel, schwaerze(str(ex), self.geheim))
            return False
        self._merke(art)
        log.info("Mail '%s' an die Betriebsadresse gesendet", titel)
        return True

    def _baue(self, titel: str, text: str, fehler: str | None, zeilen: list[str]) -> EmailMessage:
        teile = [f"{text}\n", f"Zeit: {self._ortszeit()}", f"Version: {self._version()}",
                 f"Log auf dem NAS: {ordner_hinweis(self.settings)}.", "",
                 "Zum Weitergeben: diese Mail einfach an Claude im Projekt schicken oder den Anhang hochladen.", ""]
        if fehler:
            teile += ["---------- Fehler ----------", fehler.rstrip(), ""]
        teile += [f"---------- Letzte {len(zeilen)} Zeilen ----------", *zeilen]
        m = EmailMessage()
        m["Subject"] = f"Loipenblick: {titel}"
        m["From"] = self.absender
        m["To"] = self.an
        m.set_content(schwaerze("\n".join(teile), self.geheim))
        anhang = self._dateiinhalt()
        if anhang:
            m.add_attachment(schwaerze(anhang, self.geheim), filename="worker.log")
        return m

    def _dateiinhalt(self) -> str | None:
        try:
            return (self.ordner / DATEI).read_text(encoding="utf-8", errors="replace")[-DATEI_GROESSE:]
        except OSError:
            return None

    def _letzte_zeilen(self) -> list[str]:
        inhalt = self._dateiinhalt() or ""
        return inhalt.splitlines()[-ZEILEN:]

    def _status(self) -> dict:
        try:
            return json.loads((self.ordner / STATUS).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _faellig(self, art: str, abstand: timedelta) -> bool:
        zuletzt = self._status().get(art) or getattr(self, f"_zuletzt_{art}", None)
        if not zuletzt:
            return True
        try:
            return self.jetzt() - datetime.fromisoformat(zuletzt) >= abstand
        except ValueError:
            return True

    def _merke(self, art: str) -> None:
        jetzt = self.jetzt().isoformat()
        setattr(self, f"_zuletzt_{art}", jetzt)  # auch ohne schreibbaren Ordner nicht im Minutentakt
        try:
            status = self._status()
            status[art] = jetzt
            (self.ordner / STATUS).write_text(json.dumps(status), encoding="utf-8")
        except OSError:
            pass

    def _ortszeit(self) -> str:
        try:
            zone = ZoneInfo(getattr(self.settings, "timezone", "Europe/Berlin"))
        except Exception:  # pragma: no cover
            zone = timezone.utc
        return self.jetzt().astimezone(zone).strftime("%d.%m.%Y %H:%M:%S")

    def _version(self) -> str:
        return str(getattr(self.settings, "version", "unbekannt"))

    def _stunden(self) -> str:
        h = self.fehler_abstand.total_seconds() / 3600
        return f"{h:g}"
