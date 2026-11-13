"""Saisonstatistik aus der Historie (N-17, N-38; U19, U37, U38, U39).

Grundlage ist die Tabelle zustaende (D4): jede Zeile gilt vom ersten Abruf (abgerufen_at) bis zur
letzten Bestaetigung (zuletzt_bestaetigt_at). Daraus entsteht pro Loipe ein Tagesstatus:

- Ein Tag ist *beobachtet*, wenn an ihm ein bekannter Status (offen, eingeschraenkt, geschlossen)
  vorlag. Tage ohne Abruf oder nur mit "unbekannt" zaehlen nicht, sie sind Luecken.
- Ein Tag ist *befahrbar*, wenn die Quelle an ihm irgendwann "offen" oder "eingeschraenkt" meldete.
  Gab es an einem Tag mehrere Zustaende, gilt der beste (offen vor eingeschraenkt vor geschlossen).
- Ein Winter laeuft vom 1. November bis 30. April (U19 AK 2) und heisst z. B. "2026/27".

Die Seite rechnet nichts selbst nach: der Generator schreibt eine JSON-Datei mit fertigen Zahlen
und Tagesreihen (B7). Fuer die Beispielansicht (ohne echten Winter) gibt es eine zweite Datei mit
erfundenen, deutlich gekennzeichneten Werten.
"""

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from loipen.adapters.stammdaten import KEIN_ZUSTAND
from loipen.models import Gebiet, Loipe, Quelle, Status, Wetter, WetterArt, Zustand

BERLIN = ZoneInfo("Europe/Berlin")
BEFAHRBAR = (Status.OFFEN.value, Status.EINGESCHRAENKT.value)
BEKANNT = (Status.OFFEN.value, Status.EINGESCHRAENKT.value, Status.GESCHLOSSEN.value)
_RANG = {Status.OFFEN.value: 0, Status.EINGESCHRAENKT.value: 1, Status.GESCHLOSSEN.value: 2, Status.UNBEKANNT.value: 3}
WINTER_START = (11, 1)
WINTER_ENDE = (4, 30)


# ---------- Winter ----------

def winter_jahr(tag: date) -> int | None:
    """Startjahr des Winters, zu dem der Tag gehoert, sonst None (Mai bis Oktober)."""
    if tag.month >= WINTER_START[0]:
        return tag.year
    if (tag.month, tag.day) <= WINTER_ENDE:
        return tag.year - 1
    return None


def winter_name(jahr: int) -> str:
    return f"{jahr}/{(jahr + 1) % 100:02d}"


def winter_grenzen(jahr: int) -> tuple[date, date]:
    return date(jahr, *WINTER_START), date(jahr + 1, *WINTER_ENDE)


# ---------- Tagesstatus aus der Historie ----------

def _lokal(dt: datetime) -> date:
    return dt.astimezone(BERLIN).date()


def _besser(a: str | None, b: str) -> str:
    return b if a is None or _RANG.get(b, 9) < _RANG.get(a, 9) else a


def tagesstatus(zustaende: list[Zustand]) -> dict[date, str]:
    """Pro Kalendertag (Berliner Zeit) der beste beobachtete Status. Zustaende ohne Loipenzustand
    (nur Stammdaten, P16) zaehlen nicht."""
    tage: dict[date, str] = {}
    for z in zustaende:
        if z.rohtext == KEIN_ZUSTAND:
            continue
        tag, ende = _lokal(z.abgerufen_at), _lokal(z.zuletzt_bestaetigt_at or z.abgerufen_at)
        while tag <= ende:
            tage[tag] = _besser(tage.get(tag), z.status)
            tag += timedelta(days=1)
    return tage


# ---------- Auswertung ----------

@dataclass
class LoipeInfo:
    id: int
    quelle: str
    gebiet: str | None  # None: verdeckte Dublette, zaehlt nur fuer den Quellenvergleich
    unbestaetigt: bool = False  # P22 AK 3: nur eine nachrangige Quelle nennt sie


@dataclass
class Struktur:
    """Was die Seite zeigt: Regionen mit Gebieten, Loipen und Quellen, dazu die Dubletten."""

    regionen: dict[str, list[str]] = field(default_factory=dict)  # region -> gebiete
    gebiete: dict[str, dict] = field(default_factory=dict)  # slug -> {name, region}
    loipen: dict[int, LoipeInfo] = field(default_factory=dict)
    paare: list[tuple[int, int]] = field(default_factory=list)  # (fuehrend, verdeckt), verschiedene Quellen


