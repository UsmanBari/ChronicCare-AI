"""
Unit and integration tests for Stage-2 Final Triage Agent (PR A).
Proposal Sections 13.1 Agent 10, 15, and 17.

Tests:
T1: Equivalence & single source of truth mapping.
T2: Never lower, never emergency (full parametric state exploration).
T3: R-S2-2 trend escalation cases (5 check-in threshold, target ranges, kill switch).
T4: Multi-model risk loading, population applicability, missing features, SHAP identity.
T5: Section 17 confidence table & first-checkin cap.
T6: Triage colour across endpoints & patient risk visibility privacy invariants.
T7: Seed script refuses MySQL.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from agents.final_triage import (
    level_to_colour,
    decide_stage2,
    TREND_MIN_POINTS,
    TARGET_THRESHOLDS,
)
from agents.triage_protocol import LEVEL_RANK
from agents import risk_agent


# =============================================================================
# T1: Single Source of Truth & Equivalence
# =============================================================================

def test_t1_level_to_colour_mapping():
    """Verify single source of truth triage colour mapping."""
    assert level_to_colour("routine") == "green"
    assert level_to_colour("review") == "yellow"
    assert level_to_colour("urgent") == "red"
    assert level_to_colour("emergency") == "red"

    # Case insensitivity & whitespace trimming
    assert level_to_colour(" Routine ") == "green"
    assert level_to_colour("REVIEW") == "yellow"
    assert level_to_colour("Urgent") == "red"
    assert level_to_colour(" Emergency ") == "red"

    # Unknown level must raise ValueError (never guesses a colour)
    with pytest.raises(ValueError):
        level_to_colour("unknown")
    with pytest.raises(ValueError):
        level_to_colour("")
    with pytest.raises(ValueError):
        level_to_colour("critical")


# =============================================================================
# T2: Invariants: Never Lower, Never Emergency, At Most 1 Step
# =============================================================================

@pytest.mark.parametrize("rules_level", ["routine", "review", "urgent", "emergency"])
@pytest.mark.parametrize("risk_band", ["low", "moderate", "high", "not_enough_information"])
@pytest.mark.parametrize("trend_dir", ["rising", "stable", "falling", "not_enough_history"])
@pytest.mark.parametrize("flags_combo", [
    {"RISK_ENABLED": False, "RISK_CAN_RAISE": False, "TREND_CAN_RAISE": False},
    {"RISK_ENABLED": True, "RISK_CAN_RAISE": False, "TREND_CAN_RAISE": False},
    {"RISK_ENABLED": True, "RISK_CAN_RAISE": True, "TREND_CAN_RAISE": False},
    {"RISK_ENABLED": True, "RISK_CAN_RAISE": True, "TREND_CAN_RAISE": True},
])
def test_t2_invariants_never_lower_never_emergency(rules_level, risk_band, trend_dir, flags_combo):
    """
    Parametric verification of safety invariants:
    - Never lower (final_level >= rules_level)
    - Emergency is never altered or touched
    - Urgent is never lowered
    - Stage-2 can only raise routine -> review (at most 1 step, never to urgent or emergency)
    """
    risk_results = {
        "status": "ok" if risk_band != "not_enough_information" else "not_enough_information",
        "band": risk_band,
        "disease": "diabetes",
    }
    trends = {
        "blood_pressure_systolic": {
            "direction": trend_dir,
            "n": 6,
            "values": [{"value": 150.0}] * 6,
        }
    }

    out = decide_stage2(
        rules_level=rules_level,
        risk_results=risk_results,
        trends=trends,
        flags=flags_combo,
    )

    final_lvl = out["final_level"]

    # Invariant: Never lower
    assert LEVEL_RANK[final_lvl] >= LEVEL_RANK[rules_level]

    # Invariant: Emergency never touched
    if rules_level == "emergency":
        assert final_lvl == "emergency"
        assert out["triage_colour"] == "red"
        assert out["raised"] is False

    # Invariant: Urgent never lowered or raised
    if rules_level == "urgent":
        assert final_lvl == "urgent"
        assert out["triage_colour"] == "red"
        assert out["raised"] is False

    # Invariant: Review never lowered
    if rules_level == "review":
        assert final_lvl == "review"
        assert out["triage_colour"] == "yellow"
        assert out["raised"] is False

    # Invariant: Routine can only become review at most (never urgent or emergency)
    if rules_level == "routine":
        assert final_lvl in ("routine", "review")
        assert out["triage_colour"] in ("green", "yellow")


# =============================================================================
# T3: R-S2-2 Trend Escalation Cases (Doctor's Answer 2)
# =============================================================================

def test_t3_trend_escalation_rules():
    """
    Tests R-S2-2:
    - 5 rising points + latest >= 140 mmHg -> review (flag on)
    - 5 rising points + latest < 140 mmHg -> routine
    - Only 4 points -> routine (TREND_MIN_POINTS = 5)
    - Flag off -> routine
    """
    flags_on = {"TREND_CAN_RAISE": True}
    flags_off = {"TREND_CAN_RAISE": False}

    # Case 1: 5 points, rising, latest 145 (above 140 target), flag on -> review
    trends_5_elevated = {
        "blood_pressure_systolic": {
            "direction": "rising",
            "n": 5,
            "values": [{"value": 130}, {"value": 134}, {"value": 138}, {"value": 142}, {"value": 145}],
        }
    }
    out1 = decide_stage2("routine", trends=trends_5_elevated, flags=flags_on)
    assert out1["final_level"] == "review"
    assert out1["triage_colour"] == "yellow"
    assert out1["raised"] is True
    assert out1["patient_reason_key"] == "trend_rising"
    assert any(r["source"] == "trend" for r in out1["raised_by"])

    # Case 2: 5 points, rising, but latest 135 (inside target range < 140) -> routine
    trends_5_normal = {
        "blood_pressure_systolic": {
            "direction": "rising",
            "n": 5,
            "values": [{"value": 115}, {"value": 120}, {"value": 125}, {"value": 130}, {"value": 135}],
        }
    }
    out2 = decide_stage2("routine", trends=trends_5_normal, flags=flags_on)
    assert out2["final_level"] == "routine"
    assert out2["triage_colour"] == "green"
    assert out2["raised"] is False

    # Case 3: Only 4 points, rising, latest 150 -> routine (fails 5-point minimum)
    trends_4_elevated = {
        "blood_pressure_systolic": {
            "direction": "rising",
            "n": 4,
            "values": [{"value": 135}, {"value": 140}, {"value": 145}, {"value": 150}],
        }
    }
    out3 = decide_stage2("routine", trends=trends_4_elevated, flags=flags_on)
    assert out3["final_level"] == "routine"
    assert out3["raised"] is False

    # Case 4: Flag off -> routine
    out4 = decide_stage2("routine", trends=trends_5_elevated, flags=flags_off)
    assert out4["final_level"] == "routine"
    assert out4["raised"] is False

    # Case 5: Glucose series (target threshold 180 mg/dL)
    trends_glucose_elevated = {
        "glucose": {
            "direction": "rising",
            "n": 5,
            "values": [{"value": 140}, {"value": 155}, {"value": 168}, {"value": 182}, {"value": 195}],
        }
    }
    out5 = decide_stage2("routine", trends=trends_glucose_elevated, flags=flags_on)
    assert out5["final_level"] == "review"
    assert out5["raised"] is True
    assert out5["patient_reason_key"] == "trend_rising"


def test_t3_risk_cooldown():
    """Verify RISK_RAISE_COOLDOWN_DAYS prevents repeat risk raise when cooldown is active."""
    flags = {"RISK_ENABLED": True, "RISK_CAN_RAISE": True}
    high_risk = {"status": "ok", "band": "high", "disease": "diabetes", "model_name": "diabetes_full_nhanes"}

    # Cooldown inactive -> raises to review
    out_active = decide_stage2("routine", risk_results=high_risk, flags=flags, cooldown_active=False)
    assert out_active["final_level"] == "review"
    assert out_active["raised"] is True

    # Cooldown active -> remains routine
    out_cooldown = decide_stage2("routine", risk_results=high_risk, flags=flags, cooldown_active=True)
    assert out_cooldown["final_level"] == "routine"
    assert out_cooldown["raised"] is False


def test_t3_symptom_raise_pending_signoff():
    """Verify R-S2-4: no readings + unwell symptoms raises to review behind NO_READING_SYMPTOM_RAISE flag."""
    flags_on = {"NO_READING_SYMPTOM_RAISE": True}
    flags_off = {"NO_READING_SYMPTOM_RAISE": False}

    class DummyState:
        def __init__(self, text):
            self.answers = {"symptom": text}
            self.intakes = []

    state_unwell = DummyState("I am feeling very bad and dizzy")
    state_fine = DummyState("Feeling completely fine today")

    # Flag on + no readings + unwell -> review
    out1 = decide_stage2("routine", flags=flags_on, state=state_unwell, has_readings=False)
    assert out1["final_level"] == "review"
    assert out1["raised"] is True
    assert out1["patient_reason_key"] == "symptoms_without_readings"

    # Flag on + has readings -> remains routine (R-S2-4 applies only when no readings)
    out2 = decide_stage2("routine", flags=flags_on, state=state_unwell, has_readings=True)
    assert out2["final_level"] == "routine"
    assert out2["raised"] is False

    # Flag on + fine -> remains routine
    out3 = decide_stage2("routine", flags=flags_on, state=state_fine, has_readings=False)
    assert out3["final_level"] == "routine"
    assert out3["raised"] is False

    # Flag off -> remains routine
    out4 = decide_stage2("routine", flags=flags_off, state=state_unwell, has_readings=False)
    assert out4["final_level"] == "routine"
    assert out4["raised"] is False


# =============================================================================
# T4: Multi-Model Loading & SHAP Driver Identity
# =============================================================================

def test_t4_shap_identity_and_multi_model():
    """
    Tests:
    1. Multi-model dynamic folder loading from a temporary directory.
    2. Population routing: hypertension_not_diabetes vs hypertension_or_diabetes.
    3. Missing feature reports not_enough_information for that model only.
    4. SHAP sum identity: base logit (intercept) + sum(contributions) == logit within 1e-9.
    """
    fake_chd_model = {
        "disease": "chd10",
        "population": "hypertension_or_diabetes",
        "model_name": "chd10_framingham",
        "version": "1.0.0",
        "features": ["age", "sex_male", "bmi", "sbp", "dbp", "current_smoker", "bp_meds", "diabetes", "prevalent_hyp"],
        "intercept": -2.5,
        "coefficients": {
            "age": 0.05,
            "sex_male": 0.4,
            "bmi": 0.03,
            "sbp": 0.02,
            "dbp": 0.01,
            "current_smoker": 0.5,
            "bp_meds": 0.3,
            "diabetes": 0.6,
            "prevalent_hyp": 0.4,
        },
        "scaler": {
            "means": {f: 50.0 if f == "age" else 0.5 for f in ["age", "sex_male", "bmi", "sbp", "dbp", "current_smoker", "bp_meds", "diabetes", "prevalent_hyp"]},
            "scales": {f: 10.0 if f == "age" else 1.0 for f in ["age", "sex_male", "bmi", "sbp", "dbp", "current_smoker", "bp_meds", "diabetes", "prevalent_hyp"]},
        },
        "thresholds": {"moderate": 0.10, "high": 0.20},
        "label_text": {"en": "Framingham 10-year CHD research model"},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = os.path.join(tmpdir, "chd10_framingham.json")
        with open(fake_path, "w", encoding="utf-8") as f:
            json.dump(fake_chd_model, f)

        # 1. Load models from tmp directory
        models = risk_agent.load_models(tmpdir)
        assert len(models) == 1
        model = list(models.values())[0]
        assert model["model_name"] == "chd10_framingham"

        # 2. Complete features assessment
        profile = {
            "date_of_birth": "1970-01-01",
            "sex_at_birth": "male",
            "height_cm": 175,
            "weight_kg": 75,
            "smoking_status": "current",
            "medications": ["Amlodipine 5mg"],
            "conditions": ["hypertension"],
        }
        readings = [
            {"observation_type": "blood_pressure_systolic", "value": 145.0, "source": "fhir", "timestamp": "2026-10-30T10:00:00Z"},
            {"observation_type": "blood_pressure_diastolic", "value": 90.0, "source": "fhir", "timestamp": "2026-10-30T10:00:00Z"},
        ]

        res = risk_agent.evaluate_model(model, profile, readings, ["hypertension"], now="2026-10-30T12:00:00Z")
        assert res["status"] == "ok"
        assert res["band"] in ("low", "moderate", "high")

        # 3. SHAP sum identity verification:
        # intercept + sum(contributions) == logit (within 1e-9 tolerance)
        logit = res["logit"]
        intercept = model["intercept"]
        total_contributions = sum(res["contributions"].values())
        reconstructed_logit = intercept + total_contributions
        assert abs(reconstructed_logit - logit) < 1e-9, f"SHAP sum mismatch: {reconstructed_logit} vs {logit}"

        # 4. Top reasons sorted by magnitude with sign
        top_reasons = res["top_reasons"]
        assert len(top_reasons) <= 3
        for r in top_reasons:
            assert r["sign"] in ("+", "-")
            assert "contribution" in r
            assert "feature" in r

        # 5. Missing feature reports not_enough_information
        profile_incomplete = copy.deepcopy(profile)
        del profile_incomplete["date_of_birth"]  # age missing
        res_missing = risk_agent.evaluate_model(model, profile_incomplete, readings, ["hypertension"])
        assert res_missing["status"] == "not_enough_information"
        assert "age" in res_missing["missing"]


# =============================================================================
# T5: Section 17 Confidence Rules
# =============================================================================

def test_t5_confidence_rules_table():
    """
    Tests Section 17 confidence rules:
    - High: FHIR reading, same day, no conflict
    - Medium: patient-typed reading or FHIR > 7 days
    - Low: OCR unconfirmed
    - First check-in: capped at Medium
    """
    # 1. High: FHIR same-day, not first checkin
    meta_fhir_same_day = {"source": "fhir", "age_days": 0, "conflict": False}
    assert risk_agent.compute_confidence(meta_fhir_same_day, is_first_checkin=False) == "High"

    # 2. First check-in capped at Medium
    assert risk_agent.compute_confidence(meta_fhir_same_day, is_first_checkin=True) == "Medium"

    # 3. Medium: Patient typed reading
    meta_patient = {"source": "patient", "age_days": 0}
    assert risk_agent.compute_confidence(meta_patient, is_first_checkin=False) == "Medium"

    # 4. Medium: FHIR older than 7 days
    meta_fhir_old = {"source": "fhir", "age_days": 10, "conflict": False}
    assert risk_agent.compute_confidence(meta_fhir_old, is_first_checkin=False) == "Medium"

    # 5. Low: OCR unconfirmed
    meta_ocr = {"source": "ocr_unconfirmed", "age_days": 0}
    assert risk_agent.compute_confidence(meta_ocr, is_first_checkin=False) == "Low"


# =============================================================================
# T6: Endpoint triage_colour & Patient Risk Privacy Invariant
# =============================================================================

def test_t6_patient_risk_visibility_and_privacy_invariants():
    """
    Verifies:
    1. When RISK_PATIENT_VISIBLE is unset/false: patient risk view is None.
    2. When RISK_PATIENT_VISIBLE is true: returns list with ONLY model_key, band, message_key.
    3. Strict scan: fails if any float, probability, driver, coefficient, intercept, or raised_by exists.
    """
    from orchestrator.steps import _build_patient_risk_list

    mock_risk = [
        {
            "model_key": "chd10_framingham",
            "model_name": "Framingham 10-Year Cardiovascular Disease Risk Model",
            "status": "ok",
            "band": "high",
            "probability": 0.245,
            "logit": -0.85,
            "contributions": {"age": 0.45, "sbp": 0.32},
            "top_reasons": [{"feature": "age", "contribution": 0.45}],
            "raised_by": "risk_model",
        },
        {
            "model_key": "diabetes_full_nhanes",
            "model_name": "Full Diabetes Risk Model (US NHANES)",
            "status": "not_enough_information",
            "missing": ["waist_cm"],
        }
    ]

    # 1. When flag is false/unset -> returns None
    os.environ["RISK_PATIENT_VISIBLE"] = "false"
    assert _build_patient_risk_list(mock_risk) is None

    # 2. When flag is true -> returns sanitized patient cards
    os.environ["RISK_PATIENT_VISIBLE"] = "true"
    cards = _build_patient_risk_list(mock_risk)
    assert cards is not None
    assert len(cards) == 2

    # Verify first card (ok status)
    card0 = cards[0]
    assert card0["model_key"] == "chd10_framingham"
    assert card0["band"] == "high"
    assert card0["message_key"] == "risk_chd_high"

    # Verify second card (not_enough_information)
    card1 = cards[1]
    assert card1["model_key"] == "diabetes_full_nhanes"
    assert card1["band"] == "not_enough_information"
    assert card1["message_key"] == "risk_diabetes_not_enough_info"

    # 3. Privacy scan: serialize to JSON and strictly assert NO prohibited clinical internals leak
    cards_json = json.dumps(cards)
    cards_raw = json.loads(cards_json)

    for c in cards_raw:
        # Permitted keys ONLY
        assert set(c.keys()) <= {"model_key", "band", "message_key"}
        # Never expose floats or probability decimals
        for v in c.values():
            assert not isinstance(v, float)
            assert not isinstance(v, int)

    # Negative string pattern assertions
    assert "0.245" not in cards_json
    assert "probability" not in cards_json
    assert "logit" not in cards_json
    assert "contributions" not in cards_json
    assert "top_reasons" not in cards_json
    assert "raised_by" not in cards_json
    assert "Framingham 10-Year" not in cards_json

    # Clean up env
    os.environ["RISK_PATIENT_VISIBLE"] = "false"


# =============================================================================
# T7: Seed Script Refuses MySQL
# =============================================================================

def test_t7_seed_script_refuses_mysql(monkeypatch):
    """Verifies that seed_demo_local refuses to execute if DB_BACKEND is mysql or MYSQL_URL is set."""
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("MYSQL_URL", "mysql://root:secret@localhost:3306/chronicare")

    from scripts.seed_demo_local import check_sqlite_local_guard
    with pytest.raises(RuntimeError) as exc_info:
        check_sqlite_local_guard()

    assert "refusing to run on mysql" in str(exc_info.value).lower()
