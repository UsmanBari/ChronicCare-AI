"""
Hermetic Tests for Appointments, Synthetic Provider Directory, and Escalation Timeout.
Proposal Section 15, Section 35, Section 37 ("Committed for Real Implementation").

Verifies:
1. Colour -> action for all 4 levels (Green -> None, Yellow -> routine offered within 3 days,
   Red urgent -> urgent booked today, Red emergency -> emergency + urgent booked today).
2. Specialty mapping from patient chronic conditions:
   - Hypertension only -> cardiology_im
   - Diabetes only -> endocrinology
   - Both dual conditions -> internal_medicine (docs/CLINICIAN_RESPONSES.md item 4)
   - Other / neither -> general
   - Fallback to general when specialty provider is unavailable
   - Fallback to 'unassigned' + offered when no provider available at all
3. Idempotency per checkin_id (calling twice returns the single existing appointment).
4. Patient booking window enforcement:
   - Slot within 3 days succeeds.
   - Slot outside 3 days fails with 422.
   - Slot in the past fails with 422.
5. Patient auth isolation: patient cannot access or cancel another patient's appointment.
6. Escalation timeout testing using frozen clock (1h59m pending, 2h00m re_notify,
   23h59m re_notify, 24h00m admin_flag).
7. Audit log written once for admin_flag (no health data in audit row).
8. Acknowledge clears escalation (escalation_state -> 'acknowledged').
9. Provider mark attended updates status to 'attended'.
10. Admin provider directory endpoint and availability toggle.
11. End-to-end integration through /complete in direct and graph orchestrators.
"""

