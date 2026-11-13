"""E-Mail-Abo und Fehlermeldungen, Teil auf dem NAS (E-18, N2, N3, N5–N9).

Ablauf bei jedem Lauf:

1. Abgleich (N6): Das NAS holt per HTTPS die Warteschlange vom Webspace (abo/export.php), traegt
   bestaetigte Abos in die Datenbank ein, loescht abgemeldete und quittiert erst nach dem Commit.
   Das NAS oeffnet keinen Port. Fehlermeldungen von Besuchern (N9) kommen ueber dieselbe
   Warteschlange und gehen als Push an den Betreiber; sie aendern nie einen Status.
2. Versand (N3): hoechstens eine Mail je Abonnent und Lauf, mit allen passenden Ereignissen und
   einem Abmeldelink mit Token (N2), auch als List-Unsubscribe fuer Mailprogramme.

Klappt der Abgleich nicht, gehen in diesem Lauf keine Abo-Mails raus. Sonst bekaeme jemand, der
sich gerade abgemeldet hat, noch eine Mail.
"""

import logging
import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from urllib.parse import urlencode, urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.ereignisse import ARTEN, Ereignis
from loipen.models import Abonnent, utcnow

log = logging.getLogger("loipen.mailabo")

MELDE_ARTEN = {
    "offen": "ist in Wirklichkeit offen",
    "geschlossen": "ist in Wirklichkeit geschlossen",
    "nicht_gespurt": "ist nicht gespurt",
    "daten": "Angaben stimmen nicht",
    "sonstiges": "Sonstiges",
}
Versand = Callable[[EmailMessage], None]


@dataclass
class AboKonfig:
    """Aus der .env auf dem NAS (B4). Ohne seite_url oder schluessel ist das Abo aus."""

    seite_url: str | None = None  # https://loipenblick.de
    schluessel: str | None = None  # LOIPEN_ABO_SCHLUESSEL, auf dem Webspace liegt nur der SHA-256
    absender: str | None = None  # abo@loipenblick.de
    seitenname: str = "Loipenblick"
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_benutzer: str | None = None
    smtp_passwort: str | None = None
    smtp_starttls: bool = False  # Port 587 mit STARTTLS statt 465 mit TLS

    @property
    def aktiv(self) -> bool:
        return bool(self.seite_url and self.schluessel and self.absender)

    @property
    def basis(self) -> str:
        return (self.seite_url or "").rstrip("/")

    @property
    def export_url(self) -> str:
        return f"{self.basis}/abo/export.php"

    @classmethod
    def aus_settings(cls, s) -> "AboKonfig":
        return cls(
            seite_url=s.seite_url, schluessel=s.abo_schluessel, absender=s.abo_absender,
            seitenname=s.seitenname, smtp_host=s.smtp_host, smtp_port=s.smtp_port,
            smtp_benutzer=s.smtp_benutzer, smtp_passwort=s.smtp_passwort, smtp_starttls=s.smtp_starttls,
        )


@dataclass
class Abgleich:
    neu: int = 0
    abgemeldet: int = 0
    meldungen: list[dict] = field(default_factory=list)
    anzahl: int = 0  # Zeilen, die nach dem Commit quittiert werden


# ---------- Abgleich mit dem Webspace (N6) ----------

def hole_warteschlange(cfg: AboKonfig, http: httpx.Client) -> tuple[list[dict], int]:
    antwort = http.post(cfg.export_url, data={"schluessel": cfg.schluessel})
    antwort.raise_for_status()
    daten = antwort.json()
    return list(daten.get("eintraege", [])), int(daten.get("anzahl", 0))


def quittiere(cfg: AboKonfig, http: httpx.Client, anzahl: int) -> None:
    if anzahl <= 0:
        return
    antwort = http.post(cfg.export_url, data={"schluessel": cfg.schluessel, "quittung": str(anzahl)})
    antwort.raise_for_status()


def _zeit(wert: str | None) -> datetime:
    try:
        return datetime.fromisoformat(wert) if wert else utcnow()
    except ValueError:
        return utcnow()


def _gueltig(e: dict) -> bool:
    return (
        isinstance(e.get("id"), str) and 0 < len(e["id"]) <= 32
        and isinstance(e.get("email"), str) and "@" in e["email"] and len(e["email"]) <= 254
        and isinstance(e.get("abmelden"), str) and 0 < len(e["abmelden"]) <= 64
        and isinstance(e.get("ziele"), list) and e["ziele"]
        and all(isinstance(z, str) and z[:2] in ("l:", "g:") for z in e["ziele"])
        and isinstance(e.get("ereignisse"), list)
        and all(a in ARTEN for a in e["ereignisse"]) and e["ereignisse"]
    )


