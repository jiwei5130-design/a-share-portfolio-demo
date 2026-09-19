"""Read-only access to sector and benchmark facts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.market_data.config import DATABASE_PATH


class SectorRepository:
    def __init__(self, database_path: Path | str = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def latest_common_date(self) -> str:
        with self.connect() as connection:
            sector_date = connection.execute("SELECT MAX(date) FROM sector_daily").fetchone()[0]
            benchmark_date = connection.execute(
                "SELECT MAX(date) FROM index_daily WHERE index_code='000300' AND exchange='SSE'"
            ).fetchone()[0]
        if not sector_date:
            raise LookupError("NO_SECTOR_DATA")
        if not benchmark_date:
            raise LookupError("NO_HS300_BENCHMARK_DATA")
        return min(str(sector_date), str(benchmark_date))

    def resolve_date(self, requested: str | None) -> str:
        latest = self.latest_common_date()
        if requested is None:
            return latest
        if requested > latest:
            raise ValueError(f"date cannot be later than latest common sector/benchmark date {latest}")
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(date) FROM sector_daily WHERE date<=?", (requested,)
            ).fetchone()
        if not row or not row[0]:
            raise LookupError("NO_SECTOR_DATA_FOR_DATE")
        return str(row[0])

    def history(self, as_of_date: str, rows_per_sector: int = 80) -> pd.DataFrame:
        with self.connect() as connection:
            return pd.read_sql_query(
                """
                WITH ranked AS (
                    SELECT d.*,b.sector_name,b.classification_version,b.classification_basis,
                           b.quality_status AS basic_quality_status,
                           ROW_NUMBER() OVER(PARTITION BY d.sector_code ORDER BY d.date DESC) rn
                    FROM sector_daily d JOIN sector_basic b
                      ON b.sector_system=d.sector_system AND b.sector_code=d.sector_code
                    WHERE d.sector_system='SW' AND b.level=1 AND d.date<=?
                )
                SELECT * FROM ranked WHERE rn<=? ORDER BY sector_code,date
                """,
                connection,
                params=(as_of_date, rows_per_sector),
            )

    def benchmark_history(self, as_of_date: str, rows: int = 80) -> pd.DataFrame:
        with self.connect() as connection:
            return pd.read_sql_query(
                """
                SELECT date,close FROM (
                    SELECT date,close,ROW_NUMBER() OVER(ORDER BY date DESC) rn
                    FROM index_daily
                    WHERE index_code='000300' AND exchange='SSE' AND date<=?
                ) WHERE rn<=? ORDER BY date
                """,
                connection,
                params=(as_of_date, rows),
            )

    def sector_exists(self, sector_code: str) -> bool:
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM sector_basic WHERE sector_system='SW' AND sector_code=? AND level=1",
                (sector_code,),
            ).fetchone() is not None

    def quality(self, as_of_date: str) -> dict[str, object]:
        with self.connect() as connection:
            basic_count = int(connection.execute(
                "SELECT COUNT(*) FROM sector_basic WHERE sector_system='SW' AND level=1"
            ).fetchone()[0])
            loaded_count = int(connection.execute(
                "SELECT COUNT(DISTINCT sector_code) FROM sector_daily WHERE sector_system='SW'"
            ).fetchone()[0])
            current_count = int(connection.execute(
                "SELECT COUNT(DISTINCT sector_code) FROM sector_daily WHERE sector_system='SW' AND date=?",
                (as_of_date,),
            ).fetchone()[0])
            first_date, raw_latest_date, rows = connection.execute(
                "SELECT MIN(date),MAX(date),COUNT(*) FROM sector_daily WHERE sector_system='SW'"
            ).fetchone()
            duplicates = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT sector_system,sector_code,date,COUNT(*) n FROM sector_daily GROUP BY sector_system,sector_code,date HAVING n>1)"
            ).fetchone()[0])
            invalid = int(connection.execute(
                "SELECT COUNT(*) FROM sector_daily WHERE open<=0 OR high<=0 OR low<=0 OR close<=0 OR high<MAX(open,close,low) OR low>MIN(open,close,high)"
            ).fetchone()[0])
            membership_count = int(connection.execute(
                "SELECT COUNT(*) FROM sector_membership WHERE sector_system='SW'"
            ).fetchone()[0])
            metadata = dict(connection.execute(
                "SELECT classification_version,classification_basis,source FROM sector_basic WHERE sector_system='SW' LIMIT 1"
            ).fetchone())
        return {
            "sector_basic_count": basic_count,
            "loaded_sector_count": loaded_count,
            "as_of_sector_count": current_count,
            "coverage_pct": current_count / basic_count if basic_count else None,
            "first_date": first_date,
            "raw_latest_date": raw_latest_date,
            "row_count": int(rows),
            "duplicate_primary_keys": duplicates,
            "invalid_ohlc": invalid,
            "membership_count": membership_count,
            "membership_status": "NOT_AVAILABLE" if membership_count == 0 else "CURRENT_ONLY",
            "membership_basis": "NOT_AVAILABLE_UNIQUE_POINT_IN_TIME_CLASSIFICATION" if membership_count == 0 else "CURRENT_SNAPSHOT_NOT_HISTORICAL",
            "quality_status": "PASS" if duplicates == 0 and invalid == 0 and current_count == basic_count else "PARTIAL",
            **metadata,
        }

    def stock_membership(self, stock_code: str) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT m.*,b.sector_name,b.classification_version,b.classification_basis
                FROM sector_membership m JOIN sector_basic b
                  ON b.sector_system=m.sector_system AND b.sector_code=m.sector_code
                WHERE m.sector_system='SW' AND m.code=?
                  AND m.snapshot_date=(SELECT MAX(snapshot_date) FROM sector_membership WHERE sector_system='SW')
                """,
                (stock_code,),
            ).fetchall()
        return [dict(row) for row in rows]
