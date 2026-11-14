"""
Hermetic Tests for Provider Approve or Adjust Workflow (Proposal UC-15, F6).

Verifies:
1. Approve confirms system triage recommendation and sets provider fields.
2. Adjust up (routine -> urgent) offers/creates an appointment.
3. Adjust down (review -> routine) cancels unbooked offered appointment.
4. Adjust on Red / emergency check-in returns 409 Conflict (protocol 1122).
5. Adjust without valid reason (min 5 chars) returns 422.
6. RBAC: Patient calling approve/adjust returns 403 Forbidden.
7. Queue Scoping: Unassigned provider calling approve/adjust returns 403.
8. Patient check-in view includes provider decision, provider level, and patient message.
9. SOAP note PLAN section reflects provider override decision.
10. Audit log records provider decision with levels only and ZERO clinical values.
"""

import json
import os
import tempfile
import uuid
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from data_sources import app_store
from data_sources.app_store import (
    append_audit,
    create_appointment,
    create_checkin,
    create_checkin_result,
    get_appointment_by_checkin,
    get_audit_logs,
    get_checkin_result,
    list_patient_appointments,
    migrate,
)
from main import app, get_current_user


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    migrate(backend="sqlite", db_path=path)
    yield path
    try:
        os.remove(path)
    except Exception:
        pass


@pytest.fixture
def api_client(temp_db):
    client = TestClient(app)
    yield client, temp_db
    app.dependency_overrides.clear()


def _seed_checkin(
    db_path: str,
    checkin_id: str,
    patient_id: str,
    triage_level: str = "review",
    emergency: bool = False,
    assigned_provider_id: str = "prov-dr-khan",
):
    create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        assigned_provider_id=assigned_provider_id,
        backend="sqlite",
        db_path=db_path,
    )
    create_checkin_result(
        checkin_id=checkin_id,
        emergency=emergency,
        intakes=[{"symptoms": ["fatigue"], "readings": []}],
        reconciliation={"summary": {"agreement": 1}},
        requires_review=(triage_level != "routine"),
        triage_level=triage_level,
        explanation={"sentences": [{"text": "Routine checkin"}]},
        backend="sqlite",
        db_path=db_path,
    )


def test_approve_system_recommendation(api_client):
    """Provider approve confirms system triage level and resolves alert."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-01"
    provider_id = "prov-dr-khan"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="review", assigned_provider_id=provider_id)

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={"action": "approve", "note": "Checked and approved"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["provider_decision"] == "approved"
        assert data["provider_level"] == "review"
        assert data["review_status"] == "resolved"

        # Check DB directly
        db_res = get_checkin_result(checkin_id, backend="sqlite", db_path=db_path)
        assert db_res["provider_decision"] == "approved"
        assert db_res["provider_level"] == "review"
        assert db_res["reviewed_by"] == provider_id

        # Check audit row
        audits = get_audit_logs(limit=20, backend="sqlite", db_path=db_path)
        approve_logs = [a for a in audits if a.get("action") == "approve_triage"]
        assert len(approve_logs) >= 1
        log_entry = approve_logs[0]
        assert (log_entry.get("actor_user_id") or log_entry.get("actor")) == provider_id
        raw_det = log_entry.get("detail_json") or log_entry.get("details") or log_entry.get("detail")
        details = json.loads(raw_det) if isinstance(raw_det, str) else raw_det
        assert details["from"] == "review"
        assert details["to"] == "review"
        # Zero clinical values
        for val in ["glucose", "systolic", "diastolic", "140", "180"]:
            assert val not in str(details).lower()


def test_adjust_up_creates_appointment(api_client):
    """Adjusting triage from routine to urgent creates/offers an urgent appointment."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-02"
    provider_id = "prov-dr-khan"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="routine", assigned_provider_id=provider_id)

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={
                "action": "adjust",
                "adjusted_level": "urgent",
                "reason": "Patient reports severe chest pressure and dizziness",
                "patient_message": "Please visit urgent care today",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["provider_decision"] == "adjusted"
        assert data["provider_level"] == "urgent"
        assert data["provider_reason"] == "Patient reports severe chest pressure and dizziness"

        # Verify an appointment was created
        appts = list_patient_appointments(patient_id, backend="sqlite", db_path=db_path)
        assert len(appts) >= 1
        appt = appts[0]
        assert appt["urgency"] == "urgent"
        assert appt["status"] in ("offered", "booked")


def test_adjust_down_cancels_unbooked_appointment(api_client):
    """Adjusting triage from review to routine cancels any unbooked offered appointment."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-03"
    provider_id = "prov-dr-khan"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="review", assigned_provider_id=provider_id)

    # Seed an offered appointment
    create_appointment(
        appointment_id=f"appt-{uuid.uuid4().hex[:8]}",
        patient_id=patient_id,
        checkin_id=checkin_id,
        provider_id=provider_id,
        specialty="endocrinology",
        urgency="routine",
        mode="telehealth",
        status="offered",
        backend="sqlite",
        db_path=db_path,
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={
                "action": "adjust",
                "adjusted_level": "routine",
                "reason": "Vitals normalized on recheck; isolated benign spike",
                "patient_message": "Continuing standard monitoring",
            },
        )
        assert resp.status_code == 200, resp.text

        # Verify appointment is cancelled
        appt = get_appointment_by_checkin(checkin_id, backend="sqlite", db_path=db_path)
        assert appt is not None
        assert appt["status"] == "cancelled"


def test_adjust_on_red_emergency_returns_409(api_client):
    """Adjust on Red / Emergency check-in raises 409 Conflict with emergency protocol notice."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-04"
    provider_id = "prov-dr-khan"

    _seed_checkin(
        db_path,
        checkin_id,
        patient_id,
        triage_level="emergency",
        emergency=True,
        assigned_provider_id=provider_id,
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={
                "action": "adjust",
                "adjusted_level": "routine",
                "reason": "Trying to downgrade emergency",
            },
        )
        assert resp.status_code == 409, resp.text
        assert "1122" in resp.json().get("detail", "")


def test_adjust_without_reason_returns_422(api_client):
    """Adjust without a required clinical reason raises 422."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-05"
    provider_id = "prov-dr-khan"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="review", assigned_provider_id=provider_id)

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        # Empty reason
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={"action": "adjust", "adjusted_level": "routine", "reason": ""},
        )
        assert resp.status_code == 422, resp.text

        # Reason under 5 chars
        resp2 = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={"action": "adjust", "adjusted_level": "routine", "reason": "ok"},
        )
        assert resp2.status_code == 422, resp2.text


def test_rbac_patient_calling_approve_adjust_returns_403(api_client):
    """Patient role cannot call provider approve or adjust endpoint."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-06"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="review")

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": patient_id,
        "role": "patient",
        "email": "patient@example.com",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={"action": "approve"},
        )
        assert resp.status_code == 403, resp.text


