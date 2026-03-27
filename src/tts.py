import os
import uuid
import wave
import threading
from .config import AUDIO_OUTPUT_DIR, PIPER_MODELS_DIR, PIPER_VOICE

MISTRAL_API_KEY  = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_VOICE_ID = os.getenv("MISTRAL_VOICE_ID", "sarah")  # default voice

# ── Try Voxtral TTS first ──
_use_mistral   = False
_mistral_client = None

if MISTRAL_API_KEY:
    try:
        from mistralai import Mistral
        _mistral_client = Mistral(api_key=MISTRAL_API_KEY)
        _use_mistral    = True
        print("[TTS] Voxtral TTS (Mistral) ready ✅")
    except Exception as e:
        print(f"[TTS] Mistral failed: {e} — falling back to Piper")

# ── Piper fallback ──
_piper_voice = None

if not _use_mistral:
    try:
        from piper import PiperVoice
        _MODEL_PATH = os.path.join(PIPER_MODELS_DIR, f"{PIPER_VOICE}.onnx")
        if os.path.exists(_MODEL_PATH):
            try:
                _piper_voice = PiperVoice.load(_MODEL_PATH, use_cuda=True)
                print("[TTS] Piper ready ✅ (GPU)")
            except Exception:
                _piper_voice = PiperVoice.load(_MODEL_PATH, use_cuda=False)
                print("[TTS] Piper ready ✅ (CPU)")

            def _prewarm():
                try:
                    with wave.open("/tmp/piper_prewarm.wav", "wb") as f:
                        _piper_voice.synthesize_wav("hello", f)
                    print("[TTS] Pre-warmed ✅")
                except Exception as e:
                    print(f"[TTS] Pre-warm failed: {e}")

            threading.Thread(target=_prewarm, daemon=True).start()
        else:
            print(f"[TTS] Piper model not found: {_MODEL_PATH}")
    except Exception as e:
        print(f"[TTS] Piper failed: {e}")


def synthesize_speech(text: str) -> str:
    """Convert text to WAV. Uses Voxtral TTS if available, else Piper."""
    if not text or not text.strip():
        return ""

    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(AUDIO_OUTPUT_DIR, f"tts_{uuid.uuid4().hex}.wav")

    # ── Voxtral TTS ──
    if _use_mistral and _mistral_client:
        try:
            response = _mistral_client.audio.speech.create(
                model="voxtral-tts",
                voice=MISTRAL_VOICE_ID,
                input=text,
                response_format="pcm",   # raw PCM — fastest
            )

            # Write PCM → WAV
            pcm_data = response.read()
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)       # 16-bit
                wf.setframerate(22050)   # 22kHz
                wf.writeframes(pcm_data)

            return file_path

        except Exception as e:
            print(f"[Voxtral TTS Error]: {e} — falling back to Piper")

    # ── Piper fallback ──
    if _piper_voice:
        try:
            with wave.open(file_path, "wb") as wf:
                _piper_voice.synthesize_wav(text, wf)
            return file_path
        except Exception as e:
            print(f"[Piper Error]: {e}")

    return ""