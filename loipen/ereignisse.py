"""Ereignisse erkennen und Abos bedienen (N1, N4) sowie Betriebsmeldungen (B2).

Ereignisse entstehen nur, wenn ein neuer Zustand gespeichert wird (D4). Der allererste Abruf einer
Loipe loest nichts aus, sonst gaebe es beim Start eine Flut von Meldungen.

- oeffnet:        vorher geschlossen oder unbekannt, jetzt offen oder eingeschraenkt
- schliesst:      vorher offen oder eingeschraenkt, jetzt geschlossen
- frisch_gespurt: vorher und jetzt befahrbar, aber die Quelle meldet eine neuere Praeparierung
                  oder mehr gespurte Kilometer
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Loipe, Status, Zustand

log = logging.getLogger("loipen.ereignisse")

ARTEN = ("oeffnet", "frisch_gespurt", "schliesst")
BEFAHRBAR = {Status.OFFEN.value, Status.EINGESCHRAENKT.value}
Sender = Callable[[str, str], None]  # (Titel, Text)


@dataclass
class Ereignis:
    art: str
    loipe: str
    gebiet: str  # slug
    gebiet_name: str
    region: str  # slug
    status: str
    gespurt_km: float | None = None
    loipe_id: int | None = None  # fuer E-Mail-Abos ("l:<id>", E-18)

    @property
    def text(self) -> str:
        satz = {"oeffnet": "ist jetzt befahrbar", "schliesst": "ist jetzt geschlossen",
                "frisch_gespurt": "wurde frisch gespurt"}[self.art]
        km = f", {self.gespurt_km:.1f} km gespurt".replace(".", ",") if self.gespurt_km and self.art != "schliesst" else ""
        return f"{self.loipe} ({self.gebiet_name}) {satz}{km}"


def erkenne(alt: Zustand | None, neu: Zustand) -> str | None:
    """Gibt die Art des Ereignisses zurueck oder None."""
    if alt is None:
        return None
    war, ist = alt.status in BEFAHRBAR, neu.status in BEFAHRBAR
    if not war and ist:
        return "oeffnet"
    if war and neu.status == Status.GESCHLOSSEN.value:
        return "schliesst"
    if war and ist:
        neuer = (
            neu.quelle_aktualisiert_at is not None
            and (alt.quelle_aktualisiert_at is None or neu.quelle_aktualisiert_at > alt.quelle_aktualisiert_at)
        )
        mehr = (neu.gespurt_gesamt_km or 0) > (alt.gespurt_gesamt_km or 0)
        if neuer or mehr:
            return "frisch_gespurt"
    return None


def ereignis_fuer(loipe: Loipe, alt: Zustand | None, neu: Zustand) -> Ereignis | None:
    art = erkenne(alt, neu)
    if art is None:
        return None
    g = loipe.gebiet
    return Ereignis(art, loipe.name, g.slug, g.name, g.region.slug, neu.status, neu.gespurt_gesamt_km, loipe.id)


# ---------- Abos ----------

def lade_abos(config_dir: Path = CONFIG_DIR) -> list[dict]:
    datei = config_dir / "abos.yaml"
    return lade_yaml(datei).get("abos", []) if datei.exists() else []


def pruefe_abos(abos: list[dict], gebiete: dict) -> list[str]:
    fehler = []
    gebiet_slugs = {g["slug"] for g in gebiete.get("gebiete", [])}
    region_slugs = {r["slug"] for r in gebiete.get("regionen", [])}
    for a in abos:
        name = a.get("name", "?")
        for art in a.get("ereignisse", ARTEN):
            if art not in ARTEN:
                fehler.append(f"Abo {name}: unbekanntes Ereignis {art}")
        if not (a.get("loipen") or a.get("gebiete") or a.get("regionen")):
            fehler.append(f"Abo {name}: weder Loipen noch Gebiete noch Regionen")
        for s in a.get("gebiete", []):
            if s not in gebiet_slugs:
                fehler.append(f"Abo {name}: unbekanntes Gebiet {s}")
        for s in a.get("regionen", []):
            if s not in region_slugs:
                fehler.append(f"Abo {name}: unbekannte Region {s}")
    return fehler


def passt(abo: dict, e: Ereignis) -> bool:
    """Ein Abo greift nur bei seinen Ereignissen und nur fuer seine Ziele (N1)."""
    if e.art not in abo.get("ereignisse", ARTEN):
        return False
    return (
        e.loipe in abo.get("loipen", [])
        or e.gebiet in abo.get("gebiete", [])
        or e.region in abo.get("regionen", [])
    )


def benachrichtige(abos: list[dict], ereignisse: list[Ereignis], sender: Sender | None) -> int:
    """Eine Nachricht je Abo und Lauf, mit allen passenden Ereignissen. Gibt die Anzahl gesendeter zurueck."""
    if sender is None:
        return 0
    gesendet = 0
    for abo in abos:
        treffer = [e for e in ereignisse if passt(abo, e)]
        if not treffer:
            continue
        titel = f"Loipenblick: {treffer[0].loipe}" if len(treffer) == 1 else f"Loipenblick: {len(treffer)} Neuigkeiten"
        text = "\n".join(e.text for e in treffer)
        for versuch in (1, 2):  # ein zweiter Versuch bei kurzem Netzfehler
            try:
                sender(titel, text)
                gesendet += 1
                break
            except Exception as ex:
                log.warning("Alarm fuer Abo %s fehlgeschlagen (Versuch %d): %s", abo.get("name"), versuch, ex)
    return gesendet


# ---------- ntfy (N4) ----------

def ntfy_sender(thema_url: str | None, client: httpx.Client | None = None) -> Sender | None:
    """thema_url z. B. https://ntfy.sh/mein-geheimes-thema. Ohne URL gibt es keinen Versand."""
    if not thema_url:
        return None
    teile = urlsplit(thema_url)
    basis, thema = f"{teile.scheme}://{teile.netloc}", teile.path.strip("/")
    if not thema:
        return None
    http = client or httpx.Client(timeout=15)

    def senden(titel: str, text: str) -> None:
        antwort = http.post(basis, json={"topic": thema, "title": titel, "message": text, "tags": ["ski"]})
        antwort.raise_for_status()

    return senden


# ---------- Betriebsmeldungen (B2) ----------

def betriebsmeldung(quelle: str, vorher: str | None, jetzt: str | None, fehler: str | None) -> tuple[str, str] | None:
    """Meldung nur beim Wechsel des Zustands einer Quelle. Der Worker nutzt seit B26 den Quellen-Waechter
    (loipen/waechter.py), der kurze Stoerungen abwartet und auch Einbrueche erkennt."""
    if vorher == jetzt:
        return None
    if jetzt in ("fehler", "warnung"):
        return f"Loipenblick: Quelle {quelle} meldet {jetzt}", fehler or "keine Angabe"
    if jetzt == "ok" and vorher in ("fehler", "warnung"):
        return f"Loipenblick: Quelle {quelle} läuft wieder", "Der letzte Abruf war in Ordnung."
    return None
