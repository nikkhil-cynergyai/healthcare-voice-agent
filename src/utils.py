import time

class Timer:
    def __init__(self):
        self.start = time.time()

    def elapsed(self):
        return round(time.time() - self.start, 3)
    # ── Twilio TTS voice ──
# Options (most human-like):
#   Google.en-US-Chirp3-HD-Aoede     ← female, natural
#   Google.en-US-Chirp3-HD-Charon    ← male, natural
#   Polly.Joanna-Generative          ← female, conversational
#   Polly.Matthew-Generative         ← male, conversational