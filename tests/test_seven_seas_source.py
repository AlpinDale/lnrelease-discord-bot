import datetime

from lnrelease.source import seven_seas
from lnrelease.utils import Info


def make_info(date: datetime.date) -> Info:
    return Info(
        "series",
        "https://sevenseasentertainment.com/books/example/",
        seven_seas.NAME,
        seven_seas.NAME,
        "Example Vol. 1",
        1,
        "Digital",
        "",
        date,
    )


def test_seven_seas_refreshes_recent_modified_series():
    today = datetime.date(2026, 4, 30)
    modified = today - datetime.timedelta(days=10)

    should_refresh, refresh = seven_seas.should_refresh_series(set(), modified, today)

    assert should_refresh
    assert refresh == 4


def test_seven_seas_refreshes_old_modified_series_with_upcoming_release():
    today = datetime.date(2026, 4, 30)
    modified = today - datetime.timedelta(days=120)
    previous = {make_info(today + datetime.timedelta(days=90))}

    should_refresh, refresh = seven_seas.should_refresh_series(previous, modified, today)

    assert should_refresh
    assert refresh == 10


def test_seven_seas_skips_old_inactive_api_series_by_default(monkeypatch):
    today = datetime.date(2026, 4, 30)
    modified = today - datetime.timedelta(days=120)
    previous = {make_info(today - datetime.timedelta(days=400))}
    monkeypatch.setattr(seven_seas, "random", lambda: 0.5)

    should_refresh, refresh = seven_seas.should_refresh_series(previous, modified, today)

    assert not should_refresh
    assert refresh == 10


def test_seven_seas_samples_old_inactive_api_series(monkeypatch):
    today = datetime.date(2026, 4, 30)
    modified = today - datetime.timedelta(days=120)
    previous = {make_info(today - datetime.timedelta(days=400))}
    monkeypatch.setattr(seven_seas, "random", lambda: 0.0)

    should_refresh, refresh = seven_seas.should_refresh_series(previous, modified, today)

    assert should_refresh
    assert refresh == 10
