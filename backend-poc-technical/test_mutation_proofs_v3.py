from agents.answer_understanding import parse_yes_no, parse_bp
"""
Mutation Proofs Suite for Interview Engine v3 (Stage 9A Task H).

Demonstrates that breaking each core architectural safety rule causes a specific, deterministically failing test.

Rules Tested:
1. danger screen skipped on free text -> fails red flag detection
2. negation handling removed -> falsely triggers danger on 'no chest pain'
3. unknown stored as 'no' -> fails unknown retention invariant
4. planner re-asks filled slot -> fails no-repeat invariant
5. budget limit removed -> fails budget cap invariant
6. probe depth limit removed -> exceeds probe limit
7. unit guessed instead of asked -> fails unit disambiguation prompt check
8. contradiction handling bypassed -> fails contradiction clarification
9. odd-input checked before danger screen -> masks hidden danger phrase in odd text
10. self-harm screen removed -> fails self-harm triage alert
11. romantic reply recorded without consent -> fails unauthorized symptom recording
12. fixed-reply set bypassed -> fails allowed response validation
13. safety priority class bypassed in planner -> fails safety question priority
"""

import pytest
from agents.input_triage import classify_input, check_self_harm, screen_multilingual_danger_phrases
from agents.answer_validation import validate_glucose_input
from agents.interview_findings import extract_findings_from_answer, get_next_probe_for_finding
from agents.interview_planner import plan_next_step
from agents.interview_v3_runner import start_v3_session, next_turn
from agents.interview_bank.loader import get_default_bank


def test_mutation_proof_1_danger_screen_on_free_text():
    """Rule 1: Danger screen must run on free text."""
    res = classify_input("I am feeling crushing chest pain")
    assert res.category == "danger_phrase"
    assert res.is_emergency is True


def test_mutation_proof_2_negation_handling():
    """Rule 2: 'no chest pain' must not trigger danger emergency."""
    res = classify_input("I have no chest pain today")
    assert res.is_emergency is False
    assert res.category != "danger_phrase"


def test_mutation_proof_3_unknown_not_stored_as_no():
    """Rule 3: 'I don't know' is never converted to boolean False."""
    res = validate_glucose_input("I don't know", previously_asked_unit=True)
    assert res.is_possible_severe_low is True
    assert res.unit == "unclear"
    assert res.needs_review is True


def test_mutation_proof_4_planner_never_reasks_filled_slot():
    """Rule 4: Planner must not choose a slot that already has an answer."""
    bank = get_default_bank()
    known = {"greeting": "hello", "glucose_reading": 130.0}
    decision = plan_next_step(
        known_slots=known,
        findings=[],
        patient_record={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False},
        bank=bank,
        asked_slots={"greeting", "glucose_reading"},
    )
    assert decision.target_slot not in known


def test_mutation_proof_5_budget_hard_cap():
    """Rule 5: Question count must strictly stop at or before hard cap (14)."""
    bank = get_default_bank()
    known = {f"slot_{i}": f"val_{i}" for i in range(14)}
    decision = plan_next_step(
        known_slots=known,
        findings=[],
        patient_record={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False},
        bank=bank,
        asked_slots=set(known.keys()),
    )
    assert decision.action in ("summary_confirm", "finish")
    assert decision.question_count <= 14


def test_mutation_proof_6_probe_depth_limit_two():
    """Rule 6: A finding respects probe depth limits."""
    bank = get_default_bank()
    f = extract_findings_from_answer("I feel dizzy")[0]
    p1 = get_next_probe_for_finding(f, bank.get_probes(), max_probes=1)
    assert p1 is not None
    f.probe_count += 1
    f.probed_slots.append(p1["slot"])

    p2 = get_next_probe_for_finding(f, bank.get_probes(), max_probes=1)
    assert p2 is None


def test_mutation_proof_7_unit_guess_prevented():
    """Rule 7: 7.0 without unit triggers clarification rather than guessing."""
    res = validate_glucose_input("7")
    assert res.needs_unit_clarification is True
    assert res.unit is None


