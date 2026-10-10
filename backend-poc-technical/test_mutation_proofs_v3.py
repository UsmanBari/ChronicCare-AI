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
