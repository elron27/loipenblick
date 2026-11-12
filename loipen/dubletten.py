"""Dubletten ueber mehrere Quellen (D15, P15).

Dieselbe Loipe steht oft bei mehreren Quellen: tirol.at fuehrt auch Bayrischzeller Loipen, die
Kitzbueheler Alpen dieselben Loipen wie tirol.at. Jede Loipe wird einmal gezeigt, und zwar von der
fuehrenden Quelle (kleinster rang in sources.yaml); die anderen Eintraege stehen dort als "auch bei".

Regel: zwei Eintraege verschiedener Quellen sind dieselbe Loipe, wenn
- der Name aehnlich ist (Vergleich ohne Ortsnamen und Fuellwoerter wie "Loipe", Aehnlichkeit >= 0,75)
  und die Startpunkte unter 300 m auseinander liegen, oder
- der Name gleich ist und die Startpunkte unter 2 km auseinander liegen (Quellen setzen den Start
  verschieden: Parkplatz, Ortsmitte, Einstieg), oder
- einer Quelle die Koordinate fehlt, beide im selben Gebiet liegen und der Name gleich ist.
"""

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from loipen.adapters.normalisierung import slugify

AEHNLICH = 0.75
NAH_KM = 0.3
GLEICH_NAH_KM = 2.0
FUELLWOERTER = {"loipe", "loipen", "loipennetz", "langlaufloipe", "langlaufloipen", "langlauf", "nr", "die", "der"}


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


def schluessel(name: str, gebiet_name: str = "") -> str:
    ort = set(slugify(gebiet_name).split("-")) if gebiet_name else set()
    teile = [t for t in slugify(name).split("-") if t and t not in FUELLWOERTER and t not in ort]
    return "".join(teile)


def _km(a: Eintrag, b: Eintrag) -> float | None:
    if None in (a.lat, a.lon, b.lat, b.lon):
        return None
    return math.hypot((a.lat - b.lat) * 111.2, (a.lon - b.lon) * 111.2 * math.cos(math.radians(a.lat)))


def gleich(a: Eintrag, b: Eintrag) -> bool:
    if a.quelle == b.quelle:
        return False
    ka, kb = schluessel(a.name, a.gebiet_name), schluessel(b.name, b.gebiet_name)
    if not ka or not kb:
        return False
    aehnlich = SequenceMatcher(None, ka, kb).ratio()
    abstand = _km(a, b)
    if abstand is None:
        return a.gebiet == b.gebiet and ka == kb
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