def _erster_letzter(tage: list[date]) -> tuple[str | None, str | None]:
    return (min(tage).isoformat(), max(tage).isoformat()) if tage else (None, None)


def _winter_auswerten(jahr: int, bis: date, status: dict[int, dict[date, str]], schnee: dict[str, dict[date, float]],
                      st: Struktur) -> dict:
    start, ende = winter_grenzen(jahr)
    ende = min(ende, bis)
    tage = [start + timedelta(days=i) for i in range((ende - start).days + 1)]

    loipen_out: dict[str, dict] = {}
    for lid, info in st.loipen.items():
        if info.gebiet is None:
            continue
        s = status.get(lid, {})
        beob = [t for t in tage if s.get(t) in BEKANNT]
        if not beob:
            continue
        befahrbar = [t for t in beob if s[t] in BEFAHRBAR]
        erster, letzter = _erster_letzter(befahrbar)
        loipen_out[str(lid)] = {"tage": len(befahrbar), "offen": sum(1 for t in beob if s[t] == Status.OFFEN.value),
                                "beobachtet": len(beob), "erster": erster, "letzter": letzter,
                                "unbestaetigt": info.unbestaetigt}

    nach_gebiet: dict[str, list[int]] = defaultdict(list)
    for lid, info in st.loipen.items():
        if info.gebiet is not None and not info.unbestaetigt:
            nach_gebiet[info.gebiet].append(lid)

    gebiete_out: dict[str, dict] = {}
    reihen: dict[str, list[int | None]] = {}
    for slug, g in st.gebiete.items():
        ids = nach_gebiet.get(slug, [])
        reihe: list[int | None] = []
        for t in tage:
            werte = [status.get(i, {}).get(t) for i in ids]
            bekannt = [w for w in werte if w in BEKANNT]
            reihe.append(sum(1 for w in bekannt if w in BEFAHRBAR) if bekannt else None)
        sn = schnee.get(slug, {})
        schnee_reihe = [sn.get(t) for t in tage]
        if all(v is None for v in reihe) and all(v is None for v in schnee_reihe):
            continue
        befahrbar = [t for t, v in zip(tage, reihe) if v]
        erster, letzter = _erster_letzter(befahrbar)
        reihen[slug] = reihe
        gebiete_out[slug] = {"name": g["name"], "region": g["region"], "loipen": len(ids), "tage": len(befahrbar),
                             "beobachtet": sum(1 for v in reihe if v is not None), "erster": erster, "letzter": letzter,
                             "max": max((v for v in reihe if v is not None), default=None),
                             "befahrbar": reihe,
                             "schnee": [None if v is None else round(v) for v in schnee_reihe]}

    def summe(slugs: list[str]) -> list[int | None]:
        out: list[int | None] = []
        for i in range(len(tage)):
            werte = [reihen[s][i] for s in slugs if s in reihen and reihen[s][i] is not None]
            out.append(sum(werte) if werte else None)
        return out

    regionen_out = {}
    for region, slugs in st.regionen.items():
        r = summe(slugs)
        if all(v is None for v in r):
            continue
        regionen_out[region] = {"befahrbar": r, "tage": sum(1 for v in r if v),
                                "loipen": sum(len(nach_gebiet.get(s, [])) for s in slugs)}
    gesamt = summe(list(reihen))

    return {"name": winter_name(jahr), "start": start.isoformat(), "ende": winter_grenzen(jahr)[1].isoformat(),
            "bis": ende.isoformat(), "tage": len(tage),
            "gesamt": {"befahrbar": gesamt, "tage": sum(1 for v in gesamt if v),
                       "beobachtet": sum(1 for v in gesamt if v is not None),
                       "loipen": sum(len(v) for v in nach_gebiet.values())},
            "regionen": regionen_out, "gebiete": gebiete_out, "loipen": loipen_out,
            "quellen": _quellen(tage, status, st)}


