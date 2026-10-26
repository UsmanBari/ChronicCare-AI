"""
Single Canonical Registry for EHR Test and Sample Patients (Part C).

Consolidates sample simulated patients and public sandbox suggested patients
into a single source of truth used across main.py and app_store.py.
"""

from typing import List, Dict, Any, Optional

# Canonical test patients registry
# Each item has: id, label, description, ehr_system_id, simulated
ALL_EHR_TEST_PATIENTS: List[Dict[str, Any]] = [
    # Demo hospital (simulated) archetypes
    {
        "id": "sim-ayesha",
        "label": "Ayesha K. (age 52)",
        "description": "Type 2 diabetes & hypertension (BP ~128/82, glucose 140-150, active Metformin & Lisinopril)",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-bilal",
        "label": "Bilal A. (age 67)",
        "description": "Hypertension personal baseline (BP 110-116/70-74, active Amlodipine)",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-sana",
        "label": "Sana M. (age 45)",
        "description": "Type 2 diabetes on insulin (glucose 150-175, active Insulin glargine & Metformin)",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-imran",
        "label": "Imran Q. (age 71)",
        "description": "Type 2 diabetes & hypertension, rising readings (BP 148-156/92-98, glucose 180-210)",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-newpatient",
        "label": "Nadia R. (age 38)",
        "description": "Hypertension, no recent observations (empty record test)",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    # SMART Sandbox suggested patients
    {
        "id": "d48ac962-78c6-46cf-ba33-a24771bfa0e4",
        "label": "SMART Sandbox Patient 1",
        "description": "Type 2 diabetes & hypertension in public sandbox",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3",
        "label": "SMART Sandbox Patient 2",
        "description": "Hypertension in public sandbox",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "4551370c-c3eb-4164-a2ff-b528f73a4e0f",
        "label": "SMART Sandbox Patient 3",
        "description": "Type 2 diabetes in public sandbox",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
]


def register_test_patient(
    patient_id: str,
    label: str,
    description: str,
    ehr_system_id: str,
    simulated: bool = True
) -> None:
    """Allows adding dynamic fixtures (e.g. Synthea gap fills) to the registry."""
    for p in ALL_EHR_TEST_PATIENTS:
        if p["id"] == patient_id:
            p.update({
                "label": label,
                "description": description,
                "ehr_system_id": ehr_system_id,
                "simulated": simulated,
            })
            return
    ALL_EHR_TEST_PATIENTS.append({
        "id": patient_id,
        "label": label,
        "description": description,
        "ehr_system_id": ehr_system_id,
        "simulated": simulated,
    })


def get_sample_patients_for_system(ehr_system_id: str) -> List[Dict[str, Any]]:
    """Returns sample patients dicts (id, label, description) for a given EHR system."""
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "description": p["description"]
        }
        for p in ALL_EHR_TEST_PATIENTS
        if p["ehr_system_id"] == ehr_system_id and p["simulated"]
    ]


def get_suggested_patient_ids_for_system(ehr_system_id: str) -> List[str]:
    """Returns suggested patient IDs list for a given EHR system."""
    return [
        p["id"]
        for p in ALL_EHR_TEST_PATIENTS
        if p["ehr_system_id"] == ehr_system_id
    ]


# Backwards-compatible views for existing imports
SIMULATED_SAMPLE_PATIENTS: List[Dict[str, Any]] = get_sample_patients_for_system("demo-hospital")
PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS: List[str] = get_suggested_patient_ids_for_system("smart-sandbox")
SUGGESTED_PATIENT_IDS: List[str] = PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS
