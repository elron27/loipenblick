"""Dubletten ueber mehrere Quellen (D15, P15).

Dieselbe Loipe steht oft bei mehreren Quellen: tirol.at fuehrt auch Bayrischzeller Loipen, die
Kitzbueheler Alpen dieselben Loipen wie tirol.at. Jede Loipe wird einmal gezeigt, und zwar von der
fuehrenden Quelle (kleinster rang in sources.yaml); die anderen Eintraege stehen dort als "auch bei".

Regel: zwei Eintraege verschiedener Quellen sind dieselbe Loipe, wenn
- der Name aehnlich ist (Vergleich ohne Ortsnamen und Fuellwoerter wie "Loipe", Aehnlichkeit >= 0,75)
  und die Startpunkte unter 300 m auseinander liegen, oder
- der Name gleich ist und die Startpunkte unter 2 km auseinander liegen (Quellen setzen den Start
  verschieden: Parkplatz, Ortsmitte, Einstieg), oder
- einer Quelle die Koordinate fehlt, beide im selben Gebiet (oder derselben Region) liegen und der Name gleich ist.

Innerhalb einer Quelle (D18): tirol.at fuehrt manche Loipen zwei- bis fuenfmal mit demselben Namen und
demselben Startpunkt (alte Eintraege, die noch als geoeffnet gelten). Gleicher Name und Start unter 100 m
= derselbe Eintrag. Laengen ("12,5 km"), Nummern ("Nr. 2") und Technik zaehlen beim Namensvergleich nicht.
"""

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from loipen.adapters.normalisierung import slugify

AEHNLICH = 0.75
NAH_KM = 0.3
GLEICH_NAH_KM = 2.0
FUELLWOERTER = {"loipe", "loipen", "loipennetz", "langlaufloipe", "langlaufloipen", "langlauf", "nr", "die", "der",
                "km", "klassisch", "skating", "und", "u", "barrierefrei"}
SELBE_QUELLE_KM = 0.1
NUMMER = re.compile(r"(nr)?\d+[a-z]?")  # "nr1", "2", "8a"
# Loipennummern der Verbaende ("P4", "SC3a", "KU1"): im selben Gebiet eindeutig (P22)
KENNUNG = re.compile(r"[a-z]{1,2}\d{1,2}[a-z]?")


@dataclass
class Eintrag:
    id: int
    name: str
    quelle: str
    rang: int
    gebiet: str
    gebiet_name: str
    lat: float | None
    lon: float | None
    region: str = ""


def woerter(name: str, gebiet_name: str = "") -> list[str]:
    ort = set(slugify(gebiet_name).split("-")) if gebiet_name else set()
    return [t for t in slugify(name).split("-") if t and t not in FUELLWOERTER and t not in ort and not NUMMER.fullmatch(t)
            and not KENNUNG.fullmatch(t)]


def kennungen(name: str) -> set[str]:
    return {t for t in slugify(name).split("-") if KENNUNG.fullmatch(t) and not NUMMER.fullmatch(t)}


def schluessel(name: str, gebiet_name: str = "") -> str:
    return "".join(woerter(name, gebiet_name))


def _km(a: Eintrag, b: Eintrag) -> float | None:
    if None in (a.lat, a.lon, b.lat, b.lon):
        return None
    return math.hypot((a.lat - b.lat) * 111.2, (a.lon - b.lon) * 111.2 * math.cos(math.radians(a.lat)))


def gleich(a: Eintrag, b: Eintrag) -> bool:
    if a.quelle == b.quelle:
        abstand = _km(a, b)
        return (kurzname(a.name).lower() == kurzname(b.name).lower() and abstand is not None
                and abstand < SELBE_QUELLE_KM)
    ka, kb = schluessel(a.name, a.gebiet_name), schluessel(b.name, b.gebiet_name)
    if not ka or not kb:
        return False
    aehnlich = SequenceMatcher(None, ka, kb).ratio()
    abstand = _km(a, b)
    if abstand is None:
        # D18: Gebietsgrenzen setzen die Quellen verschieden (Seefeld/Leutasch), die Region ist dieselbe
        selbe = a.gebiet == b.gebiet or (a.region and a.region == b.region)
        if not selbe:
            return False
        ca, cb = kennungen(a.name), kennungen(b.name)
        if ca and cb:
            # P22: Verbandsnummern entscheiden ("P4 - Gerntal" = "P4 - Loipe Pletzach-Gern", BH1 ist nicht BH3)
            return ca == cb
        # gleiche Woerter in anderer Reihenfolge: "C9 - Plaik" = "Plaik Loipe (C9)"
        wa, wb = set(woerter(a.name, a.gebiet_name)), set(woerter(b.name, b.gebiet_name))
        klein, gross = sorted((wa, wb), key=len)
        # ein einzelnes gemeinsames Wort reicht nicht ("Waldloipe" ist nicht "Waldloipe Alpenbad")
        return ka == kb or (len(klein) >= 2 and klein <= gross)
    return (aehnlich >= AEHNLICH and abstand < NAH_KM) or (ka == kb and abstand < GLEICH_NAH_KM)


def finde_dubletten(eintraege: list[Eintrag]) -> dict[int, int]:
    """id des verdeckten Eintrags -> id des fuehrenden. Fuehrend ist der kleinste Rang, dann die kleinste id."""
    reihenfolge = sorted(eintraege, key=lambda e: (e.rang, e.id))
    fuehrend: dict[int, int] = {}
    behalten: list[Eintrag] = []
    for e in reihenfolge:
        treffer = next((b for b in behalten if gleich(b, e)), None)
        if treffer:
            fuehrend[e.id] = treffer.id
        else:
            behalten.append(e)
    return fuehrend


def kurzname(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()
