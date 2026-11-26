"""Worker-Container: Konfiguration abgleichen, Quellen abrufen, Seite erzeugen.

    python -m loipen.worker          Zeitplan starten (Standard im Container, B3)
    python -m loipen.worker sicherung  Datenbank sofort sichern (B14)
    python -m loipen.worker lauf     einmal alle Quellen abrufen und die Seite erzeugen
    python -m loipen.worker schnee   einmal alle Schneequellen abrufen (Schneekarte, S1)
    python -m loipen.worker schnee-archiv <quelle> [von] [bis]   fruehere Winter nachladen (S5)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from loipen import generator, osm
from loipen.ablauf import rufe_quelle_ab
from loipen.benachrichtigung import PushKonfig, entprelle
from loipen.benachrichtigung import veroeffentliche as push_veroeffentliche
from loipen.config import get_settings
from loipen.db import session_scope
from loipen.ereignisse import (
    benachrichtige, lade_abos, ntfy_sender, pruefe_abos,
)
from loipen.fetcher import HoeflicherFetcher
from loipen.generator import abo as abo_vorlage
from loipen.generator import zaehler as zaehler_vorlage
from loipen.mailabo import AboKonfig, lauf_abo, smtp_versand
from loipen.konfig import ausgeblendet, lade_und_abgleichen, lade_yaml
from loipen.models import Quelle, utcnow
from loipen.sicherung import sichere
from loipen.waechter import melde as waechter_melde
from loipen.upload import UploadFehler, upload_meldung, veroeffentliche
from loipen.wetter import aktualisiere_wetter
from loipen.zeitplan import ist_faellig

log = logging.getLogger("loipen.worker")

# Ein Fetcher fuer die Lebensdauer des Workers, damit der ETag-Cache zwischen den Laeufen bleibt (P7)
_fetcher: HoeflicherFetcher | None = None


def fetcher() -> HoeflicherFetcher:
    global _fetcher
    if _fetcher is None:
        settings = get_settings()
        _fetcher = HoeflicherFetcher(settings.user_agent, settings.request_delay_s, umleitung=settings.umleitung)
    return _fetcher


def lauf(nur_faellige: datetime | None = None, abrufer=None, sender=None) -> None:
    """Ein Lauf. Mit nur_faellige werden nur Quellen abgerufen, deren Zeitplan passt."""
    settings = get_settings()
    sender = sender or ntfy_sender(settings.ntfy_url)
    ereignisse, meldungen, waechter = [], [], []
    with session_scope() as session:
        # Konfiguration bei jedem Lauf neu lesen: neue Quellen ohne Neustart (P2)
        lade_und_abgleichen(session, Path(settings.config_dir))
        quellen = session.scalars(select(Quelle).where(Quelle.enabled)).all()
        for quelle in quellen:
            if nur_faellige and not ist_faellig(nur_faellige, quelle.config.get("zeitplan")):
                continue
            if quelle.config.get("erlaubnis") == "abgelehnt":  # B30: doppelt abgesichert, enabled ist schon aus
                continue
            log.info("Quelle %s wird abgerufen", quelle.key)
            ergebnis = rufe_quelle_ab(session, quelle, abrufer or fetcher())
            ereignisse += ergebnis.ereignisse
            if ergebnis.waechter:  # B26 statt der alten Meldung bei jedem Statuswechsel
                waechter.append(ergebnis.waechter)
            log.info(
                "Quelle %s: %d Loipen, %d neue Zustaende%s",
                quelle.key, ergebnis.gefunden, ergebnis.neu,
                f", Fehler: {ergebnis.fehler}" if ergebnis.fehler else "",
            )
        try:
            wetter = aktualisiere_wetter(session, abrufer or fetcher())
            log.info("Wetter: %d Messwerte, %d Vorhersagewerte", wetter.messungen, wetter.vorhersagen)
            for w in wetter.warnungen:
                log.warning("Wetter: %s", w)
        except Exception:  # Wetter darf den Lauf nie verhindern
            log.exception("Wetter-Aktualisierung fehlgeschlagen")
        if abrufer is None:  # P40/P39: OpenStreetMap einmal pro Woche je Region, eigener Fetcher mit langem Zeitlimit
            try:
                osm_fetcher = HoeflicherFetcher(settings.user_agent, settings.request_delay_s, timeout_s=180,
                                                umleitung=settings.umleitung)
                try:
                    o = osm.aktualisiere(session, osm_fetcher)
                finally:
                    osm_fetcher.close()
                if o.abgerufen or o.fehler:
                    log.info("OpenStreetMap: %d Regionen aktualisiert, %d Fehler", len(o.abgerufen), len(o.fehler))
            except Exception:
                log.exception("OpenStreetMap-Aktualisierung fehlgeschlagen")
        unplausibel: set[int] = set()
        generator.erzeuge(session, settings.site_dir, config_dir=settings.config_dir, stale_days=settings.stale_days,
                          rechtliches=rechtliches(settings), oeffentlich=settings.oeffentlich,
                          abo_dateien=abo_dateien(session, settings), version=settings.version,
                          unplausibel=unplausibel, push=PushKonfig.aus_settings(settings).fuer_seite(),
                          zaehler_dateien=zaehler_dateien(session, settings),
                          basis_url=settings.oeffentliche_url)
        ereignisse = ohne_unplausible(ereignisse, unplausibel)
        ereignisse = ohne_ausgeblendete(ereignisse, Path(settings.config_dir))
        # N11: Wiederholungen zurueckhalten, fuer alle Kanaele. Eingetragen wird vor dem Versand: Ein
        # Versandfehler holt eine Nachricht nicht nach, sonst kaemen bei einer Stoerung spaeter Doppelte.
        ereignisse = entprelle(session, ereignisse)
    log.info("Seite erzeugt in %s", settings.site_dir)
    meldung = hochladen(settings)
    if meldung:
        meldungen.append(meldung)
    _melde(settings, sender, ereignisse, meldungen)
    melde_waechter(settings, sender, waechter)


def melde_waechter(settings, sender, meldungen, mail=None) -> dict:
    """B26: nach dem Commit, damit ein Versandfehler nie Daten gefaehrdet."""
    an = settings.waechter_mail or settings.impressum_email
    absender = settings.abo_absender or an
    if mail is None and settings.smtp_host:
        versand = smtp_versand(AboKonfig.aus_settings(settings))

        def mail(m):
            fehler = versand([m])[0]
            if fehler:
                raise fehler
    try:
        return waechter_melde(meldungen, sender, mail, an, absender)
    except Exception:
        log.exception("Quellen-Waechter: Meldung fehlgeschlagen")
        return {"push": 0, "mail": 0}


def abo_dateien(session, settings) -> dict[str, bytes]:
    """E-18: Ordner abo/ nur, wenn Adresse, Schluessel und Absender in der .env stehen."""
    return abo_vorlage.dateien(session, AboKonfig.aus_settings(settings),
                               meldungen_an=settings.abo_meldungen_an or settings.impressum_email,
                               datenordner=settings.abo_datenordner)


def zaehler_dateien(session, settings) -> dict[str, bytes]:
    """B13/E-42: Ordner zaehler/ nur mit LOIPEN_ZAEHLER_PASSWORT. Test- und Release-Seite liegen in
    getrennten Web-Ordnern und zaehlen darum getrennt; die Auswertung der Testseite traegt das Zeichen."""
    return zaehler_vorlage.dateien(session, settings.zaehler_passwort, oeffentlich=settings.oeffentlich,
                                   seite=settings.oeffentliche_url or "", datenordner=settings.zaehler_datenordner,
                                   config_dir=Path(settings.config_dir))


def rechtliches(settings) -> dict:
    """B6: Impressum und Datenschutz kommen aus der .env auf dem NAS, nie aus dem Repo."""
    text = None
    if settings.datenschutz_datei:
        try:
            text = Path(settings.datenschutz_datei).read_text(encoding="utf-8")
        except OSError:
            log.exception("Datenschutztext %s nicht lesbar, nehme die Vorlage", settings.datenschutz_datei)
    return {"name": settings.impressum_name, "anschrift": settings.impressum_anschrift,
            "email": settings.impressum_email, "hoster": settings.hoster, "log_tage": settings.log_tage,
            "datenschutz_html": text, "spenden_url": getattr(settings, "spenden_url", None)}


def hochladen(settings, **kw) -> tuple[str, str] | None:
    """B8: nach jedem Lauf hochladen, wenn ein Ziel eingerichtet ist. Gibt eine Push-Meldung zurueck."""
    if not settings.upload_url:
        return None
    fehlt = generator.rechtliches_fehlt(rechtliches(settings))
    status = Path(settings.backup_dir) / "upload-status.json"
    try:
        if fehlt:  # B6 AK 3: ohne vollstaendiges Impressum geht nichts online
            raise UploadFehler("Impressum unvollständig, es fehlen: " + ", ".join(fehlt))
        veroeffentliche(settings, settings.site_dir, **kw)
        return upload_meldung(status, True, None)
    except Exception as e:
        log.error("Upload: %s", e)
        return upload_meldung(status, False, str(e))


def ohne_ausgeblendete(ereignisse: list, config_dir: Path) -> list:
    """B30 AK 3: Was die Seite nicht zeigt, meldet auch kein Push und kein Abo-Mail. B30 AK 5: Meldungen gehen
    nach aussen, deshalb gilt hier immer die oeffentliche Seite; nur_test-Gebiete melden auch in der Testversion nichts."""
    gebiete_aus, loipen_aus = ausgeblendet(lade_yaml(config_dir / "gebiete.yaml"))
    return [e for e in ereignisse if e.gebiet not in gebiete_aus and (e.gebiet, e.loipe) not in loipen_aus]


def ohne_unplausible(ereignisse: list, unplausibel: set[int]) -> list:
    """D19 AK 5: Die Seite zeigt eine unplausible Offen-Meldung geschlossen, also meldet auch kein Push
    und kein Abo-Mail sie als befahrbar oder frisch gespurt."""
    bleiben = []
    for e in ereignisse:
        if e.art != "schliesst" and e.loipe_id in unplausibel:
            log.info("Ereignis %s fuer %s nicht gemeldet: Offen-Meldung unplausibel (D19)", e.art, e.loipe)
        else:
            bleiben.append(e)
    return bleiben


def _melde(settings, sender, ereignisse, meldungen) -> None:
    """Push nach dem Commit, damit ein Versandfehler nie Daten gefaehrdet (N4)."""
    try:
        cfg = Path(settings.config_dir)
        abos = lade_abos(cfg)
        for f in pruefe_abos(abos, lade_yaml(cfg / "gebiete.yaml")):
            log.warning("abos.yaml: %s", f)
        n = benachrichtige(abos, ereignisse, sender)
        if sender:
            for titel, text in meldungen:
                sender(titel, text)
        log.info("%d Ereignisse, %d Alarme gesendet", len(ereignisse), n)
    except Exception:
        log.exception("Benachrichtigung fehlgeschlagen")
    try:  # E-18: Abgleich mit dem Webspace, Meldungen als Push, Abo-Mails per SMTP
        lauf_abo(session_scope, AboKonfig.aus_settings(settings), ereignisse, sender)
    except Exception:
        log.exception("E-Mail-Abo fehlgeschlagen")
    push = PushKonfig.aus_settings(settings)
    if push.aktiv and ereignisse:
        try:  # N10: oeffentliche ntfy-Themen je Loipe und Gebiet
            with session_scope() as session:
                n = push_veroeffentliche(session, push, ereignisse, betreiber=sender)
            log.info("%d oeffentliche Push-Nachrichten", n)
        except Exception:
            log.exception("Oeffentlicher Push fehlgeschlagen")


def sicherung() -> None:
    settings = get_settings()
    try:
        ziel = sichere(settings.database_url, settings.backup_dir, utcnow())
        log.info("Sicherung geschrieben: %s", ziel)
    except Exception:
        log.exception("Sicherung fehlgeschlagen")
        sender = ntfy_sender(settings.ntfy_url)
        if sender:
            try:
                sender("Loipenblick: Sicherung fehlgeschlagen", "Siehe Log des Worker-Containers.")
            except Exception:
                log.exception("Meldung ueber fehlgeschlagene Sicherung nicht gesendet")


def tick() -> None:
    lauf(nur_faellige=datetime.now(ZoneInfo(get_settings().timezone)))


def schnee_tick() -> None:
    """S1: Schneekarte stuendlich um :20, jede Quelle zu ihren Uhrzeiten. Getrennt vom Loipen-Lauf (E-34)."""
    from loipen.schnee import job
    try:
        job.lauf(nur_faellige=True, sender=ntfy_sender(get_settings().ntfy_url))
    except Exception:
        log.exception("Schneekarte: Sammel-Lauf fehlgeschlagen")


def main(argv: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if argv[:1] == ["lauf"]:
        lauf()
        return
    if argv[:1] == ["sicherung"]:
        sicherung()
        return
    if argv[:1] == ["schnee"]:
        from loipen.schnee import job
        job.lauf()
        return
    if argv[:1] == ["schnee-archiv"] and len(argv) >= 2:
        from loipen.schnee import job
        log.info("Archiv: %s", job.nachladen(*argv[1:4]))
        return
    log.info("Loipenblick Version %s startet", get_settings().version)
    lauf()  # beim Start einmal, damit die Vorschau sofort etwas zeigt
    scheduler = BlockingScheduler(timezone=get_settings().timezone)
    scheduler.add_job(tick, "cron", minute=0)
    scheduler.add_job(schnee_tick, "cron", minute=20, max_instances=1, coalesce=True)  # Schneekarte (S1)
    scheduler.add_job(sicherung, "cron", hour=3, minute=30)  # taeglich, B14
    scheduler.start()


if __name__ == "__main__":
    main(sys.argv[1:])
