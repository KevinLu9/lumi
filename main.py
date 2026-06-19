import tts
import llm
import transcriber
import threading
import re
import sys

YOU_COLOR  = "\033[36m"   # cyan
RESET      = "\033[0m"

VOICE_DEBOUNCE_SEC = 4  # seconds of silence before flushing accumulated speech to Lumi
ACTIVE_TIMEOUT_SEC = 15   # seconds of silence before returning to wake-word mode

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
    transcriber.set_status("💤 say 'hey lumi'...")


def _activate():
    global _active, _active_timer
    with _active_lock:
        _active = True
    if _active_timer:
        _active_timer.cancel()
    _active_timer = threading.Timer(ACTIVE_TIMEOUT_SEC, _deactivate)
    _active_timer.start()
    transcriber.set_vad_status_enabled(True)
    transcriber.set_status("🎤 listening...")
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


def _run_lumi(text: str):
    # Suspend the idle timeout while Lumi is thinking and speaking.
    with _active_lock:
        if _active_timer:
            _active_timer.cancel()

    sys.stdout.write(f"\r\033[K{YOU_COLOR}You:{RESET} {text}\n")
    sys.stdout.write("\r\033[K💭 Lumi is thinking...")
    sys.stdout.flush()
    llm.ask(text, on_sentence=tts.speak)
    # LLM done streaming; pin the speaking status while TTS plays out
    transcriber.pin_status("🔊 Lumi is speaking... say 'hold on' to interrupt")
    tts.wait_done()
    transcriber.unpin_status()
    _reset_active_timer()
    with _active_lock:
        still_active = _active
    transcriber.set_status("🎤 listening..." if still_active else "💤 say 'hey lumi'...")


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
            transcriber.set_status("🎤 listening...")
        return

    lower = text.lower()
    wake_match = WAKE_PATTERN.search(lower)

    with _active_lock:
        currently_active = _active

    if not currently_active:
        if not wake_match:
            transcriber.set_status(f"💤 say 'hey lumi'... heard: \"{text}\"")
            return
        _activate()
        remainder = lower[wake_match.end():].strip().strip(".,!?")
        if remainder:
            _send_to_lumi(remainder)
        return

    if CANCEL_PATTERN.search(text):
        _interrupt_lumi()
        tts.speak("Okay, bye!")
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


def on_type_transcript(text: str):
    _send_to_lumi(text)


tts.load()
llm.load()

from mcp.tools import register_timer_callback, register_clear_history_callback
register_timer_callback(lambda label: tts.speak(f"Timer done: {label}"))
register_clear_history_callback(llm.clear_history)

threading.Thread(
    target=transcriber.start,
    args=(on_voice_transcript,),
    kwargs={"on_speech_start": on_speech_start, "is_tts_playing": tts.is_playing},
    daemon=True,
).start()

print("Speak or type to chat (Ctrl+C to quit):")
transcriber.set_status("💤 say 'hey lumi'...")

for line in sys.stdin:
    text = line.strip()
    if text:
        on_type_transcript(text)
