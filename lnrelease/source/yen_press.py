import datetime
import re
import warnings
from pathlib import Path
from random import random

from bs4 import BeautifulSoup, element

from lnrelease.session import Session
from lnrelease.utils import FORMATS, Info, Key, Series, Table

NAME = "Yen Press"

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PAGES = DATA_DIR / "yen_press.csv"

TITLES = re.compile(
    r"https://yenpress\.com/titles/\d{13}-(?!.*(manga-vol|vol-\d+-manga|vol-\d+-comic|-chapter-\d+))[\w-]+"
)
LINK = re.compile(r"(https://yenpress.com)?/titles/(?P<isbn>\d{13})-(?P<name>[\w-]+)")
OMNIBUS = re.compile(
    r"contains(?: the complete)? volumes (?P<volume>\d+(?:\.\d)?-\d+(?:\.\d)?)",
    flags=re.IGNORECASE,
)
START = re.compile(
    r"(?P<start>.+?) (?:omnibus |collector\'s edition |volume )+\d+(?: \(light novel\))?",
    flags=re.IGNORECASE,
)


def parse(session: Session, link: str, links: dict[str, str]) -> None | tuple[Series, set[Info]]:
    page = session.get(link)
    if page is None or page.status_code == 404:
        return None
    soup = BeautifulSoup(page.content, "lxml")

    formats: list[str] = [x.text for x in soup.select(".tabs > span")]
    details: element.ResultSet[element.Tag] = soup.select(".book-details > div")
    if not formats or not details:
        return None
    series_elem = details[0].select_one('span:-soup-contains("Series") + p')
    if not series_elem or not series_elem.text:
        return None
    series_title = series_elem.text
    if series_title.endswith("(light novel serial)"):
        return None

    category_elem = soup.select_one("div.breadcrumbs.desktop-only > a:last-child")
    if not category_elem:
        return None
    category = category_elem.get("href")
    if not category:
        return None
    imprint_elem = details[0].select_one('span:-soup-contains("Imprint") + p')
    if not imprint_elem or not imprint_elem.text:
        return None
    imprint = imprint_elem.text
    # category of ebooks is inconsistent
    if (
        category != "/category/light-novels"
        and category != "/category/audio-books"
        and imprint != "Yen On"
        and imprint != "Yen Audio"
    ):
        return None

    title_elem = soup.select_one("h1.heading")
    if not title_elem or not title_elem.text:
        return None
    title = title_elem.text
    if (
        (desc := soup.select_one(".book-info > .content-heading-txt"))
        and (vol := OMNIBUS.search(desc.text))
        and (start := START.fullmatch(title))
    ):  # rename omnibus volume
        title = f"{start.group('start')} Volume {vol.group('volume')}"
    series = Series("", series_title)
    info = set()
    publisher = imprint if imprint == "J-Novel Club" else NAME
    for format, detail in zip(formats, details, strict=False):
        if format not in FORMATS:
            continue

        isbn_elem = detail.select_one('span:-soup-contains("ISBN") + p')
        date_elem = detail.select_one('span:-soup-contains("Release Date") + p')
        if not isbn_elem or not isbn_elem.text or not date_elem or not date_elem.text:
            continue
        isbn = isbn_elem.text
        date = datetime.datetime.strptime(date_elem.text, "%b %d, %Y").date()
        if isbn not in links:
            continue
        info.add(Info(series.key, links[isbn], NAME, publisher, title, 0, format, isbn, date))

    if info:
        return series, info
    return None


def scrape_full(series: set[Series], info: set[Info]) -> tuple[set[Series], set[Info]]:
    pages = Table(PAGES, Key)
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=180)
    # no date = not light novel
    skip = {
        row.key
        for row in pages
        if isinstance(row, Key) and random() > 0.2 and (not row.date or row.date < cutoff)
    }

    isbns: dict[str, Info] = {inf.isbn: inf for inf in info}

    with Session() as session:
        page = session.get("https://yenpress.com/sitemap.xml")
        if not page:
            return series, set(isbns.values())
        soup = BeautifulSoup(page.content, "lxml-xml")

        links = {}
        for x in soup.find_all("loc"):
            if x.text and TITLES.fullmatch(x.text):
                match = LINK.fullmatch(x.text)
                if match:
                    links[match.group("isbn")] = x.text
        for isbn, link in links.items():
            if isbn in skip:
                continue

            try:
                res = parse(session, link, links)
                if res:
                    series.add(res[0])
                    for inf in res[1]:
                        isbns[inf.isbn] = inf
                        date = inf.date
                        key = Key(inf.isbn, date)
                        pages.discard(key)
                        pages.add(key)
                        skip.add(inf.isbn)
                elif isbn not in isbns:
                    key = Key(isbn, datetime.date.today())
                    pages.discard(key)
                    pages.add(key)
            except Exception as e:
                warnings.warn(f"({link}): {e}", RuntimeWarning, stacklevel=2)

    pages.save()
    return series, set(isbns.values())
