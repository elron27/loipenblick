"""Fruehere Winter nachladen (S5), einmalig von Hand: python -m loipen.worker schnee-archiv <quelle> [von] [bis]

- Nur Tage der Saison (1. November bis 31. Mai), ab archiv_ab der Quelle.
- Ruecksichtsvoll (S5 AK 2): hoechstens eine Anfrage je Sekunde (der Fetcher haelt zusaetzlich den Abstand je
  Domain ein), nach jedem Tag ein Commit. Unterbrechbar und fortsetzbar: URLs, die schon als Rohdatei vorliegen,
  werden uebersprungen.
- Gespeicherte Berichte sind als nachgeladen gekennzeichnet (S5 AK 3): Ihnen fehlen die Tagesfassungen.
- 404 heisst "an diesem Tag kein Bericht" (Sommer, Saisonbeginn) und ist kein Fehler.
"""

import logging
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from loipen.models import SchneeRohdatei, utcnow
from loipen.schnee.adapter._hilfe import antwort
from loipen.schnee.konfig import SchneeQuelle
from loipen.schnee.sammler import adapter, sammle_quelle

log = logging.getLogger("loipen.schnee.archiv")
SAISON = ((11, 1), (5, 31))


def in_saison(tag: date) -> bool:
    (vm, vt), (bm, bt) = SAISON
    return (tag.month, tag.day) >= (vm, vt) or (tag.month, tag.day) <= (bm, bt)


def tage(von: date, bis: date) -> list[date]:
    return [von + timedelta(days=i) for i in range((bis - von).days + 1) if in_saison(von + timedelta(days=i))]


def lade_nach(session_scope: Callable, q: SchneeQuelle, fetcher, wurzel: Path, von: date | None = None,
              bis: date | None = None, pause_s: float = 1.0, schlafen: Callable[[float], None] = time.sleep) -> dict:
    mod = adapter(q.adapter)
    if not hasattr(mod, "archiv_urls"):
        raise ValueError(f"Quelle {q.key} hat kein Archiv")
    von = von or date.fromisoformat(q.archiv_ab)
    bis = bis or date.today() - timedelta(days=1)
    stand = {"tage": 0, "abrufe": 0, "uebersprungen": 0, "neu": 0, "ohne_bericht": 0}
    for tag in tage(von, bis):
        with session_scope() as session:
            urls = mod.archiv_urls(q, tag)
            vorhanden = set(session.scalars(select(SchneeRohdatei.url).where(SchneeRohdatei.url.in_(urls))))
            antworten = []
            for url in urls:
                if url in vorhanden:
                    stand["uebersprungen"] += 1
                    continue
                a = antwort(fetcher, url, "archiv", tag=tag.isoformat())
                stand["abrufe"] += 1
                schlafen(pause_s)
                if a.art == "fehler":
                    if "404" in a.meta.get("fehler", ""):
                        stand["ohne_bericht"] += 1
                        continue
                    raise RuntimeError(f"{url}: {a.meta['fehler']}")  # Abbruch; beim naechsten Start geht es hier weiter
                antworten.append(a)
            if antworten:
                lauf = sammle_quelle(session, q, fetcher, wurzel, utcnow(), antworten=antworten, nachgeladen=True,
                                     protokoll=False)
                stand["neu"] += lauf.neu
        stand["tage"] += 1
        if stand["tage"] % 30 == 0:
            log.info("Archiv %s: bis %s, %s", q.key, tag, stand)
    log.info("Archiv %s fertig: %s", q.key, stand)
    return stand
