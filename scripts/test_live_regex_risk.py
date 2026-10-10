import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))

import scripts.run_v3_personas as runner
from agents.input_triage import classify_input

sentences = [
    ("It is so hot today and I feel dizzy", "symptom / weather"),
    ("so hot outside, sugar 110", "vitals / weather"),
    ("my feet feel so hot and burning", "symptom neuropathy"),
    ("the baby is so cute", "third party"),
    ("you are so cute", "bot compliment"),
    ("You are so cute and hot", "bot compliment (romantic)"),
    ("Can I skip breakfast?", "lifestyle"),
    ("Can I change my appointment?", "administrative"),
    ("can I stop taking metformin since my sugar is normal", "medication dose request"),
]

print(f"{'Sentence':<55} | {'Classification':<20} | {'Odd':<5} | {'Triage Level':<12} | {'Patient Told / Next Question'}")
print("-" * 155)

for s, cat in sentences:
    uid = f"user_{os.urandom(3).hex()}"
    tok = runner.get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    runner.client.post("/api/auth/session", headers=headers)
    runner.client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    runner.client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["diabetes", "hypertension"],
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )

    start_resp = runner.client.post("/api/checkins/start", headers=headers).json()
    cid = start_resp["checkin_id"]

    res = classify_input(s)
    class_label = f"{res.category}" + (f":{res.odd_class}" if res.odd_class else "")

    ans_resp = runner.client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": s}).json()
    odd_handled = ans_resp.get("handled_odd_input", False)

    comp = runner.client.post(f"/api/checkins/{cid}/complete", headers=headers).json()
    final_lvl = "emergency" if comp.get("emergency") else (comp.get("triage") or {}).get("level", "routine")

    bot_msg = ans_resp.get("question", "")
    if ans_resp.get("odd_input_message"):
        bot_msg = ans_resp.get("odd_input_message") + " -> " + bot_msg
    print(f"{s[:53]:<55} | {class_label:<20} | {str(odd_handled):<5} | {final_lvl:<12} | {bot_msg[:65]}")
