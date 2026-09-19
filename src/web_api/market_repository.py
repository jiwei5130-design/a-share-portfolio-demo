"""Thread-safe access to the read-only P4 market intelligence service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.market_data.config import DATABASE_PATH
from src.market_intelligence import MarketOverviewService


@lru_cache(maxsize=1)
def get_market_service() -> MarketOverviewService:
    return MarketOverviewService()


def market_data_version() -> tuple[int, int, int, int]:
    """Return a cheap cache key that changes when SQLite or its WAL changes."""
    database = Path(DATABASE_PATH)
    wal = Path(f"{database}-wal")
    database_stat = database.stat()
    if wal.exists():
        wal_stat = wal.stat()
        return database_stat.st_mtime_ns, database_stat.st_size, wal_stat.st_mtime_ns, wal_stat.st_size
    return database_stat.st_mtime_ns, database_stat.st_size, 0, 0


@lru_cache(maxsize=64)
def _overview(date: str | None, _: tuple[int, int, int, int]) -> dict[str, object]:
    return get_market_service().overview(date)


@lru_cache(maxsize=64)
def _indices(date: str | None, lookback: int, _: tuple[int, int, int, int]) -> dict[str, object]:
    return get_market_service().indices(date, lookback)


@lru_cache(maxsize=64)
def _breadth(date: str | None, lookback: int, _: tuple[int, int, int, int]) -> dict[str, object]:
    return get_market_service().breadth(date, lookback)


@lru_cache(maxsize=64)
def _quality(date: str | None, _: tuple[int, int, int, int]) -> dict[str, object]:
    return get_market_service().quality(date)


def market_overview(date: str | None = None) -> dict[str, object]:
    return _overview(date, market_data_version())


def market_indices(date: str | None, lookback: int) -> dict[str, object]:
    return _indices(date, lookback, market_data_version())


def market_breadth(date: str | None, lookback: int) -> dict[str, object]:
    return _breadth(date, lookback, market_data_version())


def market_quality(date: str | None = None) -> dict[str, object]:
    return _quality(date, market_data_version())
