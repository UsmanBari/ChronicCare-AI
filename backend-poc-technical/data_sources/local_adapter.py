"""
Local Store Adapter (Milestone 2)

Wraps SQLite local store functions and normalizes them into source-agnostic models
(NormalizedPatient, NormalizedObservation, NormalizedMedication).

=============================================================================
LOCAL STORE TO NORMALIZED MAPPING TABLE
=============================================================================
SQLite Field                        -> Normalized Field / Type
-----------------------------------------------------------------------------
patients:
  id                                -> patient_id
  name                              -> name
  date_of_birth                     -> date_of_birth

observations:
  type ("Glucose")                  -> observation_type: "glucose"
  type ("HbA1c")                    -> observation_type: "hba1c"
  type ("Blood Pressure (Systolic)")-> observation_type: "blood_pressure_systolic"
  type ("Blood Pressure (Diastolic)")-> observation_type: "blood_pressure_diastolic"
  type ("Weight")                   -> observation_type: "weight"
  value                             -> value (float)
  unit                              -> unit
  timestamp                         -> timestamp
  id                                -> source_record_id
  Constant                          -> source: "local"

medications:
  medication_name                   -> medication_name
  status                            -> status
  dosage                            -> dosage
  timestamp                         -> timestamp
  id                                -> source_record_id
  Constant                          -> source: "local"
=============================================================================
Note: Assumes standard units (mg/dL, %, mmHg, kg) across sources.
"""

from typing import List, Optional
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication
from data_sources.local_store import (
    get_local_patient,
    get_local_observations,
    get_local_medications
)

LOCAL_TYPE_MAP = {
    "glucose": "glucose",
    "hba1c": "hba1c",
    "blood pressure (systolic)": "blood_pressure_systolic",
    "blood pressure (diastolic)": "blood_pressure_diastolic",
    "weight": "weight",
}

def _canonicalize_local_type(raw_type: str) -> str:
    clean = raw_type.strip().lower()
    return LOCAL_TYPE_MAP.get(clean, clean.replace(" ", "_"))

def get_normalized_patient(patient_id: str, db_path: Optional[str] = None) -> NormalizedPatient:
    """
    Retrieves local SQLite patient record and transforms into NormalizedPatient.
    """
    raw = get_local_patient(patient_id, db_path=db_path)
    if not raw:
        raise ValueError(f"Patient {patient_id} not found in local SQLite store.")
        
    return NormalizedPatient(
        patient_id=raw["id"],
        name=raw["name"],
        date_of_birth=raw.get("date_of_birth")
    )

def get_normalized_observations(patient_id: str, db_path: Optional[str] = None) -> List[NormalizedObservation]:
    """
    Retrieves local SQLite observation records and transforms into NormalizedObservation list.
    """
    raw_obs_list = get_local_observations(patient_id, db_path=db_path)
    normalized_list = []

    for raw in raw_obs_list:
        norm_type = _canonicalize_local_type(raw["type"])
        
        normalized_list.append(NormalizedObservation(
            patient_id=patient_id,
            observation_type=norm_type,
            value=float(raw["value"]),
            unit=raw["unit"],
            timestamp=raw["timestamp"],
            source="local",
            source_record_id=raw["id"]
        ))

    return normalized_list

def get_normalized_medications(patient_id: str, db_path: Optional[str] = None) -> List[NormalizedMedication]:
    """
    Retrieves local SQLite medication records and transforms into NormalizedMedication list.
    """
    raw_meds = get_local_medications(patient_id, db_path=db_path)
    normalized_list = []

    for raw in raw_meds:
        normalized_list.append(NormalizedMedication(
            patient_id=patient_id,
            medication_name=raw["medication_name"],
            status=raw["status"],
            dosage=raw["dosage"],
            timestamp=raw["timestamp"],
            source="local",
            source_record_id=raw["id"]
        ))

    return normalized_list
