#!/bin/bash
set -e

echo "================================"
echo "  Healthcare Voice Agent"
echo "  RunPod GPU Server"
echo "================================"

# Pull latest code
cd /workspace/healthcare-voice-agent
git pull origin main 2>/dev/null || echo "Git pull skipped"

# Start Ollama in background
tmux new-session -d -s ollama 'ollama serve'
echo " Waiting for Ollama to start..."
sleep 8

# Pull qwen3:8b if not present
if ! ollama list | grep -q "qwen3:8b"; then
    echo " Pulling qwen3:8b model (~5.2GB)..."
    ollama pull qwen3:8b
fi
echo "✅ Ollama + qwen3:8b ready"

# Start ngrok (NGROK_TOKEN must be set in RunPod env vars)
if [ -z "$NGROK_TOKEN" ]; then
    echo "⚠️  NGROK_TOKEN not set — skipping ngrok"
    export BASE_URL="http://localhost:8000"
else
    tmux new-session -d -s ngrok "ngrok http 8000 --authtoken ${NGROK_TOKEN}"
    sleep 6

    URL=$(curl -s http://127.0.0.1:4040/api/tunnels | \
        python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || echo "")

    if [ -n "$URL" ]; then
        export BASE_URL=$URL
        echo "================================"
        echo "  ngrok URL : $URL"
        echo "  Twilio    : $URL/voice"
        echo "================================"
        echo "  Update Twilio webhook to: $URL/voice"
    else
        echo "  ngrok URL not found"
        export BASE_URL="http://localhost:8000"
    fi
fi

# Create audio dirs
mkdir -p /workspace/healthcare-voice-agent/audio/output \
         /workspace/healthcare-voice-agent/audio/input

# Start FastAPI server
echo "🚀 Starting server on port 8000..."
cd /workspace/healthcare-voice-agent
uvicorn src.main:app --host 0.0.0.0 --port 8000