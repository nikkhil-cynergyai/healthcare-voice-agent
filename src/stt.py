# stt.py — Twilio built-in STT
# No download, no Whisper, no latency
# Twilio transcribes on their servers and sends SpeechResult directly

def transcribe_audio(speech_result: str) -> str:
    """
    Twilio STT — text already transcribed by Twilio.
    Just clean and return it.

    Args:
        speech_result: SpeechResult from Twilio form data

    Returns:
        Cleaned lowercase transcript
    """
    return speech_result.lower().strip()