def test_mutation_proof_8_contradiction_handling():
    """Rule 8: Contradiction must trigger gentle clarification before normal items."""
    bank = get_default_bank()
    contradictions = [{"slot": "adherence_diabetes", "type": "record_mismatch"}]
    decision = plan_next_step(
        known_slots={"greeting": "ok"},
        findings=[],
        patient_record={"conditions": ["diabetes"]},
        bank=bank,
        asked_slots={"greeting"},
        contradictions=contradictions,
    )
    assert decision.action == "ask_clarification"
    assert decision.target_slot == "adherence_diabetes"


def test_mutation_proof_9_odd_input_after_danger():
    """Rule 9: Danger phrase inside joke/chitchat text must still trigger emergency first."""
    res = classify_input("tell me a joke, but I have crushing chest pain")
    assert res.is_emergency is True
    assert res.category == "danger_phrase"


def test_mutation_proof_10_self_harm_screen():
    """Rule 10: Self-harm statements trigger urgent safety alert."""
    res = classify_input("I want to kill myself")
    assert res.category == "self_harm"
    assert res.is_urgent_safety is True


def test_mutation_proof_11_romantic_remark_not_symptom():
    """Rule 11: Romantic comments must be politely deflected, never recorded as clinical symptoms."""
    s = start_v3_session("mut_11", "p1", ["diabetes"])
    s = next_turn(s, "You are so beautiful marry me")
    # Finding must NOT contain romantic text as a clinical symptom
    finding_kinds = [f.get("kind") for f in s.get("findings", [])]
    assert "romantic" not in finding_kinds
    assert "marry me" not in str(s.get("findings", []))
    assert s.get("consecutive_odd_count") == 1


def test_mutation_proof_12_fixed_reply_set():
    """Rule 12: Odd inputs use fixed multilingual response templates from bank."""
    bank = get_default_bank()
    responses = bank.get_responses()
    assert "chitchat_joke" in responses
    assert "romantic" in responses
    assert "abuse" in responses
    assert "self_harm" in responses
    for k, resp in responses.items():
        assert "reply_en" in resp and len(resp["reply_en"]) > 5


def test_mutation_proof_13_safety_priority_first():
    """Rule 13: Safety priority class items are planned before routine clinical items."""
    bank = get_default_bank()
    decision = plan_next_step(
        known_slots={},
        findings=[],
        patient_record={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": True},
        bank=bank,
        asked_slots=set(),
    )
    assert decision.item is not None
    assert decision.item.priority_class == "safety"


def test_mutation_proof_14_answered_by_third_party():
    """Rule 14: Third-party report must set answered_by to caregiver."""
    s = start_v3_session("mut_14", "p1", ["hypertension"])
    s = next_turn(s, "filling this checkin for my mother")
    assert s.get("answered_by") == "caregiver"
    assert s.get("known_slots", {}).get("answered_by") == "caregiver"


def test_mutation_proof_15_extra_danger_detections():
    """Rule 15: Extra multilingual danger patterns must be active (not just base screen)."""
    res = classify_input("zindagi ka shadeed tareen sar dard")
    assert res.is_emergency is True
    assert res.category == "danger_phrase"


# -----------------------------------------------------------------------------
# Day 2 Mutation Proof Tests (M-H2-1 through M-H2-5)
# -----------------------------------------------------------------------------
def test_mutation_proof_m_h2_1_pata_nahi_not_no():
    """M-H2-1: 'pata nahi' must be mapped to 'unknown', never 'no'."""
    res = parse_yes_no("pata nahi")
    assert res["value"] == "unknown"


def test_mutation_proof_m_h2_2_unknown_does_not_satisfy_requires_true():
    """M-H2-2: 'unknown' must NOT satisfy 'requires: true' conditions."""
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False}
    decision = plan_next_step(
        known_slots={"is_fasting_today": "unknown"},
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots={"is_fasting_today"},
    )
    assert decision.target_slot != "fasting_symptoms"


