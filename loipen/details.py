"""Stammdaten einer Loipe mit Herkunft (D21, P42, P43, E-40).

Stammdaten sind Angaben, die sich selten aendern: Hoehenmeter, hoechster und tiefster Punkt, Dauer,
Kondition, Technikbewertung, Merkmale, Webcams. Sie kommen aus Detailseiten der Quellen (herkunft
"quelle"), aus dem Hoehenmodell ("berechnet"), aus OpenStreetMap ("osm") oder von Hand ("hand").

Regeln (D21):
- Jede Angabe traegt in Loipe.herkunft ihre Herkunft, eine Quell-URL und ein Pruefdatum.
- Eine Handangabe geht vor, eine automatische ueberschreibt sie nie. Eine Quellangabe geht einer
  berechneten vor.
- Gepflegte Stammdaten liegen als YAML unter config/stammdaten/ und werden bei jedem Lauf uebernommen:
  {quellen: {<quelle_key>: {<source_key>: {feld: wert, ..., url, geprueft_am}}}}
"""

from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.models import Loipe, Quelle

FELDER = ("hoehenmeter", "hoechster_punkt_m", "tiefster_punkt_m", "dauer_min", "kondition", "technik_note",
          "merkmale", "webcams")
RANG = {"hand": 4, "quelle": 3, "osm": 2, "berechnet": 1}

# D21 AK 2: feste Liste der Merkmale. Schluessel = gespeicherter Wert, Wert = Anzeigetext.
MERKMALE = {
    "einkehr": "Einkehr",
    "familientauglich": "familientauglich",
    "hoehenloipe": "Höhenloipe",
    "bergbahn": "mit Bergbahn erreichbar",
    "schneesicher": "schneesicher",
    "hundeloipe": "Hunde erlaubt",
    "kunstschnee": "Kunstschnee",
    "nachtloipe": "Nachtloipe",
    "kostenlos": "kostenlos",
}

# Begriffe der Quellen (klein geschrieben, ohne Klammerzusatz) -> Merkmal
BEGRIFFE = {
    "einkehrmöglichkeit": "einkehr",
    "einkehrmöglichkeiten": "einkehr",
    "mit einkehrmöglichkeit": "einkehr",
    "familientauglich": "familientauglich",
    "familienfreundlich": "familientauglich",
    "für kinder geeignet": "familientauglich",
    "höhenloipe": "hoehenloipe",
    "mit bergbahn/lift erreichbar": "bergbahn",
    "mit bergbahn erreichbar": "bergbahn",
    "mit lift erreichbar": "bergbahn",
    "schneesicher": "schneesicher",
    "hundeloipe": "hundeloipe",
    "hunde erlaubt": "hundeloipe",
    "mit hund": "hundeloipe",
    "kunstschnee": "kunstschnee",
    "beschneit": "kunstschnee",
    "nachtloipe": "nachtloipe",
    "beleuchtet": "nachtloipe",
    "flutlicht": "nachtloipe",
    "kostenfrei": "kostenlos",
    "kostenlos": "kostenlos",
}

# Merkmale der Quellen, die bewusst nicht uebernommen werden (Werbeetiketten ohne Nutzen fuer die Wahl)
IGNORIERT = {"highlight tour", "top tour", "ausgewiesene loipe", "geführte tour", "rundtour",
             "streckentour", "kulturell / historisch", "botanische highlights", "faunistische highlights",
             "geologische highlights", "aussichtsreich", "kulturell/historisch", "einkehrmöglichkeit vorhanden"}


def normiere_merkmal(text: str) -> str | None:
    """'Höhenloipe (Großteil über 1000m)' -> 'hoehenloipe'; unbekannt -> None."""
    t = text.strip().lower()
    t = t.split("(")[0].strip()
    return BEGRIFFE.get(t)


def merkmale_aus(texte: list[str]) -> tuple[list[str], list[str]]:
    """Gibt (Merkmale der festen Liste, unbekannte Begriffe) zurueck."""
    gefunden: list[str] = []
    unbekannt: list[str] = []
    for text in texte:
        m = normiere_merkmal(text)
        if m:
            if m not in gefunden:
                gefunden.append(m)
        elif text.strip() and text.strip().lower().split("(")[0].strip() not in IGNORIERT:
            unbekannt.append(text.strip())
    return gefunden, unbekannt


def uebernimm_stammdaten(loipe: Loipe, werte: dict, herkunft: str, url: str | None = None,
                         geprueft_am: date | str | None = None) -> list[str]:
    """Setzt die Felder aus werte, die nicht leer sind und keine hoeherrangige Angabe ueberschreiben.

    Gibt die gesetzten Felder zurueck."""
    if herkunft not in RANG:
        raise ValueError(f"unbekannte Herkunft {herkunft!r}")
    stand = str(geprueft_am or date.today().isoformat())
    bisher = dict(loipe.herkunft or {})
    gesetzt = []
    for feld in FELDER:
        wert = werte.get(feld)
        if wert is None or wert == []:
            continue
        alt = bisher.get(feld)
        if alt and RANG.get(alt.get("herkunft"), 0) > RANG[herkunft]:
            continue
        if feld == "merkmale":
            wert = [m for m in wert if m in MERKMALE]
            if not wert:
                continue
        setattr(loipe, feld, wert)
        bisher[feld] = {"herkunft": herkunft, "url": url or werte.get("url"), "geprueft_am": stand}
        gesetzt.append(feld)
    if gesetzt:
        loipe.herkunft = bisher  # neues Objekt, damit SQLAlchemy die JSON-Aenderung sieht
    return gesetzt


def lade_stammdaten(session: Session, verzeichnis: Path) -> int:
    """Uebernimmt config/stammdaten/*.yaml in die Datenbank. Gibt die Zahl der geaenderten Loipen zurueck."""
    if not verzeichnis.is_dir():
        return 0
    quellen = {q.key: q.id for q in session.scalars(select(Quelle))}
    anzahl = 0
    for pfad in sorted(verzeichnis.glob("*.yaml")):
        inhalt = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        herkunft = inhalt.get("herkunft", "quelle")
        for quelle_key, loipen in (inhalt.get("quellen") or {}).items():
            qid = quellen.get(quelle_key)
            if qid is None or not loipen:
                continue
            bestand = {l.source_key: l for l in session.scalars(select(Loipe).where(Loipe.quelle_id == qid))}
            for source_key, werte in loipen.items():
                loipe = bestand.get(str(source_key))
                if loipe is None or not werte:
                    continue
                h = werte.get("herkunft", herkunft)
                if uebernimm_stammdaten(loipe, werte, h, werte.get("url"), werte.get("geprueft_am")):
                    anzahl += 1
    session.flush()
    return anzahl
