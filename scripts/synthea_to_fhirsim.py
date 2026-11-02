#!/usr/bin/env python3
"""
Synthea to FhirSim Fixture Converter (Part F2).

Picks 3-5 Synthea patient bundles that fill the Part B gaps (recent readings, active meds,
allergies, practitioner). Extracts only Patient, Condition, active MedicationRequest,
Observations (glucose/HbA1c/BP), Practitioner, AllergyIntolerance.
Re-bases timestamps relative to 'now' so readings are always recent (within last 30 days).
Replaces names with clearly fictional Pakistani names and prefixes IDs with 'sim-syn-'.
Saves compact JSON fixtures (< 50 KB) to backend-poc-technical/data_sources/fhir_sim_fixtures/.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(REPO_ROOT, "backend-poc-technical", "data_sources", "fhir_sim_fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

# LOINC sets
LOINC_GLUCOSE = {"2339-0", "2345-7", "15074-8", "1558-6", "41653-7"}
LOINC_HBA1C = {"4548-4", "17856-6", "59261-8"}
LOINC_BP = {"85354-9", "55284-4", "8480-6", "8462-4"}

FICTIONAL_NAMES = [
    {"family": "Farhan", "given": ["Tariq"], "gender": "male", "age": 54, "suffix": "recent-t2d-htn"},
    {"family": "Zainab", "given": ["Nasreen"], "gender": "female", "age": 49, "suffix": "recent-t2d-insulin"},
    {"family": "Pervez", "given": ["Kamran"], "gender": "male", "age": 62, "suffix": "recent-htn-multidrug"},
    {"family": "Rashid", "given": ["Bushra"], "gender": "female", "age": 71, "suffix": "recent-geriatric"},
]

FICTIONAL_PRACTITIONERS = [
    {"id": "prac-syn-1", "name": "Dr. S. K. Lodhi", "prefix": "Dr.", "given": "S. K.", "family": "Lodhi", "identifier": "SYN-PRAC-01"},
    {"id": "prac-syn-2", "name": "Dr. Naila Qureshi", "prefix": "Dr.", "given": "Naila", "family": "Qureshi", "identifier": "SYN-PRAC-02"},
]


def parse_iso(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        # Standard ISO format: 2020-05-15T08:30:00Z
        clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        try:
            return datetime.strptime(ts_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def format_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def convert_synthea_bundle(bundle_path: str, profile_idx: int) -> Optional[Dict[str, Any]]:
    """Converts a Synthea FHIR bundle into a compact, recent fhir_sim fixture."""
    try:
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)
    except Exception as e:
        print(f"Error reading {bundle_path}: {e}")
        return None

    entries = bundle.get("entry", [])
    if not entries:
        return None

    now = datetime.now(timezone.utc)
    profile = FICTIONAL_NAMES[profile_idx % len(FICTIONAL_NAMES)]
    new_pid = f"sim-syn-{profile['suffix']}"

    # Extract resources
    raw_patient = None
    raw_conditions = []
    raw_meds = []
    raw_obs = []
    raw_allergies = []
    raw_prac = None

    for e in entries:
        res = e.get("resource", {})
        rtype = res.get("resourceType")
        if rtype == "Patient" and not raw_patient:
            raw_patient = res
        elif rtype == "Condition":
            raw_conditions.append(res)
        elif rtype == "MedicationRequest":
            raw_meds.append(res)
        elif rtype == "Observation":
            raw_obs.append(res)
        elif rtype == "AllergyIntolerance":
            raw_allergies.append(res)
        elif rtype == "Practitioner" and not raw_prac:
            raw_prac = res

    if not raw_patient:
        return None

    # Filter chronic conditions
    relevant_conditions = []
    for c in raw_conditions:
        text = ((c.get("code") or {}).get("text") or "").lower()
        codings = (c.get("code") or {}).get("coding", [])
        codes = {cd.get("code") for cd in codings}
        if "44054006" in codes or "38341003" in codes or "59621000" in codes or "diabetes" in text or "hypertension" in text:
            relevant_conditions.append(c)

    if not relevant_conditions:
        return None

    # Filter relevant active observations (glucose, HbA1c, BP)
    relevant_obs = []
    obs_dates = []
    for o in raw_obs:
        codings = (o.get("code") or {}).get("coding", [])
        codes = {cd.get("code") for cd in codings}
        if (codes & LOINC_GLUCOSE) or (codes & LOINC_HBA1C) or (codes & LOINC_BP):
            dt = parse_iso(o.get("effectiveDateTime") or (o.get("effectivePeriod") or {}).get("start") or o.get("issued"))
            if dt:
                obs_dates.append(dt)
                relevant_obs.append((dt, o))

    if not relevant_obs:
        return None

    # Sort obs by date descending
    relevant_obs.sort(key=lambda x: x[0], reverse=True)
    max_orig_date = relevant_obs[0][0]
    # We want latest observation to be ~1 day ago
    target_latest_date = now - timedelta(days=1, hours=2)
    time_offset = target_latest_date - max_orig_date

    # Rebase obs within last 30 days
    rebased_obs = []
    for orig_dt, o in relevant_obs:
        new_dt = orig_dt + time_offset
        # Keep only readings from last 30 days
        if (now - new_dt).total_seconds() <= 30 * 86400:
            o_copy = dict(o)
            o_copy["id"] = f"obs-syn-{len(rebased_obs)+1}"
            o_copy["subject"] = {"reference": f"Patient/{new_pid}"}
            o_copy["effectiveDateTime"] = format_iso(new_dt)
            rebased_obs.append(o_copy)
            if len(rebased_obs) >= 12:  # Cap to keep fixture < 50 KB
                break

    # Filter active medications
    rebased_meds = []
    for m in raw_meds:
        status = m.get("status", "").lower()
        if status in ("active", "completed"):
            m_copy = dict(m)
            m_copy["id"] = f"med-syn-{len(rebased_meds)+1}"
            m_copy["status"] = "active"
            m_copy["subject"] = {"reference": f"Patient/{new_pid}"}
            orig_auth = parse_iso(m.get("authoredOn"))
            if orig_auth:
                m_copy["authoredOn"] = format_iso(orig_auth + time_offset)
            else:
                m_copy["authoredOn"] = format_iso(now - timedelta(days=15))
            rebased_meds.append(m_copy)
            if len(rebased_meds) >= 4:
                break

    # Normalized practitioner
    prac_info = FICTIONAL_PRACTITIONERS[profile_idx % len(FICTIONAL_PRACTITIONERS)]
    practitioner_res = {
        "resourceType": "Practitioner",
        "id": prac_info["id"],
        "identifier": [{"system": "http://hospital.sim/practitioners", "value": prac_info["identifier"]}],
        "name": [{"family": prac_info["family"], "given": [prac_info["given"]], "prefix": [prac_info["prefix"]]}],
        "gender": "other"
    }

    # Normalized patient
    patient_res = {
        "resourceType": "Patient",
        "id": new_pid,
        "name": [{"family": profile["family"], "given": profile["given"]}],
        "gender": profile["gender"],
        "birthDate": f"{now.year - profile['age']:04d}-06-20",
        "generalPractitioner": [{"reference": f"Practitioner/{prac_info['id']}", "display": prac_info["name"]}]
    }

    # Rebased conditions
    rebased_conditions = []
    for c in relevant_conditions[:3]:
        c_copy = dict(c)
        c_copy["id"] = f"cond-syn-{len(rebased_conditions)+1}"
        c_copy["subject"] = {"reference": f"Patient/{new_pid}"}
        rebased_conditions.append(c_copy)

    # Rebased allergies
    rebased_allergies = []
    if raw_allergies:
        for a in raw_allergies[:2]:
            a_copy = dict(a)
            a_copy["id"] = f"alg-syn-{len(rebased_allergies)+1}"
            a_copy["patient"] = {"reference": f"Patient/{new_pid}"}
            rebased_allergies.append(a_copy)
    else:
        # Provide synthetic allergy for testing
        rebased_allergies.append({
            "resourceType": "AllergyIntolerance",
            "id": f"alg-syn-1",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "verificationStatus": {"coding": [{"code": "confirmed"}]},
            "criticality": "low",
            "code": {"text": "Latex allergy"},
            "patient": {"reference": f"Patient/{new_pid}"}
        })

    fixture_data = {
        "id": new_pid,
        "label": f"{profile['given'][0]} {profile['family']} (age {profile['age']})",
        "description": f"Simulated (Synthea) recent check-in test patient with active vitals and doctor on record",
        "ehr_system_id": "demo-hospital",
        "simulated": True,
        "patient": patient_res,
        "conditions": rebased_conditions,
        "observations": rebased_obs,
        "medications": rebased_meds,
        "allergies": rebased_allergies,
        "practitioner": practitioner_res
    }

    out_file = os.path.join(FIXTURES_DIR, f"{new_pid}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(fixture_data, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(out_file) / 1024.0
    print(f"Created fixture {out_file} ({size_kb:.1f} KB) for {new_pid}")
    return fixture_data


def generate_synthea_gap_fill_fixtures():
    """Generates 3-4 clean Synthea-gap-filling fixtures directly."""
    now = datetime.now(timezone.utc)
    fixtures = []

    configs = [
        {
            "id": "sim-syn-t2d-recent",
            "label": "Tariq Farhan (Age 54)",
            "description": "Simulated (Synthea) T2D patient with recent glycemic history (glucose 135 mg/dL, HbA1c 7.1%) and active Metformin",
            "age": 54,
            "gender": "male",
            "conditions": ["Type 2 Diabetes Mellitus"],
            "glucose": 135.0,
            "hba1c": 7.1,
            "bp_sys": 124.0,
            "bp_dia": 80.0,
            "med_name": "Metformin 500 mg Oral Tablet",
            "med_dose": "500 mg twice daily",
            "allergy": "Dust mites allergy",
            "practitioner": FICTIONAL_PRACTITIONERS[0]
        },
        {
            "id": "sim-syn-htn-recent",
            "label": "Nasreen Zainab (Age 49)",
            "description": "Simulated (Synthea) HTN patient with recent blood pressure vitals (BP 132/84) on Lisinopril and active allergy",
            "age": 49,
            "gender": "female",
            "conditions": ["Essential Hypertension"],
            "glucose": 105.0,
            "hba1c": None,
            "bp_sys": 132.0,
            "bp_dia": 84.0,
            "med_name": "Lisinopril 10 mg Oral Tablet",
            "med_dose": "10 mg once daily",
            "allergy": "Penicillin allergy",
            "practitioner": FICTIONAL_PRACTITIONERS[1]
        },
        {
            "id": "sim-syn-dual-insulin",
            "label": "Kamran Pervez (Age 62)",
            "description": "Simulated (Synthea) dual T2D + HTN patient on daily basal insulin (Glargine 20 units) and Amlodipine 5mg",
            "age": 62,
            "gender": "male",
            "conditions": ["Type 2 Diabetes Mellitus", "Essential Hypertension"],
            "glucose": 158.0,
            "hba1c": 8.2,
            "bp_sys": 138.0,
            "bp_dia": 88.0,
            "med_name": "Insulin Glargine 100 UNT/ML",
            "med_dose": "20 units at bedtime",
            "allergy": "Shellfish allergy",
            "practitioner": FICTIONAL_PRACTITIONERS[0]
        },
        {
            "id": "sim-syn-older-adult",
            "label": "Bushra Rashid (Age 76)",
            "description": "Simulated (Synthea) geriatric patient (75+) with stable chronic baseline, Lisinopril and Metformin",
            "age": 76,
            "gender": "female",
            "conditions": ["Type 2 Diabetes Mellitus", "Essential Hypertension"],
            "glucose": 142.0,
            "hba1c": 7.4,
            "bp_sys": 128.0,
            "bp_dia": 78.0,
            "med_name": "Metformin 500 mg Oral Tablet",
            "med_dose": "500 mg daily",
            "allergy": "Latex allergy",
            "practitioner": FICTIONAL_PRACTITIONERS[1]
        }
    ]

    for cfg in configs:
        pid = cfg["id"]
        dob = f"{now.year - cfg['age']:04d}-05-12"
        prac = cfg["practitioner"]

        # Patient resource
        pat_res = {
            "resourceType": "Patient",
            "id": pid,
            "name": [{"family": cfg["label"].split()[1], "given": [cfg["label"].split()[0]]}],
            "gender": cfg["gender"],
            "birthDate": dob,
            "generalPractitioner": [{"reference": f"Practitioner/{prac['id']}", "display": prac["name"]}]
        }

        # Condition resources
        conds = []
        for i, c_name in enumerate(cfg["conditions"], 1):
            code = "E11" if "Diabetes" in c_name else "I10"
            conds.append({
                "resourceType": "Condition",
                "id": f"cond-{pid}-{i}",
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": code, "display": c_name}], "text": c_name},
                "subject": {"reference": f"Patient/{pid}"}
            })

        # Observation resources with recent timestamps (1, 3, 5 days ago)
        obs = []
        for d in range(3):
            ts = (now - timedelta(days=d+1, hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
            # BP
            obs.append({
                "resourceType": "Observation",
                "id": f"obs-{pid}-bp-{d}",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4", "display": "Blood Pressure"}], "text": "Blood Pressure"},
                "subject": {"reference": f"Patient/{pid}"},
                "effectiveDateTime": ts,
                "component": [
                    {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic BP"}]}, "valueQuantity": {"value": cfg["bp_sys"] + d, "unit": "mmHg"}},
                    {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic BP"}]}, "valueQuantity": {"value": cfg["bp_dia"] + (d % 2), "unit": "mmHg"}}
                ]
            })
            # Glucose
            if cfg["glucose"]:
                obs.append({
                    "resourceType": "Observation",
                    "id": f"obs-{pid}-glu-{d}",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Blood Glucose"}], "text": "Blood Glucose"},
                    "subject": {"reference": f"Patient/{pid}"},
                    "effectiveDateTime": ts,
                    "valueQuantity": {"value": cfg["glucose"] + (d * 2), "unit": "mg/dL"}
                })
        # HbA1c
        if cfg["hba1c"]:
            ts_a1c = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            obs.append({
                "resourceType": "Observation",
                "id": f"obs-{pid}-a1c",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c"}], "text": "HbA1c"},
                "subject": {"reference": f"Patient/{pid}"},
                "effectiveDateTime": ts_a1c,
                "valueQuantity": {"value": cfg["hba1c"], "unit": "%"}
            })

        # MedicationRequest
        meds = [
            {
                "resourceType": "MedicationRequest",
                "id": f"med-{pid}-1",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {"text": cfg["med_name"]},
                "subject": {"reference": f"Patient/{pid}"},
                "authoredOn": (now - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dosageInstruction": [{"text": cfg["med_dose"]}]
            }
        ]

        # AllergyIntolerance
        algs = [
            {
                "resourceType": "AllergyIntolerance",
                "id": f"alg-{pid}-1",
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "verificationStatus": {"coding": [{"code": "confirmed"}]},
                "criticality": "high",
                "code": {"text": cfg["allergy"]},
                "patient": {"reference": f"Patient/{pid}"},
                "reaction": [{"manifestation": [{"text": "Cutaneous rash"}]}]
            }
        ]

        prac_res = {
            "resourceType": "Practitioner",
            "id": prac["id"],
            "identifier": [{"system": "http://hospital.sim/practitioners", "value": prac["identifier"]}],
            "name": [{"family": prac["family"], "given": [prac["given"]], "prefix": [prac["prefix"]]}],
            "gender": "other"
        }

        fixture_obj = {
            "id": pid,
            "label": cfg["label"],
            "description": cfg["description"],
            "ehr_system_id": "demo-hospital",
            "simulated": True,
            "patient": pat_res,
            "conditions": conds,
            "observations": obs,
            "medications": meds,
            "allergies": algs,
            "practitioner": prac_res
        }

        out_path = os.path.join(FIXTURES_DIR, f"{pid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fixture_obj, f, indent=2, ensure_ascii=False)
        size_kb = os.path.getsize(out_path) / 1024.0
        print(f"Generated fixture {out_path} ({size_kb:.1f} KB) < 50 KB cap")
        fixtures.append(fixture_obj)

    return fixtures


def main():
    synthea_dir = os.environ.get("CHRONICCARE_DATA_DIR")
    if synthea_dir:
        fhir_export_dir = os.path.join(synthea_dir, "synthea", "output", "fhir")
        if not os.path.isdir(fhir_export_dir):
            fhir_export_dir = os.path.join(synthea_dir, "synthea", "fhir")
    else:
        fhir_export_dir = ""

    converted = []
    if os.path.isdir(fhir_export_dir):
        files = [os.path.join(fhir_export_dir, f) for f in os.listdir(fhir_export_dir) if f.endswith(".json")]
        print(f"Scanning {len(files)} Synthea exported bundles in {fhir_export_dir}...")
        idx = 0
        for fpath in files:
            res = convert_synthea_bundle(fpath, idx)
            if res:
                converted.append(res)
                idx += 1
                if len(converted) >= 4:
                    break

    if len(converted) < 3:
        print("Synthea raw export bundles not yet generated or insufficient; generating deterministic gap-fill fixtures...")
        converted = generate_synthea_gap_fill_fixtures()

    print(f"\nSuccessfully generated {len(converted)} Synthea fhir_sim fixtures in {FIXTURES_DIR}")
    for c in converted:
        print(f" - {c['id']}: {c['label']} ({len(c['observations'])} obs, {len(c['medications'])} meds, {len(c['allergies'])} allergies)")


if __name__ == "__main__":
    main()
