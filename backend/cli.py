"""Legacy terminal mode — runs Lumi with local microphone + speakers (no web UI).

    python -m backend.cli

Audio plays through sounddevice and the mic is captured locally; transcriber status
lines still render to stdout. The web app (backend.app) is the primary interface.
"""

import sys

from . import assistant


def main() -> None:
    # Local sounddevice playback is the default sink (no set_audio_sink call).
    assistant.start_voice_loop(source="local")

    print("Speak or type to chat (Ctrl+C to quit):")
    for line in sys.stdin:
        text = line.strip()
        if text:
            assistant.send_text(text)


if __name__ == "__main__":
    main()
