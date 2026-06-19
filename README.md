# lumi

AI Voice assistant connected to Home

## Environment

Runs with FastMCP
openai-whisper for Speech-To-Text (STT)
kokoro for Text-To-Speech (TTS)

## Setup

### 1. go into directory

```
cd server-python
```

### 2. Activate Python Environment

```
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install python dependencies

```
pip install -r requirements.txt
```

### 4. Install ffmpeg

```
# on Ubuntu or Debian
sudo apt update && sudo apt install ffmpeg

# on Arch Linux
sudo pacman -S ffmpeg

# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg

# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg

# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg
```

### 5. Download voice files for kokoro-onnx

```
curl -L -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

```
curl -L -o kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
```
