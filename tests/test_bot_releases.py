import datetime
from lnrelease.bot.releases import get_digital_releases_for_date
from lnrelease.utils import Format


class TestGetDigitalReleasesForDate:
    def test_filters_by_date(self, monkeypatch):
        from lnrelease.bot import releases
        from lnrelease.utils import Release

        test_date = datetime.date(2024, 12, 25)

        mock_releases = [
            Release("s", "l", "p", "Book 1", "1", Format.DIGITAL, "i", test_date),
            Release(
                "s",
                "l",
                "p",
                "Book 2",
                "2",
                Format.DIGITAL,
                "i",
                datetime.date(2024, 12, 26),
            ),
        ]

        def mock_get_all():
            return mock_releases

        monkeypatch.setattr(releases, "get_all_releases", mock_get_all)

        results = get_digital_releases_for_date(test_date)
        assert len(results) == 1
        assert results[0].name == "Book 1"

    def test_filters_out_audiobooks(self, monkeypatch):
        from lnrelease.bot import releases
        from lnrelease.utils import Release

        test_date = datetime.date(2024, 12, 25)

        mock_releases = [
            Release("s", "l", "p", "Digital Book", "1", Format.DIGITAL, "i", test_date),
            Release("s", "l", "p", "Audio Book", "1", Format.AUDIOBOOK, "i", test_date),
        ]

        def mock_get_all():
            return mock_releases

        monkeypatch.setattr(releases, "get_all_releases", mock_get_all)

        results = get_digital_releases_for_date(test_date)
        assert len(results) == 1
        assert results[0].name == "Digital Book"

    def test_filters_out_physical_only(self, monkeypatch):
        from lnrelease.bot import releases
        from lnrelease.utils import Release

        test_date = datetime.date(2024, 12, 25)

        mock_releases = [
            Release("s", "l", "p", "Digital", "1", Format.DIGITAL, "i", test_date),
            Release("s", "l", "p", "Physical", "1", Format.PHYSICAL, "i", test_date),
            Release("s", "l", "p", "Both", "1", Format.PHYSICAL_DIGITAL, "i", test_date),
        ]

        def mock_get_all():
            return mock_releases

        monkeypatch.setattr(releases, "get_all_releases", mock_get_all)

        results = get_digital_releases_for_date(test_date)
        assert len(results) == 2
        names = {r.name for r in results}
        assert "Digital" in names
        assert "Both" in names
        assert "Physical" not in names
