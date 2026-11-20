"""Benachrichtigung einzelner Loipen: Doppelversand vermeiden (N11) und oeffentlicher Push ohne Konto (N10).

N11 Entprellen: Ereignisse entstehen bei jedem Statuswechsel (ereignisse.py). Meldet eine Quelle kurz
"unbekannt" und danach wieder "offen", entstuende ein zweites "ist jetzt befahrbar". Darum merkt sich das
Meldeprotokoll je Loipe, was zuletzt gemeldet wurde, und haelt Wiederholungen zurueck. Das gilt fuer
alle Kanaele: Push fuer den Betreiber (abos.yaml), oeffentlicher Push und E-Mail-Abo.

- oeffnet / schliesst: nicht erneut, wenn dieselbe Art schon zuletzt gemeldet wurde und das weniger als
  `status_h` Stunden her ist. Ein gegenlaeufiger Wechsel (schliesst nach oeffnet) geht immer durch.
- frisch_gespurt: hoechstens einmal in `gespurt_h` Stunden, und nicht kurz nach "oeffnet".

N10 Oeffentlicher Push: Jede Loipe und jedes Gebiet hat ein ntfy-Thema (`<praefix>-l<id>`,
`<praefix>-g-<gebiet>`). Wer es in der ntfy-App abonniert, bekommt die Nachrichten ohne Konto und ohne
dass wir etwas ueber ihn speichern. Je Thema und Lauf hoechstens eine Nachricht. ntfy.sh begrenzt die
Nachrichten je Absender und Tag; deshalb gibt es eine Tagesgrenze, Gebietsthemen gehen zuerst.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from loipen.ereignisse import Ereignis
from loipen.models import Meldeprotokoll, PushTag, utcnow

log = logging.getLogger("loipen.benachrichtigung")

STATUS_H = 48
GESPURT_H = 18


# ---------- N11: Entprellen ----------

def entprelle(session: Session, ereignisse: list[Ereignis], jetzt: datetime | None = None,
              status_h: float = STATUS_H, gespurt_h: float = GESPURT_H) -> list[Ereignis]:
    """Gibt die Ereignisse zurueck, die gemeldet werden duerfen, und traegt sie ins Meldeprotokoll ein."""
    jetzt = jetzt or utcnow()
    bleiben = []
    for e in ereignisse:
        if e.loipe_id is None:
            bleiben.append(e)
            continue
        p = session.get(Meldeprotokoll, e.loipe_id)
        if p is None:
            p = Meldeprotokoll(loipe_id=e.loipe_id)
            session.add(p)
        if e.art in ("oeffnet", "schliesst"):
            if p.status_art == e.art and p.status_at and jetzt - p.status_at < timedelta(hours=status_h):
                log.info("%s fuer %s nicht erneut gemeldet (N11)", e.art, e.loipe)
                continue
            p.status_art, p.status_at = e.art, jetzt
            if e.art == "oeffnet":
                p.befahrbar_at = jetzt
        elif e.art == "frisch_gespurt":
            if p.befahrbar_at and jetzt - p.befahrbar_at < timedelta(hours=gespurt_h):
                log.info("frisch_gespurt fuer %s zurueckgehalten, schon gemeldet (N11)", e.loipe)
                continue
            p.befahrbar_at = jetzt
        bleiben.append(e)
    session.flush()
    return bleiben


# ---------- N10: Oeffentlicher Push ueber ntfy ----------

_ERLAUBT = re.compile(r"[^A-Za-z0-9_-]")


def thema_teil(text: str) -> str:
    """ntfy erlaubt in Themen nur Buchstaben, Ziffern, - und _ (hoechstens 64 Zeichen)."""
    return _ERLAUBT.sub("-", text)


def gueltiges_praefix(praefix: str | None) -> str | None:
    if not praefix:
        return None
    return praefix if re.fullmatch(r"[A-Za-z0-9_-]{3,40}", praefix) else None


def thema_loipe(praefix: str, loipe_id: int) -> str:
    return f"{praefix}-l{loipe_id}"


def thema_gebiet(praefix: str, slug: str) -> str:
    return f"{praefix}-g-{thema_teil(slug)}"[:64]


@dataclass
class PushKonfig:
    """Aus der .env (B4). Ohne praefix ist der oeffentliche Push aus und die Seite zeigt ihn nicht."""

    praefix: str | None = None  # LOIPEN_PUSH_PRAEFIX, z. B. loipenblick-x7q
    server: str = "https://ntfy.sh"
    token: str | None = None  # ntfy-Zugangstoken, wenn Stefan ein Konto mit Themen-Reservierung nutzt
    max_tag: int = 150  # ntfy.sh ohne Konto: 250 Nachrichten am Tag je Absender, Rest fuer Betreiber-Push
    seite_url: str | None = None  # Klick auf die Nachricht oeffnet die Loipe
    zeitzone: str = "Europe/Berlin"

    @property
    def aktiv(self) -> bool:
        return gueltiges_praefix(self.praefix) is not None

    @property
    def basis(self) -> str:
        return self.server.rstrip("/")

    def fuer_seite(self) -> dict | None:
        """Was die Seite braucht, um die Themen anzuzeigen (daten.json)."""
        if not self.aktiv:
            return None
        return {"server": self.basis, "praefix": self.praefix}

    @classmethod
    def aus_settings(cls, s) -> "PushKonfig":
        return cls(praefix=s.push_praefix, server=s.push_server or "https://ntfy.sh", token=s.push_token,
                   max_tag=s.push_max_tag, seite_url=s.oeffentliche_url, zeitzone=s.timezone)


@dataclass
class Nachricht:
    thema: str
    titel: str
    text: str
    klick: str | None = None
    gebiet: bool = False


HINWEIS = "Angaben laut Quelle, ohne Gewähr."


def nachrichten(cfg: PushKonfig, ereignisse: list[Ereignis]) -> list[Nachricht]:
    """Je Thema eine Nachricht: Gebietsthemen buendeln alle Ereignisse ihres Gebiets in diesem Lauf."""
    if not cfg.aktiv:
        return []
    basis = (cfg.seite_url or "").rstrip("/")
    gebiete: dict[str, list[Ereignis]] = {}
    loipen: list[Nachricht] = []
    for e in ereignisse:
        gebiete.setdefault(e.gebiet, []).append(e)
        if e.loipe_id is not None:
            loipen.append(Nachricht(thema_loipe(cfg.praefix, e.loipe_id), e.loipe, f"{e.text}\n{HINWEIS}",
                                    f"{basis}/#/loipe/{e.loipe_id}" if basis else None))
    ergebnis = []
    for slug, liste in gebiete.items():
        name = liste[0].gebiet_name
        titel = name if len(liste) == 1 else f"{name}: {len(liste)} Neuigkeiten"
        ergebnis.append(Nachricht(thema_gebiet(cfg.praefix, slug), titel,
                                  "\n".join(e.text for e in liste[:15])
                                  + (f"\n… und {len(liste) - 15} weitere" if len(liste) > 15 else "") + f"\n{HINWEIS}",
                                  f"{basis}/#/gebiet/{slug}" if basis else None, gebiet=True))
    # doppelte Loipen-Themen (zwei Ereignisse derselben Loipe in einem Lauf) zusammenfassen
    je_thema: dict[str, Nachricht] = {}
    for n in loipen:
        if n.thema in je_thema:
            alt = je_thema[n.thema]
            alt.text = alt.text.replace(f"\n{HINWEIS}", "") + "\n" + n.text
        else:
            je_thema[n.thema] = n
    return ergebnis + list(je_thema.values())


Senden = Callable[[Nachricht], None]


def ntfy_senden(cfg: PushKonfig, client: httpx.Client | None = None) -> Senden:
    http = client or httpx.Client(timeout=15)
    kopf = {"Authorization": f"Bearer {cfg.token}"} if cfg.token else {}

    def senden(n: Nachricht) -> None:
        daten = {"topic": n.thema, "title": n.titel[:200], "message": n.text[:3000], "tags": ["ski"]}
        if n.klick:
            daten["click"] = n.klick
        antwort = http.post(cfg.basis, json=daten, headers=kopf)
        antwort.raise_for_status()

    return senden


def _heute(cfg: PushKonfig, jetzt: datetime):
    return jetzt.astimezone(ZoneInfo(cfg.zeitzone)).date()


def veroeffentliche(session: Session, cfg: PushKonfig, ereignisse: list[Ereignis], senden: Senden | None = None,
                    betreiber: Callable[[str, str], None] | None = None, jetzt: datetime | None = None) -> int:
    """Schickt die Nachrichten bis zur Tagesgrenze. Gibt die Anzahl gesendeter zurueck."""
    liste = nachrichten(cfg, ereignisse)
    if not liste:
        return 0
    senden = senden or ntfy_senden(cfg)
    jetzt = jetzt or utcnow()
    tag = session.get(PushTag, _heute(cfg, jetzt))
    if tag is None:
        tag = PushTag(tag=_heute(cfg, jetzt), anzahl=0, grenze_gemeldet=False)
        session.add(tag)
    gesendet = 0
    for n in liste:  # Gebietsthemen stehen vorn
        if tag.anzahl >= cfg.max_tag:
            uebrig = len(liste) - gesendet
            log.warning("Push-Tagesgrenze %d erreicht, %d Nachrichten nicht gesendet (N10)", cfg.max_tag, uebrig)
            if betreiber and not tag.grenze_gemeldet:
                try:
                    betreiber("Loipenblick: Push-Tagesgrenze erreicht",
                              f"Heute gingen {tag.anzahl} öffentliche Push-Nachrichten raus, die Grenze ist "
                              f"{cfg.max_tag} (LOIPEN_PUSH_MAX_TAG). Weitere Nachrichten kommen erst morgen. "
                              "E-Mail-Abos laufen weiter.")
                    tag.grenze_gemeldet = True
                except Exception:
                    log.exception("Meldung ueber die Push-Grenze nicht gesendet")
            break
        try:
            senden(n)
            tag.anzahl += 1
            gesendet += 1
        except Exception as ex:
            log.warning("Push an Thema %s fehlgeschlagen: %s", n.thema, ex)
    session.flush()
    return gesendet
