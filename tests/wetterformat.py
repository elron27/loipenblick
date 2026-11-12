"""Antworten im Format von DWD (Tageswerte-ZIP) und Bright Sky, fuer Tests und die Attrappe im Teststack.

Nur Standardbibliothek, damit die Attrappe (tests/stack/attrappe.py) ohne pytest laeuft.
Das Format ist nach der Dokumentation gebaut; ob es zu den echten Antworten passt, prueft der
Workflow "Live-Pruefung" (.github/workflows/live.yml) mit echten Abrufen.
"""

import io
import json
import zipfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

KOPF = "STATIONS_ID;MESS_DATUM;QN_6;  RS;RSF;SH_TAG;NSH_TAG;eor"


def dwd_zip(zeilen: list[tuple]) -> bytes:
    """(datum, rs, sh, nsh) -> ZIP wie vom DWD; None wird zu -999."""
    f = lambda v: "-999" if v is None else f"{v}"
    text = KOPF + "\n" + "\n".join(
        f"      205;{d:%Y%m%d};10;   {f(rs)}; 0;   {f(sh)};   {f(nsh)};eor" for d, rs, sh, nsh in zeilen
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Metadaten_Geographie_00205.txt", "egal")
        z.writestr("produkt_nieder_tag_20250101_20261209_00205.txt", text)
    return buf.getvalue()


def brightsky(tage: dict[date, list[tuple[float, float, str]]]) -> str:
    """Je Tag Liste (Temperatur, Niederschlag, Zustand) stuendlich."""
    eintraege = []
    for tag, stunden in tage.items():
        for h, (t, n, c) in enumerate(stunden):
            ts = datetime(tag.year, tag.month, tag.day, h, tzinfo=ZoneInfo("Europe/Berlin")).isoformat()
            eintraege.append({"timestamp": ts, "temperature": t, "precipitation": n, "condition": c, "icon": c})
    return json.dumps({"weather": eintraege, "sources": []})
