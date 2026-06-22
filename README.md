# Lumi

A futuristic voice assistant with a Svelte web UI and a FastAPI backend.

- **Speech-to-text:** faster-whisper (`tiny.en`) + Silero VAD
- **Text-to-speech:** Kokoro (ONNX) — Lumi's voice
- **LLM:** Gemini or Groq, with tool-calling (time, weather, calculator, timers,
  browser control, Spotify)
- **UI:** a reactive orb flanked by HUD panels (system/controls + tool activity /
  now-playing)

Audio runs in the browser (mic capture + playback) but the Whisper and Kokoro models run
on the backend; raw PCM is streamed over a WebSocket. Live status, transcript, and
tool-call events stream over SSE; control actions go over REST.

## Architecture

```
backend/            FastAPI app + the Python voice pipeline
  app.py            SSE (/api/stream), REST (/api/*), WebSocket (/ws/audio), static serving
  assistant.py      orchestrator: wake-word, debounce, active-session state machine
  events.py         thread-safe pub/sub event bus feeding SSE
  transcriber.py    Whisper + Silero VAD (web mode: fed audio frames via feed_audio)
  tts.py            Kokoro TTS (pluggable sink: browser PCM or local sounddevice)
  llm.py            Gemini/Groq + tool-calling (emits tool_call events)
  cli.py            legacy local-mic terminal mode (python -m backend.cli)
  mcp/              tool implementations + registry
src/                Svelte + Vite frontend
  lib/audio/        mic worklet, Web Audio player, /ws/audio bridge
  lib/components/   Orb, Transcript, panels, etc.
```

## Setup

### 1. Python environment

```
python3 -m venv .venv
source .venv/bin/activate
npm run install:py          # = pip install -r requirements.txt
```

Install ffmpeg if you don't have it (`brew install ffmpeg` on macOS).

### 2. Download the Kokoro voice model into `backend/`

```
curl -L -o backend/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
curl -L -o backend/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
```

### 3. Frontend dependencies

```
npm install
```

### 4. Environment variables (`.env` at the repo root)

```
LLM_PROVIDER=gemini            # or groq
GEMINI_API_KEY=...             # or GROQ_API_KEY=...
# optional Spotify:
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
```

If using Spotify, authenticate once: `python -m backend.mcp.spotify_auth`.

## Run

```
npm run dev
```

This starts the FastAPI backend (`:8000`) and the Vite dev server (`:5173`) together.
Open **http://localhost:5173**, grant microphone access, and say “hey lumi” — or type in
the input box. The orb reacts to Lumi's state; tool calls and now-playing show in the
right panel.

### Accessing from another device on your network

Both servers now bind to `0.0.0.0`, so from another device on the same LAN you can open
`http://<your-computer-ip>:5173`. Typed chat works immediately.

**The microphone, however, needs a secure context** — browsers only allow mic access on
`localhost` or over `https`. Over plain `http://<ip>:5173` the mic button will tell you it
is blocked. To use voice from another device, start with https (self-signed cert):

```
npm run dev:lan        # serves the frontend over https with a self-signed cert
```

Then open `https://<your-computer-ip>:5173` and accept the certificate warning. (Or use
the production build behind a real https reverse proxy.)

### Production

```
npm run build      # emits dist/
npm start          # FastAPI serves dist/ + the API at 0.0.0.0:8000
```

### Headless terminal mode

```
python -m backend.cli
```
