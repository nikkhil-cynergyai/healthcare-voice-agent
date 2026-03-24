import os
from dotenv import load_dotenv

load_dotenv()

# ── Twilio ──
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# ── Public URL ──
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ── Audio ──
AUDIO_OUTPUT_DIR = "audio/output"
AUDIO_INPUT_DIR  = "audio/input"

# ── Piper TTS ──
PIPER_MODELS_DIR = os.getenv("PIPER_MODELS_DIR", "/workspace/piper_models")
PIPER_VOICE      = "en_US-lessac-high"

# ── Whisper STT ──
# RunPod GPU: set WHISPER_DEVICE=cuda in env vars
WHISPER_MODEL   = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = "float16" if WHISPER_DEVICE == "cuda" else "int8"

# ── Ollama LLM ──
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")