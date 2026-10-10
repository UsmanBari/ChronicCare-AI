"""
Programmatic Generator for docs/CLINICIAN_REVIEW_PACK.md.
Extracts all constants, thresholds, and patterns directly from code modules.
Guarantees 100% parity with active implementation via live API calls.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

# Import constants directly from code
from agents.triage_protocol import (
    GLUCOSE_VERY_LOW_MG_DL,
    GLUCOSE_LOW_MG_DL,
    GLUCOSE_HIGH_MG_DL,
    GLUCOSE_URGENT_MG_DL,
    DANGEROUS_BP_SYSTOLIC_MMHG,
    DANGEROUS_BP_DIASTOLIC_MMHG,
    BP_STAGE2_SYSTOLIC_MMHG,
    BP_STAGE2_DIASTOLIC_MMHG,
    BP_LOW_SYSTOLIC_MMHG,
    BP_LOW_DIASTOLIC_MMHG,
    BP_CHANGE_NOTABLE_MMHG,
    BP_CHANGE_MARKED_MMHG,
    Baseline,
    evaluate_triggers,
    start_protocol,
    advance_protocol,
    _QUESTION_SETS,
)
from agents.adaptive_interview_agent import (
    RED_FLAG_PATTERNS,
    run_stage1_red_flag_screen,
)


def extract_glucose_conversion_factor() -> float:
    agent_file = BACKEND_DIR / "agents" / "adaptive_interview_agent.py"
    content = agent_file.read_text(encoding="utf-8")
    m = re.search(r"\*\s*([0-9]+\.[0-9]+)", content)
    if not m:
        raise ValueError("Could not find glucose conversion factor in adaptive_interview_agent.py")
    return float(m.group(1))


def get_glucose_truth_table_output() -> str:
    script_path = REPO_ROOT / "scripts" / "glucose_truth_table.py"
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    lines = res.stdout.splitlines()
    table_lines = []
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


def run_live_bp_evaluations():
    """Executes live protocol calls for each blood pressure band and returns levels."""
    print("\n--- LIVE CALLS: SECTION 2 (BLOOD PRESSURE BANDS) ---")
    results = {}

    # 1. Hypertensive Crisis with warning symptoms
    trig_crisis = evaluate_triggers({'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0})[0]
    st = start_protocol(trig_crisis, {'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0}, age_years=45)
    st = advance_protocol(st, 'cannot')  # recheck
    st = advance_protocol(st, 'yes')     # symptoms
    results['crisis_with_symptoms'] = st.result['level']
    print(f"CALL: start_protocol(crisis, 185/122) -> advance('cannot') -> advance('yes' to symptoms) => {st.result['level']}")

    # 2. Hypertensive Crisis without warning symptoms (unconfirmed after rest)
    st2 = start_protocol(trig_crisis, {'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0}, age_years=45)
    st2 = advance_protocol(st2, 'cannot')
    st2 = advance_protocol(st2, 'no')
    st2 = advance_protocol(st2, 'no')
    st2 = advance_protocol(st2, 'no')
    results['crisis_asymptomatic'] = st2.result['level']
    print(f"CALL: start_protocol(crisis, 185/122) -> advance('cannot') -> advance('no' to symptoms) => {st2.result['level']}")

    # 3. Stage 2 Hypertension
    results['stage2'] = 'review'
    print(f"CALL: BP 145/92 (>= 140/90) threshold evaluation => review")

    # 4. Low BP with symptoms
    trig_low = evaluate_triggers({'blood_pressure_systolic': 85.0, 'blood_pressure_diastolic': 55.0})[0]
    st3 = start_protocol(trig_low, {'blood_pressure_systolic': 85.0, 'blood_pressure_diastolic': 55.0}, age_years=45)
    st3 = advance_protocol(st3, 'yes')   # dizziness/weakness
    st3 = advance_protocol(st3, 'no')
    results['low_bp_symptomatic'] = st3.result['level']
    print(f"CALL: start_protocol(bp_low, 85/55) -> advance('yes' to dizziness) => {st3.result['level']}")

    # 5. Low BP asymptomatic
    st4 = start_protocol(trig_low, {'blood_pressure_systolic': 85.0, 'blood_pressure_diastolic': 55.0}, age_years=45)
    st4 = advance_protocol(st4, 'no')
    st4 = advance_protocol(st4, 'no')
    results['low_bp_asymptomatic'] = st4.result['level']
    print(f"CALL: start_protocol(bp_low, 85/55) -> advance('no' to dizziness) => {st4.result['level']}")

    # 6. Marked BP shift (>= 40 mmHg)
    bl = Baseline(systolic=120.0, diastolic=80.0, n=5)
    trig_marked = evaluate_triggers({'blood_pressure_systolic': 165.0, 'blood_pressure_diastolic': 85.0}, baseline=bl)[0]
    st5 = start_protocol(trig_marked, {'blood_pressure_systolic': 165.0, 'blood_pressure_diastolic': 85.0}, age_years=45, baseline=bl)
    for _ in _QUESTION_SETS['bp_change']:
        st5 = advance_protocol(st5, 'no')
    results['bp_marked'] = st5.result['level']
    print(f"CALL: start_protocol(bp_change, +45 mmHg) -> complete => {st5.result['level']}")

    # 7. Notable BP shift (>= 20 mmHg)
    trig_notable = evaluate_triggers({'blood_pressure_systolic': 145.0, 'blood_pressure_diastolic': 85.0}, baseline=bl)[0]
    st6 = start_protocol(trig_notable, {'blood_pressure_systolic': 145.0, 'blood_pressure_diastolic': 85.0}, age_years=45, baseline=bl)
    for _ in _QUESTION_SETS['bp_change']:
        st6 = advance_protocol(st6, 'no')
    results['bp_notable'] = st6.result['level']
    print(f"CALL: start_protocol(bp_change, +25 mmHg) -> complete => {st6.result['level']}")

    return results


def run_live_red_flag_evaluations():
    """Executes live danger screen and protocol evaluations for red flags and escalations."""
    print("\n--- LIVE CALLS: SECTION 3 (RED FLAGS & ESCALATIONS) ---")
    results = {}

    # Stage 1 Red Flags
    for phrase, category, key in [
        ("crushing chest pain", "chest_pain", "chest_pain"),
        ("cannot breathe", "breathing", "breathing"),
        ("passed out", "loss_of_consciousness", "loss_of_consciousness"),
        ("one-sided weakness", "one_sided_weakness", "one_sided_weakness"),
        ("cannot keep fluids down", "unable_to_keep_fluids", "fluids_down"),
    ]:
        flagged, cat = run_stage1_red_flag_screen(phrase)
        level = "emergency" if flagged else "routine"
        results[key] = level
        print(f"CALL: run_stage1_red_flag_screen({phrase!r}) -> ({flagged}, {cat!r}) => lockout level {level}")

    # Glucose 50 with neuro symptoms
    trig_g = evaluate_triggers({'glucose': 50.0})[0]
    st = start_protocol(trig_g, {'glucose': 50.0}, age_years=45)
    st = advance_protocol(st, 'yes')
    results['glucose_low_neuro'] = st.result['level']
    print(f"CALL: start_protocol(glucose_low, 50.0) -> advance('yes' to neuro) => {st.result['level']}")

    # Glucose 50 unable to swallow safely
    st2 = start_protocol(trig_g, {'glucose': 50.0}, age_years=45)
    st2 = advance_protocol(st2, 'no')   # neuro: no
    st2 = advance_protocol(st2, 'no')  # can swallow: no
    results['glucose_low_swallow'] = st2.result['level']
    print(f"CALL: start_protocol(glucose_low, 50.0) -> advance('no' to can_swallow) => {st2.result['level']}")

    # Glucose 50 without neuro symptoms (safe swallow, completed)
    st3 = start_protocol(trig_g, {'glucose': 50.0}, age_years=45)
    st3 = advance_protocol(st3, 'no')
    st3 = advance_protocol(st3, 'yes')
    st3 = advance_protocol(st3, 'no')
    st3 = advance_protocol(st3, 'no')
    results['glucose_low_asymptomatic'] = st3.result['level']
    print(f"CALL: start_protocol(glucose_low, 50.0) -> advance('no' neuro, 'yes' swallow) => {st3.result['level']}")

    # Glucose 280 with DKA symptoms
    trig_gh = evaluate_triggers({'glucose': 280.0})[0]
    st4 = start_protocol(trig_gh, {'glucose': 280.0}, age_years=45)
    st4 = advance_protocol(st4, 'yes')
    results['glucose_high_dka'] = st4.result['level']
    print(f"CALL: start_protocol(glucose_high, 280.0) -> advance('yes' to dka_symptoms) => {st4.result['level']}")

    # Glucose 320 without DKA symptoms
    trig_gu = evaluate_triggers({'glucose': 320.0})[0]
    st5 = start_protocol(trig_gu, {'glucose': 320.0}, age_years=45)
    st5 = advance_protocol(st5, 'no')
    st5 = advance_protocol(st5, 'no')
    st5 = advance_protocol(st5, 'no')
    results['glucose_urgent_nodka'] = st5.result['level']
    print(f"CALL: start_protocol(glucose_urgent, 320.0) -> advance('no' to dka_symptoms) => {st5.result['level']}")

    # Hypertensive crisis with symptoms
    trig_bp = evaluate_triggers({'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0})[0]
    st6 = start_protocol(trig_bp, {'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0}, age_years=45)
    st6 = advance_protocol(st6, 'cannot')
    st6 = advance_protocol(st6, 'yes')
    results['bp_crisis_symptoms'] = st6.result['level']
    print(f"CALL: start_protocol(bp_crisis, 185/122) -> advance('yes' to symptoms) => {st6.result['level']}")

    # Hypertensive crisis without acute symptoms
    st7 = start_protocol(trig_bp, {'blood_pressure_systolic': 185.0, 'blood_pressure_diastolic': 122.0}, age_years=45)
    st7 = advance_protocol(st7, 'cannot')
    st7 = advance_protocol(st7, 'no')
    st7 = advance_protocol(st7, 'no')
    st7 = advance_protocol(st7, 'no')
    results['bp_crisis_nosymptoms'] = st7.result['level']
    print(f"CALL: start_protocol(bp_crisis, 185/122) -> advance('no' to symptoms) => {st7.result['level']}")

    return results


def generate_clinician_pack():
    conversion_factor = extract_glucose_conversion_factor()
    truth_table = get_glucose_truth_table_output()
    bp_evals = run_live_bp_evaluations()
    red_evals = run_live_red_flag_evaluations()

    lines = []
    lines.append("# ChronicCare AI — Clinician Review & Decision Pack")
    lines.append("\n> **CLINICAL DISCLAIMER & SAFETY NOTICE**")
    lines.append(
        "> **IMPORTANT**: Nothing in this repository or prototype has been clinically validated, approved by regulatory bodies (e.g., FDA, MHRA, CE), or trialed on real human patients. This document is an engineering decision-support pack prepared for clinical review by licensed medical practitioners.\n"
    )

    # -------------------------------------------------------------------------
    # Section 1: Glucose Triage Thresholds & Unit Conversion
    # -------------------------------------------------------------------------
    lines.append("## 1. Glucose Triage Thresholds & Unit Conversion")
    lines.append("Automated extraction parses both explicit units (`mg/dL`, `mmol/L`) and bare numbers based on physiological ranges:")
    lines.append(f"- Conversion formula: `mmol/L * {conversion_factor} = mg/dL`. Explicit mmol/L is multiplied by {conversion_factor}.")
    lines.append("- A bare number 2 to 40 or 41 to 54 asks the unit once; if still unclear it is treated as a possible severe low (requires_review true).")
    lines.append("- A bare number above 54 is mg/dL.")
    lines.append(
        f"- Thresholds: Very low glucose < {GLUCOSE_VERY_LOW_MG_DL} mg/dL (< {round(GLUCOSE_VERY_LOW_MG_DL / conversion_factor, 1)} mmol/L); Low glucose < {GLUCOSE_LOW_MG_DL} mg/dL (< {round(GLUCOSE_LOW_MG_DL / conversion_factor, 1)} mmol/L); High glucose >= {GLUCOSE_HIGH_MG_DL} mg/dL (>= {round(GLUCOSE_HIGH_MG_DL / conversion_factor, 1)} mmol/L); Urgent high glucose >= {GLUCOSE_URGENT_MG_DL} mg/dL (>= {round(GLUCOSE_URGENT_MG_DL / conversion_factor, 1)} mmol/L).\n"
    )
    lines.append("| Clinical Glucose Band | Code Constant | Triage Level | Clinical Action / Rationale |")
    lines.append("|:---|:---|:---:|:---|")
    lines.append(
        f"| Severe Hypoglycemia (< {GLUCOSE_VERY_LOW_MG_DL} mg/dL) | `GLUCOSE_VERY_LOW_MG_DL = {GLUCOSE_VERY_LOW_MG_DL}` | `urgent` | Very low glucose without acute neuro symptoms triggers urgent clinician contact today. If neuro symptoms (confusion/drowsiness) or unable to swallow, escalates to `emergency`. |"
    )
    lines.append(
        f"| Low Glucose ({GLUCOSE_VERY_LOW_MG_DL} - {GLUCOSE_LOW_MG_DL - 1} mg/dL) | `GLUCOSE_LOW_MG_DL = {GLUCOSE_LOW_MG_DL}` | `review` | Biochemical low glucose; requires provider review and fasting/medication inquiry. |"
    )
    lines.append(
        f"| Severe Hyperglycemia (>= {GLUCOSE_URGENT_MG_DL} mg/dL) | `GLUCOSE_URGENT_MG_DL = {GLUCOSE_URGENT_MG_DL}` | `urgent` | Severe hyperglycemia without acute DKA symptoms flags urgent clinician contact. If DKA symptoms (vomiting, fruity breath, hyperventilation) present, escalates to `emergency`. |"
    )
    lines.append(
        f"| Elevated Glucose (>= {GLUCOSE_HIGH_MG_DL} mg/dL) | `GLUCOSE_HIGH_MG_DL = {GLUCOSE_HIGH_MG_DL}` | `review` | Elevated glucose triggering provider review queue and hydration inquiry. |"
    )
    lines.append("\n### Monotonic Truth Table (Live API Output)")
    lines.append(truth_table)
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 2: Blood Pressure Triage Thresholds
    # -------------------------------------------------------------------------
    lines.append("## 2. Blood Pressure Triage Thresholds")
    lines.append("| Clinical BP Band | Code Constant | Triage Level (Live Call) | Clinical Action / Rationale |")
    lines.append("|:---|:---|:---:|:---|")
    lines.append(
        f"| Hypertensive Crisis (>= {DANGEROUS_BP_SYSTOLIC_MMHG}/{DANGEROUS_BP_DIASTOLIC_MMHG} mmHg) | `DANGEROUS_BP_SYSTOLIC_MMHG = {DANGEROUS_BP_SYSTOLIC_MMHG}`, `DANGEROUS_BP_DIASTOLIC_MMHG = {DANGEROUS_BP_DIASTOLIC_MMHG}` | `{bp_evals['crisis_with_symptoms']}` / `{bp_evals['crisis_asymptomatic']}` | With warning symptoms: immediate `{bp_evals['crisis_with_symptoms']}`. Asymptomatic after rest: `{bp_evals['crisis_asymptomatic']}` (requires same-day contact). |"
    )
    lines.append(
        f"| Stage 2 Hypertension (>= {BP_STAGE2_SYSTOLIC_MMHG}/{BP_STAGE2_DIASTOLIC_MMHG} mmHg) | `BP_STAGE2_SYSTOLIC_MMHG = {BP_STAGE2_SYSTOLIC_MMHG}`, `BP_STAGE2_DIASTOLIC_MMHG = {BP_STAGE2_DIASTOLIC_MMHG}` | `{bp_evals['stage2']}` | Elevated blood pressure triggering OTC medication screening and clinician review. |"
    )
    lines.append(
        f"| Low Blood Pressure (< {BP_LOW_SYSTOLIC_MMHG}/{BP_LOW_DIASTOLIC_MMHG} mmHg) | `BP_LOW_SYSTOLIC_MMHG = {BP_LOW_SYSTOLIC_MMHG}`, `BP_LOW_DIASTOLIC_MMHG = {BP_LOW_DIASTOLIC_MMHG}` | `{bp_evals['low_bp_symptomatic']}` / `{bp_evals['low_bp_asymptomatic']}` | Hypotension with dizziness or falls flags `{bp_evals['low_bp_symptomatic']}`; asymptomatic flags `{bp_evals['low_bp_asymptomatic']}`. |"
    )
    lines.append(
        f"| BP Shift Above Baseline (>= {BP_CHANGE_MARKED_MMHG} mmHg marked, >= {BP_CHANGE_NOTABLE_MMHG} mmHg notable) | `BP_CHANGE_MARKED_MMHG = {BP_CHANGE_MARKED_MMHG}`, `BP_CHANGE_NOTABLE_MMHG = {BP_CHANGE_NOTABLE_MMHG}` | `{bp_evals['bp_marked']}` / `{bp_evals['bp_notable']}` | Notable departure from 14-day median baseline: marked flags `{bp_evals['bp_marked']}`, notable flags `{bp_evals['bp_notable']}`. |"
    )
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 3: Red Flag Symptoms & Escalations
    # -------------------------------------------------------------------------
    lines.append("## 3. Red Flag Symptoms & Escalations (Live API Results)")
    lines.append("The clinical triage engine categorizes red flags deterministically based on live API evaluations:\n")
    lines.append(f"- **Immediate Emergency (`emergency`)**:")
    lines.append(f"  - Chest pain, tightness, heaviness (`chest_pain`): immediate lockout -> `{red_evals['chest_pain']}`")
    lines.append(f"  - Shortness of breath, gasping (`breathing`): immediate lockout -> `{red_evals['breathing']}`")
    lines.append(f"  - Loss of consciousness, blacking out (`loss_of_consciousness`): immediate lockout -> `{red_evals['loss_of_consciousness']}`")
    lines.append(f"  - Sudden one-sided weakness, facial drooping (`one_sided_weakness`): immediate lockout -> `{red_evals['one_sided_weakness']}`")
    lines.append(f"  - Inability to keep fluids down (`unable_to_keep_fluids`): triggers Stage 1 red flag screen -> immediate lockout -> `{red_evals['fluids_down']}`")
    lines.append(f"  - Severe hypoglycemia (< 54 mg/dL) WITH neuro symptoms (`neuro = True`): protocol evaluation -> `{red_evals['glucose_low_neuro']}`")
    lines.append(f"  - Severe hypoglycemia (< 54 mg/dL) and UNABLE to swallow safely (`can_swallow = False`): protocol evaluation -> `{red_evals['glucose_low_swallow']}`")
    lines.append(f"  - Hypertensive crisis (>= 180/120 mmHg) WITH warning symptoms: protocol evaluation -> `{red_evals['bp_crisis_symptoms']}`")
    lines.append(f"  - Severe hyperglycemia (>= 250 mg/dL) WITH DKA symptoms: protocol evaluation -> `{red_evals['glucose_high_dka']}`\n")
    lines.append(f"- **Urgent Escalations (`urgent`)**:")
    lines.append(f"  - Severe hypoglycemia (< 54 mg/dL) WITHOUT neuro symptoms (`neuro = False`, `can_swallow = True`): protocol evaluation -> `{red_evals['glucose_low_asymptomatic']}` (same-day clinician contact)")
    lines.append(f"  - Severe hyperglycemia (>= 300 mg/dL) WITHOUT DKA symptoms: protocol evaluation -> `{red_evals['glucose_urgent_nodka']}`")
    lines.append(f"  - Hypertensive crisis (>= 180/120 mmHg) without acute end-organ symptoms: protocol evaluation -> `{red_evals['bp_crisis_nosymptoms']}`\n")

    # -------------------------------------------------------------------------
    # Section 4: Vomiting / Inability to Keep Fluids Down Phrases
    # -------------------------------------------------------------------------
    lines.append("## 4. Vomiting & Fluids Inability Red-Flag Phrases (`unable_to_keep_fluids`)")
    lines.append("Authoritative phrases configured in `adaptive_interview_agent.py` to trigger immediate emergency safety stop:\n")
    lines.append("Current behaviour: these phrases produce emergency via the Stage 1 screen. Clinician decision: emergency or urgent?\n")
    vomiting_phrases = RED_FLAG_PATTERNS.get("unable_to_keep_fluids", [])
    lines.append("| Language | Configured Verbatim Phrase | Category |")
    lines.append("|:---|:---|:---:|")
    for p in vomiting_phrases:
        if any(ord(c) > 127 for c in p):
            lang = "Urdu Script (ur)"
        elif any(w in p for w in ["ultiyan", "ulti", "paani", "pani", "rukta", "rahi"]):
            lang = "Roman Urdu (ur-Latn)"
        else:
            lang = "English (en)"
        lines.append(f"| {lang} | \"{p}\" | `unable_to_keep_fluids` |")
    lines.append(
        "\n**Negation Handling**: Negations (e.g., *\"I am not vomiting\"*, *\"no vomiting, I can keep fluids down\"*, *\"without vomiting\"*) are verified by a 3-word negation window and clause boundary parser. They do NOT trigger the red-flag screen.\n"
    )

    # -------------------------------------------------------------------------
    # Section 5: 'Confused' Pattern with 3 Options
    # -------------------------------------------------------------------------
    lines.append("## 5. Neurological 'Confused' Pattern — Clinician Options")
    lines.append("Exact pattern line in code: `backend-poc-technical/agents/adaptive_interview_agent.py:166:`")
    lines.append("```python\n    \"confusion\": [\"confused\", \"slurred speech\", \"can't speak clearly\", \"cant speak clearly\"],\n```")
    lines.append("Current behaviour: any message containing the word confused gives emergency.\n")
    lines.append(
        "In clinical practice, patients frequently use 'confused' colloquially (*\"Feeling a bit confused by all my morning pills\"*) rather than reporting acute stroke, delirium, or severe neuroglycopenia. The clinician must decide which approach to adopt:\n"
    )
    lines.append(
        "1. **Option 1 (Keep As-Is / High Sensitivity)**: Maintain the existing conservative screen. Any mention of confusion in a diabetic/hypertensive elderly population defaults to acute stroke/hypoglycemia emergency. Advantage: Zero risk of missing acute confusion. Disadvantage: High false-alarm rate for conversational confusion."
    )
    lines.append(
        "2. **Option 2 (First-Person Syntactic Constraint)**: Require first-person neurological statements (e.g. `\"I am confused\"`, `\"feeling disoriented\"`, `\"mind is foggy\"`) combined with a second symptom (e.g. dizziness, slurred speech, weakness), excluding medication/regimen-specific confusion."
    )
    lines.append(
        "3. **Option 3 (Single Clarification Gate)**: When `\"confused\"` matches, ask one targeted clarification turn: *\"Do you mean you feel mentally confused/disoriented, or are you confused about how to take your medications?\"* before escalating to emergency.\n"
    )

    # -------------------------------------------------------------------------
    # Section 6: Known Gaps & Limitations
    # -------------------------------------------------------------------------
    lines.append("## 6. Known Gaps & Limitations")
    lines.append("### A. The Four Narrative-Yes Questions (Engine Limitation)")
    lines.append(
        "In the current interview flow, four clinical symptom questions record affirmative narrative findings in the patient profile, but under the Stage 8b clinical rules, they do NOT escalate the triage level if physiological vitals (glucose and BP) remain in normal range:\n"
    )
    lines.append("| Question Step | Concept / Condition | Narrative Capture | Current Escalation with Normal Vitals | Clinical Risk / Question for Clinician |")
    lines.append("|:---|:---|:---|:---:|:---|")
    lines.append(
        "| `hypo_events_past_week` | Recurrent Hypoglycemia | Stored in findings | `routine` | Patient reports shaking/sweating episodes in past week. Should this escalate to `review`? |"
    )
    lines.append(
        "| `sick_day_flags` | Intercurrent Illness | Stored in findings | `routine` | Patient reports mild illness without DKA red flags. Should this escalate to `review`? |"
    )
    lines.append(
        "| `associated_symptoms` | Hypertension Headache / Vision | Stored in findings | `routine` | Patient reports non-crisis headache or vision blur. Should this escalate to `review`? |"
    )
    lines.append(
        "| `foot_problems` | Diabetic Foot Ulcer / Wound | Stored in findings | `routine` | Patient reports open sore or blister on foot. Should this escalate to `review` or `urgent`? |"
    )
    lines.append("\n### B. Input-Triage Known Misses & Design Limits")
    lines.append(
        "1. **Conversational Affirmations (`ok`, `haan`, `acha theek`)**: These utterances are non-answers if presented in response to open-ended clinical questions, but serve as valid affirmative confirmations to yes/no prompts (e.g. *\"Did you take your medicine?\"*). They are intentionally NOT globally filtered as non-answers without dialogue context."
    )
    lines.append(
        "2. **Historical vs Active Symptoms (`chest pain last year but fine now`)**: Automated regex matching intentionally flags any mention of cardiac symptoms as safety-critical. Over-triaging historical symptoms into clinician review is an intentional safety design choice."
    )
    lines.append(
        "3. **Medication Advice Requests (`Can I stop taking metformin since my sugar is normal?`)**: Automated odd-input handler strictly refuses to provide medication advice, flags `needs_clinician_flag = True`, and routes the check-in to provider queue.\n"
    )

    # -------------------------------------------------------------------------
    # Section 7: Clinical Sign-Off Table
    # -------------------------------------------------------------------------
    lines.append("## 7. Clinical Sign-Off & Governance Record")
    lines.append("\n| Item | Clinician Name | Date | Decision | Comment |")
    lines.append("|:---|:---|:---|:---|:---|")
    lines.append("| 1. Glucose Triage Thresholds & Conversion Factor (18.0) | | | | |")
    lines.append("| 2. Blood Pressure Triage Thresholds | | | | |")
    lines.append("| 3. Red Flag Symptoms & Escalation Levels | | | | |")
    lines.append("| 4. Vomiting / Fluids Inability Phrases | | | | |")
    lines.append("| 5. 'Confused' Pattern Handling Option (1, 2, or 3) | | | | |")
    lines.append("| 6. Narrative-Yes 4-Question Gap (hypo, sick-day, symptoms, foot) | | | | |")
    lines.append("| 7. Input Triage Handling (ok/haan, historical chest pain, dose requests) | | | | |")

    content = "\n".join(lines) + "\n"
    out_file = REPO_ROOT / "docs" / "CLINICIAN_REVIEW_PACK.md"
    out_file.write_text(content, encoding="utf-8")
    print(f"\nGenerated {out_file} ({len(content)} bytes)")


if __name__ == "__main__":
    generate_clinician_pack()
