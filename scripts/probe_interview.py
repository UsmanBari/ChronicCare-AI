#!/usr/bin/env python3
"""
scripts/probe_interview.py: In-process probe runner for Adaptive Interview v2 vs v3.

Executes scripted check-ins in-process using FastAPI TestClient against an isolated
hermetic SQLite database, generating structured turn-by-turn audits in Markdown and JSON.
Answers are keyed by question/step ID with kind-based defaults and must_deliver validation.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Ensure backend directory is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import jwt
from auth import firebase_verify
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from data_sources import app_store, local_store
from fastapi.testclient import TestClient
from main import app

TEST_PROJECT_ID = "probe-chroniccare-ai"
TEST_KID = "probe-key-1"

PREFIXES = [
    "diabetes_", "hypertension_", "core_", "insulin_",
    "fasting_", "sick_", "barrier_", "wellbeing_", "caregiver_"
]

ALIASES: dict[str, list[str]] = {
    "glucose_reading": ["diabetes_glucose_reading"],
    "bp_reading": ["hypertension_bp_reading"],
    "adherence": ["diabetes_adherence", "hypertension_adherence", "adherence_diabetes", "adherence_hypertension"],
    "lifestyle": ["diabetes_lifestyle", "hypertension_lifestyle", "lifestyle_diabetes", "lifestyle_hypertension"],
    "greeting": ["core_greeting"],
    "summary_confirmation": ["core_summary_confirm"],
    "hypo_events_past_week": ["insulin_hypo_events_past_week", "hypoglycemia_symptoms"],
    "hypo_symptoms_acute": ["insulin_hypo_symptoms_acute", "hypoglycemia_symptoms"],
    "sick_day_flags": ["sick_vomiting_diarrhea"],
    "is_fasting_today": ["fasting_is_fasting"],
    "foot_problems": ["diabetes_foot_problems"],
    "hyperglycemia_symptoms": ["diabetes_hyperglycemia_symptoms"],
    "associated_symptoms": ["hypertension_associated_symptoms"],
}


PROTOCOL_BENIGN_DEFAULTS = {
    "neuro": "no",
    "orientation": "yes",
    "can_swallow": "yes",
    "symptoms": "no",
    "thirst": "no",
    "orthostatic": "no",
    "falls": "no",
    "context": "no",
    "chest_pain": "no",
    "shortness_of_breath": "no",
    "severe_headache": "no",
    "vision_changes": "no",
    "weakness_numbness": "no",
}

def get_step_candidates(step_id: str) -> list[str]:
    """Generates candidate keys and aliases for a given step ID."""
    cands = [step_id]
    for pref in PREFIXES:
        if step_id.startswith(pref):
            stripped = step_id[len(pref):]
            if stripped not in cands:
                cands.append(stripped)
    for k, alias_list in ALIASES.items():
        if step_id == k or step_id in alias_list:
            if k not in cands:
                cands.append(k)
            for a in alias_list:
                if a not in cands:
                    cands.append(a)
    return cands


def step_matches_pattern(step_id: str, pattern: str) -> bool:
    """Checks if step_id or any of its candidates match pattern (including wildcards)."""
    if fnmatch.fnmatch(step_id, pattern):
        return True
    for c in get_step_candidates(step_id):
        if fnmatch.fnmatch(c, pattern):
            return True
    return False


def detect_question_kind(step_id: str, options: list[str] | None) -> str:
    """
    Detects question kind ('yes_no', 'choice', 'number', 'free_text') from API response metadata.
    
    Detection Rules:
    1. If options is non-empty:
       - If all options are boolean terms (yes/no, haan/nahi, ji/na, true/false, Urdu script), kind = 'yes_no'.
       - Else (e.g. unit choices ['mmol/L', 'mg/dL'], meal contexts, PHQ-9 frequencies), kind = 'choice'.
    2. If options is empty/None:
       - If step_id contains 'reading' or 'blood_sugar' or 'bp' (excluding 'context'/'technique'), kind = 'number'.
       - If step_id starts with 'triage:' or contains 'symptoms', 'adherence', 'technique', 'confirm', 'fasting', 'sick', 'foot': kind = 'yes_no'.
       - Otherwise, kind = 'free_text' (e.g. greeting, lifestyle, notes, checkpoints).
    """
    if options:
        lower_opts = [str(o).strip().lower() for o in options]
        boolean_terms = {
            "yes", "no", "haan", "nahi", "nahin", "ji", "jee", "jee haan",
            "true", "false", "ہاں", "نہیں", "جی", "جی ہاں"
        }
        if set(lower_opts).issubset(boolean_terms):
            return "yes_no"
        return "choice"
    
    # Options is None/empty
    s_lower = step_id.lower()
    if any(k in s_lower for k in ["reading", "blood_sugar", "bp"]) and not any(k in s_lower for k in ["context", "technique"]):
        return "number"
    if s_lower.startswith("triage:") or any(k in s_lower for k in ["symptoms", "adherence", "technique", "confirm", "fasting", "sick", "foot"]):
        return "yes_no"
    return "free_text"


def resolve_answer(
    step_id: str,
    question_text: str,
    options: list[str] | None,
    scenario: dict[str, Any]
) -> tuple[str, str, str | None]:
    """
    Resolves the answer to send for the current turn and determines its source.
    Returns: (answer_string, answer_source, matched_key)
    answer_source is one of: 'step_map', 'kind_default', 'fallback'.
    """
    answers_by_step = scenario.get("answers_by_step", {})
    defaults_by_kind = scenario.get("defaults_by_kind", {})
    
    # E2: Unit clarification turn detection (options ["mmol/L", "mg/dL"])
    if options and set(options) == {"mmol/L", "mg/dL"}:
        if "glucose_unit_clarify" in answers_by_step:
            return str(answers_by_step["glucose_unit_clarify"]), "step_map", "glucose_unit_clarify"
    
    # 1. Exact step_id match
    if step_id in answers_by_step:
        return str(answers_by_step[step_id]), "step_map", step_id

    # Detect protocol step key from question_text or step_id
    q_low = (question_text or "").lower()
    proto_key = None
    if "oriented in time" in q_low:
        proto_key = "orientation"
    elif "swallow and eat or drink" in q_low:
        proto_key = "can_swallow"
    elif "confused, very drowsy" in q_low:
        proto_key = "neuro"
    elif "shaky, sweaty" in q_low or "pounding heartbeat" in q_low:
        proto_key = "symptoms"
    elif "thirsty and passing urine" in q_low:
        proto_key = "thirst"
    elif "dizzy or faint when you stand" in q_low:
        proto_key = "orthostatic"
    elif "fallen or nearly fallen" in q_low:
        proto_key = "falls"
    elif "chest pain, shortness of breath" in q_low:
        proto_key = "symptoms"
    elif "mild headache, dizziness" in q_low:
        proto_key = "symptoms"
    elif "rest for at least 5 minutes" in q_low:
        proto_key = "context"
    elif "did this reading happen" in q_low:
        proto_key = "context"

    if not proto_key and step_id.startswith("triage:"):
        parts = step_id.split(":")
        if parts[-1] in PROTOCOL_BENIGN_DEFAULTS:
            proto_key = parts[-1]
        elif len(parts) >= 2 and parts[1] in PROTOCOL_BENIGN_DEFAULTS:
            proto_key = parts[1]
    if not proto_key:
        for c in get_step_candidates(step_id):
            if c in PROTOCOL_BENIGN_DEFAULTS:
                proto_key = c
                break

    # 2. Specific protocol key in answers_by_step takes precedence over wildcards
    if proto_key and proto_key in answers_by_step:
        return str(answers_by_step[proto_key]), "step_map", proto_key

    # 3. Canonical candidate / alias match
    cands = get_step_candidates(step_id)
    for c in cands:
        if c in answers_by_step:
            return str(answers_by_step[c]), "step_map", c

    # 4. Wildcard pattern match in answers_by_step
    for pattern, ans in answers_by_step.items():
        if ("*" in pattern or "?" in pattern) and step_matches_pattern(step_id, pattern):
            return str(ans), "step_map", pattern

    # 5. Benign protocol default
    if proto_key and proto_key in PROTOCOL_BENIGN_DEFAULTS:
        return str(PROTOCOL_BENIGN_DEFAULTS[proto_key]), "protocol_default", None

    # 4. Defaults by kind
    kind = detect_question_kind(step_id, options)
    if kind == "choice" and options:
        def_choice = defaults_by_kind.get("choice", "<first option>")
        if def_choice in ["<first option>", "<first_option>", "first"]:
            return str(options[0]), "kind_default", None
        return str(def_choice), "kind_default", None
    elif kind in defaults_by_kind:
        return str(defaults_by_kind[kind]), "kind_default", None
        
    # 5. Safe fallback
    if kind == "yes_no":
        return "no", "fallback", None
    elif kind == "number":
        return "skip", "fallback", None
    elif kind == "choice" and options:
        return str(options[0]), "fallback", None
    return "none", "fallback", None


def generate_rsa_key_and_cert():
    """Generates a deterministic RSA keypair and self-signed certificate for hermetic token verification."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(1234567890)
        .not_valid_before(datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.UTC))
        .not_valid_after(datetime.datetime(2030, 1, 1, 0, 0, 0, tzinfo=datetime.UTC))
        .sign(private_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return private_key, cert_pem


def create_token(private_key, user_id: str, email: str) -> str:
    fixed_now = 1793000000
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "name": "Probe Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": fixed_now,
        "exp": fixed_now + 360000,
        "auth_time": fixed_now,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": TEST_KID})


def setup_fresh_patient(client: TestClient, token: str, scenario: dict[str, Any], user_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    
    # Grant both consents
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    
    # Calculate DOB based on age (default 45)
    age = scenario.get("age", 45)
    target_year = 2026 - int(age)
    dob = f"{target_year}-05-15"
    
    # Set profile (PUT /api/me/profile requires language in {'en', 'ur'})
    scen_lang = scenario.get("language", "en")
    api_lang = "ur" if scen_lang == "ur" else "en"
    
    resp = client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": scenario.get("conditions", ["diabetes"]),
            "language": api_lang,
            "on_insulin_or_sulfonylurea": bool(scenario.get("on_insulin", False)),
            "date_of_birth": dob,
            "inclusion_confirmed": True,
            "sex_at_birth": scenario.get("sex_at_birth", "female"),
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Profile creation failed: {resp.status_code} - {resp.text}")

    # If the scenario tests roman_ur, update the database profile row directly so
    # the checkin start logic can read language='roman_ur'
    if scen_lang == "roman_ur":
        with app_store.get_db_cursor(backend="sqlite", db_path=os.environ.get("LOCAL_DB_PATH")) as (cur, _be, ph):
            cur.execute(f"UPDATE patient_profiles SET language = 'roman_ur' WHERE user_id = {ph}", (user_id,))


def run_scenario_on_engine(client: TestClient, private_key, scenario: dict[str, Any], engine: str) -> dict[str, Any]:
    det_tag = hashlib.sha256(f"{scenario['name']}-{engine}".encode()).hexdigest()[:8]
    user_id = f"probe-{scenario['name']}-{engine}-{det_tag}"
    email = f"{user_id}@probe.test"
    token = create_token(private_key, user_id, email)
    headers = {"Authorization": f"Bearer {token}"}
    
    must_deliver = scenario.get("must_deliver", [])
    answers_by_step = scenario.get("answers_by_step", {})
    used_mapped_keys: set[str] = set()
    delivered_must_steps: set[str] = set()
    
    try:
        setup_fresh_patient(client, token, scenario, user_id)
    except Exception as e:  # noqa: BLE001
        return {
            "scenario": scenario["name"],
            "group": scenario.get("group", ""),
            "engine": engine,
            "is_valid": False,
            "must_deliver": must_deliver,
            "unfulfilled_must_deliver": list(must_deliver),
            "unmapped_answers": list(answers_by_step.keys()),
            "turns": [],
            "questions_asked": 0,
            "final_level": "ERROR_BOOTSTRAP",
            "emergency": False,
            "complete_result": None,
            "notes": f"Setup failed: {e!s}"
        }
    
    # Set interview engine dynamically
    old_engine = os.environ.get("INTERVIEW_ENGINE")
    os.environ["INTERVIEW_ENGINE"] = engine
    
    turns: list[dict[str, Any]] = []
    notes: list[str] = []
    
    try:
        # Start checkin
        resp = client.post("/api/checkins/start", headers=headers)
        if resp.status_code != 200:
            notes.append(f"Failed to start check-in: {resp.status_code} - {resp.text}")
            return {
                "scenario": scenario["name"],
                "group": scenario.get("group", ""),
                "engine": engine,
                "is_valid": False,
                "must_deliver": must_deliver,
                "unfulfilled_must_deliver": list(must_deliver),
                "unmapped_answers": list(answers_by_step.keys()),
                "turns": turns,
                "questions_asked": 0,
                "final_level": "ERROR",
                "emergency": False,
                "complete_result": None,
                "notes": "; ".join(notes)
            }
        
        data = resp.json()
        checkin_id = data["checkin_id"]
        current_step = data.get("step")
        current_question = data.get("question")
        why_text = data.get("why_text")
        options = data.get("options")
        can_skip = data.get("can_skip")
        system_note = data.get("system_note")
        progress_hint = data.get("progress_hint")
        
        turn_num = 1
        is_emergency = False
        is_complete = False
        
        while turn_num <= 25:
            # Resolve answer by step
            answer, answer_source, matched_key = resolve_answer(
                current_step, current_question, options, scenario
            )
            if matched_key:
                used_mapped_keys.add(matched_key)
                
            # Track delivery of must_deliver targets
            if answer_source == "step_map":
                for req in must_deliver:
                    if step_matches_pattern(current_step, req):
                        delivered_must_steps.add(req)
                for k in answers_by_step:
                    if step_matches_pattern(current_step, k):
                        used_mapped_keys.add(k)
            
            # Send answer
            ans_payload = {"answer": str(answer), "step": current_step}
            ans_resp = client.post(f"/api/checkins/{checkin_id}/answer", headers=headers, json=ans_payload)
            
            turn_record = {
                "turn": turn_num,
                "step_id": current_step,
                "question_text": current_question,
                "why_text": why_text,
                "options": options,
                "can_skip": can_skip,
                "progress_hint": progress_hint,
                "answer_sent": answer,
                "answer_source": answer_source,
                "matched_key": matched_key,
                "system_note": system_note,
                "status_code": ans_resp.status_code,
            }
            
            if ans_resp.status_code != 200:
                turn_record["error"] = ans_resp.text
                turns.append(turn_record)
                notes.append(f"Turn {turn_num} received HTTP {ans_resp.status_code}")
                break
            
            ans_data = ans_resp.json()
            is_emergency = bool(ans_data.get("emergency"))
            is_complete = bool(ans_data.get("complete"))
            turn_record["complete"] = is_complete
            turn_record["emergency"] = is_emergency
            turn_record["system_note"] = ans_data.get("system_note")
            turns.append(turn_record)
            
            if is_emergency:
                notes.append("Emergency triggered during turn")
                break
            if is_complete:
                break
            
            # Next turn data
            current_step = ans_data.get("step")
            current_question = ans_data.get("question")
            why_text = ans_data.get("why_text")
            options = ans_data.get("options")
            can_skip = ans_data.get("can_skip")
            system_note = ans_data.get("system_note")
            progress_hint = ans_data.get("progress_hint")
            turn_num += 1
            
        final_level = "EMERGENCY" if is_emergency else "IN_PROGRESS"
        complete_result = None
        
        if not is_emergency:
            comp_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers=headers)
            if comp_resp.status_code == 200:
                complete_result = comp_resp.json()
                triage = complete_result.get("triage") or {}
                final_level = triage.get("level") or ("review" if complete_result.get("requires_review") else "routine")
            else:
                notes.append(f"/complete failed with {comp_resp.status_code}: {comp_resp.text}")
                final_level = f"ERR_{comp_resp.status_code}"
                
        # Validate must_deliver
        unfulfilled = [req for req in must_deliver if req not in delivered_must_steps]
        is_valid = (len(unfulfilled) == 0)
        if not is_valid:
            notes.append(f"INVALID: must_deliver {unfulfilled} not delivered via step_map")
            
        # Unmapped answers
        unmapped_keys = [k for k in answers_by_step if k not in used_mapped_keys]
                
        return {
            "scenario": scenario["name"],
            "group": scenario.get("group", ""),
            "engine": engine,
            "is_valid": is_valid,
            "must_deliver": must_deliver,
            "unfulfilled_must_deliver": unfulfilled,
            "unmapped_answers": unmapped_keys,
            "turns": turns,
            "questions_asked": len(turns),
            "final_level": final_level,
            "emergency": is_emergency,
            "complete_result": complete_result,
            "notes": "; ".join(notes) if notes else "Valid normal completion"
        }
        
    finally:
        if old_engine is not None:
            os.environ["INTERVIEW_ENGINE"] = old_engine
        else:
            os.environ.pop("INTERVIEW_ENGINE", None)


def sanitize_for_determinism(data: Any) -> Any:
    """Recursively replaces runtime timestamps and timestamp-derived record IDs with canonical fixed values."""
    if isinstance(data, dict):
        new_d = {}
        for k, v in data.items():
            if k in ["timestamp", "timestamp_b", "completed_at", "created_at"] and isinstance(v, str):
                new_d[k] = "2026-10-27T12:00:00Z"
            elif k in ["source_record_id_b", "source_record_id"] and isinstance(v, str) and v.startswith("CHECKIN-"):
                parts = v.split("-")
                new_d[k] = "-".join(parts[:-2] + ["STAMP", parts[-1]])
            else:
                new_d[k] = sanitize_for_determinism(v)
        return new_d
    elif isinstance(data, list):
        return [sanitize_for_determinism(item) for item in data]
    return data


def build_markdown_report(results: list[dict[str, Any]]) -> str:
    lines = []
    lines.append("# ChronicCare AI — Interview Probe Audit Report (Day 1b: Step-Keyed Answers)\n")
    lines.append("**Audit Execution:** Hermetic in-process TestClient evaluation")
    lines.append(f"**Total Executions:** {len(results)}")
    
    # Engine validity metrics
    v2_runs = [r for r in results if r["engine"] == "v2"]
    v3_runs = [r for r in results if r["engine"] == "v3"]
    v2_valid = sum(1 for r in v2_runs if r["is_valid"])
    v3_valid = sum(1 for r in v3_runs if r["is_valid"])
    
    lines.append(f"- **Engine v2 Valid:** {v2_valid}/{len(v2_runs)} ({len(v2_runs) - v2_valid} INVALID)")
    lines.append(f"- **Engine v3 Valid:** {v3_valid}/{len(v3_runs)} ({len(v3_runs) - v3_valid} INVALID)\n")
    
    # Top-level Summary Table
    lines.append("## Summary Table\n")
    lines.append("| Scenario | Engine | Group | Status | Questions Asked | Final Level | Emergency | Unmapped Answers | Notes |")
    lines.append("|---|---|:---:|:---:|:---:|:---:|:---:|---|---|")
    for r in results:
        scen = r["scenario"]
        eng = r["engine"]
        grp = r["group"]
        status_str = "VALID" if r["is_valid"] else "**INVALID**"
        q_count = r["questions_asked"]
        lvl = r["final_level"]
        emerg = "YES" if r["emergency"] else "No"
        unmapped = ", ".join(r.get("unmapped_answers") or []) or "-"
        note = r["notes"]
        lines.append(f"| `{scen}` | **{eng}** | {grp} | {status_str} | {q_count} | `{lvl}` | {emerg} | {unmapped} | {note} |")
    
    lines.append("\n---\n")
    lines.append("## Detailed Scenario Audits\n")
    
    for r in results:
        scen = r["scenario"]
        eng = r["engine"]
        status_str = "VALID" if r["is_valid"] else "INVALID"
        lines.append(f"### Scenario: `{scen}` (Engine: {eng.upper()}) — Status: {status_str}\n")
        lines.append(f"- **Group:** {r['group']}")
        lines.append(f"- **Valid Delivery:** `{r['is_valid']}` (must_deliver: {r['must_deliver']})")
        lines.append(f"- **Final Level:** `{r['final_level']}`")
        lines.append(f"- **Emergency:** {r['emergency']}")
        lines.append(f"- **Unmapped Answers:** {r.get('unmapped_answers') or 'None'}")
        lines.append(f"- **Notes:** {r['notes']}\n")
        
        if r["turns"]:
            lines.append("| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |")
            lines.append("|:---:|---|---|---|:---:|---|---|---|")
            for t in r["turns"]:
                t_num = t["turn"]
                step = t.get("step_id") or ""
                q_text = (t.get("question_text") or "").replace("|", "\\|").replace("\n", " ")
                ans = str(t.get("answer_sent") or "").replace("|", "\\|").replace("\n", " ")
                src = t.get("answer_source", "-")
                opts = ", ".join(str(o) for o in (t.get("options") or []))
                why = (t.get("why_text") or "").replace("|", "\\|")
                flags = []
                if t.get("emergency"):
                    flags.append("🚨 EMERGENCY")
                if t.get("complete"):
                    flags.append("✅ COMPLETE")
                if t.get("system_note"):
                    flags.append(f"Note: {t['system_note']}")
                flag_str = "; ".join(flags) if flags else "-"
                lines.append(f"| {t_num} | `{step}` | {q_text} | {ans} | `{src}` | {opts} | {why} | {flag_str} |")
            lines.append("")
            
        if r.get("complete_result"):
            cr = r["complete_result"]
            triage = cr.get("triage") or {}
            reasons = ", ".join(triage.get("reasons") or [])
            factors = ", ".join(triage.get("factors") or [])
            req_rev = cr.get("requires_review")
            max_sev = cr.get("max_severity")
            lines.append("**Completion Result Details:**")
            lines.append(f"- Requires Review: `{req_rev}` | Max Severity: `{max_sev}`")
            lines.append(f"- Reasons: {reasons if reasons else 'None'}")
            lines.append(f"- Factors: {factors if factors else 'None'}")
            if cr.get("intakes"):
                intake_summaries = []
                for itk in cr["intakes"]:
                    obs_t = itk.get("observation_type")
                    conf = itk.get("confidence_label") or itk.get("confidence")
                    ans_by = itk.get("answered_by", "patient")
                    intake_summaries.append(f"{obs_t} (conf: {conf}, by: {ans_by})")
                lines.append(f"- Intakes: {'; '.join(intake_summaries)}")
            lines.append("")
        lines.append("---\n")
        
    return "\n".join(lines)


def run_invalid_check_demo():
    """Unit check to demonstrate INVALID detection works (HC1 requirement)."""
    print("Running HC1 Unit Check for INVALID detection...")
    temp_dir = tempfile.mkdtemp(prefix="probe_hc1_check_")
    temp_db_path = str(Path(temp_dir) / "probe_hc1.db")
    os.environ["LOCAL_DB_PATH"] = temp_db_path
    os.environ["DB_BACKEND"] = "sqlite"
    os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID
    app_store.migrate(db_path=temp_db_path, backend="sqlite")
    local_store.init_db(db_path=temp_db_path)
    
    private_key, cert_pem = generate_rsa_key_and_cert()
    mock_keys = {TEST_KID: cert_pem}
    firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 86400}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys
    client = TestClient(app)
    
    # Deliberately broken scenario: requires "target_step_that_never_exists"
    broken_scenario = {
        "name": "unit_check_broken_scenario",
        "group": "unit_check",
        "conditions": ["diabetes"],
        "language": "en",
        "answers_by_step": {"greeting": "hello"},
        "defaults_by_kind": {"yes_no": "no", "number": "skip", "choice": "<first option>", "free_text": "none"},
        "must_deliver": ["target_step_that_never_exists"],
        "what_we_are_testing": "Proving that an unfulfilled must_deliver step marks the scenario INVALID"
    }
    
    result = run_scenario_on_engine(client, private_key, broken_scenario, "v2")
    assert result["is_valid"] is False, "Expected scenario to be flagged INVALID"
    assert "target_step_that_never_exists" in result["unfulfilled_must_deliver"], "Expected target step in unfulfilled"
    print(f"  [HC1 VERIFIED] Broken scenario successfully flagged as INVALID: is_valid={result['is_valid']}, unfulfilled={result['unfulfilled_must_deliver']}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="ChronicCare AI Adaptive Interview Probe Tool")
    parser.add_argument("--engine", choices=["v2", "v3", "both"], default="both", help="Interview engine to evaluate")
    parser.add_argument("--scenario", default="all", help="Scenario name from probe_scenarios.json or 'all'")
    parser.add_argument("--out", required=False, help="Path to output markdown report file")
    parser.add_argument("--json", required=False, help="Path to output JSON audit file")
    parser.add_argument("--check-invalid", action="store_true", help="Run HC1 unit check demonstrating INVALID detection")
    args = parser.parse_args()
    
    if args.check_invalid:
        run_invalid_check_demo()
        return

    if not args.out:
        print("Error: --out is required when running audit.", file=sys.stderr)
        sys.exit(1)
        
    # Load scenarios
    scenarios_file = REPO_ROOT / "scripts" / "probe_scenarios.json"
    if not scenarios_file.exists():
        print(f"Error: {scenarios_file} not found.", file=sys.stderr)
        sys.exit(1)
        
    with open(scenarios_file, "r", encoding="utf-8") as f:
        all_scenarios = json.load(f)
        
    if args.scenario != "all":
        selected_scenarios = [s for s in all_scenarios if s["name"] == args.scenario]
        if not selected_scenarios:
            print(f"Error: scenario '{args.scenario}' not found in {scenarios_file}", file=sys.stderr)
            sys.exit(1)
    else:
        selected_scenarios = all_scenarios
        
    engines_to_run = ["v2", "v3"] if args.engine == "both" else [args.engine]
    
    # Create isolated temp database
    temp_dir = tempfile.mkdtemp(prefix="chroniccare_probe_")
    temp_db_path = str(Path(temp_dir) / "probe_hermetic.db")
    
    old_db_path = os.environ.get("LOCAL_DB_PATH")
    old_db_backend = os.environ.get("DB_BACKEND")
    old_proj_id = os.environ.get("FIREBASE_PROJECT_ID")
    
    os.environ["LOCAL_DB_PATH"] = temp_db_path
    os.environ["DB_BACKEND"] = "sqlite"
    os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID
    
    # Initialize DB schemas
    app_store.migrate(db_path=temp_db_path, backend="sqlite")
    local_store.init_db(db_path=temp_db_path)
    
    # Generate cryptographic keys
    private_key, cert_pem = generate_rsa_key_and_cert()
    mock_keys = {TEST_KID: cert_pem}
    firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 86400}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys
    
    client = TestClient(app)
    
    results = []
    total = len(selected_scenarios) * len(engines_to_run)
    idx = 0
    
    print(f"Starting interview probe audit: {total} runs across {len(selected_scenarios)} scenarios...")
    
    try:
        for scen in selected_scenarios:
            for eng in engines_to_run:
                idx += 1
                res = run_scenario_on_engine(client, private_key, scen, eng)
                results.append(res)
                if idx % 10 == 0 or idx == total:
                    valid_tag = "VALID" if res["is_valid"] else "INVALID"
                    print(f"[{idx}/{total}] Probed: {scen['name']} ({eng}) -> [{valid_tag}] Level: {res['final_level']} (Emerg: {res['emergency']})")
    finally:
        # Write Markdown output first
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = build_markdown_report(results)
        out_path.write_text(md_content, encoding="utf-8")
        print(f"Wrote Markdown report to {out_path} ({len(md_content)} chars)")
        
        # Write JSON output compact and sanitized for deterministic hashes (FIX 3 + HC2)
        if args.json:
            json_path = Path(args.json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            sanitized_results = sanitize_for_determinism(results)
            compact_json = json.dumps(sanitized_results, separators=(',', ':'), ensure_ascii=False)
            json_path.write_text(compact_json, encoding="utf-8")
            print(f"Wrote compact JSON trace to {json_path} ({len(compact_json)} bytes)")
            
        # Clean up temp db
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:  # noqa: BLE001, S110
            pass
            
        if old_db_path:
            os.environ["LOCAL_DB_PATH"] = old_db_path
        if old_db_backend:
            os.environ["DB_BACKEND"] = old_db_backend
        if old_proj_id:
            os.environ["FIREBASE_PROJECT_ID"] = old_proj_id


if __name__ == "__main__":
    main()
