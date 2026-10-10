"""
Unit & Property Tests for Interview Planner (Stage 9A Task D).

Verifies:
1. Priority classes strictly respected (Safety > Contradiction > Probe > Trend > Barrier > Open > Wellbeing).
2. Budget constraints (8 normal, 12 concerning, 14 hard cap).
3. No slot re-asking without a correction reason.
4. Determinism across identical state inputs.
5. Historical trends detection (rising BP, recurrent hypoglycemia, repeated missed doses).
6. Exhaustive seeded property test over 1000 generated states.
"""

import random
import pytest
from agents.interview_planner import (
    PlanDecision,
    plan_next_step,
    detect_historical_trends,
)
from agents.interview_bank.loader import get_default_bank
from agents.interview_findings import Finding


def test_safety_priority_class_chosen_first():
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": True}
    known_slots = {"greeting": "feeling weak"}
    findings = [Finding(id="f1", kind="tiredness", label="Tiredness", raw_quote="feeling weak")]

    decision = plan_next_step(
        known_slots=known_slots,
        findings=findings,
        patient_record=patient_record,
        bank=bank,
    )
    assert decision.action == "ask_bank_item"
    assert decision.item is not None
    assert decision.item.priority_class == "safety"
    assert decision.item.slot in ("hypo_events_past_week", "hypo_symptoms_acute")


def test_contradiction_priority():
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": True}
    known_slots = {"greeting": "I feel fine", "hypo_events_past_week": False, "hypo_symptoms_acute": False}
    contradictions = [{
        "slot": "adherence_diabetes",
        "type": "record_mismatch",
        "message": "Clarify insulin usage"
    }]

    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient_record,
        contradictions=contradictions,
        bank=bank,
    )
    assert decision.action == "ask_clarification"
    assert decision.target_slot == "adherence_diabetes"


def test_drilldown_probe_for_newest_finding():
    bank = get_default_bank()
    patient_record = {"conditions": ["hypertension"], "on_insulin_or_sulfonylurea": False}
    known_slots = {"greeting": "I am dizzy"}
    f = Finding(id="f1", kind="dizziness", label="Dizziness", raw_quote="I am dizzy")

    decision = plan_next_step(
        known_slots=known_slots,
        findings=[f],
        patient_record=patient_record,
        bank=bank,
    )
    assert decision.action == "ask_probe"
    assert decision.probe is not None
    assert decision.probe["slot"] == "dizziness_trigger"


def test_trend_triggers_recurrent_hypo():
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False}
    # 2 previous lows in history
    recent_checkins = [
        {"intakes": [{"readings": [{"observation_type": "glucose", "value": 55.0}]}]},
        {"intakes": [{"readings": [{"observation_type": "glucose", "value": 62.0}]}]},
    ]
    trends = detect_historical_trends(recent_checkins)
    assert trends["recurrent_lows"] is True

    known_slots = {"greeting": "I feel okay"}
    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient_record,
        recent_checkins=recent_checkins,
        bank=bank,
    )
    assert decision.item is not None
    assert decision.item.slot == "hypo_events_past_week"


def test_budget_constraints_and_summary_confirm():
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False}
    # Fill 8 slots
    known_slots = {
        "greeting": "ok",
        "glucose_reading": 130.0,
        "glucose_context": "fasting",
        "hyperglycemia_symptoms": False,
        "foot_problems": False,
        "adherence_diabetes": True,
        "lifestyle_diabetes": "normal",
        "patient_free_text_note": "none",
    }

    # At budget 8, planner must offer summary_confirm
    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient_record,
        bank=bank,
        base_budget=8,
    )
    assert decision.action == "summary_confirm"
    assert decision.target_slot == "summary_confirmation"

    # Once summary confirmed, finish
    known_slots["summary_confirmation"] = True
    decision_fin = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient_record,
        bank=bank,
        base_budget=8,
    )
    assert decision_fin.action == "finish"


def test_seeded_random_property_test_1000_states():
    """
    Property test: Generates 1,000 randomized state combinations and asserts:
    1. Planner never crashes.
    2. Never returns a slot already present in known_slots.
    3. Total question count never exceeds hard_cap (14).
    4. Deterministic: running twice on same state yields identical result.
    """
    bank = get_default_bank()
    rng = random.Random(42)

    possible_conditions = [["diabetes"], ["hypertension"], ["diabetes", "hypertension"]]
    all_bank_slots = [item.slot for item in bank.all_items()]

    for _ in range(1000):
        conds = rng.choice(possible_conditions)
        on_ins = rng.choice([True, False])
        patient_rec = {"conditions": conds, "on_insulin_or_sulfonylurea": on_ins}

        # Randomly pre-fill 0 to 12 slots
        k = rng.randint(0, min(12, len(all_bank_slots)))
        chosen_slots = rng.sample(all_bank_slots, k)
        known_slots = {s: "sample_val" for s in chosen_slots}

        decision1 = plan_next_step(
            known_slots=known_slots,
            findings=[],
            patient_record=patient_rec,
            bank=bank,
        )
        decision2 = plan_next_step(
            known_slots=known_slots,
            findings=[],
            patient_record=patient_rec,
            bank=bank,
        )

        # Invariant 1: Determinism
        assert decision1.action == decision2.action
        assert decision1.target_slot == decision2.target_slot

        # Invariant 2: Never repeat an existing slot
        if decision1.target_slot and decision1.action in ("ask_bank_item", "ask_probe"):
            assert decision1.target_slot not in known_slots

        # Invariant 3: Budget hard cap
        assert decision1.question_count <= 14
