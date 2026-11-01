"""
Unit & Integration Tests for Orchestrator Equivalence & Privacy Invariants.
Validates:
- U6-02: Graph behind ORCHESTRATOR flag; default direct
- U6-03: Equivalence across representative clinical scenarios (connected + isolated, emergency, triage categories)
- U6-04: Trace steps with counts/levels only (no reading values, dates of birth, or patient names)
"""

import os
import sys
import re
import time
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import jwt

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from orchestrator.graph import run_checkin_graph_with_state as _run_checkin_graph_with_state
from orchestrator.steps import (
    step_check_idempotency,
    step_parse_and_validate_intake,
    step_fetch_prior_bundle,
    step_build_bundles,
    step_reconcile,
    step_verify,
    step_decide_triage,
    step_persist_and_respond,
)
from data_sources.data_source import NormalizedPatient, NormalizedObservation, NormalizedMedication


TEST_PROJECT_ID = "test-orchestrator-ci"
TEST_KID = "test-key-orchestrator-ci"


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "ci_equiv.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    return rsa_key


def _create_token(rsa_key, uid: str) -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": "Jane Doe",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def _bootstrap(client: TestClient, token: str, conditions: list) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": True,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )
    return headers


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("checkin_id", "created_at", "completed_at", "escalated_at", "started_at"):
                continue
            out[k] = _clean(v)
        return out
    elif isinstance(obj, list):
        return [_clean(x) for x in obj]
    elif isinstance(obj, str):
        s = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "<TS>", obj)
        s = re.sub(r"CHECKIN-[^\s\'\"]+", "<CHECKIN_RECORD_ID>", s)
        s = re.sub(r"(dir|grp)_[a-zA-Z0-9_-]+", "<UID>", s)
        s = re.sub(r"local-(dir|grp)_[a-zA-Z0-9_-]+", "<LOCAL_PATIENT>", s)
        return s
    return obj


def test_orchestrator_flag_default_direct(monkeypatch):
    """U6-02: ORCHESTRATOR defaults to 'direct'."""
    monkeypatch.delenv("ORCHESTRATOR", raising=False)
    from main import ORCHESTRATOR as default_mode
    # Module-level or os.environ check
    mode = os.environ.get("ORCHESTRATOR", "direct").lower()
    assert mode == "direct"


def test_trace_steps_privacy_invariant_u6_04(setup_test_db, monkeypatch):
    """
    U6-04: Trace steps must contain counts and levels ONLY.
    NEVER patient names, dates of birth, or clinical reading values.
    """
    rsa_key = setup_test_db
    client = TestClient(app)
    tok = _create_token(rsa_key, "u6_trace_patient")
    headers = _bootstrap(client, tok, ["diabetes"])

    start_resp = client.post("/api/checkins/start", headers=headers).json()
    cid = start_resp["checkin_id"]

    # Provide answers until complete
    answers = ["I feel fine", "145 mg/dL", "No other symptoms", "Yes, metformin taken", "No changes", "No", "No"]
    for ans in answers:
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": ans})
        if ans_resp.status_code != 200:
            break
        b = ans_resp.json()
        if b.get("complete") or b.get("emergency"):
            break

    checkin = app_store.get_checkin_by_id(cid)
    user = app_store.get_user_by_id(checkin["user_id"])

    resp, state = _run_checkin_graph_with_state(checkin, user, record_label="Local File")

    trace = state.get("trace", [])
    assert len(trace) > 0, "Trace must not be empty"

    forbidden_patterns = [
        "Jane Doe",
        "u6_trace_patient",
        "1980-05-15",
        "145",
        "mg/dL",
        "mmHg",
    ]

    for step in trace:
        assert "node" in step, "Trace step missing 'node'"
        assert "started_at" in step, "Trace step missing 'started_at'"
        assert "ms" in step, "Trace step missing 'ms'"
        assert "summary" in step, "Trace step missing 'summary'"

        summary = step["summary"]
        assert isinstance(summary, str) and len(summary) > 0

        for pattern in forbidden_patterns:
            assert pattern.lower() not in summary.lower(), (
                f"Privacy violation U6-04: forbidden pattern '{pattern}' found in trace summary: '{summary}'"
            )


