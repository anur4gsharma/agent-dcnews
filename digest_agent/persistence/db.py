from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path


class DigestDB:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    sent_date TEXT NOT NULL,
                    category TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    rating INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES sent_items(id)
                )
                """
            )

    def get_recent_headlines(self, limit: int = 100) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT title FROM sent_items ORDER BY sent_date DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [row["title"] for row in rows]

    def get_recent_urls(self, limit: int = 100) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT url FROM sent_items ORDER BY sent_date DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [row["url"] for row in rows]

    def record_digest(self, digest: dict, sent_date: date) -> None:
        rows = []
        for item in digest.get("top_news", []):
            rows.append((item["title"], item["url"], sent_date.isoformat(), "news"))
        for item in digest.get("top_opportunities", []):
            rows.append((item["title"], item["url"], sent_date.isoformat(), "opportunity"))

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO sent_items (title, url, sent_date, category)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

    def log_feedback(self, item_id: int, rating: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (item_id, rating, timestamp) VALUES (?, ?, ?)",
                (item_id, rating, datetime.now(timezone.utc).isoformat()),
            )

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

