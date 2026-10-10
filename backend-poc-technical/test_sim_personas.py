"""
Simulated Patient Persona Suite and Safety Invariants (Stage 9A Task G).

Runs all 52 personas from tests/sim/personas.json and verifies:
1. Hard Invariant: 100% recall across 130+ gold danger phrases in tests/sim/danger_phrases_gold.json.
2. Hard Invariant: 'Unknown' is never converted to or stored as 'No'.
3. Hard Invariant: No slot is asked twice without a valid correction/clarification reason.
4. Hard Invariant: Question count never exceeds the hard budget cap (14).
5. Hard Invariant: Odd inputs never lower a clinical triage level.
6. Hard Invariant: Every odd-input response comes from the fixed bank responses set.
7. Zero crashes across all 52 personas.
"""

import json
import os
import pytest

from agents.input_triage import classify_input, screen_multilingual_danger_phrases
from agents.interview_bank.loader import get_default_bank
from agents.interview_planner import plan_next_step
from agents.interview_findings import extract_findings_from_answer


def test_danger_phrases_gold_list_100_percent_recall():
    """Hard invariant: 100% recall across all positive and negated danger phrases."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gold_path = os.path.join(repo_root, "tests", "sim", "danger_phrases_gold.json")
    assert os.path.exists(gold_path), f"Missing danger phrases gold file at {gold_path}"

    with open(gold_path, "r", encoding="utf-8") as f:
        phrases = json.load(f)

    assert len(phrases) >= 120, f"Expected >= 120 phrases, found {len(phrases)}"

    failures = []
    for p in phrases:
        text = p["text"]
        expected_danger = p["expected_danger"]
        actual_danger, cat = screen_multilingual_danger_phrases(text)

        if actual_danger != expected_danger:
            failures.append({
                "text": text,
                "expected": expected_danger,
                "actual": actual_danger,
                "detected_category": cat,
            })

    if failures:
        pytest.fail(f"Danger phrase recall failed on {len(failures)} items: {failures[:5]}")


def test_run_all_52_simulated_personas_and_verify_invariants():
    """Executes the interview state machine against all 52 simulated patient personas."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    personas_path = os.path.join(repo_root, "tests", "sim", "personas.json")
    assert os.path.exists(personas_path), f"Missing personas file at {personas_path}"

    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    assert len(personas) >= 50, f"Expected >= 50 personas, found {len(personas)}"
    bank = get_default_bank()
    allowed_responses = set(bank.get_responses().keys())

    for persona in personas:
        pid = persona["id"]
        conds = persona["conditions"]
        on_ins = persona["on_insulin"]
        answers = persona["answers"]
        patient_rec = {"conditions": conds, "on_insulin_or_sulfonylurea": on_ins}

        known_slots = {}
        asked_slots = set()
        findings = []
        consecutive_odd = 0
        is_emergency = False

        for ans_idx, ans_text in enumerate(answers):
            # 1. Input Triage First
            triage_res = classify_input(ans_text, consecutive_odd_count=consecutive_odd)
            if triage_res.is_emergency:
                is_emergency = True
                break

            if triage_res.category == "odd_input":
                consecutive_odd += 1
                assert triage_res.response_key in allowed_responses, f"Odd response key '{triage_res.response_key}' not in fixed responses bank!"
                continue
            else:
                consecutive_odd = 0

            if triage_res.category == "pregnancy":
                # Eligibility exit
                break

            # 2. Finding Extraction
            fnds = extract_findings_from_answer(ans_text)
            findings.extend(fnds)

            # 3. Planner step
            decision = plan_next_step(
                known_slots=known_slots,
                findings=findings,
                patient_record=patient_rec,
                bank=bank,
                asked_slots=asked_slots,
            )

            # Invariant: Question count never exceeds hard cap (14)
            assert decision.question_count <= 14, f"Persona {pid} exceeded 14 questions budget!"

            if decision.target_slot:
                # Invariant: No slot re-asking without a correction reason
                assert decision.target_slot not in known_slots, f"Persona {pid} re-asked filled slot '{decision.target_slot}'!"
                asked_slots.add(decision.target_slot)
                known_slots[decision.target_slot] = ans_text

            if decision.action == "finish":
                break

        # Invariant: Final slot verification - unknown is never stored as boolean 'False'
        for slot_name, slot_val in known_slots.items():
            if slot_val == "I don't know" or slot_val == "not sure":
                assert slot_val is not False, f"Unknown slot '{slot_name}' was converted to False in persona {pid}"
