import datetime
import hashlib
from collections import defaultdict
from dataclasses import dataclass

from lnrelease.parse import BOOKS
from lnrelease.utils import FORMATS, Book, Format, Release, Table


@dataclass
class ReleaseInfo:
    release_id: str
    date: datetime.date
    name: str
    volume: str
    publisher: str
    link: str
    isbn: str
    format: Format

    @classmethod
    def from_release(cls, release: Release) -> "ReleaseInfo":
        release_id = generate_release_id(release)
        return cls(
            release_id=release_id,
            date=release.date,
            name=release.name,
            volume=release.volume,
            publisher=release.publisher,
            link=release.link,
            isbn=release.isbn,
            format=release.format,
        )


def generate_release_id(release: Release) -> str:
    key = f"{release.date.isoformat()}|{release.publisher}|{release.name}|{release.volume}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def get_all_releases() -> list[Release]:
    dic: defaultdict[Release, list[Book]] = defaultdict(list)
    for item in sorted(Table(BOOKS, Book)):
        if not isinstance(item, Book):
            continue
        book = item
        release = Release(
            serieskey=book.serieskey,
            link=book.link,
            publisher=book.publisher,
            name=book.name,
            volume=book.volume,
            format=Format.from_str(book.format),
            isbn=book.isbn,
            date=book.date,
        )
        dic[release].append(book)
    for release, books in dic.items():
        books.sort(key=lambda b: FORMATS.get(b.format, 0))
        formats = {Format.from_str(b.format) for b in books}
        release.format = formats.pop() if len(formats) == 1 else Format.PHYSICAL_DIGITAL
        release.link = books[0].link
        release.isbn = books[0].isbn
    return sorted(dic)


def get_digital_releases_for_date(date: datetime.date) -> list[ReleaseInfo]:
    all_releases = get_all_releases()
    digital_releases = []

    for release in all_releases:
        if release.date != date:
            continue

        if release.format == Format.AUDIOBOOK:
            continue

        if not release.format.is_digital():
            continue

        digital_releases.append(ReleaseInfo.from_release(release))

    return digital_releases


def get_digital_releases_for_today(timezone_str: str = "UTC") -> list[ReleaseInfo]:
    import zoneinfo

    tz = zoneinfo.ZoneInfo(timezone_str)
    today = datetime.datetime.now(tz).date()
    return get_digital_releases_for_date(today)
