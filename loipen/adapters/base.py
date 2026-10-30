"""Schnittstelle, die jeder Adapter erfuellt. Adapter liefern nur Daten, speichern nichts."""

from collections.abc import Iterable
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
    technik: Technik = Technik.UNBEKANNT
    schwierigkeit: Schwierigkeit = Schwierigkeit.UNBEKANNT
    nachtloipe: bool | None = None
    laenge_km: float | None = None
    gespurt_klassisch_km: float | None = None
    gespurt_skating_km: float | None = None
    gespurt_gesamt_km: float | None = None
    schneehoehe_cm: int | None = None
    quelle_aktualisiert_at: datetime | None = None
    lat: float | None = None
    lon: float | None = None
    unbekannte_begriffe: list[str] = field(default_factory=list)


class Fetcher(Protocol):
    def get(self, url: str) -> str: ...


class Adapter(Protocol):
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> Iterable[LoipenDaten]: ...
