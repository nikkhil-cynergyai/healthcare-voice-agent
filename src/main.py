import time
import random
import requests
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .config import BASE_URL
from .tts import synthesize_speech
from .llm import generate_response, OLLAMA_URL, MODEL

app = FastAPI()
app.mount("/audio", StaticFiles(directory="audio"), name="audio")


# ── Ollama warmup + pre-build fillers ──
@app.on_event("startup")
async def warmup():
    print("🔥 Warming up Ollama...")
    try:
        requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": "hi", "stream": False,
                  "options": {"num_predict": 1}},
            timeout=30
        )
        print("✅ Ollama ready")
    except Exception as e:
        print(f"⚠️  Ollama warmup failed: {e}")

    # Pre-generate filler audio with Piper at startup
    # So fillers play instantly — no TTS generation delay
    print("[Fillers] Pre-generating with Piper...")
    for text in FILLERS:
        path = synthesize_speech(text)
        if path:
            _filler_audio.append(f"{BASE_URL}/{path}")
    print(f"[Fillers] {len(_filler_audio)} ready ")


# ── Twilio TTS voice ──
TWILIO_VOICE = "Google.en-US-Chirp3-HD-Charon"

# ── Filler text + pre-generated Piper audio ──
# Short fillers = less delay before Piper audio plays
FILLERS = [
    "Sure, one sec.",
    "Mhm, let me check.",
    "Yeah, one moment.",
    "Got it, just a sec.",
    "Sure thing.",
]
_filler_audio: list[str] = []   # populated at startup

GREETINGS  = {"hi", "hello", "hey", "good morning", "good afternoon", "yo", "hey there"}
EXIT_WORDS = {"bye", "goodbye", "thanks", "thank you", "that's all", "thats all", "that's it"}


# ── Sessions ──
sessions: dict[str, dict] = {}

def get_session(call_sid):
    if call_sid not in sessions:
        sessions[call_sid] = {"history": [], "pending": ""}
    return sessions[call_sid]

def clear_session(call_sid):
    sessions.pop(call_sid, None)


# ── Latency tracker ──
class Timer:
    LABELS = {
        "STT":   "🎙️  Twilio STT  ",
        "LLM":   "🧠  Ollama LLM  ",
        "TOTAL": "⏱️  TOTAL       ",
    }

    def __init__(self):
        self._start = time.time()
        self._steps = []
        self._marks = {}

    def start(self, label):
        self._marks[label] = time.time()

    def end(self, label):
        if label in self._marks:
            self._steps.append((label, round(time.time() - self._marks[label], 3)))

    def summary(self):
        total = round(time.time() - self._start, 3)
        self._steps.append(("TOTAL", total))
        print("\n" + "─" * 42)
        print("  LATENCY BREAKDOWN")
        print("─" * 42)
        for label, s in self._steps:
            d = self.LABELS.get(label, label)
            c = "🟢" if s < 1 else "🟡" if s < 2 else "🔴"
            print(f"  {d}  {s:.3f}s  {c}{'█' * min(int(s/0.2), 20)}")
        print("─" * 42 + "\n")


# ── TwiML helpers ──

def say(text: str) -> str:
    return f'<Say voice="{TWILIO_VOICE}">{text}</Say>'


def twiml_gather(text: str, action: str = "/voice") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech"
            action="{action}"
            method="POST"
            speechTimeout="auto"
            timeout="8"
            bargeIn="true">
        {say(text)}
    </Gather>
    <Redirect method="POST">{action}</Redirect>
</Response>"""


def twiml_filler(audio_url: str) -> str:
    """Play pre-recorded Piper filler instantly — no TTS generation delay."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech"
            action="/voice"
            method="POST"
            speechTimeout="auto"
            timeout="3"
            bargeIn="true">
        <Play>{audio_url}</Play>
    </Gather>
    <Redirect method="POST">{BASE_URL}/respond</Redirect>
</Response>"""


def twiml_filler_say(text: str) -> str:
    """Fallback: use Twilio Say if pre-recorded audio not ready."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech"
            action="/voice"
            method="POST"
            speechTimeout="auto"
            timeout="3"
            bargeIn="true">
        {say(text)}
    </Gather>
    <Redirect method="POST">{BASE_URL}/respond</Redirect>
</Response>"""


def twiml_hangup(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    {say(text)}
    <Hangup/>
</Response>"""


# ── /voice ──
@app.post("/voice")
async def voice(request: Request):
    t = Timer()
    form     = await request.form()
    call_sid = form.get("CallSid", "unknown")
    session  = get_session(call_sid)

    t.start("STT")
    user_text = form.get("SpeechResult", "").lower().strip()
    t.end("STT")

    print(f"\n[/voice] '{user_text}'")

    # Exit
    if user_text and any(w in user_text for w in EXIT_WORDS):
        t.summary()
        clear_session(call_sid)
        return Response(
            twiml_hangup("Of course — take care, and don't hesitate to call if you need anything. Bye!"),
            media_type="text/xml"
        )

    # First call — no speech yet
    if not user_text:
        t.summary()
        return Response(
            twiml_gather("Hi there, this is Sarah from the billing team at City Hospital. How can I help you today?"),
            media_type="text/xml"
        )

    # Greeting
    if user_text.rstrip(".,!?") in GREETINGS:
        t.summary()
        greet_replies = [
            "Hey! How can I help you today?",
            "Hi there! What can I do for you?",
            "Hello! Go ahead, what do you need?",
        ]
        return Response(
            twiml_gather(random.choice(greet_replies)),
            media_type="text/xml"
        )

    # Billing question — instant pre-recorded filler + /respond
    session["pending"] = user_text
    filler_url = random.choice(_filler_audio) if _filler_audio else None
    if filler_url:
        print(f"[filler] playing pre-recorded audio")
        t.summary()
        return Response(twiml_filler(filler_url), media_type="text/xml")
    else:
        # fallback if audio not ready
        t.summary()
        return Response(twiml_filler_say(random.choice(FILLERS)), media_type="text/xml")


# ── /respond ──
@app.post("/respond")
async def respond(request: Request):
    t = Timer()
    form      = await request.form()
    call_sid  = form.get("CallSid", "unknown")
    session   = get_session(call_sid)

    barge_text = form.get("SpeechResult", "").lower().strip()
    user_text  = barge_text if barge_text else session.pop("pending", "")

    print(f"[/respond] '{user_text}'")

    if not user_text:
        return Response(
            twiml_gather("Sorry, I didn't quite catch that — could you say it again?"),
            media_type="text/xml"
        )

    session["history"].append(f"Patient: {user_text}")

    t.start("LLM")
    reply = generate_response(user_text, session["history"])
    t.end("LLM")

    session["history"].append(f"Sarah: {reply}")

    print(f"[reply] '{reply}'")
    t.summary()

    return Response(twiml_gather(reply), media_type="text/xml")


# ── Call status cleanup ──
@app.post("/call-status")
async def call_status(request: Request):
    form     = await request.form()
    call_sid = form.get("CallSid", "")
    status   = form.get("CallStatus", "")
    print(f"Call {call_sid} → {status}")
    if status in ("completed", "failed", "busy", "no-answer"):
        clear_session(call_sid)
    return Response("", status_code=204)