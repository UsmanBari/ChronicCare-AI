#!/usr/bin/env python3
"""
Find EHR Test Patients from SMART Health IT R4 Sandbox (Part A).

Uses existing fhir_client.fhir_get against https://r4.smarthealthit.org.
Caches responses under $CHRONICCARE_DATA_DIR/ehr_probe/ to avoid redundant network calls.
Evaluates candidates for age >= 18, conditions (T2D / HTN), active in-scope meds,
readings (HbA1c, Glucose, BP), practitioner, and allergies.
"""

import os
import sys
import json
import time
import argparse
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Ensure backend-poc-technical is in path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-poc-technical")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from data_sources.fhir_client import fhir_get, FHIRError
from data_sources.medication_scope import select_chronic_care_medications
from data_sources.models import NormalizedMedication

DEFAULT_FHIR_BASE = "https://r4.smarthealthit.org"
SNOMED_T2D = "http://snomed.info/sct|44054006"
SNOMED_HTN_SPEC = "http://snomed.info/sct|59621000"
SNOMED_HTN_SMART = "http://snomed.info/sct|38341003"  # SMART sandbox uses 38341003 for hypertension

LOINC_HBA1C = {"4548-4", "17856-6", "59261-8"}
LOINC_GLUCOSE = {"2339-0", "2345-7", "15074-8", "1558-6", "41653-7"}
LOINC_BP = {"85354-9", "55284-4", "8480-6", "8462-4"}


def get_cache_dir() -> str:
    data_dir = os.environ.get("CHRONICCARE_DATA_DIR")
    if not data_dir:
        data_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Chronicare-data")
    cache_dir = os.path.join(data_dir, "ehr_probe")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def cached_fhir_get(base: str, path: str, params: Optional[Dict[str, Any]] = None, throttle: float = 0.35) -> Any:
    """Retrieves FHIR data with disk caching and rate limiting."""
    cache_dir = get_cache_dir()
    param_str = json.dumps(sorted((params or {}).items()))
    key = hashlib.sha256(f"{base}:{path}:{param_str}".encode("utf-8")).hexdigest()
    cache_file = os.path.join(cache_dir, f"{key}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Throttle before making network call
    time.sleep(throttle)
    
    # Attempt with one retry
    try:
        data = fhir_get(base, path, params=params, timeout_connect=6.0, timeout_read=12.0, max_retries=1)
    except FHIRError as e:
        if e.status_code == 404:
            data = {}
        else:
            raise

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

    return data


def parse_patient_age(birth_date_str: Optional[str]) -> Optional[int]:
    if not birth_date_str:
        return None
    try:
        # Format usually YYYY or YYYY-MM or YYYY-MM-DD
        year = int(birth_date_str[:4])
        current_year = datetime.now(timezone.utc).year
        return current_year - year
    except Exception:
        return None


def search_condition_patient_ids(base: str, code: str, max_patients: int = 300) -> List[str]:
    """Search for Condition with given code and extract patient IDs, paging via link 'next'."""
    patient_ids = []
    seen = set()
    params: Dict[str, Any] = {"code": code, "_count": 50}
    path = "Condition"

    while path and len(patient_ids) < max_patients:
        data = cached_fhir_get(base, path, params=params)
        entries = data.get("entry", []) if isinstance(data, dict) else []
        for entry in entries:
            res = entry.get("resource", {})
            subject = res.get("subject", {})
            ref = subject.get("reference", "")
            if ref.startswith("Patient/"):
                pid = ref.replace("Patient/", "").strip()
                if pid and pid not in seen:
                    seen.add(pid)
                    patient_ids.append(pid)
                    if len(patient_ids) >= max_patients:
                        break

        # Check pagination
        next_url = None
        for link in data.get("link", []) if isinstance(data, dict) else []:
            if link.get("relation") == "next" and link.get("url"):
                next_url = link["url"]
                break

        if next_url and next_url.startswith(base):
            # Extract relative path and query
            rel = next_url[len(base):].lstrip("/")
            if "?" in rel:
                path, q_str = rel.split("?", 1)
                from urllib.parse import parse_qs
                params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(q_str).items()}
            else:
                path = rel
                params = None
        else:
            break

    return patient_ids


