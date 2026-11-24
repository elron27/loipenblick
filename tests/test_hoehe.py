"""Hoehe einer Loipe aus dem Hoehenmodell (D23), ohne Netz: die Hoehen entlang der Strecke sind nachgebildet."""

import pytest

from loipen import hoehe


@pytest.mark.req("D23", ak=1)
def test_d23_punkte_hoechstens_50_m_auseinander():
    linie = [(47.0, 12.0), (47.0, 12.01)]  # rund 760 m
    punkte = hoehe.verdichte(linie)
    assert punkte[0] == linie[0] and punkte[-1] == pytest.approx(linie[-1])
    assert max(hoehe._m(a, b) for a, b in zip(punkte, punkte[1:])) <= 50.0
    assert len(punkte) == 17


@pytest.mark.req("D23", ak=1)
def test_d23_hoehenmeter_geglaettet():
    # 100 m Anstieg, 100 m Abstieg, mit Messrauschen von +-3 m
    rauschen = [3, -3] * 50
    hoehen = [1000 + i + rauschen[i] for i in range(100)] + [1100 - i + rauschen[i] for i in range(100)]
    k = hoehe.kennzahlen(hoehen)
    assert 95 <= k["hoehenmeter"] <= 125  # ungeglaettet waeren es ueber 300 m
    assert (k["hoechster_punkt_m"], k["tiefster_punkt_m"]) == (1103, 998)
    assert hoehe.kennzahlen([None, 1000]) is None


@pytest.mark.req("D23", ak=2)
def test_d23_freigabe_nur_bei_kleiner_abweichung():
    assert hoehe.freigabe([(110, 109), (420, 430), (160, 150)]) == (True, pytest.approx(0.0233, abs=0.001))
    ok, m = hoehe.freigabe([(200, 109), (900, 430), (150, 150)])
    assert not ok and m > 0.25
    assert hoehe.freigabe([]) == (False, None)


@pytest.mark.req("D23", ak=3)
def test_d23_kachel_und_quellenangabe():
    assert hoehe.kachel(47.67, 12.01).endswith("Copernicus_DSM_COG_10_N47_00_E012_00_DEM.tif")
    assert "COPERNICUS" in hoehe.QUELLENANGABE
