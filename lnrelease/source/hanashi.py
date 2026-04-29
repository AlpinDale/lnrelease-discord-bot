import datetime
import re
import warnings
from pathlib import Path
from random import random
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from lnrelease import store
from lnrelease.session import CHROME, Session
from lnrelease.utils import Info, Key, Series, Table

NAME = "Hanashi Media"

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PAGES = DATA_DIR / "hanashi.csv"
LINK = re.compile(r"/light-novels/[\w-]+")
IA = re.compile(r"https?://web\.archive\.org/web/\d+/(?P<url>https?://.+)")
IA_PARTS = re.compile(r"(?P<prefix>https?://web\.archive\.org/web/\d+)/(?P<url>https?://.+)")
VOLUME_LIST = re.compile(r"Volume:\[(?P<volumes>.*?)\],wings", flags=re.DOTALL)
VOLUME = re.compile(r"number:(?P<number>\d+(?:\.\d+)?)")
VOLUME_DATA = re.compile(
    r"volume:\{(?P<data>.*?)\}\},uses:\{params:\[\"id\",\"volume\"\]\}",
    flags=re.DOTALL,
)
RELEASE = re.compile(r"release:new Date\((?P<timestamp>\d+)\)")
STORE_LINK = re.compile(
    r"(?P<store>amazon|apple|barnes|google|hanashi|kobo):\"(?P<link>https?://[^\"]+)\""
)


def remove_archive(link: str) -> str:
    if match := IA.fullmatch(link):
        return match.group("url")
    return link


def volume_path(volume: float) -> str:
    return str(int(volume)) if volume.is_integer() else str(volume)


def parse_volume_numbers(script: str) -> list[float]:
    volumes_match = VOLUME_LIST.search(script)
    if not volumes_match:
        return []
    return [
        float(match.group("number")) for match in VOLUME.finditer(volumes_match.group("volumes"))
    ]


def parse_embedded_volume(script: str) -> tuple[str, datetime.date, list[str]]:
    volume_match = VOLUME_DATA.search(script)
    if not volume_match:
        raise ValueError("Could not parse embedded volume data")
    data = volume_match.group("data")

    number_match = VOLUME.search(data)
    release_match = RELEASE.search(data)
    if not number_match or not release_match:
        raise ValueError("Could not parse volume metadata")

    date = datetime.datetime.fromtimestamp(
        int(release_match.group("timestamp")) / 1000, tz=datetime.timezone.utc
    ).date()
    links = [remove_archive(match.group("link")) for match in STORE_LINK.finditer(data)]
    return number_match.group("number"), date, links


def read(
    session: Session,
    jsn: dict,
    series: Series,
    link: str,
    volumes: dict[float, int],
    skip: set[str],
) -> tuple[int, set[Info]]:
    info = set()
    data = jsn["nodes"][2]["data"]
    vol = data[data[1]["number"]]
    title = f"{series.title} Volume {vol}"
    index = volumes.pop(vol, 0)
    date = datetime.date.fromisoformat(data[data[1]["release"]][1][:10])

    urls = []
    for url in data:
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        url = session.resolve(url)
        if norm := store.normalise(session, url, resolve=True):
            urls.append([norm, url])
        elif norm is None:
            warnings.warn(f"{url} normalise failed", RuntimeWarning, stacklevel=2)

    alts = []
    force = True
    urls.sort(key=lambda x: ".amazon" in x[0])
    for norm, url in urls:
        if urlparse(norm).netloc in store.PROCESSED:
            alts.append(norm)
            continue
        res = store.parse(
            session,
            [norm, url],
            (force or random() < 0.1) and norm not in skip,
            series=series,
            publisher=NAME,
            title=title,
            index=index,
            format="Digital",
        )
        if res and res[1]:
            info |= res[1]
            force = False
            alts.extend(inf.link for inf in res[1])
        else:
            alts.append(norm)

    info.add(Info(series.key, link, NAME, NAME, title, 0, "Digital", "", date, alts))
    return vol, info


