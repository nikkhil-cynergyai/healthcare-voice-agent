import requests
from .db import get_patient

RUNPOD_URL = "https://vtagw7z69r7gvs-8000.proxy.runpod.net/chat"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen3:8b"

def generate_response(user_text: str, history: list, patient_id: str = "P1023") -> str:
    rec = get_patient(patient_id)
    if not rec:
        return "I'm having trouble pulling up your records right now."

    billing_data = (
        f"Visit: {rec['visit']} on {rec['date']}\n"
        f"Doctor: {rec['doctor']} at {rec['location']}\n"
        f"Total bill: ${rec['total']}\n"
        f"Insurance paid: ${rec['insurance']}\n"
        f"Copay: ${rec['copay']}\n"
        f"Remaining balance: ${rec['balance']}"
    )

    try:
        response = requests.post(
            RUNPOD_URL,
            json={"user_text": user_text, "history": history, "billing_data": billing_data},
            timeout=15
        )
        response.raise_for_status()
        reply = response.json().get("reply", "").strip()
        if reply:
            print("[LLM] RunPod GPU ✅")
            return reply
    except Exception as e:
        print(f"[RunPod] Failed: {e} — falling back to local Ollama")

    try:
        messages = [{"role": "system", "content": f"You are Sarah, billing specialist. Reply in ONE sentence. Use ONLY: {billing_data}"}]
        for line in history[-8:]:
            if line.startswith("Patient:"):
                messages.append({"role": "user", "content": line.replace("Patient:", "").strip()})
            elif line.startswith("Sarah:"):
                messages.append({"role": "assistant", "content": line.replace("Sarah:", "").strip()})
        messages.append({"role": "user", "content": user_text})

        r = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": messages, "stream": False, "think": False, "options": {"temperature": 0.15, "num_predict": 60}}, timeout=30)
        reply = r.json().get("message", {}).get("content", "").strip()
        print("[LLM] Local Ollama fallback ✅")
        for sep in [".", "!", "?"]:
            idx = reply.find(sep)
            if idx > 8:
                reply = reply[:idx+1]
                break
        return reply
    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return "Give me just a moment."
