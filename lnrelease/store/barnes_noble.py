from __future__ import annotations

import datetime
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from lnrelease import utils
from lnrelease.session import CHROME, Session

NAME = "Barnes & Noble"
SALT = hash(NAME)

PATH = re.compile(r"/w/(?P<name>[\w-]+)/(?P<id>\d+)")
PUBLISHER = re.compile(r"^\s*Publisher:\s*(?P<name>.+)$")
DATE = re.compile(r"^\s*Pub\. Date:\s*(?P<date>.+)$")

FORMATS = "https://www.barnesandnoble.com/cartridges/ProductDetailContent/ProductDetailTypes/includes/formatModal-ra.jsp"


def equal(a: str, b: str) -> bool:
    ua = urlparse(a)
    ub = urlparse(b)
    match_a = PATH.fullmatch(ua.path)
    match_b = PATH.fullmatch(ub.path)
    ean_a = next((v for k, v in parse_qsl(ua.query) if k == "ean"), "")
    ean_b = next((v for k, v in parse_qsl(ub.query) if k == "ean"), "")

    if ean_a and ean_b and ean_a == ean_b:
        return True
    if match_a and match_b and match_a.group("id") == match_b.group("id") and not (ean_a and ean_b):
        return True
    return False


def hash_link(link: str) -> int:
    u = urlparse(link)
    ean = next((v for k, v in parse_qsl(u.query) if k == "ean"), "")
    match = PATH.fullmatch(u.path)
    if match:
        return SALT + hash(ean or match.group("id"))
    return SALT + hash(ean or link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    query = urlencode([(k, v) for k, v in parse_qsl(u.query) if k == "ean"])
    if not PATH.fullmatch(u.path):
        res = session.resolve(link, force=True, headers=CHROME)
        if res != link:
            return normalise(session, res)
        if query and u.path.startswith("/w"):
            return urlunparse(("https", "www.barnesandnoble.com", "/w", "", query, ""))
        return None
    return urlunparse(("https", "www.barnesandnoble.com", u.path, "", query, ""))


def parse(
    session: Session,
    links: list[str],
    *,
    series: utils.Series | None = None,
    publisher: str = "",
    title: str = "",
    index: int = 0,
    format: str = "",
    isbn: str = "",
) -> tuple[utils.Series, set[utils.Info]] | None:
    u = urlparse(links[0])
    match = PATH.fullmatch(u.path)
    if not match:
        return None
    ean = next((v for k, v in parse_qsl(u.query) if k == "ean"), "")
    id = match.group("id")
    page = session.get(FORMATS, params={"workId": id}, headers=CHROME)
    if not page:
        return None
    soup = BeautifulSoup(page.content, "lxml")

    if not series:
        series = utils.Series("", "")
    serieskey = series.key
    if h3 := soup.find("h3", class_="all-formats-text"):
        title = h3.text
    info = set()
    found = False
    for li in soup.select('div[role="tablist"] > ul > li'):
        a_tag = li.find("a")
        if not a_tag:
            continue
        href = a_tag.get("href")
        if not href or not isinstance(href, str):
            continue
        link = urljoin("https://www.barnesandnoble.com/", href)
        found |= ean == next((v for k, v in parse_qsl(urlparse(link).query) if k == "ean"), "")
        parent = li.parent
        if not parent:
            continue
        format_attr = parent.get("data-format-type")
        if not format_attr or not isinstance(format_attr, str):
            continue
        format = format_attr
        pub_match = li.find(string=PUBLISHER)
        if pub_match:
            pub_match_obj = PUBLISHER.fullmatch(pub_match.text)
            if pub_match_obj:
                publisher = publisher or pub_match_obj.group("name")
        date_match = li.find(string=DATE)
        if not date_match:
            continue
        date_match_obj = DATE.fullmatch(date_match.text)
        if not date_match_obj:
            continue
        date = date_match_obj.group("date")
        date = datetime.datetime.strptime(date, "%m/%d/%Y").date()
        info.add(utils.Info(serieskey, link, NAME, publisher, title, index, format, isbn, date))

    if not found:
        link = session.resolve(links[0], force=True, headers=CHROME)
        if links[0] != link:
            res = parse(
                session,
                [link],
                series=series,
                publisher=publisher,
                title=title,
                index=index,
                format=format,
            )
            if res:
                info |= res[1]

    return series, info
