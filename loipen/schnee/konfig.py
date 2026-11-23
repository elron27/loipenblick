"""Quellen der Schneekarte mit Lizenz und Bedingungen (S6, E-33), aus config/schnee.yaml.

Jede Quelle braucht: key, name, adapter, lizenz, namensnennung, einnahmen (ja, nein, unklar), archiv_ab
(Datum oder null), geprueft_am, erlaubnis (liegt_vor, ausstehend, nur_test; ohne Angabe ausstehend, B27).
Eine Quelle ohne Lizenzeintrag lehnt die Pruefung ab, der Sammel-Job ruft sie nicht ab (S6 AK 2).
Open-Meteo ist nie erlaubt (S6 AK 3).
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PFLICHT = ("key", "name", "adapter", "lizenz", "namensnennung", "einnahmen", "geprueft_am")
EINNAHMEN = {"ja", "nein", "unklar"}
ERLAUBNIS = {"liegt_vor", "ausstehend", "nur_test"}
VERBOTEN = ("open-meteo", "openmeteo")
STANDARD_UHRZEITEN = [7, 12, 18]


@dataclass
class SchneeQuelle:
    key: str
    name: str
    adapter: str
    lizenz: str
    namensnennung: str
    einnahmen: str
    geprueft_am: str
    archiv_ab: str | None = None
    erlaubnis: str = "ausstehend"
    lizenz_url: str | None = None
    laender: list[str] = field(default_factory=list)
    uhrzeiten: list[int] = field(default_factory=lambda: list(STANDARD_UHRZEITEN))
    enabled: bool = True
    optionen: dict = field(default_factory=dict)

    @property
    def nur_test(self) -> bool:
        """S6 AK 4: einnahmen unklar (oder nein) ist nur in der Testversion sichtbar, wie nur_test in B27."""
        return self.erlaubnis == "nur_test" or self.einnahmen != "ja"


class KonfigFehler(ValueError):
    pass


def pruefe(eintraege: list[dict]) -> tuple[list[SchneeQuelle], list[str]]:
    """Gueltige Quellen und Fehlermeldungen. Eine fehlerhafte Quelle faellt heraus, die anderen bleiben."""
    quellen, fehler, keys = [], [], set()
    for e in eintraege or []:
        key = e.get("key") or "?"
        fehlt = [p for p in PFLICHT if not e.get(p)]
        if fehlt:
            fehler.append(f"{key}: es fehlt {', '.join(fehlt)} (S6)")
            continue
        if e["einnahmen"] not in EINNAHMEN:
            fehler.append(f"{key}: einnahmen muss ja, nein oder unklar sein, nicht {e['einnahmen']!r}")
            continue
        erlaubnis = e.get("erlaubnis") or "ausstehend"
        if erlaubnis not in ERLAUBNIS:
            fehler.append(f"{key}: erlaubnis {erlaubnis!r} unbekannt")
            continue
        text = yaml.safe_dump(e).lower()
        if any(v in text for v in VERBOTEN):
            fehler.append(f"{key}: Open-Meteo ist für die Schneekarte nicht erlaubt (E-33)")
            continue
        if key in keys:
            fehler.append(f"{key}: doppelt")
            continue
        keys.add(key)
        bekannt = set(SchneeQuelle.__dataclass_fields__) - {"optionen", "erlaubnis"}
        werte = {k: (str(v) if k in ("geprueft_am", "archiv_ab") and v is not None else v)
                 for k, v in e.items() if k in bekannt}
        optionen = {k: v for k, v in e.items() if k not in bekannt and k != "erlaubnis"}
        quellen.append(SchneeQuelle(**werte, erlaubnis=erlaubnis, optionen=optionen))
    return quellen, fehler


def lade(config_dir: str | Path) -> tuple[list[SchneeQuelle], list[str]]:
    pfad = Path(config_dir) / "schnee.yaml"
    if not pfad.exists():
        return [], []
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    return pruefe(daten.get("quellen") or [])
