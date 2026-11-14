"""
Doctor Decision D5 Tests (Nov 2026).
Spec: "No don't review the normal stuff, normal parameters should also be added to the app to avoid confusion"
(The doctor on record).

Tests:
1. Normal self-reported BP and glucose with no record value gives routine / Green,
   with the "self-reported" / low-trust label still present and auto-resolved reason.
2. Abnormal self-reported value with no record value gives review / Yellow (unchanged).
3. Normal self-reported value that CONFLICTS with the hospital record behaves as today (review required).
4. Red flags and emergencies remain emergency / Red regardless of normal vitals.
5. Connected AND isolated mode equivalence.
6. ORCHESTRATOR direct AND graph equivalence.
"""

from __future__ import annotations

import copy
import pytest
from agents.reconciliation_agent import ObservationComparison, ReconciliationResult
from agents.verification_agent import verify_reconciliation, derive_trust_level
from agents.reference_ranges import is_reading_in_normal_range, get_all_reference_ranges
from agents.adaptive_interview_agent import InterviewState, INTERVIEW_COMPLETE
from agents.triage_protocol import TriageProtocolState
from data_sources.models import NormalizedPatient, NormalizedObservation
from orchestrator.steps import (
    step_reconcile,
    step_verify,
    step_decide_triage,
)


def _make_recon_result(patient_id: str, comparisons: list) -> ReconciliationResult:
    status_counts = {"agree": 0, "conflict": 0, "missing_in_a": 0, "missing_in_b": 0, "insufficient_data": 0}
    for c in comparisons:
        st = c.status
        if st in status_counts:
            status_counts[st] += 1
    return ReconciliationResult(
        patient_id=patient_id,
        observation_comparisons=comparisons,
        medication_comparisons=[],
        summary=status_counts,
    )


# =============================================================================
# 1. Normal Self-Reported Readings Auto-Resolve While Keeping Low-Trust Label
# =============================================================================
def test_d5_normal_self_reported_vitals_auto_resolve():
    """
    D5 core rule: A self-reported reading with no record value (missing_in_a)
    that falls within the normal reference range does NOT require review.
    Trust level remains low/'self-reported', provenance preserved.
    """
    comp_sbp = ObservationComparison(
        observation_type="blood_pressure_systolic",
        value_a=None,
        value_b=120.0,
        unit_a=None,
        unit_b="mmHg",
        source_a=None,
        source_b="checkin",
        source_record_id_a=None,
        source_record_id_b="chk-sbp-1",
        timestamp_a=None,
        timestamp_b="2026-11-14T10:00:00Z",
        status="missing_in_a",
        delta=None,
    )
    comp_dbp = ObservationComparison(
        observation_type="blood_pressure_diastolic",
        value_a=None,
        value_b=80.0,
        unit_a=None,
        unit_b="mmHg",
        source_a=None,
        source_b="checkin",
        source_record_id_a=None,
        source_record_id_b="chk-dbp-1",
        timestamp_a=None,
        timestamp_b="2026-11-14T10:00:00Z",
        status="missing_in_a",
        delta=None,
    )
    comp_glucose = ObservationComparison(
        observation_type="glucose",
        value_a=None,
        value_b=100.0,
        unit_a=None,
        unit_b="mg/dL",
        source_a=None,
        source_b="checkin",
        source_record_id_a=None,
        source_record_id_b="chk-glu-1",
        timestamp_a=None,
        timestamp_b="2026-11-14T10:00:00Z",
        status="missing_in_a",
        delta=None,
    )

    recon = _make_recon_result("pat-d5-normal", [comp_sbp, comp_dbp, comp_glucose])
    origins = {
        "chk-sbp-1": "self_reported",
        "chk-dbp-1": "self_reported",
        "chk-glu-1": "self_reported",
    }
    verif = verify_reconciliation(recon, origins=origins)

    # 1. Summary: 0 requires_review, all 3 auto-resolved
    assert verif.summary["requires_review"] == 0, f"Expected 0 requires_review, got {verif.summary['requires_review']}"
    assert verif.summary["auto_resolved"] == 3

    # 2. Individual observation checks:
    for obs in verif.observation_verifications:
        assert obs.requires_human_review is False
        assert obs.severity == "low"
        assert "within normal reference range (auto-resolved)" in obs.review_reason
        # Trust tag and provenance are preserved:
        assert obs.trust_level_a is None
        assert obs.trust_level_b == "low"
        assert obs.source_b == "checkin"

    # 3. When fed into triage decision, check-in stays routine / Green!
    proto_state = TriageProtocolState(
        protocol="bp_severe",
        age_band="adult",
        result={"level": "routine", "reasons": [], "factors": []},
    )
    intake_state = InterviewState(patient_id="pat-d5-normal", conditions_on_file=["hypertension", "diabetes"], step=INTERVIEW_COMPLETE)
    dec = step_decide_triage(
        verif_result=verif,
        state=intake_state,
        protocol_state=proto_state,
        user_id="pat-d5-normal",
        get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
    )
    assert dec["final_triage_level"] == "routine"
    assert dec["final_requires_review"] is False
    assert dec["review_status"] == "resolved"


