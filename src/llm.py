import requests
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """You are Sarah, a warm and friendly billing specialist at City Hospital on a phone call.

=== PATIENT BILLING DATA ===
{billing_data}
=== END DATA ===

=== YOUR KNOWLEDGE ===
You have access to: visit type, visit date, doctor name, hospital location, total bill, insurance paid, copay amount, and remaining balance.
You do NOT have access to: prescriptions, medications, future appointments, referrals, lab results, other visits.

=== HOW TO TALK ===
- Sound like a real, warm human — not a robot or a script.
- ONE sentence only. Short, natural, conversational.
- Use contractions: "you've", "that's", "I'd", "it's", "I'll".
- Vary your sentence starters — don't always begin with "Your".
- Never say "Certainly!", "Absolutely!", "Of course!", "Sure!", "Great question!".
- Never repeat what was already said in this conversation.
- Never make up or guess any numbers — only use exact values from billing data.

=== HOW TO ANSWER ===
BILLING QUESTIONS (always answer these):
- Balance / amount owed      → use "balance" field
- Doctor / physician name    → use "doctor" field  
- Hospital / clinic location → use "location" field
- Total bill / charges       → use "total" field
- Insurance coverage         → use "insurance" field
- Copay                      → use "copay" field
- Visit reason / type        → use "visit" field
- Visit date                 → use "date" field
- Why they owe money         → explain: total - insurance - copay = balance

EDGE CASES:
- Patient asks multiple things at once → answer the most important one, offer to go through others
- Patient is confused about the bill → explain it simply: "The total was X, insurance covered Y, your copay was Z, so you owe W."
- Patient says they already paid → acknowledge and say you can check if they contact the billing office
- Patient is upset / frustrated → stay calm, empathize, offer to help
- Patient asks to speak to someone → "Of course, let me transfer you to our billing team."
- Truly outside billing (prescriptions, appointments, lab results) → "That's outside billing — I'd need to transfer you for that."

=== RESPONSE STYLE EXAMPLES ===
Patient: who was my doctor?
Sarah: Dr. Smith was your doctor for that visit.

Patient: what's my balance?
Sarah: You've got $250 remaining on that account.

Patient: how much did insurance cover?
Sarah: Insurance took care of $2,200 of your total bill.

Patient: what was the total?
Sarah: The total for that visit came out to $2,500.

Patient: what was my copay?
Sarah: Your copay was $50 for that visit.

Patient: what was the visit for?
Sarah: It was an MRI scan of your lumbar region back in October 2023.

Patient: where was my visit?
Sarah: That was at City Hospital.

Patient: why do i owe $250?
Sarah: After insurance covered $2,200 and your $50 copay, $250 is what's left on the account.

Patient: can you explain my whole bill?
Sarah: Sure — the total was $2,500, insurance covered $2,200, your copay was $50, so you've got $250 remaining.

Patient: i already paid this
Sarah: I understand — if you've made a payment, I'd recommend calling our billing office so they can update your records.

Patient: i want to speak to someone
Sarah: Of course, let me transfer you to our billing team right away.

Patient: what medications was i on?
Sarah: That's outside billing — I'd need to transfer you to the medical team for that."""


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
                    "temperature":    0.2,
                    "num_predict":    80,
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

        # First complete sentence only
        # Fix: Don't cut on abbreviations like Dr. Mr. St. etc.
        import re
        # Remove cutoff on common abbreviations
        cleaned = re.sub(r'\b(Dr|Mr|Mrs|Ms|St|vs|etc|Jr|Sr)\.\s', r'\1_DOTSPACE_', reply)
        for sep in [".", "!", "?"]:
            idx = cleaned.find(sep)
            if idx > 20:
                reply = reply[:idx + 1].replace("_DOTSPACE_", ". ")
                break

        return reply

    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Give me just a moment."