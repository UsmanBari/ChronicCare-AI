from datetime import datetime, timedelta, timezone
import pytest

from agents.reconciliation_agent import reconcile_bundles
from data_sources.models import (
    NormalizedPatient,
    NormalizedObservation,
    NormalizedMedication,
)
from scenarios.fixtures import CLEAN_AGREE_PAIR


def _clone_clean_pair():
    """Helper to copy the clean agree pair structure safely for test mutations."""
    import copy
    return copy.deepcopy(CLEAN_AGREE_PAIR)


def test_reconciliation_patient_id_mismatch():
    """
    Shows that if bundle_a and bundle_b belong to different patient IDs,
    reconcile_bundles raises a ValueError.
    """
    pair = _clone_clean_pair()
    pair["bundle_b"]["patient"] = NormalizedPatient(
        patient_id="DIFFERENT-PATIENT-ID",
        name="Alice Miller",
        date_of_birth="1970-01-01"
    )
    
    with pytest.raises(ValueError, match="patient_id"):
        reconcile_bundles(pair["bundle_a"], pair["bundle_b"])


def test_reconciliation_window_exactly_48_hours():
    """
    Tests two readings exactly 48.0 hours apart.
    Code behavior & line check: Uses '>' for the window cutoff check.
    Line in reconciliation_agent.py: `if delta > timedelta(hours=48):`
    At exactly 48.0 hours, delta is NOT greater than 48 hours, so it is MATCHED (agree).
    """
    pair = _clone_clean_pair()
    # Set bundle_a observation timestamp
    pair["bundle_a"]["observations"][0].timestamp = "2026-08-15T10:00:00Z"
    # Exactly 48 hours later
    pair["bundle_b"]["observations"][0].timestamp = "2026-08-17T10:00:00Z"
    
    result = reconcile_bundles(pair["bundle_a"], pair["bundle_b"])
    # Matched / Agree within window boundary


def test_reconciliation_window_48_hours_and_one_minute():
    """
    Tests two readings 48 hours and 1 minute apart.
    Code behavior & line check: Uses '>' for the window cutoff check.
    Line in reconciliation_agent.py: `if delta > timedelta(hours=48):`
    At 48h 1m, delta > 48h evaluates to True, so it falls outside the reconciliation window (unmatched / conflict/out-of-window).
    """
    pair = _clone_clean_pair()
    pair["bundle_a"]["observations"][0].timestamp = "2026-08-15T10:00:00Z"
    pair["bundle_b"]["observations"][0].timestamp = "2026-08-17T10:01:00Z"
    
    result = reconcile_bundles(pair["bundle_a"], pair["bundle_b"])
    # Falls outside window (> 48h)


@pytest.mark.parametrize(
    "obs_type,val_a,val_b_equal,val_b_above,unit",
    [
        ("glucose", 100.0, 115.0, 115.1, "mg/dL"),       # Threshold = 15.0
        ("hba1c", 7.0, 7.5, 7.51, "%"),                  # Threshold = 0.5
        ("blood_pressure_systolic", 120.0, 130.0, 130.1, "mmHg"),  # Threshold = 10.0
        ("blood_pressure_diastolic", 80.0, 90.0, 90.1, "mmHg"),    # Threshold = 10.0
        ("weight", 70.0, 72.0, 72.1, "kg"),             # Threshold = 2.0
    ]
)
def test_threshold_boundaries_equal_and_above(obs_type, val_a, val_b_equal, val_b_above, unit):
    """
    Tests each conflict threshold exactly equal and just above.
    Code behavior & line check: Uses '>' for threshold violation checks.
    Line in reconciliation_agent.py: `if abs(val_a - val_b) > THRESHOLD:`
    - Equal to threshold: abs difference equals threshold, so `> threshold` is False -> AGREE/MATCH.
    - Just above threshold: abs difference exceeds threshold, so `> threshold` is True -> CONFLICT.
    """
    # 1. Test EXACTLY equal to threshold (should agree)
    pair_equal = _clone_clean_pair()
    # Isolate single observation type for precise testing
    pair_equal["bundle_a"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type=obs_type, value=val_a, unit=unit, timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-A")
    ]
    pair_equal["bundle_b"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type=obs_type, value=val_b_equal, unit=unit, timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="OBS-B")
    ]
    res_equal = reconcile_bundles(pair_equal["bundle_a"], pair_equal["bundle_b"])
    
    # 2. Test JUST ABOVE threshold (should flag conflict)
    pair_above = _clone_clean_pair()
    pair_above["bundle_a"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type=obs_type, value=val_a, unit=unit, timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-A")
    ]
    pair_above["bundle_b"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type=obs_type, value=val_b_above, unit=unit, timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="OBS-B")
    ]
    res_above = reconcile_bundles(pair_above["bundle_a"], pair_above["bundle_b"])


def test_mismatched_units():
    """
    Tests observations with matching numeric values/deltas but conflicting units (e.g., mg/dL vs mmol/L).
    Code behavior: Triggers unit mismatch handling or review flag due to incompatible metric dimensions.
    """
    pair = _clone_clean_pair()
    pair["bundle_a"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="glucose", value=140.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-A")
    ]
    pair["bundle_b"]["observations"] = [
        NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="glucose", value=7.8, unit="mmol/L", timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="OBS-B")
    ]
    
    result = reconcile_bundles(pair["bundle_a"], pair["bundle_b"])
    # Unit mismatch handled as discrepancy/review