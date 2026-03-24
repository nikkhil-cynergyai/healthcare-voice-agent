#!/bin/bash
set -e

echo "================================"
echo "  Healthcare Voice Agent"
echo "  RunPod GPU Server"
echo "================================"

# System deps
apt-get install -y tmux zstd sox libsox-fmt-all -q > /dev/null 2>&1

# Activate venv
source /workspace/venv/bin/activate

# Pull latest code from GitHub
cd /workspace/healthcare-voice-agent
git pull origin main 2>/dev/null || echo "Git pull skipped"

# Audio dirs
mkdir -p audio/output audio/input

# Start Ollama
tmux kill-session -t ollama 2>/dev/null || true
tmux new-session -d -s ollama 'ollama serve'
echo "⏳ Waiting for Ollama..."
sleep 8

# Pull model if not present
if ! ollama list | grep -q "qwen3:8b"; then
    echo "📥 Pulling qwen3:8b (~5.2GB)..."
    ollama pull qwen3:8b
fi
echo "✅ Ollama + qwen3:8b ready"

# Start ngrok (NGROK_TOKEN must be in RunPod env vars)
if [ -z "$NGROK_TOKEN" ]; then
    echo "⚠️  NGROK_TOKEN not set — set it in RunPod env vars"
    export BASE_URL="http://localhost:8000"
else
    ngrok config add-authtoken ${NGROK_TOKEN} > /dev/null 2>&1
    tmux kill-session -t ngrok 2>/dev/null || true
    tmux new-session -d -s ngrok "ngrok http 8000"
    sleep 6

    URL=$(curl -s http://127.0.0.1:4040/api/tunnels | \
        python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || echo "")

    if [ -n "$URL" ]; then
        export BASE_URL=$URL
        # Update .env with new URL
        if [ -f .env ]; then
            sed -i "s|BASE_URL=.*|BASE_URL=$URL|" .env
        else
            echo "BASE_URL=$URL" > .env
        fi
        echo "================================"
        echo "  ngrok URL : $URL"
        echo "  Twilio    : $URL/voice"
        echo "================================"
        echo "  ⚠️  Update Twilio webhook to: $URL/voice"
        echo "================================"
    else
        echo "⚠️  ngrok URL not found"
        export BASE_URL="http://localhost:8000"
    fi
fi

# Start FastAPI server
echo "🚀 Starting server on port 8000..."
uvicorn src.main:app --host 0.0.0.0 --port 8000