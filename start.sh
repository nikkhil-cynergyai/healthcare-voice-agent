#!/bin/bash
# Healthcare Voice Agent — RunPod GPU Startup Script
# Usage: /workspace/startup.sh
# Required env vars in RunPod UI:
#   NGROK_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
#   TWILIO_PHONE_NUMBER, MY_PHONE_NUMBER,
#   ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

echo "================================"
echo "Healthcare Voice Agent - RunPod"
echo "================================"

# ── Step 1: System packages ──
echo "[1/7] System dependencies..."
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq curl wget tmux zstd sox libsox-fmt-all > /dev/null 2>&1

# ngrok
if ! command -v ngrok &> /dev/null; then
    echo "      Installing ngrok..."
    curl -sL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar xz -C /tmp
    mv /tmp/ngrok /usr/local/bin/
fi

# Piper voice model
mkdir -p /workspace/piper_models
if [ ! -f "/workspace/piper_models/en_US-lessac-high.onnx" ]; then
    echo "      Downloading Piper model..."
    curl -sL -o /workspace/piper_models/en_US-lessac-high.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx"
    curl -sL -o /workspace/piper_models/en_US-lessac-high.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx.json"
fi
echo "      Done"

# ── Step 2: Ollama ──
echo "[2/7] Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "      Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh > /dev/null 2>&1
fi
echo "      Ready"

# ── Step 3: Python venv ──
echo "[3/7] Python environment..."
if [ ! -d "/workspace/venv" ]; then
    echo "      Creating venv..."
    python3 -m venv /workspace/venv
    source /workspace/venv/bin/activate
    pip install -q fastapi uvicorn faster-whisper piper-tts \
        numpy soundfile requests python-dotenv twilio websockets \
        python-multipart onnxruntime-gpu elevenlabs
else
    source /workspace/venv/bin/activate
    pip install -q python-multipart onnxruntime-gpu elevenlabs > /dev/null 2>&1 || true
fi
echo "      Ready"

# ── Step 4: Code ──
echo "[4/7] Pulling latest code..."
cd /workspace/healthcare-voice-agent
git pull origin main 2>&1 | tail -1
mkdir -p audio/output audio/input

# ── Step 5: Ollama + qwen3:8b ──
echo "[5/7] Starting Ollama (GPU)..."
tmux kill-session -t ollama 2>/dev/null || true
tmux new-session -d -s ollama 'ollama serve'
sleep 8

for i in 1 2 3 4 5; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "      Ollama ready"
        break
    fi
    sleep 3
done

if ! ollama list 2>/dev/null | grep -q "qwen3:8b"; then
    echo "      Pulling qwen3:8b (~5.2GB)..."
    ollama pull qwen3:8b
fi
echo "      qwen3:8b ready"

# ── Step 6: ngrok ──
echo "[6/7] Starting ngrok..."
if [ -z "$NGROK_TOKEN" ]; then
    echo "      WARNING: NGROK_TOKEN not set in RunPod env vars"
    BASE_URL="http://localhost:8000"
else
    ngrok config add-authtoken "$NGROK_TOKEN" > /dev/null 2>&1 || true
    tmux kill-session -t ngrok 2>/dev/null || true
    tmux new-session -d -s ngrok "ngrok http 8000"
    sleep 8

    NGROK_URL=""
    for i in 1 2 3; do
        NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])" 2>/dev/null || echo "")
        if [ -n "$NGROK_URL" ]; then
            break
        fi
        echo "      Waiting... ($i/3)"
        sleep 4
    done

    if [ -n "$NGROK_URL" ]; then
        BASE_URL=$NGROK_URL
        # Update .env with new URL
        if [ -f .env ]; then
            sed -i "s|BASE_URL=.*|BASE_URL=$NGROK_URL|" .env
        else
            echo "BASE_URL=$NGROK_URL" > .env
        fi
        echo "================================"
        echo "ngrok URL : $NGROK_URL"
        echo "Twilio    : $NGROK_URL/voice"
        echo "================================"
        echo "ACTION: Update Twilio webhook!"
        echo "================================"
    else
        echo "      ngrok URL not found — using localhost"
        BASE_URL="http://localhost:8000"
    fi
fi

export BASE_URL

# ── Step 7: FastAPI server ──
echo "[7/7] Starting server..."
cd /workspace/healthcare-voice-agent
uvicorn src.main:app --host 0.0.0.0 --port 8000