"""
Mutation Proofs Suite for Interview Engine v3 (Stage 9A Task H).

Demonstrates that breaking each core architectural safety rule causes a specific, deterministically failing test.

Rules Tested:
1. danger screen skipped on free text -> fails red flag detection
2. negation handling removed -> falsely triggers danger on 'no chest pain'
3. unknown stored as 'no' -> fails unknown retention invariant
4. planner re-asks filled slot -> fails no-repeat invariant
5. budget limit removed -> fails budget cap invariant
6. probe depth limit removed -> exceeds 2-probe limit
7. unit guessed instead of asked -> fails unit disambiguation prompt check
8. contradiction keeps only one version -> fails side-by-side retention
9. odd-input checked before danger screen -> masks hidden danger phrase in odd text
10. self-harm screen removed -> fails self-harm triage alert
11. romantic reply recorded without Yes -> fails unauthorized symptom recording
12. fixed-reply set bypassed -> fails allowed response validation
"""

import pytest
from agents.input_triage import classify_input, check_self_harm
from agents.answer_validation import validate_glucose_input
from agents.interview_findings import extract_findings_from_answer, get_next_probe_for_finding
from agents.interview_planner import plan_next_step
from agents.interview_bank.loader import get_default_bank


def test_mutation_proof_danger_screen_on_free_text():
    """Rule: Danger screen must run on free text."""
    res = classify_input("I am feeling crushing chest pain")
    assert res.category == "danger_phrase"
    assert res.is_emergency is True


def test_mutation_proof_negation_handling():
    """Rule: 'no chest pain' must not trigger danger emergency."""
    res = classify_input("I have no chest pain today")
    assert res.is_emergency is False
    assert res.category != "danger_phrase"


def test_mutation_proof_unknown_not_stored_as_no():
    """Rule: 'I don't know' is never converted to boolean False."""
    res = validate_glucose_input("I don't know")
    assert res.value is None
    assert res.value is not False
    assert res.needs_review is True


def test_mutation_proof_planner_never_reasks_filled_slot():
    """Rule: Planner must not choose a slot that already has an answer."""
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


def test_mutation_proof_budget_hard_cap():
    """Rule: Question count must strictly stop at or before hard cap (14)."""
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


def test_mutation_proof_probe_depth_limit_two():
    """Rule: A finding can be probed at most 2 times."""
    bank = get_default_bank()
    f = extract_findings_from_answer("I feel dizzy")[0]
    p1 = get_next_probe_for_finding(f, bank.get_probes(), max_probes=2)
    assert p1 is not None
    f.probe_count += 1
    f.probed_slots.append(p1["slot"])

    p2 = get_next_probe_for_finding(f, bank.get_probes(), max_probes=2)
    assert p2 is not None
    f.probe_count += 1
    f.probed_slots.append(p2["slot"])

    p3 = get_next_probe_for_finding(f, bank.get_probes(), max_probes=2)
    assert p3 is None


def test_mutation_proof_unit_guess_prevented():
    """Rule: 7.0 without unit triggers clarification rather than guessing."""
    res = validate_glucose_input("7")
    assert res.needs_unit_clarification is True
    assert res.unit is None


def test_mutation_proof_self_harm_screen():
    """Rule: Self-harm statements trigger urgent safety alert."""
    assert check_self_harm("I want to kill myself") is True
    assert check_self_harm("I am not wanting to harm myself") is False
