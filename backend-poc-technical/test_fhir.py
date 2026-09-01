"""
FHIR Connectivity Test Script for SMART Health IT Open R4 Endpoint.

Verifies server reachability, searches for a suitable Synthea synthetic patient
with Patient, Observation, and MedicationRequest resources, and outputs raw FHIR JSON
evidence to output/fhir_connectivity.json.
"""

import os
import sys
import json
from typing import Dict, Any, Optional

# Ensure local imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_sources.fhir_client import (
    check_fhir_metadata,
    search_fhir_patients,
    get_fhir_patient,
    get_fhir_observations,
    get_fhir_medications,
    DEFAULT_FHIR_BASE_URL
)

def find_synthetic_patient(base_url: str = DEFAULT_FHIR_BASE_URL) -> Optional[str]:
    """
    Searches recent patients to find one with Observation (including glucose, HbA1c, BP, weight)
    and MedicationRequest resources.
    Returns patient ID string if found.
    """
    print(f"Searching for optimal Synthea patient on {base_url}...")
    patients = search_fhir_patients(count=50, base_url=base_url)
    print(f"Retrieved {len(patients)} candidate patients.")
    
    # First pass: look for patient with Glucose / HbA1c, BP, Weight, and Meds
    for patient in patients:
        p_id = patient.get("id")
        if not p_id:
            continue
        try:
            obs = get_fhir_observations(p_id, base_url=base_url)
            meds = get_fhir_medications(p_id, base_url=base_url)
            if len(obs) > 0 and len(meds) > 0:
                obs_types = [o.get("code", {}).get("text") or o.get("code", {}).get("coding", [{}])[0].get("display", "") for o in obs]
                has_glucose = any("Glucose" in t or "glucose" in t.lower() or "HbA1c" in t or "A1c" in t for t in obs_types)
                has_weight = any("Weight" in t or "weight" in t.lower() for t in obs_types)
                has_bp = any("Blood Pressure" in t or "pressure" in t.lower() for t in obs_types)
                
                if has_glucose and has_weight and has_bp:
                    print(f"Selected Optimal Patient ID: {p_id} (Observations: {len(obs)}, MedicationRequests: {len(meds)})")
                    return p_id
        except Exception as e:
            continue

    # Fallback pass: any patient with obs and meds
    for patient in patients:
        p_id = patient.get("id")
        if not p_id:
            continue
        try:
            obs = get_fhir_observations(p_id, base_url=base_url)
            meds = get_fhir_medications(p_id, base_url=base_url)
            if len(obs) > 0 and len(meds) > 0:
                print(f"Selected Fallback Patient ID: {p_id}")
                return p_id
        except Exception:
            continue
            
    return None

def test_connectivity_and_save_evidence(patient_id: Optional[str] = None, base_url: str = DEFAULT_FHIR_BASE_URL):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    evidence_file = os.path.join(output_dir, "fhir_connectivity.json")
    env_file = os.path.join(script_dir, ".env")

    print("Step 1: Checking FHIR metadata endpoint...")
    metadata = check_fhir_metadata(base_url=base_url)
    fhir_version = metadata.get("fhirVersion", "Unknown")
    software_name = metadata.get("software", {}).get("name", "Unknown")
    print(f"Server is REACHABLE! Software: {software_name}, FHIR Version: {fhir_version}")

    if not patient_id:
        patient_id = find_synthetic_patient(base_url=base_url)
        
    if not patient_id:
        raise RuntimeError("Failed to identify a valid synthetic patient ID on FHIR server.")

    print(f"\nStep 2: Retrieving Patient resource for ID: {patient_id}...")
    patient_data = get_fhir_patient(patient_id, base_url=base_url)
    patient_name_info = patient_data.get("name", [{}])[0]
    given_name = " ".join(patient_name_info.get("given", []))
    family_name = patient_name_info.get("family", "")
    full_name = f"{given_name} {family_name}".strip()
    print(f"Patient Name: {full_name}, DOB: {patient_data.get('birthDate')}")

    print(f"\nStep 3: Retrieving Observations for patient: {patient_id}...")
    observations_data = get_fhir_observations(patient_id, base_url=base_url)
    print(f"Retrieved {len(observations_data)} Observation resources.")
    for idx, obs in enumerate(observations_data[:5]):
        code_text = obs.get("code", {}).get("text") or obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
        value_quantity = obs.get("valueQuantity", {})
        val_str = f"{value_quantity.get('value')} {value_quantity.get('unit')}" if value_quantity else "N/A"
        print(f"  [{idx+1}] {code_text} = {val_str}")

    print(f"\nStep 4: Retrieving MedicationRequests for patient: {patient_id}...")
    medications_data = get_fhir_medications(patient_id, base_url=base_url)
    print(f"Retrieved {len(medications_data)} MedicationRequest resources.")
    for idx, med in enumerate(medications_data[:5]):
        med_concept = med.get("medicationCodeableConcept", {})
        med_name = med_concept.get("text") or med_concept.get("coding", [{}])[0].get("display", "Unknown")
        status = med.get("status", "unknown")
        print(f"  [{idx+1}] {med_name} (Status: {status})")

    evidence = {
        "fhir_base_url": base_url,
        "selected_patient_id": patient_id,
        "server_metadata_summary": {
            "resourceType": metadata.get("resourceType"),
            "fhirVersion": fhir_version,
            "software": software_name
        },
        "patient": patient_data,
        "observations_count": len(observations_data),
        "observations": observations_data,
        "medication_requests_count": len(medications_data),
        "medication_requests": medications_data
    }

    with open(evidence_file, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)
        
    print(f"\nSaved raw FHIR JSON evidence to: {evidence_file}")

    # Write .env file
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"FHIR_BASE_URL={base_url}\n")
        f.write(f"FHIR_PATIENT_ID={patient_id}\n")
        f.write("LOCAL_DB_PATH=local_store.db\n")
    print(f"Updated environment configuration in: {env_file}")

    return patient_id

if __name__ == "__main__":
    test_connectivity_and_save_evidence()
