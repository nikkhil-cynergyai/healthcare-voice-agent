import requests
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """You are Sarah, a friendly billing specialist at City Hospital on a phone call with a patient.

=== PATIENT BILLING DATA ===
{billing_data}
=== END DATA ===

HOW TO RESPOND:
- Sound like a real, warm human — not a robot.
- ONE sentence only. Conversational and natural.
- Use contractions: "you've", "that's", "I'll", "it's".
- Vary your openings — don't always start with "Your".
- Use ONLY facts from BILLING DATA. Never guess.
- BILLING DATA includes visit, date, doctor, location, total, insurance, copay, balance — answer all of these.
- Only say you can't help if the question is truly outside billing (prescriptions, appointments, medications).
- Never say "Certainly", "Absolutely", "Of course", "Sure!".
- Never repeat what you already told them in this conversation.

RESPONSE STYLE EXAMPLES:
Patient: who was my doctor?
Sarah: Dr. Smith handled your visit.

Patient: what's my balance?
Sarah: You've got $250 left on that account.

Patient: how much did insurance cover?
Sarah: Insurance took care of $2,200 of the total.

Patient: what was the total bill?
Sarah: The total came out to $2,500.

Patient: what was my copay?
Sarah: Your copay for that visit was $50.

Patient: what was the visit for?
Sarah: It was an MRI scan of your lumbar region back in October 2023.

Patient: where was my visit?
Sarah: That was at City Hospital.

Patient: why do i owe $250?
Sarah: After insurance covered $2,200 and your $50 copay, $250 is what's remaining.

Patient: can you tell me everything about my bill?
Sarah: Sure — you had an MRI on October 15th, the total was $2,500, insurance covered $2,200, your copay was $50, and you've got $250 left.

Patient: what medications was i prescribed?
Sarah: That's outside billing — I'd need to transfer you for that."""


def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having a bit of trouble pulling up your records right now."

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
                "options":  {
                    "temperature": 0.2,
                    "num_predict": 80,      # increased — no more cut-off
                    "repeat_penalty": 1.2,
                }
            },
            timeout=30
        )
        r.raise_for_status()
        reply = r.json().get("message", {}).get("content", "").strip()

        if not reply:
            return "Give me just a moment."

        # Clean up
        reply = reply.strip('"').strip("'")
        if reply.lower().startswith("sarah:"):
            reply = reply[6:].strip()
        if "A:" in reply:
            reply = reply.split("A:")[-1].strip()

        # Take only first sentence — but make sure it's complete
        # Find first sentence ending after at least 20 chars
        for sep in [".", "!", "?"]:
            idx = reply.find(sep)
            if idx > 20:
                reply = reply[:idx + 1]
                break

        return reply

    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Give me just a moment."