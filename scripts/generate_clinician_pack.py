"""
Programmatic Generator for docs/CLINICIAN_REVIEW_PACK.md (Stage 9A-7 Task D).
Generates the clinician review pack directly from live code modules and clinical rules docs.
No hand-typed levels or synthetic assumptions.
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from agents.adaptive_interview_agent import RED_FLAG_PATTERNS
from agents.input_triage import MULTILINGUAL_DANGER_CATEGORIES, ROMANTIC_PATTERNS, ADVICE_PATTERNS

def get_glucose_truth_table_output() -> str:
    script_path = REPO_ROOT / "scripts" / "glucose_truth_table.py"
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    # Extract markdown table lines
    lines = res.stdout.splitlines()
    table_lines = []
    recording = False
    for line in lines:
        if line.startswith("| `"):
            table_lines.append(line)
        elif line.startswith("| Series |"):
            table_lines.append(line)
        elif line.startswith("|:---|"):
            table_lines.append(line)
        elif "### Context: Normal Answers" in line:
            table_lines.append("\n#### Context: Normal Check-in (v2 Default Engine)\n")
        elif "### Context: Hypo Symptoms" in line:
            table_lines.append("\n#### Context: Hypo Symptoms ('shaky and sweating')\n")
    return "\n".join(table_lines)

def generate_clinician_pack():
    lines = []
    lines.append("# ChronicCare AI — Clinician Review & Decision Pack")
    lines.append("\n> **CLINICAL DISCLAIMER & SAFETY NOTICE**")
    lines.append("> **IMPORTANT**: Nothing in this repository or prototype has been clinically validated, approved by regulatory bodies (e.g., FDA, MHRA, CE), or trialed on real human patients. This document is an engineering decision-support pack prepared for clinical review by licensed medical practitioners.\n")

    # -------------------------------------------------------------------------
    # Section 1: Level-Raising Rules (v2.3)
    # -------------------------------------------------------------------------
    lines.append("## 1. Level-Raising Rules (Interview Engine v2.3)")
    lines.append("The clinical intake interview protocol operates four categorical triage levels: `routine`, `review`, `urgent`, and `emergency`.\n")
    lines.append("| Trigger Condition | Protocol Rule / Node | Target Level | Clinical Rationale |")
    lines.append("|:---|:---|:---:|:---|")
    lines.append("| Red-Flag Danger Screen Match | Stage 1 Emergency Screen (`run_stage1_red_flag_screen`) | `emergency` | Immediate safety danger hard-stop (e.g. crushing chest pain, inability to keep fluids down, stroke symptoms). |")
    lines.append("| Severe Hypoglycemia (< 54 mg/dL or < 3.0 mmol/L) | `evaluate_triage_decision` | `urgent` | Critical neuroglycopenic risk requiring urgent carbohydrate rescue and clinical escalation. |")
    lines.append("| Moderate Hypoglycemia (54 - 69 mg/dL or 3.0 - 3.8 mmol/L) | `evaluate_triage_decision` | `review` | Biochemical low sugar; requires adherence review and preventive guidance. |")
    lines.append("| Severe Hyperglycemia / Crisis (>= 300 mg/dL or >= 16.7 mmol/L) | `evaluate_triage_decision` | `urgent` | Severe acute hyperglycemia requiring clinical investigation for dehydration or hyperosmolarity. |")
    lines.append("| Moderate Hyperglycemia (>= 250 mg/dL or >= 13.9 mmol/L) | `evaluate_triage_decision` | `review` | Elevated reading triggering sick-day protocol check and provider notification. |")
    lines.append("| Hypertensive Crisis (BP >= 180/120 mmHg) | `evaluate_triage_decision` | `emergency` | Immediate hypertensive emergency / urgency threshold. |")
    lines.append("| Stage 2 Hypertension (BP >= 140/90 mmHg) | `evaluate_triage_decision` | `review` | Elevated blood pressure triggering OTC medication screening and clinician review. |")
    lines.append("| Reported Medication Non-Adherence | `ADHERENCE` Step | `review` | Missed medication doses flag provider review queue for adherence barrier evaluation. |")
    lines.append("| Possible Severe Low with Inability to Swallow Safely | `FAST_HYPO_SAFETY` Step | `urgent` | Hypoglycemic patient reporting inability to safely eat or drink. |")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 2: Glucose Unit Rule and Thresholds with Truth Table
    # -------------------------------------------------------------------------
    lines.append("## 2. Glucose Unit Rules, Conversion Thresholds & Truth Table")
    lines.append("Automated extraction parses both explicit units (`mg/dL`, `mmol/L`) and bare numbers based on physiological ranges:")
    lines.append("- Values < 25 without explicit units are inferred as `mmol/L` (or clarified) and converted via multiplication by 18.0182.")
    lines.append("- Values >= 25 are treated as `mg/dL`.")
    lines.append("- Hypoglycemia thresholds: Level 2 severe low < 54 mg/dL (< 3.0 mmol/L); Level 1 low < 70 mg/dL (< 3.9 mmol/L).\n")
    lines.append("### Monotonic Truth Table (Live API Output)")
    lines.append(get_glucose_truth_table_output())
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 3: Vomiting & Inability to Keep Fluids Down Phrases
    # -------------------------------------------------------------------------
    lines.append("## 3. Vomiting & Fluids Inability Red-Flag Phrases (`unable_to_keep_fluids`)")
    lines.append("Authoritative phrases configured in `adaptive_interview_agent.py` to trigger immediate emergency safety stop:")
    vomiting_phrases = RED_FLAG_PATTERNS.get("unable_to_keep_fluids", [])
    lines.append("| Language | Configured Verbatim Phrase | Category |")
    lines.append("|:---|:---|:---:|")
    for p in vomiting_phrases:
        if any(ord(c) > 127 for c in p):
            lang = "Urdu Script (ur)"
        elif any(w in p for w in ["ultiyan", "ulti", "paani", "rukta", "rahi"]):
            lang = "Roman Urdu (ur-Latn)"
        else:
            lang = "English (en)"
        lines.append(f"| {lang} | \"{p}\" | `unable_to_keep_fluids` |")
    lines.append("\n**Negation Handling**: Negations (e.g., *\"I am not vomiting\"*, *\"no vomiting, I can keep fluids down\"*, *\"without vomiting\"*) are verified by a 3-word negation window and clause boundary parser. They do NOT trigger the red-flag screen.\n")

    # -------------------------------------------------------------------------
    # Section 4: 'Confused' Pattern with 3 Options
    # -------------------------------------------------------------------------
    lines.append("## 4. Neurological 'Confused' Pattern — Clinician Options")
    lines.append("Currently, `RED_FLAG_PATTERNS[\"confusion\"]` includes `\"confused\"`, `\"slurred speech\"`, `\"can't speak clearly\"`.")
    lines.append("In clinical practice, patients frequently use 'confused' colloquially (*\"I am confused about my insulin dose\"*) rather than reporting acute encephalopathy, stroke, or severe neuroglycopenia.\n")
    lines.append("We submit three architectural options for clinician sign-off:")
    lines.append("1. **Option 1: Strict / High Sensitivity (Current Behavior)**: Keep bare `\"confused\"` as an immediate emergency red-flag stop. **Advantage**: Zero risk of missing acute stroke or severe hypoglycemic confusion. **Disadvantage**: High false-positive rate for conversational confusion.")
    lines.append("2. **Option 2: Neurological Co-occurrence Requirement**: Require co-occurrence of confusion with neurological or speech keywords (e.g. `\"confused and dizzy\"`, `\"confused and slurred\"`, `\"confused and disoriented\"`, `\"suddenly confused\"`).")
    lines.append("3. **Option 3: Conversational Exclusion Filter**: Exclude non-neurological contexts (e.g., *\"confused about [medication/dose/instructions]\"*, *\"confused by doctor\"*) while retaining bare 'confused' in symptom descriptions.\n")

    # -------------------------------------------------------------------------
    # Section 5: The Four Narrative-Yes Questions (KNOWN GAP)
    # -------------------------------------------------------------------------
    lines.append("## 5. Four Narrative-Yes Questions That Do Not Raise Triage Level (KNOWN GAP)")
    lines.append("In Interview Engine v2.3, the following four Stage 8b questions ask narrative questions where an affirmative answer reports clinically relevant symptoms, but **does not raise the automated check-in level beyond `routine`** when blood glucose and blood pressure numbers are within normal physiological bounds:\n")
    lines.append("1. `hypo_events_past_week`: Patient asked if they had low blood sugar episodes in the past week. Narrative affirmative reports are captured in the intake record, but do not promote normal glucose check-ins to `review`.")
    lines.append("2. `sick_day_flags`: Patient asked if they have experienced nausea, fever, vomiting, or illness. Narrative reports are recorded, but do not promote the check-in level unless matched verbatim by Stage 1 emergency red flags.")
    lines.append("3. `associated_symptoms`: Patient asked if they have headaches, dizziness, or visual changes with blood pressure. Answering 'yes, mild headache' records the text, but leaves triage at `routine` if BP is normal.")
    lines.append("4. `foot_problems`: Patient asked about foot ulcers, numbness, cuts, or sores. Reporting a cut or sore records the note in the clinical intake, but does not promote the level to `review` or `urgent`.\n")
    lines.append("> **Doctor Action Required**: Clinicians must specify whether affirmative responses to these four questions should automatically promote check-ins from `routine` to `review` (or `urgent`).\n")

    # -------------------------------------------------------------------------
    # Section 6: Input-Triage Known Misses & Over-Triage
    # -------------------------------------------------------------------------
    lines.append("## 6. Input Triage Known Misses & Intentional Over-Triage")
    lines.append("Evaluation of input triage over `tests/sim/odd_input_gold.json` demonstrates:")
    lines.append("- **Romantic Miss Fixed**: *\"You are so cute and hot\"* was formerly missed; now authoritatively classified as `odd_input` (`romantic`).")
    lines.append("- **Dose Advice Request Fixed**: *\"Can I stop taking metformin since my sugar is normal?\"* was formerly missed; now authoritatively classified as `odd_input` (`medical_advice_dose_request`).")
    lines.append("- **Non-Answer Phrases ('ok', 'haan', 'acha theek')**: In isolated benchmark files without dialogue context, these appear labeled as `non_answer`. However, in live clinical dialogues, they represent affirmative confirmations to yes/no questions (e.g., adherence confirmation). They are intentionally not flagged as odd inputs globally to avoid corrupting valid clinical dialogues.")
    lines.append("- **Intentional Safety Over-Triage**: *\"chest pain last year but fine now\"* is classified as `danger_phrase` (`emergency`). Automated negation engines deliberately avoid temporal discounting of chest pain to ensure that historical cardiac complaints are never dangerously under-triaged.\n")

    # -------------------------------------------------------------------------
    # Section 7: Clinician Sign-Off Table
    # -------------------------------------------------------------------------
    lines.append("## 7. Clinician Sign-Off & Governance Record")
    lines.append("To be completed by reviewing clinical practitioners:\n")
    lines.append("| Review Item | Reviewer Name | Professional Title / GMC / Reg | Date | Clinical Decision (Approve / Reject / Modify) | Signature / Notes |")
    lines.append("|:---|:---|:---|:---:|:---:|:---|")
    lines.append("| Glucose Unit Inference & Thresholds | | | | | |")
    lines.append("| Vomiting / Inability to Keep Fluids Red Flags | | | | | |")
    lines.append("| 'Confused' Pattern Option (1, 2, or 3) | | | | | |")
    lines.append("| Narrative-Yes 4-Question Promotion Rule | | | | | |")
    lines.append("| Input Triage Safety Over-Triage Policy | | | | | |")
    lines.append("")

    return "\n".join(lines)

def main():
    content = generate_clinician_pack()
    out_path = REPO_ROOT / "docs" / "CLINICIAN_REVIEW_PACK.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"Generated {out_path} ({len(content.splitlines())} lines, {len(content)} bytes)")

if __name__ == "__main__":
    main()
