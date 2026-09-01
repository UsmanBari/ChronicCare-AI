"""
FHIR Adapter (Milestone 2)

Wraps raw FHIR client responses and normalizes them into source-agnostic models
(NormalizedPatient, NormalizedObservation, NormalizedMedication).

=============================================================================
FHIR TO NORMALIZED MAPPING TABLE
=============================================================================
FHIR Field / Code                    -> Normalized Field / Type
-----------------------------------------------------------------------------
Patient:
  id                                 -> patient_id
  name[0] (given + family)           -> name
  birthDate                          -> date_of_birth

Observation:
  LOINC 2339-0 / "Glucose"           -> observation_type: "glucose"
  LOINC 4548-4 / "Hemoglobin A1c"    -> observation_type: "hba1c"
  LOINC 29463-7 / "Body Weight"      -> observation_type: "weight"
  LOINC 8302-2 / "Body Height"       -> observation_type: "height"
  LOINC 39156-5 / "Body Mass Index"  -> observation_type: "bmi"
  LOINC 85354-9 / "Blood Pressure"   -> Splitted into:
    component (8480-6 / Systolic)    -> observation_type: "blood_pressure_systolic"
    component (8462-4 / Diastolic)   -> observation_type: "blood_pressure_diastolic"
  valueQuantity.value                -> value (float)
  valueQuantity.unit                 -> unit
  effectiveDateTime / issued         -> timestamp
  id                                 -> source_record_id
  Constant                           -> source: "fhir"

MedicationRequest:
  medicationCodeableConcept          -> medication_name
  status                             -> status
  dosageInstruction[0].text          -> dosage
  authoredOn / meta.lastUpdated      -> timestamp
  id                                 -> source_record_id
  Constant                           -> source: "fhir"
=============================================================================
Note: Assumes standard units (mg/dL, %, mmHg, kg) across sources.
"""

import re
from typing import List, Optional
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication
from data_sources.fhir_client import (
    get_fhir_patient,
    get_fhir_observations,
    get_fhir_medications
)

# Canonical Code / Display Mapping Dictionary
OBS_TYPE_MAP = {
    "2339-0": "glucose",
    "glucose": "glucose",
    "fasting blood glucose": "glucose",
    "4548-4": "hba1c",
    "hemoglobin a1c": "hba1c",
    "hemoglobin a1c/hemoglobin.total in blood": "hba1c",
    "hba1c": "hba1c",
    "29463-7": "weight",
    "body weight": "weight",
    "8302-2": "height",
    "body height": "height",
    "39156-5": "bmi",
    "body mass index": "bmi",
    "8480-6": "blood_pressure_systolic",
    "systolic blood pressure": "blood_pressure_systolic",
    "8462-4": "blood_pressure_diastolic",
    "diastolic blood pressure": "blood_pressure_diastolic",
}

def _canonicalize_type(code_text: str, loinc_code: Optional[str] = None) -> str:
    if loinc_code and loinc_code in OBS_TYPE_MAP:
        return OBS_TYPE_MAP[loinc_code]
    
    clean_text = code_text.strip().lower()
    if clean_text in OBS_TYPE_MAP:
        return OBS_TYPE_MAP[clean_text]
        
    for k, v in OBS_TYPE_MAP.items():
        if k in clean_text:
            return v
            
    # Fallback to snake_case string
    snake = re.sub(r'[\s\-/]+', '_', clean_text)
    return re.sub(r'[^a-z0-9_]', '', snake).strip('_')

def get_normalized_patient(patient_id: str, base_url: Optional[str] = None) -> NormalizedPatient:
    """
    Retrieves FHIR Patient resource and transforms into NormalizedPatient.
    """
    raw = get_fhir_patient(patient_id, base_url=base_url)
    
    names = raw.get("name", [{}])
    primary_name = names[0] if names else {}
    given = " ".join(primary_name.get("given", []))
    family = primary_name.get("family", "")
    full_name = f"{given} {family}".strip() or f"FHIR Patient {patient_id}"
    
    return NormalizedPatient(
        patient_id=raw.get("id", patient_id),
        name=full_name,
        date_of_birth=raw.get("birthDate")
    )