# =============================================================================
# 2. Abnormal Self-Reported Readings Require Review (Unchanged)
# =============================================================================
def test_d5_abnormal_self_reported_vitals_require_review():
    """
    Abnormal self-reported vitals (e.g. Stage 2 BP 155/95 or Glucose 240)
    with no hospital record must still require human review (severity moderate).
    """
    comp_abnormal = ObservationComparison(
        observation_type="blood_pressure_systolic",
        value_a=None,
        value_b=155.0,  # Abnormal (>140 Stage 2)
        unit_a=None,
        unit_b="mmHg",
        source_a=None,
        source_b="checkin",
        source_record_id_a=None,
        source_record_id_b="chk-sbp-high",
        timestamp_a=None,
        timestamp_b="2026-11-14T10:00:00Z",
        status="missing_in_a",
        delta=None,
    )
    recon = _make_recon_result("pat-d5-abnormal", [comp_abnormal])
    origins = {"chk-sbp-high": "self_reported"}
    verif = verify_reconciliation(recon, origins=origins)

    assert verif.summary["requires_review"] == 1
    assert verif.summary["severity_moderate"] == 1
    obs = verif.observation_verifications[0]
    assert obs.requires_human_review is True
    assert obs.severity == "moderate"
    assert "present side is low-trust" in obs.review_reason

    # Triage decision raises to review (Yellow)
    proto_state = TriageProtocolState(
        protocol="bp_severe",
        age_band="adult",
        result={"level": "routine", "reasons": [], "factors": []},
    )
    intake_state = InterviewState(patient_id="pat-d5-abnormal", conditions_on_file=["hypertension"], step=INTERVIEW_COMPLETE)
    dec = step_decide_triage(
        verif_result=verif,
        state=intake_state,
        protocol_state=proto_state,
        user_id="pat-d5-abnormal",
        get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
    )
    assert dec["final_triage_level"] == "review"
    assert dec["final_requires_review"] is True
    assert dec["review_status"] == "open"


# =============================================================================
# 3. Normal Reading That Conflicts With Record Still Requires Review
# =============================================================================
def test_d5_normal_reading_conflicting_with_record_requires_review():
    """
    If a self-reported reading is physically normal (e.g. 130 mmHg) but conflicts
    with a different record reading (e.g. 110 mmHg, delta 20 > threshold 10),
    Rule 2 (conflict) fires and requires review.
    """
    comp_conflict = ObservationComparison(
        observation_type="blood_pressure_systolic",
        value_a=110.0,
        value_b=130.0,
        unit_a="mmHg",
        unit_b="mmHg",
        source_a="fhir",
        source_b="checkin",
        source_record_id_a="rec-sbp-1",
        source_record_id_b="chk-sbp-1",
        timestamp_a="2026-11-01T10:00:00Z",
        timestamp_b="2026-11-14T10:00:00Z",
        status="conflict",
        delta=20.0,
    )
    recon = _make_recon_result("pat-d5-conf", [comp_conflict])
    origins = {"rec-sbp-1": "clinician_entered", "chk-sbp-1": "self_reported"}
    verif = verify_reconciliation(recon, origins=origins)

    assert verif.summary["requires_review"] == 1
    obs = verif.observation_verifications[0]
    assert obs.reconciliation_status == "conflict"
    assert obs.requires_human_review is True
    assert obs.severity == "moderate"


# =============================================================================
# 4. Red Flags and Emergencies Remain Unchanged
# =============================================================================
def test_d5_red_flags_and_emergencies_unchanged():
    """
    Even if all vitals are normal and auto-resolved, an emergency red flag
    (e.g. chest pain) guarantees final_triage_level == 'emergency' (Red).
    """
    comp_normal = ObservationComparison(
        observation_type="glucose",
        value_a=None,
        value_b=110.0,
        unit_a=None,
        unit_b="mg/dL",
        source_a=None,
        source_b="checkin",
        source_record_id_a=None,
        source_record_id_b="chk-glu-normal",
        timestamp_a=None,
        timestamp_b="2026-11-14T10:00:00Z",
        status="missing_in_a",
        delta=None,
    )
    recon = _make_recon_result("pat-d5-emg", [comp_normal])
    verif = verify_reconciliation(recon, origins={"chk-glu-normal": "self_reported"})
    assert verif.summary["requires_review"] == 0

    proto_state = TriageProtocolState(
        protocol="bp_severe",
        age_band="adult",
        result={"level": "emergency", "reasons": ["chest_pain"], "factors": []},
    )
    intake_state = InterviewState(patient_id="pat-d5-emg", conditions_on_file=["diabetes"], step=INTERVIEW_COMPLETE)
    dec = step_decide_triage(
        verif_result=verif,
        state=intake_state,
        protocol_state=proto_state,
        user_id="pat-d5-emg",
        get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
    )
    assert dec["final_triage_level"] == "emergency"
    assert dec["final_requires_review"] is True