def inspect_candidate(base: str, patient_id: str) -> Optional[Dict[str, Any]]:
    """Inspects candidate for all requirements in Part A3."""
    # 1. Patient resource
    pat = cached_fhir_get(base, f"Patient/{patient_id}")
    if not pat or pat.get("resourceType") != "Patient":
        return None

    # Check deceased
    if pat.get("deceasedBoolean") is True or pat.get("deceasedDateTime"):
        return None

    age = parse_patient_age(pat.get("birthDate"))
    if age is None or age < 18:
        return None

    gender = pat.get("gender", "unknown")
    name_entry = pat.get("name", [{}])[0] if pat.get("name") else {}
    given = " ".join(name_entry.get("given", []))
    family = name_entry.get("family", "")
    full_name = f"{given} {family}".strip() or f"Patient {patient_id[:8]}"

    # Practitioner from Patient.generalPractitioner
    practitioner_name = None
    practitioner_ref = None
    gen_prac = pat.get("generalPractitioner", [])
    if gen_prac and isinstance(gen_prac, list) and gen_prac[0].get("reference"):
        ref = gen_prac[0]["reference"]
        practitioner_ref = ref
        if ref.startswith("Practitioner/"):
            prac_id = ref.replace("Practitioner/", "")
            prac_res = cached_fhir_get(base, f"Practitioner/{prac_id}")
            p_name = prac_res.get("name", [{}])[0] if prac_res.get("name") else {}
            practitioner_name = f"{' '.join(p_name.get('given', []))} {p_name.get('family', '')}".strip() or prac_id

    # 2. Conditions
    cond_bundle = cached_fhir_get(base, "Condition", params={"patient": patient_id, "_count": 50})
    cond_entries = cond_bundle.get("entry", []) if isinstance(cond_bundle, dict) else []
    conditions = []
    has_t2d = False
    has_htn = False
    for e in cond_entries:
        res = e.get("resource", {})
        code_concept = res.get("code", {})
        text = code_concept.get("text", "")
        codings = code_concept.get("coding", [])
        code_vals = {c.get("code") for c in codings}
        
        if "44054006" in code_vals or "diabetes" in text.lower():
            has_t2d = True
            if "Type 2 Diabetes" not in conditions:
                conditions.append("Type 2 Diabetes")
        if "59621000" in code_vals or "38341003" in code_vals or "hypertension" in text.lower():
            has_htn = True
            if "Hypertension" not in conditions:
                conditions.append("Hypertension")

    # 3. Encounters (for practitioner fallback if not in Patient.generalPractitioner)
    if not practitioner_name:
        enc_bundle = cached_fhir_get(base, "Encounter", params={"patient": patient_id, "_count": 1, "_sort": "-date"})
        enc_entries = enc_bundle.get("entry", []) if isinstance(enc_bundle, dict) else []
        if enc_entries:
            enc_res = enc_entries[0].get("resource", {})
            parts = enc_res.get("participant", [])
            for p in parts:
                ind = p.get("individual", {})
                ref = ind.get("reference", "")
                if ref.startswith("Practitioner/"):
                    practitioner_ref = ref
                    prac_id = ref.replace("Practitioner/", "")
                    prac_res = cached_fhir_get(base, f"Practitioner/{prac_id}")
                    p_name = prac_res.get("name", [{}])[0] if prac_res.get("name") else {}
                    practitioner_name = f"{' '.join(p_name.get('given', []))} {p_name.get('family', '')}".strip() or prac_id
                    break

    # 4. MedicationRequests
    med_bundle = cached_fhir_get(base, "MedicationRequest", params={"patient": patient_id, "_count": 50})
    med_entries = med_bundle.get("entry", []) if isinstance(med_bundle, dict) else []
    active_meds = []
    normalized_meds = []
    for e in med_entries:
        res = e.get("resource", {})
        status = res.get("status", "").lower()
        concept = res.get("medicationCodeableConcept", {})
        codings = concept.get("coding", [])
        med_name = concept.get("text") or (codings[0].get("display") if codings else "Medication")
        authored = res.get("authoredOn", "2020-01-01T00:00:00Z")
        
        if status == "active":
            active_meds.append(med_name)
            normalized_meds.append(
                NormalizedMedication(
                    patient_id=patient_id,
                    medication_name=med_name,
                    status="active",
                    dosage="As directed",
                    timestamp=authored,
                    source="fhir",
                    source_record_id=res.get("id", "med")
                )
            )

    in_scope_meds = select_chronic_care_medications(normalized_meds)
    in_scope_names = [m.medication_name for m in in_scope_meds]

    # 5. Observations (HbA1c, Glucose, BP)
    obs_bundle = cached_fhir_get(base, "Observation", params={"patient": patient_id, "_count": 100, "_sort": "-date"})
    obs_entries = obs_bundle.get("entry", []) if isinstance(obs_bundle, dict) else []
    
    latest_hba1c_date = None
    latest_glucose_date = None
    latest_bp_date = None

    for e in obs_entries:
        res = e.get("resource", {})
        dt = res.get("effectiveDateTime") or (res.get("effectivePeriod") or {}).get("start") or res.get("issued")
        codings = (res.get("code") or {}).get("coding", [])
        codes = {c.get("code") for c in codings}
        
        if not latest_hba1c_date and (codes & LOINC_HBA1C):
            latest_hba1c_date = dt
        if not latest_glucose_date and (codes & LOINC_GLUCOSE):
            latest_glucose_date = dt
        if not latest_bp_date and (codes & LOINC_BP):
            latest_bp_date = dt

    # 6. AllergyIntolerance
    allergy_bundle = cached_fhir_get(base, "AllergyIntolerance", params={"patient": patient_id, "_count": 50})
    allergy_entries = allergy_bundle.get("entry", []) if isinstance(allergy_bundle, dict) else []
    allergies = []
    for e in allergy_entries:
        res = e.get("resource", {})
        verif = (res.get("verificationStatus") or {}).get("coding", [{}])[0].get("code", "")
        if verif == "entered-in-error":
            continue
        substance = (res.get("code") or {}).get("text") or "Allergy"
        allergies.append(substance)

    # Usefulness score calculation
    score = 0.0
    if has_t2d and has_htn:
        score += 5.0
    elif has_t2d or has_htn:
        score += 3.0

    score += len(in_scope_names) * 2.0
    score += (len(active_meds) - len(in_scope_names)) * 0.5

    if latest_hba1c_date:
        score += 1.5
    if latest_glucose_date:
        score += 1.5
    if latest_bp_date:
        score += 1.5

    if practitioner_name:
        score += 2.0
    if allergies:
        score += 1.5
    if age >= 75:
        score += 1.0

    return {
        "id": patient_id,
        "name": full_name,
        "age": age,
        "gender": gender,
        "has_t2d": has_t2d,
        "has_htn": has_htn,
        "conditions": conditions,
        "active_med_count": len(active_meds),
        "in_scope_meds": in_scope_names,
        "latest_hba1c": latest_hba1c_date[:10] if latest_hba1c_date else None,
        "latest_glucose": latest_glucose_date[:10] if latest_glucose_date else None,
        "latest_bp": latest_bp_date[:10] if latest_bp_date else None,
        "practitioner": practitioner_name,
        "allergy_count": len(allergies),
        "allergies": allergies,
        "usefulness_score": round(score, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Find EHR Test Patients from SMART Sandbox")
    parser.add_argument("--base", default=DEFAULT_FHIR_BASE, help="FHIR R4 base URL")
    parser.add_argument("--max-patients", type=int, default=300, help="Max patients to collect from search")
    parser.add_argument("--limit-inspect", type=int, default=60, help="Max candidate patients to fully inspect")
    parser.add_argument("--out", default=None, help="Output JSON path")
    args = parser.parse_args()

    print(f"=== Searching SMART Sandbox ({args.base}) for T2D & HTN Patients ===")
    
    # 1. Search T2D
    t2d_ids = search_condition_patient_ids(args.base, SNOMED_T2D, max_patients=args.max_patients)
    print(f"Found {len(t2d_ids)} candidate IDs with T2D (SNOMED 44054006)")

    # 2. Search HTN (spec code 59621000)
    htn_spec_ids = search_condition_patient_ids(args.base, SNOMED_HTN_SPEC, max_patients=args.max_patients)
    print(f"Found {len(htn_spec_ids)} candidate IDs with HTN (SNOMED 59621000)")

    # 3. Search HTN (SMART sandbox code 38341003)
    htn_smart_ids = search_condition_patient_ids(args.base, SNOMED_HTN_SMART, max_patients=args.max_patients)
    print(f"Found {len(htn_smart_ids)} candidate IDs with HTN (SNOMED 38341003)")

    # Merge candidates
    all_candidate_ids = []
    seen = set()
    # Interleave to get good distribution
    max_len = max(len(t2d_ids), len(htn_spec_ids), len(htn_smart_ids))
    for i in range(max_len):
        if i < len(t2d_ids) and t2d_ids[i] not in seen:
            seen.add(t2d_ids[i])
            all_candidate_ids.append(t2d_ids[i])
        if i < len(htn_smart_ids) and htn_smart_ids[i] not in seen:
            seen.add(htn_smart_ids[i])
            all_candidate_ids.append(htn_smart_ids[i])
        if i < len(htn_spec_ids) and htn_spec_ids[i] not in seen:
            seen.add(htn_spec_ids[i])
            all_candidate_ids.append(htn_spec_ids[i])

    print(f"Total unique candidates to inspect: {len(all_candidate_ids)}")
    inspect_pool = all_candidate_ids[:args.limit_inspect]
    print(f"Inspecting top {len(inspect_pool)} candidates...")

    results = []
    for idx, pid in enumerate(inspect_pool, 1):
        try:
            cand = inspect_candidate(args.base, pid)
            if cand:
                results.append(cand)
                print(f"[{idx}/{len(inspect_pool)}] {pid}: score={cand['usefulness_score']} age={cand['age']} conds={cand['conditions']} meds={len(cand['in_scope_meds'])}")
            else:
                print(f"[{idx}/{len(inspect_pool)}] {pid}: skipped (age < 18, deceased, or unreadable)")
        except Exception as e:
            print(f"[{idx}/{len(inspect_pool)}] {pid}: error {e}")

    # Sort results by usefulness score descending
    results.sort(key=lambda x: x["usefulness_score"], reverse=True)

    print("\n" + "=" * 115)
    print(f"{'Patient ID':<38} {'Age':<4} {'Sex':<6} {'Conditions':<22} {'In-Scope Meds':<5} {'Latest BP':<11} {'Latest Gluc':<11} {'Practitioner':<18} {'Score':<5}")
    print("=" * 115)
    for r in results[:25]:
        cond_str = ", ".join(r["conditions"])
        prac_str = (r["practitioner"] or "None")[:17]
        bp_str = r["latest_bp"] or "None"
        glu_str = r["latest_glucose"] or "None"
        print(f"{r['id']:<38} {r['age']:<4} {r['gender']:<6} {cond_str:<22} {len(r['in_scope_meds']):<5} {bp_str:<11} {glu_str:<11} {prac_str:<18} {r['usefulness_score']:<5.1f}")
    print("=" * 115)

    out_path = args.out or os.path.join(get_cache_dir(), "candidate_patients.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} evaluated candidates to {out_path}")


if __name__ == "__main__":
    main()
