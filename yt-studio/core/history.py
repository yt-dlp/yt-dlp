import os
import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return base / "YTStudio" / "data.db"


class HistoryStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    format TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def add_download(self, title: str, url: str, output_path: str, format_id: str, status: str = "queued") -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO downloads (title, url, output_path, format, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title or url, url, output_path, format_id, status),
            )
            return int(cursor.lastrowid)

    def finish_download(self, download_id: int, status: str, error: str | None = None):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE downloads
                SET status = ?, completed_at = CURRENT_TIMESTAMP, error = ?
                WHERE id = ?
                """,
                (status, error, download_id),
            )

    def search_downloads(self, query: str = "") -> list[dict]:
        pattern = f"%{query}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, url, output_path, format, status, started_at, completed_at, error
                FROM downloads
                WHERE ? = '%%' OR title LIKE ? OR url LIKE ? OR output_path LIKE ?
                ORDER BY id DESC
                LIMIT 200
                """,
                (pattern, pattern, pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_setting(self, key: str, value: str):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def get_settings(self) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}
