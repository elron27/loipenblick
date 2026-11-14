"""Zuordnungstabellen und Parser fuer Quelltexte (P5, P6).

Die Tabellen sind Daten: ein neues Wort der Quelle kommt hier als Zeile dazu, nicht als
if-Kette in einen Adapter. Unbekannte Woerter werden nie verschluckt, der Aufrufer bekommt
sie zurueck und protokolliert sie mit Quelle und Rohtext.
"""

import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from loipen.models import Schwierigkeit, Status

BERLIN = ZoneInfo("Europe/Berlin")

# Quelltext (klein geschrieben, ohne "Loipenzustand:") -> normierter Status
ZUSTAND: dict[str, Status] = {
    "geöffnet": Status.OFFEN,
    "offen": Status.OFFEN,
    "befahrbar": Status.OFFEN,
    "fahrbar": Status.OFFEN,
    "top": Status.OFFEN,
    "gespurt": Status.OFFEN,
    "präpariert": Status.OFFEN,
    "sehr gut": Status.OFFEN,
    "gut": Status.OFFEN,
    "bedingt befahrbar": Status.EINGESCHRAENKT,
    "eingeschränkt": Status.EINGESCHRAENKT,
    "befriedigend": Status.EINGESCHRAENKT,
    "mittel": Status.EINGESCHRAENKT,
    # Oesterreich (P18): tirol.at, Kitzbueheler Alpen, langlaufdorf.at
    "teilweise geöffnet": Status.EINGESCHRAENKT,
    "teilgeöffnet": Status.EINGESCHRAENKT,
    "teilweise offen": Status.EINGESCHRAENKT,
    "eingeschränkt befahrbar": Status.EINGESCHRAENKT,
    "nur eingeschränkt befahrbar": Status.EINGESCHRAENKT,
    "teilweise gespurt": Status.EINGESCHRAENKT,
    "in betrieb": Status.OFFEN,
    "außer betrieb": Status.GESCHLOSSEN,
    # Italienisch fuer Suedtirol (P12)
    "aperta": Status.OFFEN,
    "aperto": Status.OFFEN,
    "battuta": Status.OFFEN,
    "parzialmente aperta": Status.EINGESCHRAENKT,
    "parzialmente aperto": Status.EINGESCHRAENKT,
    "chiusa": Status.GESCHLOSSEN,
    "chiuso": Status.GESCHLOSSEN,
    # Statuscodes von Dolomiti NordicSki (P23): td[data-status]
    "open": Status.OFFEN,
    "partially_open": Status.EINGESCHRAENKT,
    "open_not_prepared": Status.EINGESCHRAENKT,
    "closed": Status.GESCHLOSSEN,
    "unknown": Status.UNBEKANNT,
    # Schweiz (P25, P26): Zustandswoerter von infosnow.ch (Schweiz Tourismus) und tourinfra
    "gut-fahrbar": Status.OFFEN,
    "gut fahrbar": Status.OFFEN,
    "sehr gut-fahrbar": Status.OFFEN,
    "schlecht": Status.EINGESCHRAENKT,
    "frühlingsverhältnisse": Status.EINGESCHRAENKT,
    "saisonschluss": Status.GESCHLOSSEN,
    "saisonvorbereitung": Status.GESCHLOSSEN,
    "betriebssperre": Status.GESCHLOSSEN,
    "keine meldung": Status.UNBEKANNT,
    "good": Status.OFFEN,
    "very good": Status.OFFEN,
    "fair-good": Status.OFFEN,
    "mittel-gut": Status.OFFEN,
    "fair": Status.EINGESCHRAENKT,
    "poor": Status.EINGESCHRAENKT,
    "end of season": Status.GESCHLOSSEN,
    "no report": Status.UNBEKANNT,
    "nicht befahrbar": Status.GESCHLOSSEN,
    "geschlossen": Status.GESCHLOSSEN,
    "gesperrt": Status.GESCHLOSSEN,
    # bekannt, aber ohne Aussage
    "k.a.": Status.UNBEKANNT,
    "unbekannt": Status.UNBEKANNT,
    "": Status.UNBEKANNT,
}

