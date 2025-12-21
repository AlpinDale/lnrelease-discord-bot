from __future__ import annotations

import datetime
import json
import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from lnrelease import utils
from lnrelease.session import Session

NAME = "Audible"
SALT = hash(NAME)

PARAMS = {"overrideBaseCountry": "true", "ipRedirectOverride": "true"}
PATH = re.compile(r"/pd/(?P<name>[^/]+)/(?P<asin>\w{10})(?:/.*)?")
SERIES = re.compile(r'"series":')
BOOK = re.compile(r"Book (?P<index>\d+)")


def equal(a: str, b: str) -> bool:
    ua = urlparse(a)
    ub = urlparse(b)
    if ua.netloc.removeprefix("www.") != ub.netloc.removeprefix("www."):
        return False

    match_a = PATH.fullmatch(ua.path)
    match_b = PATH.fullmatch(ub.path)
    if match_a and match_b:
        return match_a.group("asin") == match_b.group("asin")
    return False


def hash_link(link: str) -> int:
    u = urlparse(link)
    netloc = u.netloc.removeprefix("www.")
    match = PATH.fullmatch(u.path)
    if match:
        asin = match.group("asin")
        return SALT + hash(netloc + asin)
    return SALT + hash(netloc + link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if match := PATH.fullmatch(u.path):
        path = f"/pd/{match.group('name')}/{match.group('asin')}"
    else:
        return None
    netloc = u.netloc
    if not netloc.startswith("www."):
        if netloc.startswith("audible."):
            netloc = f"www.{netloc}"
        else:
            return None
    return urlunparse(("https", netloc, path, "", "", ""))


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
    page = session.get(links[0], cf=True, ia=True, params=PARAMS)
    if not page:
        return None
    soup = BeautifulSoup(page.content, "lxml")

    script = soup.select_one('#bottom-0 script[type="application/ld+json"]')
    if not script:
        return None
    jsn = json.loads(script.text)[0]
    publisher = publisher or jsn["publisher"]

    title = title or jsn["name"]
    format = format or "Audiobook"
    isbn = isbn or jsn.get("isbn", "")
    date = datetime.date.fromisoformat(jsn["datePublished"])

    series_title = title
    metadata = None
    for script in soup.find_all("script", type="application/json"):
        if script.string and SERIES.search(script.string):
            metadata = script
            break
    if metadata:
        data = json.loads(metadata.text)["series"][0]
        if not index and (match := BOOK.fullmatch(data["part"])):
            index = int(match.group("index"))
        series_title = data["name"]

    series = series or utils.Series("", series_title)
    info = utils.Info(series.key, links[0], NAME, publisher, title, index, format, isbn, date)
    return series, {info}
