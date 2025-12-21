from __future__ import annotations

import datetime
import json
import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from lnrelease import utils
from lnrelease.session import Session

NAME = "Apple"
SALT = hash(NAME)

PATH = re.compile(r"/(?P<country>\w+)/(?P<format>book|audiobook)/(?:[\w%-]+/)?(?P<id>id\d{10})")


def equal(a: str, b: str) -> bool:
    match_a = PATH.fullmatch(urlparse(a).path)
    match_b = PATH.fullmatch(urlparse(b).path)
    if match_a and match_b:
        return match_a.group("id") == match_b.group("id")
    return False


def hash_link(link: str) -> int:
    match = PATH.fullmatch(urlparse(link).path)
    if match:
        return SALT + hash(match.group("id"))
    return SALT + hash(link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if match := PATH.fullmatch(u.path):
        path = f"/us/{match.group('format')}/{match.group('id')}"
    else:
        return None
    return urlunparse(("https", "books.apple.com", path, "", "", ""))


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
    page = session.get(links[0], cf=True, ia=True)
    if not page or page.status_code == 404:
        return None
    soup = BeautifulSoup(page.content, "lxml")

    serieskey = series.key if series else ""
    script = soup.find("script", type="application/ld+json")
    if not script or not script.text:
        return None
    jsn = json.loads(script.text)
    publisher = publisher or jsn["publisher"]
    title = title or jsn["name"]
    format = format or jsn["@type"]
    if format == "Book":
        format = "Digital"
    isbn = isbn or jsn.get("isbn", "")
    date = datetime.date.fromisoformat(jsn["datePublished"][:10])

    info = utils.Info(serieskey, links[0], NAME, publisher, title, index, format, isbn, date)
    if not series:
        series = utils.Series("", "")
    return series, {info}
