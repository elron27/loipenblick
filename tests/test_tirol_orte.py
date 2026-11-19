"""Ortsseiten Oetztal, Pitztal, Tiroler Oberland/Nauders, Serfaus-Fiss-Ladis, Paznaun (P31, E-24).

Schnappschuesse vom 19.11.2026 (Workflow Schnappschuss, Runden 21 bis 23), Fixture-Regressionstests nach
CLAUDE.md Regel 10:
- oetztal/2026-11-19/: Sitemap, Tourensitemap und 6 der 22 Loipen-Detailseiten (Outdooractive-ID als Dateiname)
- pitztal/2026-11-19/: Tourenportal Langlaufen, Seite 1 und ?page=2 (Micado, Daten in self.__next_f)
- tiroler-oberland/2026-11-19/, nauders/2026-11-19/: "Geöffnete Einrichtungen" (Pimcore, Valantic)
- serfaus-fiss-ladis/2026-11-19/: Langlaufseite und Skigebietsstatus
- paznaun/2026-11-19/: Anlagenliste ischgl.com als JSON (&ajax=1) und die Seite selbst (Stand)
Am 19.11. war fast alles geschlossen; offen waren nur Gletscher/Mandarfen im Pitztal und die
Opening Loipe am Vermunt (Paznaun), die tirol.at ebenfalls offen fuehrt.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from loipen.adapters import ADAPTERS
from loipen.adapters.oetztal import OetztalAdapter
from loipen.adapters.paznaun import PaznaunAdapter
from loipen.adapters.pitztal import PitztalAdapter
from loipen.adapters.serfaus import SerfausAdapter
from loipen.adapters.tirol_orte import km, technik
from loipen.adapters.tiroler_oberland import TirolerOberlandAdapter
from loipen.generator.daten import baue
from loipen.konfig import CONFIG_DIR, lade_yaml, nur_test_quellen, pruefe
from loipen.models import Schwierigkeit, Status, Technik
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher
from tests.test_plausibel import JETZT, Welt, loipen_nach_name

BERLIN = ZoneInfo("Europe/Berlin")
P31 = ("oetztal", "pitztal", "tiroler-oberland", "nauders", "serfaus-fiss-ladis", "paznaun")


def quelle(key: str) -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == key)


def lauf(key: str):
    q = quelle(key)
    return ADAPTERS[q["adapter"]].run(q["base_url"], q["config"],
                                       FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN[key]))


def nach_name(r) -> dict:
    return {l.name: l for l in r.loipen}


@pytest.mark.req("P31", ak=1)
def test_p31_oetztal_detailseiten_aus_der_tourensitemap():
    r = lauf("oetztal")
    # 22 Loipen in der Sitemap, 6 Detailseiten im Schnappschuss; die fehlenden ergeben je eine Warnung
    assert len(r.loipen) == 6
    assert len(r.warnungen) == 16 and all("HTTP 404" in w for w in r.warnungen)
    l = nach_name(r)
    assert {x.status for x in r.loipen} == {Status.GESCHLOSSEN}
    lehen = l["Lehen Loipe - Umhausen-Niederthai"]
    assert (lehen.gebiet_slug, lehen.laenge_km, lehen.schwierigkeit) == ("oetztal", 0.656, Schwierigkeit.LEICHT)
    assert lehen.source_key == "oa-23683688" and lehen.quelle_aktualisiert_at is None
    nacht = l["4.1 Nachtloipe Variante - Längenfeld"]
    assert nacht.technik == Technik.SKATING and nacht.nachtloipe is True
    assert l["Langlaufloipe Zwieselstein - Sölden"].gebiet_slug == "soelden"
    assert l["Übungsloipe Obergurgl - Nr. 3"].gebiet_slug == "obergurgl"
    assert l["Übungsloipe - Bergsteigerdorf Vent"].gebiet_slug == "vent"
    assert l["Loipe Ochsengarten"].laenge_km == 4.86 and l["Loipe Ochsengarten"].schwierigkeit == Schwierigkeit.SCHWER
    assert all(not x.unbekannte_begriffe for x in r.loipen)


@pytest.mark.req("P31", ak=1)
def test_p31_pitztal_tourenportal_beide_seiten():
    r = lauf("pitztal")
    assert r.warnungen == []
    # 15 Touren, die Rollerstrecke Mandarfen ist keine Langlauf-Tour (tourObjectTypeIdentifier)
    assert len(r.loipen) == 14
    l = nach_name(r)
    offen = {x.name for x in r.loipen if x.status == Status.OFFEN}
    assert offen == {"Trainingsloipe Mandarfen",
                     "Höhenloipe am Pitztaler Gletscher im Herbst für Gruppen mit Voranmeldung"}
    assert {"Talloipe", "Boden-Runde", "Scheibrand-Runde"} <= set(l)  # Seite 2
    tal = l["Talloipe"]
    assert (tal.laenge_km, tal.schwierigkeit, tal.gebiet_slug) == (21.3, Schwierigkeit.MITTEL, "pitztal")
    # Koordinaten sind in den Seitendaten vertauscht
    assert (round(tal.lat, 3), round(tal.lon, 3)) == (47.112, 10.804)
    assert l["Rifflseeloipe"].gebiet_slug == "pitztaler-gletscher"
    assert l["Nachtloipe Stillebach"].nachtloipe is True


@pytest.mark.req("P31", ak=1)
def test_p31_tiroler_oberland_gruppen_ohne_nauders():
    r = lauf("tiroler-oberland")
    assert r.warnungen == [] and len(r.loipen) == 11
    l = nach_name(r)
    assert not any("Moasloipe" in n for n in l)  # Nauders liest die eigene Quelle
    assert l["Höhenloipe Pfundser Tschey"].gebiet_slug == "tiroler-oberland"
    assert {l[n].gebiet_slug for n in ("Anger-Runde", "Winkel-Runde", "Kaunertal-Runde")} == {"kaunertal"}
    assert {l[n].gebiet_slug for n in ("Bärenbadloipe", "Hubertusloipe")} == {"pitztal"}
    assert {x.status for x in r.loipen} == {Status.GESCHLOSSEN}
    assert l["Anger-Runde"].status_rohtext == "Anlage closed"


@pytest.mark.req("P31", ak=1)
def test_p31_nauders_mit_laenge_technik_und_stand():
    r = lauf("nauders")
    assert r.warnungen == [] and len(r.loipen) == 11  # jede Zeile einmal, obwohl die Reiter sie wiederholen
    l = nach_name(r)
    arsangs = l["Arsangsloipe"]
    assert (arsangs.technik, arsangs.laenge_km, arsangs.schwierigkeit) == (Technik.KLASSISCH, 3.6, Schwierigkeit.LEICHT)
    assert arsangs.quelle_aktualisiert_at == datetime(2026, 11, 19, 15, 40, tzinfo=BERLIN)
    assert l["Höhenloipe Langtaufers"].laenge_km == 15.0
    assert l["Langlaufroute Schwarzer See"].schwierigkeit == Schwierigkeit.SCHWER
    assert {x.status for x in r.loipen} == {Status.GESCHLOSSEN}
    assert {x.gebiet_slug for x in r.loipen} == {"tiroler-oberland"}


@pytest.mark.req("P31", ak=1)
def test_p31_serfaus_status_technik_und_laenge():
    r = lauf("serfaus-fiss-ladis")
    assert r.warnungen == [] and len(r.loipen) == 10
    l = nach_name(r)
    assert {x.status for x in r.loipen} == {Status.GESCHLOSSEN}
    moos = l["Moosloipe L1"]
    assert (moos.laenge_km, moos.technik, moos.schwierigkeit) == (1.0, Technik.BEIDES, Schwierigkeit.LEICHT)
    l10 = l["Langlaufroute Schöngampalm L10"]
    assert (l10.laenge_km, l10.technik, l10.schwierigkeit) == (22.4, Technik.SKATING, Schwierigkeit.SCHWER)
    assert sum(x.laenge_km for x in r.loipen) == pytest.approx(37.5)
    assert {x.gebiet_slug for x in r.loipen} == {"serfaus-fiss-ladis"}


@pytest.mark.req("P31", ak=1)
def test_p31_paznaun_anlagenliste_ohne_samnaun():
    r = lauf("paznaun")
    assert r.warnungen == [] and len(r.loipen) == 20
    l = nach_name(r)
    assert not any("Samnaun" in n for n in l)
    assert [n for n, x in l.items() if x.status == Status.OFFEN] == ["L Opening Loipe"]
    wald = l["L.3 Waldloipe"]
    assert (wald.laenge_km, wald.technik, wald.schwierigkeit) == (5.0, Technik.BEIDES, Schwierigkeit.MITTEL)
    assert wald.startpunkt == "Tschafein"
    assert wald.quelle_aktualisiert_at == datetime(2026, 11, 19, 15, 40, tzinfo=BERLIN)
    assert l["L.10 Loipe Bielerhöhe"].schwierigkeit == Schwierigkeit.SCHWER  # unuebersetzter Schluessel
    assert all(not x.unbekannte_begriffe for x in r.loipen)


@pytest.mark.req("P31", ak=2)
def test_p31_quellen_rang_4_querpruefung_nur_test():
    sources = lade_yaml(CONFIG_DIR / "sources.yaml")
    for key in P31:
        q = quelle(key)
        assert q["rang"] == 4 and q["querpruefung"] is True, key
        assert q["nutzung"]["erlaubnis"] == "nur_test" and q["nutzung"]["robots"] == "erlaubt", key
    assert set(P31) <= set(nur_test_quellen(sources))
    assert quelle("tirol")["rang"] < 4
    assert not [f for f in pruefe(sources, lade_yaml(CONFIG_DIR / "gebiete.yaml")) if any(k in f for k in P31)]
    hosts = set(lade_yaml(CONFIG_DIR / "cloud-umgebung.yaml")["hosts"])
    assert {quelle(k)["base_url"].split("/")[2] for k in P31} <= hosts


@pytest.mark.req("P31", ak=2)
def test_p31_tirol_offen_aber_ortsseite_geschlossen_ist_unplausibel(session):
    """Die Waldloipe im Paznaun: tirol.at offen ohne Beleg, die Ortsseite meldet sie am 19.11. geschlossen."""
    wald = nach_name(lauf("paznaun"))["L.3 Waldloipe"]
    w = Welt(session)
    g = w.gebiet("paznaun", schnee_cm=None, messtag=None)
    w.loipe(g, "Waldloipe")
    w.loipe(g, wald.name, "paznaun", 4, status=wald.status.value, lat=47.0994)
    w.quellen["paznaun"].config = {**w.quellen["paznaun"].config, "querpruefung": True}
    session.flush()
    l = loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["Waldloipe"]
    assert l["status"] == Status.GESCHLOSSEN.value
    assert l["unplausibel"] == ["Der Loipenbericht vor Ort (Quelle paznaun) meldet sie geschlossen"]


@pytest.mark.req("P31", ak=2)
def test_p31_tirol_offen_und_ortsseite_offen_bleibt_offen(session):
    """Opening Loipe: tirol.at und die Ortsseite melden sie offen, kein Widerspruch."""
    opening = nach_name(lauf("paznaun"))["L Opening Loipe"]
    w = Welt(session)
    g = w.gebiet("paznaun", schnee_cm=None, messtag=None)
    w.loipe(g, "Opening Loipe Sedlsee small", stand=JETZT - timedelta(hours=3))
    w.loipe(g, opening.name, "paznaun", 4, status=opening.status.value)
    w.quellen["paznaun"].config = {**w.quellen["paznaun"].config, "querpruefung": True}
    session.flush()
    l = loipen_nach_name(baue(session, JETZT, CONFIG_DIR))["Opening Loipe Sedlsee small"]
    assert l["status"] == Status.OFFEN.value and "unplausibel" not in l


class _Leer:
    def get(self, url: str) -> str:
        return '{"success": true, "html": ""}' if "ajax=1" in url else "<html><body>neu</body></html>"

    def get_bytes(self, url: str) -> bytes:
        return self.get(url).encode()


@pytest.mark.req("P31", ak=3)
@pytest.mark.parametrize("adapter", [OetztalAdapter(), PitztalAdapter(), TirolerOberlandAdapter(),
                                     SerfausAdapter(), PaznaunAdapter()])
def test_p31_geaenderter_seitenaufbau_gibt_warnung(adapter):
    r = adapter.run("https://ort.example", {"default_gebiet": "x"}, _Leer())
    assert r.loipen == [] and r.warnungen


def test_p31_laenge_und_technik_lesen():
    assert (km("5,52 km"), km("656 m"), km("3600\n m"), km("5.5 km"), km("")) == (5.52, 0.656, 3.6, 5.5, None)
    assert technik("Klassisch, Skating") == Technik.BEIDES and technik("Langlaufen Skating") == Technik.SKATING
    assert technik("klassisch") == Technik.KLASSISCH and technik(None) == Technik.UNBEKANNT