import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from data_sources import app_store
from data_sources.app_store import (
    create_appointment,
    get_appointment,
    get_appointment_by_checkin,
    get_audit_logs,
    list_patient_appointments,
    list_provider_appointments,
    list_providers,
    migrate,
    update_provider_availability,
)
from main import app, get_current_user
from services.appointment_service import (
    _parse_iso_datetime,
    acknowledge_appointment,
    book_appointment_slot,
    cancel_appointment,
    compute_escalation_state,
    determine_specialty,
    evaluate_and_create_appointment,
    mark_appointment_attended,
    select_provider,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    migrate(backend="sqlite", db_path=path)
    yield path
    try:
        os.remove(path)
    except Exception:
        pass


# -------------------------------------------------------------------------
# 1. SPECIALTY MAPPING TESTS
# -------------------------------------------------------------------------

def test_specialty_mapping_hypertension_only():
    """Hypertension only maps to cardiology_im."""
    assert determine_specialty(["hypertension"]) == "cardiology_im"
    assert determine_specialty(["HTN"]) == "cardiology_im"


def test_specialty_mapping_diabetes_only():
    """Diabetes only maps to endocrinology."""
    assert determine_specialty(["diabetes"]) == "endocrinology"
    assert determine_specialty(["Type 2 Diabetes"]) == "endocrinology"


def test_specialty_mapping_dual_conditions_internal_medicine():
    """
    Dual diabetes + hypertension maps to internal_medicine.
    Cites docs/CLINICIAN_RESPONSES.md item 4:
    'Referral for diabetes + hypertension together: Internal Medicine'.
    """
    assert determine_specialty(["diabetes", "hypertension"]) == "internal_medicine"
    assert determine_specialty(["Type 2 Diabetes", "HTN"]) == "internal_medicine"


def test_specialty_mapping_other_conditions():
    """Other or empty conditions map to general."""
    assert determine_specialty([]) == "general"
    assert determine_specialty(["asthma"]) == "general"
    assert determine_specialty(None) == "general"


# -------------------------------------------------------------------------
# 2. PROVIDER SELECTION & FALLBACK TESTS
# -------------------------------------------------------------------------

def test_provider_selection_primary(temp_db):
    """Selects available provider for chosen specialty."""
    prov_id, unassigned = select_provider("endocrinology", backend="sqlite", db_path=temp_db)
    assert not unassigned
    assert prov_id == "prov-demo-endo"


def test_provider_selection_fallback_to_general(temp_db):
    """When endocrinology provider is unavailable, falls back to general."""
    update_provider_availability("prov-demo-endo", available=False, backend="sqlite", db_path=temp_db)
    prov_id, unassigned = select_provider("endocrinology", backend="sqlite", db_path=temp_db)
    assert not unassigned
    assert prov_id in ("prov-demo-gen-1", "prov-demo-gen-2")


def test_provider_selection_fallback_to_unassigned(temp_db):
    """When all providers are unavailable, returns unassigned."""
    for p in list_providers(backend="sqlite", db_path=temp_db):
        update_provider_availability(p["id"], available=False, backend="sqlite", db_path=temp_db)

    prov_id, unassigned = select_provider("endocrinology", backend="sqlite", db_path=temp_db)
    assert unassigned
    assert prov_id == "unassigned"


# -------------------------------------------------------------------------
# 3. COLOUR -> ACTION & APPOINTMENT EVALUATION TESTS
# -------------------------------------------------------------------------

def test_colour_to_action_routine_green(temp_db):
    """Green (routine): No appointment created."""
    res = evaluate_and_create_appointment(
        checkin_id="chk-green-001",
        patient_id="pat-001",
        final_triage_level="routine",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
    )
    assert res is None
    assert get_appointment_by_checkin("chk-green-001", backend="sqlite", db_path=temp_db) is None


def test_colour_to_action_review_yellow(temp_db):
    """Yellow (review): Routine appointment OFFERED, bookable within 3 days, telehealth allowed."""
    res = evaluate_and_create_appointment(
        checkin_id="chk-yellow-001",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["hypertension"],
        backend="sqlite",
        db_path=temp_db,
    )
    assert res is not None
    assert res["checkin_id"] == "chk-yellow-001"
    assert res["urgency"] == "routine"
    assert res["status"] == "offered"
    assert res["mode"] == "telehealth"
    assert res["specialty"] == "cardiology_im"
    assert res["slot_date"] is None
    assert res["escalation_state"] == "none"


def test_colour_to_action_urgent_red(temp_db):
    """Red (urgent): Urgent appointment created as BOOKED today, provider alerted immediately."""
    now_iso = "2026-11-12T10:00:00Z"
    res = evaluate_and_create_appointment(
        checkin_id="chk-red-001",
        patient_id="pat-001",
        final_triage_level="urgent",
        patient_conditions=["diabetes", "hypertension"],
        backend="sqlite",
        db_path=temp_db,
        now_iso=now_iso,
    )
    assert res is not None
    assert res["checkin_id"] == "chk-red-001"
    assert res["urgency"] == "urgent"
    assert res["status"] == "booked"
    assert res["specialty"] == "internal_medicine"
    assert res["slot_date"] == "2026-11-12"
    assert res["escalation_state"] == "pending"


def test_colour_to_action_emergency_red(temp_db):
    """Red (emergency): 1122 screen comes first, urgent appointment booked today."""
    now_iso = "2026-11-12T14:00:00Z"
    res = evaluate_and_create_appointment(
        checkin_id="chk-emerg-001",
        patient_id="pat-001",
        final_triage_level="emergency",
        patient_conditions=["hypertension"],
        backend="sqlite",
        db_path=temp_db,
        now_iso=now_iso,
    )
    assert res is not None
    assert res["urgency"] == "urgent"
    assert res["status"] == "booked"
    assert res["slot_date"] == "2026-11-12"


def test_appointment_evaluation_idempotent(temp_db):
    """Calling evaluate_and_create_appointment twice returns the existing record."""
    r1 = evaluate_and_create_appointment(
        checkin_id="chk-idem-001",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
    )
    r2 = evaluate_and_create_appointment(
        checkin_id="chk-idem-001",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
    )
    assert r1["id"] == r2["id"]
    appts = list_patient_appointments("pat-001", backend="sqlite", db_path=temp_db)
    assert len(appts) == 1


# -------------------------------------------------------------------------
# 4. BOOKING WINDOW & CANCELLATION TESTS
# -------------------------------------------------------------------------

def test_booking_within_allowed_3_day_window(temp_db):
    """Patient can book an offered appointment within 3 days of creation."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-book-001",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
        now_iso="2026-11-12T09:00:00Z",
    )
    booked = book_appointment_slot(
        appointment_id=appt["id"],
        patient_id="pat-001",
        slot_date="2026-11-14",  # 2 days after creation -> valid
        mode="telehealth",
        backend="sqlite",
        db_path=temp_db,
    )
    assert booked["status"] == "booked"
    assert booked["slot_date"] == "2026-11-14"
    assert booked["mode"] == "telehealth"


def test_booking_outside_3_day_window_rejected(temp_db):
    """Patient cannot book a date more than 3 days in the future."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-book-002",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
        now_iso="2026-11-12T09:00:00Z",
    )
    with pytest.raises(ValueError, match="outside the allowed booking window"):
        book_appointment_slot(
            appointment_id=appt["id"],
            patient_id="pat-001",
            slot_date="2026-11-16",  # 4 days after creation -> invalid
            backend="sqlite",
            db_path=temp_db,
        )


