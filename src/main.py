import os
import json
import time
import base64
import random
import asyncio
import requests
import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .config import BASE_URL
from .tts import synthesize_speech
from .stt import mulaw_to_pcm16, transcribe_chunks
from .llm import generate_response, OLLAMA_URL, MODEL

app = FastAPI()
app.mount("/audio", StaticFiles(directory="audio"), name="audio")


# ─────────────────────────────────────────
# OLLAMA WARMUP
# ─────────────────────────────────────────

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

    _prebuild_fillers()


# ─────────────────────────────────────────
# FILLER PHRASES — pre-generated with Piper
# ─────────────────────────────────────────

FILLERS = [
    "Give me a moment while I check that.",
    "Let me look into your records.",
    "One moment please.",
    "I'm checking that for you.",
]

GREETINGS  = {"hi", "hello", "hey", "good morning", "good afternoon"}
EXIT_WORDS = {"bye", "goodbye", "thanks", "thank you", "that's all"}

_filler_urls: list[str] = []

def _prebuild_fillers():
    print("[Fillers] Pre-generating with Piper TTS...")
    for text in FILLERS:
        path = synthesize_speech(text)
        if path:
            _filler_urls.append(f"{BASE_URL}/{path}")
    print(f"[Fillers] {len(_filler_urls)} ready ✅")


# ─────────────────────────────────────────
# SESSIONS
# ─────────────────────────────────────────

sessions: dict[str, dict] = {}

def get_session(call_sid: str) -> dict:
    if call_sid not in sessions:
        sessions[call_sid] = {
            "history": [],
            "pending": "",
            "stream_sid": ""
        }
    return sessions[call_sid]

def clear_session(call_sid: str):
    sessions.pop(call_sid, None)


# ─────────────────────────────────────────
# LATENCY TRACKER
# ─────────────────────────────────────────

