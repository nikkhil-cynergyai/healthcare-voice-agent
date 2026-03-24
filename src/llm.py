import requests
import re
import random
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL


# ---------------- INTENT DETECTION ---------------- #

def detect_intent(text: str) -> str:
    t = text.lower()

    billing_keywords = [
        "bill", "balance", "pay", "payment", "charge",
        "insurance", "copay", "total", "amount",
        "doctor", "visit", "date", "hospital"
    ]

    fuzzy_map = {
        "build": "bill",
        "doc": "doctor",
        "dock": "doctor",
        "duck": "doctor",
    }

    for wrong, correct in fuzzy_map.items():
        t = t.replace(wrong, correct)

    if any(k in t for k in billing_keywords):
        return "billing"

    return "unknown"


# ---------------- HUMANIZER ---------------- #

def humanize(text: str) -> str:
    replacements = {
        "You have": "Looks like you’ve got",
        "Your": "It looks like your",
        "The total": "So the total",
    }

    for k, v in replacements.items():
        if text.startswith(k):
            text = text.replace(k, v, 1)

    prefixes = [
        "",
        "Looks like ",
        "From what I can see, ",
        "So, "
    ]

    text = random.choice(prefixes) + text.lower()
    return text.capitalize()


# ---------------- PROMPT ---------------- #

SYSTEM_PROMPT = """You are Sarah, a warm and friendly billing specialist at City Hospital on a phone call.

=== PATIENT BILLING DATA ===
{billing_data}
=== END DATA ===

=== HOW TO TALK ===
- Sound like a real human, slightly conversational.
- Keep responses short (1–2 sentences max).
- Use contractions naturally.
- Occasionally soften tone with:
  "looks like", "it seems", "from what I can see"
- Vary phrasing — don’t repeat patterns.
- Don't sound scripted or robotic.

=== HOW TO ANSWER ===
- Answer billing questions clearly using the data.
- If unclear but seems billing-related, assume it is.
- If truly unrelated:
  "Hmm, that doesn’t sound like billing — want me to connect you to the right team?"

=== STYLE EXAMPLES ===
"Looks like you've got $250 left on that account."
"So the total came out to $2,500, and insurance covered most of it."
"From what I can see, Dr. Smith was your doctor for that visit."
"""


# ---------------- MAIN FUNCTION ---------------- #

def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having a bit of trouble pulling up your records right now."

    intent = detect_intent(user_text)

    # fallback for short vague voice queries
    if intent == "unknown" and len(user_text.split()) <= 6:
        intent = "billing"

    billing_data = (
        f"- Visit type  : {rec['visit']}\n"
        f"- Visit date  : {rec['date']}\n"
        f"- Doctor      : {rec['doctor']}\n"
        f"- Location    : {rec['location']}\n"
        f"- Total bill  : ${rec['total']}\n"
        f"- Insurance   : ${rec['insurance']}\n"
        f"- Copay       : ${rec['copay']}\n"
        f"- Balance due : ${rec['balance']}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(billing_data=billing_data)}
    ]

    for line in history[-8:]:
        if line.startswith("Patient:"):
            messages.append({
                "role": "user",
                "content": line.replace("Patient:", "").strip()
            })
        elif line.startswith("Sarah:"):
            messages.append({
                "role": "assistant",
                "content": line.replace("Sarah:", "").strip()
            })

    messages.append({"role": "user", "content": user_text})

    print(f"[LLM] history={len(history)} | intent={intent}")

    # hard block
    if intent != "billing":
        return "Hmm, that doesn’t sound like billing — want me to connect you to the right team?"

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.4,  # 🔥 more human variation
                    "num_predict": 80,
                    "repeat_penalty": 1.1,
                }
            },
            timeout=30
        )
        r.raise_for_status()

        reply = r.json().get("message", {}).get("content", "").strip()

        if not reply:
            return "Just a second, pulling that up."

        # cleanup
        reply = reply.strip('"').strip("'")

        # sentence trimming
        cleaned = re.sub(r'\b(Dr|Mr|Mrs|Ms|St)\.\s', r'\1_DOT_', reply)
        for sep in [".", "!", "?"]:
            idx = cleaned.find(sep)
            if idx > 20:
                reply = reply[:idx + 1].replace("_DOT_", ". ")
                break

        # humanize
        reply = humanize(reply)

        return reply

    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Just a second, I’m checking that for you."