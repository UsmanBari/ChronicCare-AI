"""
Single Canonical Registry for EHR Test and Sample Patients (Part C & Fix 3).

Consolidates sample simulated patients and public sandbox suggested patients
into a single source of truth used across main.py and app_store.py.
"""

from typing import List, Dict, Any, Optional

# Canonical test patients registry
# Each item has: id, label, description, ehr_system_id, simulated
ALL_EHR_TEST_PATIENTS: List[Dict[str, Any]] = [
    # Demo hospital (simulated) archetypes (5 baseline + 4 Synthea gap-fills)
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
    {
        "id": "sim-syn-recent-geriatric",
        "label": "Bushra Rashid (age 71) (Simulated, Synthea)",
        "description": "Geriatric dual T2D & HTN with active vitals and doctor on record",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-syn-recent-htn-multidrug",
        "label": "Kamran Pervez (age 62) (Simulated, Synthea)",
        "description": "Multi-drug HTN with recent blood pressure observations and doctor on record",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-syn-recent-t2d-htn",
        "label": "Tariq Farhan (age 54) (Simulated, Synthea)",
        "description": "Dual T2D & HTN with recent glucose and blood pressure observations",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },
    {
        "id": "sim-syn-recent-t2d-insulin",
        "label": "Nasreen Zainab (age 49) (Simulated, Synthea)",
        "description": "Type 2 diabetes on insulin therapy with recent glucose readings",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
    },

    # SMART Sandbox suggested patients (12 selected from EHR_TEST_PATIENTS.md + 3 legacy)
    {
        "id": "12edb5a0-ec71-45b7-aff6-0fef1c382881",
        "label": "SMART Sandbox (Age 75, Dual T2D + HTN, 3 Meds)",
        "description": "Triple in-scope therapy (Amlodipine, Humulin Insulin, Hydrochlorothiazide) with doctor Cedrick Runte",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "9bf59715-246f-4ce2-85a6-58c1757f8d21",
        "label": "SMART Sandbox (Age 78, Dual T2D + HTN)",
        "description": "Older adult with complete labs, Metformin ER and Hydrochlorothiazide",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "948e608d-e408-4788-8cf2-8157c49c2940",
        "label": "SMART Sandbox (Age 55, Dual T2D + HTN, Multi-Drug)",
        "description": "Humulin Insulin, Hydrochlorothiazide, and Metformin ER with doctor Jonah Schroeder",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "bd6f9f37-7295-4cd6-b212-134afcef1253",
        "label": "SMART Sandbox (Age 70, Dual T2D + HTN, Full Panel)",
        "description": "Dual diagnosis on 3 in-scope chronic medications with full synchronized laboratory panel",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "fa064acf-b7f1-4279-83d3-7a94686da7ba",
        "label": "SMART Sandbox (Age 106, Dual Centenarian)",
        "description": "Centenarian edge case with dual conditions, BP vitals, and chronic medications",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "0e61c3ad-d11e-4080-a6aa-cac89cae4e37",
        "label": "SMART Sandbox (Age 73, Dual T2D + HTN)",
        "description": "Insulin therapy combined with thiazide diuretic and biguanide",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "ab4e7a7d-8b0d-41e1-9ce9-3877d7615aed",
        "label": "SMART Sandbox (Age 69, Dual T2D + HTN)",
        "description": "Dual diagnosis on Humulin 70/30 Insulin and Hydrochlorothiazide",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "4d58465c-4703-4c36-ab8f-2f935dc4bee7",
        "label": "SMART Sandbox (Age 64, Dual T2D + HTN)",
        "description": "Female adult on triple chronic therapy (Humulin, Metformin ER, Hydrochlorothiazide)",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "7099b4c5-6f47-4293-9690-f2afb23b9dd6",
        "label": "SMART Sandbox (Age 80, T2D Only, Oral + Injectable)",
        "description": "Octogenarian on Humulin Insulin and Metformin ER with doctor Gregg Johns",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "132f48ba-1d72-4e0c-a220-91786d7501aa",
        "label": "SMART Sandbox (Age 56, T2D Only)",
        "description": "Type 2 Diabetes isolated condition on Humulin and Metformin with full glycemic history",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "71304c2e-64b0-4b57-91f6-2c1ff771d72c",
        "label": "SMART Sandbox (Age 67, T2D Monotherapy)",
        "description": "Type 2 Diabetes on single first-line oral antidiabetic (Metformin ER)",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "d4f1aab1-73e6-4d51-98eb-e1556406b2a3",
        "label": "SMART Sandbox (Age 63, HTN Monotherapy)",
        "description": "Essential hypertension isolated condition on Hydrochlorothiazide diuretic therapy",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "d48ac962-78c6-46cf-ba33-a24771bfa0e4",
        "label": "SMART Sandbox (Age 87, T2D, Legacy Sandbox)",
        "description": "Jerrell Gerlach, Type 2 diabetes with practitioner Felicitas Kub",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3",
        "label": "SMART Sandbox (Age 53, T2D, Legacy Sandbox)",
        "description": "Twanda Rippin, Type 2 diabetes with practitioner Erlinda Franecki and allergies",
        "ehr_system_id": "smart-sandbox",
        "simulated": False,
    },
    {
        "id": "4551370c-c3eb-4164-a2ff-b528f73a4e0f",
        "label": "SMART Sandbox (Age 29, Legacy Sandbox)",
        "description": "Octavio Dickens, public sandbox patient with allergy intolerance records",
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
    """Allows adding dynamic fixtures to the registry."""
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
        if p["ehr_system_id"] == ehr_system_id and not p["simulated"]
    ]


# Backwards-compatible views for existing imports
SIMULATED_SAMPLE_PATIENTS: List[Dict[str, Any]] = get_sample_patients_for_system("demo-hospital")
PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS: List[str] = get_suggested_patient_ids_for_system("smart-sandbox")
SUGGESTED_PATIENT_IDS: List[str] = PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS
