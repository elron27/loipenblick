"""Sonderloipen (13.11.2026): Loipen, die eine Quelle als offen meldet, die aber keine gewoehnliche
Loipe fuer jeden sind. Snowfarming- und Opening-Loipen sind kurze Fruehstart-Runden aus gelagertem oder
technischem Schnee, Gletscherloipen liegen hochalpin hinter einer Bergbahn, manche sind nur fuer Gruppen
mit Voranmeldung. Die Seite zeigt sie mit Hinweis und zaehlt sie nicht als "befahrbar" fuer alle.

Erkannt wird am Namen, weil keine Quelle ein eigenes Feld dafuer hat."""

import re

# Reihenfolge = Vorrang: "Gletscher ... fuer Gruppen" ist eine Gruppenloipe
REGELN: list[tuple[str, re.Pattern, str, str]] = [
    ("gruppen", re.compile(r"f(ü|ue)r\s+gruppen|voranmeldung|nur\s+mit\s+anmeldung", re.I),
     "Nur für Gruppen", "Nur für Gruppen mit Voranmeldung, nicht frei zugänglich."),
    ("snowfarming", re.compile(r"snow\s*-?\s*farming|snow\s*factory|schneedepot", re.I),
     "Snowfarming",
     "Frühstart-Loipe aus gelagertem oder technisch erzeugtem Schnee: meist kurz, oft mit Gebühr. "
     "Sie sagt nichts über die übrigen Loipen im Gebiet."),
    ("opening", re.compile(r"\bopening\b|fr(ü|ue)hstart", re.I),
     "Opening-Loipe",
     "Kurze Loipe zum Saisonstart, solange die übrigen Loipen noch nicht gespurt sind."),
    ("gletscher", re.compile(r"gletscher", re.I),
     "Gletscherloipe",
     "Hochalpine Loipe am Gletscher, meist nur mit Bergbahn-Ticket erreichbar und oft nur im Herbst "
     "und Frühjahr gespurt."),
]


def sonderloipe(name: str) -> dict | None:
    """{"art", "kurz", "text"} oder None fuer eine gewoehnliche Loipe."""
    for art, muster, kurz, text in REGELN:
        if muster.search(name or ""):
            return {"art": art, "kurz": kurz, "text": text}
    return None
