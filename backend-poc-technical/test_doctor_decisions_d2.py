"""
Doctor Decisions D2 Tests (Nov 2026).
Spec: "just having heart risk doesn't need a review unless associated with any symptoms" (Doctor on record).

Tests:
(a) High risk + no symptoms gives Green, with the risk band still present in the provider response;
(b) High risk + one symptom gives Yellow with the new reason;
(c) A second symptom check-in within 30 days gives no repeat raise, after cooldown gives a raise;
(d) Low/Moderate risk + symptoms gives no risk raise;
(e) Both ORCHESTRATOR=direct and graph are equivalent.
"""
from __future__ import annotations

import copy
import pytest
from agents.final_triage import decide_stage2, check_has_qualifying_symptoms
from agents.adaptive_interview_agent import InterviewState, INTERVIEW_COMPLETE
from orchestrator.steps import step_risk


FLAGS_ON = {
    "RISK_ENABLED": True,
    "RISK_CAN_RAISE": True,
    "TREND_CAN_RAISE": False,
    "NO_READING_SYMPTOM_RAISE": True,
}

HIGH_RISK_RESULT = {
    "status": "ok",
    "band": "high",
    "probability": 0.28,
    "disease": "cardiovascular",
    "model_name": "chd10_framingham",
    "models": [
        {
            "status": "ok",
            "band": "high",
            "probability": 0.28,
            "disease": "cardiovascular",
            "model_name": "chd10_framingham",
        }
    ],
}

MODERATE_RISK_RESULT = {
    "status": "ok",
    "band": "moderate",
    "probability": 0.15,
    "disease": "cardiovascular",
    "model_name": "chd10_framingham",
    "models": [
        {
            "status": "ok",
            "band": "moderate",
            "probability": 0.15,
            "disease": "cardiovascular",
            "model_name": "chd10_framingham",
        }
    ],
}

LOW_RISK_RESULT = {
    "status": "ok",
    "band": "low",
    "probability": 0.05,
    "disease": "cardiovascular",
    "model_name": "chd10_framingham",
    "models": [
        {
            "status": "ok",
            "band": "low",
            "probability": 0.05,
            "disease": "cardiovascular",
            "model_name": "chd10_framingham",
        }
    ],
}


# =============================================================================
# (a) High Risk + No Symptoms -> Green (Routine)
# =============================================================================
def test_d2_high_risk_asymptomatic_gives_green():
    """Assertion (a): High risk + no symptoms gives Green (routine), risk band remains high."""
    state_asymp = InterviewState(
        patient_id="p_d2_asymp",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={
            "associated_symptoms": "No symptoms",
            "adherence": "Took all meds",
            "lifestyle": "Normal diet",
            "patient_free_text": "None",
        },
    )

    out = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(HIGH_RISK_RESULT),
        flags=FLAGS_ON,
        state=state_asymp,
        cooldown_active=False,
    )

    assert out["final_level"] == "routine"
    assert out["triage_colour"] == "green"
    assert out["raised"] is False
    assert out["triggered_rules"] == ["ROUTINE_UNCHANGED"]
    assert out["patient_reason_key"] is None


# =============================================================================
# (b) High Risk + One Symptom -> Yellow (Review) with new reason text
# =============================================================================
def test_d2_high_risk_with_one_symptom_gives_yellow():
    """Assertion (b): High risk + one symptom gives Yellow with reason text like 'high heart risk with symptoms'."""
    state_symp = InterviewState(
        patient_id="p_d2_symp",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={
            "associated_symptoms": "Mild headache and dizziness",
            "adherence": "Took all meds",
        },
    )

    out = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(HIGH_RISK_RESULT),
        flags=FLAGS_ON,
        state=state_symp,
        cooldown_active=False,
    )

    assert out["final_level"] == "review"
    assert out["triage_colour"] == "yellow"
    assert out["raised"] is True
    assert "R-S2-1" in out["triggered_rules"]
    assert out["patient_reason_key"] == "high_heart_risk_with_symptoms"
    assert len(out["raised_by"]) >= 1
    raised_info = out["raised_by"][0]
    assert raised_info["source"] == "risk_model"
    assert raised_info["band"] == "high"
    assert "high heart risk with symptoms" in raised_info["detail"].lower()


