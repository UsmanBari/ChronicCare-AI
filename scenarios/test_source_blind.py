"""
Source-Blind Acceptance Test Script (Milestone 2)

Proves structural and type equivalence between Connected Mode (FHIR) and Isolated Mode (Local Store).
Imports and calls ONLY get_patient_bundle() from data_sources.data_source.

Implements summarize_bundle() with ZERO source or mode awareness.
"""

import os
import sys
import json
from typing import Dict, Any

# Ensure local imports work regardless of execution directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CRITICAL CONSTRAINT: Import ONLY get_patient_bundle from data_source
from data_sources.data_source import get_patient_bundle
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication

def summarize_bundle(bundle: Dict[str, Any]) -> str:
    """
    Source-Blind Summary Function.
    Operates PURELY on normalized bundle models (patient, observations, medications).
    Contains ZERO source or mode conditional checks.
    """
    patient: NormalizedPatient = bundle["patient"]
    observations = bundle["observations"]
    medications = bundle["medications"]

    lines = []
    lines.append(f"=== PATIENT SUMMARY ===")
    lines.append(f"ID: {patient.patient_id}")
    lines.append(f"Name: {patient.name}")
    lines.append(f"DOB: {patient.date_of_birth or 'N/A'}")

    lines.append(f"\n--- OBSERVATIONS ({len(observations)} total) ---")
    # Group observations by normalized type
    by_type = {}
    for obs in observations:
        by_type.setdefault(obs.observation_type, []).append(obs)

    for obs_type, obs_list in sorted(by_type.items()):
        display_obs = obs_list[0]  # Take sample for demonstration output
        lines.append(f"  • {obs_type.upper()}: {display_obs.value} {display_obs.unit} (Timestamp: {display_obs.timestamp}, SourceTag: {display_obs.source})")

    lines.append(f"\n--- MEDICATIONS ({len(medications)} total) ---")
    for med in medications[:5]:  # Display top 5
        lines.append(f"  • {med.medication_name} [{med.status}] - Dosage: {med.dosage} (SourceTag: {med.source})")

    return "\n".join(lines)

def run_source_blind_test():
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Obtain FHIR patient ID from environment or fallback
    env_file = os.path.join(script_dir, ".env")
    fhir_patient_id = "768be7ac-743f-4c24-aa0f-fed5a3a38b6a"  # Fallback to selected M1 patient ID
    if os.path.isfile(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("FHIR_PATIENT_ID="):
                    val = line.strip().split("=", 1)[1]
                    if val and val != "<selected_synthetic_patient_id>":
                        fhir_patient_id = val

    local_patient_id = "LOCAL-PATIENT-001"
    db_path = os.path.join(script_dir, "local_store.db")

    print("==================================================")
    print("M2 SOURCE-BLIND ABSTRACTION TEST")
    print("==================================================\n")

    print(f"1. Querying FHIR Connected Mode (Patient ID: {fhir_patient_id})...")
    connected_bundle = get_patient_bundle(fhir_patient_id, mode="connected")

    print(f"2. Querying Local Store Isolated Mode (Patient ID: {local_patient_id})...")
    isolated_bundle = get_patient_bundle(local_patient_id, mode="isolated", db_path=db_path)

    print("\n--------------------------------------------------")
    print("STRUCTURAL & TYPE EQUIVALENCE VERIFICATION")
    print("--------------------------------------------------")

    EXPECTED_PATIENT_FIELDS = {"patient_id", "name", "date_of_birth"}
    EXPECTED_OBSERVATION_FIELDS = {"patient_id", "observation_type", "value", "unit", "timestamp", "source", "source_record_id"}
    EXPECTED_MEDICATION_FIELDS = {"patient_id", "medication_name", "status", "dosage", "timestamp", "source", "source_record_id"}

    # Assert model types for Connected Bundle
    assert isinstance(connected_bundle["patient"], NormalizedPatient), "Connected patient is not NormalizedPatient"
    assert all(isinstance(o, NormalizedObservation) for o in connected_bundle["observations"]), "Connected observations are not NormalizedObservation"
    assert all(isinstance(m, NormalizedMedication) for m in connected_bundle["medications"]), "Connected medications are not NormalizedMedication"
    print("[PASS] Connected Bundle conforms strictly to Normalized Data Models.")

    # Assert model types for Isolated Bundle
    assert isinstance(isolated_bundle["patient"], NormalizedPatient), "Isolated patient is not NormalizedPatient"
    assert all(isinstance(o, NormalizedObservation) for o in isolated_bundle["observations"]), "Isolated observations are not NormalizedObservation"
    assert all(isinstance(m, NormalizedMedication) for m in isolated_bundle["medications"]), "Isolated medications are not NormalizedMedication"
    print("[PASS] Isolated Bundle conforms strictly to Normalized Data Models.")

    # Assert EVERY record in both bundles matches the exact schema field definitions
    assert set(connected_bundle["patient"].to_dict().keys()) == EXPECTED_PATIENT_FIELDS
    assert set(isolated_bundle["patient"].to_dict().keys()) == EXPECTED_PATIENT_FIELDS
    print(f"[PASS] All patient records conform strictly to expected fields: {sorted(list(EXPECTED_PATIENT_FIELDS))}")

    for obs in connected_bundle["observations"] + isolated_bundle["observations"]:
        assert set(obs.to_dict().keys()) == EXPECTED_OBSERVATION_FIELDS, f"Observation record {obs} mismatch"
    print(f"[PASS] All {len(connected_bundle['observations']) + len(isolated_bundle['observations'])} observation records conform strictly to expected fields: {sorted(list(EXPECTED_OBSERVATION_FIELDS))}")

    for med in connected_bundle["medications"] + isolated_bundle["medications"]:
        assert set(med.to_dict().keys()) == EXPECTED_MEDICATION_FIELDS, f"Medication record {med} mismatch"
    print(f"[PASS] All {len(connected_bundle['medications']) + len(isolated_bundle['medications'])} medication records conform strictly to expected fields: {sorted(list(EXPECTED_MEDICATION_FIELDS))}")

    print("\n--------------------------------------------------")
    print("EXECUTING SOURCE-BLIND SUMMARIZE_BUNDLE()")
    print("--------------------------------------------------")

    print("\n[CONNECTED MODE BUNDLE SUMMARY]")
    print(summarize_bundle(connected_bundle))

    print("\n[ISOLATED MODE BUNDLE SUMMARY]")
    print(summarize_bundle(isolated_bundle))

    print("\n--------------------------------------------------")
    print("SIDE-BY-SIDE NORMALIZED SCHEMA COMPARISON")
    print("--------------------------------------------------")
    
    sample_obs_conn = connected_bundle["observations"][0].to_dict()
    sample_obs_iso = isolated_bundle["observations"][0].to_dict()

    print(f"{'FIELD':<22} | {'CONNECTED MODE (FHIR)':<35} | {'ISOLATED MODE (LOCAL)':<35}")
    print("-" * 98)
    for k in sorted(sample_obs_conn.keys()):
        val_c = str(sample_obs_conn[k])[:33]
        val_i = str(sample_obs_iso[k])[:33]
        print(f"{k:<22} | {val_c:<35} | {val_i:<35}")

    print("\n==================================================")
    print("SOURCE-BLIND ABSTRACTION TEST PASSED SUCCESSFULLY!")
    print("==================================================")
    return True

if __name__ == "__main__":
    run_source_blind_test()