def _quellen(tage: list[date], status: dict[int, dict[date, str]], st: Struktur) -> list[dict]:
    """U39: an wie vielen Tagen eine Quelle Daten lieferte und wie oft sie mit anderen Quellen
    uebereinstimmt, die dieselbe Loipe fuehren (Dubletten, D15)."""
    nach_quelle: dict[str, list[int]] = defaultdict(list)
    for lid, info in st.loipen.items():
        nach_quelle[info.quelle].append(lid)
    tagset = set(tage)
    out = {}
    for name, ids in nach_quelle.items():
        mit_daten = set()
        for i in ids:
            mit_daten |= {t for t, s in status.get(i, {}).items() if t in tagset}
        if not mit_daten:
            continue
        erster = min(mit_daten)
        moeglich = (tage[-1] - erster).days + 1
        out[name] = {"name": name, "tage_mit_daten": len(mit_daten), "tage_moeglich": moeglich,
                     "erster": erster.isoformat(), "vergleich": {"tage": 0, "gleich": 0}, "paare": {}}
    for fuehrend, verdeckt in st.paare:
        a, b = st.loipen.get(fuehrend), st.loipen.get(verdeckt)
        if a is None or b is None or a.quelle == b.quelle:
            continue
        sa, sb = status.get(fuehrend, {}), status.get(verdeckt, {})
        n = gleich = 0
        for t in tage:
            x, y = sa.get(t), sb.get(t)
            if x in BEKANNT and y in BEKANNT:
                n += 1
                gleich += (x in BEFAHRBAR) == (y in BEFAHRBAR)
        if not n:
            continue
        for eigen, fremd in ((a.quelle, b.quelle), (b.quelle, a.quelle)):
            if eigen not in out:
                continue
            q = out[eigen]
            q["vergleich"]["tage"] += n
            q["vergleich"]["gleich"] += gleich
            p = q["paare"].setdefault(fremd, {"mit": fremd, "tage": 0, "gleich": 0, "loipen": 0})
            p["tage"] += n
            p["gleich"] += gleich
            p["loipen"] += 1
    for q in out.values():
        q["paare"] = sorted(q["paare"].values(), key=lambda p: (-p["tage"], p["mit"]))
    return sorted(out.values(), key=lambda q: q["name"].lower())


def auswerten(status: dict[int, dict[date, str]], schnee: dict[str, dict[date, float]], st: Struktur,
              heute: date, beispiel: bool = False, erzeugt: str | None = None) -> dict:
    """Alle Winter, in denen es Beobachtungen oder Schneewerte gibt, plus der laufende Winter."""
    jahre = {winter_jahr(t) for s in status.values() for t in s} | {winter_jahr(t) for s in schnee.values() for t in s}
    if winter_jahr(heute) is not None:
        jahre.add(winter_jahr(heute))
    jahre.discard(None)
    winter = [_winter_auswerten(j, heute, status, schnee, st) for j in sorted(jahre, reverse=True)
              if winter_grenzen(j)[0] <= heute]
    return {"version": 1, "erzeugt": erzeugt, "beispiel": beispiel,
            "regel": "Befahrbar heißt: die Quelle meldete an diesem Tag offen oder eingeschränkt. Ein Winter dauert vom 1. November bis 30. April.",
            "winter": winter}


# ---------- Aus der Datenbank ----------

def struktur_aus(session: Session, daten: dict) -> Struktur:
    """Baut die Struktur aus den Daten der Seite (generator.daten.baue), damit die Statistik genau die
    Loipen zaehlt, die die Seite zeigt."""
    st = Struktur()
    quelle_von: dict[int, str] = {}
    for slug, r in daten["regionen"].items():
        st.regionen[slug] = []
        for g in r["gebiete"]:
            st.regionen[slug].append(g["slug"])
            st.gebiete[g["slug"]] = {"name": g["name"], "region": slug}
            for l in g["loipen"]:
                if l.get("ohne_zustand"):
                    continue
                st.loipen[l["id"]] = LoipeInfo(l["id"], l["quelle"]["name"], g["slug"], bool(l.get("nicht_im_bericht")))
                quelle_von[l["id"]] = l["quelle"]["name"]
    verdeckt: dict[int, int] = daten.get("verdeckt", {})
    if verdeckt:
        namen = dict(session.execute(select(Loipe.id, Quelle.name).join(Quelle).where(Loipe.id.in_(list(verdeckt)))).all())
        for v, f in sorted(verdeckt.items()):
            if f in st.loipen and v in namen and namen[v] != st.loipen[f].quelle:
                st.loipen.setdefault(v, LoipeInfo(v, namen[v], None))
                st.paare.append((f, v))
    return st


