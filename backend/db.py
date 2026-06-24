"""Shared SQLite connection for Lumi's durable state.

A single stdlib-sqlite3 connection to `lumi_memory.db` — the same file the sqlite-vec
embedding index (mcp/_memvec.py) uses, but these are plain relational tables that don't
need the vec extension, so stdlib sqlite3 (always available) is enough here.

Tables: memories, schedules, usage, settings. Each owning module
(mcp/memory.py, scheduler.py, usage.py, llm.py) reads/writes its own table through the
helpers below and migrates its legacy JSON file on first run.

WAL is enabled here so this connection and _memvec's APSW connection can share the file
without locking each other out; busy_timeout makes the rare concurrent write wait rather
than error. Call connect() once at startup before _memvec opens the file.
"""

import os
import sqlite3
import threading

_DB_PATH = os.path.join(os.path.dirname(__file__), "lumi_memory.db")
# Reentrant so query()/write() can hold the lock and still call connect() underneath.
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    key        TEXT PRIMARY KEY,
    tier       TEXT NOT NULL,
    fact       TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
    id         TEXT PRIMARY KEY,
    prompt     TEXT NOT NULL,
    cron       TEXT NOT NULL,
    label      TEXT NOT NULL DEFAULT '',
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    last_run   REAL
);
CREATE TABLE IF NOT EXISTS usage (
    day         TEXT NOT NULL,
    model       TEXT NOT NULL,
    input       INTEGER NOT NULL DEFAULT 0,
    output      INTEGER NOT NULL DEFAULT 0,
    cache_read  INTEGER NOT NULL DEFAULT 0,
    cache_write INTEGER NOT NULL DEFAULT 0,
    reasoning   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, model)
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    """Open (once) the shared connection, set pragmas, and ensure the schema."""
    global _conn
    with _lock:
        if _conn is not None:
            return _conn
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _migrate_usage_to_per_model(conn)
        conn.executescript(_SCHEMA)
        conn.commit()
        _conn = conn
        return _conn


def _migrate_usage_to_per_model(conn: sqlite3.Connection) -> None:
    """Upgrade an older day-only `usage` table to the per-model (day, model) shape.

    Pre-existing totals weren't attributed to a model, so they're filed under 'legacy'
    (they won't surface in the UI, which only shows the current model's usage)."""
    cols = conn.execute("PRAGMA table_info(usage)").fetchall()
    if not cols or any(c[1] == "model" for c in cols):
        return  # table absent (fresh) or already migrated
    conn.executescript(
        """
        ALTER TABLE usage RENAME TO usage_old;
        CREATE TABLE usage (
            day TEXT NOT NULL, model TEXT NOT NULL,
            input INTEGER NOT NULL DEFAULT 0, output INTEGER NOT NULL DEFAULT 0,
            cache_read INTEGER NOT NULL DEFAULT 0, cache_write INTEGER NOT NULL DEFAULT 0,
            reasoning INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, model)
        );
        INSERT INTO usage(day, model, input, output, cache_read, cache_write, reasoning)
            SELECT day, 'legacy', input, output, cache_read, cache_write, reasoning FROM usage_old;
        DROP TABLE usage_old;
        """
    )
    conn.commit()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a read query and return all rows."""
    with _lock:
        return connect().execute(sql, params).fetchall()


def write(fn) -> None:
    """Run fn(conn) inside a single transaction under the connection lock.

    Use this for atomic multi-statement writes (e.g. DELETE-all + executemany rewrites).
    Commits on success, rolls back on error.
    """
    with _lock:
        conn = connect()
        try:
            fn(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
