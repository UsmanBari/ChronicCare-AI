"""
FHIR Client for Connected Mode (SMART Health IT Open R4 Endpoint)

Provides deterministic, retrieval-only functions for accessing FHIR R4 resources.
Performs NO clinical interpretation, risk calculation, reconciliation, or LLM processing.
"""

import os
import requests
from typing import Dict, List, Any, Optional

DEFAULT_FHIR_BASE_URL = "https://r4.smarthealthit.org"

def _get_base_url(base_url: Optional[str] = None) -> str:
    if base_url:
        return base_url.rstrip("/")
    env_url = os.environ.get("FHIR_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    return DEFAULT_FHIR_BASE_URL.rstrip("/")

def check_fhir_metadata(base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks the FHIR server metadata (CapabilityStatement) endpoint.
    Returns parsed JSON dict of server capabilities.
    """
    url = f"{_get_base_url(base_url)}/metadata"
    headers = {"Accept": "application/fhir+json, application/json"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()

def search_fhir_patients(count: int = 10, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Searches for Patient resources on the FHIR server up to `count`.
    Returns list of Patient resource dictionaries.
    """
    url = f"{_get_base_url(base_url)}/Patient"
    headers = {"Accept": "application/fhir+json, application/json"}
    params = {"_count": count}
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    bundle = response.json()
    entries = bundle.get("entry", [])
    return [entry["resource"] for entry in entries if "resource" in entry]

def get_fhir_patient(patient_id: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves a Patient resource by patient ID.
    Returns Patient resource dictionary.
    """
    url = f"{_get_base_url(base_url)}/Patient/{patient_id}"
    headers = {"Accept": "application/fhir+json, application/json"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()

def get_fhir_observations(patient_id: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves Observation resources for a given patient ID.
    Covers observations such as blood glucose, HbA1c, blood pressure, weight, etc.
    Returns list of Observation resource dictionaries.
    """
    url = f"{_get_base_url(base_url)}/Observation"
    headers = {"Accept": "application/fhir+json, application/json"}
    params = {"patient": patient_id, "_count": 100}
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    bundle = response.json()
    entries = bundle.get("entry", [])
    return [entry["resource"] for entry in entries if "resource" in entry]

def get_fhir_medications(patient_id: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves MedicationRequest resources for a given patient ID.
    Returns list of MedicationRequest resource dictionaries.
    """
    url = f"{_get_base_url(base_url)}/MedicationRequest"
    headers = {"Accept": "application/fhir+json, application/json"}
    params = {"patient": patient_id, "_count": 100}
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    bundle = response.json()
    entries = bundle.get("entry", [])
    return [entry["resource"] for entry in entries if "resource" in entry]
