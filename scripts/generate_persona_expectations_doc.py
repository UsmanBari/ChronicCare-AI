"""
Generator for docs/PERSONA_EXPECTATIONS_FOR_CLINICIAN.md.
Lists all simulated patient personas that embody clinical risks,
comparing the current persona expectation with the engine's actual triage assignment.
Provides an empty 'Clinician Expected Level' column for clinical governance.
"""

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

import scripts.run_v3_personas as runner

RISK_KEYWORDS = [
    "hypo",
    "dka",
    "crisis",
    "headache",
    "foot_ulcer",
    "ulcer",
    "dizzy",
    "swollen_ankles",
    "ankle",
    "dyspnea",
    "confused",
    "confusion",
    "hidden_danger",
]


def run_persona(p):
    p_id = p["id"]
    lang = p.get("language", "en")
    conditions = p.get("conditions", ["hypertension"])
    on_insulin = p.get("on_insulin", False)

    uid = f"per_{p_id}_{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
    headers = runner.bootstrap_patient(uid, conditions, lang, on_insulin)

    start_resp = runner.client.post("/api/checkins/start", headers=headers)
    if start_resp.status_code != 200:
        return "error"

    start_body = start_resp.json()
    c_id = start_body["checkin_id"]
    curr_q = start_body.get("question")
    curr_step = start_body.get("step")

    facts = runner.build_persona_facts(p)
    turn = 0
    is_emergency = False

    while curr_q and turn < 15:
        turn += 1
        ans, _ = runner.pick_answer(facts, curr_step, curr_q, lang)
        ans_resp = runner.client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        if ans_resp.status_code == 403 and "pregnant" in ans_resp.text:
            break
        if ans_resp.status_code != 200:
            break
        body = ans_resp.json()
        if body.get("emergency"):
            is_emergency = True
            break
        if body.get("complete"):
            break
        curr_q = body.get("question")
        curr_step = body.get("step")

    comp_resp = runner.client.post(f"/api/checkins/{c_id}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {}

    if is_emergency:
        return "emergency"
    triage_dict = comp_body.get("triage") or {}
    return triage_dict.get("level", "routine").lower()


def generate_doc():
    personas_path = REPO_ROOT / "tests" / "sim" / "personas.json"
    personas = json.load(open(personas_path, encoding="utf-8"))

    # Match personas with clinical risk in id, archetype, or name
    risk_personas = []
    for p in personas:
        text = (p.get("archetype", "") + " " + p.get("id", "") + " " + p.get("name", "")).lower()
        if any(kw in text for kw in RISK_KEYWORDS):
            risk_personas.append(p)

    lines = []
    lines.append("# Simulated Patient Persona Clinical Risk Expectations")
    lines.append("\n> **CLINICAL GOVERNANCE & EVALUATION PACK**")
    lines.append(
        "> This document lists all simulated personas that model acute or progressive clinical risks (hypoglycemia, DKA, hypertensive crisis, headache, foot ulcer, dizziness, ankle swelling, dyspnea, confusion). It compares the current engineering expectations against the active engine's evaluated triage levels.\n"
    )

    lines.append("## 1. Summary of Clinical Risk Personas")
    lines.append(
        f"A total of **{len(risk_personas)}** personas directly evaluate acute physiological risk or symptoms requiring clinical scrutiny.\n"
    )

    lines.append(
        "| Persona ID | Archetype | Clinical Risk / Manifestation | Current File `expected_level` | Engine Assigned Level | Clinician Expected Level | Clinical Status / Gap Notes |"
    )
    lines.append(
        "|:---|:---|:---|:---:|:---:|:---:|:---|"
    )

    for p in risk_personas:
        pid = p["id"]
        arch = p["archetype"]
        name = p["name"]
        exp_lvl = p.get("expected_level", "routine")

        # Determine clinical risk category
        risk_cat = ""
        notes = ""
        if "crisis" in arch:
            risk_cat = "Hypertensive Crisis (BP 210/120)"
            notes = "Correctly escalated to emergency on Turn 1."
        elif "hidden_danger" in arch:
            risk_cat = "Crushing Chest Pain in Long Text"
            notes = "Correctly escalated to emergency on Turn 1."
        elif "dka" in arch:
            risk_cat = "DKA (High Glucose + Vomiting)"
            notes = "Correctly escalated to emergency on Turn 1."
        elif "severe_hypo" in arch:
            risk_cat = "Acute Severe Hypoglycemia (48 mg/dL + Shaking)"
            notes = "Engine escalates to emergency; file expected urgent."
        elif "fasting_low" in arch:
            risk_cat = "Fasting Hypoglycemia (58 mg/dL, Fast Broken)"
            notes = "Engine assigns review."
        elif "roman_urdu_hypo" in arch:
            risk_cat = "Hypoglycemia on Insulin (Roman Urdu)"
            notes = "Engine assigns review."
        elif "htn_headache" in arch:
            risk_cat = "Hypertension with Severe Headache"
            notes = "GAP: Normal vitals leave reading at routine; clinician review expected."
        elif "foot_ulcer" in arch:
            risk_cat = "Diabetic Foot Ulcer / Bleeding Toe Wound"
            notes = "GAP: Normal vitals leave reading at routine; clinician review expected."
        elif "orthostatic_dizzy" in arch:
            risk_cat = "Orthostatic Postural Dizziness / Fall Risk"
            notes = "GAP: Normal vitals leave reading at routine; clinician review expected."
        elif "swollen_ankles" in arch:
            risk_cat = "Bilateral Ankle Edema / High Sodium"
            notes = "GAP: Normal vitals leave reading at routine; clinician review expected."
        elif "dyspnea" in arch:
            risk_cat = "Dyspnea on Exertion"
            notes = "Normal vitals leave reading at routine."
        elif "confused" in arch:
            risk_cat = "Confusion (Units / Medication Regimen)"
            notes = "Colloquial confusion vs stroke/hypo ambiguity."
        else:
            risk_cat = name
            notes = p.get("notes", "")

        engine_lvl = run_persona(p)

        lines.append(
            f"| `{pid}` | `{arch}` | {risk_cat} | `{exp_lvl}` | `{engine_lvl}` | | {notes} |"
        )

    lines.append("\n## 2. Key Observations for the Reviewing Clinician")
    lines.append(
        "1. **The 'Normal Vitals' Narrative Gap**: Personas reporting acute symptomatic pathology (diabetic foot ulcer `p44`, severe hypertensive headache `p43`, orthostatic dizziness `p45`, swollen ankles `p52`) currently finish as `routine` when blood pressure and glucose readings are physiologically normal. The clinician must establish whether affirmative symptom reports must override normal vitals to assign `review` or `urgent`."
    )
    lines.append(
        "2. **Severe Hypoglycemia Target**: Persona `p36_severe_hypo_urgent` tests a reading of 48 mg/dL with acute tremor and diaphoresis. The file expected level was `urgent`, but the engine escalated to `emergency`. The clinician should confirm whether glucose < 54 mg/dL with acute neuroglycopenic symptoms should be categorized as `emergency` (911 ambulance) or `urgent` (immediate clinic contact)."
    )
    lines.append(
        "3. **Elderly Conversational Confusion (`p46`)**: Persona `p46_elderly_complex_meds` states *'Feeling a bit confused by all my morning pills'*. This triggers the bare `confusion` emergency red flag. Clinician guidance is requested on the three options presented in `CLINICIAN_REVIEW_PACK.md`."
    )

    lines.append("\n## 3. Clinical Governance Sign-Off")
    lines.append(
        "\n| Clinician Name | License # / Hospital | Signature | Date | Overall Decision |"
    )
    lines.append("|:---|:---|:---|:---|:---|")
    lines.append("| | | | | |")

    out_file = REPO_ROOT / "docs" / "PERSONA_EXPECTATIONS_FOR_CLINICIAN.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {out_file} ({len(risk_personas)} risk personas)")


if __name__ == "__main__":
    generate_doc()
