"""
Unified Data Source Interface (Milestone 2)

Serves as the single entry point for accessing normalized patient data.
Routes requests to Connected Mode (FHIR Adapter) or Isolated Mode (Local Store Adapter).
Performs NO clinical interpretation, risk scoring, reconciliation, or trust assignment.
"""

from typing import Dict, Any, Optional
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication
from data_sources import fhir_adapter
from data_sources import local_adapter

def get_patient_bundle(
    patient_id: str,
    mode: str,
    base_url: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves a unified patient bundle containing normalized patient, observations,
    and medication records.

    Parameters:
    - patient_id: ID of the patient in the target source.
    - mode: "connected" (routes to FHIR) or "isolated" (routes to Local SQLite store).
    - base_url: Optional custom base URL for FHIR server (connected mode).
    - db_path: Optional custom database path for SQLite store (isolated mode).

    Returns:
    - Dict containing:
        "patient": NormalizedPatient
        "observations": List[NormalizedObservation]
        "medications": List[NormalizedMedication]
        "mode": str
    """
    clean_mode = mode.lower().strip()
    
    if clean_mode == "connected":
        patient = fhir_adapter.get_normalized_patient(patient_id, base_url=base_url)
        observations = fhir_adapter.get_normalized_observations(patient_id, base_url=base_url)
        medications = fhir_adapter.get_normalized_medications(patient_id, base_url=base_url)
    elif clean_mode == "isolated":
        patient = local_adapter.get_normalized_patient(patient_id, db_path=db_path)
        observations = local_adapter.get_normalized_observations(patient_id, db_path=db_path)
        medications = local_adapter.get_normalized_medications(patient_id, db_path=db_path)
    else:
        raise ValueError(f"Unrecognized data source mode '{mode}'. Must be 'connected' or 'isolated'.")

    return {
        "patient": patient,
        "observations": observations,
        "medications": medications
    }
