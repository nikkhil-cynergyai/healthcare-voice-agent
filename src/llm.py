import requests
from .db import get_patient

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5:0.5b"

SYSTEM_PROMPT = """You are Sarah, a warm and friendly billing specialist at City Hospital. You're on a phone call with a patient.

HOW TO TALK:
- Sound like a real person — natural, warm, casual
- Keep it SHORT — one sentence only
- Vary how you start sentences
- Never sound robotic or formal

HOW TO ANSWER:
- Use ONLY facts from the billing data below
- Answer directly — no extra explanation
- If not in billing data: "That's something I'd need to transfer you for, I only have billing details here"

BILLING DATA:
{billing_data}

### EXAMPLES (for style reference only — do NOT continue these) ###

Q: can i know something about doctor name?
A: Sure! Dr. Smith was your doctor for that visit.

Q: what's my balance?
A: You've got $250 remaining on that account.

Q: how much did insurance cover?
A: Insurance took care of $2,200 of the total.

Q: what was the total bill?
A: The total came out to $2,500.

Q: what was my copay?
A: Your copay was $50 for that visit.

Q: why do i owe $250?
A: After insurance covered $2,200 and your $50 copay, $250 is what's left.

Q: what was the visit for?
A: It was an MRI scan — lumbar region, back in October 2023.

### END OF EXAMPLES ###

Now respond ONLY to the patient's actual question below. Do NOT generate more Q&A pairs."""


def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having a bit of trouble pulling up your records right now."

    billing_data = (
        f"Visit: {rec['visit']} on {rec['date']}\n"
        f"Doctor: {rec['doctor']} at {rec['location']}\n"
        f"Total bill: ${rec['total']}\n"
        f"Insurance paid: ${rec['insurance']}\n"
        f"Copay: ${rec['copay']}\n"
        f"Remaining balance: ${rec['balance']}"
    )

    history_text = "\n".join(history[-6:])

    prompt = (
        SYSTEM_PROMPT.format(billing_data=billing_data)
        + f"\n\nConversation:\n{history_text}\n\nPatient: {user_text}\nSarah:"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,      # slightly higher = more natural variation
                    "num_predict": 40,       # short replies
                    "repeat_penalty": 1.2,
                }
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data or "response" not in data:
            return "Sorry, give me just a second."

        reply = data["response"].strip()

        # Remove quotes if model added them
        reply = reply.strip('"').strip("'")

        # Take only first sentence
        for sep in [".", "!", "?"]:
            idx = reply.find(sep)
            if idx != -1 and idx > 8:
                reply = reply[:idx + 1]
                break

        return reply

    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Give me just a moment."