"""Abrufzeiten pro Quelle (P8): in der Saison standardmaessig 7, 12 und 17 Uhr,
ausserhalb hoechstens einmal am Tag. Alles kommt aus der Konfiguration."""

from datetime import date, datetime

STANDARD = {
    "saison": {"von": "11-01", "bis": "04-30"},
    "saison_uhrzeiten": [7, 12, 17],
    "nebensaison_uhrzeiten": [8],
}


def _monat_tag(text: str) -> tuple[int, int]:
    m, t = text.split("-")
    return int(m), int(t)


def ist_saison(tag: date, zeitplan: dict | None = None) -> bool:
    saison = {**STANDARD, **(zeitplan or {})}["saison"]
    von, bis = _monat_tag(saison["von"]), _monat_tag(saison["bis"])
    heute = (tag.month, tag.day)
    if von <= bis:
        return von <= heute <= bis
    return heute >= von or heute <= bis  # Saison ueber den Jahreswechsel


def uhrzeiten(tag: date, zeitplan: dict | None = None) -> list[int]:
    plan = {**STANDARD, **(zeitplan or {})}
    if ist_saison(tag, plan):
        return sorted(plan["saison_uhrzeiten"])
    # ausserhalb der Saison hoechstens ein Abruf pro Tag
    return sorted(plan["nebensaison_uhrzeiten"])[:1]


def ist_faellig(jetzt: datetime, zeitplan: dict | None = None) -> bool:
    """Wird stuendlich zur vollen Stunde aufgerufen."""
    return jetzt.hour in uhrzeiten(jetzt.date(), zeitplan)