# =============================================================================
# (c) Cooldown Behavior: Repeat check-in within 30 days suppressed
# =============================================================================
def test_d2_cooldown_30_days_suppresses_repeat_raise():
    """Assertion (c): Second symptom check-in within 30 days gives no repeat raise; after cooldown gives raise."""
    state_symp = InterviewState(
        patient_id="p_d2_cd",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={"associated_symptoms": "headache"},
    )

    # 1. Initial check-in (cooldown inactive): raises to review
    out_initial = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(HIGH_RISK_RESULT),
        flags=FLAGS_ON,
        state=state_symp,
        cooldown_active=False,
    )
    assert out_initial["final_level"] == "review"
    assert out_initial["raised"] is True

    # 2. Second check-in within 30 days (cooldown active): suppressed, stays routine
    out_within_cooldown = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(HIGH_RISK_RESULT),
        flags=FLAGS_ON,
        state=state_symp,
        cooldown_active=True,
    )
    assert out_within_cooldown["final_level"] == "routine"
    assert out_within_cooldown["triage_colour"] == "green"
    assert out_within_cooldown["raised"] is False

    # 3. Subsequent check-in after 30-day cooldown expires (cooldown inactive): raises again
    out_after_cooldown = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(HIGH_RISK_RESULT),
        flags=FLAGS_ON,
        state=state_symp,
        cooldown_active=False,
    )
    assert out_after_cooldown["final_level"] == "review"
    assert out_after_cooldown["triage_colour"] == "yellow"
    assert out_after_cooldown["raised"] is True


# =============================================================================
# (d) Low / Moderate Risk + Symptoms -> No Risk Raise
# =============================================================================
@pytest.mark.parametrize("risk_payload", [LOW_RISK_RESULT, MODERATE_RISK_RESULT])
def test_d2_low_moderate_risk_with_symptoms_gives_no_raise(risk_payload):
    """Assertion (d): Low or Moderate risk + symptoms gives no risk raise (stays routine)."""
    state_symp = InterviewState(
        patient_id="p_d2_low_mod",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={"associated_symptoms": "Mild headache"},
    )

    out = decide_stage2(
        rules_level="routine",
        risk_results=copy.deepcopy(risk_payload),
        flags=FLAGS_ON,
        state=state_symp,
        cooldown_active=False,
    )

    assert out["final_level"] == "routine"
    assert out["triage_colour"] == "green"
    assert out["raised"] is False


# =============================================================================
# (e) Direct and Graph Orchestrator Equivalence
# =============================================================================
def test_d2_orchestrator_step_risk_equivalence(monkeypatch):
    """Assertion (e): Both direct and graph orchestrators utilize step_risk identically for D2."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "true")

    # Mock risk_agent.assess to return HIGH_RISK_RESULT
    import agents.risk_agent as ra
    monkeypatch.setattr(ra, "assess", lambda *args, **kwargs: copy.deepcopy(HIGH_RISK_RESULT))

    # Profile with hypertension
    mock_profile = {
        "date_of_birth": "1960-01-01",
        "sex_at_birth": "male",
        "conditions": ["hypertension"],
        "waist_cm": 95.0,
    }

    # Case 1: Asymptomatic patient
    state_asymp = InterviewState(
        patient_id="p_eq_asymp",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={"associated_symptoms": "None", "lifestyle": "Fine"},
    )
    triage_dec_asymp = {
        "final_triage_level": "routine",
        "triage_colour": "green",
        "final_requires_review": False,
        "final_max_sev": "none",
        "review_status": "resolved",
        "triage_dict": {"level": "routine", "triage_colour": "green"},
    }

    res_asymp = step_risk(
        user_id="u_asymp",
        state=state_asymp,
        triage_decision=triage_dec_asymp,
        get_patient_profile_fn=lambda uid: mock_profile,
        get_reading_history_fn=lambda uid, days=30: [],
    )

    assert triage_dec_asymp["final_triage_level"] == "routine"
    assert triage_dec_asymp["triage_colour"] == "green"
    assert triage_dec_asymp["final_requires_review"] is False
    assert res_asymp["raised"] is False
    assert res_asymp["models"][0]["band"] == "high"

    # Case 2: Symptomatic patient
    state_symp = InterviewState(
        patient_id="p_eq_symp",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={"associated_symptoms": "Dizziness and headache"},
    )
    triage_dec_symp = {
        "final_triage_level": "routine",
        "triage_colour": "green",
        "final_requires_review": False,
        "final_max_sev": "none",
        "review_status": "resolved",
        "triage_dict": {"level": "routine", "triage_colour": "green"},
    }

    res_symp = step_risk(
        user_id="u_symp",
        state=state_symp,
        triage_decision=triage_dec_symp,
        get_patient_profile_fn=lambda uid: mock_profile,
        get_reading_history_fn=lambda uid, days=30: [],
    )

    assert triage_dec_symp["final_triage_level"] == "review"
    assert triage_dec_symp["triage_colour"] == "yellow"
    assert triage_dec_symp["final_requires_review"] is True
    assert triage_dec_symp["review_status"] == "open"
    assert res_symp["raised"] is True
    assert triage_dec_symp["patient_reason_key"] == "high_heart_risk_with_symptoms"
