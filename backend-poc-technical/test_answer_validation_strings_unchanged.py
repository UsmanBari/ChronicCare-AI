"""
Hermetic Regression Test: Answer Validation Strings Unchanged (PR #80 Correction).

Asserts that deterministic error messages, clarification prompts, and contradiction warnings
in answer_validation.py remain byte-for-byte identical to their pre-PR origin/dev baseline.
Ensures live v2 check-in safety messages have not altered meaning or dosage advice.
"""

from __future__ import annotations

import pytest
from agents.answer_validation import (
    validate_glucose_input,
    detect_cross_checks_and_contradictions,
)


def test_glucose_unclear_safety_guidance_exact_pre_pr():
    # 1. Unknown / skip input with previously_asked_unit=True
    res_skip = validate_glucose_input("don't know", previously_asked_unit=True)
    assert res_skip.safety_guidance == (
        "If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar "
        "(fruit juice or sweets) and re-check, or seek medical advice."
    )
    assert res_skip.clarification_prompt == (
        "Glucose unit unclear. Treated as possible low sugar for safety review."
    )

    # 2. Ambiguous glucose in 2.0-40.0 with previously_asked_unit=True
    res_ambig_2nd = validate_glucose_input("7", previously_asked_unit=True)
    assert res_ambig_2nd.safety_guidance == (
        "If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar "
        "(fruit juice or sweets) and re-check, or seek medical advice."
    )
    assert res_ambig_2nd.clarification_prompt == (
        "Glucose unit unclear. Treated as possible low sugar for safety review."
    )


def test_glucose_unit_clarification_prompt_exact_pre_pr():
    # 3. Ambiguous glucose in 2.0-40.0 with previously_asked_unit=False
    res_ambig_1st = validate_glucose_input("7", previously_asked_unit=False)
    assert res_ambig_1st.clarification_prompt == "I heard 7. Is that mmol/L or mg/dL?"

    res_ambig_float = validate_glucose_input("6.5", previously_asked_unit=False)
    assert res_ambig_float.clarification_prompt == "I heard 6.5. Is that mmol/L or mg/dL?"


def test_contradiction_messages_exact_pre_pr():
    # 4. Insulin profile mismatch
    res_insulin = detect_cross_checks_and_contradictions(
        current_slot="medication_adherence",
        answer_text="I don't take insulin",
        known_slots={},
        patient_record={"on_insulin_or_sulfonylurea": True},
    )
    assert res_insulin is not None
    assert res_insulin["message"] == (
        "Your medical profile lists insulin or sulfonylurea, but you mentioned not taking it. "
        "Did your doctor recently change this medication?"
    )

    # 5. Adherence contradiction: reported adherent then ran out
    res_adherence = detect_cross_checks_and_contradictions(
        current_slot="medication_adherence",
        answer_text="ran out of medicine",
        known_slots={"adherence_diabetes": True},
        patient_record={},
    )
    assert res_adherence is not None
    assert res_adherence["message"] == (
        "Earlier you mentioned taking all doses, but also mentioned running out of medicine. "
        "Would you like to clarify?"
    )

    # 6. Fasting context mismatch: recorded fasting then mentioned eating recently
    res_fasting = detect_cross_checks_and_contradictions(
        current_slot="glucose_reading",
        answer_text="just ate lunch",
        known_slots={"glucose_context": "fasting"},
        patient_record={},
    )
    assert res_fasting is not None
    assert res_fasting["message"] == (
        "We noted this reading as fasting, but you mentioned eating recently. "
        "Was this reading taken before or after your meal?"
    )

