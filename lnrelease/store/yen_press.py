from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from lnrelease.session import Session

NAME = "Yen Press"
SALT = hash(NAME)

PATH = re.compile(r"/titles/(?P<isbn>\d{13})-(?P<name>[\w-]+)")


def equal(a: str, b: str) -> bool:
    match_a = PATH.fullmatch(urlparse(a).path)
    match_b = PATH.fullmatch(urlparse(b).path)
    if match_a and match_b:
        return match_a.group("isbn") == match_b.group("isbn")
    return False


def hash_link(link: str) -> int:
    match = PATH.fullmatch(urlparse(link).path)
    if match:
        return SALT + hash(match.group("isbn"))
    return SALT + hash(link)


def normalise(session: Session, link: str) -> str | None:
    u = urlparse(link)
    if not PATH.fullmatch(u.path):
        return None
    return urlunparse(("https", "yenpress.com", u.path, "", "", ""))
