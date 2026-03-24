 
FROM runpod/pytorch:2.1.0-py3.11-cuda12.1.0-devel-ubuntu22.04

# ── System dependencies ──
RUN apt-get update && apt-get install -y \
    curl git wget tmux zstd \
    sox libsox-fmt-all \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.0 \
    faster-whisper \
    piper-tts==1.4.1 \
    numpy \
    soundfile \
    requests \
    python-dotenv \
    twilio \
    websockets

# ── Ollama install ──
RUN curl -fsSL https://ollama.ai/install.sh | sh

# ── ngrok install ──
RUN curl -sL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar xz \
    && mv ngrok /usr/local/bin/ngrok

# ── Piper voice model pre-download ──
RUN mkdir -p /workspace/piper_models && \
    curl -sL -o /workspace/piper_models/en_US-lessac-high.onnx \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx" && \
    curl -sL -o /workspace/piper_models/en_US-lessac-high.onnx.json \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx.json"

# ── Whisper model pre-download ──
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# ── App code ──
WORKDIR /workspace
RUN git clone https://github.com/nikkhile-cynergyai/healthcare-voice-agent.git

# ── Audio folders ──
RUN mkdir -p /workspace/healthcare-voice-agent/audio/output \
             /workspace/healthcare-voice-agent/audio/input

# ── Startup script ──
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

# ── Environment defaults ──
ENV PIPER_MODELS_DIR=/workspace/piper_models
ENV WHISPER_MODEL=base
ENV WHISPER_DEVICE=cuda
ENV OLLAMA_MODEL=qwen3:8b
ENV OLLAMA_URL=http://localhost:11434/api/chat

EXPOSE 8000

CMD ["/workspace/start.sh"]