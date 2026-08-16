"""
Normalized Data Models for Data Source Abstraction Layer (Milestone 2)

Source-agnostic dataclass schemas representing Patient, Observation, and Medication records.
Contains ONLY structural normalization fields.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class NormalizedPatient:
    patient_id: str
    name: str
    date_of_birth: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class NormalizedObservation:
    patient_id: str
    observation_type: str  # e.g., "glucose", "hba1c", "blood_pressure_systolic", "blood_pressure_diastolic", "weight"
    value: float
    unit: str
    timestamp: str
    source: str  # "fhir" or "local"
    source_record_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class NormalizedMedication:
    patient_id: str
    medication_name: str
    status: str  # e.g., "active", "stopped", "completed"
    dosage: str
    timestamp: str
    source: str  # "fhir" or "local"
    source_record_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
