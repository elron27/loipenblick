"""Ortsseiten Alpbachtal, Wildschoenau, Wilder Kaiser als Querpruefung zu tirol.at (P34, E-24, nur Test).

Schnappschuesse vom 19.11.2026 (Workflow Schnappschuss, Runde P34):
- tests/fixtures/alpbachtal/2026-11-19/langlaufen.html: Loipenbericht-Tabelle, 7 Abschnitte, gespurte km
- tests/fixtures/wildschoenau/2026-11-19/langlaufen.html: gleiche Tabelle (Pimcore/valantic), 6 Loipen
- tests/fixtures/wilderkaiser/2026-11-19/langlaufen-am-wilden-kaiser.html: Liste mit 10 Loipen, Ort, Stil, Laenge
Am 19.11. war in allen drei Regionen alles geschlossen, gespurt 0 km.
Nicht angebunden (Befund in docs/kontaktliste.md): Kitzbuehel (die Karte maps.kitzbuehel.com laedt
tirol.mapservices.eu, also dieselben Daten wie tirol.at) und St. Johann (die Seite /de/stjo/ zeigt nur
eine Teilmenge der schon angebundenen Kitzbueheler-Alpen-Seite).
"""

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.tvb_tabelle import TvbTabelleAdapter
from loipen.adapters.wilderkaiser import WilderKaiserAdapter
from loipen.models import Status, Technik
from tests.helpers import FixtureFetcher
from tests.test_lokale_quellen import quelle

STAND = "2026-11-19"


def lauf(key: str, adapter):
    q = quelle(key)
    return adapter.run(q["base_url"], q["config"], FixtureFetcher(key, q["base_url"], stand=STAND))


@pytest.mark.req("P34", ak=1)
def test_p34_alpbachtal_loipenbericht_mit_gespurten_km():
    r = lauf("alpbachtal", TvbTabelleAdapter())
    assert r.warnungen == []
    assert [l.name for l in r.loipen] == [
        "Inneralpbach Greitergraben", "Inneralpbach Luegergraben", "Loipen Brandenberg", "Loipen Münster",
        "Schönauer Loipe", "Ortsloipe Reith", "Reintalerseeloipe"]
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    assert {l.gespurt_gesamt_km for l in r.loipen} == {0.0}
    assert {l.gebiet_slug for l in r.loipen} == {"alpbachtal"}
    reith = next(l for l in r.loipen if l.name == "Ortsloipe Reith")
    assert reith.startpunkt == "Reith im Alpbachtal" and reith.source_key == "ortsloipe-reith"
    assert reith.quelle_aktualisiert_at is None  # die Seite nennt keinen Stand
    assert all(not l.unbekannte_begriffe for l in r.loipen)


@pytest.mark.req("P34", ak=1)
def test_p34_wildschoenau_gleiche_tabelle():
    r = lauf("wildschoenau", TvbTabelleAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 6
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    assert {l.startpunkt for l in r.loipen} == {"Niederau", "Oberau", "Auffach"}
    assert {l.gebiet_slug for l in r.loipen} == {"wildschoenau"}
    assert next(l for l in r.loipen if l.name == "Höhenloipe Markbachjoch").gespurt_gesamt_km == 0.0


@pytest.mark.req("P34", ak=1)
def test_p34_wilder_kaiser_status_ort_stil_laenge():
    r = lauf("wilderkaiser", WilderKaiserAdapter())
    assert r.warnungen == []
    assert len(r.loipen) == 10
    assert {l.status for l in r.loipen} == {Status.GESCHLOSSEN}
    assert {l.gebiet_slug for l in r.loipen} == {"ellmau", "going", "soell"}
    bichl = next(l for l in r.loipen if l.name == "Bichlloipe Ellmau")
    assert (bichl.laenge_km, bichl.technik, bichl.gebiet_slug) == (1.3, Technik.BEIDES, "ellmau")
    assert bichl.source_url == "https://www.wilderkaiser.info/de/tours/bichlloipe-ellmau.html"
    verb = next(l for l in r.loipen if l.name == "Verbindung Dorfbichl-Sonnbichl")
    assert (verb.laenge_km, verb.technik, verb.gebiet_slug) == (0.9, Technik.KLASSISCH, "soell")  # "900,00 m"
    assert all(not l.unbekannte_begriffe for l in r.loipen)


TABELLE = ('<div class="pimcore_area_content-facility-table"><table><tbody>{}</tbody></table></div>')
ZEILE = ('<tr><td><span class="table__status icon {sym} table__status--{st}"></span></td>'
         '<td><span>{name}</span></td><td><span>{km}</span></td><td>{ort}</td></tr>')


class Seite:
    def __init__(self, html):
        self.html = html

    def get(self, url):
        return self.html


@pytest.mark.req("P34", ak=2)
def test_p34_offene_und_unbekannte_symbole():
    html = TABELLE.format("".join([
        ZEILE.format(sym="icon-check", st="open", name="Loipe Bernau", km="7,5 km", ort="Auffach"),
        ZEILE.format(sym="icon-x", st="closed", name="Loipe Penning", km="0 km", ort="Niederau"),
        ZEILE.format(sym="icon-q", st="wartung", name="Nachtloipe Oberau", km="", ort="Oberau"),
    ]))
    r = TvbTabelleAdapter().run("https://x", {"pfad": "/l", "default_gebiet": "wildschoenau"}, Seite(html))
    offen, zu, neu = r.loipen
    assert (offen.status, offen.gespurt_gesamt_km) == (Status.OFFEN, 7.5)
    assert zu.status == Status.GESCHLOSSEN
    assert neu.status == Status.UNBEKANNT and neu.unbekannte_begriffe == [("status", "wartung")]
    assert neu.gespurt_gesamt_km is None and neu.nachtloipe is True


@pytest.mark.req("P34", ak=2)
def test_p34_leere_seite_gibt_warnung():
    for adapter in (TvbTabelleAdapter(), WilderKaiserAdapter()):
        r = adapter.run("https://x", {"pfad": "/l", "default_gebiet": "ellmau"}, Seite("<html><body>neu</body></html>"))
        assert r.loipen == [] and r.warnungen


def test_p34_adapter_sind_eingetragen():
    assert isinstance(ADAPTERS["tvb_tabelle"], TvbTabelleAdapter)
    assert isinstance(ADAPTERS["wilderkaiser"], WilderKaiserAdapter)


@pytest.mark.req("P34", ak=3)
def test_p34_quellen_nur_test_mit_rang_4_und_querpruefung():
    for key in ("alpbachtal", "wildschoenau", "wilderkaiser"):
        q = quelle(key)
        assert q["rang"] == 4 and q["querpruefung"] is True, key
        assert q["nutzung"]["erlaubnis"] == "nur_test", key
    assert quelle("tirol")["rang"] < 4  # tirol.at bleibt fuehrend
