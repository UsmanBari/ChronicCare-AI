"""
Reconciliation Agent Acceptance Test Script (Milestone 3)

Tests reconcile_bundles() against synthetic paired test fixtures:
- Clean/Agree Pair (Positive test & Negative control)
- Conflict Pair (Value deltas > thresholds & med status mismatch)
- Missing Data Pair (Records present in one source, missing in other)
- Insufficient Data Pair (Matched observation with None value)
- Negative Control Pair (100% exact agreement, zero conflicts/insufficient_data)
- Patient Identity Contract Error Handling (Asserts ValueError on mismatched patient_id)

Asserts full provenance preservation (source_a, source_b, source_record_id_a, source_record_id_b).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.reconciliation_agent import reconcile_bundles
from scenarios.fixtures import (
    CLEAN_AGREE_PAIR,
    CONFLICT_PAIR,
    MISSING_DATA_PAIR,
    INSUFFICIENT_DATA_PAIR,
    NEGATIVE_CONTROL_PAIR,
    ALL_FIXTURE_PAIRS
)
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication

def print_result_summary(fixture_name: str, result):
    print(f"\n==================================================")
    print(f"FIXTURE: {fixture_name} (Patient ID: {result.patient_id})")
    print(f"==================================================")
    print(f"Summary Counts: {result.summary}")
    
    print("\n--- Observation Comparisons ---")
    for o in result.observation_comparisons:
        print(f"  • [{o.status.upper():<17}] {o.observation_type:<25} | A: {o.value_a} {o.unit_a or ''} ({o.source_a}:{o.source_record_id_a}) vs B: {o.value_b} {o.unit_b or ''} ({o.source_b}:{o.source_record_id_b}) | Delta: {o.delta}")

    print("\n--- Medication Comparisons ---")
    for m in result.medication_comparisons:
        print(f"  • [{m.comparison_status.upper():<17}] {m.medication_name:<25} | A: status={m.status_a}, dosage='{m.dosage_a}' ({m.source_a}:{m.source_record_id_a}) vs B: status={m.status_b}, dosage='{m.dosage_b}' ({m.source_b}:{m.source_record_id_b})")

def run_reconciliation_tests():
    print("==================================================")
    print("CHRONICCARE AI POC - MILESTONE 3 RECONCILIATION TESTS")
    print("==================================================")

    # 1. Test Patient Identity Contract Error Case
    print("\nTest 1: Patient Identity Contract Validation (Error Case)...")
    mismatched_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-100", name="Alice"),
        "observations": [],
        "medications": []
    }
    mismatched_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-200", name="Bob"),
        "observations": [],
        "medications": []
    }
    
    error_caught = False
    try:
        reconcile_bundles(mismatched_bundle_a, mismatched_bundle_b)
    except ValueError as e:
        error_caught = True
        print(f"[PASS] Successfully caught Patient Identity Contract error: {e}")
        
    assert error_caught, "Failed to raise ValueError on mismatched patient IDs!"

    # 2. Test Fixture Pairs
    for fixture in ALL_FIXTURE_PAIRS:
        name = fixture["name"]
        res = reconcile_bundles(fixture["bundle_a"], fixture["bundle_b"])
        print_result_summary(name, res)

    # Specific Assertions per Fixture with Exact Provenance Checks
    # Clean Agree Pair
    res_clean = reconcile_bundles(CLEAN_AGREE_PAIR["bundle_a"], CLEAN_AGREE_PAIR["bundle_b"])
    assert res_clean.summary["conflicts"] == 0, "Clean agree pair should have 0 conflicts"
    assert res_clean.summary["agreements"] == 5, f"Expected 5 agreements in clean pair, got {res_clean.summary['agreements']}"
    assert all(o.status == "agree" for o in res_clean.observation_comparisons)
    # Exact Provenance check for Clean Agree Glucose
    glucose_clean = [o for o in res_clean.observation_comparisons if o.observation_type == "glucose"][0]
    assert glucose_clean.source_record_id_a == "FHIR-OBS-01", f"Expected FHIR-OBS-01, got {glucose_clean.source_record_id_a}"
    assert glucose_clean.source_record_id_b == "FHIR-OBS-01-CHECKIN", f"Expected FHIR-OBS-01-CHECKIN, got {glucose_clean.source_record_id_b}"
    assert glucose_clean.source_a == "fhir" and glucose_clean.source_b == "fhir"

    # Conflict Pair
    res_conflict = reconcile_bundles(CONFLICT_PAIR["bundle_a"], CONFLICT_PAIR["bundle_b"])
    assert res_conflict.summary["conflicts"] == 3, f"Expected 3 conflicts in conflict pair, got {res_conflict.summary['conflicts']}"
    obs_conflicts = [o for o in res_conflict.observation_comparisons if o.status == "conflict"]
    med_conflicts = [m for m in res_conflict.medication_comparisons if m.comparison_status == "conflict"]
    assert len(obs_conflicts) == 2, "Expected 2 observation conflicts (glucose, hba1c)"
    assert len(med_conflicts) == 1, "Expected 1 medication conflict (Lisinopril status)"
    # Exact Provenance check for Conflict Glucose
    glucose_conflict = [o for o in res_conflict.observation_comparisons if o.observation_type == "glucose"][0]
    assert glucose_conflict.source_record_id_a == "LOC-OBS-21" and glucose_conflict.source_record_id_b == "LOC-OBS-21-CHECKIN"

    # Missing Data Pair
    res_missing = reconcile_bundles(MISSING_DATA_PAIR["bundle_a"], MISSING_DATA_PAIR["bundle_b"])
    assert res_missing.summary["missing_in_a"] == 1, "Expected 1 missing_in_a (hba1c)"
    assert res_missing.summary["missing_in_b"] == 2, "Expected 2 missing_in_b (weight, Atorvastatin)"
    weight_missing = [o for o in res_missing.observation_comparisons if o.observation_type == "weight"][0]
    assert weight_missing.source_record_id_a == "FHIR-OBS-32" and weight_missing.source_record_id_b is None

    # Insufficient Data Pair
    res_insuff = reconcile_bundles(INSUFFICIENT_DATA_PAIR["bundle_a"], INSUFFICIENT_DATA_PAIR["bundle_b"])
    assert res_insuff.summary["insufficient_data"] == 1, "Expected 1 insufficient_data"
    assert res_insuff.observation_comparisons[0].status == "insufficient_data"

    # Negative Control Pair
    res_neg = reconcile_bundles(NEGATIVE_CONTROL_PAIR["bundle_a"], NEGATIVE_CONTROL_PAIR["bundle_b"])
    assert res_neg.summary["conflicts"] == 0, "Negative control must have 0 conflicts"
    assert res_neg.summary["insufficient_data"] == 0, "Negative control must have 0 insufficient_data"
    assert res_neg.summary["agreements"] == 3, "Negative control should have 3 agreements"

    # 3. Edge-Case Verification Tests
    print("\n--------------------------------------------------")
    print("EDGE-CASE & BOUNDARY TEST SUITE")
    print("--------------------------------------------------")

    # Edge Case A: Boundary Threshold Test (delta == threshold -> agree; delta > threshold -> conflict)
    print("Running Boundary Threshold Test...")
    boundary_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-BOUND", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-BOUND", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-B1"),
            NormalizedObservation(patient_id="PATIENT-BOUND", observation_type="weight", value=70.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-B2"),
        ],
        "medications": []
    }
    boundary_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-BOUND", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-BOUND", observation_type="glucose", value=125.0, unit="mg/dL", timestamp="2026-08-15T10:30:00Z", source="fhir", source_record_id="OBS-B3"), # delta 15.0 == threshold 15.0 -> agree
            NormalizedObservation(patient_id="PATIENT-BOUND", observation_type="weight", value=72.1, unit="kg", timestamp="2026-08-15T10:30:00Z", source="fhir", source_record_id="OBS-B4"), # delta 2.1 > threshold 2.0 -> conflict
        ],
        "medications": []
    }
    res_bound = reconcile_bundles(boundary_bundle_a, boundary_bundle_b)
    glucose_b = [o for o in res_bound.observation_comparisons if o.observation_type == "glucose"][0]
    weight_b = [o for o in res_bound.observation_comparisons if o.observation_type == "weight"][0]
    assert glucose_b.status == "agree", f"Expected delta=15.0 to AGREE, got {glucose_b.status}"
    assert weight_b.status == "conflict", f"Expected delta=2.1 to CONFLICT, got {weight_b.status}"
    print("[PASS] Boundary threshold test passed (delta == threshold -> agree; delta > threshold -> conflict).")

    # Edge Case B: Timestamp Outside 48-Hour Matching Window
    print("Running Timestamp Outside 48-Hour Window Test...")
    window_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-WIN", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-WIN", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-01T10:00:00Z", source="fhir", source_record_id="OBS-W1")
        ],
        "medications": []
    }
    window_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-WIN", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-WIN", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-05T10:00:00Z", source="fhir", source_record_id="OBS-W2") # 96 hours diff > 48h
        ],
        "medications": []
    }
    res_win = reconcile_bundles(window_bundle_a, window_bundle_b)
    assert res_win.summary["missing_in_a"] == 1 and res_win.summary["missing_in_b"] == 1
    print("[PASS] 48-Hour matching window test passed (diff > 48h classified as unmatched missing_in_a/missing_in_b).")

    # Edge Case C: 1-to-1 Nearest Neighbor Matching (No Source Reuse)
    print("Running 1-to-1 Nearest-Neighbor Matching Test...")
    nn_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-NN", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-NN", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-NN-A1"),
            NormalizedObservation(patient_id="PATIENT-NN", observation_type="glucose", value=130.0, unit="mg/dL", timestamp="2026-08-15T20:00:00Z", source="fhir", source_record_id="OBS-NN-A2"),
        ],
        "medications": []
    }
    nn_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-NN", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-NN", observation_type="glucose", value=122.0, unit="mg/dL", timestamp="2026-08-15T10:15:00Z", source="fhir", source_record_id="OBS-NN-B1"),
            NormalizedObservation(patient_id="PATIENT-NN", observation_type="glucose", value=131.0, unit="mg/dL", timestamp="2026-08-15T20:15:00Z", source="fhir", source_record_id="OBS-NN-B2"),
        ],
        "medications": []
    }
    res_nn = reconcile_bundles(nn_bundle_a, nn_bundle_b)
    assert len(res_nn.observation_comparisons) == 2, f"Expected 2 matched comparisons, got {len(res_nn.observation_comparisons)}"
    matched_ids_b = {o.source_record_id_b for o in res_nn.observation_comparisons}
    assert matched_ids_b == {"OBS-NN-B1", "OBS-NN-B2"}, f"Expected 1-to-1 match without reuse, got {matched_ids_b}"
    print("[PASS] 1-to-1 nearest-neighbor matching test passed (each observation matched once without reuse).")

    # Edge Case D: Incompatible Units Test
    print("Running Incompatible Units Test...")
    unit_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-UNIT", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-UNIT", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-U1")
        ],
        "medications": []
    }
    unit_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-UNIT", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-UNIT", observation_type="glucose", value=6.1, unit="mmol/L", timestamp="2026-08-15T10:15:00Z", source="fhir", source_record_id="OBS-U2")
        ],
        "medications": []
    }
    res_unit = reconcile_bundles(unit_bundle_a, unit_bundle_b)
    assert res_unit.observation_comparisons[0].status == "insufficient_data", f"Incompatible units must produce insufficient_data, got {res_unit.observation_comparisons[0].status}"
    print("[PASS] Incompatible units test passed (mg/dL vs mmol/L classified as insufficient_data).")

    # Edge Case E: Unknown Observation Type Test
    print("Running Unknown Observation Type Test...")
    unk_bundle_a = {
        "patient": NormalizedPatient(patient_id="PATIENT-UNK", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-UNK", observation_type="body_temperature", value=37.0, unit="Cel", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="OBS-UNK1")
        ],
        "medications": []
    }
    unk_bundle_b = {
        "patient": NormalizedPatient(patient_id="PATIENT-UNK", name="Test"),
        "observations": [
            NormalizedObservation(patient_id="PATIENT-UNK", observation_type="body_temperature", value=37.2, unit="Cel", timestamp="2026-08-15T10:15:00Z", source="fhir", source_record_id="OBS-UNK2")
        ],
        "medications": []
    }
    res_unk = reconcile_bundles(unk_bundle_a, unk_bundle_b)
    assert res_unk.observation_comparisons[0].status == "insufficient_data", f"Unknown type should be classified as insufficient_data, got {res_unk.observation_comparisons[0].status}"
    print("[PASS] Unknown observation type test passed (unsupported type classified as insufficient_data).")

    print("\n==================================================")
    print("ALL RECONCILIATION FIXTURE AND EDGE-CASE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")
    return True

if __name__ == "__main__":
    run_reconciliation_tests()
