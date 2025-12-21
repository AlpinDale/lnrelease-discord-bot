from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from lnrelease.session import Session

NAME = "BOOK☆WALKER"
SALT = hash(NAME)

PATH = re.compile(r"(?P<path>/[a-f\d]{10}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12})(?:/.*)?")


def equal(a: str, b: str) -> bool:
    match_a = PATH.fullmatch(urlparse(a).path)
    match_b = PATH.fullmatch(urlparse(b).path)
    if match_a and match_b:
        return match_a.group("path") == match_b.group("path")
    return False


def hash_link(link: str) -> int:
    match = PATH.fullmatch(urlparse(link).path)
    if match:
        return SALT + hash(match.group("path"))
    return SALT + hash(link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if match := PATH.fullmatch(u.path):
        path = match.group("path") + "/"
    else:
        return None
    return urlunparse(("https", u.netloc, path, "", "", ""))