def schnee_aus(session: Session) -> dict[str, dict[date, float]]:
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for slug, tag, wert in session.execute(
            select(Gebiet.slug, Wetter.datum, Wetter.schneehoehe_cm).join(Gebiet, Gebiet.id == Wetter.gebiet_id)
            .where(Wetter.art == WetterArt.MESSUNG.value, Wetter.schneehoehe_cm.is_not(None))):
        if winter_jahr(tag) is not None:
            out[slug][tag] = wert
    return dict(out)


def baue_statistik(session: Session, daten: dict, jetzt: datetime) -> dict:
    st = struktur_aus(session, daten)
    zustaende: dict[int, list[Zustand]] = defaultdict(list)
    for z in session.scalars(select(Zustand).where(Zustand.loipe_id.in_(list(st.loipen)))
                             .order_by(Zustand.abgerufen_at, Zustand.id)):
        zustaende[z.loipe_id].append(z)
    status = {lid: tagesstatus(zs) for lid, zs in zustaende.items()}
    heute = jetzt.astimezone(BERLIN).date()
    return auswerten(status, schnee_aus(session), st, heute,
                     erzeugt=jetzt.astimezone(BERLIN).isoformat(timespec="minutes"))


# ---------- Beispielwerte ----------

def _zufall(*teile) -> float:
    """Gleiche Eingabe, gleiche Zahl in [0, 1): die Beispielansicht sieht bei jedem Lauf gleich aus."""
    h = hashlib.sha256("|".join(map(str, teile)).encode()).digest()
    return int.from_bytes(h[:6], "big") / 2 ** 48


def beispiel_statistik(session: Session, daten: dict, jetzt: datetime) -> dict:
    """Erfundener letzter Winter fuer die Beispielansicht: Schneehoehe je Gebiet als glatte Kurve
    (mehr Schnee in der Hoehe), Loipen offen ab einer Schwelle, verdeckte Dubletten weichen selten ab."""
    st = struktur_aus(session, daten)
    heute = jetzt.astimezone(BERLIN).date()
    jahr = (winter_jahr(heute) or heute.year) - 1
    start, ende = winter_grenzen(jahr)
    tage = [start + timedelta(days=i) for i in range((ende - start).days + 1)]
    hoehe = {g["slug"]: g.get("hoehe_m") for r in daten["regionen"].values() for g in r["gebiete"]}

    schnee: dict[str, dict[date, float]] = {}
    for slug in st.gebiete:
        h = hoehe.get(slug) or 900
        spitze = 25 + (h - 600) / 12 + 25 * _zufall(slug, "spitze")
        versatz = 10 * _zufall(slug, "versatz")
        werte = {}
        for i, t in enumerate(tage):
            x = (i - 18 - versatz) / 120  # Winterbeginn Mitte/Ende November, Hoehepunkt im Februar
            basis = spitze * math.sin(math.pi * x) if 0 < x < 1 else 0
            welle = 9 * math.sin(i / 6.5 + 6 * _zufall(slug, "welle")) + 5 * math.sin(i / 2.3)
            werte[t] = max(0.0, round(basis + welle * (basis > 5)))
        schnee[slug] = werte

    status: dict[int, dict[date, str]] = {}
    for lid, info in st.loipen.items():
        if info.gebiet is None:
            continue
        schwelle = 18 + 14 * _zufall(lid, "schwelle")
        s = {}
        for t in tage:
            if _zufall(lid, t, "luecke") < 0.02:
                continue  # Tag ohne Abruf, wie bei einem Ausfall
            cm = schnee[info.gebiet][t]
            s[t] = (Status.OFFEN.value if cm >= schwelle + 6 else
                    Status.EINGESCHRAENKT.value if cm >= schwelle else Status.GESCHLOSSEN.value)
        status[lid] = s
    for fuehrend, verdeckt in st.paare:
        quote = 0.04 + 0.12 * _zufall(st.loipen[verdeckt].quelle, "abweichung")
        s = {}
        for t, x in status.get(fuehrend, {}).items():
            if _zufall(verdeckt, t, "kipp") < quote:
                x = Status.GESCHLOSSEN.value if x in BEFAHRBAR else Status.OFFEN.value
            s[t] = x
        status[verdeckt] = s
    # Nur der erfundene Winter, kein laufender: die Beispielansicht soll einen vollen Winter zeigen
    erg = auswerten(status, schnee, st, ende, beispiel=True, erzeugt=jetzt.astimezone(BERLIN).isoformat(timespec="minutes"))
    erg["winter"] = [w for w in erg["winter"] if w["name"] == winter_name(jahr)]
    return erg
