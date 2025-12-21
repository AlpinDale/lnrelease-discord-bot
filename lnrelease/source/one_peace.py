import datetime
import re
import warnings
from collections import defaultdict
from pathlib import Path
from random import random
from urllib.parse import urljoin, urlparse, quote

from bs4 import BeautifulSoup

from lnrelease import store
from lnrelease.session import Session
from lnrelease.utils import EPOCH, Format, Info, Key, Series, Table

NAME = "One Peace Books"

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PAGES = DATA_DIR / "one_peace.csv"

ISBN = re.compile(r"^ISBN: (?P<isbn>[\d-]{13,})$")
VOLUME = re.compile(r"(?P<title>.+) Volume (?P<volume>\d+(?:\.\d)?)")


def parse(session: Session, series: Series, link: str, skip: set[str]) -> set[Info]:
    page = session.get(link)
    if not page:
        return set()
    soup = BeautifulSoup(page.content, "lxml")
    info = set()

    lst = reversed(soup.select("div.newbook-case-detail"))
    for index, detail in enumerate(lst, start=1):
        booktitle_elem = detail.select_one(".booktitle")
        if not booktitle_elem or not booktitle_elem.text:
            continue
        booktitle = booktitle_elem.text
        if match := VOLUME.fullmatch(booktitle):
            title = f"{match.group('title')} Volume {match.group('volume').lstrip('0')}"
        else:
            title = booktitle
        isbn_elem = detail.find(class_="bookinfo", string=ISBN)
        if not isbn_elem or not isbn_elem.text:
            continue
        isbn_match = ISBN.fullmatch(isbn_elem.text)
        if not isbn_match:
            continue
        isbn = isbn_match.group("isbn")

        alts: defaultdict[str, list[str]] = defaultdict(list)
        force = True
        links = detail.select(".bookstore-case-detail a")
        links = sorted(links, key=lambda x: "amazon." in x.get("href"))
        formats = {Format.PHYSICAL, Format.DIGITAL}
        for a in links:
            if a.text == "OFFICIAL WIKI":
                continue
            url = a.get("href")
            norm = store.normalise(session, url, resolve=True)
            if norm is None:
                warnings.warn(f"{url} normalise failed", RuntimeWarning)
                continue

            if urlparse(norm).netloc in store.PROCESSED:
                alts[Format.PHYSICAL].append(norm)
            else:
                res = store.parse(
                    session,
                    [norm, url],
                    (force or random() < 0.1) and norm not in skip,
                    series=series,
                    publisher=NAME,
                    title=title,
                    index=index,
                    format="Physical",
                )
                if res and res[1]:
                    info |= res[1]
                    force = False
                    for inf in res[1]:
                        format = Format.from_str(inf.format)
                        formats.add(format)
                        alts[format].append(inf.link)
                else:
                    alts[Format.PHYSICAL].append(norm)

        for format in formats:
            l = f"{link}#:~:text={quote(booktitle)}"
            f = format.name.title()
            i = isbn if format == Format.PHYSICAL else ""
            a = alts[format]
            info.add(Info(series.key, l, NAME, NAME, title, index, f, i, EPOCH, a))

    return info


def scrape_full(series: set[Series], info: set[Info]) -> tuple[set[Series], set[Info]]:
    pages = Table(PAGES, Key)
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=30)
    skip = {
        row.key
        for row in pages
        if isinstance(row, Key) and random() > 0.1 and row.date and row.date < cutoff
    }

    with Session() as session:
        page = session.get("https://www.onepeacebooks.com/books_jt.html")
        if not page:
            return series, info
        soup = BeautifulSoup(page.content, "lxml")
        volumes = soup.select('dt:has(.bookpage-cate:-soup-contains("LIGHT NOVELS")) + dd a')
        for a in volumes:
            try:
                href = a.get("href")
                if not href or not isinstance(href, str):
                    continue
                link = urljoin("https://www.onepeacebooks.com/", href)
                title_elem = a.find("p", class_="booktitle")
                if not title_elem or not title_elem.text:
                    continue
                title = title_elem.text.removesuffix(" Series")
                serie = Series("", title)
                inf = parse(session, serie, link, skip)
                if inf:
                    series.add(serie)
                    info -= {i for i in info if i.serieskey == serie.key} | inf
                    info |= inf
                    for inf in inf:
                        if inf.source == NAME:
                            continue
                        l = Key(inf.link, inf.date)
                        pages.discard(l)
                        pages.add(l)
            except Exception as e:
                warnings.warn(f"({link}): {e}", RuntimeWarning)

    pages.save()
    return series, info