def get_normalized_observations(patient_id: str, base_url: Optional[str] = None) -> List[NormalizedObservation]:
    """
    Retrieves FHIR Observation resources and transforms into NormalizedObservation instances.
    Handles compound observations (such as Blood Pressure with components).
    """
    raw_obs_list = get_fhir_observations(patient_id, base_url=base_url)
    normalized_list = []

    for raw in raw_obs_list:
        obs_id = raw.get("id", "unknown_fhir_obs")
        timestamp = raw.get("effectiveDateTime") or raw.get("issued") or "unknown_time"
        
        # Extract LOINC code & Display text
        code_concept = raw.get("code", {})
        codings = code_concept.get("coding", [])
        loinc = codings[0].get("code") if codings else None
        display = code_concept.get("text") or (codings[0].get("display") if codings else "Observation")

        # 1. Single valueQuantity observation
        if "valueQuantity" in raw:
            vq = raw["valueQuantity"]
            val = float(vq.get("value", 0.0))
            unit = vq.get("unit") or vq.get("code") or "N/A"
            norm_type = _canonicalize_type(display, loinc)
            
            normalized_list.append(NormalizedObservation(
                patient_id=patient_id,
                observation_type=norm_type,
                value=val,
                unit=unit,
                timestamp=timestamp,
                source="fhir",
                source_record_id=obs_id
            ))
            
        # 2. Compound observation (e.g. Blood Pressure components)
        elif "component" in raw:
            for comp_idx, comp in enumerate(raw["component"]):
                comp_concept = comp.get("code", {})
                comp_codings = comp_concept.get("coding", [])
                comp_loinc = comp_codings[0].get("code") if comp_codings else None
                comp_display = comp_concept.get("text") or (comp_codings[0].get("display") if comp_codings else display)
                
                vq = comp.get("valueQuantity", {})
                if "value" in vq:
                    val = float(vq.get("value", 0.0))
                    unit = vq.get("unit") or vq.get("code") or "mmHg"
                    norm_type = _canonicalize_type(comp_display, comp_loinc)
                    
                    normalized_list.append(NormalizedObservation(
                        patient_id=patient_id,
                        observation_type=norm_type,
                        value=val,
                        unit=unit,
                        timestamp=timestamp,
                        source="fhir",
                        source_record_id=f"{obs_id}_comp_{comp_idx}"
                    ))

    return normalized_list

def get_normalized_medications(patient_id: str, base_url: Optional[str] = None) -> List[NormalizedMedication]:
    """
    Retrieves FHIR MedicationRequest resources and transforms into NormalizedMedication instances.
    """
    raw_meds = get_fhir_medications(patient_id, base_url=base_url)
    normalized_list = []

    for raw in raw_meds:
        med_id = raw.get("id", "unknown_fhir_med")
        status = raw.get("status", "unknown")
        timestamp = raw.get("authoredOn") or raw.get("meta", {}).get("lastUpdated", "unknown_time")

        # Medication Name
        concept = raw.get("medicationCodeableConcept", {})
        codings = concept.get("coding", [])
        med_name = concept.get("text") or (codings[0].get("display") if codings else "Unspecified Medication")

        # Dosage Text
        dosages = raw.get("dosageInstruction", [])
        dosage_text = "As directed"
        if dosages:
            dosage_text = dosages[0].get("text") or dosages[0].get("patientInstruction") or "As directed"

        normalized_list.append(NormalizedMedication(
            patient_id=patient_id,
            medication_name=med_name,
            status=status,
            dosage=dosage_text,
            timestamp=timestamp,
            source="fhir",
            source_record_id=med_id
        ))

    return normalized_list
