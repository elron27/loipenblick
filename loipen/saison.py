"""B32: Handangaben zu Saisonbeginn und Saisonende pruefen (ohne Netzzugriff testbar).

scripts/saisonpruefung.py ruft die Quell-URLs ab und schreibt den Bericht; der Workflow "Saisonpruefung"
oeffnet damit Anfang November und Ende Maerz ein GitHub-Issue (AK 1, AK 2). Die Anzeige "Stand Winter JJJJ/JJ"
(AK 3) steht in loipen/generator/static/app.js (standHand).
"""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Angabe:
    gebiet: str
    art: str              # Loipengebuehr, Parkplatz, Webcam, Verleih, Stammdaten
    text: str
    url: str | None
    geprueft_am: str | None
    eur: float | None = None
    befund: list[str] = field(default_factory=list)


def winter(tag: date) -> str:
    """Saison eines Tages: 24.11.2026 -> "2026/27", 10.03.2027 -> "2026/27"."""
    j = tag.year if tag.month >= 7 else tag.year - 1
    return f"{j}/{str(j + 1)[-2:]}"


def handangaben(gebiete: list[dict], stammdaten: dict | None = None) -> list[Angabe]:
    """Alle von Hand gepflegten Angaben aus config/gebiete.yaml (und config/stammdaten/hand*.yaml)."""
    liste = []
    for g in gebiete:
        name, geprueft = g.get("name") or g["slug"], g.get("geprueft_am")
        geb = g.get("loipengebuehr") or {}
        if geb.get("text") or geb.get("eur") is not None:
            liste.append(Angabe(name, "Loipengebühr", geb.get("text") or f"{geb['eur']} €", geb.get("url"),
                                str(geb.get("geprueft_am") or geprueft or "") or None, eur=geb.get("eur")))
        for p in g.get("parkplaetze") or []:
            liste.append(Angabe(name, "Parkplatz", p.get("name") or "Parkplatz", p.get("url"),
                                str(p.get("geprueft_am") or geprueft or "") or None, eur=p.get("gebuehr_eur_tag")))
        for w in g.get("webcams") or []:
            liste.append(Angabe(name, "Webcam", w.get("name") or "Webcam", w.get("url"),
                                str(w.get("geprueft_am") or geprueft or "") or None))
        for v in g.get("verleih") or []:
            liste.append(Angabe(name, "Verleih", v.get("name") or "Verleih", v.get("url"),
                                str(v.get("geprueft_am") or geprueft or "") or None))
    for quelle, loipen in ((stammdaten or {}).get("quellen") or {}).items():
        for sk, w in (loipen or {}).items():
            liste.append(Angabe(f"{quelle}/{sk}", "Stammdaten", ", ".join(sorted(k for k in w if k not in (
                "url", "geprueft_am"))), w.get("url"), str(w.get("geprueft_am") or "") or None))
    return liste


def betraege(text: str) -> set[float]:
    """Euro-Betraege in einem Seitentext: "7 €", "7,50 EUR", "€ 8.-" -> {7.0, 7.5, 8.0}."""
    werte = set()
    for m in re.finditer(r"(?:€|EUR)\s*(\d{1,3}(?:[.,]\d{1,2})?)|(\d{1,3}(?:[.,]\d{1,2})?)\s*(?:,-|\.-)?\s*(?:€|EUR|Euro)",
                         text, flags=re.I):
        werte.add(float((m.group(1) or m.group(2)).replace(",", ".")))
    return werte


def pruefe(a: Angabe, status: int | None, seite: str | None, heute: date) -> list[str]:
    """Befund einer Angabe (AK 2): nicht erreichbar, Gebuehr nicht mehr gefunden, Pruefdatum aelter als eine Saison."""
    befund = []
    if not a.url:
        befund.append("keine Quell-URL")
    elif status is None or status >= 400:
        befund.append(f"Seite nicht erreichbar ({status or 'keine Antwort'})")
    elif a.eur and seite is not None and a.eur not in betraege(seite):
        befund.append(f"Betrag {a.eur:g} € nicht mehr auf der Seite gefunden, Gebühr prüfen")
    if not a.geprueft_am:
        befund.append("ohne Prüfdatum")
    elif winter(date.fromisoformat(a.geprueft_am[:10])) != winter(heute):
        befund.append(f"Prüfdatum {a.geprueft_am} aus Winter {winter(date.fromisoformat(a.geprueft_am[:10]))}")
    return befund


def bericht(angaben: list[Angabe], heute: date) -> str:
    offen = [a for a in angaben if a.befund]
    z = [f"# Saisonprüfung der Handangaben, Winter {winter(heute)}", "",
         f"Stand {heute.isoformat()}: {len(angaben)} Handangaben, {len(offen)} mit Befund. Nach der Prüfung "
         "`geprueft_am` in `config/gebiete.yaml` auf das heutige Datum setzen, Gebühren und Links anpassen.", "",
         "| Gebiet | Art | Angabe | Prüfdatum | Befund | Quelle |", "| --- | --- | --- | --- | --- | --- |"]
    for a in sorted(angaben, key=lambda x: (not x.befund, x.gebiet, x.art)):
        z.append(f"| {a.gebiet} | {a.art} | {a.text[:80].replace('|', '/')} | {a.geprueft_am or '–'} | "
                 f"{'; '.join(a.befund) or 'ok'} | {a.url or '–'} |")
    return "\n".join(z) + "\n"


def lade(config_dir: Path) -> list[Angabe]:
    import yaml

    gebiete = (yaml.safe_load((Path(config_dir) / "gebiete.yaml").read_text(encoding="utf-8")) or {}).get("gebiete") or []
    stamm: dict = {"quellen": {}}
    for pfad in sorted((Path(config_dir) / "stammdaten").glob("*.yaml")):
        inhalt = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        if inhalt.get("herkunft") == "hand":
            for q, l in (inhalt.get("quellen") or {}).items():
                stamm["quellen"].setdefault(q, {}).update(l or {})
    return handangaben(gebiete, stamm)
