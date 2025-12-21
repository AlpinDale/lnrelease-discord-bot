from lnrelease.utils import Book, Info, Series

from . import check, copy, one, standard, url

NAME = "VIZ Media"


def parse(series: Series, info: dict[str, list[Info]], links: set[Info]) -> dict[str, list[Book]]:
    books: dict[str, list[Book | None]] = {}
    for format, lst in info.items():
        books[format] = [None] * len(lst)

    standard(series, info, books)
    url(series, info, books)
    one(series, info, books)
    copy(series, info, books)
    check(series, info, books)
    return {k: [b for b in v if b is not None] for k, v in books.items()}
