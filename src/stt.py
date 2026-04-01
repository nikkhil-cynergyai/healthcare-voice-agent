import numpy as np
from faster_whisper import WhisperModel
from .config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE

# ── Model loading ──
# distil-large-v3 needs HuggingFace path
# other models use standard names
_DISTIL_MODELS = {
    "distil-large-v3",
    "distil-large-v2",
    "distil-medium.en",
    "distil-small.en"
}

_is_distil = WHISPER_MODEL in _DISTIL_MODELS

print(f"[STT] Loading {WHISPER_MODEL} on {WHISPER_DEVICE}...")

if _is_distil:
    _model = WhisperModel(
        f"distil-whisper/{WHISPER_MODEL}",
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE,
    )
else:
    _model = WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE,
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

    # Too short = silence
    if len(audio) < 16000 * 0.3:
        return ""

    try:
        # distil-large-v3 needs padding to 128 mel bins
        # faster-whisper handles this internally when model is loaded correctly
        kwargs = dict(
            language="en",
            beam_size=1,
            best_of=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=200),
        )

        # distil models don't support condition_on_previous_text same way
        if not _is_distil:
            kwargs["condition_on_previous_text"] = False

        segments, _ = _model.transcribe(audio, **kwargs)
        return " ".join(seg.text for seg in segments).strip().lower()

    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""