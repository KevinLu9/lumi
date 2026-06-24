"""sqlite-vec index for Lumi's long-term memory — pure vector storage.

The JSON store in `memory.py` is the source of truth for fact text; this is a
derived cosine-similarity index over the long-term tier's embeddings, keyed by the
same memory key. `memory.py` owns embedding + rebuild orchestration; this module
only stores, deletes, and searches vectors.

The venv's stdlib sqlite3 is built without loadable-extension support, so we use
APSW (which ships arm64/x86 wheels and supports `loadextension`). If APSW or the
sqlite-vec extension can't load, AVAILABLE is False and `memory.py` falls back to
keyword search.

Underscore-prefixed so the tool registry never imports it as a tool module.
"""

import os
import threading

from ._embeddings import DIM

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lumi_memory.db")
_lock = threading.Lock()
_conn = None

AVAILABLE = True
try:
    import apsw
    import sqlite_vec
except Exception:
    AVAILABLE = False


def _connect():
    """Open (once) the APSW connection with the sqlite-vec extension loaded and the
    schema ensured. Returns the connection, or None if the extension can't load."""
    global _conn, AVAILABLE
    if _conn is not None:
        return _conn
    if not AVAILABLE:
        return None
    try:
        conn = apsw.Connection(_DB_PATH)
        conn.enableloadextension(True)
        conn.loadextension(sqlite_vec.loadable_path())
        conn.enableloadextension(False)
        conn.cursor().execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec "
            f"USING vec0(embedding float[{DIM}] distance_metric=cosine)"
        )
        conn.cursor().execute(
            "CREATE TABLE IF NOT EXISTS map(rowid INTEGER PRIMARY KEY, key TEXT UNIQUE)"
        )
        _conn = conn
        return _conn
    except Exception:
        AVAILABLE = False
        return None


def _rowid_for(conn, key: str):
    row = conn.cursor().execute("SELECT rowid FROM map WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def upsert(key: str, embedding: list[float]) -> bool:
    """Insert or replace the vector for `key`. Returns True on success."""
    with _lock:
        conn = _connect()
        if conn is None:
            return False
        try:
            blob = sqlite_vec.serialize_float32(embedding)
            cur = conn.cursor()
            rid = _rowid_for(conn, key)
            if rid is not None:
                cur.execute("DELETE FROM vec WHERE rowid = ?", (rid,))
            else:
                cur.execute("INSERT INTO map(key) VALUES (?)", (key,))
                rid = conn.last_insert_rowid()
            cur.execute("INSERT INTO vec(rowid, embedding) VALUES (?, ?)", (rid, blob))
            return True
        except Exception:
            return False


def delete(key: str) -> None:
    """Remove the vector for `key` (no-op if absent)."""
    with _lock:
        conn = _connect()
        if conn is None:
            return
        try:
            rid = _rowid_for(conn, key)
            if rid is not None:
                conn.cursor().execute("DELETE FROM vec WHERE rowid = ?", (rid,))
                conn.cursor().execute("DELETE FROM map WHERE rowid = ?", (rid,))
        except Exception:
            pass


def search(embedding: list[float], k: int = 5) -> list[tuple[str, float]]:
    """Return up to k (key, cosine_distance) pairs nearest to `embedding`, closest
    first. Empty list if unavailable or the index is empty."""
    with _lock:
        conn = _connect()
        if conn is None:
            return []
        try:
            blob = sqlite_vec.serialize_float32(embedding)
            rows = conn.cursor().execute(
                "SELECT rowid, distance FROM vec WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                (blob, k),
            ).fetchall()
            if not rows:
                return []
            keys = dict(conn.cursor().execute("SELECT rowid, key FROM map").fetchall())
            return [(keys[rid], dist) for rid, dist in rows if rid in keys]
        except Exception:
            return []


def count() -> int:
    """Number of vectors currently indexed."""
    with _lock:
        conn = _connect()
        if conn is None:
            return 0
        try:
            return conn.cursor().execute("SELECT COUNT(*) FROM map").fetchone()[0]
        except Exception:
            return 0


def clear() -> None:
    """Drop all vectors (used before a full rebuild from the JSON store)."""
    with _lock:
        conn = _connect()
        if conn is None:
            return
        try:
            conn.cursor().execute("DELETE FROM vec")
            conn.cursor().execute("DELETE FROM map")
        except Exception:
            pass


if __name__ == "__main__":
    from ._embeddings import embed
    print("AVAILABLE:", AVAILABLE)
    clear()
    for key, fact in [
        ("diet", "The user is vegetarian."),
        ("pet", "The user has a dog named Rex."),
        ("city", "The user lives in Sydney."),
    ]:
        v = embed(fact)
        print(f"upsert {key}:", upsert(key, v) if v else "no embedding")
    print("count:", count())
    q = embed("what does the user eat?", query=True)
    print("search 'what does the user eat?':", search(q, 3) if q else "no embedding")
    delete("diet")
    print("count after delete diet:", count())
    clear()