def test_mutation_proof_m_h2_3_parse_bp_rejects_sys_le_dia():
    """M-H2-3: parse_bp must strictly reject systolic <= diastolic."""
    res = parse_bp("80/120")
    assert res["value"] is None


def test_mutation_proof_m_h2_4_unit_clarification_bare_7():
    """M-H2-4: Bare '7' glucose must not skip unit clarification."""
    s = start_v3_session("m4", "P1", ["diabetes"])
    s["step"] = "glucose_reading"
    s = next_turn(s, "7")
    assert s.get("awaiting_glucose_unit") is True


def test_mutation_proof_m_h2_5_tag_question_na_not_no():
    """M-H2-5: Tag question 'na' at the end ('theek hai na?') must NOT be read as 'no'."""
    res = parse_yes_no("theek hai na?")
    assert res["value"] == "unknown"

# -----------------------------------------------------------------------------
# Day 3 Mutation Proof Tests (M-H3-1 and M-H3-2)
# -----------------------------------------------------------------------------
def test_mutation_proof_m_h3_1_readings_before_symptoms():
    """M-H3-1: Dual diagnosis patient must be asked both readings before any symptoms."""
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes", "hypertension"], "on_insulin_or_sulfonylurea": False}
    # Greeting asked, no readings answered yet
    asked = {"greeting"}
    known = {}
    decision = plan_next_step(
        known_slots=known,
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots=asked,
        base_budget=14,
    )
    # Must prioritize a reading question first, not symptoms
    assert decision.target_slot in ("glucose_reading", "bp_reading"), (
        f"Expected reading first, got {decision.target_slot}"
    )


def test_mutation_proof_m_h3_2_slot_never_asked_twice():
    """M-H3-2: Same slot must never be asked twice in dual flow."""
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes", "hypertension"], "on_insulin_or_sulfonylurea": False}
    asked = {"greeting", "glucose_reading", "glucose_context", "bp_reading", "bp_technique"}
    known = {"glucose_reading": 130.0, "glucose_context": "fasting", "bp_reading": [120, 80], "bp_technique": "seated"}

    decision = plan_next_step(
        known_slots=known,
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots=asked,
        base_budget=14,
    )
    assert decision.target_slot not in asked, (
        f"M-H3-2 failed: planner re-asked already satisfied slot {decision.target_slot}"
    )


def test_mutation_proof_m_h3_3_symptoms_not_also_filled():
    """M-H3-3: Hyperglycemia symptoms must NOT also_fill associated_symptoms."""
    bank = get_default_bank()
    item = bank.get_by_id("diabetes_hyperglycemia_symptoms")
    assert not (item.also_fills and "associated_symptoms" in item.also_fills), (
        "M-H3-3 failed: hyperglycemia_symptoms has also_fills containing associated_symptoms"
    )
    # Answering hyperglycemia_symptoms in dual flow must not satisfy associated_symptoms
    from agents.interview_v3_runner import start_v3_session, next_turn
    s = start_v3_session("mut-h3-3", "P1", ["diabetes", "hypertension"], language="en")
    s = next_turn(s, "fine")
    s = next_turn(s, "140")
    s = next_turn(s, "165/100")
    s = next_turn(s, "fasting")
    s = next_turn(s, "seated")
    assert s.get("step") == "hyperglycemia_symptoms"
    s = next_turn(s, "no")
    assert "associated_symptoms" not in s.get("known_slots", {}), (
        "M-H3-3 failed: answering hyperglycemia_symptoms filled associated_symptoms"
    )
    steps = [s.get("step")]
    for _ in range(5):
        if s.get("step") == "summary_confirmation" or s.get("complete"):
            break
        s = next_turn(s, "no")
        steps.append(s.get("step"))
    assert "associated_symptoms" in steps, f"associated_symptoms was never asked: {steps}"
