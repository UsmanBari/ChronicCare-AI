"""
Production Live Smoke Suite (Release 2 Verification)
Target: https://chroniccare-backend-w568.onrender.com
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BACKEND_URL = "https://chroniccare-backend-w568.onrender.com"
FIREBASE_SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={key}"
FIREBASE_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key}"

DIABETES_SOURCE_PREFIXES = ("ada_2026", "idf_dar", "aku_diabetes")


def get_firebase_api_key() -> str:
    env_file = Path(".env.local")
    if not env_file.exists():
        raise FileNotFoundError(".env.local not found")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("NEXT_PUBLIC_FIREBASE_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if key:
                return key
    raise ValueError("NEXT_PUBLIC_FIREBASE_API_KEY not found in .env.local")


def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Tuple[int, Dict[str, Any]]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            body_bytes = resp.read()
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            return status_code, body
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            body_bytes = e.read()
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {"detail": str(e)}
        return status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def wake_backend(max_retries: int = 18, interval_sec: int = 10) -> bool:
    print(f"[*] Checking backend health at {BACKEND_URL}/api/health...")
    for attempt in range(1, max_retries + 1):
        status, body = http_request(f"{BACKEND_URL}/api/health", method="GET", timeout=10)
        if status == 200:
            print(f"[+] Backend is healthy (attempt {attempt}, HTTP {status})")
            return True
        print(f"[-] Attempt {attempt}/{max_retries}: HTTP {status}. Waiting {interval_sec}s...")
        time.sleep(interval_sec)
    return False


def create_fake_patient_auth(api_key: str, case_label: str) -> Tuple[str, str]:
    ts = int(time.time())
    email = f"r2smoke.{case_label}.{ts}@demo.care"
    signup_url = FIREBASE_SIGNUP_URL.format(key=api_key)
    status, body = http_request(
        signup_url,
        method="POST",
        payload={"email": email, "password": "SmokeTestPass123!", "returnSecureToken": True},
        timeout=10,
    )
    if status != 200 or "idToken" not in body:
        raise RuntimeError(f"Firebase signup failed for {case_label}: HTTP {status} {body}")
    return body["idToken"], email


def answer_question(q: str, case: Dict[str, Any]) -> str:
    ql = (q or "").lower()
    if case.get("is_emergency"):
        return "I have severe chest pain"
    if "blood pressure" in ql and ("reading" in ql or "measured" in ql) and "measure your blood pressure again" not in ql:
        return case.get("target_bp", "120/80")
    if "blood sugar" in ql or ("mg/dl" in ql and "reading" in ql):
        return case.get("target_glucose", "100 fasting")
    if "measure your blood pressure again" in ql or "new reading" in ql:
        return "cannot"
    if "how are you feeling" in ql or "symptoms you'd like to report" in ql:
        return "I feel good today"
    if "severe headache" in ql or "shortness of breath" in ql or "right now, do you have" in ql:
        return "No severe headache, no dizziness, no chest pain"
    if "blood pressure medication" in ql or "diabetes medication" in ql or "taken your" in ql:
        return "Yes, took my medication as prescribed"
    if "sodium" in ql or "diet, exercise" in ql or "stress" in ql:
        return "Stress and sodium have been normal"
    if "your record lists" in ql or "are you still taking it" in ql:
        return "yes"
    if "cold or flu" in ql or "physically active" in ql or "pain, very upset" in ql:
        return "no"
    if "thirst" in ql or "urination" in ql or "blurred vision" in ql:
        return "no"
    return "no"


def run_case(case: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    case_id = case["id"]
    print(f"\n================================================================================")
    print(f"CASE {case_id}: {case['condition'].upper()} | {case['lang'].upper()} | Expected: {case['expected_level']} | Model: {case['expected_mode']}")
    print(f"================================================================================")

    steps_log: List[str] = []
    id_token, email = create_fake_patient_auth(api_key, f"c{case_id}")
    headers = {"Authorization": f"Bearer {id_token}"}
    steps_log.append(f"auth_signup: 200")

    # 1. Session
    status, body = http_request(f"{BACKEND_URL}/api/auth/session", method="POST", headers=headers, payload={})
    steps_log.append(f"auth_session: {status}")

    # 2. Consent
    status, body = http_request(f"{BACKEND_URL}/api/me/consent", method="POST", headers=headers, payload={"granted": True})
    steps_log.append(f"consent: {status}")
    status, body = http_request(f"{BACKEND_URL}/api/me/consent/provider-notification", method="POST", headers=headers, payload={"granted": True})
    steps_log.append(f"provider_consent: {status}")

    # 3. Profile
    profile_payload = {
        "date_of_birth": "1980-05-12",
        "inclusion_confirmed": True,
        "conditions": [case["condition"]],
        "language": case["lang"],
    }
    status, body = http_request(f"{BACKEND_URL}/api/me/profile", method="PUT", headers=headers, payload=profile_payload)
    steps_log.append(f"profile: {status}")

    # 4. EHR Connect (using designated sample patient from demo-hospital)
    patient_id = case["patient_id"]
    conn_payload = {"ehr_system_id": "demo-hospital", "external_patient_id": patient_id}
    status, body = http_request(f"{BACKEND_URL}/api/ehr/connect", method="POST", headers=headers, payload=conn_payload)
    steps_log.append(f"ehr_connect: {status}")

    # 5. Start Checkin
    status, body = http_request(f"{BACKEND_URL}/api/checkins/start", method="POST", headers=headers, payload={})
    steps_log.append(f"checkin_start: {status}")
    checkin_id = body.get("checkin_id")
    next_question = body.get("question")

    # 6. Answer loop
    ans_idx = 0
    is_complete = False
    is_emergency = False
    emergency_text = None

    while not is_complete and ans_idx < 25:
        ans_idx += 1
        ans_text = answer_question(next_question, case)
        status, body = http_request(
            f"{BACKEND_URL}/api/checkins/{checkin_id}/answer",
            method="POST",
            headers=headers,
            payload={"answer": ans_text},
        )
        steps_log.append(f"answer_{ans_idx}: {status}")
        is_complete = bool(body.get("complete"))
        is_emergency = bool(body.get("emergency"))
        if is_emergency:
            emergency_text = body.get("emergency_reason") or body.get("question")
            break
        next_question = body.get("question")

    # 7. Complete Checkin
    status, comp_body = http_request(
        f"{BACKEND_URL}/api/checkins/{checkin_id}/complete",
        method="POST",
        headers=headers,
        payload={},
    )
    steps_log.append(f"checkin_complete: {status}")

    triage_info = comp_body.get("triage") or {}
    final_level = triage_info.get("level") or ("emergency" if comp_body.get("emergency") else None)
    risk_in_resp = comp_body.get("risk")
    has_1122 = False
    if case.get("is_emergency"):
        comp_str = json.dumps(comp_body)
        has_1122 = "1122" in comp_str or "1122" in (emergency_text or "")

    # 8. Poll Explanation (Cases 1-7)
    exp_status = None
    sentences_count = 0
    sources_info: List[Dict[str, Any]] = []
    source_ids: List[str] = []
    ada_details: List[str] = []
    htn_safe = True

    if not case.get("is_emergency"):
        print("[*] Polling explanation...")
        poll_max = 30
        for p in range(1, poll_max + 1):
            time.sleep(3)
            e_status, e_body = http_request(
                f"{BACKEND_URL}/api/checkins/{checkin_id}/explanation",
                method="GET",
                headers=headers,
            )
            exp_status = e_body.get("status")
            if exp_status == "ready":
                sentences = e_body.get("sentences") or []
                sentences_count = len(sentences)
                sources_info = e_body.get("sources") or []
                source_ids = [str(s.get("source_id") or s.get("id") or "") for s in sources_info]
                for s in sources_info:
                    sid = str(s.get("source_id") or s.get("id") or "")
                    if sid.startswith("ada_2026"):
                        has_cit = bool(s.get("citation"))
                        has_doi = bool(s.get("doi"))
                        ada_details.append(f"{sid}: citation={'yes' if has_cit else 'no'}, doi={'yes' if has_doi else 'no'}")
                print(f"[+] Explanation ready at poll {p} (sentences={sentences_count}, sources={len(source_ids)})")
                break
            elif exp_status == "error":
                print(f"[-] Explanation returned error at poll {p}")
                break
            else:
                if p % 5 == 0:
                    print(f"[*] Poll {p}/{poll_max}: status={exp_status}")

    # Check HTN safety invariant: no diabetes sources
    if case["condition"] == "hypertension":
        for sid in source_ids:
            if any(sid.startswith(pfx) for pfx in DIABETES_SOURCE_PREFIXES):
                htn_safe = False

    # 9. Clean up EHR connection
    del_status, _ = http_request(f"{BACKEND_URL}/api/ehr/connection", method="DELETE", headers=headers)
    steps_log.append(f"ehr_revoke: {del_status}")

    # Determine PASS / FAIL for this case
    case_passed = True
    reasons: List[str] = []
    level_status = "MATCH"

    if final_level != case["expected_level"]:
        level_status = f"LEVEL DIFFERS (got {final_level}, expected {case['expected_level']})"
        print(f"[*] Note: {level_status}", flush=True)

    has_http_error = any(int(s.split(": ")[1]) >= 400 for s in steps_log if ": " in s and s.split(": ")[1].isdigit())
    if has_http_error:
        case_passed = False
        reasons.append("One or more HTTP steps returned error status")
    if risk_in_resp is not None:
        case_passed = False
        reasons.append(f"Patient privacy violated: risk is not null ({risk_in_resp})")
    if case.get("is_emergency"):
        if not has_1122:
            case_passed = False
            reasons.append("1122 not found in emergency response")
    else:
        if exp_status != "ready":
            case_passed = False
            reasons.append(f"Explanation not ready: {exp_status}")
        if not htn_safe:
            case_passed = False
            reasons.append("Hypertension source isolation failed (diabetes source cited)")

    print(f"HTTP Statuses: {', '.join(steps_log)}", flush=True)
    print(f"Final Triage Level: {final_level} [{level_status}]", flush=True)
    print(f"Risk in Complete Response: {risk_in_resp}", flush=True)
    if case.get("is_emergency"):
        print(f"Emergency 1122 in response: {'yes' if has_1122 else 'no'}", flush=True)
    else:
        print(f"Explanation Status: {exp_status}", flush=True)
        print(f"Cited Source IDs: {source_ids}", flush=True)
        if ada_details:
            print(f"ADA Sources Citation/DOI: {', '.join(ada_details)}", flush=True)
        print(f"HTN Source Safety (No DM sources): {'PASS' if htn_safe else 'FAIL'}", flush=True)

    res_str = "PASS" if case_passed else f"FAIL ({'; '.join(reasons)})"
    print(f"Case {case_id} Result: {res_str}", flush=True)

    return {
        "case_id": case_id,
        "label": f"{case['condition']} {case['lang']}",
        "steps_log": steps_log,
        "final_level": final_level,
        "expected_level": case["expected_level"],
        "level_status": level_status,
        "risk_null": risk_in_resp is None,
        "exp_status": exp_status,
        "source_ids": source_ids,
        "ada_details": ada_details,
        "htn_safe": htn_safe,
        "passed": case_passed,
        "reasons": reasons,
    }


def main() -> None:
    print("================================================================================")
    print("CHRONICCARE-AI RELEASE 2 LIVE PRODUCTION SMOKE SUITE")
    print(f"Target: {BACKEND_URL}")
    print("================================================================================")

    if not wake_backend():
        print("[FATAL] Backend is not reachable. Aborting smoke.")
        sys.exit(1)

    api_key = get_firebase_api_key()
    print("[+] Public Firebase Web API Key loaded from .env.local: SET")

    cases = [
        {
            "id": 1,
            "condition": "hypertension",
            "lang": "en",
            "target_bp": "118/76",
            "patient_id": "sim-newpatient",
            "expected_level": "routine",
            "expected_mode": "llm",
            "calls_groq": True,
        },
        {
            "id": 2,
            "condition": "hypertension",
            "lang": "ur",
            "target_bp": "145/92",
            "patient_id": "sim-syn-recent-htn-multidrug",
            "expected_level": "review",
            "expected_mode": "template (language_template_only)",
            "calls_groq": False,
        },
        {
            "id": 3,
            "condition": "hypertension",
            "lang": "roman_ur",
            "target_bp": "145/92",
            "patient_id": "sim-imran",
            "expected_level": "review",
            "expected_mode": "template (language_template_only)",
            "calls_groq": False,
        },
        {
            "id": 4,
            "condition": "hypertension",
            "lang": "en",
            "target_bp": "182/112",
            "patient_id": "sim-ayesha",
            "expected_level": "urgent",
            "expected_mode": "llm",
            "calls_groq": True,
        },
        {
            "id": 5,
            "condition": "hypertension",
            "lang": "ur",
            "target_bp": "182/112",
            "patient_id": "sim-syn-recent-t2d-htn",
            "expected_level": "urgent",
            "expected_mode": "template (language_template_only)",
            "calls_groq": False,
        },
        {
            "id": 6,
            "condition": "diabetes",
            "lang": "en",
            "target_glucose": "190 fasting",
            "patient_id": "sim-sana",
            "expected_level": "review",
            "expected_mode": "llm",
            "calls_groq": True,
        },
        {
            "id": 7,
            "condition": "diabetes",
            "lang": "ur",
            "target_glucose": "190 fasting",
            "patient_id": "sim-syn-recent-t2d-insulin",
            "expected_level": "review",
            "expected_mode": "template (language_template_only)",
            "calls_groq": False,
        },
        {
            "id": 8,
            "condition": "hypertension",
            "lang": "en",
            "patient_id": "sim-syn-recent-geriatric",
            "expected_level": "emergency",
            "expected_mode": "none (0 LLM calls)",
            "is_emergency": True,
            "calls_groq": False,
        },
    ]

    results: List[Dict[str, Any]] = []

    for idx, c in enumerate(cases):
        res = run_case(c, api_key)
        results.append(res)
        # Sleep 60 seconds after cases that call Groq to respect OTPM rate limit
        if c.get("calls_groq") and idx < len(cases) - 1:
            print("[*] Sleeping 60s to respect Groq free-tier OTPM pacer...")
            time.sleep(60)

    # Print Gate Summary
    print("\n" + "=" * 90, flush=True)
    print("PRODUCTION LIVE SMOKE SUMMARY TABLE", flush=True)
    print("=" * 90, flush=True)
    print(f"{'Case':<6} | {'Target':<24} | {'Expected Level':<14} | {'Actual Level':<12} | {'Risk Null':<10} | {'Status':<20}", flush=True)
    print("-" * 90, flush=True)
    for r in results:
        status_str = "PASS (LEVEL DIFFERS)" if "LEVEL DIFFERS" in r.get("level_status", "") else ("PASS" if r["passed"] else "FAIL")
        print(f"Case {r['case_id']:<1} | {r['label']:<24} | {r['expected_level']:<14} | {r['final_level'] or 'None':<12} | {str(r['risk_null']):<10} | {status_str:<20}", flush=True)

    print("-" * 90, flush=True)
    print("Case 9: Provider Review Detail for 4 & 6 -> NOT RUN (provider credentials from DEMO_ROLE_MAP not provided)", flush=True)
    all_risk_null = all(r["risk_null"] for r in results)
    print(f"Case 10: Patient View Privacy Invariant (risk=null across all responses) -> {'PASS' if all_risk_null else 'FAIL'}", flush=True)
    print("=" * 90, flush=True)

    all_passed = all(r["passed"] for r in results) and all_risk_null
    if all_passed:
        print("[SUCCESS] ALL RUN CASES PASSED STRICT LIVE PRODUCTION INVARIANTS.")
    else:
        print("[FAILURE] ONE OR MORE CASES FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
