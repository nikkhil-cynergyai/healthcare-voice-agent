import numpy as np
from faster_whisper import WhisperModel
from .config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE

print(f"[STT] Loading Whisper {WHISPER_MODEL} on {WHISPER_DEVICE} ({WHISPER_COMPUTE})...")
_model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
print(f"[STT] Whisper ready on {WHISPER_DEVICE.upper()}")


def mulaw_to_pcm16(mulaw_bytes: bytes) -> np.ndarray:
    """Convert Twilio mulaw 8kHz → PCM float32 16kHz for Whisper."""
    import audioop
    pcm_bytes  = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_bytes, 2, 1, 8000, 16000, None)
    return np.frombuffer(pcm_16k, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_chunks(audio_chunks: list) -> str:
    """Transcribe buffered audio chunks using Whisper."""
    if not audio_chunks:
        return ""

    audio = np.concatenate(audio_chunks)

    # Skip if too short (less than 0.3s)
    if len(audio) < 16000 * 0.3:
        return ""

    try:
        segments, _ = _model.transcribe(
            audio,
            language="en",
            beam_size=1,          # fastest — greedy decoding
            best_of=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=200)
        )
        return " ".join(seg.text for seg in segments).strip().lower()
    except Exception as e:
        print(f"[STT] Error: {e}")
        return ""