# Farben der Loipenkarte und Worte der Listen -> Schwierigkeit
SCHWIERIGKEIT: dict[str, Schwierigkeit] = {
    "leicht": Schwierigkeit.LEICHT,
    "blau": Schwierigkeit.LEICHT,
    "mittel": Schwierigkeit.MITTEL,
    "mittelschwierig": Schwierigkeit.MITTEL,
    "mittelschwer": Schwierigkeit.MITTEL,
    "rot": Schwierigkeit.MITTEL,
    "schwer": Schwierigkeit.SCHWER,
    "schwarz": Schwierigkeit.SCHWER,
    "schwierig": Schwierigkeit.SCHWER,
    "facile": Schwierigkeit.LEICHT,
    "medio": Schwierigkeit.MITTEL,
    "difficile": Schwierigkeit.SCHWER,
    "k.a.": Schwierigkeit.UNBEKANNT,
    "": Schwierigkeit.UNBEKANNT,
}


def _schluessel(text: str | None) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"^loipenzustand\s*:\s*", "", text)
    return re.sub(r"\s+", " ", text)


def normiere_zustand(text: str | None) -> tuple[Status, bool]:
    """Gibt (Status, bekannt) zurueck. Unbekannter Text ergibt (UNBEKANNT, False)."""
    schluessel = _schluessel(text)
    if schluessel in ZUSTAND:
        return ZUSTAND[schluessel], True
    return Status.UNBEKANNT, False


def normiere_schwierigkeit(text: str | None) -> tuple[Schwierigkeit, bool]:
    schluessel = _schluessel(text)
    if schluessel in SCHWIERIGKEIT:
        return SCHWIERIGKEIT[schluessel], True
    return Schwierigkeit.UNBEKANNT, False


_ZAHL = re.compile(r"-?\d+(?:\.\d{3})*(?:,\d+)?|-?\d+(?:\.\d+)?")


def parse_zahl(text: str | None) -> float | None:
    """'9,0km' -> 9.0, '1.234,5 km' -> 1234.5, '8 km' -> 8.0. Ohne Zahl None (P6)."""
    if not text:
        return None
    treffer = _ZAHL.search(text.replace("\xa0", " "))
    if not treffer:
        return None
    zahl = treffer.group(0)
    if "," in zahl:
        zahl = zahl.replace(".", "").replace(",", ".")
    return float(zahl)


_DATUM = re.compile(
    r"(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})(?:\s*(?:um\s*|/\s*|,\s*)?(\d{1,2}):(\d{2})(?:\s*Uhr)?)?"
)


def parse_datum(text: str | None) -> datetime | None:
    """'Daten zuletzt aktualisiert am 02.01.26 um 08:53 Uhr' -> 2026-01-02 08:53 Europe/Berlin.

    Zweistellige Jahre gelten als 20xx. Die Zeitzone wird gesetzt, nicht umgerechnet, damit
    Sommer- und Winterzeit stimmen.
    """
    if not text:
        return None
    treffer = _DATUM.search(text)
    if not treffer:
        return None
    tag, monat, jahr, stunde, minute = treffer.groups()
    jahr_i = int(jahr)
    if jahr_i < 100:
        jahr_i += 2000
    try:
        return datetime(jahr_i, int(monat), int(tag), int(stunde or 0), int(minute or 0), tzinfo=BERLIN)
    except ValueError:
        return None


def parse_ja_nein(text: str | None) -> bool | None:
    schluessel = _schluessel(text)
    if schluessel in {"ja", "yes", "true"}:
        return True
    if schluessel in {"nein", "no", "false"}:
        return False
    return None


def slugify(text: str) -> str:
    """'KU1 Weissach I' -> 'ku1-weissach-i', Umlaute als ae/oe/ue, Satzzeichen fallen weg ('1,5 km' -> '15-km')."""
    t = text.strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    return re.sub(r"[\s-]+", "-", t).strip("-")
