"""Erzeugt docs/schneekarte-quellen.md aus config/schnee.yaml (S6 AK 5): python -m loipen.schnee.doku"""

import sys
from pathlib import Path

from loipen.schnee.konfig import lade

KOPF = """# Schneekarte: Quellen und Lizenzen

Erzeugt aus `config/schnee.yaml` mit `python -m loipen.schnee.doku`. Nicht von Hand ändern.
Grundlage: Prüfung vom 23.11.2026, Schnappschüsse und Lizenzseiten in `tests/fixtures/schnee-2026-11-23/`
(ausführlich in `quellen.md` dort).

**Einnahmen erlaubt** heißt: Die Lizenz erlaubt die Nutzung auch dann, wenn die Seite Spenden oder Affiliate-Links
hat. Bei *nein* oder *unklar* wird gesammelt, die Daten erscheinen aber nur in der Testversion (S6 AK 4), bis der
Betreiber zugestimmt hat. Open-Meteo ist nicht dabei (E-33).

| Quelle | Länder | Lizenz | Namensnennung | Einnahmen erlaubt | Erlaubnis | Archiv ab | Abruf (Uhr) |
|---|---|---|---|---|---|---|---|
"""


def tabelle(config_dir: str | Path) -> str:
    quellen, fehler = lade(config_dir)
    if fehler:
        raise SystemExit("schnee.yaml fehlerhaft: " + "; ".join(fehler))
    zeilen = []
    for q in quellen:
        lizenz = f"[{q.lizenz}]({q.lizenz_url})" if q.lizenz_url else q.lizenz
        abruf = "nur von Hand (Archiv)" if not q.enabled else ", ".join(map(str, q.uhrzeiten))
        if q.optionen.get("wochentage"):
            abruf += " (montags)"
        zeilen.append(f"| {q.name} (`{q.key}`) | {', '.join(q.laender)} | {lizenz} | {q.namensnennung} | "
                      f"{q.einnahmen} | {q.erlaubnis} | {q.archiv_ab or '–'} | {abruf} |")
    return KOPF + "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    ziel = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/schneekarte-quellen.md")
    ziel.write_text(tabelle("config"), encoding="utf-8")
    print(f"{ziel} geschrieben")
