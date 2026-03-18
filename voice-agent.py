import os
import warnings
import logging

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

logging.basicConfig(level=logging.INFO, format="%(levelname)s:voice-agent:%(message)s")
log = logging.getLogger("voice-agent")

import re
import queue
import numpy as np
import sounddevice as sd

WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"

VOICE = "af_heart"
LANG = "en-us"
SPEED = 1.0

SR = 16000
CHANNELS = 1
CHUNK = 0.03
SILENCE_THRESH = 0.015
SILENCE_TIME = 1.2

EXIT_WORDS = {"bye", "stop", "exit", "thank you", "thanks"}

# ================= PATIENT DB =================
PATIENT_DB = {
    "P1023": {
        "name": "nikhil",
        "dob": "2000-12-24",
        "visit": "MRI Scan (Lumbar)",
        "date": "2023-10-15",
        "doctor": "Dr. Smith",
        "location": "City Hospital",
        "total": 2500,
        "insurance": 2200,
        "copay": 50,
        "balance": 250
    },
    "P2044": {
        "name": "john doe",
        "dob": "1985-01-01",
        "visit": "CT Brain",
        "date": "2023-09-01",
        "doctor": "Dr. Adams",
        "location": "Metro Clinic",
        "total": 1800,
        "insurance": 1500,
        "copay": 100,
        "balance": 200
    }
}

# ================= INIT =================
def init_whisper():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

def init_tts():
    from kokoro import KPipeline
    return KPipeline(lang_code=LANG, repo_id="hexgrad/Kokoro-82M")

# ================= NORMALIZE =================
def normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()

# ================= AUDIO =================
def record_audio():
    chunk_size = int(SR * CHUNK)
    silence_chunks = int(SILENCE_TIME / CHUNK)

    q = queue.Queue()
    buf = []
    silent = 0
    speaking = False

    def cb(indata, frames, t, status):
        q.put(indata.copy())

    with sd.InputStream(samplerate=SR, channels=CHANNELS,
                        dtype="float32", blocksize=chunk_size,
                        callback=cb):
        while True:
            data = q.get()
            rms = float(np.sqrt(np.mean(data**2)))

            if rms > SILENCE_THRESH:
                speaking = True
                silent = 0
                buf.append(data)
            elif speaking:
                buf.append(data)
                silent += 1
                if silent >= silence_chunks:
                    break

    if not buf:
        return np.zeros(chunk_size, dtype=np.float32)

    return np.concatenate(buf).flatten()

# ================= STT =================
def transcribe(model, audio):
    segments, _ = model.transcribe(audio.astype(np.float32))
    text = " ".join(s.text for s in segments).strip().lower()
    log.info(f"User: {text}")
    return text

# ================= TTS =================
def speak(tts, text):
    if not text:
        return

    log.info(f"Bot: {text}")

    audio_parts = []
    for _, _, audio in tts(text, voice=VOICE, speed=SPEED):
        if audio is not None and len(audio) > 0:
            audio_parts.append(audio)

    if audio_parts:
        audio = np.concatenate(audio_parts)
        sd.play(audio, samplerate=24000)
        sd.wait()
def extract_name(text):
    text = normalize(text)

    # remove greetings + fillers
    text = re.sub(r"\b(hi|hello|hey|my|name|is|this|i am|im)\b", "", text)
    words = re.findall(r"[a-z]+", text)

    if not words:
        return None

    # assume last word(s) = name
    return words[-1] if len(words) == 1 else " ".join(words)

def extract_dob(text):
    text = normalize(text)

    # remove ordinal suffixes: 24th → 24
    text = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", text)

    months = {
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
    }

    m = re.search(r"\b(\d{1,2})\s*(%s)\s*(\d{4})\b" % "|".join(months.keys()), text)
    if m:
        day = int(m.group(1))
        month = months[m.group(2)]
        year = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    return None

def extract_pid(text):
    m = re.search(r"p\s*[\- ]?\s*(\d{3,5})", text.lower())
    if m:
        return f"P{m.group(1)}"
    return None

def is_exit(text):
    return any(w in text for w in EXIT_WORDS)

# ================= VERIFY =================
def verify(pid, name, dob):
    rec = PATIENT_DB.get(pid)
    if not rec:
        return False, None
    if rec["name"] == name and rec["dob"] == dob:
        return True, rec
    return False, None

# ================= MAIN =================
def main():
    whisper = init_whisper()
    tts = init_tts()

    state = "NAME"
    name = None
    dob = None
    pid = None
    verified_record = None

    speak(tts, "Hello. Please tell me your full name.")

    while True:
        audio = record_audio()
        text = transcribe(whisper, audio)

        if not text:
            continue

        if state != "POST_VERIFY" and is_exit(text):
            speak(tts, "Goodbye and have a great day.")
            break

        # ===== NAME =====
        if state == "NAME":
            n = extract_name(text)
            if n:
                name = n
                log.info(f"Parsed name: '{name}'")
                speak(tts, "Thank you. Please tell your date of birth.")
                state = "DOB"
            else:
                speak(tts, "I did not catch your name. Please repeat.")

        # ===== DOB =====
        elif state == "DOB":
            d = extract_dob(text)
            if d:
                dob = d
                log.info(f"Parsed DOB: {dob}")
                speak(tts, "Thank you. Please tell your patient ID.")
                state = "PID"
            else:
                speak(tts, "I did not catch your date of birth. Please repeat.")

        # ===== PID =====
        elif state == "PID":
            p = extract_pid(text)
            if p:
                pid = p
                log.info(f"Parsed PID: {pid}")
                ok, rec = verify(pid, name, dob)

                if ok:
                    verified_record = rec
                    speak(tts, f"Thank you {rec['name']}. Your verification is complete.")
                    speak(
                        tts,
                        f"You had a {rec['visit']} on {rec['date']} at {rec['location']} "
                        f"with {rec['doctor']}. The remaining balance is {rec['balance']} dollars."
                    )
                    speak(tts, "What would you like to check more ?")
                    state = "POST_VERIFY"
                else:
                    speak(tts, "I am sorry. The details do not match our records. Please try again.")
                    state = "NAME"
            else:
                speak(tts, "I did not catch your patient ID. Please repeat.")

        # ===== POST VERIFY LOOP =====
        elif state == "POST_VERIFY":
            if is_exit(text):
                speak(tts, "You're welcome. Have a great day. Goodbye.")
                break

            if "balance" in text:
                speak(tts, f"Your remaining balance is {verified_record['balance']} dollars.")
            elif "visit" in text or "appointment" in text:
                speak(
                    tts,
                    f"Your last visit was {verified_record['visit']} on {verified_record['date']} "
                    f"with {verified_record['doctor']} at {verified_record['location']}."
                )
            else:
                speak(tts, "I can help with balance or visit details. What would you like to check?")

# ================= ENTRY =================
if __name__ == "__main__":
    main()