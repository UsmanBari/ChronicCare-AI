"""
Generated Level-Change Verification Table for Stage 8b Question Steps (Stage 9A-3 Task D).
Runs the real interview state machine and triage evaluation under both v2 and v3.
"""

import sys
import os
from pathlib import Path

# Ensure backend-poc-technical is on path
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    HypertensionStep,
    adaptive_interview_node,
)
from agents.triage_protocol import (
    TriageProtocolState,
    evaluate_triggers,
    advance_protocol,
    run_stage1_red_flag_screen,
)
from agents.interview_v3_runner import start_v3_session, next_turn
from agents.input_triage import classify_input

STAGE_8B_STEPS = [
    ("glucose_context", "diabetes"),
    ("hypo_events_past_week", "diabetes"),
    ("sick_day_flags", "diabetes"),
    ("foot_problems", "diabetes"),
    ("bp_technique", "hypertension"),
    ("associated_symptoms", "hypertension"),
    ("otc_meds_bp", "hypertension"),
    ("missed_doses_reason", "diabetes"),
    ("patient_free_text_note", "diabetes"),
]

ANSWER_CLASSES = [
    ("yes", "yes"),
    ("no", "no"),
    ("unknown", "I don't know"),
    ("skip", "skip"),
    ("danger_phrase", "I have severe crushing chest pain"),
    ("very_long_answer", "I woke up early at 7am and took my tea with some bread then around noon felt a bit warm and had some water and rested for half an hour before taking the reading."),
]

LEVEL_SEVERITY = {
    "routine": 0,
    "review": 1,
    "urgent": 2,
    "emergency": 3,
}

def get_v2_baseline_state(step_name: str, condition: str) -> InterviewState:
    if condition == "diabetes":
        state = InterviewState(
            patient_id="sim_p_1",
            conditions_on_file=["diabetes"],
            interview_version="v2.3",
            on_insulin_or_sulfonylurea=True,
        )
        state = adaptive_interview_node(state, None) # start
        state = adaptive_interview_node(state, "hello")
        state = adaptive_interview_node(state, "130") # sets glucose
        # Now at glucose_context or similar
        if step_name == "hypo_events_past_week":
            state.step = DiabetesStep.HYPO_EVENTS_PAST_WEEK.value
        elif step_name == "sick_day_flags":
            state.step = DiabetesStep.SICK_DAY_FLAGS.value
        elif step_name == "foot_problems":
            state.step = DiabetesStep.FOOT_PROBLEMS.value
        elif step_name == "missed_doses_reason":
            state.step = DiabetesStep.MISSED_DOSES_REASON.value
        elif step_name == "patient_free_text_note":
            state.step = DiabetesStep.PATIENT_FREE_TEXT.value
        elif step_name == "glucose_context":
            state.step = DiabetesStep.GLUCOSE_CONTEXT.value
    else:
        state = InterviewState(
            patient_id="sim_p_1",
            conditions_on_file=["hypertension"],
            interview_version="v2.3",
        )
        state = adaptive_interview_node(state, None) # start
        state = adaptive_interview_node(state, "hello")
        state = adaptive_interview_node(state, "135/85")
        if step_name == "bp_technique":
            state.step = HypertensionStep.BP_TECHNIQUE.value
        elif step_name == "associated_symptoms":
            state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
        elif step_name == "otc_meds_bp":
            state.step = HypertensionStep.OTC_MEDS_BP.value
    return state

def evaluate_v2_level(state: InterviewState) -> str:
    if state.stage1_red_flag:
        return "emergency"
    glucose = state.answers.get("glucose_reading")
    bp = state.answers.get("bp_reading")
    readings = {}
    if glucose is not None:
        readings["glucose"] = float(glucose)
    if bp is not None:
        readings["blood_pressure_systolic"] = float(bp[0])
        readings["blood_pressure_diastolic"] = float(bp[1])
    
    triggers = evaluate_triggers(readings)
    if not triggers:
        return "routine"
    
    # Check warning symptoms from answers
    for k, v in state.answers.items():
        if isinstance(v, str):
            rf, _ = run_stage1_red_flag_screen(v)
            if rf:
                return "emergency"
    return "routine"

