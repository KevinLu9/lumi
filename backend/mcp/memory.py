"""Personal memory — two tiers so Lumi knows the user without bloating the prompt.

  * Permanent tier: a SMALL set of core, identity-level facts (name, location, a
    few standing preferences). Every fact here is injected into the system prompt
    on every turn via `memory_block()`, so Lumi always knows them. Kept small on
    purpose to limit prompt size.
  * Long-term tier: the large store for everything else (situational details,
    context, one-off facts). NOT injected; Lumi pulls relevant items in on demand
    by calling `memory_recall`. The prompt only carries a count + nudge so the
    model knows the store exists.

Both tiers persist to one JSON file (like the scheduler's job store) so they
survive restarts and a `reset_chat`.
"""

import json
import os
import threading
import time
import uuid

from ._registry import Registry
from . import _memvec
from ._embeddings import embed as _embed, available as _embed_available

registry = Registry()
DESCRIPTION = "Remember personal facts about the user: a small always-on core plus a searchable long-term store."

_STORE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lumi_memory.json")
_lock = threading.Lock()

# Semantic-recall tuning (cosine distance; smaller = more similar). Calibrated for
# gemini-embedding-001, whose distances cluster fairly high:
#   _MAX_DISTANCE  — absolute cap; beyond this nothing is "relevant" (a query that
#                    matches nothing returns empty and falls back to keyword search).
#   _REL_MARGIN    — only keep extra hits within this much of the best hit, so a
#                    clearly-best match collapses to just itself instead of dragging
#                    in the weakly-related tail.
_RECALL_K = 5
_MAX_DISTANCE = 0.40
_REL_MARGIN = 0.07

# Two tiers, each: key -> {"fact": str, "created_at": float}
_memories: dict[str, dict] = {"permanent": {}, "longterm": {}}
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    if not os.path.exists(_STORE):
        return
    try:
        with open(_STORE) as f:
            data = json.load(f)
    except Exception:
        return  # corrupt/legacy file — start empty rather than crash
    if isinstance(data, dict) and ("permanent" in data or "longterm" in data):
        _memories["permanent"].update(data.get("permanent", {}))
        _memories["longterm"].update(data.get("longterm", {}))
    elif isinstance(data, dict):
        # Migrate an old single-tier store (flat key -> {fact,...}) into long-term.
        _memories["longterm"].update(data)


def _save() -> None:
    tmp = _STORE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_memories, f, indent=2)
    os.replace(tmp, _STORE)


# --- vector index sync (semantic recall) ------------------------------------
# The sqlite-vec index is a derived cache of long-term embeddings. All of these
# are best-effort: if embeddings or sqlite-vec are unavailable they no-op, and
# recall falls back to keyword matching. They run outside _lock (embedding is a
# network call) and never raise.

def _reindex(key: str, fact: str) -> None:
    """Embed one long-term fact and upsert it into the vector index."""
    if not (_memvec.AVAILABLE and _embed_available()):
        return
    vec = _embed(fact)
    if vec:
        _memvec.upsert(key, vec)


def _ensure_index(longterm: dict) -> None:
    """Rebuild the index from the long-term store if it's missing or out of sync
    (e.g. first run with a pre-existing store, or the .db was deleted)."""
    if not (_memvec.AVAILABLE and _embed_available()):
        return
    if _memvec.count() == len(longterm):
        return
    _memvec.clear()
    for k, v in longterm.items():
        vec = _embed(v["fact"])
        if vec:
            _memvec.upsert(k, vec)


@registry.tool
def memory_save(fact: str, key: str = "", permanent: bool = False) -> str:
    """Save a personal fact or preference about the user to memory.

    Choose the tier deliberately:
      * Long-term (default, permanent=False): use for MOST things — situational
        details, context, one-off facts, anything that isn't core identity. These
        are searched on demand via memory_recall.
      * Permanent (permanent=True): reserve for a SMALL handful of core,
        identity-level facts that should always be in mind — the user's name,
        where they live, a few standing preferences. Keep this tier small; don't
        promote situational details here.

    Args:
        fact: The thing to remember, as a short standalone sentence, e.g.
            'The user is vegetarian.' or "The user's manager is named Sarah."
        key: Optional short label to file it under (e.g. 'diet' or 'name'). Reuse
            an existing key to update that memory; omit it to auto-generate one.
        permanent: True to store in the small always-remembered permanent tier;
            default False stores it in long-term memory.
    """
    fact = fact.strip()
    if not fact:
        return "Nothing to remember — the fact was empty."
    tier = "permanent" if permanent else "longterm"
    with _lock:
        _load()
        k = key.strip() or uuid.uuid4().hex[:8]
        # A key is unique across tiers: if it already exists elsewhere, move it.
        other = "longterm" if permanent else "permanent"
        _memories[other].pop(k, None)
        existed = k in _memories[tier]
        _memories[tier][k] = {"fact": fact, "created_at": time.time()}
        _save()
    # Keep the vector index in step (outside the lock — embedding is a network call).
    if permanent:
        _memvec.delete(k)  # no-op unless it was previously long-term
    else:
        _reindex(k, fact)
    label = "permanent" if permanent else "long-term"
    return f"{'Updated' if existed else 'Saved'} {label} memory ({k}): {fact}"


