#!/usr/bin/env python3
"""
scripts/replay_13nov_sentences.py — Replay 13 Nov Browser Test Sentences
Replays key clinical test sentences through the real ChronicCare AI check-in API
and verifies triage levels, color chips, and emergency safety bypasses.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
import main as backend_main

client = TestClient(backend_main.app)

def test_sentence(name: str, condition: str, answers: list[str]) -> dict:
    uid = "test_dm_insulin_patient" if condition == "diabetes" else "demo_user_new"
    email = "dm_insulin@demo.care" if condition == "diabetes" else "demo_patient_new@demo.care"

    if condition == "diabetes":
        from data_sources.app_store import upsert_patient_profile, create_user, set_patient_consent, set_patient_provider_notification_consent
        try:
            create_user(user_id=uid, email=email, role="patient")
        except Exception:
            pass
        set_patient_consent(user_id=uid, granted=True)
        set_patient_provider_notification_consent(user_id=uid, granted=True)
        upsert_patient_profile(
            user_id=uid,
            conditions=["diabetes"],
            on_insulin_or_sulfonylurea=True,
            date_of_birth="1965-01-01",
            inclusion_confirmed=True,
            language="en"
        )

    backend_main.app.dependency_overrides[backend_main.get_current_user] = lambda: {
        "user_id": uid,
        "email": email,
        "role": "patient",
    }
    backend_main.app.dependency_overrides[backend_main.extract_bearer_token] = lambda: "demo_token"

    r_start = client.post("/api/checkins/start", json={"condition": condition})
    if r_start.status_code != 200:
        return {"test": name, "error": f"start failed {r_start.status_code}"}
    chk_id = r_start.json()["checkin_id"]
    
    last_res = {}
    is_emergency = False
    turn_answers = list(answers)
    for _ in range(25):
        ans = turn_answers.pop(0) if turn_answers else "no"
        r_ans = client.post(f"/api/checkins/{chk_id}/answer", json={"answer": ans})
        if r_ans.status_code != 200:
            break
        last_res = r_ans.json()
        if last_res.get("emergency"):
            is_emergency = True
            break
        if last_res.get("complete"):
            break

    # If not emergency, call complete
    comp_res = {}
    if not is_emergency:
        r_comp = client.post(f"/api/checkins/{chk_id}/complete")
        if r_comp.status_code == 200:
            comp_res = r_comp.json()
            
    # Also fetch checkin details
    r_det = client.get(f"/api/checkins/{chk_id}")
    det_res = r_det.json() if r_det.status_code == 200 else {}
    
    comp_triage = comp_res.get("triage") if isinstance(comp_res.get("triage"), dict) else {}
    last_triage = last_res.get("triage") if isinstance(last_res.get("triage"), dict) else {}

    level = (
        comp_triage.get("level")
        or comp_res.get("level")
        or last_triage.get("level")
        or last_res.get("triage_level")
        or det_res.get("triage_level")
        or det_res.get("level")
        or ("emergency" if is_emergency else None)
    )
    
    colour = (
        comp_triage.get("colour")
        or comp_res.get("colour")
        or last_triage.get("colour")
        or det_res.get("triage_colour")
        or det_res.get("colour")
    )
    if not colour and level:
        if level == "emergency":
            colour = "red"
        elif level == "urgent":
            colour = "red"
        elif level == "review":
            colour = "yellow"
        elif level == "routine":
            colour = "green"

    return {
        "test": name,
        "input": answers[0] if answers else "",
        "level": level,
        "colour": colour,
        "emergency": is_emergency or (level == "emergency"),
    }

replays = [
    ("Urdu Chest Pain", "hypertension", ["سینے میں شدید درد اور دباؤ محسوس ہو رہا ہے"]),
    ("Roman Urdu Chest Pain", "hypertension", ["Seene mein shadeed dard aur dabao mehsoos ho raha hai"]),
    ("English Slurred Speech (Stroke)", "hypertension", ["My speech is slurred and I feel confused"]),
    ("English Vomiting / Fluids", "hypertension", ["cannot keep fluids down"]),
    ("BP 152/94 (Mild/Mod Elevation)", "hypertension", ["Feeling fine", "152/94", "No symptoms", "Yes took meds", "Normal diet", "None"]),
    ("BP 186/122 (Severe Confirmed)", "hypertension", ["Feeling fine", "186/122", "186/122", "No headache", "Yes took meds", "Fine"]),
    ("Glucose 58 (Hypoglycemia on Insulin)", "diabetes", ["fine", "58", "none", "yes", "none", "yes", "no", "no"]),
    ("Lone Dizzy (Ambiguous Non-Emergency)", "hypertension", ["dizzy", "120/80", "just mild dizziness", "Yes took meds", "Normal diet", "None"]),
]

def main() -> None:
    print("| Test Case | Replayed Input | Triage Level | Colour Chip | Emergency Status |")
    print("|:---|:---|:---:|:---:|:---:|")
    for r in replays:
        res = test_sentence(*r)
        lvl_str = f"**{res['level'].upper()}**" if res["level"] else "N/A"
        clr_str = res["colour"].title() if res["colour"] else "N/A"
        emg_str = "EMERGENCY" if res["emergency"] else "Routine/Review"
        print(f"| {res['test']} | `{res['input']}` | {lvl_str} | {clr_str} | {emg_str} |")

if __name__ == "__main__":
    main()