class Timer:
    LABELS = {
        "STT":   "🎙️  Whisper STT",
        "LLM":   "🧠  Ollama LLM ",
        "TTS":   "🔊  Piper TTS  ",
        "TOTAL": "⏱️  TOTAL      ",
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


# ─────────────────────────────────────────
# TWIML HELPERS
# ─────────────────────────────────────────

def twiml_stream() -> str:
    """
    Initial TwiML — starts Media Stream WebSocket connection.
    Twilio will stream audio chunks to /media-stream via WSS.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{BASE_URL.replace('https://', '')}/media-stream"/>
    </Connect>
</Response>"""


def twiml_play_and_stream(audio_url: str) -> str:
    """Play audio then re-open stream for next user input."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Connect>
        <Stream url="wss://{BASE_URL.replace('https://', '')}/media-stream"/>
    </Connect>
</Response>"""


def twiml_hangup(audio_url: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Hangup/>
</Response>"""


# ─────────────────────────────────────────
# /voice — initial call entry point
# ─────────────────────────────────────────

@app.post("/voice")
async def voice(request: Request):
    """
    Called once when call starts.
    Returns TwiML to open Media Stream WebSocket.
    """
    form     = await request.form()
    call_sid = form.get("CallSid", "unknown")
    get_session(call_sid)

    print(f"\n[/voice] New call: {call_sid}")

    # Greet patient + open stream
    greeting_path = synthesize_speech(
        "Hi, this is Sarah from City Hospital billing. How can I help you today?"
    )
    greeting_url = f"{BASE_URL}/{greeting_path}"

    return Response(twiml_play_and_stream(greeting_url), media_type="text/xml")


# ─────────────────────────────────────────
# /media-stream — WebSocket endpoint
# Twilio streams audio chunks here in real-time
# ─────────────────────────────────────────

# Silence threshold — how long to wait after user stops speaking
SILENCE_THRESHOLD_MS = 800    # 0.8s of silence = user done speaking
CHUNK_DURATION_MS    = 20     # Twilio sends 20ms chunks
CHUNKS_FOR_SILENCE   = SILENCE_THRESHOLD_MS // CHUNK_DURATION_MS  # 40 chunks


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    Real-time WebSocket handler for Twilio Media Streams.

    Flow:
    1. Twilio sends 'start' event with call metadata
    2. Twilio streams 'media' events with base64 mulaw audio
    3. We buffer audio chunks
    4. When silence detected → transcribe → LLM → TTS → reply
    5. Repeat until call ends
    """

    await websocket.accept()
    print("[WS] Media stream connected")

    call_sid   = ""
    stream_sid = ""

    # Audio buffer
    audio_chunks: list[np.ndarray] = []
    silent_chunks = 0
    is_speaking   = False

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event", "")

            # ── START event — call metadata ──
            if event == "start":
                call_sid   = data["start"]["callSid"]
                stream_sid = data["start"]["streamSid"]
                session    = get_session(call_sid)
                session["stream_sid"] = stream_sid
                print(f"[WS] Stream started: {call_sid}")

            # ── MEDIA event — audio chunk ──
            elif event == "media":
                payload   = data["media"]["payload"]
                mulaw_raw = base64.b64decode(payload)

                # Convert mulaw 8kHz → PCM float32 16kHz
                pcm_chunk = mulaw_to_pcm16(mulaw_raw)

                # Simple energy-based VAD
                energy = np.abs(pcm_chunk).mean()

                if energy > 0.005:
                    # User is speaking
                    is_speaking   = True
                    silent_chunks = 0
                    audio_chunks.append(pcm_chunk)

                elif is_speaking:
                    # User was speaking but now silent
                    silent_chunks += 1
                    audio_chunks.append(pcm_chunk)

                    if silent_chunks >= CHUNKS_FOR_SILENCE:
                        # User finished speaking — process
                        print(f"[WS] User stopped speaking — processing {len(audio_chunks)} chunks")

                        t = Timer()
                        chunks_to_process = audio_chunks.copy()
                        audio_chunks      = []
                        silent_chunks     = 0
                        is_speaking       = False

                        # ── STT ──
                        t.start("STT")
                        user_text = transcribe_chunks(chunks_to_process)
                        t.end("STT")

                        print(f"[WS] Transcript: '{user_text}'")

                        if not user_text:
                            continue

                        session = get_session(call_sid)

                        # ── EXIT ──
                        if any(w in user_text for w in EXIT_WORDS):
                            t.start("TTS")
                            audio = synthesize_speech(
                                "Take care, don't hesitate to call again. Goodbye."
                            )
                            t.end("TTS")
                            t.summary()
                            clear_session(call_sid)

                            # Send play URL via Twilio REST
                            await _redirect_call(call_sid,
                                twiml_hangup(f"{BASE_URL}/{audio}"))
                            break

                        # ── GREETING ──
                        cleaned = user_text.strip().rstrip(".,!?")
                        if cleaned in GREETINGS:
                            t.start("TTS")
                            audio = synthesize_speech("Hey! How can I help you today?")
                            t.end("TTS")
                            t.summary()
                            await _redirect_call(call_sid,
                                twiml_play_and_stream(f"{BASE_URL}/{audio}"))
                            continue

                        # ── BILLING QUESTION ──
                        # Play filler immediately
                        if _filler_urls:
                            filler_url = random.choice(_filler_urls)
                            await _redirect_call(call_sid,
                                twiml_play_and_stream(filler_url))

                        # LLM + TTS in background
                        asyncio.create_task(
                            _generate_and_reply(call_sid, user_text, t)
                        )

            # ── STOP event ──
            elif event == "stop":
                print(f"[WS] Stream stopped: {call_sid}")
                break

    except WebSocketDisconnect:
        print(f"[WS] Disconnected: {call_sid}")
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        print(f"[WS] Closing stream: {call_sid}")


async def _generate_and_reply(call_sid: str, user_text: str, t: Timer):
    """LLM + TTS in background, then update call via Twilio REST."""
    session = get_session(call_sid)
    session["history"].append(f"Patient: {user_text}")

    t.start("LLM")
    reply = await asyncio.to_thread(
        generate_response, user_text, session["history"]
    )
    t.end("LLM")

    session["history"].append(f"Sarah: {reply}")
    print(f"[LLM] Reply: '{reply}'")

    t.start("TTS")
    audio_path = await asyncio.to_thread(synthesize_speech, reply)
    t.end("TTS")

    t.summary()

    # Update the live call to play the response
    await _redirect_call(
        call_sid,
        twiml_play_and_stream(f"{BASE_URL}/{audio_path}")
    )


async def _redirect_call(call_sid: str, twiml: str):
    """
    Update a live Twilio call with new TwiML via REST API.
    This is how we send audio back during an active Media Stream.
    """
    from .config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

    try:
        await asyncio.to_thread(
            requests.post,
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{call_sid}.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"Twiml": twiml},
            timeout=10
        )
    except Exception as e:
        print(f"[Twilio REST Error]: {e}")


# ─────────────────────────────────────────
# /call-status — cleanup
# ─────────────────────────────────────────

@app.post("/call-status")
async def call_status(request: Request):
    form     = await request.form()
    call_sid = form.get("CallSid", "")
    status   = form.get("CallStatus", "")
    print(f"Call {call_sid} → {status}")
    if status in ("completed", "failed", "busy", "no-answer"):
        clear_session(call_sid)
    return Response("", status_code=204)