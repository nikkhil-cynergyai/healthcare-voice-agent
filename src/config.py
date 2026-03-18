import os
from dotenv import load_dotenv

load_dotenv()

# Twilio
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Public URL (ngrok)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Audio
AUDIO_INPUT_DIR  = "audio/input"
AUDIO_OUTPUT_DIR = "audio/output"