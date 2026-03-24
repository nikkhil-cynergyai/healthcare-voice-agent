import requests
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """You are Sarah, a billing specialist at City Hospital on a phone call.

=== BILLING DATA (answer ALL questions from this) ===
{billing_data}
=== END BILLING DATA ===

RULES:
- Reply in ONE short sentence. Max 15 words.
- Use ONLY facts from BILLING DATA above.
- BILLING DATA includes doctor name, location, visit details — use them!
- Answer ONLY what was asked.
- Never say "Certainly", "Absolutely", "Of course".
- Never repeat info already said.
- Only say "That's outside billing" for things truly NOT in billing data
  (e.g. prescriptions, future appointments, insurance company phone numbers).
- Sound warm and natural like a real person.

EXAMPLES:
Patient: what's my balance?
Sarah: You've got $250 remaining on that account.

Patient: who was my doctor?
Sarah: Dr. Smith handled that visit.

Patient: where was the visit?
Sarah: That was at City Hospital.

Patient: how much did insurance cover?
Sarah: Insurance covered $2,200 of the total bill.

Patient: what was the total?
Sarah: The total for that visit was $2,500.

Patient: what was my copay?
Sarah: Your copay was $50.

Patient: what was the visit for?
Sarah: It was an MRI scan of the lumbar region in October 2023.

Patient: why do i owe $250?
Sarah: After insurance paid $2,200 and your $50 copay, $250 is what's left."""


def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having trouble pulling up your records right now."

    billing_data = (
        f"- Visit: {rec['visit']} on {rec['date']}\n"
        f"- Doctor: {rec['doctor']} at {rec['location']}\n"
        f"- Total bill: ${rec['total']}\n"
        f"- Insurance paid: ${rec['insurance']}\n"
        f"- Copay: ${rec['copay']}\n"
        f"- Remaining balance: ${rec['balance']}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(billing_data=billing_data)}
    ]

    for line in history[-8:]:
        if line.startswith("Patient:"):
            messages.append({"role": "user",      "content": line.replace("Patient:", "").strip()})
        elif line.startswith("Sarah:"):
            messages.append({"role": "assistant", "content": line.replace("Sarah:", "").strip()})

    messages.append({"role": "user", "content": user_text})

    print(f"[LLM] history={len(history)} turns")

    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model":    OLLAMA_MODEL,
                "messages": messages,
                "stream":   False,
                "think":    False,
                "options":  {"temperature": 0.15, "num_predict": 60}
            },
            timeout=30
        )
        r.raise_for_status()
        reply = r.json().get("message", {}).get("content", "").strip()

        if not reply:
            return "Give me just a moment."

        reply = reply.strip('"').strip("'")
        if reply.lower().startswith("sarah:"):
            reply = reply[6:].strip()
        if "A:" in reply:
            reply = reply.split("A:")[-1].strip()

        for sep in [".", "!", "?"]:
            idx = reply.find(sep)
            if idx > 8:
                reply = reply[:idx + 1]
                break

        return reply

    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Give me just a moment."