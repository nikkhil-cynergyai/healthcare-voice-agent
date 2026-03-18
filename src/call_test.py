from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MY_NUMBER = os.getenv("MY_PHONE_NUMBER")
BASE_URL = os.getenv("BASE_URL")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

call = client.calls.create(
    url=f"{BASE_URL}/voice",
    to=MY_NUMBER,
    from_=TWILIO_NUMBER,
    status_callback=f"{BASE_URL}/call-status",   
    status_callback_method="POST"
)

print("Call initiated:", call.sid)