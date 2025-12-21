import pytest
import datetime
from lnrelease.utils import (
    Format,
    clean_str,
    volume_lt,
    Series,
    Info,
    Book,
    Release,
    find_series,
)
from lnrelease.bot.releases import generate_release_id, ReleaseInfo


class TestFormat:
    def test_from_str_physical(self):
        assert Format.from_str("Physical") == Format.PHYSICAL
        assert Format.from_str("Hardcover") == Format.PHYSICAL
        assert Format.from_str("Paperback") == Format.PHYSICAL

    def test_from_str_digital(self):
        assert Format.from_str("Digital") == Format.DIGITAL
        assert Format.from_str("eBook") == Format.DIGITAL

    def test_from_str_audiobook(self):
        assert Format.from_str("Audiobook") == Format.AUDIOBOOK
        assert Format.from_str("Audio") == Format.AUDIOBOOK

    def test_is_digital(self):
        assert Format.DIGITAL.is_digital()
        assert Format.PHYSICAL_DIGITAL.is_digital()
        assert not Format.PHYSICAL.is_digital()
        assert not Format.AUDIOBOOK.is_digital()

    def test_is_physical(self):
        assert Format.PHYSICAL.is_physical()
        assert Format.PHYSICAL_DIGITAL.is_physical()
        assert not Format.DIGITAL.is_physical()
        assert not Format.AUDIOBOOK.is_physical()


class TestCleanStr:
    def test_basic_cleaning(self):
        assert clean_str("Hello World") == "helloworld"

    def test_special_characters(self):
        assert clean_str("Test-Book: Volume 1") == "testbookvolume1"

    def test_unicode_normalization(self):
        assert clean_str("café") == "cafe"

    def test_empty_string(self):
        assert clean_str("") == ""


class TestVolumeLt:
    def test_simple_numbers(self):
        assert volume_lt("1", "2")
        assert not volume_lt("2", "1")
        assert not volume_lt("1", "1")

    def test_decimal_volumes(self):
        assert volume_lt("1", "1.5")
        assert volume_lt("1.5", "2")

    def test_range_volumes(self):
        assert not volume_lt("1", "1-2")
        assert volume_lt("1-3", "4")

    def test_non_numeric_fallback(self):
        assert volume_lt("a", "b")
        assert not volume_lt("b", "a")


class TestSeries:
    def test_creation(self):
        series = Series(key="", title="Test Series")
        assert series.title == "Test Series"
        assert series.key == "testseries"

    def test_key_provided(self):
        series = Series(key="customkey", title="Test Series")
        assert series.key == "customkey"

    def test_title_cleanup(self):
        series = Series(key="", title="Test Series (Light Novels)")
        assert series.title == "Test Series"

    def test_equality(self):
        s1 = Series(key="test", title="Test")
        s2 = Series(key="test", title="Different Title")
        s3 = Series(key="other", title="Test")
        assert s1 == s2
        assert s1 != s3

    def test_hash(self):
        s1 = Series(key="test", title="Test")
        s2 = Series(key="test", title="Different")
        assert hash(s1) == hash(s2)


class TestInfo:
    def test_creation(self, sample_info):
        assert sample_info.serieskey == "testseries"
        assert sample_info.publisher == "Test Publisher"
        assert sample_info.format == "Digital"

    def test_title_cleanup(self):
        info = Info(
            serieskey="test",
            link="http://example.com",
            source="Test",
            publisher="Test",
            title="Book Title (Light Novel)",
            index=1,
            format="Digital",
            isbn="",
            date=datetime.date(2024, 1, 1),
        )
        assert info.title == "Book Title"

    def test_equality_same_link_format(self):
        i1 = Info(
            "s",
            "http://ex.com/1",
            "src",
            "pub",
            "t",
            1,
            "Digital",
            "",
            datetime.date(2024, 1, 1),
        )
        i2 = Info(
            "s",
            "http://ex.com/1",
            "src",
            "pub",
            "t",
            2,
            "Digital",
            "",
            datetime.date(2024, 1, 2),
        )
        assert i1 == i2

    def test_equality_different_format(self):
        i1 = Info(
            "s",
            "http://ex.com/1",
            "src",
            "pub",
            "t",
            1,
            "Digital",
            "",
            datetime.date(2024, 1, 1),
        )
        i2 = Info(
            "s",
            "http://ex.com/1",
            "src",
            "pub",
            "t",
            1,
            "Physical",
            "",
            datetime.date(2024, 1, 1),
        )
        assert i1 != i2