def uebernimm(session: Session, eintraege: list[dict]) -> Abgleich:
    """Wendet die Eintraege der Reihe nach an. Doppelte Eintraege schaden nicht (gleiche ID)."""
    ergebnis = Abgleich()
    for e in eintraege:
        typ = e.get("typ")
        if typ == "bestaetigt":
            if not _gueltig(e):
                log.warning("Abo-Eintrag ungueltig, uebersprungen")
                continue
            a = session.get(Abonnent, e["id"])
            if a is None:
                a = Abonnent(id=e["id"])
                session.add(a)
                ergebnis.neu += 1
            a.email = e["email"]
            a.ziele = list(dict.fromkeys(e["ziele"]))
            a.ereignisse = [x for x in ARTEN if x in e["ereignisse"]]
            a.abmelde_token = e["abmelden"]
            a.angefragt_at = _zeit(e.get("angefragt"))
            a.bestaetigt_at = _zeit(e.get("bestaetigt"))
            session.flush()
        elif typ == "abgemeldet":
            a = session.get(Abonnent, str(e.get("id", "")))
            if a is not None:
                session.delete(a)  # N7: Abmelden loescht die Adresse
                session.flush()
                ergebnis.abgemeldet += 1
        elif typ == "meldung":
            ergebnis.meldungen.append(e)
    return ergebnis


def gleiche_ab(session: Session, cfg: AboKonfig, http: httpx.Client) -> Abgleich:
    """Holt und uebernimmt die Warteschlange. Quittieren erst nach dem Commit (quittiere)."""
    eintraege, anzahl = hole_warteschlange(cfg, http)
    ergebnis = uebernimm(session, eintraege)
    ergebnis.anzahl = anzahl
    return ergebnis


def meldung_als_push(m: dict) -> tuple[str, str]:
    """Fehlermeldung eines Besuchers als Push an den Betreiber (N9). Text ist Besucher-Eingabe: nur anzeigen."""
    name = str(m.get("name") or m.get("ziel") or "?")[:200]
    art = MELDE_ARTEN.get(str(m.get("art")), "Sonstiges")
    zeilen = [f"{name}: {art}"]
    if m.get("text"):
        zeilen.append(str(m["text"])[:500])
    if m.get("kontakt"):
        zeilen.append(f"Rückfragen an: {str(m['kontakt'])[:254]}")
    zeilen.append("Status bleibt unverändert, bitte von Hand prüfen.")
    return f"Loipenblick: Meldung zu {name}", "\n".join(zeilen)


# ---------- Versand (N3) ----------

def passt(abonnent: Abonnent, e: Ereignis) -> bool:
    if e.art not in abonnent.ereignisse:
        return False
    return (e.loipe_id is not None and f"l:{e.loipe_id}" in abonnent.ziele) or f"g:{e.gebiet}" in abonnent.ziele


def abmelde_link(cfg: AboKonfig, a: Abonnent) -> str:
    return f"{cfg.basis}/abo/abmelden.php?" + urlencode({"id": a.id, "t": a.abmelde_token})


def baue_mail(cfg: AboKonfig, a: Abonnent, treffer: list[Ereignis]) -> EmailMessage:
    if len(treffer) == 1:
        betreff = f"{cfg.seitenname}: {treffer[0].text}"
    else:
        betreff = f"{cfg.seitenname}: {len(treffer)} Neuigkeiten zu deinen Loipen"
    zeilen = ["Hallo,", "", "es gibt Neuigkeiten zu deinen Loipen:", ""]
    for e in treffer:
        zeilen.append(f"- {e.text}")
        if e.loipe_id is not None:
            zeilen.append(f"  {cfg.basis}/#/loipe/{e.loipe_id}")
    abmelden = abmelde_link(cfg, a)
    zeilen += [
        "",
        "Angaben laut der jeweiligen Quelle, ohne Gewähr. Vor Ort gelten Beschilderung und Sperrungen.",
        "",
        f"Du bekommst diese Mail, weil du das Abo am {a.bestaetigt_at:%d.%m.%Y} bestätigt hast.",
        f"Abmelden: {abmelden}",
    ]
    msg = EmailMessage()
    msg["Subject"] = betreff[:180]
    msg["From"] = formataddr((cfg.seitenname, cfg.absender))
    msg["To"] = a.email
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=urlsplit(cfg.basis).hostname or "localhost")
    msg["Auto-Submitted"] = "auto-generated"
    # RFC 2369 / RFC 8058: Abmelden direkt im Mailprogramm
    msg["List-Unsubscribe"] = f"<{abmelden}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content("\n".join(zeilen) + "\n")
    return msg


