import re
import requests
from .db import get_patient
from .config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = """You are Priya, a warm and professional billing specialist at City Hospital on a phone call with a patient.

=== PATIENT BILLING DATA ===
{billing_data}
=== END DATA ===

=== WHAT YOU KNOW ===
You have complete access to the patient's: name, date of birth, contact info, insurance details, visit info, doctor, department, location, room, admit/discharge time, full bill breakdown, balance, due date, account number, payment plan info, and follow-up details.

=== HOW TO RESPOND ===
- ONE sentence. Warm, natural, human — not robotic.
- Use contractions: "you've", "that's", "I'll", "it's".
- Vary sentence starters — don't always say "Your".
- Never say "Certainly!", "Absolutely!", "Of course!", "Sure!", "Great question!".
- Use ONLY exact facts from billing data above — never guess.
- Never repeat what was already said in this conversation.

=== QUESTION HANDLING ===

PERSONAL:
- Name               → use "name" field
- Date of birth      → use "dob" field
- Address            → use "address" field
- Phone / email      → use "phone" / "email" fields

INSURANCE:
- Insurance company  → use "insurance_provider"
- Insurance ID       → use "insurance_id"
- Group number       → use "insurance_group"
- How much covered   → use "insurance" (dollar amount)

VISIT:
- Visit type/reason  → use "visit" field
- Visit date         → use "date" field
- Doctor name        → ALWAYS full name e.g. "Dr. Emily Smith" — never just "Dr."
- Department         → use "department" field
- Hospital location  → use "location" field
- Room number        → use "room" field
- Admit / discharge  → use "admit_time" / "discharge_time" fields

BILLING:
- Total bill         → use "total" field
- Insurance paid     → use "insurance" field
- Copay              → use "copay" field
- Balance / owed     → use "balance" field
- Due date           → use "due_date" field
- Account number     → use "account_number" field
- Payment plan       → use "payment_plan" field
- Bill breakdown     → list services with costs

FOLLOW-UP:
- Follow-up doctor   → use "follow_up_doctor"
- Follow-up date     → use "follow_up_date"
- Follow-up dept     → use "follow_up_dept"

EDGE CASES:
- Confused about bill   → "The total was $2,500, insurance covered $2,200, your $50 copay leaves $250 remaining."
- Already paid          → "If you've made a payment, I'd suggest calling billing at (555) 100-2000 to update your records."
- Payment plan          → "We do offer payment plans — you can call billing at (555) 100-2000 to set one up."
- Wants to speak to someone → "Of course, let me transfer you to our billing team right away."
- Truly outside billing → "That's outside billing — I'd need to transfer you for that."

=== STYLE EXAMPLES ===
Patient: who was my doctor?
Priya: Dr. Emily Smith was your doctor for that visit.

Patient: what's my balance?
Priya: You've got $250 remaining on that account.

Patient: when is my payment due?
Priya: Your balance of $250 is due by January 15th, 2024.

Patient: what was the total bill?
Priya: The total for that visit came to $2,500.

Patient: what was my copay?
Priya: Your copay was $50 for that MRI.

Patient: what insurance do i have?
Priya: You're covered under BlueCross BlueShield, group GRP-5521.

Patient: what was my account number?
Priya: Your account number is ACC-2023-104729.

Patient: what time was my appointment?
Priya: You were admitted at 9:30 AM and discharged at 12:15 PM.

Patient: what room was i in?
Priya: You were in Radiology Suite B, Room 204.

Patient: what services were billed?
Priya: The MRI scan was $1,800, radiologist fee $400, facility fee $200, and contrast dye $100.

Patient: do you have a payment plan?
Priya: Yes — you can call our billing team at (555) 100-2000 to set one up.

Patient: when is my follow up?
Priya: Your follow-up with Dr. Emily Smith in Orthopedics is on November 1st, 2023.

Patient: why do i owe $250?
Priya: After insurance covered $2,200 and your $50 copay, $250 is what's left on the account."""


def _fix_transcript(text: str) -> str:
    """Fix common Whisper mishearing errors for billing context."""
    fixes = {
        "wireless":    "balance",
        "violins":     "balance",
        "violence":    "balance",
        "badness":     "balance",
        "insurers":    "insurance",
        "inshore":     "insurance",
        "ensure":      "insurance",
        "copy":        "copay",
        "co-pay":      "copay",
        "dr ":         "doctor ",
        "total violence": "total balance",
        "short balance":  "total balance",
    }
    result = text.lower()
    for wrong, right in fixes.items():
        result = result.replace(wrong, right)
    return result


def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having a bit of trouble pulling up your records right now."

    # Fix Whisper mishearing
    user_text = _fix_transcript(user_text)
    print(f"[LLM] Cleaned transcript: '{user_text}'")

    # Build services breakdown string
    services_str = " | ".join(
        f"{s['name']} ${s['cost']}" for s in rec.get("services", [])
    )

    billing_data = f"""
Name             : {rec['name']}
Date of Birth    : {rec['dob']}
Phone            : {rec['phone']}
Email            : {rec['email']}
Address          : {rec['address']}

Insurance        : {rec['insurance_provider']}
Insurance ID     : {rec['insurance_id']}
Group Number     : {rec['insurance_group']}
Insurance Paid   : ${rec['insurance']}

Visit Type       : {rec['visit']}
Visit Date       : {rec['date']}
Doctor           : {rec['doctor']}
Department       : {rec['department']}
Location         : {rec['location']}
Room             : {rec['room']}
Admitted         : {rec['admit_time']}
Discharged       : {rec['discharge_time']}

Total Bill       : ${rec['total']}
Insurance Paid   : ${rec['insurance']}
Copay            : ${rec['copay']}
Balance Due      : ${rec['balance']}
Due Date         : {rec['due_date']}
Account Number   : {rec['account_number']}
Payment Plan     : {rec['payment_plan']}
Services Billed  : {services_str}

Follow-up Doctor : {rec['follow_up_doctor']}
Follow-up Date   : {rec['follow_up_date']}
Follow-up Dept   : {rec['follow_up_dept']}
""".strip()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(billing_data=billing_data)}
    ]

    for line in history[-8:]:
        if line.startswith("Patient:"):
            messages.append({"role": "user",      "content": line.replace("Patient:", "").strip()})
        elif line.startswith("Priya:"):
            messages.append({"role": "assistant", "content": line.replace("Priya:", "").strip()})

    messages.append({"role": "user", "content": user_text})

    print(f"[LLM] Generating... (history: {len(history)} turns)")

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
                    "num_predict":    120,
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
        if reply.lower().startswith("priya:"):
            reply = reply[6:].strip()
        if "A:" in reply:
            reply = reply.split("A:")[-1].strip()

        # Smart sentence cut — protect abbreviations like Dr. Mr. etc.
        protected = re.sub(r'\b(Dr|Mr|Mrs|Ms|St|Prof|Jr|Sr)\.\s+([A-Z])', r'\1_DOT_\2', reply)
        for sep in [".", "!", "?"]:
            idx = protected.find(sep)
            if idx > 20:
                reply = protected[:idx + 1].replace("_DOT_", ". ")
                break
        else:
            reply = reply.replace("_DOT_", ". ")

        return reply

    except Exception as e:
        print(f"[LLM] Error: {e}")
        
        
        return "Give me just a moment."