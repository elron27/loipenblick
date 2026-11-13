"""Quellen-Waechter (B26): merkt, wenn eine Quelle ploetzlich kaputt wirkt, und sagt Stefan Bescheid.

Meist steckt eine geaenderte Webseite dahinter: der Adapter findet nichts mehr (0 Loipen), nur noch einen
Teil (Einbruch) oder bricht mit einem Fehler ab. Jeder Abruf landet im Abrufprotokoll. Der Waechter
vergleicht die Anzahl mit dem ueblichen Wert der Quelle (Median der letzten unauffaelligen Abrufe).

Damit eine kurze Stoerung (Zeitueberschreitung, Wartung) keinen Alarm ausloest, meldet er erst, wenn
`bestaetigen` Abrufe hintereinander auffaellig waren. Danach erinnert er hoechstens alle `erinnern_h`
Stunden und gibt Entwarnung, sobald die Quelle wieder normal liefert. Liefert eine Quelle ueber
`neu_normal_tage` stabil weniger, gilt das als neuer Normalwert (z. B. weil der Ort Loipen gestrichen hat).

Gemeldet wird per ntfy-Push (N4) und per Mail an LOIPEN_WAECHTER_MAIL ueber den SMTP-Zugang des
Mail-Abos (E-18). Beides ist optional; ohne Kanal steht der Befund nur im Log.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from statistics import median
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import Abrufprotokoll, Quelle

log = logging.getLogger("loipen.waechter")

STANDARD = {"bestaetigen": 2, "einbruch_anteil": 0.5, "einbruch_ab": 4, "erinnern_h": 24, "neu_normal_tage": 7}
GRUNDWERT_AUS = 10  # so viele unauffaellige Abrufe ergeben den ueblichen Wert
BEFUNDE = {"fehler": "Abruf schlägt fehl", "leer": "liefert 0 Loipen", "einbruch": "liefert deutlich weniger Loipen"}
BERLIN = ZoneInfo("Europe/Berlin")


@dataclass
class Meldung:
    art: str  # alarm, wechsel, erinnerung, entwarnung, neu_normal
    quelle: str  # key
    name: str
    url: str
    befund: str | None
    anzahl: int
    ueblich: int | None
    seit: datetime | None
    fehler: str | None = None

    def _seit(self) -> str:
        return self.seit.astimezone(BERLIN).strftime("%d.%m. %H:%M") if self.seit else "?"

    def _was(self) -> str:
        if self.befund == "einbruch":
            return f"liefert nur {self.anzahl} statt üblich {self.ueblich} Loipen"
        return BEFUNDE.get(self.befund or "", "ist auffällig")

    @property
    def titel(self) -> str:
        if self.art == "entwarnung":
            return f"Quellen-Wächter: {self.name} läuft wieder"
        if self.art == "neu_normal":
            return f"Quellen-Wächter: {self.name} liefert dauerhaft weniger"
        if self.art == "erinnerung":
            return f"Quellen-Wächter: {self.name} weiterhin gestört"
        return f"Quellen-Wächter: {self.name} {BEFUNDE.get(self.befund or '', 'ist auffällig')}"

    @property
    def text(self) -> str:
        if self.art == "entwarnung":
            ueblich = f" (üblich {self.ueblich})" if self.ueblich else ""
            return f"Wieder {self.anzahl} Loipen{ueblich}. Gestört seit {self._seit()}."
        if self.art == "neu_normal":
            return (f"Seit {self._seit()} kommen nur noch {self.anzahl} statt {self.ueblich} Loipen. "
                    "Das gilt ab jetzt als normal. Falls nicht, Adapter prüfen.")
        satz = f"Die Quelle {self._was()}, seit {self._seit()}."
        if self.art == "erinnerung":
            satz = f"Immer noch: Die Quelle {self._was()}, seit {self._seit()}."
        if self.art == "wechsel":
            satz = f"Jetzt: Die Quelle {self._was()} (gestört seit {self._seit()})."
        if self.fehler and self.befund == "fehler":
            satz += f" Fehler: {self.fehler[:300]}"
        return satz


def einstellungen(quelle: Quelle) -> dict:
    return {**STANDARD, **((quelle.config or {}).get("waechter") or {})}


def grundwert(session: Session, quelle: Quelle, ohne_id: int | None = None) -> int | None:
    """Ueblicher Wert: Median der letzten unauffaelligen Abrufe (ohne den aktuellen)."""
    abfrage = (select(Abrufprotokoll.anzahl)
               .where(Abrufprotokoll.quelle_id == quelle.id, Abrufprotokoll.befund.is_(None),
                      Abrufprotokoll.status != "fehler")
               .order_by(Abrufprotokoll.zeit.desc(), Abrufprotokoll.id.desc()).limit(GRUNDWERT_AUS))
    if ohne_id is not None:
        abfrage = abfrage.where(Abrufprotokoll.id != ohne_id)
    werte = list(session.scalars(abfrage))
    return round(median(werte)) if werte else None


def befund(eintrag: Abrufprotokoll, ueblich: int | None, cfg: dict) -> str | None:
    if eintrag.status == "fehler":
        return "fehler"
    if eintrag.anzahl == 0:
        return "leer"
    if ueblich and ueblich >= cfg["einbruch_ab"] and eintrag.anzahl < ueblich * cfg["einbruch_anteil"]:
        return "einbruch"
    return None


def pruefe(session: Session, quelle: Quelle, anzahl: int, status: str, fehler: str | None,
           dauer_s: float | None, jetzt: datetime) -> Meldung | None:
    """Schreibt den Abruf ins Protokoll und gibt eine Meldung zurueck, wenn Stefan etwas wissen soll."""
    cfg = einstellungen(quelle)
    eintrag = Abrufprotokoll(quelle_id=quelle.id, zeit=jetzt, anzahl=anzahl, status=status,
                             fehler=fehler if status == "fehler" or anzahl == 0 else None, dauer_s=dauer_s)
    session.add(eintrag)
    session.flush()
    ueblich = grundwert(session, quelle, ohne_id=eintrag.id)

    def meldung(art: str, b: str | None) -> Meldung:
        return Meldung(art, quelle.key, quelle.name, quelle.base_url, b, anzahl, ueblich,
                       quelle.waechter_seit, quelle.last_error if b in ("fehler", "leer") else None)

    b = befund(eintrag, ueblich, cfg)
    eintrag.befund = b
    if cfg.get("aus"):
        quelle.waechter_alarm = quelle.waechter_seit = quelle.waechter_gemeldet_at = None
        return None

    # Neuer Normalwert: lange stabil weniger, aber nicht leer und ohne Fehler
    if (b == "einbruch" and quelle.waechter_alarm == "einbruch" and quelle.waechter_seit
            and jetzt - quelle.waechter_seit >= timedelta(days=cfg["neu_normal_tage"])):
        seit = quelle.waechter_seit
        for e in session.scalars(select(Abrufprotokoll).where(
                Abrufprotokoll.quelle_id == quelle.id, Abrufprotokoll.zeit >= seit,
                Abrufprotokoll.befund == "einbruch")):
            e.befund = None
        m = meldung("neu_normal", "einbruch")
        quelle.waechter_alarm = quelle.waechter_seit = quelle.waechter_gemeldet_at = None
        return m

    if b is None:
        if quelle.waechter_alarm:
            m = meldung("entwarnung", None)
            quelle.waechter_alarm = quelle.waechter_seit = quelle.waechter_gemeldet_at = None
            return m
        return None

    if quelle.waechter_alarm is None:
        reihe = list(session.scalars(
            select(Abrufprotokoll).where(Abrufprotokoll.quelle_id == quelle.id)
            .order_by(Abrufprotokoll.zeit.desc(), Abrufprotokoll.id.desc()).limit(int(cfg["bestaetigen"]))))
        if len(reihe) < int(cfg["bestaetigen"]) or any(e.befund is None for e in reihe):
            return None  # noch nicht bestaetigt, vielleicht nur eine kurze Stoerung
        quelle.waechter_alarm, quelle.waechter_seit, quelle.waechter_gemeldet_at = b, reihe[-1].zeit, jetzt
        return meldung("alarm", b)

    if b != quelle.waechter_alarm:
        quelle.waechter_alarm, quelle.waechter_gemeldet_at = b, jetzt
        return meldung("wechsel", b)
    if quelle.waechter_gemeldet_at is None or jetzt - quelle.waechter_gemeldet_at >= timedelta(hours=cfg["erinnern_h"]):
        quelle.waechter_gemeldet_at = jetzt
        return meldung("erinnerung", b)
    return None


# ---------- Versand ----------

def baue_mail(meldungen: list[Meldung], an: str, absender: str, seitenname: str = "Loipenblick") -> EmailMessage:
    """Eine Mail je Lauf mit allen Meldungen, dazu was zu tun ist."""
    stoerungen = [m for m in meldungen if m.art not in ("entwarnung", "neu_normal")]
    if len(meldungen) == 1:
        betreff = meldungen[0].titel
    elif stoerungen:
        betreff = f"Quellen-Wächter: {len(stoerungen)} Quellen gestört"
    else:
        betreff = f"Quellen-Wächter: {len(meldungen)} Quellen wieder in Ordnung"
    zeilen = [f"{seitenname} hat bei den Quellen etwas bemerkt:", ""]
    for m in meldungen:
        zeilen += [f"- {m.titel.removeprefix('Quellen-Wächter: ')}", f"  {m.text}", f"  Quelle: {m.url}", ""]
    if stoerungen:
        zeilen += [
            "Was tun:",
            "1. Die Quelle im Browser öffnen: Gibt es die Seite noch, sieht sie anders aus?",
            "2. Neuen Schnappschuss holen (Workflow „Schnappschuss“ oder scripts/schnappschuss.py).",
            "3. Erst einen Fixture-Test schreiben, der den Fehler zeigt, dann den Adapter reparieren (CLAUDE.md Regel 10).",
            "Kein Handlungsbedarf, wenn die Quelle nur kurz offline ist: Dann kommt automatisch eine Entwarnung.",
            "",
        ]
    zeilen.append("Diese Mail schickt der Worker auf dem NAS. Abschalten: waechter in config/sources.yaml oder LOIPEN_WAECHTER_MAIL leeren.")
    msg = EmailMessage()
    msg["Subject"] = betreff[:180]
    msg["From"] = formataddr((f"{seitenname} Wächter", absender))
    msg["To"] = an
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=absender.rpartition("@")[2] or "localhost")
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content("\n".join(zeilen) + "\n")
    return msg


def melde(meldungen: list[Meldung], push: Callable[[str, str], None] | None,
          mail: Callable[[EmailMessage], None] | None, an: str | None, absender: str | None) -> dict:
    """Push je Meldung, eine Mail fuer alle. Ein Versandfehler stoppt den anderen Kanal nicht."""
    ergebnis = {"push": 0, "mail": 0}
    if not meldungen:
        return ergebnis
    for m in meldungen:
        log.warning("%s: %s", m.titel, m.text)
        if push:
            try:
                push(m.titel, m.text)
                ergebnis["push"] += 1
            except Exception:
                log.exception("Waechter-Push nicht gesendet")
    if mail and an and absender:
        try:
            mail(baue_mail(meldungen, an, absender))
            ergebnis["mail"] = 1
        except Exception:
            log.exception("Waechter-Mail nicht gesendet")
    return ergebnis
