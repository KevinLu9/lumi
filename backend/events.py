"""Thread-safe pub/sub event bus bridging worker threads to asyncio SSE consumers.

Worker threads (transcriber, tts, llm, assistant) call the synchronous `emit()` from
any thread; events are fanned out to every subscribed asyncio.Queue via the captured
event loop. The SSE endpoint subscribes, drains its queue, and serializes to the client.
"""

import asyncio
import threading
from typing import Any

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: set[asyncio.Queue] = set()
_lock = threading.Lock()

# Latest snapshot so /api/state and freshly-connected SSE clients can hydrate.
current_state: dict[str, Any] = {
    "status": "idle",
    "active": False,
    "tts_playing": False,
    # list of {"role": "user"|"lumi", "text": str} and
    # {"role": "tool", "name": str, "args": dict, "result": str}, interleaved in order.
    "transcript": [],
    "now_playing": None,
    "active_tools": [],   # tool names currently loaded into the LLM context
}

# Cap transcript history kept in the snapshot so it doesn't grow unbounded.
_MAX_TRANSCRIPT = 100


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Capture the running asyncio loop (call once at FastAPI startup)."""
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    with _lock:
        _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    with _lock:
        _subscribers.discard(q)


def _update_state(event_type: str, data: dict) -> None:
    if event_type == "status":
        current_state["status"] = data.get("status", current_state["status"])
    elif event_type == "active_state":
        current_state["active"] = data.get("active", current_state["active"])
        current_state["tts_playing"] = data.get("tts_playing", current_state["tts_playing"])
    elif event_type == "user_transcript":
        current_state["transcript"].append({"role": "user", "text": data.get("text", "")})
        del current_state["transcript"][:-_MAX_TRANSCRIPT]
    elif event_type == "lumi_message":
        item = {"role": "lumi", "text": data.get("text", "")}
        if data.get("usage"):
            item["usage"] = data["usage"]
        current_state["transcript"].append(item)
        del current_state["transcript"][:-_MAX_TRANSCRIPT]
    elif event_type == "tool_call":
        current_state["transcript"].append({
            "role": "tool",
            "name": data.get("name", ""),
            "args": data.get("args") or {},
            "result": data.get("result", ""),
        })
        del current_state["transcript"][:-_MAX_TRANSCRIPT]
    elif event_type == "chat_reset":
        current_state["transcript"] = []
    elif event_type == "tools_active":
        current_state["active_tools"] = data.get("names", current_state["active_tools"])
    elif event_type == "now_playing":
        current_state["now_playing"] = data.get("track")


def emit(event_type: str, **data: Any) -> None:
    """Emit an event to all subscribers. Safe to call from any thread."""
    _update_state(event_type, data)
    payload = {"type": event_type, **data}

    with _lock:
        queues = list(_subscribers)
    if not queues or _loop is None:
        return

    def _dispatch() -> None:
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    try:
        _loop.call_soon_threadsafe(_dispatch)
    except RuntimeError:
        # Loop not running (e.g. CLI mode without a server) — drop silently.
        pass
