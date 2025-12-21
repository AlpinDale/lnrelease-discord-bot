import datetime

from lnrelease.publisher import OMNIBUS, PARSE, guess, omnibus, short, standard
from lnrelease.utils import Info, Series


class TestStandard:
    def test_parse_volume_number(self):
        series = Series("", "Test Series")
        info = {
            "Digital": [
                Info(
                    "test",
                    "l1",
                    "s",
                    "p",
                    "Test Series Volume 1",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 1),
                ),
                Info(
                    "test",
                    "l2",
                    "s",
                    "p",
                    "Test Series Volume 2",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 2),
                ),
            ]
        }
        books = {"Digital": [None, None]}

        changed = standard(series, info, books)

        assert changed
        assert books["Digital"][0] is not None
        assert books["Digital"][1] is not None
        assert books["Digital"][0].volume == "1"
        assert books["Digital"][1].volume == "2"

    def test_parse_with_part(self):
        series = Series("", "Test Series")
        info = {
            "Digital": [
                Info(
                    "test",
                    "l",
                    "s",
                    "p",
                    "Test Series Volume 1, Part 2",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 1),
                ),
            ]
        }
        books = {"Digital": [None]}

        standard(series, info, books)

        assert books["Digital"][0] is not None
        assert books["Digital"][0].volume == "1.2"


class TestOmnibus:
    def test_parse_omnibus(self):
        series = Series("", "Test Series")
        info = {
            "Physical": [
                Info(
                    "test",
                    "l",
                    "s",
                    "p",
                    "Test Series Volumes 1-3",
                    0,
                    "Physical",
                    "",
                    datetime.date(2024, 1, 1),
                ),
            ]
        }
        books = {"Physical": [None]}

        changed = omnibus(series, info, books)

        assert changed
        assert books["Physical"][0] is not None
        assert books["Physical"][0].volume == "1-3"


class TestGuess:
    def test_sequential_guessing(self):
        series = Series("", "Test Series")
        info = {
            "Digital": [
                Info(
                    "test",
                    "l1",
                    "s",
                    "p",
                    "Unknown Title 1",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 1),
                ),
                Info(
                    "test",
                    "l2",
                    "s",
                    "p",
                    "Unknown Title 2",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 2),
                ),
                Info(
                    "test",
                    "l3",
                    "s",
                    "p",
                    "Unknown Title 3",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 3),
                ),
            ]
        }
        books = {"Digital": [None, None, None]}

        guess(series, info, books)

        assert books["Digital"][0] is not None
        assert books["Digital"][1] is not None
        assert books["Digital"][2] is not None
        assert books["Digital"][0].volume == "1"
        assert books["Digital"][1].volume == "2"
        assert books["Digital"][2].volume == "3"


class TestShort:
    def test_parse_short_number(self):
        series = Series("", "Test Series")
        info = {
            "Digital": [
                Info(
                    "test",
                    "l1",
                    "s",
                    "p",
                    "Test Series 1",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 1),
                ),
                Info(
                    "test",
                    "l2",
                    "s",
                    "p",
                    "Test Series 2",
                    0,
                    "Digital",
                    "",
                    datetime.date(2024, 1, 2),
                ),
            ]
        }
        books = {"Digital": [None, None]}

        short(series, info, books)

        assert books["Digital"][0] is not None
        assert books["Digital"][1] is not None
        assert books["Digital"][0].volume == "1"
        assert books["Digital"][1].volume == "2"


class TestParseRegex:
    def test_parse_regex(self):
        match = PARSE.fullmatch("Test Series Volume 5")
        assert match is not None
        assert match.group("name") == "Test Series"
        assert match.group("volume") == "5"

    def test_parse_with_colon(self):
        match = PARSE.fullmatch("Test Series: Volume 3")
        assert match is not None
        assert match.group("volume") == "3"

    def test_omnibus_regex(self):
        match = OMNIBUS.fullmatch("Test Series Volumes 1-3")
        assert match is not None
        assert match.group("name") == "Test Series"
        assert match.group("volume") == "1-3"
