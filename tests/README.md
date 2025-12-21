# Tests

Comprehensive test suite for the lnrelease Discord bot.

## Running Tests

Install dev dependencies:
```bash
pip install -e ".[dev]"
```

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=lnrelease --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_utils.py
```

Run specific test:
```bash
pytest tests/test_utils.py::TestFormat::test_is_digital
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_utils.py` - Tests for core utilities (Format, Series, Book, etc.)
- `test_store.py` - Tests for store URL normalization and equality
- `test_bot_storage.py` - Tests for SQLite database operations
- `test_bot_releases.py` - Tests for release filtering logic
- `test_publisher_parsing.py` - Tests for volume parsing heuristics

## Coverage Goals

- **Core utilities**: >90% coverage for pure functions
- **Store modules**: URL normalization/equality functions
- **Publisher parsing**: Regex matching and heuristics
- **Bot storage**: All database operations
- **Release filtering**: Digital-only filtering logic

## Note

Network-dependent tests (actual scrapers) are intentionally excluded from the main test suite. For scraper validation, use the manual scraping workflow or add fixture-based tests with `responses` library.

