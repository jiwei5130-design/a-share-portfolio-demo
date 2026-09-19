"""Read-only SQLite access for market intelligence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.market_data.config import DATABASE_PATH


class MarketIntelligenceRepository:
    def __init__(self, database_path: Path | str = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def latest_common_date(self) -> str:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MIN(last_date) FROM (SELECT MAX(date) last_date FROM index_daily GROUP BY index_code,exchange)"
            ).fetchone()
        if not row or not row[0]:
            raise LookupError("NO_INDEX_DATA")
        return str(row[0])

    def resolve_date(self, requested: str | None) -> str:
        latest = self.latest_common_date()
        if requested is None:
            return latest
        if requested > latest:
            raise ValueError(f"date cannot be later than latest common index date {latest}")
        with self.connect() as connection:
            row = connection.execute("SELECT MAX(date) FROM index_daily WHERE date<=?", (requested,)).fetchone()
        if not row or not row[0]:
            raise LookupError("NO_DATA_FOR_DATE")
        return str(row[0])

    def index_history(self, as_of_date: str, rows_per_index: int) -> pd.DataFrame:
        with self.connect() as connection:
            return pd.read_sql_query(
                """
                WITH ranked AS (
                    SELECT d.*,b.index_name,
                           ROW_NUMBER() OVER(PARTITION BY d.index_code,d.exchange ORDER BY d.date DESC) rn
                    FROM index_daily d JOIN index_basic b USING(index_code,exchange)
                    WHERE d.date<=? AND b.is_core=1
                )
                SELECT * FROM ranked WHERE rn<=? ORDER BY index_code,exchange,date
                """,
                connection,
                params=(as_of_date, rows_per_index),
            )

    def stock_window(self, as_of_date: str, warmup_dates: int = 90) -> pd.DataFrame:
        with self.connect() as connection:
            dates = [row[0] for row in connection.execute(
                "SELECT DISTINCT date FROM market_daily WHERE date<=? ORDER BY date DESC LIMIT ?",
                (as_of_date, warmup_dates),
            )]
            if not dates:
                raise LookupError("NO_MARKET_DAILY_DATA")
            cutoff = min(dates)
            return pd.read_sql_query(
                """
                SELECT d.code,d.exchange,d.date,d.close,d.volume,d.amount,b.market
                FROM market_daily d JOIN stock_basic b USING(code,exchange)
                WHERE d.date BETWEEN ? AND ? AND d.adjust_type='RAW'
                ORDER BY d.code,d.exchange,d.date
                """,
                connection,
                params=(cutoff, as_of_date),
            )

    def coverage(self, as_of_date: str) -> dict[str, object]:
        with self.connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0])
            loaded = int(connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT code,exchange FROM market_daily
                    WHERE adjust_type='RAW' AND date<=?
                )
                """,
                (as_of_date,),
            ).fetchone()[0])
            traded = int(connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT code,exchange FROM market_daily
                    WHERE adjust_type='RAW' AND date=?
                )
                """,
                (as_of_date,),
            ).fetchone()[0])
            markets = [dict(row) for row in connection.execute(
                """
                SELECT b.market,COUNT(*) stock_basic_count,
                       SUM(CASE WHEN x.code IS NOT NULL THEN 1 ELSE 0 END) loaded_count
                FROM stock_basic b LEFT JOIN (
                    SELECT DISTINCT code,exchange FROM market_daily
                    WHERE adjust_type='RAW' AND date<=?
                ) x USING(code,exchange)
                GROUP BY b.market ORDER BY b.market
                """,
                (as_of_date,),
            )]
        for item in markets:
            item["coverage_pct"] = item["loaded_count"] / item["stock_basic_count"] if item["stock_basic_count"] else None
        return {
            "as_of_date": as_of_date,
            "stock_basic_count": total,
            "loaded_count": loaded,
            "traded_count": traded,
            "coverage_pct": loaded / total if total else None,
            "loaded_count_basis": "DISTINCT_RAW_SECURITY_THROUGH_AS_OF_DATE",
            "traded_count_basis": "DISTINCT_RAW_SECURITY_ON_AS_OF_DATE",
            "markets": markets,
        }

    def database_quality(self) -> dict[str, object]:
        with self.connect() as connection:
            return {
                "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
                "index_duplicate_count": int(connection.execute(
                    "SELECT COUNT(*) FROM (SELECT index_code,exchange,date,COUNT(*) n FROM index_daily GROUP BY index_code,exchange,date HAVING n>1)"
                ).fetchone()[0]),
                "index_invalid_ohlc_count": int(connection.execute(
                    "SELECT COUNT(*) FROM index_daily WHERE open<=0 OR high<=0 OR low<=0 OR close<=0 OR high<MAX(open,close,low) OR low>MIN(open,close,high)"
                ).fetchone()[0]),
                "market_non_raw_count": int(connection.execute("SELECT COUNT(*) FROM market_daily WHERE adjust_type<>'RAW'").fetchone()[0]),
                "index_count": int(connection.execute("SELECT COUNT(DISTINCT index_code||char(124)||exchange) FROM index_daily").fetchone()[0]),
                "index_rows": int(connection.execute("SELECT COUNT(*) FROM index_daily").fetchone()[0]),
            }

    def index_summary(self) -> dict[str, int]:
        with self.connect() as connection:
            return {
                "index_count": int(connection.execute("SELECT COUNT(DISTINCT index_code||char(124)||exchange) FROM index_daily").fetchone()[0]),
                "index_rows": int(connection.execute("SELECT COUNT(*) FROM index_daily").fetchone()[0]),
            }
