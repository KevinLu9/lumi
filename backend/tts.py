from kokoro_onnx import Kokoro
from scipy import signal
import sounddevice as sd
import numpy as np
import pyrubberband as pyrb
import threading
import queue
import time
import os

TAIL_SILENCE_SEC = 0.4  # seconds of silence padded after each sentence so words don't get clipped

MODEL_PATH = os.path.join(os.path.dirname(__file__), "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(os.path.dirname(__file__), "voices-v1.0.bin")

# Voice settings
# VOICE = "af_bella"   # af_bella 1x speed, am_michael 1.2x speed
#                      # bf_emma, bf_isabella, bm_george, bm_lewis
#                      # https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
# SPEED = 1.1
LANG  = "en-us"

# Post-processing — set POSTPROCESS = False to bypass entirely
POSTPROCESS = False

# Original Bella
VOICE, SPEED, PITCH_SHIFT, BASS_BOOST_DB, TREBLE_DB, REVERB_MIX = "af_bella", 1.1, 0, 0, 0, 0
# "High Pitched" Bella
# VOICE, SPEED, PITCH_SHIFT, BASS_BOOST_DB, TREBLE_DB, REVERB_MIX = "af_bella", 1.1, 1, 0, 0, 0
# "Deep" Michael
# VOICE, SPEED, PITCH_SHIFT, BASS_BOOST_DB, TREBLE_DB, REVERB_MIX = "am_michael", 1.2, -1.5, 0, 0, 0
# "Warm" Michael
# VOICE, SPEED, PITCH_SHIFT, BASS_BOOST_DB, TREBLE_DB, REVERB_MIX = "am_michael", 1.2, 0, 2, 0, 0

# PITCH_SHIFT   = -2    # semitones: +2 = higher/lighter, -2 = deeper, 0 = off
# BASS_BOOST_DB = 2    # dB boost below ~300Hz: +3 = warmer, -3 = thinner
# TREBLE_DB     = 0.0    # dB boost above ~3kHz:  +3 = crisper, -3 = softer
# REVERB_MIX    = 0.0    # 0.0 = dry, 0.15 = subtle room, 0.4 = spacious

_kokoro: Kokoro | None = None
_gen_queue: queue.Queue = queue.Queue()
_play_queue: queue.Queue = queue.Queue()

# Monotonically increasing; items tagged with an old generation are discarded.
_generation = 0
_generation_lock = threading.Lock()
_playing = threading.Event()

# Audio sink. When _send_audio is set, TTS runs in "web" mode: generated PCM is shipped
# to the browser instead of played locally via sounddevice. _send_control delivers JSON
# control messages (flush on interrupt, chime tone).
_send_audio = None        # callable(pcm_bytes: bytes, sample_rate: int)
_send_control = None      # callable(message: dict)
_web_playing_until = 0.0  # monotonic time the browser is estimated to finish playing
_web_lock = threading.Lock()


def set_audio_sink(send_audio=None, send_control=None) -> None:
    """Switch TTS to web mode by providing browser-bound senders. Call with no args to
    revert to local sounddevice playback (used by the CLI)."""
    global _send_audio, _send_control
    _send_audio = send_audio
    _send_control = send_control


def notify_playback_ended() -> None:
    """Browser reports its audio buffer has drained — clear the speaking estimate."""
    global _web_playing_until
    with _web_lock:
        _web_playing_until = 0.0


def _shelf_filter(samples: np.ndarray, sr: int, cutoff: float, gain_db: float, high: bool) -> np.ndarray:
    if gain_db == 0.0:
        return samples
    gain = 10 ** (gain_db / 20)
    sos = signal.butter(2, cutoff / (sr / 2), btype="high" if high else "low", output="sos")
    filtered = signal.sosfilt(sos, samples)
    return samples + (gain - 1) * filtered


def _reverb(samples: np.ndarray, sr: int, mix: float) -> np.ndarray:
    if mix == 0.0:
        return samples
    delays = [int(sr * d) for d in (0.03, 0.05, 0.08, 0.13)]
    decays = [0.5, 0.35, 0.25, 0.15]
    wet = np.zeros_like(samples)
    for delay, decay in zip(delays, decays):
        padded = np.concatenate([np.zeros(delay), samples])[:len(samples)]
        wet += padded * decay
    return samples * (1 - mix) + wet * mix


def _postprocess(samples: np.ndarray, sr: int) -> np.ndarray:
    if PITCH_SHIFT != 0.0:
        samples = pyrb.pitch_shift(samples, sr, PITCH_SHIFT)
    samples = _shelf_filter(samples, sr, cutoff=300,  gain_db=BASS_BOOST_DB, high=False)
    samples = _shelf_filter(samples, sr, cutoff=3000, gain_db=TREBLE_DB,     high=True)
    samples = _reverb(samples, sr, REVERB_MIX)
    return np.clip(samples, -1.0, 1.0)


def _generator():
    while True:
        text, voice, speed, lang, gen = _gen_queue.get()
        if gen != _generation:
            continue
        try:
            samples, sample_rate = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
        except Exception:
            continue
        if gen != _generation:
            continue
        if POSTPROCESS:
            samples = _postprocess(samples, sample_rate)
        padding = np.zeros(int(sample_rate * TAIL_SILENCE_SEC), dtype=samples.dtype)
        _play_queue.put((np.concatenate([samples, padding]), sample_rate, gen))


def is_playing() -> bool:
    if _send_audio is not None:
        return time.monotonic() < _web_playing_until
    return _playing.is_set()


def wait_done():
    """Block until all queued audio has finished playing."""
    time.sleep(0.05)  # let the first item reach the gen queue
    while is_playing() or not _gen_queue.empty() or not _play_queue.empty():
        time.sleep(0.05)


def _web_play(samples: np.ndarray, sample_rate: int):
    """Ship a PCM chunk to the browser and extend the playback-time estimate."""
    global _web_playing_until
    duration = len(samples) / sample_rate
    _send_audio(samples.astype(np.float32).tobytes(), sample_rate)
    now = time.monotonic()
    with _web_lock:
        start_at = max(now, _web_playing_until)
        _web_playing_until = start_at + duration


def _player():
    while True:
        samples, sample_rate, gen = _play_queue.get()
        if gen != _generation:
            continue
        if _send_audio is not None:
            _web_play(samples, sample_rate)
        else:
            _playing.set()
            sd.play(samples, sample_rate, latency="high")
            sd.wait()
            _playing.clear()


def chime():
    """Play a short activation tone directly, bypassing the TTS queue."""
    if _send_control is not None:
        _send_control({"type": "chime"})
        return
    sr = 44100
    t = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
    tone = np.sin(2 * np.pi * 880 * t).astype(np.float32)
    fade = np.linspace(1.0, 0.0, len(tone)) ** 2
    sd.play(tone * fade, sr)


def interrupt():
    """Stop current playback and discard all queued audio."""
    global _generation, _web_playing_until
    with _generation_lock:
        _generation += 1
    if _send_audio is not None:
        with _web_lock:
            _web_playing_until = 0.0
        if _send_control is not None:
            _send_control({"type": "flush"})
    else:
        sd.stop()
    for q in (_gen_queue, _play_queue):
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                break


def load():
    global _kokoro
    print("Loading TTS model...")
    _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    threading.Thread(target=_generator, daemon=True).start()
    threading.Thread(target=_player, daemon=True).start()


def _chunk(text: str, max_chars: int = 200) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        chunks.append(current)
    return chunks


def speak(text: str, voice: str = VOICE, speed: float = SPEED, lang: str = LANG):
    if not _kokoro:
        raise RuntimeError("Call tts.load() before tts.speak()")
    for chunk in _chunk(text):
        _gen_queue.put((chunk, voice, speed, lang, _generation))