class TestBook:
    def test_creation(self):
        book = Book(
            serieskey="test",
            link="http://example.com",
            publisher="Test Pub",
            name="Test Book",
            volume="1",
            format="Digital",
            isbn="123",
            date=datetime.date(2024, 1, 1),
        )
        assert book.volume == "1"
        assert book.format == "Digital"

    def test_equality(self):
        b1 = Book("s", "l", "p", "n", "1", "Digital", "i", datetime.date(2024, 1, 1))
        b2 = Book("s", "l", "p", "n", "1", "Digital", "i", datetime.date(2024, 1, 1))
        b3 = Book("s", "l", "p", "n", "2", "Digital", "i", datetime.date(2024, 1, 1))
        assert b1 == b2
        assert b1 != b3


class TestRelease:
    def test_equality_same_core_fields(self):
        r1 = Release(
            "s",
            "l1",
            "Pub",
            "Book Name",
            "1",
            Format.DIGITAL,
            "i1",
            datetime.date(2024, 1, 1),
        )
        r2 = Release(
            "s",
            "l2",
            "Pub",
            "Book Name",
            "1",
            Format.DIGITAL,
            "i2",
            datetime.date(2024, 1, 1),
        )
        assert r1 == r2

    def test_equality_different_volume(self):
        r1 = Release(
            "s",
            "l",
            "Pub",
            "Book Name",
            "1",
            Format.DIGITAL,
            "i",
            datetime.date(2024, 1, 1),
        )
        r2 = Release(
            "s",
            "l",
            "Pub",
            "Book Name",
            "2",
            Format.DIGITAL,
            "i",
            datetime.date(2024, 1, 1),
        )
        assert r1 != r2

    def test_sorting_by_date(self):
        r1 = Release("s", "l", "p", "n", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 2))
        r2 = Release("s", "l", "p", "n", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 1))
        releases = sorted([r1, r2])
        assert releases[0] == r2
        assert releases[1] == r1


class TestFindSeries:
    def test_exact_match(self):
        series_set = {
            Series("", "Test Series"),
            Series("", "Other Series"),
        }
        result = find_series("Test Series Volume 1", series_set)
        assert result is not None
        assert result.title == "Test Series"

    def test_longest_match(self):
        series_set = {
            Series("", "Test"),
            Series("", "Test Series"),
        }
        result = find_series("Test Series Volume 1", series_set)
        assert result is not None
        assert result.title == "Test Series"

    def test_no_match(self):
        series_set = {
            Series("", "Other Series"),
        }
        result = find_series("Test Series Volume 1", series_set)
        assert result is None


class TestGenerateReleaseId:
    def test_consistency(self):
        release = Release(
            "test",
            "http://example.com",
            "Publisher",
            "Book Name",
            "1",
            Format.DIGITAL,
            "123",
            datetime.date(2024, 12, 25),
        )
        id1 = generate_release_id(release)
        id2 = generate_release_id(release)
        assert id1 == id2
        assert len(id1) == 16

    def test_different_releases(self):
        r1 = Release("s", "l", "p", "Book 1", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 1))
        r2 = Release("s", "l", "p", "Book 2", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 1))
        assert generate_release_id(r1) != generate_release_id(r2)

    def test_same_book_different_date(self):
        r1 = Release("s", "l", "p", "Book", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 1))
        r2 = Release("s", "l", "p", "Book", "1", Format.DIGITAL, "i", datetime.date(2024, 1, 2))
        assert generate_release_id(r1) != generate_release_id(r2)


class TestReleaseInfo:
    def test_from_release(self):
        release = Release(
            "test",
            "http://example.com",
            "Publisher",
            "Book Name",
            "1",
            Format.DIGITAL,
            "9781234567890",
            datetime.date(2024, 12, 25),
        )
        info = ReleaseInfo.from_release(release)
        assert info.name == "Book Name"
        assert info.volume == "1"
        assert info.publisher == "Publisher"
        assert info.format == Format.DIGITAL
        assert len(info.release_id) == 16
