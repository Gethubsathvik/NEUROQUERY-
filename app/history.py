"""Tiny persistent query history (separate SQLite file)."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class History:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS history ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL, sql TEXT NOT NULL, "
                "row_count INTEGER NOT NULL, engine TEXT NOT NULL, "
                "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def add(self, question: str, sql: str, row_count: int, engine: str) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO history (question, sql, row_count, engine) VALUES (?,?,?,?)",
                    (question, sql, row_count, engine),
                )
        finally:
            conn.close()

    def recent(self, limit: int = 20) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, question, sql, row_count, engine, created_at FROM history "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
        keys = ("id", "question", "sql", "row_count", "engine", "created_at")
        return [dict(zip(keys, r)) for r in rows]
