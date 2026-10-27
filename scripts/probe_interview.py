#!/usr/bin/env python3
"""
scripts/probe_interview.py: In-process probe runner for Adaptive Interview v2 vs v3.

Executes scripted check-ins in-process using FastAPI TestClient against an isolated
hermetic SQLite database, generating structured turn-by-turn audits in Markdown and JSON.
"""

import argparse
import copy
import datetime
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend directory is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store


TEST_PROJECT_ID = "probe-chroniccare-ai"
TEST_KID = "probe-key-1"


def generate_rsa_key_and_cert():
    """Generates an RSA keypair and self-signed certificate for hermetic token verification."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(private_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return private_key, cert_pem


def create_token(private_key, user_id: str, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "name": "Probe Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": TEST_KID})


def setup_fresh_patient(client: TestClient, token: str, scenario: Dict[str, Any], user_id: str) -> None:
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
        with app_store.get_db_cursor(backend="sqlite", db_path=os.environ.get("LOCAL_DB_PATH")) as (cur, be, ph):
            cur.execute(f"UPDATE patient_profiles SET language = 'roman_ur' WHERE user_id = {ph}", (user_id,))


def run_scenario_on_engine(client: TestClient, private_key, scenario: Dict[str, Any], engine: str) -> Dict[str, Any]:
    user_id = f"probe-{scenario['name']}-{engine}-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@probe.test"
    token = create_token(private_key, user_id, email)
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        setup_fresh_patient(client, token, scenario, user_id)
    except Exception as e:
        return {
            "scenario": scenario["name"],
            "group": scenario.get("group", ""),
            "engine": engine,
            "turns": [],
            "questions_asked": 0,
            "final_level": "ERROR_BOOTSTRAP",
            "emergency": False,
            "complete_result": None,
            "notes": f"Setup failed: {str(e)}"
        }
    
    # Set interview engine dynamically
    old_engine = os.environ.get("INTERVIEW_ENGINE")
    os.environ["INTERVIEW_ENGINE"] = engine
    
    turns: List[Dict[str, Any]] = []
    final_result: Dict[str, Any] = {}
    notes: List[str] = []
    
    try:
        # Start checkin
        resp = client.post("/api/checkins/start", headers=headers)
        if resp.status_code != 200:
            notes.append(f"Failed to start check-in: {resp.status_code} - {resp.text}")
            return {
                "scenario": scenario["name"],
                "group": scenario.get("group", ""),
                "engine": engine,
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
        
        answers_queue = list(scenario.get("answers", []))
        fallback_queue = list(scenario.get("fallback", ["no", "fine", "none", "yes", "120", "120/80", "Yes, submit"]))
        
        turn_num = 1
        is_emergency = False
        is_complete = False
        
        while turn_num <= 25:
            # Decide answer to send
            used_fallback = False
            if answers_queue:
                answer = answers_queue.pop(0)
            elif fallback_queue:
                answer = fallback_queue.pop(0)
                used_fallback = True
                notes.append(f"Turn {turn_num} used fallback answer: {answer}")
            else:
                answer = "I don't know"
                used_fallback = True
                notes.append(f"Turn {turn_num} used default fallback 'I don't know'")
            
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
                "used_fallback": used_fallback,
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
                
        return {
            "scenario": scenario["name"],
            "group": scenario.get("group", ""),
            "engine": engine,
            "turns": turns,
            "questions_asked": len(turns),
            "final_level": final_level,
            "emergency": is_emergency,
            "complete_result": complete_result,
            "notes": "; ".join(notes) if notes else "Normal completion"
        }
        
    finally:
        if old_engine is not None:
            os.environ["INTERVIEW_ENGINE"] = old_engine
        else:
            os.environ.pop("INTERVIEW_ENGINE", None)


def build_markdown_report(results: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("# ChronicCare AI — Interview Probe Audit Report (Day 1)\n")
    lines.append(f"**Date:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Total Executions:** {len(results)}\n")
    
    # Top-level Summary Table
    lines.append("## Summary Table\n")
    lines.append("| Scenario | Engine | Group | Questions Asked | Final Level | Emergency | Notes |")
    lines.append("|---|---|:---:|:---:|:---:|:---:|---|")
    for r in results:
        scen = r["scenario"]
        eng = r["engine"]
        grp = r["group"]
        q_count = r["questions_asked"]
        lvl = r["final_level"]
        emerg = "YES" if r["emergency"] else "No"
        note = r["notes"]
        lines.append(f"| `{scen}` | **{eng}** | {grp} | {q_count} | `{lvl}` | {emerg} | {note} |")
    
    lines.append("\n---\n")
    lines.append("## Detailed Scenario Audits\n")
    
    for r in results:
        scen = r["scenario"]
        eng = r["engine"]
        lines.append(f"### Scenario: `{scen}` (Engine: {eng.upper()})\n")
        lines.append(f"- **Group:** {r['group']}")
        lines.append(f"- **Final Level:** `{r['final_level']}`")
        lines.append(f"- **Emergency:** {r['emergency']}")
        lines.append(f"- **Notes:** {r['notes']}\n")
        
        if r["turns"]:
            lines.append("| Turn | Step ID | Question Text Served | Answer Sent | Options | Why Text | Flags / Note |")
            lines.append("|:---:|---|---|---|---|---|---|")
            for t in r["turns"]:
                t_num = t["turn"]
                step = t.get("step_id") or ""
                q_text = (t.get("question_text") or "").replace("|", "\\|").replace("\n", " ")
                ans = str(t.get("answer_sent") or "").replace("|", "\\|").replace("\n", " ")
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
                lines.append(f"| {t_num} | `{step}` | {q_text} | {ans} | {opts} | {why} | {flag_str} |")
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


def main():
    parser = argparse.ArgumentParser(description="ChronicCare AI Adaptive Interview Probe Tool")
    parser.add_argument("--engine", choices=["v2", "v3", "both"], default="both", help="Interview engine to evaluate")
    parser.add_argument("--scenario", default="all", help="Scenario name from probe_scenarios.json or 'all'")
    parser.add_argument("--out", required=True, help="Path to output markdown report file")
    parser.add_argument("--json", required=False, help="Path to output JSON audit file")
    args = parser.parse_args()
    
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
                    print(f"[{idx}/{total}] Probed: {scen['name']} ({eng}) -> Level: {res['final_level']} (Emerg: {res['emergency']})")
    finally:
        # Write Markdown output first
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = build_markdown_report(results)
        out_path.write_text(md_content, encoding="utf-8")
        print(f"Wrote Markdown report to {out_path} ({len(md_content)} chars)")
        
        # Write JSON output if requested
        if args.json:
            json_path = Path(args.json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Wrote JSON audit to {json_path}")
            
        if old_db_path:
            os.environ["LOCAL_DB_PATH"] = old_db_path
        else:
            os.environ.pop("LOCAL_DB_PATH", None)
            
        if old_db_backend:
            os.environ["DB_BACKEND"] = old_db_backend
        else:
            os.environ.pop("DB_BACKEND", None)
            
        if old_proj_id:
            os.environ["FIREBASE_PROJECT_ID"] = old_proj_id
        else:
            os.environ.pop("FIREBASE_PROJECT_ID", None)
            
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
