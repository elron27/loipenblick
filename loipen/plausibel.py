"""Plausibilitaetspruefung offener Meldungen (D19, E-23, 19.11.2026).

Am Saisonanfang meldet etwa tirol.at Loipen als geoeffnet, ohne Datum, obwohl im Tal kein Schnee liegt
(Ginzling, Holzgau, Vals am 19.11.2026), oder ein Schneebericht steht seit Oktober unveraendert auf offen
(Samnaun). Diese Pruefung vergleicht jede Offen-Meldung mit dem, was wir selbst wissen:

1. Schnee: Die Quelle belegt die Meldung nicht (kein eigener Stand aus den letzten 48 h, keine gespurten
   Kilometer, keine Schneehoehe), und die Station des Gebiets misst 0 cm ohne Neuschnee in 72 h.
   Sonderloipen (Snowfarming, Opening, Gletscher, Gruppen) liegen auf technischem oder hochalpinem Schnee
   und sind ausgenommen.
2. Stand: Die Meldung der Quelle ist aelter als 7 Tage.
3. Widerspruch: Ein oertlicher Bericht (Rang 1 oder 2) meldet dieselbe Loipe geschlossen.

Unplausibel heisst nach E-23: Die Seite zeigt die Loipe geschlossen, mit dem Wortlaut der Quelle und dem
Grund. In der Datenbank bleibt der Rohwert stehen, die Pruefung laeuft nur beim Erzeugen der Seite.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from loipen.models import Status, Zustand

BERLIN = ZoneInfo("Europe/Berlin")
BEFAHRBAR = (Status.OFFEN.value, Status.EINGESCHRAENKT.value)
FRISCH_STUNDEN = 48  # AK 1: so alt darf ein eigener Stand der Quelle sein, damit er die Meldung belegt
MESSUNG_MAX_TAGE = 3  # AK 1: aeltere Schneemessungen sagen nichts ueber heute
STAND_MAX_TAGE = 7  # AK 2
OERTLICH_BIS_RANG = 2  # AK 3: Rang 1 und 2 sind Berichte vor Ort (tourinfra, Verbaende)


def _schnee_grund(schnee: dict, heute: date, tmax_heute: float | None) -> str | None:
    messtag = schnee.get("messtag")
    if isinstance(messtag, str):
        messtag = date.fromisoformat(messtag)
    if messtag is None or (heute - messtag).days > MESSUNG_MAX_TAGE:
        return None
    if schnee.get("schneehoehe_cm") is None or schnee["schneehoehe_cm"] > 0:
        return None
    if (schnee.get("neuschnee_72h_cm") or 0) > 0:
        return None
    station = schnee.get("station_name") or schnee.get("station_id") or "des Gebiets"
    grund = f"Station {station} misst am {messtag:%d.%m.} 0 cm Schnee, kein Neuschnee in 72 Stunden"
    if tmax_heute is not None and tmax_heute > 0:
        grund += f", heute bis {round(tmax_heute):+d} °C"
    return grund


def gruende(z: Zustand | None, status: str, sonder: dict | None, schnee: dict | None, tmax_heute: float | None,
            widerspruch: list[str], jetzt: datetime) -> list[str]:
    """Warum eine Offen-Meldung unplausibel ist. Leer heisst: plausibel oder gar nicht offen."""
    if z is None or status not in BEFAHRBAR:
        return []
    ergebnis = []
    stand = z.quelle_aktualisiert_at
    if stand is not None and jetzt - stand > timedelta(days=STAND_MAX_TAGE):
        ergebnis.append(f"Die Meldung der Quelle ist vom {stand.astimezone(BERLIN):%d.%m.%Y}, älter als {STAND_MAX_TAGE} Tage")
    beleg = (
        (stand is not None and jetzt - stand <= timedelta(hours=FRISCH_STUNDEN))
        or any((km or 0) > 0 for km in (z.gespurt_gesamt_km, z.gespurt_klassisch_km, z.gespurt_skating_km))
        or (z.schneehoehe_cm or 0) > 0
    )
    if not beleg and not sonder and schnee:
        grund = _schnee_grund(schnee, jetzt.astimezone(BERLIN).date(), tmax_heute)
        if grund:
            ergebnis.append(grund)
    for name in widerspruch:
        ergebnis.append(f"Der Loipenbericht vor Ort ({name}) meldet sie geschlossen")
    return ergebnis


def anwenden(d: dict, gruende_liste: list[str]) -> bool:
    """E-23: unplausibel = geschlossen. Der Wortlaut der Quelle bleibt als status_laut_quelle sichtbar."""
    if not gruende_liste:
        return False
    d["status_laut_quelle"] = d["status"]
    d["status"] = Status.GESCHLOSSEN.value
    for feld in ("status_klassisch", "status_skating"):
        if d.get(feld) in BEFAHRBAR:
            d[feld] = Status.GESCHLOSSEN.value
    d["unplausibel"] = gruende_liste
    return True