def test_queue_scoping_unassigned_provider_returns_403(api_client):
    """Provider not assigned to checkin cannot approve/adjust when checkin is scoped."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-07"
    assigned_provider = "prov-dr-assigned"
    other_provider = "prov-dr-intruder"

    _seed_checkin(
        db_path,
        checkin_id,
        patient_id,
        triage_level="review",
        assigned_provider_id=assigned_provider,
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": other_provider,
        "role": "provider",
        "email": "other@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={"action": "approve"},
        )
        assert resp.status_code == 403, resp.text


def test_patient_view_and_soap_plan_reflect_provider_adjustment(api_client):
    """Patient check-in view and SOAP note PLAN reflect provider override."""
    client, db_path = api_client
    checkin_id = f"chk-{uuid.uuid4().hex[:8]}"
    patient_id = "pat-test-08"
    provider_id = "prov-dr-khan"

    _seed_checkin(db_path, checkin_id, patient_id, triage_level="review", assigned_provider_id=provider_id)

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": provider_id,
        "role": "provider",
        "email": "doctor@hospital.org",
    }

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        # 1. Adjust
        client.post(
            f"/api/provider/review/{checkin_id}/action",
            json={
                "action": "adjust",
                "adjusted_level": "routine",
                "reason": "Normal physiological fluctuation",
                "patient_message": "All looks good; continue routine diet and meds",
            },
        )

        # 2. Patient reads check-in
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": patient_id,
            "role": "patient",
            "email": "patient@example.com",
        }
        pat_resp = client.get(f"/api/checkins/{checkin_id}")
        assert pat_resp.status_code == 200, pat_resp.text
        pat_data = pat_resp.json()
        assert pat_data["provider_decision"] == "adjusted"
        assert pat_data["provider_level"] == "routine"
        assert pat_data["patient_message"] == "All looks good; continue routine diet and meds"

        # 3. SOAP note PLAN check via provider endpoint
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": provider_id,
            "role": "provider",
            "email": "doctor@hospital.org",
        }
        soap_resp = client.get(f"/api/provider/review/{checkin_id}/soap")
        assert soap_resp.status_code == 200, soap_resp.text
        soap = soap_resp.json()
        plan_text = " ".join(soap["plan"])
        assert "Provider decision: Adjusted triage level" in plan_text
        assert "routine" in plan_text
        assert "Normal physiological fluctuation" in plan_text
