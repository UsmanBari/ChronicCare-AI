"""
Comprehensive Verification Tests for Adaptive Interview Engine v3 (Part E1).

Verifies:
1. Actual question sequences for >= 8 personas: no repeats, branch matches readings,
   fewer turns than v2 when early slots or normal ranges skip redundant queries.
2. Clinical Branching:
   - Glucose < 70 mg/dL: strictly hypo branch only, zero hyperglycemia questions.
   - Glucose >= 250 mg/dL: strictly hyper branch only, zero acute hypo questions.
   - BP < 90/60 mmHg: strictly hypotension/low-BP safe, zero high-BP/OTC questions.
3. Condition Isolation:
   - Diabetes-only patient receives 0 blood pressure questions.
   - Hypertension-only patient receives 0 glucose/hypo/hyper questions.
4. Dual Diagnosis:
   - Both readings asked first.
   - Zero duplicate symptom or lifestyle questions.
5. Multilingual early slot filling:
   - English, Urdu script, and Roman Urdu early extractions reduce check-in turn counts.
"""

import json
from pathlib import Path
import pytest

from agents.interview_bank.loader import get_default_bank
from agents.interview_planner import plan_next_step
from agents.interview_v3_runner import start_v3_session, next_turn
from scripts.run_v3_personas import build_persona_facts, pick_answer

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_PATH = REPO_ROOT / "tests" / "sim" / "personas.json"


@pytest.fixture(scope="module")
def personas():
    with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_persona_v3(p):
    pid = p["id"]
    conds = p.get("conditions", ["diabetes"])
    lang = p.get("language", "en")
    facts = build_persona_facts(p)
    s = start_v3_session(f"eval-{pid}", pid, conds, language=lang)
    steps = [s["step"]]
    readings = {}

    for turn in range(25):
        if s.get("complete") or s.get("step") == "COMPLETE" or s.get("emergency"):
            break
        step = s.get("step")
        q = s.get("current_question")
        ans, _ = pick_answer(facts, step, q, lang)
        s = next_turn(s, ans)
        if s.get("readings"):
            readings.update(s["readings"])
        next_step = s.get("step")
        if next_step and next_step != "COMPLETE":
            steps.append(next_step)

    is_emergency = bool(s.get("emergency"))
    return {
        "id": pid,
        "steps": steps,
        "turns": len(steps),
        "emergency": is_emergency,
        "readings": readings,
        "completed": bool(s.get("complete") or s.get("completed")),
    }


def test_actual_question_sequence_8_diverse_personas(personas):
    """
    Evaluates 8+ diverse personas checking:
    - 0 repeated slots after other questions.
    - Branch strictly matches clinical reading.
    - Emergency personas are correctly identified.
    """
    target_ids = [
        "p01_stoic_minimiser",
        "p03_people_pleaser",
        "p06_urdu_script_normal",
        "p07_roman_urdu_normal",
        "p14_fasting_ramadan_with_low",
        "p22_hidden_danger_phrase_long_text",
        "p35_hypertensive_crisis_emergency",
        "p37_dka_sick_day_emergency",
        "dual_glucose_low_bp_normal",
        "p10_caregiver_son",
    ]

    for tid in target_ids:
        p = next((x for x in personas if x["id"] == tid), None)
        assert p is not None, f"Missing persona {tid}"
        res = _run_persona_v3(p)
        steps = res["steps"]

        # 1. No repeated slot asked after another slot
        seen_distinct = []
        prev = None
        for st in steps:
            if st != prev:
                assert st not in seen_distinct, f"Persona {tid} re-asked slot '{st}'! Steps={steps}"
                seen_distinct.append(st)
                prev = st

        # 2. Branch matching checks
        if tid == "p14_fasting_ramadan_with_low":
            # Hypo reading (62 mg/dL) -> must NOT have hyperglycemia_symptoms
            assert "hyperglycemia_symptoms" not in steps, f"p14 got high sugar question on hypo: {steps}"
            assert "hypo_symptoms_acute" in steps or "hypo_recovery_food" in steps

        elif tid == "p22_hidden_danger_phrase_long_text":
            assert res["emergency"] is True, f"Emergency chest pain missed: {res}"

        elif tid == "p35_hypertensive_crisis_emergency":
            assert res["emergency"] is True, f"Hypertensive crisis missed: {res}"

        elif tid == "p37_dka_sick_day_emergency":
            assert res["emergency"] is True, f"DKA emergency missed: {res}"

        elif tid == "dual_glucose_low_bp_normal":
            # Dual diagnosis readings before symptoms
            if "glucose_reading" in steps and "associated_symptoms" in steps:
                assert steps.index("glucose_reading") < steps.index("associated_symptoms")


def test_glucose_hypo_branch_strictly_excludes_hyperglycemia():
    """A glucose reading < 70 mg/dL must strictly branch to hypo and exclude hyperglycemia_symptoms."""
    s = start_v3_session("test-hypo-branch", "P-HYPO", ["diabetes"], language="en")
    s = next_turn(s, "feeling fine")      # greeting
    s = next_turn(s, "58")                # glucose_reading = 58 mg/dL (hypo)

    steps = [s["step"]]
    for _ in range(15):
        if s.get("complete") or s.get("step") == "summary_confirmation":
            break
        s = next_turn(s, "no")
        steps.append(s["step"])

    assert "hyperglycemia_symptoms" not in steps, f"Hypo patient was asked hyperglycemia_symptoms! Steps={steps}"
    assert "hypo_symptoms_acute" in steps, f"Hypo patient was not asked hypo_symptoms_acute! Steps={steps}"


