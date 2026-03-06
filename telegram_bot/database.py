import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import DB_PATH, MAX_HISTORY_PER_USER

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        # WAL: читатели не блокируют писателей при параллельных загрузках
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                is_approved INTEGER NOT NULL DEFAULT 0,
                is_banned   INTEGER NOT NULL DEFAULT 0,
                is_admin    INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                approved_at TEXT,
                approved_by INTEGER,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS download_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                url         TEXT NOT NULL,
                title       TEXT,
                format_id   TEXT,
                quality     TEXT,
                file_size   INTEGER,
                status      TEXT NOT NULL DEFAULT 'pending',
                error       TEXT,
                created_at  TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS stats (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_user ON download_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_history_status ON download_history(status);

            CREATE TABLE IF NOT EXISTS sessions (
                chat_id         INTEGER NOT NULL,
                message_id      INTEGER NOT NULL,
                url             TEXT NOT NULL,
                video_info_json TEXT NOT NULL,
                created_at      TEXT,
                PRIMARY KEY (chat_id, message_id)
            );
        """)
    logger.info("Database initialized at %s", DB_PATH)


# ── User management ────────────────────────────────────────────────────────────

def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()


def upsert_user(user_id: int, username: str, full_name: str) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username or "", full_name or "", datetime.utcnow().isoformat()))


def approve_user(user_id: int, approved_by: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE users
               SET is_approved = 1,
                   approved_at = ?,
                   approved_by = ?
             WHERE user_id = ?
        """, (datetime.utcnow().isoformat(), approved_by, user_id))
        return cur.rowcount > 0


def ban_user(user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        return cur.rowcount > 0


def unban_user(user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        return cur.rowcount > 0


def set_admin(user_id: int, is_admin: bool) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if is_admin else 0, user_id)
        )
        return cur.rowcount > 0


def list_users(approved: Optional[bool] = None, banned: bool = False) -> list:
    with get_connection() as conn:
        if approved is None:
            return conn.execute(
                "SELECT * FROM users WHERE is_banned = ? ORDER BY created_at DESC",
                (1 if banned else 0,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM users WHERE is_approved = ? AND is_banned = ? ORDER BY created_at DESC",
            (1 if approved else 0, 1 if banned else 0)
        ).fetchall()


def pending_users() -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE is_approved = 0 AND is_banned = 0 ORDER BY created_at"
        ).fetchall()


def is_authorized(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT is_approved, is_banned FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return False
        return bool(row["is_approved"]) and not bool(row["is_banned"])


def is_admin(user_id: int) -> bool:
    from config import ADMIN_IDS
    if user_id in ADMIN_IDS:
        return True
    with get_connection() as conn:
        row = conn.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row["is_admin"]) if row else False


# ── Download history ───────────────────────────────────────────────────────────

def add_download(user_id: int, url: str) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO download_history (user_id, url, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (user_id, url, datetime.utcnow().isoformat()))
        return cur.lastrowid


def update_download(
    download_id: int,
    *,
    title: str = None,
    format_id: str = None,
    quality: str = None,
    file_size: int = None,
    status: str = None,
    error: str = None,
) -> None:
    fields, values = [], []
    for col, val in [
        ("title", title), ("format_id", format_id), ("quality", quality),
        ("file_size", file_size), ("status", status), ("error", error),
    ]:
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if status in ("done", "error"):
        fields.append("finished_at = ?")
        values.append(datetime.utcnow().isoformat())
    if not fields:
        return
    values.append(download_id)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE download_history SET {', '.join(fields)} WHERE id = ?",
            values
        )


def get_user_history(user_id: int, limit: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM download_history
             WHERE user_id = ?
             ORDER BY created_at DESC
             LIMIT ?
        """, (user_id, limit)).fetchall()


# ── Sessions (persistent quality-selection state) ──────────────────────────────

def save_session(chat_id: int, message_id: int, url: str, video_info_json: str) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sessions (chat_id, message_id, url, video_info_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, message_id, url, video_info_json, datetime.utcnow().isoformat()))


def get_session(chat_id: int, message_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT url, video_info_json FROM sessions WHERE chat_id=? AND message_id=?",
            (chat_id, message_id)
        ).fetchone()
    return dict(row) if row else None


def delete_session(chat_id: int, message_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE chat_id=? AND message_id=?",
            (chat_id, message_id)
        )


# ── Cleanup ────────────────────────────────────────────────────────────────────

def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    cutoff = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
        return cur.rowcount


def cleanup_old_history(max_age_days: int = 30) -> int:
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM download_history WHERE created_at < ?", (cutoff,))
        return cur.rowcount


def get_global_stats() -> dict:
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_approved=1").fetchone()[0]
        total_downloads = conn.execute(
            "SELECT COUNT(*) FROM download_history WHERE status='done'"
        ).fetchone()[0]
        total_size = conn.execute(
            "SELECT COALESCE(SUM(file_size),0) FROM download_history WHERE status='done'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_approved=0 AND is_banned=0"
        ).fetchone()[0]
        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "total_size_bytes": total_size,
            "pending_requests": pending,
        }
