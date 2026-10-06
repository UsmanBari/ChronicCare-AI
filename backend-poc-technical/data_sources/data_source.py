"""
Unified Data Source Interface.

Serves as the single entry point for accessing normalized patient data.
Routes requests to Connected Mode (FHIR Adapter) or Isolated Mode (Local Store Adapter).
Fetches resources in parallel with ThreadPoolExecutor(max_workers=3) for Connected Mode.
"""

from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
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
    """
    clean_mode = mode.lower().strip()
    
    if clean_mode == "connected":
        with ThreadPoolExecutor(max_workers=3) as executor:
            fut_p = executor.submit(fhir_adapter.get_normalized_patient, patient_id, base_url=base_url)
            fut_o = executor.submit(fhir_adapter.get_normalized_observations, patient_id, base_url=base_url)
            fut_m = executor.submit(fhir_adapter.get_normalized_medications, patient_id, base_url=base_url)
            patient = fut_p.result()
            observations = fut_o.result()
            medications = fut_m.result()
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