def read_html(
    session: Session,
    series: Series,
    link: str,
    index: int,
    skip: set[str],
    archive_prefix: str = "",
) -> tuple[float, set[Info]]:
    direct_link = remove_archive(link)
    page = None
    if archive_prefix:
        page = session.try_get(f"{archive_prefix}/{direct_link}", retries=2, headers=CHROME)
    if not page:
        page = session.get(direct_link, cf=True, ia=True, refresh=4, headers=CHROME)
    if not page:
        raise ValueError(f"Failed to fetch {direct_link}")

    soup = BeautifulSoup(page.content, "lxml")
    script = next(
        (
            script.get_text()
            for script in soup.find_all("script")
            if "volume:{" in script.get_text()
        ),
        "",
    )
    if not script:
        raise ValueError(f"Could not find embedded volume data in {direct_link}")

    try:
        number, date, store_links = parse_embedded_volume(script)
    except ValueError:
        raise ValueError(f"Could not parse volume metadata in {direct_link}") from None
    vol = float(number)
    title = f"{series.title} Volume {number}"

    urls = []
    for url in store_links:
        url = session.resolve(url)
        if norm := store.normalise(session, url, resolve=True):
            urls.append([remove_archive(norm), url])
        elif norm is None:
            warnings.warn(f"{url} normalise failed", RuntimeWarning, stacklevel=2)

    info = set()
    alts = []
    force = True
    urls.sort(key=lambda x: ".amazon" in x[0])
    for norm, url in urls:
        if urlparse(norm).netloc in store.PROCESSED:
            alts.append(norm)
            continue
        res = store.parse(
            session,
            [norm, url],
            (force or random() < 0.1) and norm not in skip,
            series=series,
            publisher=NAME,
            title=title,
            index=index,
            format="Digital",
        )
        if res and res[1]:
            info |= res[1]
            force = False
            alts.extend(inf.link for inf in res[1])
        else:
            alts.append(norm)

    info.add(Info(series.key, direct_link, NAME, NAME, title, 0, "Digital", "", date, alts))
    return vol, info


def parse_html(session: Session, link: str, skip: set[str]) -> tuple[Series, set[Info]]:
    direct_link = remove_archive(link)
    page = session.get(direct_link, cf=True, ia=True, refresh=4, headers=CHROME)
    if not page:
        raise ValueError(f"Failed to fetch {direct_link}")

    soup = BeautifulSoup(page.content, "lxml")
    title_elem = soup.find("h1")
    if not title_elem or not title_elem.text:
        raise ValueError(f"Could not find series title in {direct_link}")
    series = Series("", title_elem.text)

    script = next(
        (
            script.get_text()
            for script in soup.find_all("script")
            if "Volume:[" in script.get_text()
        ),
        "",
    )
    volumes = parse_volume_numbers(script)
    if not volumes:
        raise ValueError(f"Could not parse volume list in {direct_link}")

    archive_prefix = ""
    if archive_match := IA_PARTS.fullmatch(str(page.url)):
        archive_prefix = archive_match.group("prefix")

    path = direct_link.rsplit("/", 1)[0]
    info = set()
    for index, volume in enumerate(volumes, start=1):
        try:
            volume_link = f"{path}/{volume_path(volume)}"
            info |= read_html(session, series, volume_link, index, skip, archive_prefix)[1]
        except Exception as e:
            warnings.warn(f"({direct_link} volume {volume:g}): {e}", RuntimeWarning, stacklevel=2)

    return series, info


def parse_json(session: Session, link: str, skip: set[str]) -> tuple[Series, set[Info]]:
    page = session.get(f"{link}/__data.json")
    if not page:
        raise ValueError(f"Failed to fetch {link}/__data.json")
    jsn = page.json()
    data = jsn["nodes"][1]["data"]
    series_title = data[data[1]["title"]]
    volumes = {data[data[x]["number"]]: i for i, x in enumerate(data[data[1]["Volume"]])}
    series = Series("", series_title)

    vol, info = read(session, jsn, series, link, volumes, skip)
    path = link.rsplit("/", 1)[0]
    for vol in list(volumes):
        try:
            page = session.get(f"{path}/{vol}/__data.json")
            if not page:
                continue
            info |= read(session, page.json(), series, f"{path}/{vol}", volumes, skip)[1]
        except Exception as e:
            warnings.warn(f"({link}): {e}", RuntimeWarning, stacklevel=2)

    return series, info


def parse(session: Session, link: str, skip: set[str]) -> tuple[Series, set[Info]]:
    direct_link = remove_archive(link)
    try:
        return parse_json(session, direct_link, skip)
    except Exception:
        pass
    return parse_html(session, direct_link, skip)


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
        page = session.get(
            "https://hanashi.media/light-novels", cf=True, ia=True, refresh=4, headers=CHROME
        )
        if not page:
            return series, info
        soup = BeautifulSoup(page.content, "lxml")
        links = [
            href
            for href in {a.get("href", "") for a in soup.select("a")}
            if href and isinstance(href, str) and LINK.search(href)
        ]
        for link in links:
            try:
                link_str = urljoin(str(page.url), link)
                s, inf = parse(session, link_str, skip)

                if inf:
                    series.add(s)
                    info -= {i for i in info if i.serieskey == s.key} | inf
                    info |= inf
                    for i in inf:
                        if i.source == NAME:
                            continue
                        key = Key(i.link, i.date)
                        pages.discard(key)
                        pages.add(key)
            except Exception as e:
                warnings.warn(f"({link}): {e}", RuntimeWarning, stacklevel=2)

    pages.save()
    return series, info
