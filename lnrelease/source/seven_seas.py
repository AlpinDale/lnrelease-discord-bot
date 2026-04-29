import datetime
import re
import warnings
from html import unescape
from random import random

from bs4 import BeautifulSoup

from lnrelease.session import CHROME, Session
from lnrelease.utils import PHYSICAL, Info, Series

NAME = "Seven Seas Entertainment"

PAGES = re.compile(r"Page (?P<cur>\d+) of (?P<last>\d+)")
OMNIBUS = re.compile(
    rf"(?P<name>.+?)(?: \w+ Edition \d+)? \(Light Novel\)\s*\(Vol\. (?P<volume>\d+(?:\.\d)?-\d+(?:\.\d)?) ?(?P<format>{'|'.join(PHYSICAL)})? Omnibus\)"
)
NON_FORMATS = ("Manga", "Novel")
FORMATS = ("Light Novel", "Reference Guide")
DATES = (r"%b %d, %Y", r"%Y-%m-%d", r"%B %d, %Y", r"%Y/%m/%d")
RECENT_MODIFIED_DAYS = 30
ACTIVE_RELEASE_PAST_DAYS = 60
OLD_API_REFRESH_RATE = 0.1
OLD_LIST_REFRESH_RATE = 0.2


def strpdate(s: str) -> datetime.date:
    for d in DATES:
        try:
            return datetime.datetime.strptime(s, d).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid time data '{s}'")


def should_refresh_series(
    previous: set[Info], modified: datetime.date, today: datetime.date
) -> tuple[bool, int]:
    if modified == datetime.date(1, 1, 1):
        if not previous:
            return True, 4

        old = (today - max(i.date for i in previous)).days > 365
        if old:
            return random() <= OLD_LIST_REFRESH_RATE, 10
        return True, 4

    days = (today - modified).days
    if days < 2:
        return True, 0
    if days < RECENT_MODIFIED_DAYS:
        return True, 4

    if previous and max(i.date for i in previous) >= today - datetime.timedelta(
        days=ACTIVE_RELEASE_PAST_DAYS
    ):
        return True, 10

    return random() <= OLD_API_REFRESH_RATE, 10


def parse(session: Session, link: str, series: Series, refresh: int) -> set[Info]:
    info = set()
    page = session.get(link, cf=True, ia=True, refresh=refresh, headers=CHROME)
    if not page:
        return info
    soup = BeautifulSoup(page.content, "lxml")
    audio = False
    index = 0
    for release in soup.find_all(class_="series-volume"):
        index += 1
        header_elem = release.find_previous("h3", class_="header")
        if not header_elem or not header_elem.text:
            continue
        header = header_elem.text
        h3 = release.find("h3")
        if not h3 or not h3.text:
            continue
        title = h3.text
        if " (Light Novel)" in title:
            pass
        else:
            format_elem = None
            for b_tag in release.find_all("b"):
                if b_tag.string == "Format:":
                    format_elem = b_tag
                    break
            if format_elem:
                if not format_elem.next_sibling:
                    continue
                format = str(format_elem.next_sibling).strip()
                if format in NON_FORMATS:
                    continue
                if format not in FORMATS:
                    warnings.warn(f"Unknown SS format: {format}", RuntimeWarning, stacklevel=2)
                    continue
        if not audio and header == "AUDIOBOOKS":
            if not info:
                break
            audio = True
            index = 1

        href = release.get("href")
        if not href or not isinstance(href, str):
            a_tag = release.find("a")
            if not a_tag:
                continue
            href_attr = a_tag.get("href")
            if not href_attr or not isinstance(href_attr, str):
                continue
            volume_link: str = href_attr
        else:
            volume_link = href
        date = None
        for b_tag in release.find_all("b"):
            if b_tag.string == "Release Date":
                date = b_tag
                break
        if not date or not date.next_sibling:
            continue
        physical_date = strpdate(str(date.next_sibling).strip(" \t\n\r\v\f:"))
        digital_date = None
        early_digital_elem = None
        for b_tag in release.find_all("b"):
            if b_tag.string == "Early Digital:":
                early_digital_elem = b_tag
                break
        if early_digital_elem and early_digital_elem.next_sibling:
            digital_date = strpdate(str(early_digital_elem.next_sibling).strip())
        isbn = ""
        format = "Physical" if header == "VOLUMES" else "Audiobook"
        if header == "VOLUMES":
            isbn_tag = None
            for b_tag in release.find_all("b"):
                if b_tag.string == "ISBN:":
                    isbn_tag = b_tag
                    break
            if isbn_tag and isbn_tag.next_sibling:
                isbn = str(isbn_tag.next_sibling).strip()
            if not isbn or "digital" in isbn:
                digital_date = physical_date
                physical_date = None
                isbn = ""
            elif match := OMNIBUS.fullmatch(title):
                title = f"{match.group('name')} Vol. {match.group('volume')}"
                format = match.group("format") or "Physical"
                digital_date = None

        if physical_date:
            info.add(
                Info(
                    series.key,
                    volume_link,
                    NAME,
                    NAME,
                    title,
                    index,
                    format,
                    isbn,
                    physical_date,
                )
            )
        if digital_date:
            info.add(
                Info(
                    series.key,
                    volume_link,
                    NAME,
                    NAME,
                    title,
                    index,
                    "Digital",
                    "",
                    digital_date,
                )
            )
    return info


def scrape_full(series: set[Series], info: set[Info]) -> tuple[set[Series], set[Info]]:
    with Session() as session:
        links: dict[str, tuple[str, datetime.date]] = {}
        kwargs = {
            "cf": True,
            "ia": True,
            "refresh": 0,
            "headers": CHROME,
        }
        url = "https://sevenseasentertainment.com/wp-json/wp/v2/series"
        params = {
            "tags[0]": 43,
            "orderby": "modified",
            "per_page": 100,
            "page": 1,
        }
        while True:
            page = session.get(url, params=params, **kwargs)
            if not page:
                break
            jsn = page.json()
            for serie in jsn:
                link = serie["link"]
                title = unescape(serie["title"]["rendered"])
                modified = datetime.date.fromisoformat(serie["modified_gmt"][:10])
                links.setdefault(link, (title, modified))
            if len(jsn) != params["per_page"]:
                break
            params["page"] = str(int(params["page"]) + 1)

        page = session.get("https://sevenseasentertainment.com/series-list/", **kwargs)
        if not page:
            return series, info
        soup = BeautifulSoup(page.content, "lxml")
        lst = soup.select("tr#volumes > td:first-child > a")
        if not lst:
            warnings.warn(f"No series found: {page.url}", RuntimeWarning, stacklevel=2)
        for a in lst:
            href = a.get("href")
            if not href or not isinstance(href, str):
                continue
            link = href
            if link.endswith("-light-novel/"):
                text = a.text if a.text else ""
                if link not in links:
                    links[link] = (text, datetime.date(1, 1, 1))

        today = datetime.date.today()
        for link, (title, modified) in links.items():
            try:
                serie = Series("", title)
                prev = {i for i in info if i.serieskey == serie.key}
                should_refresh, refresh = should_refresh_series(prev, modified, today)
                if not should_refresh:
                    continue

                if inf := parse(session, link, serie, refresh):
                    series.add(serie)
                    isbns = {i.isbn for i in inf if i.isbn}
                    info -= {i for i in info if i in inf or i.isbn in isbns}
                    info |= inf
            except Exception as e:
                warnings.warn(f"({link}): {e}", RuntimeWarning, stacklevel=2)
    return series, info
