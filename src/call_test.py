from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

call = client.calls.create(
    url=f"{os.getenv('BASE_URL')}/voice",
    to=os.getenv("MY_PHONE_NUMBER"),
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    status_callback=f"{os.getenv('BASE_URL')}/call-status",
    status_callback_method="POST"
)

print(f"Call initiated: {call.sid}")