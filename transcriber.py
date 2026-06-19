from faster_whisper import WhisperModel
from collections import deque
from typing import Callable
import sounddevice as sd
import numpy as np
import queue
import threading
import sys
import torch

SAMPLE_RATE = 16000        # Hz — Whisper and Silero VAD both expect 16kHz mono
BLOCK_SAMPLES = 512        # audio callback chunk size (~32ms at 16kHz)
PRE_ROLL_CHUNKS = 3        # chunks captured before VAD "start" to avoid clipping word onset (~96ms)
MAX_SEGMENT_SECONDS = 12   # force-flush a speech segment if it runs this long without silence
NO_SPEECH_THRESHOLD = 0.6  # Whisper segment is discarded if no_speech_prob exceeds this
MAX_SEGMENT_SAMPLES = SAMPLE_RATE * MAX_SEGMENT_SECONDS

WHISPER_VOCABULARY = """
Lumi
Spotify
nevermind
stop
close
that's all
pause
wait
hold on
play
pause
skip
next
previous
volume up
volume down
playlist
"""

HALLUCINATIONS = {
    "", ".", "you", "you.",
    "thank you.", "thank you for watching.",
    "thanks for watching.", "please subscribe.",
    "bye.", "bye!",
}

_stdout_lock = threading.Lock()
_context = ""
_vad_status_enabled = False
_pinned_status: str | None = None  # when set, VAD status calls redraw this instead


def set_vad_status_enabled(enabled: bool):
    global _vad_status_enabled
    _vad_status_enabled = enabled


def set_context(text: str):
    global _context
    _context = text


def set_status(msg: str):
    with _stdout_lock:
        display = _pinned_status if _pinned_status is not None else msg
        suffix = f" {_context}" if _context else ""
        sys.stdout.write(f"\r\033[K{display}{suffix}")
        sys.stdout.flush()


def pin_status(msg: str):
    """Pin a status line so that VAD updates cannot overwrite it."""
    global _pinned_status
    _pinned_status = msg
    with _stdout_lock:
        suffix = f" {_context}" if _context else ""
        sys.stdout.write(f"\r\033[K{msg}{suffix}")
        sys.stdout.flush()


def unpin_status():
    global _pinned_status
    _pinned_status = None


def start(
    on_transcript: Callable[[str, bool], None],
    on_speech_start: Callable[[], None] | None = None,
    is_tts_playing: Callable[[], bool] | None = None,
):
    print("Loading transcription models...")
    # cpu_threads=2 caps Whisper's OpenMP threads so it doesn't starve the audio output thread.
    whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)

    vad_model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        verbose=False,
    )
    vad = utils[3](vad_model, threshold=0.5, sampling_rate=SAMPLE_RATE, min_silence_duration_ms=300)

    audio_queue: queue.Queue = queue.Queue()
    transcribe_queue: queue.Queue = queue.Queue()

    def transcribe_worker():
        while True:
            audio, tts_was_active = transcribe_queue.get()
            if _vad_status_enabled:
                set_status("⏳ transcribing...")

            segments, _ = whisper_model.transcribe(
                audio,
                beam_size=1,
                language="en",
                vad_filter=True,
                initial_prompt=WHISPER_VOCABULARY,
            )

            parts = [s.text for s in segments if s.no_speech_prob < NO_SPEECH_THRESHOLD]
            text = "".join(parts).strip()

            if text and text.lower() not in HALLUCINATIONS:
                on_transcript(text, tts_was_active)
            if _vad_status_enabled:
                set_status("🎤 listening...")

    def audio_callback(indata, frames, time, status):
        audio_queue.put(indata.copy())

    def vad_loop():
        speech_buffer: list[np.ndarray] = []
        pre_roll: deque = deque(maxlen=PRE_ROLL_CHUNKS)
        speaking = False
        tts_active_at_start = False

        if _vad_status_enabled:
            set_status("🎤 listening...")

        while True:
            chunk = audio_queue.get()
            result = vad(torch.from_numpy(chunk.flatten()))

            if not speaking:
                pre_roll.append(chunk)
                if result and "start" in result:
                    speaking = True
                    tts_active_at_start = is_tts_playing() if is_tts_playing else False
                    if _vad_status_enabled:
                        set_status("🗣 recording...")
                    if on_speech_start:
                        on_speech_start()
                    speech_buffer = list(pre_roll)
            else:
                speech_buffer.append(chunk)
                total_samples = sum(len(c.flatten()) for c in speech_buffer)
                is_end = result and "end" in result
                is_max = total_samples >= MAX_SEGMENT_SAMPLES

                if is_end or is_max:
                    audio = np.concatenate([c.flatten() for c in speech_buffer])
                    transcribe_queue.put((audio, tts_active_at_start))
                    speech_buffer = []

                    if is_end:
                        speaking = False
                        tts_active_at_start = False
                        pre_roll.clear()
                        vad.reset_states()
                        if _vad_status_enabled:
                            set_status("🎤 listening...")

    threading.Thread(target=transcribe_worker, daemon=True).start()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=BLOCK_SAMPLES, callback=audio_callback):
        vad_loop()
