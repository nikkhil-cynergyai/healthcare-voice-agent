"""
Cynergy AI Voice Agent Backend — ElevenLabs + Twilio
Run:  pip install fastapi uvicorn httpx python-dotenv
      uvicorn main:app --reload --port 5000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx, os
from datetime import datetime

load_dotenv()

# ─── Config ───
ELEVENLABS_API_KEY         = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_AGENT_ID        = os.getenv("ELEVENLABS_AGENT_ID")
ELEVENLABS_PHONE_NUMBER_ID = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
COMPANY_NAME               = os.getenv("COMPANY_NAME", "Cynergy AI")

ELEVENLABS_BASE    = "https://api.elevenlabs.io/v1/convai"
OUTBOUND_URL       = f"{ELEVENLABS_BASE}/twilio/outbound-call"

app = FastAPI(title="Cynergy AI Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory call store ───
calls: dict[str, dict] = {}


# ─── Models ───
class CallRequest(BaseModel):
    phone: str


# ─── Routes ───
@app.post("/call")
async def start_call(req: CallRequest):
    """Trigger outbound call with 1s first-message pause."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                OUTBOUND_URL,
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "agent_id": ELEVENLABS_AGENT_ID,
                    "agent_phone_number_id": ELEVENLABS_PHONE_NUMBER_ID,
                    "to_number": req.phone,
                    "conversation_initiation_client_data": {
                        "dynamic_variables": {
                            "company_name": COMPANY_NAME,
                        },
                    },
                },
                timeout=30,
            )

        data = res.json()

        if not res.is_success:
            raise HTTPException(status_code=res.status_code, detail=data)

        call_sid = data.get("callSid", "")
        conv_id  = data.get("conversation_id", "")

        calls[call_sid] = {
            "call_sid": call_sid,
            "conversation_id": conv_id,
            "phone": req.phone,
            "status": "initiated",
            "started_at": datetime.utcnow().isoformat(),
            "duration": 0,
        }

        return {
            "message": "Call initiated",
            "call_sid": call_sid,
            "conversation_id": conv_id,
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"ElevenLabs unreachable: {e}")


@app.get("/call-status/{conv_id}")
async def call_status(conv_id: str):
    """Poll ElevenLabs for real conversation status."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{ELEVENLABS_BASE}/conversations/{conv_id}",
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                timeout=10,
            )
        data = res.json()
        status = data.get("status", "unknown")
        duration = data.get("metadata", {}).get("call_duration_secs", 0)
        return {"status": status, "duration": duration}
    except Exception:
        return {"status": "unknown", "duration": 0}


@app.get("/calls")
def list_calls():
    return sorted(calls.values(), key=lambda c: c["started_at"], reverse=True)


@app.get("/calls/{call_sid}")
def get_call(call_sid: str):
    if call_sid not in calls:
        raise HTTPException(404, "Call not found")
    return calls[call_sid]