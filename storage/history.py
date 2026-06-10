from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HistoryItem:
    created_at: str
    file_name: str
    analysis_type: str
    result_summary: str
    report_file_id: str | None = None


class HistoryRepository:
    def __init__(self, database_path: Path = Path("analysis_history.sqlite3")) -> None:
        self.database_path = database_path
        self._ensure_schema()

    def add(
        self,
        telegram_id: int,
        file_name: str,
        analysis_type: str,
        results: dict[str, Any],
        report_file_id: str | None = None,
    ) -> None:
        payload = json.dumps(_json_safe(results), ensure_ascii=False)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO analysis_history (telegram_id, created_at, file_name, analysis_type, result_json, report_file_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (telegram_id, datetime.now().isoformat(timespec="seconds"), file_name, analysis_type, payload, report_file_id),
            )

    def list_recent(self, telegram_id: int, limit: int = 5) -> list[HistoryItem]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT created_at, file_name, analysis_type, result_json, report_file_id
                FROM analysis_history
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_id, limit),
            ).fetchall()

        items: list[HistoryItem] = []
        for created_at, file_name, analysis_type, result_json, report_file_id in rows:
            data = json.loads(result_json)
            summary = "; ".join(f"{key}: {value}" for key, value in data.get("kpis", {}).items()) or "без KPI"
            items.append(HistoryItem(created_at, file_name, analysis_type, summary, report_file_id))
        return items

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            _add_column_if_missing(connection, "analysis_history", "report_file_id", "TEXT")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict(orient="records")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
