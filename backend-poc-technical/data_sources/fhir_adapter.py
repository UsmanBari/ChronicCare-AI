"""
FHIR Adapter for Connected Mode.

Wraps raw FHIR client responses and normalizes them into source-agnostic models
(NormalizedPatient, NormalizedObservation, NormalizedMedication).

Provides accurate LOINC resolution, standard clinical unit conversions,
safe component extraction, and robust timestamp fallback.
"""

import re
from typing import List, Optional, Dict, Any
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication
from data_sources.fhir_client import (
    get_fhir_patient,
    get_fhir_observations,
    get_fhir_medications,
    get_fhir_conditions
)

GLUCOSE_LOINCS = {"2339-0", "2345-7", "15074-8", "1558-6", "41653-7"}
HBA1C_LOINCS = {"4548-4", "17856-6", "59261-8"}
WEIGHT_LOINCS = {"29463-7"}
HEIGHT_LOINCS = {"8302-2"}
BMI_LOINCS = {"39156-5"}
BP_PANEL_LOINCS = {"55284-4", "85354-9"}
BP_SYSTOLIC_LOINCS = {"8480-6"}
BP_DIASTOLIC_LOINCS = {"8462-4"}


def _canonicalize_type(code_text: str, loinc_code: Optional[str] = None) -> str:
    if loinc_code:
        clean_loinc = loinc_code.strip()
        if clean_loinc in GLUCOSE_LOINCS:
            return "glucose"
        if clean_loinc in HBA1C_LOINCS:
            return "hba1c"
        if clean_loinc in WEIGHT_LOINCS:
            return "weight"
        if clean_loinc in HEIGHT_LOINCS:
            return "height"
        if clean_loinc in BMI_LOINCS:
            return "bmi"
        if clean_loinc in BP_SYSTOLIC_LOINCS:
            return "blood_pressure_systolic"
        if clean_loinc in BP_DIASTOLIC_LOINCS:
            return "blood_pressure_diastolic"

    clean_text = (code_text or "").strip().lower()
    if "glucose" in clean_text:
        return "glucose"
    if "a1c" in clean_text or "hba1c" in clean_text or "hemoglobin a1c" in clean_text:
        return "hba1c"
    if "weight" in clean_text:
        return "weight"
    if "height" in clean_text:
        return "height"
    if "body mass index" in clean_text or "bmi" in clean_text:
        return "bmi"
    if "systolic" in clean_text:
        return "blood_pressure_systolic"
    if "diastolic" in clean_text:
        return "blood_pressure_diastolic"

    # Fallback to snake_case string
    snake = re.sub(r'[\s\-/]+', '_', clean_text)
    return re.sub(r'[^a-z0-9_]', '', snake).strip('_')


def _convert_unit_and_value(obs_type: str, val: float, unit: str) -> tuple[float, str]:
    clean_unit = (unit or "").strip()
    u_lower = clean_unit.lower()

    # 1. Glucose: mmol/L to mg/dL (* 18.016)
    if obs_type == "glucose":
        if u_lower in ("mmol/l", "mmol/liter"):
            return round(val * 18.016, 1), "mg/dL"
        if u_lower in ("mg/dl", "mg/deciliter"):
            return round(val, 1), "mg/dL"

    # 2. HbA1c: mmol/mol to % ((mmol/mol * 0.09148) + 2.152)
    if obs_type == "hba1c":
        if u_lower in ("mmol/mol", "mmol/mole"):
            return round((val * 0.09148) + 2.152, 1), "%"
        if u_lower in ("%", "percent"):
            return round(val, 1), "%"

    # 3. Weight: lb / [lb_av] to kg (* 0.45359237)
    if obs_type == "weight":
        if u_lower in ("[lb_av]", "lb", "lbs", "pound", "pounds"):
            return round(val * 0.45359237, 1), "kg"
        if u_lower in ("kg", "kgs", "kilogram", "kilograms"):
            return round(val, 1), "kg"

    # 4. Blood pressure: standard mm[Hg]
    if obs_type in ("blood_pressure_systolic", "blood_pressure_diastolic"):
        if u_lower in ("mm[hg]", "mmhg"):
            return round(val, 1), "mmHg"
        return round(val, 1), clean_unit

    return round(val, 1), clean_unit


def _extract_timestamp(raw: Dict[str, Any]) -> str:
    if raw.get("effectiveDateTime"):
        return str(raw["effectiveDateTime"])
    if isinstance(raw.get("effectivePeriod"), dict) and raw["effectivePeriod"].get("start"):
        return str(raw["effectivePeriod"]["start"])
    if raw.get("issued"):
        return str(raw["issued"])
    return "unknown_time"


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
        patient_id=str(raw.get("id", patient_id)),
        name=full_name,
        date_of_birth=raw.get("birthDate")
    )


