"""Central configuration for Market Data Layer V1.0."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "market_data.db"
REPORT_DIR = DATA_DIR / "market_data_reports"

HISTORY_START_DATE = "2020-01-01"
RETRY_COUNT = 3
REQUEST_INTERVAL = 0.25
BATCH_SIZE = 200

DATA_SOURCE_PRIORITY = {
    "stock_basic": ("exchange", "akshare_aggregate"),
    "market_daily": ("tencent", "sina", "eastmoney_future"),
    "index_daily": ("sina", "tencent", "eastmoney_future"),
    "trading_calendar": ("sina",),
    "industry": ("sw", "eastmoney_future"),
    "concept": ("eastmoney_future",),
    "suspension": ("eastmoney_future",),
}

CORE_INDEX_LIST = (
    {"index_code": "000001", "exchange": "SSE", "index_name": "上证指数", "canonical": "000001.SH", "symbol": "sh000001"},
    {"index_code": "399001", "exchange": "SZSE", "index_name": "深证成指", "canonical": "399001.SZ", "symbol": "sz399001"},
    {"index_code": "000300", "exchange": "SSE", "index_name": "沪深300", "canonical": "000300.SH", "symbol": "sh000300"},
    {"index_code": "000905", "exchange": "SSE", "index_name": "中证500", "canonical": "000905.SH", "symbol": "sh000905"},
    {"index_code": "000852", "exchange": "SSE", "index_name": "中证1000", "canonical": "000852.SH", "symbol": "sh000852"},
    {"index_code": "399006", "exchange": "SZSE", "index_name": "创业板指", "canonical": "399006.SZ", "symbol": "sz399006"},
    {"index_code": "000688", "exchange": "SSE", "index_name": "科创50", "canonical": "000688.SH", "symbol": "sh000688"},
)

MARKET_MAPPING = {
    "SH_MAIN": {"exchange": "SSE", "prefixes": ("600", "601", "603", "605")},
    "STAR": {"exchange": "SSE", "prefixes": ("688", "689")},
    "SZ_MAIN": {"exchange": "SZSE", "prefixes": ("000", "001", "002", "003")},
    "GEM": {"exchange": "SZSE", "prefixes": ("300", "301", "302")},
    "BSE": {"exchange": "BSE", "prefixes": ("4", "8", "9")},
}

QUALITY_THRESHOLDS = {
    "stock_daily_coverage_min": 0.98,
    "core_index_coverage_min": 1.0,
    "max_cross_source_close_diff_pct": 0.005,
    "volume_outlier_median_multiple": 100.0,
    "calendar_duplicate_max": 0,
}

SQLITE_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "foreign_keys": "ON",
    "busy_timeout": 30000,
    "temp_store": "MEMORY",
}


def ensure_data_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
