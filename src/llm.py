import requests
import re
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL


# ---------------- INTENT ---------------- #

def normalize(text: str) -> str:
    t = text.lower()

    fuzzy_map = {
        "build": "bill",
        "inshore": "insurance",
        "badless": "balance",
        "dock": "doctor",
        "doc": "doctor",
        "duck": "doctor",
    }

    for wrong, correct in fuzzy_map.items():
        t = t.replace(wrong, correct)

    return t


def detect_field(text: str) -> str:
    t = normalize(text)

    if "balance" in t:
        return "balance"
    if "doctor" in t:
        return "doctor"
    if "insurance" in t:
        return "insurance"
    if "copay" in t:
        return "copay"
    if "total" in t or "bill" in t:
        return "total"
    if "visit" in t or "what was my last billing" in t:
        return "visit"

    return "unknown"


# ---------------- DIRECT RESPONSES ---------------- #

def build_response(field: str, rec: dict) -> str:
    if field == "balance":
        return f"You’ve got ${rec['balance']} left on your account."

    if field == "doctor":
        return f"{rec['doctor']} was your doctor for that visit."

    if field == "insurance":
        return f"Insurance covered ${rec['insurance']} of your bill."

    if field == "copay":
        return f"Your copay was ${rec['copay']}."

    if field == "total":
        return f"The total bill was ${rec['total']}."

    if field == "visit":
        return f"That visit was for {rec['visit']} on {rec['date']}."

    return None


# ---------------- LLM (ONLY FOR EXPLANATION) ---------------- #

SYSTEM_PROMPT = """You are a natural human billing assistant.

Explain billing clearly using:
total, insurance, copay, balance.

Keep it short and natural.
No fillers.
"""


def call_llm(messages: list) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 80,
            }
        },
        timeout=30
    )
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()


# ---------------- MAIN ---------------- #

def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having trouble accessing your records."

    field = detect_field(user_text)

    print(f"[ROUTER] field={field}")

    # ✅ DIRECT DB RESPONSE (NO LLM)
    if field != "unknown":
        return build_response(field, rec)

    # 🤖 fallback to LLM (only complex queries)
    billing_data = (
        f"total: {rec['total']}, "
        f"insurance: {rec['insurance']}, "
        f"copay: {rec['copay']}, "
        f"balance: {rec['balance']}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_text}\n\nData: {billing_data}"}
    ]

    try:
        reply = call_llm(messages)

        if not reply:
            return "Let me check that for you."

        # clean sentence
        cleaned = re.sub(r'\b(Dr|Mr|Mrs|Ms|St)\.\s', r'\1_DOT_', reply)
        for sep in [".", "!", "?"]:
            idx = cleaned.find(sep)
            if idx > 20:
                reply = reply[:idx + 1].replace("_DOT_", ". ")
                break

        return reply

    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return "Let me check that for you."