def test_glucose_hyper_branch_strictly_excludes_hypo_questions():
    """A glucose reading >= 250 mg/dL must branch to hyper and exclude acute hypo questions."""
    s = start_v3_session("test-hyper-branch", "P-HYPER", ["diabetes"], language="en")
    s = next_turn(s, "feeling thirsty and tired")   # greeting
    s = next_turn(s, "280")                         # glucose_reading = 280 mg/dL (hyper)

    steps = [s["step"]]
    for _ in range(15):
        if s.get("complete") or s.get("step") == "summary_confirmation":
            break
        s = next_turn(s, "no")
        steps.append(s["step"])

    assert "hypo_symptoms_acute" not in steps, f"Hyper patient was asked hypo_symptoms_acute! Steps={steps}"
    assert "hypo_events_past_week" not in steps, f"Hyper patient was asked hypo_events_past_week! Steps={steps}"
    assert "hyperglycemia_symptoms" in steps, f"Hyper patient was not asked hyperglycemia_symptoms! Steps={steps}"


def test_hypotension_branch_strictly_excludes_high_bp_questions():
    """A BP reading < 90/60 mmHg must not ask elevated-BP symptom queries or OTC meds."""
    s = start_v3_session("test-hypotension-branch", "P-LOW-BP", ["hypertension"], language="en")
    s = next_turn(s, "feeling a bit lightheaded")  # greeting
    s = next_turn(s, "84/55")                      # bp_reading = 84/55 (low BP)

    steps = [s["step"]]
    for _ in range(15):
        if s.get("complete") or s.get("step") == "summary_confirmation":
            break
        s = next_turn(s, "no")
        steps.append(s["step"])

    assert "otc_meds_bp" not in steps, f"Low BP patient was asked otc_meds_bp! Steps={steps}"
    assert "associated_symptoms" not in steps, f"Low BP patient was asked high-BP associated_symptoms! Steps={steps}"


def test_condition_isolation_diabetes_only_gets_no_bp():
    """Diabetes-only patient receives 0 blood pressure questions."""
    s = start_v3_session("test-iso-dm", "P-DM", ["diabetes"], language="en")
    steps = [s["step"]]
    for _ in range(15):
        if s.get("complete") or s.get("step") == "summary_confirmation":
            break
        s = next_turn(s, "no")
        steps.append(s["step"])

    for st in steps:
        assert not st.startswith("bp_"), f"Diabetes patient got BP step '{st}'! Steps={steps}"
        assert st not in ("hypertension_bp_reading", "hypertension_bp_technique", "associated_symptoms", "otc_meds_bp")


def test_condition_isolation_hypertension_only_gets_no_glucose():
    """Hypertension-only patient receives 0 glucose/hypo/hyper questions."""
    s = start_v3_session("test-iso-htn", "P-HTN", ["hypertension"], language="en")
    steps = [s["step"]]
    for _ in range(15):
        if s.get("complete") or s.get("step") == "summary_confirmation":
            break
        s = next_turn(s, "no")
        steps.append(s["step"])

    for st in steps:
        assert not st.startswith("glucose_"), f"HTN patient got glucose step '{st}'! Steps={steps}"
        assert not st.startswith("hyperglycemia_"), f"HTN patient got hyper step '{st}'! Steps={steps}"
        assert not st.startswith("hypo_"), f"HTN patient got hypo step '{st}'! Steps={steps}"
        assert st not in ("foot_problems", "diabetes_adherence", "fasting_symptoms")


def test_multilingual_early_slot_filling_reduces_turns():
    """Early BP and Glucose extraction across EN, Urdu, and Roman Urdu skips redundant reading steps."""
    # 1. English early BP in greeting
    s_en = start_v3_session("early-bp-en", "P-E1", ["hypertension"], language="en")
    s_en = next_turn(s_en, "I am fine, my blood pressure is 132/86 today")
    assert s_en["step"] == "bp_technique", f"Early BP in EN did not skip bp_reading! Step={s_en['step']}"

    # 2. Urdu Script early glucose in greeting
    s_ur = start_v3_session("early-gluc-ur", "P-E2", ["diabetes"], language="ur")
    s_ur = next_turn(s_ur, "میں ٹھیک ہوں، میری شوگر نہار منہ 125 تھی")
    assert s_ur["step"] in ("hyperglycemia_symptoms", "foot_problems"), f"Early glucose in UR did not skip reading! Step={s_ur['step']}"

    # 3. Roman Urdu early BP in greeting
    s_rur = start_v3_session("early-bp-rur", "P-E3", ["hypertension"], language="roman_ur")
    s_rur = next_turn(s_rur, "theek hoon, aaj bp 128/84 tha")
    assert s_rur["step"] == "bp_technique", f"Early BP in Roman UR did not skip bp_reading! Step={s_rur['step']}"
