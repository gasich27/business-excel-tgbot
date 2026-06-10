from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from analysis.umap_analysis import UmapResult


@dataclass(frozen=True)
class UmapHistoryItem:
    created_at: str
    file_name: str
    used_columns: str
    sample_size: int
    total_rows: int


class UmapHistoryRepository:
    """SQLite repository for UMAP previews built for users."""

    def __init__(self, database_path: Path = Path("umap_history.sqlite3")) -> None:
        self.database_path = database_path
        self._ensure_schema()

    def add(self, telegram_id: int, file_name: str, result: UmapResult) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO umap_history
                (telegram_id, created_at, file_name, used_columns, sample_size, total_rows)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    datetime.now().isoformat(timespec="seconds"),
                    file_name,
                    ", ".join(result.used_columns),
                    result.sample_size,
                    result.total_rows,
                ),
            )

    def list_recent(self, telegram_id: int, limit: int = 10) -> list[UmapHistoryItem]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT created_at, file_name, used_columns, sample_size, total_rows
                FROM umap_history
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_id, limit),
            ).fetchall()
        return [UmapHistoryItem(*row) for row in rows]

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS umap_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    used_columns TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    total_rows INTEGER NOT NULL
                )
                """
            )
