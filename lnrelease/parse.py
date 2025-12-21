import importlib
import warnings
from collections import defaultdict
from itertools import groupby
from operator import attrgetter
from pathlib import Path

import lnrelease.publisher as publisher
from lnrelease.scrape import INFO, SERIES, DATA_DIR
from lnrelease.utils import (
    FORMATS,
    PRIMARY,
    SECONDARY,
    SOURCES,
    Book,
    Info,
    Series,
    Table,
)

PUBLISHERS = {}
PUBLISHER_DIR = Path(__file__).parent / "publisher"
for file in PUBLISHER_DIR.glob("*.py"):
    if file.stem != "__init__":
        module = importlib.import_module(f"lnrelease.publisher.{file.stem}")
        PUBLISHERS[module.NAME] = module

from lnrelease.scrape import DATA_DIR

BOOKS = DATA_DIR / "books.csv"


def main() -> None:
    series = {row.key: row for row in Table(SERIES, Series) if isinstance(row, Series)}
    info_table = Table(INFO, Info)
    info: list[Info] = [i for i in info_table if isinstance(i, Info)]
    links_dict: defaultdict[str, list[Info]] = defaultdict(list)
    lst: list[Info] = []
    for i in info:
        links_dict[i.link].append(i)
        if (i.source not in SECONDARY or i.publisher not in PRIMARY) or (
            i.source == "BOOK☆WALKER" and i.publisher == "J-Novel Club" and i.format == "Audiobook"
        ):
            lst.append(i)
    lst.sort()
    links: dict[str, list[Info]] = dict(
        sorted(links_dict.items(), key=lambda x: (SOURCES[x[1][0].source], x[1][0].title))
    )
    BOOKS.unlink(missing_ok=True)
    books = Table(BOOKS, Book)

    for key, group in groupby(lst, attrgetter("serieskey", "publisher")):
        serieskey = key[0]
        serie = series[serieskey]
        pub = key[1]
        if pub in PUBLISHERS:
            module = PUBLISHERS[pub]
        else:
            module = publisher
            warnings.warn(f"Unknown publisher: {pub}; {serieskey}", RuntimeWarning)
        inf_dict: defaultdict[str, list[Info]] = defaultdict(list)
        for i in group:
            inf_dict[i.format].append(i)
        inf: dict[str, list[Info]] = dict(
            sorted(inf_dict.items(), key=lambda x: FORMATS.get(x[0], 0))
        )
        for x in module.parse(serie, inf, links).values():
            books.update(x)

    books.save()


if __name__ == "__main__":
    main()
