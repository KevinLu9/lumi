"""FastAPI entry point for Lumi.

Transport split:
  - SSE  GET  /api/stream        live status / transcript / tool-call events
  - REST POST /api/message|...   discrete control actions
  - WS        /ws/audio          browser mic PCM up, Kokoro TTS PCM down

Audio frames on /ws/audio are raw little-endian: a 4-byte int32 sample rate followed by
float32 PCM samples. Mic frames from the browser are 16kHz mono float32 (no header).
"""

import asyncio
import os
import struct

import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import assistant, events, transcriber, tts
from .mcp.registry import TOOL_SCHEMAS

app = FastAPI(title="Lumi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Audio hub — bridges the (threaded) TTS player to connected browser sockets.
# ---------------------------------------------------------------------------
class AudioHub:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def add(self, ws: WebSocket) -> None:
        self._sockets.add(ws)

    def remove(self, ws: WebSocket) -> None:
        self._sockets.discard(ws)

    def send_audio(self, pcm_bytes: bytes, sample_rate: int) -> None:
        """Called from the TTS player thread."""
        header = struct.pack("<i", sample_rate)
        self._broadcast_bytes(header + pcm_bytes)

    def send_control(self, message: dict) -> None:
        """Called from TTS / assistant threads (flush, chime)."""
        if self._loop is None:
            return
        for ws in list(self._sockets):
            asyncio.run_coroutine_threadsafe(self._safe_json(ws, message), self._loop)

    def _broadcast_bytes(self, data: bytes) -> None:
        if self._loop is None:
            return
        for ws in list(self._sockets):
            asyncio.run_coroutine_threadsafe(self._safe_bytes(ws, data), self._loop)

    async def _safe_bytes(self, ws: WebSocket, data: bytes) -> None:
        try:
            await ws.send_bytes(data)
        except Exception:
            self.remove(ws)

    async def _safe_json(self, ws: WebSocket, message: dict) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            self.remove(ws)


audio_hub = AudioHub()


# ---------------------------------------------------------------------------
# Startup wiring
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def _startup() -> None:
    loop = asyncio.get_running_loop()
    events.set_loop(loop)
    audio_hub.bind_loop(loop)
    tts.set_audio_sink(send_audio=audio_hub.send_audio, send_control=audio_hub.send_control)
    # Load models + start capture loop off the event loop (blocking model loads).
    await asyncio.to_thread(assistant.start_voice_loop, "web")


# ---------------------------------------------------------------------------
# SSE event stream
# ---------------------------------------------------------------------------
@app.get("/api/stream")
async def stream(request: Request):
    queue = events.subscribe()

    async def gen():
        # Hydrate the new client with the current snapshot first.
        yield {"event": "message", "data": _json({"type": "snapshot", **events.current_state})}
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": "message", "data": _json(payload)}
        finally:
            events.unsubscribe(queue)

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# REST control
# ---------------------------------------------------------------------------
class Message(BaseModel):
    text: str


@app.get("/api/state")
def get_state():
    return events.current_state


@app.get("/api/tools")
def get_tools():
    return [
        {"name": s["function"]["name"], "description": s["function"]["description"]}
        for s in TOOL_SCHEMAS
    ]


@app.post("/api/message")
def post_message(msg: Message):
    assistant.send_text(msg.text)
    return {"ok": True}


@app.post("/api/interrupt")
def post_interrupt():
    assistant.interrupt()
    return {"ok": True}


@app.post("/api/reset")
def post_reset():
    assistant.reset()
    return {"ok": True}


@app.post("/api/activate")
def post_activate():
    assistant.activate()
    return {"ok": True}


@app.post("/api/deactivate")
def post_deactivate():
    assistant.deactivate()
    return {"ok": True}


@app.get("/api/spotify/now-playing")
def spotify_now_playing():
    if not os.environ.get("SPOTIFY_CLIENT_ID"):
        return JSONResponse({"configured": False, "track": None})
    from .mcp import spotify
    track = spotify.spotify_now_playing()
    events.emit("now_playing", track=track)
    return {"configured": True, "track": track}


# ---------------------------------------------------------------------------
# WebSocket audio
# ---------------------------------------------------------------------------
@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    await ws.accept()
    audio_hub.add(ws)
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if (data := msg.get("bytes")) is not None:
                frame = np.frombuffer(data, dtype=np.float32)
                if frame.size:
                    transcriber.feed_audio(frame.copy())
            elif (text := msg.get("text")) is not None:
                import json
                try:
                    payload = json.loads(text)
                except ValueError:
                    continue
                if payload.get("type") == "playback_ended":
                    tts.notify_playback_ended()
    except WebSocketDisconnect:
        pass
    finally:
        audio_hub.remove(ws)


# ---------------------------------------------------------------------------
# Static frontend (production: `npm run build` emits dist/)
# ---------------------------------------------------------------------------
_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


def _json(obj) -> str:
    import json
    return json.dumps(obj)
