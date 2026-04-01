import os
import json
import time
import base64
import asyncio
import requests
import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .config import (
    BASE_URL, OLLAMA_URL, OLLAMA_MODEL,
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    ELEVENLABS_API_KEY
)
from .tts import synthesize_speech
from .stt import mulaw_to_pcm16, transcribe_chunks
from .llm import generate_response

app = FastAPI()
app.mount("/audio", StaticFiles(directory="audio"), name="audio")

TTS_ENGINE = "ElevenLabs" if ELEVENLABS_API_KEY else "Piper"


# ── Ollama warmup ──
@app.on_event("startup")
async def warmup():
    print("\n" + "=" * 42)
    print("  Healthcare Voice Agent Starting")
    print("=" * 42)
    print(f"  STT : Whisper (CUDA)")
    print(f"  LLM : {OLLAMA_MODEL} (GPU)")
    print(f"  TTS : {TTS_ENGINE}")
    print("=" * 42 + "\n")

    print("[LLM] Warming up Ollama...")
    try:
        requests.post(
            OLLAMA_URL,
            json={
                "model":    OLLAMA_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "stream":   False,
                "think":    False,
                "options":  {"num_predict": 1}
            },
            timeout=120
        )
        print("[LLM] Ollama ready")
    except Exception as e:
        print(f"[LLM] Warmup failed: {e}")


# ── Keywords ──
GREETINGS  = {"hi", "hello", "hey", "good morning", "good afternoon"}
EXIT_WORDS = {"bye", "goodbye", "thanks", "thank you", "that's all", "thank you bye"}


# ── Sessions ──
sessions: dict[str, dict] = {}

def get_session(call_sid: str) -> dict:
    if call_sid not in sessions:
        sessions[call_sid] = {"history": []}
    return sessions[call_sid]

def clear_session(call_sid: str):
    sessions.pop(call_sid, None)


# ── Latency tracker ──
class Timer:
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
        labels = {
            "STT":   f"[STT] Whisper      ",
            "LLM":   f"[LLM] Ollama       ",
            "TTS":   f"[TTS] {TTS_ENGINE:<10}",
            "TOTAL": "[---] TOTAL        ",
        }
        print("\n" + "─" * 42)
        print("  LATENCY BREAKDOWN")
        print("─" * 42)
        for label, s in self._steps:
            d = labels.get(label, label)
            c = "🟢" if s < 1 else "🟡" if s < 2 else "🔴"
            print(f"  {d}  {s:.3f}s  {c}{'█' * min(int(s / 0.2), 20)}")
        print("─" * 42 + "\n")


# ── TwiML helpers ──
def _ws_url():
    return BASE_URL.replace("https://", "wss://").replace("http://", "ws://")

def twiml_play_and_stream(audio_url: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Connect><Stream url="{_ws_url()}/media-stream"/></Connect>
</Response>"""

def twiml_hangup(audio_url: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Hangup/>
</Response>"""


# ── /voice ──
@app.post("/voice")
async def voice(request: Request):
    form     = await request.form()
    call_sid = form.get("CallSid", "unknown")
    get_session(call_sid)

    print(f"\n{'='*42}")
    print(f"  NEW CALL: {call_sid}")
    print(f"{'='*42}")

    greeting = synthesize_speech(
        "Hi, this is Priya from City Hospital billing. How can I help you today?"
    )
    return Response(
        twiml_play_and_stream(f"{BASE_URL}/{greeting}"),
        media_type="text/xml"
    )


# ── WebSocket Media Stream ──
SILENCE_MS     = 800
CHUNK_MS       = 20
CHUNKS_SILENCE = SILENCE_MS // CHUNK_MS


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()

    call_sid      = ""
    audio_chunks  = []
    silent_chunks = 0
    is_speaking   = False

    try:
        async for message in websocket.iter_text():
            data  = json.loads(message)
            event = data.get("event", "")

            if event == "start":
                call_sid = data["start"]["callSid"]
                get_session(call_sid)
                print(f"[WS] Stream open: {call_sid[:20]}...")

            elif event == "media":
                mulaw_raw = base64.b64decode(data["media"]["payload"])
                pcm_chunk = mulaw_to_pcm16(mulaw_raw)
                energy    = np.abs(pcm_chunk).mean()

                if energy > 0.005:
                    is_speaking   = True
                    silent_chunks = 0
                    audio_chunks.append(pcm_chunk)

                elif is_speaking:
                    silent_chunks += 1
                    audio_chunks.append(pcm_chunk)

                    if silent_chunks >= CHUNKS_SILENCE:
                        t = Timer()
                        chunks_to_process = audio_chunks.copy()
                        audio_chunks      = []
                        silent_chunks     = 0
                        is_speaking       = False

                        # STT
                        t.start("STT")
                        user_text = transcribe_chunks(chunks_to_process)
                        t.end("STT")

                        if not user_text:
                            continue

                        print(f"\n[USER] '{user_text}'")
                        session = get_session(call_sid)

                        # Exit
                        if any(w in user_text for w in EXIT_WORDS):
                            t.start("TTS")
                            audio = synthesize_speech(
                                "Take care, and don't hesitate to call us again. Goodbye!"
                            )
                            t.end("TTS")
                            t.summary()
                            clear_session(call_sid)
                            await _update_call(call_sid, twiml_hangup(f"{BASE_URL}/{audio}"))
                            break

                        # Greeting
                        if user_text.strip().rstrip(".,!?") in GREETINGS:
                            t.start("TTS")
                            audio = synthesize_speech(
                                "Hey there! How can I help you with your billing today?"
                            )
                            t.end("TTS")
                            t.summary()
                            await _update_call(call_sid, twiml_play_and_stream(f"{BASE_URL}/{audio}"))
                            continue

                        # Generate reply
                        asyncio.create_task(_reply(call_sid, user_text, t))

            elif event == "stop":
                print(f"[WS] Stream closed: {call_sid[:20]}...")
                break

    except WebSocketDisconnect:
        print(f"[WS] Disconnected: {call_sid[:20]}...")
    except Exception as e:
        print(f"[WS] Error: {e}")


async def _reply(call_sid: str, user_text: str, t: Timer):
    """LLM + TTS → direct reply."""
    session = get_session(call_sid)
    session["history"].append(f"Patient: {user_text}")

    t.start("LLM")
    reply = await asyncio.to_thread(generate_response, user_text, session["history"])
    t.end("LLM")

    session["history"].append(f"Priya: {reply}")
    print(f"[SARAH] '{reply}'")

    t.start("TTS")
    audio_path = await asyncio.to_thread(synthesize_speech, reply)
    t.end("TTS")

    t.summary()

    if audio_path:
        await _update_call(call_sid, twiml_play_and_stream(f"{BASE_URL}/{audio_path}"))


async def _update_call(call_sid: str, twiml: str):
    try:
        await asyncio.to_thread(
            requests.post,
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{call_sid}.json",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"Twiml": twiml},
            timeout=10
        )
    except Exception as e:
        print(f"[Twilio] REST error: {e}")


# ── Call status ──
@app.post("/call-status")
async def call_status(request: Request):
    form     = await request.form()
    call_sid = form.get("CallSid", "")
    status   = form.get("CallStatus", "")
    print(f"[CALL] {call_sid[:20]}... → {status}")
    if status in ("completed", "failed", "busy", "no-answer"):
        
        clear_session(call_sid)
    return Response("", status_code=204)