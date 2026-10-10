"""
Unit tests for vomiting and inability to keep fluids red-flag screen (Stage 9A-7 Task B).
Verifies:
1. Cannot keep fluids down triggers red flag (unable_to_keep_fluids).
2. All added phrase variants trigger red flag.
3. Negations do NOT trigger.
4. Mutation kill test: removing 'cannot keep fluids down' causes test failure.
"""

import pytest
from agents.adaptive_interview_agent import run_stage1_red_flag_screen as screen_red_flags
from agents.input_triage import classify_input


def test_cannot_keep_fluids_down_triggers_red_flag():
    """Direct proof that 'cannot keep fluids down' triggers red flag."""
    triggered, reason = screen_red_flags("I have been vomiting and cannot keep fluids down")
    assert triggered is True, "Expected red flag to trigger for vomiting and cannot keep fluids down"
    assert reason == "unable_to_keep_fluids", f"Expected unable_to_keep_fluids, got {reason}"


def test_vomiting_phrase_variants_trigger():
    """All caution-raising variants must trigger red flag."""
    variants = [
        "cannot keep fluids down",
        "can not keep fluids down",
        "unable to keep fluids down",
        "not able to keep fluids down",
        "cannot keep anything down",
        "can not keep anything down",
        "unable to keep anything down",
        "not able to keep anything down",
        "won't stay down",
        "wont stay down",
        "throwing up everything",
        "keep nothing down",
        "vomiting all day",
        "musalsal ultiyan",
        "ulti ruk nahi rahi",
        "paani bhi nahi rukta",
    ]
    for phrase in variants:
        triggered, reason = screen_red_flags(phrase)
        assert triggered is True, f"Failed to trigger red flag for: '{phrase}'"
        assert reason == "unable_to_keep_fluids", f"Expected unable_to_keep_fluids for: '{phrase}', got {reason}"


def test_vomiting_negations_do_not_trigger():
    """Negated vomiting statements must NOT trigger red flag."""
    negations = [
        "I am not vomiting",
        "no vomiting, I can keep fluids down",
        "I do not have vomiting and can keep fluids down",
        "denies vomiting all day",
        "without vomiting and able to keep fluids down",
        "never had vomiting, keeping fluids down fine",
    ]
    for phrase in negations:
        triggered, reason = screen_red_flags(phrase)
        assert triggered is False, f"Negation erroneously triggered red flag for: '{phrase}' (reason: {reason})"


def test_classify_input_catches_vomiting_variants():
    """Verifies classify_input catches vomiting and cannot keep fluids down as emergency danger."""
    res = classify_input("I have been vomiting and cannot keep fluids down")
    assert res.is_emergency is True
    assert res.category == "danger_phrase"


def test_mutation_proof_vomiting_fluids():
    """Mutation proof test: verifies that 'cannot keep fluids down' is authoritatively required."""
    phrase = "cannot keep fluids down"
    triggered, reason = screen_red_flags(phrase)
    assert triggered is True
    assert reason == "unable_to_keep_fluids"
