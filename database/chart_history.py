from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from visualization.chart_config import ChartConfig


@dataclass(frozen=True)
class ChartHistoryItem:
    created_at: str
    file_name: str
    chart_type: str
    x_column: str | None
    y_columns: str
    aggregation: str | None
    output_format: str
    telegram_file_id: str | None = None
    media_type: str | None = None


class ChartHistoryRepository:
    """SQLite repository for manually created chart history."""

    def __init__(self, database_path: Path = Path("chart_history.sqlite3")) -> None:
        self.database_path = database_path
        self._ensure_schema()

    def add(
        self,
        telegram_id: int,
        file_name: str,
        config: ChartConfig,
        telegram_file_id: str | None = None,
        media_type: str | None = None,
    ) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO chart_history
                (telegram_id, created_at, file_name, chart_type, x_column, y_columns, aggregation, output_format, telegram_file_id, media_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    datetime.now().isoformat(timespec="seconds"),
                    file_name,
                    config.chart_type,
                    config.x_column,
                    ", ".join(config.y_columns),
                    config.aggregation,
                    config.output_format,
                    telegram_file_id,
                    media_type,
                ),
            )

    def list_recent(self, telegram_id: int, limit: int = 10) -> list[ChartHistoryItem]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT created_at, file_name, chart_type, x_column, y_columns, aggregation, output_format, telegram_file_id, media_type
                FROM chart_history
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_id, limit),
            ).fetchall()
        return [ChartHistoryItem(*row) for row in rows]

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chart_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    chart_type TEXT NOT NULL,
                    x_column TEXT,
                    y_columns TEXT,
                    aggregation TEXT,
                    output_format TEXT NOT NULL
                )
                """
            )
            _add_column_if_missing(connection, "chart_history", "telegram_file_id", "TEXT")
            _add_column_if_missing(connection, "chart_history", "media_type", "TEXT")


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
