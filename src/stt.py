import numpy as np
from faster_whisper import WhisperModel

# ─────────────────────────────────────────
# Faster Whisper — local STT
# beam_size=1 → greedy decoding (fastest, minimal accuracy loss)
# ─────────────────────────────────────────

_MODEL_SIZE = "base"
_DEVICE     = "cpu"
_COMPUTE    = "int8"

print(f"[Whisper STT] Loading model: {_MODEL_SIZE}...")
_model = WhisperModel(_MODEL_SIZE, device=_DEVICE, compute_type=_COMPUTE)
print("[Whisper STT] Model ready ✅")


def mulaw_to_pcm16(mulaw_bytes: bytes) -> np.ndarray:
    """mulaw 8kHz (Twilio) → PCM float32 16kHz (Whisper)"""
    import audioop

    # mulaw → linear PCM 16-bit
    pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)

    # 8kHz → 16kHz upsample
    pcm_16k, _ = audioop.ratecv(pcm_bytes, 2, 1, 8000, 16000, None)

    # bytes → float32
    audio = np.frombuffer(pcm_16k, dtype=np.int16).astype(np.float32) / 32768.0
    return audio


def transcribe_chunks(audio_chunks: list) -> str:
    """Transcribe buffered audio with Faster Whisper."""

    if not audio_chunks:
        return ""

    audio = np.concatenate(audio_chunks)

    # Too short = silence (less than 0.3s)
    if len(audio) < 16000 * 0.3:
        return ""

    try:
        segments, _ = _model.transcribe(
            audio,
            language="en",
            beam_size=1,            # greedy — fastest, still accurate for short phrases
            best_of=1,              # no candidates sampling
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=200)
        )

        return " ".join(seg.text for seg in segments).strip().lower()

    except Exception as e:
        print(f"[Whisper STT Error]: {e}")
        return ""