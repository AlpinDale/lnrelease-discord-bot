from lnrelease.utils import Book, Info, Series

from . import check, copy, guess, standard

NAME = "Impress Corporation"


def parse(
    series: Series, info: dict[str, list[Info]], links: dict[str, list[Info]]
) -> dict[str, list[Book]]:
    books: dict[str, list[Book | None]] = {}
    for format, lst in info.items():
        books[format] = [None] * len(lst)

    standard(series, info, books)
    guess(series, info, books)
    copy(series, info, books)
    check(series, info, books)
    return {k: [b for b in v if b is not None] for k, v in books.items()}