def fhir_to_normalized_observations(
    bundle_or_resources: Any,
    patient_id: str = "patient-1"
) -> List[NormalizedObservation]:
    """
    Transforms a FHIR Observation Bundle or list of Observation resources into NormalizedObservations.
    Handles compound observations (BP panels 55284-4 and 85354-9) and single observations.
    """
    if isinstance(bundle_or_resources, dict) and bundle_or_resources.get("resourceType") == "Bundle":
        raw_obs_list = [e.get("resource", {}) for e in bundle_or_resources.get("entry", []) if isinstance(e, dict)]
    elif isinstance(bundle_or_resources, list):
        raw_obs_list = bundle_or_resources
    elif isinstance(bundle_or_resources, dict) and bundle_or_resources.get("resourceType") == "Observation":
        raw_obs_list = [bundle_or_resources]
    else:
        raw_obs_list = []

    normalized_list: List[NormalizedObservation] = []

    for raw in raw_obs_list:
        obs_id = str(raw.get("id", "unknown_fhir_obs"))
        timestamp = _extract_timestamp(raw)
        pid = patient_id
        if "subject" in raw and isinstance(raw["subject"], dict) and "reference" in raw["subject"]:
            ref = raw["subject"]["reference"]
            pid = ref.replace("Patient/", "")
        
        # Concept & LOINC
        code_concept = raw.get("code", {})
        codings = code_concept.get("coding", [])
        loinc = codings[0].get("code") if codings else None
        display = code_concept.get("text") or (codings[0].get("display") if codings else "Observation")

        # 1. Compound observation (e.g. BP panels)
        if "component" in raw and raw["component"]:
            for comp_idx, comp in enumerate(raw["component"]):
                comp_concept = comp.get("code", {})
                comp_codings = comp_concept.get("coding", [])
                comp_loinc = comp_codings[0].get("code") if comp_codings else None
                comp_display = comp_concept.get("text") or (comp_codings[0].get("display") if comp_codings else display)
                
                vq = comp.get("valueQuantity", {})
                if "value" in vq and vq["value"] is not None:
                    try:
                        raw_val = float(vq["value"])
                        raw_unit = vq.get("unit") or vq.get("code") or "mm[Hg]"
                        norm_type = _canonicalize_type(comp_display, comp_loinc)
                        conv_val, conv_unit = _convert_unit_and_value(norm_type, raw_val, raw_unit)
                        
                        normalized_list.append(NormalizedObservation(
                            patient_id=pid,
                            observation_type=norm_type,
                            value=conv_val,
                            unit=conv_unit,
                            timestamp=timestamp,
                            source="fhir",
                            source_record_id=f"{obs_id}_comp_{comp_idx}"
                        ))
                    except (ValueError, TypeError):
                        continue

        # 2. Single valueQuantity observation
        elif "valueQuantity" in raw:
            vq = raw["valueQuantity"]
            if "value" in vq and vq["value"] is not None:
                try:
                    raw_val = float(vq["value"])
                    raw_unit = vq.get("unit") or vq.get("code") or "N/A"
                    norm_type = _canonicalize_type(display, loinc)
                    conv_val, conv_unit = _convert_unit_and_value(norm_type, raw_val, raw_unit)
                    
                    normalized_list.append(NormalizedObservation(
                        patient_id=pid,
                        observation_type=norm_type,
                        value=conv_val,
                        unit=conv_unit,
                        timestamp=timestamp,
                        source="fhir",
                        source_record_id=obs_id
                    ))
                except (ValueError, TypeError):
                    continue

    return normalized_list


def fhir_to_normalized_medications(
    bundle_or_resources: Any,
    patient_id: str = "patient-1"
) -> List[NormalizedMedication]:
    """
    Transforms a FHIR MedicationRequest Bundle or list into NormalizedMedications.
    Status mapping: active stays active; completed/stopped/cancelled/entered-in-error become stopped;
    draft/unknown are ignored.
    """
    if isinstance(bundle_or_resources, dict) and bundle_or_resources.get("resourceType") == "Bundle":
        raw_meds = [e.get("resource", {}) for e in bundle_or_resources.get("entry", []) if isinstance(e, dict)]
    elif isinstance(bundle_or_resources, list):
        raw_meds = bundle_or_resources
    elif isinstance(bundle_or_resources, dict) and bundle_or_resources.get("resourceType") == "MedicationRequest":
        raw_meds = [bundle_or_resources]
    else:
        raw_meds = []

    normalized_list: List[NormalizedMedication] = []

    for raw in raw_meds:
        med_id = str(raw.get("id", "unknown_fhir_med"))
        raw_status = (raw.get("status") or "").lower().strip()
        
        # Status normalization
        if raw_status == "active":
            norm_status = "active"
        elif raw_status in ("completed", "stopped", "cancelled", "entered-in-error"):
            norm_status = "stopped"
        else:
            # draft, unknown, or missing are skipped
            continue

        pid = patient_id
        if "subject" in raw and isinstance(raw["subject"], dict) and "reference" in raw["subject"]:
            ref = raw["subject"]["reference"]
            pid = ref.replace("Patient/", "")

        timestamp = raw.get("authoredOn") or (raw.get("meta") or {}).get("lastUpdated") or "unknown_time"

        # Medication Name
        concept = raw.get("medicationCodeableConcept", {})
        codings = concept.get("coding", [])
        med_name = concept.get("text") or (codings[0].get("display") if codings else "Unspecified Medication")

        # Dosage Text
        dosages = raw.get("dosageInstruction", [])
        dosage_text = "As directed"
        if dosages and isinstance(dosages, list) and len(dosages) > 0:
            dosage_text = dosages[0].get("text") or dosages[0].get("patientInstruction") or "As directed"

        normalized_list.append(NormalizedMedication(
            patient_id=pid,
            medication_name=med_name,
            status=norm_status,
            dosage=dosage_text,
            timestamp=str(timestamp),
            source="fhir",
            source_record_id=med_id
        ))

    return normalized_list


def get_normalized_observations(patient_id: str, base_url: Optional[str] = None) -> List[NormalizedObservation]:
    """
    Retrieves FHIR Observation resources and transforms into NormalizedObservation instances.
    """
    raw_obs_list = get_fhir_observations(patient_id, base_url=base_url)
    return fhir_to_normalized_observations(raw_obs_list, patient_id=patient_id)


def get_normalized_medications(patient_id: str, base_url: Optional[str] = None) -> List[NormalizedMedication]:
    """
    Retrieves FHIR MedicationRequest resources and transforms into NormalizedMedication instances.
    """
    raw_meds = get_fhir_medications(patient_id, base_url=base_url)
    return fhir_to_normalized_medications(raw_meds, patient_id=patient_id)

