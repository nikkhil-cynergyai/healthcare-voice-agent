import os
import uuid
import wave
import threading
from .config import AUDIO_OUTPUT_DIR, PIPER_MODELS_DIR, PIPER_VOICE

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Sarah voice
ELEVENLABS_MODEL = "eleven_turbo_v2"   # fastest model ~300ms

# ── Try ElevenLabs first, fallback to Piper ──
_use_elevenlabs = False
_eleven_client  = None

if ELEVENLABS_API_KEY:
    try:
        from elevenlabs.client import ElevenLabs
        _eleven_client  = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        _use_elevenlabs = True
        print("[TTS] ElevenLabs ready ✅")
    except Exception as e:
        print(f"[TTS] ElevenLabs failed: {e} — falling back to Piper")

# ── Piper fallback ──
_piper_voice = None

if not _use_elevenlabs:
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
    """Convert text to WAV. Uses ElevenLabs if available, else Piper."""
    if not text or not text.strip():
        return ""

    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(AUDIO_OUTPUT_DIR, f"tts_{uuid.uuid4().hex}.wav")

    # ── ElevenLabs ──
    if _use_elevenlabs and _eleven_client:
        try:
            audio = _eleven_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=text,
                model_id=ELEVENLABS_MODEL,
                output_format="pcm_22050",   # raw PCM — fast
            )
            # Write PCM to WAV
            pcm_data = b"".join(audio)
            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(pcm_data)
            return file_path
        except Exception as e:
            print(f"[ElevenLabs Error]: {e} — falling back to Piper")

    # ── Piper fallback ──
    if _piper_voice:
        try:
            with wave.open(file_path, "wb") as wf:
                _piper_voice.synthesize_wav(text, wf)
            return file_path
        except Exception as e:
            print(f"[Piper Error]: {e}")

    return ""