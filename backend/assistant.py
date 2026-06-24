"""Lumi orchestrator — wake-word, debounce, and active-session state machine.

This is the headless core: it wires the transcriber → LLM → TTS pipeline and broadcasts
state changes over the event bus. The web layer (app.py) drives it via the public control
functions; the CLI (cli.py) drives it through local audio. No stdin/stdout UI here.
"""

import re
import threading
import traceback

from . import tts
from . import llm
from . import transcriber
from . import events
from . import scheduler

VOICE_DEBOUNCE_SEC = 4   # seconds of silence before flushing accumulated speech to Lumi
ACTIVE_TIMEOUT_SEC = 15  # seconds of silence before returning to wake-word mode

debounce_lock = threading.Lock()
pending_text: list[str] = []
debounce_timer: threading.Timer | None = None

_lumi_thread: threading.Thread | None = None
_lumi_thread_lock = threading.Lock()

_active = False
_active_timer: threading.Timer | None = None
_active_lock = threading.Lock()

WAKE_PATTERN      = re.compile(r"(?:hey[\W_]*)?(?:lumi|lemmy|limi|loo me|Lamy|lay me|leamy|leave me|Lamey|leemee|lemie|levi|libby|leemi|loomy)", re.IGNORECASE)
CANCEL_PATTERN    = re.compile(r"^[\W_]*(?:nevermind|never\s+mind|stop|close|that's all|thats all)[\W_]*$", re.IGNORECASE)
INTERRUPT_PATTERN = re.compile(r"\b(?:pause|wait|hold on)\b", re.IGNORECASE)


def _emit_status(status: str) -> None:
    events.emit("status", status=status)


def _emit_active_state() -> None:
    events.emit("active_state", active=_active, tts_playing=tts.is_playing())


def _deactivate():
    global _active, _active_timer, debounce_timer
    with _active_lock:
        _active = False
        if _active_timer:
            _active_timer.cancel()
            _active_timer = None
    with debounce_lock:
        if debounce_timer:
            debounce_timer.cancel()
            debounce_timer = None
        pending_text.clear()
    transcriber.set_vad_status_enabled(False)
    transcriber.set_context("")
    _emit_status("idle")
    _emit_active_state()


def _activate():
    global _active, _active_timer
    with _active_lock:
        _active = True
    if _active_timer:
        _active_timer.cancel()
    _active_timer = threading.Timer(ACTIVE_TIMEOUT_SEC, _deactivate)
    _active_timer.start()
    transcriber.set_vad_status_enabled(True)
    _emit_status("listening")
    _emit_active_state()
    tts.chime()


def _reset_active_timer():
    global _active_timer
    if _active_timer:
        _active_timer.cancel()
    _active_timer = threading.Timer(ACTIVE_TIMEOUT_SEC, _deactivate)
    _active_timer.start()


def _interrupt_lumi():
    """Cancel any in-progress LLM stream and stop TTS playback."""
    llm.cancel()
    tts.interrupt()
    transcriber.unpin_status()
    with _lumi_thread_lock:
        t = _lumi_thread
    if t and t.is_alive():
        t.join(timeout=3)


def _on_sentence(sentence: str):
    events.emit("lumi_sentence", text=sentence)
    tts.speak(sentence)


def _run_lumi(text: str):
    # Suspend the idle timeout while Lumi is thinking and speaking.
    with _active_lock:
        if _active_timer:
            _active_timer.cancel()

    events.emit("user_transcript", text=text)
    _emit_status("thinking")
    try:
        llm.ask(text, on_sentence=_on_sentence)
        # LLM done streaming; pin the speaking status while TTS plays out.
        transcriber.pin_status("🔊 Lumi is speaking... say 'hold on' to interrupt")
        _emit_status("speaking")
        _emit_active_state()
        tts.wait_done()
    except Exception as e:
        # Surface the failure in the UI (an error card with a retry button) instead
        # of letting the worker thread die silently. `retry` carries the original
        # prompt so the frontend can re-send it.
        traceback.print_exc()
        events.emit("error", message=str(e) or e.__class__.__name__, retry=text)
    finally:
        transcriber.unpin_status()
        _reset_active_timer()
        with _active_lock:
            still_active = _active
        _emit_status("listening" if still_active else "idle")
        _emit_active_state()