def mails_fuer(cfg: AboKonfig, abonnenten: list[Abonnent], ereignisse: list[Ereignis]) -> list[tuple[Abonnent, EmailMessage]]:
    """Eine Mail je Abonnent mit allen passenden Ereignissen dieses Laufs (N3)."""
    mails = []
    for a in abonnenten:
        treffer = [e for e in ereignisse if passt(a, e)]
        if treffer:
            mails.append((a, baue_mail(cfg, a, treffer)))
    return mails


def smtp_versand(cfg: AboKonfig) -> Callable[[list[EmailMessage]], list[Exception | None]]:
    """Schickt alle Mails eines Laufs ueber eine SMTP-Verbindung (Zugangsdaten nur in der .env)."""

    def senden(mails: list[EmailMessage]) -> list[Exception | None]:
        if not mails:
            return []
        kontext = ssl.create_default_context()
        if cfg.smtp_starttls:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30)
            server.starttls(context=kontext)
        else:
            server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30, context=kontext)
        ergebnisse: list[Exception | None] = []
        with server:
            if cfg.smtp_benutzer:
                server.login(cfg.smtp_benutzer, cfg.smtp_passwort or "")
            for m in mails:
                try:
                    server.send_message(m)
                    ergebnisse.append(None)
                except smtplib.SMTPException as ex:  # eine abgelehnte Adresse stoppt die anderen nicht
                    ergebnisse.append(ex)
        return ergebnisse

    return senden


def versende(session: Session, cfg: AboKonfig, ereignisse: list[Ereignis],
             versand: Callable[[list[EmailMessage]], list[Exception | None]], jetzt: datetime | None = None) -> int:
    if not ereignisse:
        return 0
    abonnenten = session.scalars(select(Abonnent).order_by(Abonnent.id)).all()
    paare = mails_fuer(cfg, list(abonnenten), ereignisse)
    if not paare:
        return 0
    ergebnisse = versand([m for _, m in paare])
    gesendet = 0
    for (a, _), fehler in zip(paare, ergebnisse):
        if fehler is None:
            a.letzte_mail_at = jetzt or utcnow()
            gesendet += 1
        else:
            log.warning("Abo-Mail an Abonnent %s abgelehnt: %s", a.id, fehler)
    return gesendet


def lauf_abo(session_factory, cfg: AboKonfig, ereignisse: list[Ereignis], push: Callable[[str, str], None] | None,
             http: httpx.Client | None = None, versand=None) -> tuple[Abgleich | None, int]:
    """Abgleich, Push der Meldungen, Versand. session_factory liefert einen Kontextmanager (session_scope)."""
    if not cfg.aktiv:
        return None, 0
    http = http or httpx.Client(timeout=30, headers={"User-Agent": "Loipenblick-NAS"})
    try:
        with session_factory() as session:
            abgleich = gleiche_ab(session, cfg, http)
        quittiere(cfg, http, abgleich.anzahl)
    except Exception as ex:
        log.warning("Abo-Abgleich mit dem Webspace fehlgeschlagen, keine Abo-Mails in diesem Lauf: %s", ex)
        return None, 0
    if push:
        for m in abgleich.meldungen:
            try:
                push(*meldung_als_push(m))
            except Exception:
                log.exception("Meldung nicht als Push gesendet")
    gesendet = 0
    if cfg.smtp_host or versand:
        try:
            with session_factory() as session:
                gesendet = versende(session, cfg, ereignisse, versand or smtp_versand(cfg))
        except Exception as ex:
            log.warning("Abo-Mails nicht versendet (SMTP): %s", ex)
            if push:
                try:
                    push("Loipenblick: Abo-Mails nicht versendet", f"SMTP-Fehler: {type(ex).__name__}")
                except Exception:
                    log.exception("Push ueber SMTP-Fehler nicht gesendet")
    log.info("Abo: %d neu, %d abgemeldet, %d Meldungen, %d Mails", abgleich.neu, abgleich.abgemeldet,
             len(abgleich.meldungen), gesendet)
    return abgleich, gesendet
