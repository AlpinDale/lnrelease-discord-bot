import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from lnrelease.scrape import DATA_DIR
from lnrelease.utils import Book, Series, Table, clean_str


def volume_key(volume: str) -> tuple[float, str]:
    try:
        num = float(volume.split("-")[0].split(".")[0])
        return (num, volume)
    except ValueError:
        return (float("inf"), volume)


BOOKS_CSV = DATA_DIR / "books.csv"
SERIES_CSV = DATA_DIR / "series.csv"

VOLUME_PATTERN = re.compile(r"(?:vol\.?|volume|v\.?|#)\s*(\d+(?:\.\d+)?(?:-\d+)?)", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(\d+(?:\.\d+)?(?:-\d+)?)")


@dataclass
class SearchResult:
    series: Series
    books: list[Book]
    confidence: float
    match_type: str


def normalize_volume(volume: str) -> str:
    volume = volume.strip()
    if not volume:
        return ""

    if match := VOLUME_PATTERN.search(volume):
        return match.group(1)

    if match := NUMBER_PATTERN.search(volume):
        return match.group(1)

    volume_lower = volume.lower()
    if "special" in volume_lower or "sp" in volume_lower:
        return "special"
    if "omnibus" in volume_lower:
        if match := NUMBER_PATTERN.search(volume):
            return f"omnibus-{match.group(1)}"
        return "omnibus"

    return volume.lower()


def volume_matches(query_vol: str, book_vol: str, threshold: float = 0.8) -> bool:
    if not query_vol:
        return True

    query_norm = normalize_volume(query_vol)
    book_norm = normalize_volume(book_vol)

    if query_norm == book_norm:
        return True

    if not query_norm or not book_norm:
        ratio = fuzz.ratio(query_vol.lower(), book_vol.lower()) / 100.0
        return ratio >= threshold

    if query_norm.isdigit() and book_norm.isdigit():
        return query_norm == book_norm

    ratio = fuzz.ratio(query_norm, book_norm) / 100.0
    return ratio >= threshold


class SeriesSearcher:
    def __init__(self):
        self._series_cache: dict[str, Series] | None = None
        self._books_cache: list[Book] | None = None
        self._series_keys_cache: list[str] | None = None

    def _load_series(self) -> dict[str, Series]:
        if self._series_cache is None:
            series_table = Table(SERIES_CSV, Series)
            self._series_cache = {s.key: s for s in series_table if isinstance(s, Series)}
        return self._series_cache

    def _load_books(self) -> list[Book]:
        if self._books_cache is None:
            books_table = Table(BOOKS_CSV, Book)
            self._books_cache = [b for b in books_table if isinstance(b, Book)]
        return self._books_cache

    def _get_series_keys(self) -> list[str]:
        if self._series_keys_cache is None:
            series = self._load_series()
            self._series_keys_cache = list(series.keys())
        return self._series_keys_cache

    def search(self, query: str, volume: str | None = None, limit: int = 5) -> list[SearchResult]:
        query_clean = clean_str(query)
        series = self._load_series()
        books = self._load_books()
        series_keys = self._get_series_keys()

        if not query_clean:
            return []

        results: list[SearchResult] = []

        exact_match = series.get(query_clean)
        if exact_match:
            matched_books = [b for b in books if b.serieskey == exact_match.key]
            if volume:
                matched_books = [b for b in matched_books if volume_matches(volume, b.volume)]

            if matched_books:
                results.append(
                    SearchResult(
                        series=exact_match,
                        books=sorted(matched_books, key=lambda x: (x.format, volume_key(x.volume))),
                        confidence=1.0,
                        match_type="exact",
                    )
                )
                if len(results) >= limit:
                    return results[:limit]

        prefix_matches: list[tuple[str, Series]] = []
        for key, s in series.items():
            if key.startswith(query_clean) or query_clean.startswith(key):
                prefix_matches.append((key, s))

        if prefix_matches:
            prefix_matches.sort(key=lambda x: len(x[0]), reverse=True)
            for key, s in prefix_matches[: limit - len(results)]:
                matched_books = [b for b in books if b.serieskey == key]
                if volume:
                    matched_books = [b for b in matched_books if volume_matches(volume, b.volume)]

                if matched_books:
                    confidence = len(query_clean) / len(key) if key else 0.5
                    results.append(
                        SearchResult(
                            series=s,
                            books=sorted(
                                matched_books, key=lambda x: (x.format, volume_key(x.volume))
                            ),
                            confidence=min(confidence, 0.95),
                            match_type="prefix",
                        )
                    )
                    if len(results) >= limit:
                        return results[:limit]

        fuzzy_results = process.extract(
            query_clean,
            series_keys,
            scorer=fuzz.ratio,
            limit=limit - len(results),
            score_cutoff=60,
        )

        results_dict = {r.series.key for r in results}
        for key, score, _ in fuzzy_results:
            if key in results_dict:
                continue

            s = series[key]
            matched_books = [b for b in books if b.serieskey == key]
            if volume:
                matched_books = [b for b in matched_books if volume_matches(volume, b.volume)]

            if matched_books:
                confidence = score / 100.0
                results.append(
                    SearchResult(
                        series=s,
                        books=sorted(matched_books, key=lambda x: (x.format, volume_key(x.volume))),
                        confidence=confidence,
                        match_type="fuzzy",
                    )
                )
                if len(results) >= limit:
                    break

        if not results and query:
            title_results = process.extract(
                query,
                [s.title for s in series.values()],
                scorer=fuzz.partial_ratio,
                limit=limit,
                score_cutoff=50,
            )

            for title, score, _ in title_results:
                for s in series.values():
                    if s.title == title:
                        matched_books = [b for b in books if b.serieskey == s.key]
                        if volume:
                            matched_books = [
                                b for b in matched_books if volume_matches(volume, b.volume)
                            ]

                        if matched_books:
                            confidence = score / 100.0
                            results.append(
                                SearchResult(
                                    series=s,
                                    books=sorted(
                                        matched_books,
                                        key=lambda x: (x.format, volume_key(x.volume)),
                                    ),
                                    confidence=confidence,
                                    match_type="partial",
                                )
                            )
                            if len(results) >= limit:
                                break
                        break
                if len(results) >= limit:
                    break

        return results[:limit]


searcher = SeriesSearcher()