def _send_to_lumi(text: str):
    global _lumi_thread
    _interrupt_lumi()
    t = threading.Thread(target=_run_lumi, args=(text,), daemon=True)
    with _lumi_thread_lock:
        _lumi_thread = t
    t.start()


def _flush_pending():
    global debounce_timer
    with debounce_lock:
        text = " ".join(pending_text).strip()
        pending_text.clear()
        debounce_timer = None
    transcriber.set_context("")
    with _active_lock:
        still_active = _active
    if text and still_active:
        _send_to_lumi(text)


def on_speech_start():
    pass


def on_voice_transcript(text: str, tts_was_active: bool = False):
    global debounce_timer

    if tts_was_active:
        # While Lumi is speaking, only the interrupt word breaks through — everything else is discarded.
        if INTERRUPT_PATTERN.search(text):
            _interrupt_lumi()
            _reset_active_timer()
            _emit_status("listening")
        return

    lower = text.lower()
    wake_match = WAKE_PATTERN.search(lower)

    with _active_lock:
        currently_active = _active

    if not currently_active:
        if not wake_match:
            return
        _activate()
        remainder = lower[wake_match.end():].strip().strip(".,!?")
        if remainder:
            _send_to_lumi(remainder)
        return

    if CANCEL_PATTERN.search(text):
        _interrupt_lumi()
        _on_sentence("Okay, bye!")
        _deactivate()
        return

    _reset_active_timer()

    if wake_match:
        text = (text[:wake_match.start()] + text[wake_match.end():]).strip().strip(".,!?")
        if not text:
            return

    with debounce_lock:
        pending_text.append(text)
        transcriber.set_context(" ".join(pending_text))
        if debounce_timer:
            debounce_timer.cancel()
        debounce_timer = threading.Timer(VOICE_DEBOUNCE_SEC, _flush_pending)
        debounce_timer.start()


# ---------------------------------------------------------------------------
# Public control surface (used by app.py REST endpoints)
# ---------------------------------------------------------------------------

def send_text(text: str):
    """Handle a typed message from the UI — bypasses the wake word and activates."""
    global _active
    text = text.strip()
    if not text:
        return
    with _active_lock:
        was_active = _active
        _active = True
    if not was_active:
        transcriber.set_vad_status_enabled(True)
        _emit_active_state()
    _reset_active_timer()
    _send_to_lumi(text)


def interrupt():
    _interrupt_lumi()
    _reset_active_timer()
    _emit_status("listening")
    _emit_active_state()


def _clear_history():
    llm.clear_history()
    events.emit("chat_reset")


def reset():
    _clear_history()


def activate():
    _activate()


def deactivate():
    _interrupt_lumi()
    _deactivate()


def _on_timer(label: str, action: str = ""):
    # A timer with an action runs as a full Lumi turn (like a scheduled job) so Lumi can
    # load tools and carry it out, then speak. Without one it just announces.
    if action:
        send_text(action)
    else:
        events.emit("timer", label=label)
        _on_sentence(f"Timer done: {label}")


def start_voice_loop(source: str = "web"):
    """Load models, wire callbacks, and start the capture loop in a background thread."""
    tts.load()
    llm.load()

    from .mcp.tools import register_timer_callback, register_clear_history_callback
    register_timer_callback(_on_timer)
    register_clear_history_callback(_clear_history)

    transcriber.set_state_callback(_emit_status)

    # Scheduled jobs drive a full Lumi turn (LLM + spoken response) at their cron time.
    scheduler.start(action=send_text)

    threading.Thread(
        target=transcriber.start,
        args=(on_voice_transcript,),
        kwargs={
            "on_speech_start": on_speech_start,
            "is_tts_playing": tts.is_playing,
            "source": source,
        },
        daemon=True,
    ).start()

    _emit_status("idle")
