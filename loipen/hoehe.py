"""D23: Hoehenmeter, hoechster und tiefster Punkt einer Loipe aus dem Copernicus-Hoehenmodell GLO-30.

Die Rechnung ist hier, damit sie ohne Netz testbar ist; scripts/hoehe_dem.py liest die Hoehen (Kacheln aus dem
offenen AWS-Bucket copernicus-dem-30m) und schreibt config/stammdaten/hoehe.yaml.

- Entlang des Verlaufs alle hoechstens 50 m ein Punkt (AK 1).
- Glaettung: gleitendes Mittel ueber 5 Punkte (rund 200 m), damit Rauschen und Baumkronen nicht als Anstieg
  zaehlen. Hoehenmeter = Summe der Anstiege der geglaetteten Kurve.
- Freigabe (AK 2): an Loipen mit Hoehenmetern laut Quelle wird die Abweichung gemessen; liegt ihr Median ueber
  25 %, wird nichts uebernommen.

Quellenangabe (Lizenz): "© DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, bereitgestellt
im Rahmen von COPERNICUS durch die Europaeische Union und die ESA; alle Rechte vorbehalten" (GLO-30 Public).
"""

import math
from statistics import median

ABSTAND_M = 50.0
GLAETTUNG = 5
MAX_ABWEICHUNG = 0.25
QUELLENANGABE = ("Copernicus DEM GLO-30: © DLR e.V. 2010-2014 und © Airbus Defence and Space GmbH 2014-2018, "
                 "bereitgestellt im Rahmen von COPERNICUS durch die Europäische Union und die ESA")


def _m(a: tuple[float, float], b: tuple[float, float]) -> float:
    dlat = (a[0] - b[0]) * 111_200
    dlon = (a[1] - b[1]) * 111_200 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dlat, dlon)


def verdichte(linie: list[tuple[float, float]], abstand_m: float = ABSTAND_M) -> list[tuple[float, float]]:
    """Punkte entlang der Linie, hoechstens abstand_m auseinander (AK 1)."""
    if len(linie) < 2:
        return list(linie)
    punkte = [linie[0]]
    for a, b in zip(linie, linie[1:]):
        n = max(1, math.ceil(_m(a, b) / abstand_m))
        for i in range(1, n + 1):
            punkte.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return punkte


def glaette(werte: list[float], fenster: int = GLAETTUNG) -> list[float]:
    h = fenster // 2
    return [sum(werte[max(0, i - h):i + h + 1]) / len(werte[max(0, i - h):i + h + 1]) for i in range(len(werte))]


def kennzahlen(hoehen: list[float | None]) -> dict | None:
    """{hoehenmeter, hoechster_punkt_m, tiefster_punkt_m} aus den Hoehen entlang der Strecke."""
    werte = [h for h in hoehen if h is not None and h > -100]
    if len(werte) < 2:
        return None
    g = glaette(werte)
    anstieg = sum(max(0.0, b - a) for a, b in zip(g, g[1:]))
    return {"hoehenmeter": int(round(anstieg)), "hoechster_punkt_m": int(round(max(werte))),
            "tiefster_punkt_m": int(round(min(werte)))}


def freigabe(vergleich: list[tuple[int, int]]) -> tuple[bool, float | None]:
    """(freigegeben, Median der relativen Abweichung) aus Paaren (berechnet, laut Quelle)."""
    abw = [abs(b - q) / q for b, q in vergleich if q and q > 0]
    if not abw:
        return False, None
    m = median(abw)
    return m <= MAX_ABWEICHUNG, m


def kachel(lat: float, lon: float) -> str:
    """Name der GLO-30-Kachel im AWS-Bucket fuer einen Punkt."""
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    la, lo = abs(math.floor(lat)), abs(math.floor(lon))
    name = f"Copernicus_DSM_COG_10_{ns}{la:02d}_00_{ew}{lo:03d}_00_DEM"
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
