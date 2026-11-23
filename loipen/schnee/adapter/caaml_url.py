"""Lawinenlageberichte im Format CAAML v6 ueber feste URL-Muster (S4, S5).

Optionen in config/schnee.yaml:
  regionen:  EAWS-Codes, z. B. [DE-BY, AT-05]
  sprache:   de (Standard)
  url_neu:   Muster fuer den neuesten Bericht, {region} {sprache}; optional
  url_tag:   Muster fuer einen Tag, {datum} {region} {sprache}
  tage:      welche Tage bei jedem Lauf geholt werden, relativ zu heute (Standard [0, 1]: heute und morgen)
Abendbericht und Morgen-Aktualisierung ueberschreiben bei manchen Diensten die Datei des Tages. Deshalb holt der
Job mehrmals am Tag; jede neue Fassung (andere Ausgabezeit) wird gespeichert, gleiche Dateien nur einmal.
404 heisst "kein Bericht" (Saison noch nicht begonnen) und ist kein Fehler.
"""

from datetime import date, datetime, timedelta

from loipen.fetcher import HttpFehler
from loipen.schnee import caaml
from loipen.schnee.adapter._hilfe import BERLIN, UTC
from loipen.schnee.adapter._hilfe import tage as _tage
from loipen.schnee.daten import Ergebnis


def _urls(q, tag: date | None, jetzt: datetime | None = None) -> list[tuple[str, str]]:
    o = q.optionen
    sprache = o.get("sprache", "de")
    out = []
    for region in o.get("regionen", []):
        if tag is None:
            if o.get("url_neu"):
                zeit = (jetzt or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                out.append((region, o["url_neu"].format(region=region, sprache=sprache, jetzt=zeit)))
        else:
            out.append((region, o["url_tag"].format(datum=tag.isoformat(), region=region, sprache=sprache)))
    return out


def _hole(fetcher, url):
    try:
        return fetcher.get_bytes(url)
    except HttpFehler as e:
        if e.status == 404:
            return None
        raise


def abrufe(q, fetcher, jetzt: datetime, session=None):
    from loipen.schnee.sammler import Antwort
    gesehen = set()
    ziele = _urls(q, None, jetzt)
    heute = _tage(jetzt, 0)[0]
    for versatz in q.optionen.get("tage", [0, 1]):
        ziele += _urls(q, heute + timedelta(days=versatz))
    for _, url in ziele:
        if url in gesehen:
            continue
        gesehen.add(url)
        inhalt = _hole(fetcher, url)
        if inhalt:
            yield Antwort(url=url, inhalt=inhalt)


def archiv_urls(q, tag: date) -> list[str]:
    """S5: URLs der Berichte eines frueheren Tages."""
    return [url for _, url in _urls(q, tag)]


def verarbeite(antwort, q) -> Ergebnis:
    berichte = caaml.lies(antwort.inhalt)
    erlaubt = set(q.optionen.get("nur_regionen") or [])
    if erlaubt:  # Sammelberichte (EUREGIO) enthalten auch Regionen anderer Quellen
        for b in berichte:
            b.regionen = [r for r in b.regionen if any(r.startswith(p) for p in erlaubt)]
        berichte = [b for b in berichte if b.regionen]
    vorlage = q.optionen.get("link")
    for b in berichte:  # CAAML-Dateien der Dienste enthalten meist keinen Link auf die Webseite des Berichts
        if not b.link and vorlage:
            b.link = vorlage.format(datum=b.gueltig_bis.astimezone(BERLIN).date().isoformat(),
                                    region=b.regionen[0])
    return Ergebnis(berichte=berichte)
