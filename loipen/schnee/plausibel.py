"""Ausreisser markieren statt glaetten (S7). Der Rohwert bleibt unveraendert; markiert wird mit dem Namen der Regel.
Neuschnee wird nie aus der Differenz der Schneehoehe berechnet (S7 AK 3): diese Datei rechnet keine Werte aus.

Regeln der ersten Stufe (S7 AK 2):
- negativ:       negative Schneehoehe
- sprung:        Anstieg um mehr als 50 cm in 24 h ohne gemessenen Niederschlag
- warm:          Schneehoehe > 0 bei Tageshoechsttemperatur > 15 Grad an drei Tagen hintereinander (Sensor misst Gras)
- eingefroren:   automatischer Wert zehn Tage unveraendert (nur bei Schneehoehe > 0)
"""

from dataclasses import dataclass
from datetime import date, timedelta

SPRUNG_CM = 50.0
WARM_C = 15.0
WARM_TAGE = 3
EINGEFROREN_TAGE = 10


@dataclass
class Tag:
    datum: date
    hs: float | None = None
    rr: float | None = None
    ta_max: float | None = None


def pruefe(reihe: list[Tag], automatisch: bool = True) -> dict[date, str]:
    """Gibt fuer jeden verdaechtigen Tag die erste Regel zurueck, die anschlaegt. reihe: ein Eintrag je Tag."""
    tage = {t.datum: t for t in reihe}
    befund: dict[date, str] = {}
    for t in sorted(reihe, key=lambda t: t.datum):
        if t.hs is None:
            continue
        if t.hs < 0:
            befund[t.datum] = "negativ"
            continue
        gestern = tage.get(t.datum - timedelta(days=1))
        if (gestern and gestern.hs is not None and gestern.datum not in befund and t.hs - gestern.hs > SPRUNG_CM
                and not ((t.rr or 0) > 0 or (gestern.rr or 0) > 0)):
            befund[t.datum] = "sprung"
            continue
        warm = [tage.get(t.datum - timedelta(days=i)) for i in range(WARM_TAGE)]
        if t.hs > 0 and all(w and w.ta_max is not None and w.ta_max > WARM_C and (w.hs or 0) > 0 for w in warm):
            befund[t.datum] = "warm"
            continue
        if automatisch and t.hs > 0:
            davor = [tage.get(t.datum - timedelta(days=i)) for i in range(EINGEFROREN_TAGE)]
            if all(d and d.hs == t.hs for d in davor):
                befund[t.datum] = "eingefroren"
    return befund
