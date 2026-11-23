"""Was ein Schnee-Adapter liefert, unabhaengig von der Quelle."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class StationDaten:
    kennung: str
    name: str
    lat: float
    lon: float
    hoehe_m: int | None  # ohne Hoehe wird die Station nicht uebernommen (S2 AK 2)
    betreiber: str | None = None
    land: str | None = None
    warnregion: str | None = None
    messart: str = "automatisch"
    messgroessen: list[str] = field(default_factory=list)


@dataclass
class MesswertDaten:
    station: str  # kennung der Station bei der Quelle
    zeitpunkt: datetime  # mit Zeitzone
    groesse: str  # hs, hn24, ta, ta_min, ta_max, rr, ff
    wert: float
    einheit: str
    takt: str = "tag"  # tag oder stunde


@dataclass
class Stufe:
    stufe: str  # EAWS-Wort: low, moderate, considerable, high, very_high, no_snow, no_rating
    tageszeit: str = "ganztags"  # ganztags, vormittag, nachmittag
    hoehe_unten: int | str | None = None  # Meter oder "treeline" (Waldgrenze), wie im Bericht
    hoehe_oben: int | str | None = None
    expositionen: list[str] = field(default_factory=list)  # nur wenn der Bericht die Stufe darauf beschraenkt

    @property
    def zahl(self) -> int | None:
        return {"low": 1, "moderate": 2, "considerable": 3, "high": 4, "very_high": 5}.get(self.stufe)


@dataclass
class Problem:
    art: str  # EAWS: new_snow, wind_slab, persistent_weak_layers, wet_snow, gliding_snow, ...
    expositionen: list[str] = field(default_factory=list)
    hoehe_unten: int | str | None = None
    hoehe_oben: int | str | None = None
    tageszeit: str = "ganztags"


@dataclass
class BerichtDaten:
    bulletin_id: str
    ausgabe_at: datetime
    gueltig_von: datetime
    gueltig_bis: datetime
    regionen: list[str]
    stufen: list[Stufe]
    probleme: list[Problem] = field(default_factory=list)
    sprache: str | None = None
    link: str | None = None
    tendenz: str | None = None


@dataclass
class ModellwertDaten:
    warnregion: str
    hoehe_von: int
    datum: date
    groesse: str
    mittel: float
    minimum: float
    maximum: float
    zellen: int


@dataclass
class RegionDaten:
    id: str
    name: str | None
    land: str
    geometrie: dict | None = None


@dataclass
class Ergebnis:
    stationen: list[StationDaten] = field(default_factory=list)
    messwerte: list[MesswertDaten] = field(default_factory=list)
    berichte: list[BerichtDaten] = field(default_factory=list)
    modellwerte: list[ModellwertDaten] = field(default_factory=list)
    regionen: list[RegionDaten] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)

    def dazu(self, anderes: "Ergebnis") -> "Ergebnis":
        for name in ("stationen", "messwerte", "berichte", "modellwerte", "regionen", "warnungen"):
            getattr(self, name).extend(getattr(anderes, name))
        return self
