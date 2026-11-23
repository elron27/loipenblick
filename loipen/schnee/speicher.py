"""Ergebnisse eines Schnee-Adapters in die Datenbank schreiben (S1, S2, S4, S9).

- Stationen: Abgleich je Quelle; neue kommen dazu, fehlende werden inaktiv, nie geloescht (S2 AK 4).
  Ohne Hoehe wird eine Station nicht uebernommen, sondern gemeldet (S2 AK 2).
- Messwerte: ein zweiter Lauf legt nichts doppelt an; ein geaenderter Wert wird neue Fassung (S1 AK 3).
- Lageberichte: jede Fassung (dienst, bulletin_id, ausgabe_at) genau einmal (S4).
"""

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from loipen.models import (
    LageberichtFassung,
    LageberichtRegion,
    SchneeMesswert,
    SchneeModellwert,
    SchneeRohdatei,
    SchneeStation,
    Warnregion,
    utcnow,
)
from loipen.schnee.daten import Ergebnis


class Zaehler:
    def __init__(self):
        self.stationen = 0
        self.werte = 0
        self.warnungen: list[str] = []


def speichere(session: Session, quelle: str, erg: Ergebnis, rohdatei: SchneeRohdatei | None = None,
              jetzt: datetime | None = None, nachgeladen: bool = False, katalog_vollstaendig: bool = False,
              land: str | None = None) -> Zaehler:
    jetzt = jetzt or utcnow()
    z = Zaehler()
    z.warnungen += erg.warnungen
    stationen = _stationen(session, quelle, erg, jetzt, z, katalog_vollstaendig)
    for m in erg.messwerte:
        st = stationen.get(m.station)
        if st is None:
            continue  # Station unbekannt oder ohne Hoehe
        z.werte += _messwert(session, st, m, rohdatei, jetzt)
    for b in erg.berichte:
        z.werte += _bericht(session, quelle, b, rohdatei, jetzt, nachgeladen)
    for mw in erg.modellwerte:
        z.werte += _modellwert(session, quelle, mw, rohdatei, jetzt)
    for r in erg.regionen:
        reg = session.get(Warnregion, r.id) or Warnregion(id=r.id)
        reg.name, reg.land, reg.dienst, reg.aktualisiert_at = r.name, r.land, quelle, jetzt
        if r.geometrie is not None:
            reg.geometrie = r.geometrie
        session.add(reg)
    session.flush()
    return z


def _stationen(session, quelle, erg, jetzt, z, katalog_vollstaendig) -> dict[str, SchneeStation]:
    vorhanden = {s.kennung: s for s in session.scalars(select(SchneeStation).where(SchneeStation.quelle == quelle))}
    gesehen = set()
    for d in erg.stationen:
        if d.hoehe_m is None:
            z.warnungen.append(f"Station {d.kennung} ({d.name}) ohne Höhe, nicht übernommen (S2)")
            continue
        gesehen.add(d.kennung)
        st = vorhanden.get(d.kennung)
        if st is None:
            st = SchneeStation(quelle=quelle, kennung=d.kennung, erstmals_at=jetzt)
            session.add(st)
            vorhanden[d.kennung] = st
        st.name, st.lat, st.lon, st.hoehe_m = d.name, d.lat, d.lon, int(d.hoehe_m)
        st.betreiber, st.land, st.messart = d.betreiber, d.land, d.messart
        st.warnregion = d.warnregion or st.warnregion
        st.messgroessen = sorted(set(d.messgroessen))
        st.aktiv, st.zuletzt_at = True, jetzt
        z.stationen += 1
    if katalog_vollstaendig and gesehen:
        for kennung, st in vorhanden.items():
            if kennung not in gesehen and st.aktiv and st.id is not None:
                st.aktiv = False
    session.flush()
    return {k: v for k, v in vorhanden.items() if v.id is not None and (k in gesehen or v.aktiv)}


def _messwert(session, st, m, rohdatei, jetzt) -> int:
    letzte = session.scalar(
        select(SchneeMesswert).where(SchneeMesswert.station_id == st.id, SchneeMesswert.zeitpunkt == m.zeitpunkt,
                                     SchneeMesswert.groesse == m.groesse, SchneeMesswert.takt == m.takt)
        .order_by(SchneeMesswert.fassung.desc()).limit(1))
    if letzte is not None and abs(letzte.wert - m.wert) < 1e-9:
        return 0
    session.add(SchneeMesswert(station_id=st.id, zeitpunkt=m.zeitpunkt, groesse=m.groesse, wert=m.wert,
                               einheit=m.einheit, takt=m.takt, fassung=(letzte.fassung + 1) if letzte else 1,
                               rohdatei_id=rohdatei.id if rohdatei else None, abgerufen_at=jetzt))
    return 1


def _bericht(session, quelle, b, rohdatei, jetzt, nachgeladen) -> int:
    da = session.scalar(select(func.count()).select_from(LageberichtFassung).where(
        LageberichtFassung.dienst == quelle, LageberichtFassung.bulletin_id == b.bulletin_id,
        LageberichtFassung.ausgabe_at == b.ausgabe_at))
    if da:
        return 0
    f = LageberichtFassung(dienst=quelle, bulletin_id=b.bulletin_id, ausgabe_at=b.ausgabe_at,
                           gueltig_von=b.gueltig_von, gueltig_bis=b.gueltig_bis, sprache=b.sprache, link=b.link,
                           tendenz=b.tendenz, nachgeladen=nachgeladen, abgerufen_at=jetzt,
                           rohdatei_id=rohdatei.id if rohdatei else None)
    stufen = [asdict(s) | {"zahl": s.zahl} for s in b.stufen]
    probleme = [asdict(p) for p in b.probleme]
    for r in dict.fromkeys(b.regionen):
        f.regionen.append(LageberichtRegion(warnregion=r, stufen=stufen, probleme=probleme))
    session.add(f)
    session.flush()
    return len(f.regionen)


def _modellwert(session, quelle, mw, rohdatei, jetzt) -> int:
    alt = session.scalar(select(SchneeModellwert).where(
        SchneeModellwert.quelle == quelle, SchneeModellwert.warnregion == mw.warnregion,
        SchneeModellwert.hoehe_von == mw.hoehe_von, SchneeModellwert.datum == mw.datum,
        SchneeModellwert.groesse == mw.groesse))
    if alt is not None:
        return 0
    session.add(SchneeModellwert(quelle=quelle, warnregion=mw.warnregion, hoehe_von=mw.hoehe_von, datum=mw.datum,
                                 groesse=mw.groesse, mittel=mw.mittel, minimum=mw.minimum, maximum=mw.maximum,
                                 zellen=mw.zellen, rohdatei_id=rohdatei.id if rohdatei else None, abgerufen_at=jetzt))
    return 1
