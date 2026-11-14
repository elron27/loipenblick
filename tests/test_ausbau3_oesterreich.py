"""Ausbaustufe 3, Oesterreich (E-21): St. Anton am Arlberg (P27), Kaernten (P28).

Schnappschuss vom 13.11.2026 (Workflow Schnappschuss, Runde 11):
- tests/fixtures/st-anton/2026-11-13/aktueller-loipenzustand.html: Loipenzustand St. Anton, Stand 13.11.2026 16:16.
"""

import pytest

from loipen.adapters import ADAPTERS
from loipen.konfig import CONFIG_DIR, lade_yaml
from loipen.models import Schwierigkeit, Status
from tests.helpers import SEITEN_QUELLEN, FixtureFetcher


def quelle(key: str) -> dict:
    return next(q for q in lade_yaml(CONFIG_DIR / "sources.yaml")["quellen"] if q["key"] == key)


def lauf(key: str, ersetze: dict | None = None):
    q = quelle(key)
    fetcher = FixtureFetcher(key, q["base_url"], seiten=SEITEN_QUELLEN.get(key), ersetze=ersetze)
    return ADAPTERS[q["adapter"]].run(q["base_url"], q["config"], fetcher), fetcher


@pytest.mark.req("P27", ak=1)
def test_p27_st_anton_loipen_mit_status_und_stand():
    erg, fetcher = lauf("st-anton")
    assert len(fetcher.abgerufen) == 1 and erg.warnungen == []
    assert len(erg.loipen) == 15  # Winterwanderwege fallen weg
    assert not [d for d in erg.loipen if d.name.startswith("Winterwanderweg")]
    assert {d.gebiet_slug for d in erg.loipen} == {"st-anton"}
    assert {d.status for d in erg.loipen} == {Status.GESCHLOSSEN}
    assert all(d.quelle_aktualisiert_at.strftime("%d.%m.%Y %H:%M") == "13.11.2026 16:16" for d in erg.loipen)
    verwall = next(d for d in erg.loipen if d.name.startswith("Loipe Verwall 10 km (Start"))
    assert verwall.schwierigkeit == Schwierigkeit.MITTEL
    assert verwall.laenge_km == 2.5  # Teilstueck, nicht die ganze Loipe
    nacht = next(d for d in erg.loipen if d.name.startswith("Night"))
    assert nacht.nachtloipe is True


@pytest.mark.req("P27", ak=2)
def test_p27_offene_loipe_und_geaenderter_aufbau():
    q = quelle("st-anton")
    pfad = q["config"]["pfad"].strip("/")
    seite = FixtureFetcher("st-anton", q["base_url"], seiten=SEITEN_QUELLEN["st-anton"]).get(
        q["base_url"] + "/" + pfad)
    offen = seite.replace("skiing-entry skiing-status-close", "skiing-entry skiing-status-open", 1)
    erg, _ = lauf("st-anton", ersetze={pfad: offen})
    assert erg.loipen[0].status == Status.OFFEN and erg.loipen[0].status_rohtext == "geöffnet"
    erg, _ = lauf("st-anton", ersetze={pfad: "<html><body>Neu</body></html>"})
    assert erg.loipen == [] and "Seitenaufbau" in erg.warnungen[0]


# ---------- P28: Kaernten, Wintersportbericht Nassfeld-Pressegger See ----------
# Schnappschuss: tests/fixtures/nassfeld-nlw/2026-11-13/wintersportbericht-nps.pdf (Runde 12).
# Mitte November melden alle sechs Orte "0 / n" Loipen offen.

NLW_ORTE = {"hermagor", "gitschtal", "kirchbach", "dellach-gailtal", "koetschach-mauthen", "weissensee-techendorf"}


@pytest.mark.req("P28", ak=1)
def test_p28_je_ort_ein_loipennetz_im_kaerntner_gebiet():
    erg, fetcher = lauf("nassfeld-nlw")
    assert len(fetcher.abgerufen) == 1 and erg.warnungen == []
    assert {d.gebiet_slug for d in erg.loipen} == NLW_ORTE
    assert all(d.name.startswith("Loipennetz ") for d in erg.loipen)
    stand = {d.quelle_aktualisiert_at.strftime("%d.%m.%Y %H:%M") for d in erg.loipen}
    assert stand == {"13.11.2026 09:00"}  # Erzeugung des PDFs 08:00 UTC
    g = {x["slug"]: x for x in lade_yaml(CONFIG_DIR / "gebiete.yaml")["gebiete"]}
    r = {x["slug"]: x for x in lade_yaml(CONFIG_DIR / "gebiete.yaml")["regionen"]}
    assert {r[g[s]["region"]]["bundesland"] for s in NLW_ORTE} == {"Kärnten"}
    assert all(g[s]["wetterstation"]["dienst"] == "geosphere" for s in NLW_ORTE)


@pytest.mark.req("P28", ak=2)
def test_p28_status_aus_dem_zaehler():
    from loipen.adapters.kaernten import NlwBerichtAdapter
    q = quelle("nassfeld-nlw")
    text = "Heute 20.12.2026\nLoipen\nHermagor 9 / 9\nGitschtal 1 / 2\nKirchbach 0 / 1\nDellach 0 / 0\n"
    erg = NlwBerichtAdapter().run_text(text, q["base_url"] + q["config"]["pfad"], q["config"])
    st = {d.gebiet_slug: d.status for d in erg.loipen}
    assert st == {"hermagor": Status.OFFEN, "gitschtal": Status.EINGESCHRAENKT,
                  "kirchbach": Status.GESCHLOSSEN, "dellach-gailtal": Status.UNBEKANNT}
    gitschtal = next(d for d in erg.loipen if d.gebiet_slug == "gitschtal")
    assert gitschtal.status_rohtext == "Wintersportbericht NLW: 1 von 2 Loipen offen"
    assert gitschtal.quelle_aktualisiert_at.strftime("%d.%m.%Y") == "20.12.2026"
    # Schnappschuss: alles geschlossen
    erg, _ = lauf("nassfeld-nlw")
    assert {d.status for d in erg.loipen} == {Status.GESCHLOSSEN}
    assert all(d.status_rohtext.startswith("Wintersportbericht NLW: 0 von ") for d in erg.loipen)


@pytest.mark.req("P28", ak=3)
def test_p28_fehlender_ort_oder_zaehler_gibt_warnung():
    from loipen.adapters.kaernten import NlwBerichtAdapter
    q = quelle("nassfeld-nlw")
    url = q["base_url"] + q["config"]["pfad"]
    erg = NlwBerichtAdapter().run_text("Loipen\nHermagor 0 / 9\n", url, q["config"])
    assert len(erg.loipen) == 1 and len(erg.warnungen) == 5 and "kein Zaehler" in erg.warnungen[0]
    erg = NlwBerichtAdapter().run_text("Pistenbericht ohne Loipen", url, q["config"])
    assert erg.loipen == [] and "Aufbau" in erg.warnungen[0]


def test_neue_hosts_oesterreich_stehen_in_der_cloud_liste():
    hosts = set(lade_yaml(CONFIG_DIR / "cloud-umgebung.yaml")["hosts"])
    assert {"www.stantonamarlberg.com", "tools.nlw.at"} <= hosts