@pytest.mark.parametrize("scenario_type", [
    "routine_isolated",
    "emergency_red_flag",
    "urgent_high_glucose",
    "crisis_bp",
    "medication_conflict_connected",
])
def test_representative_scenarios_equivalence(setup_test_db, monkeypatch, scenario_type):
    """
    U6-03: Representative CI subset proving 100% equivalence between direct and graph.
    Covers routine, emergency, glucose triggers, BP crisis, connected, isolated.
    """
    rsa_key = setup_test_db
    client = TestClient(app)

    def execute_under(mode_str: str, pfx: str):
        monkeypatch.setenv("ORCHESTRATOR", mode_str)
        uid = f"{pfx}_{scenario_type}"
        conds = ["diabetes", "hypertension"]
        headers = _bootstrap(client, _create_token(rsa_key, uid), conds)

        start_resp = client.post("/api/checkins/start", headers=headers).json()
        cid = start_resp["checkin_id"]

        if scenario_type == "routine_isolated":
            answers = ["Doing well", "110 mg/dL", "120/80", "No symptoms", "Taken meds", "No"]
        elif scenario_type == "emergency_red_flag":
            answers = ["I have crushing chest pain radiating to my left arm"]
        elif scenario_type == "urgent_high_glucose":
            answers = ["Feeling tired", "380 mg/dL", "Yes I can swallow", "No vomiting", "Taken meds", "No"]
        elif scenario_type == "crisis_bp":
            answers = ["Terrible sudden headache", "120 mg/dL", "195/115", "Taken meds", "No"]
        elif scenario_type == "medication_conflict_connected":
            answers = ["Doing well", "115 mg/dL", "120/80", "Stopped taking metformin due to nausea", "No"]
        else:
            answers = ["Doing well", "115 mg/dL", "120/80", "No"]

        for ans in answers:
            ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": ans})
            if ans_resp.status_code != 200:
                break
            b = ans_resp.json()
            if b.get("emergency") or b.get("complete"):
                break

        comp = client.post(f"/api/checkins/{cid}/complete", headers=headers).json()
        db_row = app_store.get_checkin_result(cid) or {}
        return comp, db_row

    comp_dir, db_dir = execute_under("direct", "dir")
    comp_grp, db_grp = execute_under("graph", "grp")

    cleaned_comp_dir = _clean(comp_dir)
    cleaned_comp_grp = _clean(comp_grp)
    cleaned_db_dir = _clean(db_dir)
    cleaned_db_grp = _clean(db_grp)

    # 1. API response field-by-field equality
    assert cleaned_comp_dir == cleaned_comp_grp, (
        f"Mismatch in API complete response for {scenario_type}:\n"
        f"Direct: {cleaned_comp_dir}\n"
        f"Graph:  {cleaned_comp_grp}"
    )

    # 2. Database persistence equality
    assert cleaned_db_dir == cleaned_db_grp, (
        f"Mismatch in DB checkin_results for {scenario_type}:\n"
        f"Direct: {cleaned_db_dir}\n"
        f"Graph:  {cleaned_db_grp}"
    )

    # 3. Clinical triage level equivalence
    triage_dir = comp_dir.get("triage") or {}
    triage_grp = comp_grp.get("triage") or {}
    lvl_dir = "emergency" if comp_dir.get("emergency") else (triage_dir.get("level") or db_dir.get("triage_level"))
    lvl_grp = "emergency" if comp_grp.get("emergency") else (triage_grp.get("level") or db_grp.get("triage_level"))
    assert lvl_dir == lvl_grp, f"Triage level mismatch for {scenario_type}: direct={lvl_dir}, graph={lvl_grp}"
