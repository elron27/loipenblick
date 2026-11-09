from datetime import datetime

from loipen.worker.main import in_season


def test_in_season_during_winter_day():
    assert in_season(datetime(2027, 1, 15, 9, 0))


def test_not_in_season_at_night():
    assert not in_season(datetime(2027, 1, 15, 23, 0))


def test_not_in_season_in_summer():
    assert not in_season(datetime(2027, 7, 15, 9, 0))
