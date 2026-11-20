"""Bestandsaufnahme (D20): Welche Loipen haben Streckenverlauf, Lage, Laenge und Parkinfos?

Liest die erzeugte Seite (daten.json, daten/*.json, strecken/*.json), also genau das, was Besucher sehen,
und zaehlt je Quelle und je Gebiet. Laeuft ueber scripts/bestandsaufnahme.py, im Bericht der Live-Pruefung
und auf dem NAS gegen den echten Datenstand.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

OSM = "OpenStreetMap"


@dataclass
class Zaehler:
    loipen: int = 0
    strecke: int = 0           # irgendein Streckenverlauf
    strecke_eigen: int = 0     # von der Quelle selbst
    strecke_dublette: int = 0  # von einer anderen Quelle derselben Loipe (D15)
    strecke_osm: int = 0       # aus OpenStreetMap zugeordnet (P36)
    lage: int = 0
    laenge: int = 0
    parken: int = 0            # mindestens ein Parkplatz an der Loipe
    parken_hand: int = 0       # von Hand recherchiert (config/gebiete.yaml)
    parken_osm: int = 0

    def zaehle(self, l: dict, punkte: list | None) -> None:
        self.loipen += 1
        if punkte:
            self.strecke += 1
            von = l.get("strecke_von")
            if von == OSM:
                self.strecke_osm += 1
            elif von:
                self.strecke_dublette += 1
            else:
                self.strecke_eigen += 1
        self.lage += l.get("lat") is not None
        self.laenge += l.get("laenge_km") is not None
        parken = l.get("parken") or []
        self.parken += bool(parken)
        self.parken_hand += any(p.get("quelle") != OSM for p in parken)
        self.parken_osm += any(p.get("quelle") == OSM for p in parken)


@dataclass
class Gebietszeile:
    region: str
    gebiet: str
    land: str
    quellen: set[str] = field(default_factory=set)
    z: Zaehler = field(default_factory=Zaehler)
    parkplaetze_hand: int = 0
    gebuehr: bool = False
    haltestellen: int = 0


@dataclass
class Bestand:
    erzeugt: str
    gesamt: Zaehler
    quellen: dict[str, Zaehler]
    gebiete: list[Gebietszeile]


def lies_seite(site: Path) -> Bestand:
    site = Path(site)
    index = json.loads((site / "daten.json").read_text(encoding="utf-8"))
    gesamt, quellen, gebiete = Zaehler(), {}, []
    for r in index["regionen"]:
        daten = json.loads((site / r["datei"]).read_text(encoding="utf-8"))
        strecken_datei = site / r["strecken"]
        strecken = json.loads(strecken_datei.read_text(encoding="utf-8")) if strecken_datei.exists() else {}
        for g in daten["gebiete"]:
            if not g["loipen"]:
                continue
            zeile = Gebietszeile(r["name"], g["name"], g.get("land") or "",
                                 parkplaetze_hand=sum(1 for p in g["parkplaetze"] if not p.get("geschaetzt")),
                                 gebuehr=bool((g.get("loipengebuehr") or {}).get("text")
                                              or (g.get("loipengebuehr") or {}).get("eur") is not None),
                                 haltestellen=len(g.get("haltestellen") or []))
            for l in g["loipen"]:
                punkte = strecken.get(str(l["id"]))
                for z in (gesamt, quellen.setdefault(l["quelle"]["name"], Zaehler()), zeile.z):
                    z.zaehle(l, punkte)
                zeile.quellen.add(l["quelle"]["name"])
            gebiete.append(zeile)
    return Bestand(index.get("erzeugt", ""), gesamt, quellen, gebiete)


def _anteil(teil: int, ganz: int) -> str:
    return f"{teil} ({round(100 * teil / ganz)} %)" if ganz else "0"


def als_markdown(b: Bestand, titel: str = "Bestandsaufnahme Strecken und Parkinfos", hinweis: str = "") -> str:
    g = b.gesamt
    z = [f"# {titel}", "", f"Datenstand der Seite: {b.erzeugt}." + (f" {hinweis}" if hinweis else ""), "",
         "Gezählt wird, was die Seite zeigt: verdeckte Dubletten zählen nicht, ihre Daten zählen bei der führenden Loipe.",
         "", "## Gesamt", "",
         "| | Loipen | Anteil |", "| --- | ---: | ---: |",
         f"| Loipen | {g.loipen} | |",
         f"| mit Streckenverlauf | {g.strecke} | {_anteil(g.strecke, g.loipen)} |",
         f"| davon von der Quelle selbst | {g.strecke_eigen} | |",
         f"| davon von einer anderen Quelle derselben Loipe | {g.strecke_dublette} | |",
         f"| davon aus OpenStreetMap | {g.strecke_osm} | |",
         f"| mit Lage (Startpunkt) | {g.lage} | {_anteil(g.lage, g.loipen)} |",
         f"| mit Länge | {g.laenge} | {_anteil(g.laenge, g.loipen)} |",
         f"| mit Parkplatz | {g.parken} | {_anteil(g.parken, g.loipen)} |",
         f"| davon von Hand recherchiert | {g.parken_hand} | |",
         f"| davon aus OpenStreetMap | {g.parken_osm} | |",
         "", "## Je Quelle", "",
         "| Quelle | Loipen | Strecke | davon OSM | Lage | Länge | Parkplatz | davon OSM |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, q in sorted(b.quellen.items(), key=lambda x: (-x[1].loipen, x[0])):
        z.append(f"| {name} | {q.loipen} | {_anteil(q.strecke, q.loipen)} | {q.strecke_osm} | "
                 f"{_anteil(q.lage, q.loipen)} | {_anteil(q.laenge, q.loipen)} | {_anteil(q.parken, q.loipen)} | {q.parken_osm} |")
    z += ["", "## Gebiete mit Lücken", "",
          "Gebiete, in denen mindestens einer Loipe Strecke oder Parkplatz fehlt. „Hand“ = Parkplätze aus "
          "`config/gebiete.yaml` mit bestätigter Lage.", "",
          "| Region | Gebiet | Loipen | ohne Strecke | ohne Parkplatz | Parkplätze Hand | Gebühr | Haltestellen |",
          "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |"]
    for r in sorted(b.gebiete, key=lambda x: (x.land != "DE", x.region, x.gebiet)):
        ohne_s, ohne_p = r.z.loipen - r.z.strecke, r.z.loipen - r.z.parken
        if ohne_s or ohne_p:
            z.append(f"| {r.region} | {r.gebiet} | {r.z.loipen} | {ohne_s} | {ohne_p} | {r.parkplaetze_hand} | "
                     f"{'ja' if r.gebuehr else 'unbekannt'} | {r.haltestellen} |")
    return "\n".join(z) + "\n"
