# Lumi

A futuristic voice assistant with a Svelte web UI and a FastAPI backend.

- **Speech-to-text:** faster-whisper (`tiny.en`) + Silero VAD
- **Text-to-speech:** Kokoro (ONNX) — Lumi's voice
- **LLM:** Gemini or Groq, with tool-calling (time, weather, calculator, timers,
  long-term memory, web search, Google Calendar/Gmail, browser control, Spotify)
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
# optional Tuya / Smart Life smart bulb (cloud control):
TUYA_DEVICE_ID=...
TUYA_API_REGION=...           # eu, us, cn, or in
TUYA_API_KEY=...
TUYA_API_SECRET=...
# optional web search (Tavily — free tier, no card):
TAVILY_API_KEY=...
# optional Google Calendar + Gmail (read-only):
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

If using Spotify, authenticate once: `python -m backend.mcp.spotify_auth`.

### Memory (built in, no setup)

Lumi remembers personal facts across sessions, in two tiers (both persisted to
`backend/lumi_memory.json`, gitignored; no API key needed):

- **Permanent** — a small core set (name, where you live, standing preferences)
  that is injected into Lumi's prompt every turn, so it always knows them.
- **Long-term** — the larger store for everything else. It isn't kept in the
  prompt; Lumi searches it on demand when a question calls for it. This keeps the
  prompt small while still letting Lumi recall details you mentioned long ago.

Say "remember that I'm vegetarian" (Lumi decides the tier, defaulting to
long-term and reserving permanent for core identity facts), ask "what do you
remember about me?", or say "forget that".

Long-term recall is **semantic** when a `GEMINI_API_KEY` is set: each long-term
fact is embedded (Gemini `gemini-embedding-001`) into a local sqlite-vec index
(`backend/lumi_memory.db`), so "what does the user eat?" finds a saved "I'm
vegetarian" even with no shared words. The JSON file stays the source of truth and
the index rebuilds from it automatically, so deleting the `.db` is safe. Without a
Gemini key (or if the vector store can't load), recall falls back to keyword
matching — everything still works, just less fuzzy.

### Web search (optional, Tavily)

Lets Lumi answer general-knowledge and current-events questions. Get a free key at
[tavily.com](https://app.tavily.com) (free tier: 1,000 searches/month, no credit
card) and set `TAVILY_API_KEY` in `.env`. Then ask things like "search the web for
…" or "who won the game last night?".

### Google Calendar + Gmail (optional)

Lumi can read your agenda, create events, and read/search your inbox (read-only).
Both share one Google login.

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a
   project, enable the **Google Calendar API** and **Gmail API**, and create an
   OAuth client of type **Desktop app**.
2. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
3. Authenticate once: `python -m backend.mcp.google_auth` (opens a browser).

Then ask "what's on my calendar today?", "schedule lunch at noon tomorrow", or
"do I have any new email?".

### Tuya / Smart Life smart bulb (optional)

Lumi can control a Tuya-based wifi bulb (e.g. paired in the **Smart Life** app) through the
**Tuya cloud** — the same path the Smart Life app uses, so it works even if your router has
WiFi AP/client isolation that blocks direct LAN access to the bulb. You need the bulb's
device ID plus your Tuya cloud API credentials — get them once like this:

1. Create a free account on the [Tuya IoT Platform](https://iot.tuya.com/), make a Cloud
   project, and link your Smart Life app account so the bulb appears.
2. `python -m tinytuya wizard` — writes `devices.json` (the **device ID**) and `tinytuya.json`
   (your cloud **API key**, **secret**, and **region**).
3. Put `TUYA_DEVICE_ID`, `TUYA_API_REGION`, `TUYA_API_KEY`, `TUYA_API_SECRET` into `.env`.

The bulb just needs to be online in the Smart Life app. Once configured, ask Lumi things
like "turn the light blue", "dim the light to 20%", or "warm white".

Lumi discovers **all** lights on your account automatically and can target them by name —
rename your bulbs in the Smart Life app (e.g. "desk lamp", "bedroom"), then say "turn the
desk lamp purple" or ask "what lights can you control?". With a single light you can leave
the name out.

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
