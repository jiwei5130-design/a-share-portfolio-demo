"""SQLite connection and one-shot schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import DATABASE_PATH, SQLITE_PRAGMAS, ensure_data_directories
from .schema import DDL_STATEMENTS, INDEX_STATEMENTS, SCHEMA_VERSION


def connect(database_path: Path | str = DATABASE_PATH) -> sqlite3.Connection:
    ensure_data_directories()
    connection = sqlite3.connect(str(database_path), timeout=30)
    connection.row_factory = sqlite3.Row
    for key, value in SQLITE_PRAGMAS.items():
        connection.execute(f"PRAGMA {key}={value}")
    return connection


def initialize_database(database_path: Path | str = DATABASE_PATH) -> dict[str, object]:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        for statement in DDL_STATEMENTS:
            connection.execute(statement)
        for statement in INDEX_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value, updated_at)
            VALUES('schema_version', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (SCHEMA_VERSION,),
        )
        from .sources.source_registry import seed_registry
        seed_registry(connection)
        connection.commit()
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        indexes = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex%' ORDER BY name"
        )]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    result = {"database": str(path), "schema_version": SCHEMA_VERSION, "tables": tables, "indexes": indexes, "integrity": integrity}
    print(f"Database: {path}")
    print(f"Schema version: {SCHEMA_VERSION}")
    print(f"Tables ({len(tables)}): {', '.join(tables)}")
    print(f"Indexes ({len(indexes)}): {', '.join(indexes)}")
    print(f"Integrity: {integrity}")
    return result


if __name__ == "__main__":
    initialize_database()
