import io
import os
import uuid
import wave
import numpy as np
import soundfile as sf
from piper import PiperVoice

from .config import AUDIO_OUTPUT_DIR

# ─────────────────────────────────────────
# Piper TTS v1.4 — fast local ONNX model
# ~0.3s on CPU, no GPU needed, fully offline
#
# Model must be downloaded first — run this once:
#   python3 -m piper.download_voices en_US-lessac-medium
#
# Other good voices (download same way):
#   en_US-ryan-high       → male, high quality
#   en_US-amy-medium      → female, natural
#   en_US-libritts-high   → neutral, high quality
#
# Listen to samples: https://rhasspy.github.io/piper-samples/
# ─────────────────────────────────────────

_VOICE_NAME  = "en_US-lessac-medium"
_MODELS_DIR  = "piper_models"
_MODEL_PATH  = os.path.join(_MODELS_DIR, f"{_VOICE_NAME}.onnx")


def _load_model():
    os.makedirs(_MODELS_DIR, exist_ok=True)

    # Auto-download if model not present
    if not os.path.exists(_MODEL_PATH):
        print(f"[Piper TTS] Model not found. Downloading {_VOICE_NAME}...")
        import subprocess
        subprocess.run(
            ["python3", "-m", "piper.download_voices", _VOICE_NAME,
             "--output-dir", _MODELS_DIR],
            check=True
        )

    print(f"[Piper TTS] Loading {_VOICE_NAME}...")
    voice = PiperVoice.load(_MODEL_PATH)
    print("[Piper TTS] Model ready ✅")
    return voice


_voice = _load_model()


def synthesize_speech(text: str) -> str:
    """
    Convert text to speech WAV using local Piper TTS v1.4.

    Uses synthesize_wav() — writes directly to WAV file.
    ONNX inference, ~0.3s on CPU.

    Args:
        text: text to synthesize

    Returns:
        local path to saved WAV file
    """

    if not text or not text.strip():
        return ""

    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

    try:
        file_name = f"tts_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(AUDIO_OUTPUT_DIR, file_name)

        with wave.open(file_path, "wb") as wav_file:
            _voice.synthesize_wav(text, wav_file)

        return file_path

    except Exception as e:
        print(f"[Piper TTS Error]: {e}")
        return _kokoro_fallback(text)


def _kokoro_fallback(text: str) -> str:
    """Fallback to Kokoro if Piper fails."""
    print("[TTS] Falling back to Kokoro...")
    try:
        from kokoro import KPipeline

        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        pipeline = KPipeline(lang_code="en-us", repo_id="hexgrad/Kokoro-82M")
        chunks = []
        for _, _, audio in pipeline(text, voice="af_heart", speed=1.0):
            if audio is not None and len(audio) > 0:
                chunks.append(audio)

        if not chunks:
            return ""

        file_name = f"tts_fallback_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(AUDIO_OUTPUT_DIR, file_name)
        sf.write(file_path, np.concatenate(chunks), 24000)
        return file_path

    except Exception as e2:
        print(f"[Kokoro Fallback Error]: {e2}")
        return ""