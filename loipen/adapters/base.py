"""Schnittstelle, die jeder Adapter erfuellt. Adapter liefern nur Daten, speichern nichts."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from loipen.models import Schwierigkeit, Status, Technik


@dataclass
class LoipenDaten:
    """Was ein Adapter pro Loipe findet. Unbekanntes bleibt None."""

    source_key: str
    name: str
    source_url: str
    gebiet_slug: str
    status: Status = Status.UNBEKANNT
    status_rohtext: str | None = None
    status_klassisch: Status | None = None
    status_skating: Status | None = None
    technik: Technik = Technik.UNBEKANNT
    schwierigkeit: Schwierigkeit = Schwierigkeit.UNBEKANNT
    nachtloipe: bool | None = None
    rundkurs: bool | None = None
    laenge_km: float | None = None
    gespurt_klassisch_km: float | None = None
    gespurt_skating_km: float | None = None
    gespurt_gesamt_km: float | None = None
    schneehoehe_cm: int | None = None
    # P41: Schneehoehe am Berg, Hinweis und Sperrgrund des Betreibers (je Abruf)
    schneehoehe_berg_cm: int | None = None
    hinweis: str | None = None
    sperrgrund: str | None = None
    # P41: Stammdaten laut Quelle
    hund_erlaubt: bool | None = None
    kunstschnee: bool | None = None
    loipengebiet: str | None = None
    einstiege: list[dict] | None = None
    # D21/P43: Stammdaten aus Detailseiten, z. B. {"hoechster_punkt_m": 803, "merkmale": [...]}
    stammdaten: dict = field(default_factory=dict)
    quelle_aktualisiert_at: datetime | None = None
    lat: float | None = None
    lon: float | None = None
    startpunkt: str | None = None
    rohtext: str | None = None
    # Streckenverlauf als Liste von (lat, lon), falls die Quelle ihn liefert
    verlauf: list[tuple[float, float]] | None = None
    # (Feld, Rohtext) fuer Woerter, die keine Zuordnungstabelle kennt (P5)
    unbekannte_begriffe: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class AdapterErgebnis:
    loipen: list[LoipenDaten] = field(default_factory=list)
    # Einzelne Seiten, die nicht gelesen werden konnten; der Lauf geht trotzdem weiter
    warnungen: list[str] = field(default_factory=list)
    # False, wenn Seiten wegen Netzfehlern fehlen: die Loipen sind dann nur ein Teil (B28). Fehlende Loipen
    # werden in diesem Fall nicht als verschwunden behandelt (B29).
    vollstaendig: bool = True


class Fetcher(Protocol):
    def get(self, url: str) -> str: ...

    def get_bytes(self, url: str) -> bytes: ...


class Adapter(Protocol):
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis: ...
