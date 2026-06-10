from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class TableHistoryItem:
    created_at: str
    file_name: str
    telegram_file_id: str | None = None


class TableHistoryRepository:
    """SQLite repository for files uploaded by Telegram users."""

    def __init__(self, database_path: Path = Path("table_history.sqlite3")) -> None:
        self.database_path = database_path
        self._ensure_schema()

    def add(self, telegram_id: int, file_name: str, telegram_file_id: str | None = None) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO table_history (telegram_id, created_at, file_name, telegram_file_id)
                VALUES (?, ?, ?, ?)
                """,
                (telegram_id, datetime.now().isoformat(timespec="seconds"), file_name, telegram_file_id),
            )

    def list_recent(self, telegram_id: int, limit: int = 10) -> list[TableHistoryItem]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT created_at, file_name, telegram_file_id
                FROM table_history
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_id, limit),
            ).fetchall()
        return [TableHistoryItem(*row) for row in rows]

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS table_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL
                )
                """
            )
            _add_column_if_missing(connection, "table_history", "telegram_file_id", "TEXT")


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
