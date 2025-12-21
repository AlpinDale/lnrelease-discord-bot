import datetime
import re
import warnings
from pathlib import Path
from random import random
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lnrelease.session import Session
from lnrelease.utils import Info, Key, Series, Table

NAME = "VIZ Media"

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PAGES = DATA_DIR / "viz.csv"
ISBN = re.compile(r"e?ISBN-13")


def parse(session: Session, link: str) -> tuple[Series, set[Info], datetime.date] | None:
    info = set()
    page = session.get(link, cf=True, ia=True)
    if not page:
        return None
    soup = BeautifulSoup(page.content, "lxml")
    product = soup.find(id="product_row")
    if not product:
        return None

    series_elem = product.find("strong", string="Series")
    if not series_elem:
        return None
    series_sibling = series_elem.find_next_sibling(class_="color-red")
    if not series_sibling or not series_sibling.text:
        return None
    series_title = series_sibling.text
    title_elem = product.select_one("div#purchase_links_block h2")
    if not title_elem or not title_elem.text:
        return None
    title = title_elem.text
    index = 0
    isbn_elem = product.find("strong", string=ISBN)
    if not isbn_elem or not isbn_elem.next_sibling:
        return None
    isbn = str(isbn_elem.next_sibling).strip()
    date_elem = product.find("strong", string="Release")
    if not date_elem or not date_elem.next_sibling:
        return None
    date = str(date_elem.next_sibling).strip()
    date = datetime.datetime.strptime(date, "%B %d, %Y").date()

    series = Series("", series_title)
    tablist = product.find(role="tablist")
    if not tablist:
        return series, info, date
    for a in tablist.find_all("a"):
        format = a.text
        url = f"{link}/{format.lower()}"
        i = isbn if a.get("data-tab-state") == "on" else ""
        info.add(Info(series.key, url, NAME, NAME, title, index, format, i, date))
    return series, info, date


def scrape_full(
    series: set[Series], info: set[Info], limit: int = 1000
) -> tuple[set[Series], set[Info]]:
    pages = Table(PAGES, Key)
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=365)
    # no date = not light novel
    skip = {
        row.key
        for row in pages
        if isinstance(row, Key) and random() > 0.2 and (not row.date or row.date < cutoff)
    }

    with Session() as session:
        site = "https://www.viz.com/search/{}?search=Novel&category=Novel"
        for i in range(1, limit + 1):
            page = session.get(site.format(i))
            if not page:
                break
            soup = BeautifulSoup(page.content, "lxml")

            results = soup.select("div#results > article > div > a")
            for a in results:
                href = a.get("href")
                if not href or not isinstance(href, str):
                    continue
                link = urljoin("https://www.viz.com/", href)
                if link in skip:
                    continue

                try:
                    res = parse(session, link)
                    if res:
                        series.add(res[0])
                        info -= res[1]
                        info |= res[1]
                        date = res[2]
                    else:
                        date = datetime.date.today()
                    key = Key(link, date)
                    pages.discard(key)
                    pages.add(key)
                except Exception as e:
                    warnings.warn(f"({link}): {e}", RuntimeWarning, stacklevel=2)

            if not results:
                break
    pages.save()
    return series, info


def scrape(series: set[Series], info: set[Info]) -> tuple[set[Series], set[Info]]:
    return scrape_full(series, info, 5)