# =============================================================================
# 5. Connected vs Isolated Mode Equivalence
# =============================================================================
def test_d5_connected_and_isolated_mode_equivalence():
    """
    Verify that in both connected and isolated modes, normal self-reported vitals
    without hospital records auto-resolve and produce routine triage.
    """
    patient = NormalizedPatient(patient_id="p-mode", name="Mode Patient", date_of_birth="1980-01-01")
    checkin_bundle = {
        "patient": patient,
        "observations": [
            NormalizedObservation(patient_id="p-mode", observation_type="blood_pressure_systolic", value=125.0, unit="mmHg", timestamp="2026-11-14T10:00:00Z", source="local", source_record_id="c-1"),
            NormalizedObservation(patient_id="p-mode", observation_type="blood_pressure_diastolic", value=82.0, unit="mmHg", timestamp="2026-11-14T10:00:00Z", source="local", source_record_id="c-2"),
        ],
        "medications": [],
    }

    # Empty hospital record (no prior readings)
    empty_record_bundle = {"patient": patient, "observations": [], "medications": []}

    for mode in ("isolated", "connected"):
        recon = step_reconcile(empty_record_bundle, checkin_bundle)
        verif = step_verify(recon, checkin_bundle, None, mode=mode, record_patient_id="p-mode")
        assert verif.summary["requires_review"] == 0, f"Mode {mode} failed: expected 0 requires_review"
        assert verif.summary["auto_resolved"] == 2


# =============================================================================
# 6. Direct vs Graph Orchestrator Equivalence
# =============================================================================
def test_d5_orchestrator_direct_and_graph_equivalence():
    """
    Direct and graph orchestrator pipelines produce identical routine decisions
    on normal self-reported vitals with no prior hospital record.
    """
    from orchestrator.graph import node_verify, node_decide_triage

    patient = NormalizedPatient(patient_id="pat-d5-orch", name="Test D5 Patient", date_of_birth="1975-06-15")
    checkin_bundle = {
        "patient": patient,
        "observations": [
            NormalizedObservation(patient_id="pat-d5-orch", observation_type="blood_pressure_systolic", value=122.0, unit="mmHg", timestamp="2026-11-14T10:00:00Z", source="local", source_record_id="c-1"),
            NormalizedObservation(patient_id="pat-d5-orch", observation_type="blood_pressure_diastolic", value=78.0, unit="mmHg", timestamp="2026-11-14T10:00:00Z", source="local", source_record_id="c-2"),
        ],
        "medications": [],
    }
    empty_record_bundle = {"patient": patient, "observations": [], "medications": []}

    recon = step_reconcile(empty_record_bundle, checkin_bundle)

    # 1. Direct step verify & decide
    verif_direct = step_verify(recon, checkin_bundle, None, mode="isolated", record_patient_id="pat-d5-orch")
    intake_state = InterviewState(patient_id="pat-d5-orch", conditions_on_file=["hypertension"], step=INTERVIEW_COMPLETE)
    dec_direct = step_decide_triage(
        verif_result=verif_direct,
        state=intake_state,
        protocol_state=None,
        user_id="user-d5-orch",
        get_patient_profile_fn=lambda uid: {"conditions": ["hypertension"], "date_of_birth": "1975-06-15"},
    )

    # 2. Graph node verify & decide
    graph_state = {
        "checkin": {
            "checkin_id": "chk-d5-orch",
            "user_id": "user-d5-orch",
            "patient_id": "pat-d5-orch",
            "record_patient_id": "pat-d5-orch",
            "mode": "isolated",
        },
        "mode": "isolated",
        "recon_result": recon,
        "bundles": {
            "checkin_bundle": checkin_bundle,
            "prior_bundle": empty_record_bundle,
        },
        "checkin_bundle": checkin_bundle,
        "parsed_context": {
            "med_state": None,
            "state": intake_state,
            "protocol_state": None,
        },
        "user": {
            "user_id": "user-d5-orch",
            "patient_profile": {"conditions": ["hypertension"], "date_of_birth": "1975-06-15"},
        },
    }

    verif_node_out = node_verify(graph_state)
    graph_state.update(verif_node_out)
    dec_node_out = node_decide_triage(graph_state)

    # Assert 0 requires review and routine level across both
    assert verif_direct.summary["requires_review"] == 0
    assert dec_direct["final_triage_level"] == "routine"
    assert dec_direct["final_requires_review"] is False

    assert graph_state["verif_result"].summary["requires_review"] == 0
    assert dec_node_out["triage_decision"]["final_triage_level"] == "routine"
    assert dec_node_out["triage_decision"]["final_requires_review"] is False

    assert dec_direct["final_triage_level"] == dec_node_out["triage_decision"]["final_triage_level"]
    assert dec_direct["final_requires_review"] == dec_node_out["triage_decision"]["final_requires_review"]
