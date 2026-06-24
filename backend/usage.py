"""Per-day, per-model LLM token usage ledger, persisted in the shared SQLite database.

Tracks token usage bucketed by local calendar date (YYYY-MM-DD) AND model in the `usage`
table, so the UI can show "today's" usage for the active model. Independent of conversation
history — it survives `chat_reset` and server restarts, and accumulates across every session
in a day. Past days/models are kept as a cheap history; only today()'s current-model row is
surfaced to the UI.
"""

import json
import os
import threading
from datetime import date

from . import db

_FIELDS = ("input", "output", "cache_read", "cache_write", "reasoning")


def _model_key(model) -> str:
    """Canonical 'provider/model' key. Accepts a {provider,model} dict or a string."""
    if isinstance(model, dict):
        return f"{model.get('provider', '')}/{model.get('model', '')}"
    return str(model or "")
# Legacy JSON store, migrated into SQLite on first use then renamed to .bak.
_LEGACY_JSON = os.path.join(os.path.dirname(__file__), "usage.json")
_migrate_lock = threading.Lock()
_migrated = False


def _zero() -> dict:
    return {f: 0 for f in _FIELDS}


def _ensure_migrated() -> None:
    """One-time import of the legacy usage.json into the usage table."""
    global _migrated
    with _migrate_lock:
        if _migrated:
            return
        _migrated = True
        if not os.path.exists(_LEGACY_JSON):
            return
        try:
            with open(_LEGACY_JSON) as f:
                raw = json.load(f)
        except Exception:
            return
        # Pre-per-model buckets weren't attributed to a model; file them under 'legacy'.
        rows = [
            (day, "legacy", *[int(b.get(f, 0) or 0) for f in _FIELDS])
            for day, b in raw.items()
            if isinstance(b, dict)
        ]
        if rows:
            db.write(lambda c: c.executemany(
                "INSERT OR REPLACE INTO usage(day, model, input, output, cache_read, cache_write, reasoning) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            ))
        os.replace(_LEGACY_JSON, _LEGACY_JSON + ".bak")


def add(usage: dict, model) -> dict:
    """Add a turn's usage into today's bucket for `model` and persist. Returns that
    model's today total. `model` is a {provider,model} dict or a 'provider/model' string."""
    mkey = _model_key(model)
    if not usage:
        return today(model)
    _ensure_migrated()
    day = date.today().isoformat()
    vals = [int(usage.get(f, 0) or 0) for f in _FIELDS]
    db.write(lambda c: c.execute(
        "INSERT INTO usage(day, model, input, output, cache_read, cache_write, reasoning) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(day, model) DO UPDATE SET "
        "input = input + excluded.input, output = output + excluded.output, "
        "cache_read = cache_read + excluded.cache_read, "
        "cache_write = cache_write + excluded.cache_write, "
        "reasoning = reasoning + excluded.reasoning",
        (day, mkey, *vals),
    ))
    return today(model)


def today(model) -> dict:
    """Today's totals for `model` (zeros if nothing recorded yet)."""
    _ensure_migrated()
    day = date.today().isoformat()
    rows = db.query(
        "SELECT input, output, cache_read, cache_write, reasoning FROM usage "
        "WHERE day = ? AND model = ?",
        (day, _model_key(model)),
    )
    if not rows:
        return _zero()
    r = rows[0]
    return {f: r[f] for f in _FIELDS}
