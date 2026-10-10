"""
Unit Tests for Glucose mmol/L Conversion in Interview Engine v3 (Stage 9A-6 Task A).

Verifies that explicit mmol/L inputs (2.0, 3.8, 7.0, 10.0 mmol/L) are converted with x18.0
to mg/dL and yield the EXACT SAME triage level as their matching mg/dL values.
"""

import os
import pytest
from agents.interview_v3_runner import start_v3_session, next_turn, finish_v3_session
from agents.triage_protocol import evaluate_triggers, _decide, TriageProtocolState, GLUCOSE


@pytest.mark.parametrize(
    "mmol_str, mmol_val, matching_mgdl_str, matching_mgdl_val, expected_level",
    [
        ("2.0 mmol/L", 2.0, "36 mg/dL", 36.0, "urgent"),
        ("3.8 mmol/L", 3.8, "68.4 mg/dL", 68.4, "review"),
        ("7.0 mmol/L", 7.0, "126 mg/dL", 126.0, "routine"),
        ("10.0 mmol/L", 10.0, "180 mg/dL", 180.0, "routine"),
    ],
)
def test_v3_mmol_conversion_matches_mgdl_triage(
    mmol_str, mmol_val, matching_mgdl_str, matching_mgdl_val, expected_level, monkeypatch
):
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")

    # 1. Run v3 turn with mmol/L input
    session_mmol = start_v3_session(
        checkin_id="test-mmol",
        patient_id="patient-1",
        conditions=["diabetes"],
    )
    # Ensure current question expects glucose reading
    assert session_mmol["step"] in ("diabetes_glucose_reading", "glucose_reading", "greeting")
    if session_mmol["step"] == "greeting":
        session_mmol = next_turn(session_mmol, "Feeling fine, no complaints")

    session_mmol = next_turn(session_mmol, mmol_str)
    mmol_stored = session_mmol["readings"].get("glucose")
    assert mmol_stored is not None, f"Expected glucose reading stored for {mmol_str}"
    assert mmol_stored == pytest.approx(mmol_val * 18.0, abs=0.1)

    # 2. Run v3 turn with matching mg/dL input
    session_mgdl = start_v3_session(
        checkin_id="test-mgdl",
        patient_id="patient-2",
        conditions=["diabetes"],
    )
    if session_mgdl["step"] == "greeting":
        session_mgdl = next_turn(session_mgdl, "Feeling fine, no complaints")

    session_mgdl = next_turn(session_mgdl, matching_mgdl_str)
    mgdl_stored = session_mgdl["readings"].get("glucose")
    assert mgdl_stored is not None, f"Expected glucose reading stored for {matching_mgdl_str}"
    assert mgdl_stored == pytest.approx(matching_mgdl_val, abs=0.1)

    # 3. Verify triage level is identical between mmol and mg/dL
    def get_triage_level(stored_glucose):
        trigs = evaluate_triggers({"glucose": stored_glucose})
        if not trigs:
            return "routine"
        p_state = TriageProtocolState(
            protocol=trigs[0].protocol,
            age_band="adult",
            trigger_reason=trigs[0].reason,
            readings={"glucose": stored_glucose},
            answers={
                "neuro": False,
                "can_swallow": True,
                "symptoms": False,
                "recheck": None,
                "substances": False,
                "circumstances": False,
                "dka_symptoms": False,
                "thirst": False,
                "context": False,
            },
        )
        dec = _decide(p_state)
        return dec["level"]

    mmol_level = get_triage_level(mmol_stored)
    mgdl_level = get_triage_level(mgdl_stored)

    assert mmol_level == mgdl_level == expected_level, (
        f"Mismatch for {mmol_str} ({mmol_level}) vs {matching_mgdl_str} ({mgdl_level}), "
        f"expected {expected_level}"
    )
