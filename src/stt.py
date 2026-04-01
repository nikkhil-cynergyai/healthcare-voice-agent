import numpy as np
from faster_whisper import WhisperModel
from .config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE

# Distil-Whisper models need special handling
_DISTIL_MODELS = {"distil-large-v3", "distil-large-v2", "distil-medium.en", "distil-small.en"}
_is_distil = WHISPER_MODEL in _DISTIL_MODELS

print(f"[STT] Loading {WHISPER_MODEL} on {WHISPER_DEVICE}...")

if _is_distil:
    # Distil-Whisper from HuggingFace
    _model = WhisperModel(
        f"distil-whisper/{WHISPER_MODEL}",
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE
    )
else:
    _model = WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE
    )

print(f"[STT] Ready — {WHISPER_MODEL} on {WHISPER_DEVICE.upper()}")


def mulaw_to_pcm16(mulaw_bytes: bytes) -> np.ndarray:
    """mulaw 8kHz (Twilio) → PCM float32 16kHz (Whisper)"""
    import audioop
    pcm_bytes  = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_bytes, 2, 1, 8000, 16000, None)
    return np.frombuffer(pcm_16k, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_chunks(audio_chunks: list) -> str:
    """Transcribe buffered audio chunks."""
    if not audio_chunks:
        return ""

    audio = np.concatenate(audio_chunks)

    if len(audio) < 16000 * 0.3:
        return ""

    try:
        segments, _ = _model.transcribe(
            audio,
            language="en",
            beam_size=1,
            best_of=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=200),
            # Distil-Whisper specific — better accuracy
            condition_on_previous_text=False,
        )
        return " ".join(seg.text for seg in segments).strip().lower()
    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""