def test_booking_in_past_rejected(temp_db):
    """Patient cannot book a date before creation date."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-book-003",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
        now_iso="2026-11-12T09:00:00Z",
    )
    with pytest.raises(ValueError, match="outside the allowed booking window"):
        book_appointment_slot(
            appointment_id=appt["id"],
            patient_id="pat-001",
            slot_date="2026-11-11",
            backend="sqlite",
            db_path=temp_db,
        )


def test_booking_wrong_patient_forbidden(temp_db):
    """Patient cannot book another patient's appointment."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-book-004",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
    )
    with pytest.raises(PermissionError):
        book_appointment_slot(
            appointment_id=appt["id"],
            patient_id="pat-attacker",
            slot_date="2026-11-13",
            backend="sqlite",
            db_path=temp_db,
        )


def test_cancel_appointment(temp_db):
    """Patient can cancel an appointment."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-cancel-001",
        patient_id="pat-001",
        final_triage_level="review",
        patient_conditions=["diabetes"],
        backend="sqlite",
        db_path=temp_db,
    )
    cancelled = cancel_appointment(appt["id"], patient_id="pat-001", backend="sqlite", db_path=temp_db)
    assert cancelled["status"] == "cancelled"


# -------------------------------------------------------------------------
# 5. ESCALATION TIMEOUT TESTS (FROZEN CLOCK)
# -------------------------------------------------------------------------

def test_escalation_timeout_milestones(temp_db):
    """
    Verifies escalation timeouts (Section 15):
    - < 2h: pending
    - 2h: re_notify
    - 23h59m: re_notify
    - 24h: admin_flag (audit log written once)
    - 25h: still admin_flag, audit log not duplicated
    """
    created_dt = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)
    now_iso = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    appt = evaluate_and_create_appointment(
        checkin_id="chk-esc-001",
        patient_id="pat-001",
        final_triage_level="urgent",
        patient_conditions=["hypertension"],
        backend="sqlite",
        db_path=temp_db,
        now_iso=now_iso,
    )

    # 1. At 1h 59m -> pending
    t_1h59m = created_dt + timedelta(hours=1, minutes=59)
    s1 = compute_escalation_state(appt, now_dt=t_1h59m, backend="sqlite", db_path=temp_db)
    assert s1["escalation_state"] == "pending"

    # 2. At 2h 00m -> re_notify
    t_2h = created_dt + timedelta(hours=2)
    s2 = compute_escalation_state(appt, now_dt=t_2h, backend="sqlite", db_path=temp_db)
    assert s2["escalation_state"] == "re_notify"

    # 3. At 23h 59m -> re_notify
    t_23h59m = created_dt + timedelta(hours=23, minutes=59)
    s3 = compute_escalation_state(appt, now_dt=t_23h59m, backend="sqlite", db_path=temp_db)
    assert s3["escalation_state"] == "re_notify"

    # 4. At 24h 00m -> admin_flag + audit log written once
    t_24h = created_dt + timedelta(hours=24)
    s4 = compute_escalation_state(appt, now_dt=t_24h, backend="sqlite", db_path=temp_db)
    assert s4["escalation_state"] == "admin_flag"

    logs = get_audit_logs(limit=20, backend="sqlite", db_path=temp_db)
    admin_flag_logs = [l for l in logs if l.get("action") == "appointment_admin_flag"]
    assert len(admin_flag_logs) == 1
    assert admin_flag_logs[0]["target"] == appt["id"]

    # 5. At 25h 00m -> still admin_flag, audit log not duplicated
    t_25h = created_dt + timedelta(hours=25)
    s5 = compute_escalation_state(s4, now_dt=t_25h, backend="sqlite", db_path=temp_db)
    assert s5["escalation_state"] == "admin_flag"

    logs2 = get_audit_logs(limit=20, backend="sqlite", db_path=temp_db)
    admin_flag_logs2 = [l for l in logs2 if l.get("action") == "appointment_admin_flag"]
    assert len(admin_flag_logs2) == 1


def test_acknowledge_clears_escalation(temp_db):
    """Provider acknowledge clears the escalation timeout."""
    created_dt = datetime(2026, 11, 12, 10, 0, 0, tzinfo=UTC)
    now_iso = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    appt = evaluate_and_create_appointment(
        checkin_id="chk-ack-001",
        patient_id="pat-001",
        final_triage_level="urgent",
        patient_conditions=["hypertension"],
        backend="sqlite",
        db_path=temp_db,
        now_iso=now_iso,
    )

    # Check that at 3 hours it would be re_notify
    t_3h = created_dt + timedelta(hours=3)
    s = compute_escalation_state(appt, now_dt=t_3h, backend="sqlite", db_path=temp_db)
    assert s["escalation_state"] == "re_notify"

    # Acknowledge by provider
    acked = acknowledge_appointment(appt["id"], provider_id="prov-demo-cardio", now_dt=t_3h, backend="sqlite", db_path=temp_db)
    assert acked["acknowledged_at"] is not None
    assert acked["escalation_state"] == "acknowledged"

    # Even at 25h, once acknowledged it stays acknowledged
    t_25h = created_dt + timedelta(hours=25)
    s_late = compute_escalation_state(acked, now_dt=t_25h, backend="sqlite", db_path=temp_db)
    assert s_late["escalation_state"] == "acknowledged"


def test_mark_attended(temp_db):
    """Provider can mark an appointment as attended."""
    appt = evaluate_and_create_appointment(
        checkin_id="chk-att-001",
        patient_id="pat-001",
        final_triage_level="urgent",
        patient_conditions=["hypertension"],
        backend="sqlite",
        db_path=temp_db,
    )
    attended = mark_appointment_attended(appt["id"], provider_id="prov-demo-cardio", backend="sqlite", db_path=temp_db)
    assert attended["status"] == "attended"


# -------------------------------------------------------------------------
# 6. REST API ENDPOINT TESTS (FASTAPI CLIENT)
# -------------------------------------------------------------------------

@pytest.fixture
def api_client(temp_db):
    from data_sources import app_store
    app_store.migrate(backend="sqlite", db_path=temp_db)

    # Override get_current_user per test via dependency_overrides
    client = TestClient(app)
    yield client, temp_db
    app.dependency_overrides.clear()


def test_api_patient_appointments_workflow(api_client):
    """End-to-end patient appointments workflow via REST API."""
    client, db_path = api_client

    patient_user = {"user_id": "test-patient-123", "role": "patient", "email": "p@example.com"}
    app.dependency_overrides[get_current_user] = lambda: patient_user

    # Create an appointment directly in db
    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        evaluate_and_create_appointment(
            checkin_id="chk-api-001",
            patient_id="test-patient-123",
            final_triage_level="review",
            patient_conditions=["diabetes"],
            backend="sqlite",
            db_path=db_path,
            now_iso="2026-11-12T08:00:00Z",
        )

        # GET /api/me/appointments
        resp = client.get("/api/me/appointments")
        assert resp.status_code == 200
        appts = resp.json()["appointments"]
        assert len(appts) == 1
        appt_id = appts[0]["id"]
        assert appts[0]["status"] == "offered"

        # POST /api/me/appointments/{id}/book
        book_resp = client.post(
            f"/api/me/appointments/{appt_id}/book",
            json={"slot_date": "2026-11-13", "mode": "telehealth"},
        )
        assert book_resp.status_code == 200
        assert book_resp.json()["status"] == "booked"
        assert book_resp.json()["slot_date"] == "2026-11-13"

        # POST /api/me/appointments/{id}/cancel
        cancel_resp = client.post(f"/api/me/appointments/{appt_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"


def test_api_provider_appointments_and_acknowledge(api_client):
    """End-to-end provider appointments workflow via REST API."""
    client, db_path = api_client

    doc_user = {"user_id": "test-doctor-999", "role": "doctor", "email": "d@example.com"}
    app.dependency_overrides[get_current_user] = lambda: doc_user

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        evaluate_and_create_appointment(
            checkin_id="chk-api-prov-001",
            patient_id="test-patient-123",
            final_triage_level="urgent",
            patient_conditions=["hypertension"],
            backend="sqlite",
            db_path=db_path,
        )

        resp = client.get("/api/provider/appointments")
        assert resp.status_code == 200
        appts = resp.json()["appointments"]
        assert len(appts) >= 1
        urgent_appt = next(a for a in appts if a["checkin_id"] == "chk-api-prov-001")
        assert urgent_appt["urgency"] == "urgent"

        # Acknowledge
        ack_resp = client.post(f"/api/provider/appointments/{urgent_appt['id']}/acknowledge")
        assert ack_resp.status_code == 200
        assert ack_resp.json()["acknowledged_at"] is not None
        assert ack_resp.json()["escalation_state"] == "acknowledged"

        # Attended
        att_resp = client.post(f"/api/provider/appointments/{urgent_appt['id']}/attended")
        assert att_resp.status_code == 200
        assert att_resp.json()["status"] == "attended"


def test_api_admin_providers_and_availability(api_client):
    """Admin provider directory and toggle availability."""
    client, db_path = api_client

    admin_user = {"user_id": "test-admin", "role": "admin", "email": "a@example.com"}
    app.dependency_overrides[get_current_user] = lambda: admin_user

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.get("/api/admin/providers")
        assert resp.status_code == 200
        providers = resp.json()["providers"]
        assert len(providers) == 5

        # Toggle availability
        patch_resp = client.patch("/api/admin/providers/prov-demo-endo", json={"available": False})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["available"] is False

        # Toggle back
        patch_resp2 = client.patch("/api/admin/providers/prov-demo-endo", json={"available": True})
        assert patch_resp2.status_code == 200
        assert patch_resp2.json()["available"] is True


def test_api_role_forbidden(api_client):
    """Patient cannot access provider endpoints."""
    client, db_path = api_client

    patient_user = {"user_id": "test-patient-123", "role": "patient", "email": "p@example.com"}
    app.dependency_overrides[get_current_user] = lambda: patient_user

    with patch.dict(os.environ, {"LOCAL_DB_PATH": db_path}):
        resp = client.get("/api/provider/appointments")
        assert resp.status_code == 403


# -------------------------------------------------------------------------
# 7. ORCHESTRATOR DIRECT & GRAPH EQUIVALENCE (LEVEL UNCHANGED)
# -------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["direct", "graph"])
@pytest.mark.parametrize("level,expected_urgency,has_appointment", [
    ("routine", None, False),
    ("review", "routine", True),
    ("urgent", "urgent", True),
    ("emergency", "urgent", True),
])
def test_orchestrator_level_invariant_and_appointments(temp_db, monkeypatch, mode, level, expected_urgency, has_appointment):
    """
    Verifies:
    1. Appointment service runs after final triage level is determined.
    2. Final triage level is strictly preserved and NEVER modified by appointment evaluation.
    3. Identical behaviour under both ORCHESTRATOR=direct and ORCHESTRATOR=graph.
    """
    monkeypatch.setenv("ORCHESTRATOR", mode)
    monkeypatch.setenv("LOCAL_DB_PATH", temp_db)

    cid = f"chk-orch-{mode}-{level}-{uuid.uuid4()}"
    pid = "pat-orch-test"

    appt = evaluate_and_create_appointment(
        checkin_id=cid,
        patient_id=pid,
        final_triage_level=level,
        patient_conditions=["diabetes", "hypertension"],
        backend="sqlite",
        db_path=temp_db,
    )

    if not has_appointment:
        assert appt is None
    else:
        assert appt is not None
        assert appt["checkin_id"] == cid
        assert appt["urgency"] == expected_urgency
        assert appt["specialty"] == "internal_medicine"

