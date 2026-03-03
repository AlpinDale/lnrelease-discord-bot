import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

VOLUME_PATTERN = re.compile(
    r"\b(?:vol\.?|volume|v\.?|#)\s*(\d+(?:\.\d+)?(?:-\d+)?)\b", re.IGNORECASE
)
NUMBER_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?(?:-\d+)?)\b")


@dataclass
class NyaaTorrent:
    id: str
    name: str
    magnet: str
    size: str
    category: str
    date: datetime | None
    seeders: int
    leechers: int
    downloads: int


def get_volume_search_variants(volume: str) -> list[str]:
    volume = volume.strip()
    if not volume:
        return []

    vol_num = None
    if match := VOLUME_PATTERN.search(volume):
        vol_num = match.group(1)
    elif match := NUMBER_PATTERN.search(volume):
        vol_num = match.group(1)

    if not vol_num:
        return [volume.lower()]

    variants = [
        f"volume {vol_num}",
        f"vol {vol_num}",
        f"vol. {vol_num}",
        f"v{vol_num}",
        f"v {vol_num}",
        f"#{vol_num}",
        vol_num,
    ]

    if vol_num.isdigit():
        variants.append(f"volume {int(vol_num):02d}")
        variants.append(f"vol {int(vol_num):02d}")

    return variants


def extract_volume_from_query(query: str) -> tuple[str, str | None]:
    match = VOLUME_PATTERN.search(query)
    if match:
        volume = match.group(1)
        query_without_volume = VOLUME_PATTERN.sub("", query).strip()
        return query_without_volume, volume

    match = NUMBER_PATTERN.search(query)
    if match and len(query.split()) <= 5:
        volume = match.group(1)
        query_without_volume = NUMBER_PATTERN.sub("", query, count=1).strip()
        if query_without_volume:
            return query_without_volume, volume

    return query, None


def search_nyaa_with_variants(
    series: str,
    volume: str | None = None,
    category: str = "3_1",
    page: int = 1,
    max_results: int = 10,
    filter_epub_only: bool = True,
) -> list[NyaaTorrent]:
    if not volume:
        results = search_nyaa(series, category=category, page=page, max_results=max_results * 3)
    else:
        variants = get_volume_search_variants(volume)
        all_results: list[NyaaTorrent] = []
        seen_ids: set[str] = set()

        for variant in variants:
            search_query = f"{series} {variant}".strip()
            variant_results = search_nyaa(
                search_query, category=category, page=page, max_results=max_results * 3
            )

            for torrent in variant_results:
                if torrent.id not in seen_ids:
                    seen_ids.add(torrent.id)
                    all_results.append(torrent)

            if len(all_results) >= max_results * 3:
                break

        results = all_results[: max_results * 3]

    if filter_epub_only:
        return filter_torrents_with_epub(results, max_results=max_results)

    return results[:max_results]


def get_torrent_file_list(torrent_id: str) -> list[str]:
    base_url = "https://nyaa.si"
    url = f"{base_url}/view/{torrent_id}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    file_list_elem = soup.select_one(".torrent-file-list")
    if not file_list_elem:
        return []

    files: list[str] = []
    for li in file_list_elem.find_all("li"):
        file_text = li.get_text(strip=True)
        if file_text:
            file_name = file_text.split("(")[0].strip()
            files.append(file_name)

    return files


def has_epub_files(torrent_id: str) -> bool:
    try:
        files = get_torrent_file_list(torrent_id)
        return any(file.lower().endswith(".epub") for file in files)
    except Exception:
        return False


def filter_torrents_with_epub(
    torrents: list[NyaaTorrent], max_results: int = 10
) -> list[NyaaTorrent]:
    epub_results: list[NyaaTorrent] = []
    for torrent in torrents:
        if has_epub_files(torrent.id):
            epub_results.append(torrent)
            if len(epub_results) >= max_results:
                break
    return epub_results


def search_nyaa(
    query: str, category: str = "3_1", page: int = 1, max_results: int = 10
) -> list[NyaaTorrent]:
    base_url = "https://nyaa.si"
    url = f"{base_url}/?q={quote(query)}&c={category}&f=0&p={page}&s=&o="

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    torrents: list[NyaaTorrent] = []
    for row in soup.select("tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 8:
            continue

        link_elem = cells[1].find("a")
        if not link_elem:
            continue

        href = link_elem.get("href", "")
        if "/view/" not in href:
            continue

        torrent_id = href.replace("/view/", "").split("?")[0]
        name = link_elem.get_text(strip=True)

        magnet_links = cells[2].find_all("a")
        magnet_href = magnet_links[1].get("href") if len(magnet_links) > 1 else None
        magnet = str(magnet_href) if magnet_href else ""

        size = cells[3].get_text(strip=True)
        category_elem = cells[0].find("a")
        category_name = category_elem.get("title", "") if category_elem else ""

        timestamp_attr = cells[4].get("data-timestamp")
        date = None
        if timestamp_attr:
            timestamp_str = (
                str(timestamp_attr) if not isinstance(timestamp_attr, str) else timestamp_attr
            )
            date = datetime.fromtimestamp(int(timestamp_str))

        seeders = int(cells[5].get_text(strip=True) or 0)
        leechers = int(cells[6].get_text(strip=True) or 0)
        downloads = int(cells[7].get_text(strip=True) or 0)

        torrents.append(
            NyaaTorrent(
                id=torrent_id,
                name=name,
                magnet=magnet,
                size=size,
                category=category_name,
                date=date,
                seeders=seeders,
                leechers=leechers,
                downloads=downloads,
            )
        )

        if len(torrents) >= max_results:
            break

    return torrents
