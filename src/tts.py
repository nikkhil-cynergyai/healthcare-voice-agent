import os
import uuid
import wave
from piper import PiperVoice
from .config import AUDIO_OUTPUT_DIR, PIPER_MODELS_DIR, PIPER_VOICE

_MODEL_PATH = os.path.join(PIPER_MODELS_DIR, f"{PIPER_VOICE}.onnx")

print(f"[Piper TTS] Loading {PIPER_VOICE} on GPU...")

if not os.path.exists(_MODEL_PATH):
    raise FileNotFoundError(
        f"Piper model not found: {_MODEL_PATH}\n"
        f"Run: curl -L -o {_MODEL_PATH} "
        f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx"
    )

# use_cuda=True → onnxruntime-gpu uses NVIDIA GPU
_voice = PiperVoice.load(_MODEL_PATH, use_cuda=True)
print("[Piper TTS] Model ready ✅ (GPU)")


def synthesize_speech(text: str) -> str:
    """Convert text to WAV using Piper TTS on GPU. Returns file path."""
    if not text or not text.strip():
        return ""

    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

    try:
        file_path = os.path.join(AUDIO_OUTPUT_DIR, f"tts_{uuid.uuid4().hex}.wav")
        with wave.open(file_path, "wb") as wav_file:
            _voice.synthesize_wav(text, wav_file)
        return file_path
    except Exception as e:
        print(f"[Piper TTS Error]: {e}")
        return ""