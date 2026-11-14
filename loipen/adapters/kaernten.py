"""Adapter O: Wintersportbericht Nassfeld-Pressegger See (tools.nlw.at), PDF (P28, E-21).

Kaernten hat kein Landesportal mit Status je Loipe (kaernten.at zeigt bergfex-Daten, siehe
docs/recherche-suedtirol-kaernten-schweiz.md). Die Nassfeld-Pressegger See GmbH (NLW) veroeffentlicht taeglich
einen Wintersportbericht als PDF. Befund (tests/fixtures/nassfeld-nlw/2026-11-13/wintersportbericht-nps.pdf):
- Abschnitt "Loipen" mit einer Zeile je Ort: "Hermagor 0 / 9", "Weissensee 0 / 9" = offene / alle Loipen.
- Keine Namen einzelner Loipen und kein Datum im Text; das PDF wird morgens erzeugt (CreationDate
  "D:20261113080009+00'00'" beim Abruf um 23:05 UTC), das gilt als Stand.
Je Ort entsteht deshalb eine Zeile "Loipennetz <Ort>" mit dem Zaehler, wie bei Schweiz Tourismus (P29 AK 3):
alle offen = offen, keine offen = geschlossen, dazwischen = eingeschraenkt.
"""

import io
import json
import re
from datetime import datetime

from loipen.adapters.base import AdapterErgebnis, Fetcher, LoipenDaten
from loipen.adapters.normalisierung import BERLIN
from loipen.models import Status


def pdf_lesen(inhalt: bytes) -> tuple[str, datetime | None]:
    """Text aller Seiten und Erzeugungszeit des PDFs (Ortszeit)."""
    from pypdf import PdfReader

    pdf = PdfReader(io.BytesIO(inhalt))
    text = "\n".join(seite.extract_text() or "" for seite in pdf.pages)
    try:
        erzeugt = pdf.metadata.creation_date if pdf.metadata else None
    except ValueError:  # unlesbares Datum im PDF
        erzeugt = None
    if erzeugt is not None and erzeugt.tzinfo is not None:
        erzeugt = erzeugt.astimezone(BERLIN)
    elif erzeugt is not None:
        erzeugt = None  # ohne Zeitzone nicht eindeutig
    return text, erzeugt


def pdf_text(inhalt: bytes) -> str:
    return pdf_lesen(inhalt)[0]


def lese_zaehler(text: str, orte: list[str]) -> dict[str, tuple[int, int]]:
    """{'Hermagor': (offen, alle)} fuer die Orte im Abschnitt Loipen."""
    teil = text[text.find("Loipen"):] if "Loipen" in text else text
    werte = {}
    for ort in orte:
        m = re.search(rf"{re.escape(ort)}\s+(\d+)\s*/\s*(\d+)", teil)
        if m:
            werte[ort] = (int(m.group(1)), int(m.group(2)))
    return werte


def heute(text: str) -> datetime | None:
    m = re.search(r"Heute\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=BERLIN) if m else None


class NlwBerichtAdapter:
    def run(self, base_url: str, config: dict, fetcher: Fetcher) -> AdapterErgebnis:
        url = base_url.rstrip("/") + config["pfad"]
        text, erzeugt = pdf_lesen(fetcher.get_bytes(url))
        return self.run_text(text, url, config, erzeugt)

    def run_text(self, text: str, url: str, config: dict, erzeugt: datetime | None = None) -> AdapterErgebnis:
        ergebnis = AdapterErgebnis()
        orte: dict[str, str] = {o["name"]: o["gebiet"] for o in config["orte"]}
        zaehler = lese_zaehler(text, list(orte))
        if not zaehler:
            ergebnis.warnungen.append("NLW-Wintersportbericht: keine Loipenzaehler gefunden, Aufbau geaendert?")
            return ergebnis
        for ort in orte:
            if ort not in zaehler:
                ergebnis.warnungen.append(f"NLW-Wintersportbericht: kein Zaehler fuer {ort}")
        tag = erzeugt or heute(text)
        for ort, (offen, alle) in zaehler.items():
            d = LoipenDaten(source_key=f"nlw_{orte[ort]}", name=f"Loipennetz {ort}", source_url=url,
                            gebiet_slug=orte[ort])
            if alle == 0:
                d.status = Status.UNBEKANNT
            elif offen == 0:
                d.status = Status.GESCHLOSSEN
            elif offen >= alle:
                d.status = Status.OFFEN
            else:
                d.status = Status.EINGESCHRAENKT
            d.status_rohtext = f"Wintersportbericht NLW: {offen} von {alle} Loipen offen"
            # Stand: Erzeugungszeit des PDFs, sonst der Tag "Heute" aus dem Text
            d.quelle_aktualisiert_at = tag
            d.rohtext = json.dumps({"ort": ort, "offen": offen, "alle": alle}, ensure_ascii=False)
            ergebnis.loipen.append(d)
        return ergebnis
