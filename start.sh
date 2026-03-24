#!/bin/bash
# Healthcare Voice Agent - RunPod Startup Script

echo "================================"
echo "Healthcare Voice Agent - RunPod"
echo "================================"

# ── Step 1: System dependencies ──
echo "[1/7] Installing system dependencies..."
apt-get update -qq > /dev/null 2>&1
apt-get install -y -qq curl wget tmux zstd sox libsox-fmt-all > /dev/null 2>&1
echo "      System deps ready"

# ── Step 2: Install Ollama if missing ──
echo "[2/7] Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "      Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh > /dev/null 2>&1
fi
echo "      Ollama found: $(ollama --version 2>/dev/null | head -1)"

# ── Step 3: Activate venv ──
echo "[3/7] Activating venv..."
if [ ! -d "/workspace/venv" ]; then
    echo "      Creating venv..."
    python3 -m venv /workspace/venv
    source /workspace/venv/bin/activate
    pip install -q fastapi uvicorn faster-whisper piper-tts \
        numpy soundfile requests python-dotenv twilio websockets python-multipart
else
    source /workspace/venv/bin/activate
fi
echo "      Venv active"

# ── Step 4: Pull latest code ──
echo "[4/7] Pulling latest code from GitHub..."
cd /workspace/healthcare-voice-agent
git pull origin main 2>&1 | tail -1
mkdir -p audio/output audio/input

# ── Step 5: Start Ollama ──
echo "[5/7] Starting Ollama..."
tmux kill-session -t ollama 2>/dev/null || true
tmux new-session -d -s ollama 'ollama serve'
sleep 8

# Wait for Ollama to be ready
for i in 1 2 3 4 5; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "      Ollama ready"
        break
    fi
    echo "      Waiting... ($i/5)"
    sleep 3
done

# Pull model if not present
if ! ollama list 2>/dev/null | grep -q "qwen3:8b"; then
    echo "      Pulling qwen3:8b (~5.2GB)..."
    ollama pull qwen3:8b
fi
echo "      qwen3:8b ready"

# ── Step 6: Start ngrok ──
echo "[6/7] Starting ngrok..."
if [ -z "$NGROK_TOKEN" ]; then
    echo "      WARNING: NGROK_TOKEN not set"
    BASE_URL="http://localhost:8000"
else
    ngrok config add-authtoken "$NGROK_TOKEN" > /dev/null 2>&1 || true
    tmux kill-session -t ngrok 2>/dev/null || true
    tmux new-session -d -s ngrok "ngrok http 8000" || true
    sleep 8

    NGROK_URL=""
    for i in 1 2 3; do
        NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])" 2>/dev/null || echo "")
        if [ -n "$NGROK_URL" ]; then
            break
        fi
        echo "      Waiting for ngrok... ($i/3)"
        sleep 4
    done

    if [ -n "$NGROK_URL" ]; then
        BASE_URL=$NGROK_URL
        if [ -f .env ]; then
            sed -i "s|BASE_URL=.*|BASE_URL=$NGROK_URL|" .env
        else
            echo "BASE_URL=$NGROK_URL" > .env
        fi
        echo "================================"
        echo "ngrok URL : $NGROK_URL"
        echo "Twilio    : $NGROK_URL/voice"
        echo "================================"
    else
        echo "      ngrok URL not found, using localhost"
        BASE_URL="http://localhost:8000"
    fi
fi

export BASE_URL

# ── Step 7: Start server ──
echo "[7/7] Starting FastAPI server on port 8000..."
cd /workspace/healthcare-voice-agent
uvicorn src.main:app --host 0.0.0.0 --port 8000