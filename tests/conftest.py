import pytest
import datetime
from pathlib import Path


@pytest.fixture
def temp_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_release_date():
    return datetime.date(2024, 12, 25)


@pytest.fixture
def sample_series():
    from lnrelease.utils import Series

    return Series(key="testreeries", title="Test Series")


@pytest.fixture
def sample_info():
    from lnrelease.utils import Info

    return Info(
        serieskey="testseries",
        link="https://example.com/book/1",
        source="Test Source",
        publisher="Test Publisher",
        title="Test Series Volume 1",
        index=1,
        format="Digital",
        isbn="9781234567890",
        date=datetime.date(2024, 12, 25),
    )
