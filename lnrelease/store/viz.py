from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from lnrelease.session import Session

NAME = "VIZ Media"
SALT = hash(NAME)

PATH = re.compile(r"/manga-books/novel/(?P<name>[\w-]+)/product/(?P<id>\d+)/(?P<format>\w+)")


def equal(a: str, b: str) -> bool:
    match_a = PATH.fullmatch(urlparse(a).path)
    match_b = PATH.fullmatch(urlparse(b).path)
    if match_a and match_b:
        return match_a.group("id") == match_b.group("id") and match_a.group(
            "format"
        ) == match_b.group("format")
    return False


def hash_link(link: str) -> int:
    match = PATH.fullmatch(urlparse(link).path)
    if match:
        return SALT + hash(match.group("id") + match.group("format"))
    return SALT + hash(link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if not PATH.fullmatch(u.path):
        return None
    return urlunparse(("https", "www.viz.com", u.path, "", "", ""))