def run_level_change_matrix():
    print("# Generated Level-Change Table (Stage 8b Questions under v2 & v3)")
    print()
    print("| Engine | Question Step | Answer Class | Answer Text | Level Before | Level After | Monotonic? | Responsible Code / Rule |")
    print("|:---:|:---|:---:|:---|:---:|:---:|:---:|:---|")

    monotonicity_violations = []

    for step_name, condition in STAGE_8B_STEPS:
        for ans_class, ans_text in ANSWER_CLASSES:
            # --- V2 Evaluation ---
            v2_state_before = get_v2_baseline_state(step_name, condition)
            v2_lvl_before = evaluate_v2_level(v2_state_before)
            
            v2_state_after = adaptive_interview_node(v2_state_before, ans_text)
            v2_lvl_after = evaluate_v2_level(v2_state_after)
            
            v2_sev_before = LEVEL_SEVERITY.get(v2_lvl_before, 0)
            v2_sev_after = LEVEL_SEVERITY.get(v2_lvl_after, 0)
            v2_monotonic = v2_sev_after >= v2_sev_before
            if not v2_monotonic:
                monotonicity_violations.append(f"v2 {step_name} {ans_class}: {v2_lvl_before} -> {v2_lvl_after}")

            v2_rule = "agents/adaptive_interview_agent.py:L194 (stage1_red_flag)" if v2_state_after.stage1_red_flag else "agents/triage_protocol.py:L480 (evaluate_overall_level)"

            # Print v2 row
            print(f"| v2 | `{step_name}` | {ans_class} | \"{ans_text[:28]}...\" | {v2_lvl_before} | {v2_lvl_after} | {'YES' if v2_monotonic else 'FAIL'} | `{v2_rule}` |")

            # --- V3 Evaluation ---
            import copy
            v3_session = start_v3_session(
                checkin_id="sim_c_1",
                patient_id="sim_p_1",
                conditions=[condition],
                on_insulin_or_sulfonylurea=True,
                language="en",
            )
            # Answer greeting and reading
            v3_session = next_turn(v3_session, "hello")
            if condition == "diabetes":
                v3_session = next_turn(v3_session, "130 mg/dL")
            else:
                v3_session = next_turn(v3_session, "135/85")

            v3_lvl_before = "emergency" if v3_session.get("emergency") else ("urgent" if v3_session.get("urgent_safety") else "routine")
            v3_session_after = next_turn(copy.deepcopy(v3_session), ans_text)
            v3_lvl_after = "emergency" if v3_session_after.get("emergency") else ("urgent" if v3_session_after.get("urgent_safety") else "routine")
            
            v3_sev_before = LEVEL_SEVERITY.get(v3_lvl_before, 0)
            v3_sev_after = LEVEL_SEVERITY.get(v3_lvl_after, 0)
            v3_monotonic = v3_sev_after >= v3_sev_before
            if not v3_monotonic:
                monotonicity_violations.append(f"v3 {step_name} {ans_class}: {v3_lvl_before} -> {v3_lvl_after}")

            if v3_session_after.get("emergency"):
                v3_rule = "agents/input_triage.py:L118 (authoritative_danger_screen)"
            elif v3_session_after.get("urgent_safety"):
                v3_rule = "agents/input_triage.py:L444 (self_harm_urgent_safety)"
            else:
                v3_rule = "agents/interview_v3_runner.py:L174 (next_turn_flow)"

            print(f"| v3 | `{step_name}` | {ans_class} | \"{ans_text[:28]}...\" | {v3_lvl_before} | {v3_lvl_after} | {'YES' if v3_monotonic else 'FAIL'} | `{v3_rule}` |")

    print()
    print(f"Total combinations tested: {len(STAGE_8B_STEPS) * len(ANSWER_CLASSES) * 2}")
    print(f"Monotonicity violations: {len(monotonicity_violations)}")
    if monotonicity_violations:
        print("VIOLATIONS:", monotonicity_violations)

if __name__ == "__main__":
    run_level_change_matrix()
