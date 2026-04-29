import datetime

from lnrelease.source import hanashi


def test_hanashi_remove_archive_url():
    link = "https://web.archive.org/web/20260214215045/https://books.apple.com/us/book/id123"

    assert hanashi.remove_archive(link) == "https://books.apple.com/us/book/id123"


def test_hanashi_volume_path_formats_integer_and_decimal():
    assert hanashi.volume_path(8.0) == "8"
    assert hanashi.volume_path(8.5) == "8.5"


def test_hanashi_parse_volume_numbers_from_embedded_script():
    script = "novel:{Volume:[{number:1},{number:2},{number:8.5}],wings:[]}"

    assert hanashi.parse_volume_numbers(script) == [1.0, 2.0, 8.5]


def test_hanashi_parse_embedded_volume_data():
    script = (
        'data:{volume:{number:8.5,release:new Date(1759190400000),'
        'amazon:"https://web.archive.org/web/20260214215045/https://a.co/example",'
        'apple:"https://books.apple.com/us/book/id123"}}},uses:{params:["id","volume"]}'
    )

    number, date, links = hanashi.parse_embedded_volume(script)

    assert number == "8.5"
    assert date == datetime.date(2025, 9, 30)
    assert links == ["https://a.co/example", "https://books.apple.com/us/book/id123"]