@registry.tool
def memory_recall(query: str = "") -> str:
    """Search the user's long-term memory and recall matching facts. Use this when
    a question might depend on something the user told you earlier that isn't in
    your always-on context.

    Args:
        query: What to look for, in natural language — recall matches by meaning,
            not just keywords (e.g. 'what does the user eat?' finds a saved fact
            that they're vegetarian). Leave empty to list everything remembered.
    """
    with _lock:
        _load()
        longterm = dict(_memories["longterm"])
        permanent = dict(_memories["permanent"])
    if not longterm and not permanent:
        return "I don't have anything saved about you yet."

    q = query.strip()
    if not q:
        # List everything, long-term first, oldest to newest.
        items = sorted(list(longterm.items()) + list(permanent.items()),
                       key=lambda kv: kv[1].get("created_at", 0))
        return "; ".join(f"{v['fact']} ({k})" for k, v in items)

    # Semantic path: embed the query and search the long-term vector index.
    _ensure_index(longterm)
    if _memvec.AVAILABLE and _embed_available():
        qv = _embed(q, query=True)
        if qv:
            hits = [(k, d) for k, d in _memvec.search(qv, _RECALL_K)
                    if d <= _MAX_DISTANCE and k in longterm]
            if hits:
                best = hits[0][1]  # search returns nearest first
                hits = [(k, d) for k, d in hits if d <= best + _REL_MARGIN]
                return "; ".join(f"{longterm[k]['fact']} ({k})" for k, _ in hits)

    # Fallback: keyword/substring scan across both tiers.
    ql = q.lower()
    items = [(k, v) for k, v in (list(longterm.items()) + list(permanent.items()))
             if ql in v["fact"].lower() or ql in k.lower()]
    if not items:
        return f"I don't have anything saved about '{query}'."
    items.sort(key=lambda kv: kv[1].get("created_at", 0))
    return "; ".join(f"{v['fact']} ({k})" for k, v in items)


@registry.tool
def memory_forget(key: str) -> str:
    """Forget a saved memory by its key (label), from either tier.

    Args:
        key: The key of the memory to remove (shown in parentheses by
            memory_recall / memory_save).
    """
    key = key.strip()
    with _lock:
        _load()
        removed = _memories["permanent"].pop(key, None) or _memories["longterm"].pop(key, None)
        if removed is not None:
            _save()
    if removed is None:
        return f"No memory filed under '{key}'."
    _memvec.delete(key)  # drop its vector too (no-op if it had none)
    return f"Forgot memory ({key}): {removed['fact']}"


def memory_block() -> str:
    """System-prompt section: the small permanent tier (always in mind) plus a
    one-line nudge that long-term memory exists. Injected by llm.py. Returns ''
    when there is nothing at all."""
    with _lock:
        _load()
        perm = [v["fact"] for v in sorted(_memories["permanent"].values(),
                                          key=lambda v: v.get("created_at", 0))]
        longterm_count = len(_memories["longterm"])
    if not perm and not longterm_count:
        return ""
    parts = ["# What you know about the user"]
    if perm:
        parts.append("Core facts (always keep in mind):\n" + "\n".join(f"- {f}" for f in perm))
    if longterm_count:
        parts.append(
            f"You also have {longterm_count} long-term memory item(s). When a question "
            "might depend on something the user told you before, call "
            "memory_recall(query) to search them."
        )
    parts.append(
        "To remember something new, call memory_save (permanent=True only for a few "
        "core identity facts; otherwise it goes to long-term)."
    )
    return "\n".join(parts)


if __name__ == "__main__":
    print("vector index available:", _memvec.AVAILABLE and _embed_available())
    print(memory_save("The user's name is Kevin.", "name", permanent=True))
    print(memory_save("The user lives in Sydney.", "location", permanent=True))
    print(memory_save("The user is vegetarian.", "diet"))
    print(memory_save("The user has a golden retriever named Rex.", "pet"))
    print(memory_save("The user is debugging a WebSocket audio bug today.", "task_today"))
    # Semantic recall: none of these queries share keywords with the stored facts.
    print("\nrecall 'what does the user eat?':", memory_recall("what does the user eat?"))
    print("recall 'tell me about their animals':", memory_recall("tell me about their animals"))
    print("recall 'what are they working on?':", memory_recall("what are they working on?"))
    print("\nblock (system prompt):\n" + memory_block())
    for k in ("name", "location", "diet", "pet", "task_today"):
        print(memory_forget(k))
