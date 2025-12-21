import importlib
import os
import warnings
from collections import defaultdict
from concurrent.futures import Future, as_completed
from faulthandler import dump_traceback
from pathlib import Path
from threading import Thread
from time import time

from lnrelease.utils import SOURCES, Info, Series, Table

ROOT = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR = Path(__file__).parent / "source"
MODULES = [
    importlib.import_module(f"lnrelease.source.{s.stem}")
    for s in SOURCE_DIR.glob("*.py")
    if s.stem != "__init__"
]

SERIES = DATA_DIR / "series.csv"
INFO = DATA_DIR / "info.csv"


def worker(future: Future, fn, *args) -> None:
    try:
        result = fn(*args)
    except BaseException as exc:
        future.set_exception(exc)
    else:
        future.set_result(result)


def main() -> None:
    series = Table(SERIES, Series)
    info = Table(INFO, Info)
    sources: defaultdict[str, set[Info]] = defaultdict(set)
    for inf in info:
        if isinstance(inf, Info):
            sources[inf.source].add(inf)

    start = time()
    futures: dict[Future[tuple[set[Series], set[Info]]], str] = {}
    for module in MODULES:
        future = Future()
        name: str = module.NAME
        futures[future] = name
        Thread(
            target=worker,
            name=f"Thread-{name.replace(' ', '-')}",
            args=(future, module.scrape_full, series.copy(), sources[name].copy()),
            daemon=True,
        ).start()

    try:
        for future in as_completed(futures, timeout=60 * 60 * 4):
            try:
                serie, inf = future.result()
                series |= serie
                series.save()
                info -= sources[futures[future]]
                info |= inf
                info.save()
                sources[futures[future]] = inf
            except Exception as e:
                warnings.warn(f"Error scraping {futures[future]}: {e}", RuntimeWarning)
            else:
                print(f"{futures[future]} done ({time() - start:.2f}s)", flush=True)
    except TimeoutError:
        dump_traceback()

    print("\nStats:")
    from lnrelease.session import REQUEST_STATS

    for netloc, stats in REQUEST_STATS.items():
        print(f"{netloc:>50s}: {stats}")

    series -= series - {Series(i.serieskey, "") for i in info if isinstance(i, Info)}
    series.save()
    info.clear()
    for _, inf in sorted(sources.items(), key=lambda x: SOURCES[x[0]]):
        info_set = {i for i in info if isinstance(i, Info)}
        info.update(inf - info_set)
    info.save()


if __name__ == "__main__":
    main()
