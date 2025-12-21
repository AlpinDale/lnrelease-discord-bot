from __future__ import annotations

import datetime
import json
import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from lnrelease import utils
from lnrelease.session import CHROME, Session

NAME = "Kobo"
SALT = hash(NAME)

PATH = re.compile(r"(?:/\w+/\w+)?/(?P<format>ebook|audiobook)/(?P<name>[^/]+)(?:/.*)?")
INDEX = re.compile(r"Book (?P<index>\d+) - ")


def equal(a: str, b: str) -> bool:
    match_a = PATH.fullmatch(urlparse(a).path)
    match_b = PATH.fullmatch(urlparse(b).path)
    if match_a and match_b:
        return match_a.group("format") == match_b.group("format") and match_a.group(
            "name"
        ) == match_b.group("name")
    return False


def hash_link(link: str) -> int:
    match = PATH.fullmatch(urlparse(link).path)
    if match:
        return SALT + hash(match.group("format") + match.group("name"))
    return SALT + hash(link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if match := PATH.fullmatch(u.path):
        path = f"/ww/en/{match.group('format')}/{match.group('name')}"
    else:
        return None
    return urlunparse(("https", "www.kobo.com", path, "", "", ""))


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
    page = session.get(links[0], cf=True, ia=True, headers=CHROME, timeout=10)
    if not page:
        return None
    soup = BeautifulSoup(page.content, "lxml")

    about = soup.select_one("div.about > p.series > span.series")
    if not about:
        return None
    prefix = about.find("span", class_="sequenced-name-prefix")
    if prefix and prefix.text:
        match = INDEX.fullmatch(prefix.text)
        if match:
            index = int(match.group("index"))
    a_tag = about.find("a")
    if a_tag and a_tag.text:
        series = series or utils.Series("", a_tag.text)

    gizmo = soup.select_one("div.RatingAndReviewWidget > div.kobo-gizmo")
    if not gizmo:
        return None
    gizmo_config = gizmo.get("data-kobo-gizmo-config")
    if not gizmo_config or not isinstance(gizmo_config, str):
        return None
    jsn = json.loads(gizmo_config)
    jsn = json.loads(jsn["googleBook"])
    publisher = publisher or jsn["publisher"]["name"]
    work = jsn["workExample"]
    title = title or work["name"]
    format = format or work["@type"]
    if format == "Book":
        format = "Digital"
    isbn = isbn or work.get("isbn", "")
    date = datetime.date.fromisoformat(work["datePublished"][:10])

    if not series:
        series = utils.Series("", "")
    info = utils.Info(series.key, links[0], NAME, publisher, title, index, format, isbn, date)
    return series, {info}
