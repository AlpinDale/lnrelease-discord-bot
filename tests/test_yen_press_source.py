import datetime

from lnrelease.source import yen_press
from lnrelease.utils import Key


def test_yen_press_refreshes_nearby_cached_release():
    today = datetime.date(2026, 4, 30)
    row = Key("9798855400000", today + datetime.timedelta(days=30))

    assert not yen_press.skip_cached_page(row, today)


def test_yen_press_skips_far_future_cached_release_by_default(monkeypatch):
    today = datetime.date(2026, 4, 30)
    row = Key("9798855400000", today + datetime.timedelta(days=180))
    monkeypatch.setattr(yen_press, "random", lambda: 0.5)

    assert yen_press.skip_cached_page(row, today)


def test_yen_press_samples_far_future_cached_release(monkeypatch):
    today = datetime.date(2026, 4, 30)
    row = Key("9798855400000", today + datetime.timedelta(days=180))
    monkeypatch.setattr(yen_press, "random", lambda: 0.0)

    assert not yen_press.skip_cached_page(row, today)


def test_yen_press_skips_non_ln_cached_page_by_default(monkeypatch):
    today = datetime.date(2026, 4, 30)
    row = Key("9798855400000", None)
    monkeypatch.setattr(yen_press, "random", lambda: 0.5)

    assert yen_press.skip_cached_page(row, today)
