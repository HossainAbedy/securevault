"""
SecureVault SQLite database layer.

Schema design:
  users         — one row per vault owner; stores encrypted vault key
                  (DPAPI blob for Windows owner, Argon2-wrapped for others)
  vault_entries — per-user password records; enc_password is AES-256-GCM blob
  settings      — simple key/value app config

The DB file itself is NOT encrypted at the file level; all sensitive columns
are encrypted individually at the application layer before writing.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path.home() / ".securevault" / "vault.db"


# ── Connection ──────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory   = sqlite3.Row
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA foreign_keys = ON")
    return c


# ── Schema ──────────────────────────────────────────────────────────────────

def initialize_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,

            -- Windows DPAPI path (owner only)
            windows_sid   TEXT,
            dpapi_enc_key BLOB,          -- vault key wrapped by DPAPI

            -- Master-password path (all other users)
            mpw_salt      BLOB,          -- Argon2id salt
            mpw_enc_key   BLOB,          -- vault key encrypted with derived key
            mpw_hash      TEXT,          -- Argon2id hash (for fast verify before KDF)

            created_at    TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vault_entries (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL
                               REFERENCES users(id) ON DELETE CASCADE,
            title          TEXT    NOT NULL,
            url            TEXT    DEFAULT '',
            entry_username TEXT    DEFAULT '',
            enc_password   BLOB    NOT NULL,   -- AES-256-GCM(vault_key, password)
            notes          TEXT    DEFAULT '',
            category       TEXT    DEFAULT 'General',
            created_at     TEXT    DEFAULT CURRENT_TIMESTAMP,
            updated_at     TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_entries_user
            ON vault_entries(user_id);

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)


# ── Users ───────────────────────────────────────────────────────────────────

def create_user(
    username: str,
    *,
    windows_sid:   Optional[str]   = None,
    dpapi_enc_key: Optional[bytes] = None,
    mpw_salt:      Optional[bytes] = None,
    mpw_enc_key:   Optional[bytes] = None,
    mpw_hash:      Optional[str]   = None,
) -> int:
    with _conn() as c:
        r = c.execute(
            """INSERT INTO users
               (username, windows_sid, dpapi_enc_key, mpw_salt, mpw_enc_key, mpw_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, windows_sid, dpapi_enc_key, mpw_salt, mpw_enc_key, mpw_hash),
        )
        return r.lastrowid


def get_user_by_sid(sid: str) -> Optional[sqlite3.Row]:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE windows_sid = ?", (sid,)
        ).fetchone()


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_all_users() -> list:
    with _conn() as c:
        return c.execute(
            "SELECT id, username, windows_sid FROM users ORDER BY username"
        ).fetchall()


def update_user_dpapi(user_id: int, dpapi_enc_key: bytes, windows_sid: str):
    """Link an existing master-password user to the current Windows account."""
    with _conn() as c:
        c.execute(
            "UPDATE users SET dpapi_enc_key = ?, windows_sid = ? WHERE id = ?",
            (dpapi_enc_key, windows_sid, user_id),
        )


def update_master_password(
    user_id: int, mpw_salt: bytes, mpw_enc_key: bytes, mpw_hash: str
):
    with _conn() as c:
        c.execute(
            """UPDATE users
               SET mpw_salt = ?, mpw_enc_key = ?, mpw_hash = ?
               WHERE id = ?""",
            (mpw_salt, mpw_enc_key, mpw_hash, user_id),
        )


# ── Vault entries ───────────────────────────────────────────────────────────

def add_entry(
    user_id: int,
    title: str,
    url: str,
    username: str,
    enc_password: bytes,
    notes: str = "",
    category: str = "General",
) -> int:
    with _conn() as c:
        r = c.execute(
            """INSERT INTO vault_entries
               (user_id, title, url, entry_username, enc_password, notes, category)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, url, username, enc_password, notes, category),
        )
        return r.lastrowid


def get_entries(user_id: int) -> list:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM vault_entries WHERE user_id = ? ORDER BY category, title",
            (user_id,),
        ).fetchall()


def get_entry(entry_id: int, user_id: int) -> Optional[sqlite3.Row]:
    with _conn() as c:
        return c.execute(
            "SELECT * FROM vault_entries WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        ).fetchone()


def update_entry(
    entry_id: int,
    user_id: int,
    title: str,
    url: str,
    username: str,
    enc_password: bytes,
    notes: str,
    category: str,
):
    with _conn() as c:
        c.execute(
            """UPDATE vault_entries
               SET title = ?, url = ?, entry_username = ?, enc_password = ?,
                   notes = ?, category = ?, updated_at = ?
               WHERE id = ? AND user_id = ?""",
            (
                title, url, username, enc_password,
                notes, category, datetime.now().isoformat(),
                entry_id, user_id,
            ),
        )


def delete_entry(entry_id: int, user_id: int):
    with _conn() as c:
        c.execute(
            "DELETE FROM vault_entries WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )


def search_entries(user_id: int, query: str) -> list:
    like = f"%{query}%"
    with _conn() as c:
        return c.execute(
            """SELECT * FROM vault_entries
               WHERE user_id = ?
                 AND (title LIKE ? OR url LIKE ?
                      OR entry_username LIKE ? OR category LIKE ?)
               ORDER BY title""",
            (user_id, like, like, like, like),
        ).fetchall()


def get_entries_for_domain(user_id: int, domain: str) -> list:
    """Used by native messaging host to find credentials by URL substring."""
    with _conn() as c:
        return c.execute(
            """SELECT id, title, entry_username, enc_password
               FROM vault_entries
               WHERE user_id = ? AND url LIKE ?
               ORDER BY title""",
            (user_id, f"%{domain}%"),
        ).fetchall()


# ── Settings ────────────────────────────────────────────────────────────────

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with _conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
