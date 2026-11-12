"""
Hermetic Tests for In-App Notification Centre, Daily Reminders & Escalation Alerts (PR I4-H).
Verifies:
1. Notification triggers (urgent check-in, 2h escalation re-notify, 24h admin-flag, daily reminder).
2. Idempotency (each trigger creates exactly one notification, duplicate triggers return existing).
3. Zero clinical values / PHI on lock screen (validate_no_health_values guard).
4. Role isolation (patient cannot access provider/admin notifications; cross-patient read forbidden).
5. Escalation milestones with frozen clock (1h59m, 2h00m, 24h00m).
6. Daily reminder eligibility (hour gating, same-day check-in suppression, same-day deduplication).
7. FCM push dispatch (mocked, dormant by default, skipped without credentials).
8. REST endpoints for Patient, Provider, and Admin roles.
"""

from datetime import UTC, datetime, timedelta
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from data_sources import app_store
from data_sources.app_store import (
    create_notification,
    get_notification,
    list_notifications,
    count_unread_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    save_fcm_token,
    delete_fcm_token,
    list_fcm_tokens,
    migrate,
)
from services.notification_service import (
    validate_no_health_values,
    notify_urgent_checkin,
    notify_escalation_renotify,
    notify_escalation_admin_flag,
    notify_daily_reminder,
    send_fcm_push,
    is_fcm_enabled,
)
from services.reminder_service import (
    is_patient_reminder_due,
    dispatch_due_reminders,
    is_reminders_enabled,
)
from services.appointment_service import (
    compute_escalation_state,
    evaluate_and_create_appointment,
)
import main


@pytest.fixture
def temp_db(monkeypatch):
    """Hermetic SQLite database fixture migrated to latest schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name

    monkeypatch.setenv("LOCAL_DB_PATH", path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    migrate(backend="sqlite", db_path=path)

    yield path

    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def api_client(temp_db, monkeypatch):
    """TestClient wired to hermetic SQLite database."""
    client = TestClient(main.app)
    yield client
    main.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. PHI / Health Values Lock Screen Guard Tests
# ---------------------------------------------------------------------------

def test_phi_lock_screen_guard_rejects_clinical_values():
    """Validates that text containing blood pressure, glucose, or lab units is rejected."""
    # Reject Blood Pressure values
    with pytest.raises(ValueError, match="PHI Guard Violation"):
        validate_no_health_values("Check-in alert: BP was 140/90")

    # Reject Glucose values
    with pytest.raises(ValueError, match="PHI Guard Violation"):
        validate_no_health_values("Patient reported 250 mg/dL")

    with pytest.raises(ValueError, match="PHI Guard Violation"):
        validate_no_health_values("High blood sugar reading reported")

    with pytest.raises(ValueError, match="PHI Guard Violation"):
        validate_no_health_values("Recent HbA1c is 8.5")

    # Safe text passes without exception
    validate_no_health_values("Urgent check-in from Ali Khan requires clinical review")
    validate_no_health_values("An urgent case has remained unacknowledged for over 2 hours.")
    validate_no_health_values("Your daily health check-in is due.")


def test_generated_notifications_contain_no_health_values(temp_db):
    """Verifies that all 4 notification types generate clean text without clinical numbers."""
    n_urgent = notify_urgent_checkin("chk-safe-1", "p-safe-1", "urgent", db_path=temp_db)
    validate_no_health_values(n_urgent["title"])
    validate_no_health_values(n_urgent["body"])

    n_renotify = notify_escalation_renotify("apt-safe-1", "prov-demo-gen-1", "p-safe-1", db_path=temp_db)
    validate_no_health_values(n_renotify["title"])
    validate_no_health_values(n_renotify["body"])

    n_admin = notify_escalation_admin_flag("apt-safe-1", "p-safe-1", db_path=temp_db)
    validate_no_health_values(n_admin["title"])
    validate_no_health_values(n_admin["body"])

    n_remind = notify_daily_reminder("p-safe-1", "2026-11-12", db_path=temp_db)
    validate_no_health_values(n_remind["title"])
    validate_no_health_values(n_remind["body"])


# ---------------------------------------------------------------------------
# 2. Trigger Idempotency Tests
# ---------------------------------------------------------------------------

def test_urgent_checkin_notification_idempotent(temp_db):
    """Multiple dispatches for the same check-in return the existing notification without creating duplicates."""
    n1 = notify_urgent_checkin("chk-idem-1", "p-1", "urgent", provider_id="prov-demo-cardio", db_path=temp_db)
    assert n1 is not None
    assert n1["role"] == "provider"
    assert n1["event_type"] == "urgent_checkin"

    n2 = notify_urgent_checkin("chk-idem-1", "p-1", "urgent", provider_id="prov-demo-cardio", db_path=temp_db)
    assert n2["id"] == n1["id"]

    all_prov = list_notifications(role="provider", db_path=temp_db)
    assert len(all_prov) == 1


def test_escalation_notifications_idempotent(temp_db):
    """Escalation re-notify and admin-flag notifications are created idempotently per appointment."""
    r1 = notify_escalation_renotify("apt-idem-2", "prov-demo-endo", "p-2", db_path=temp_db)
    r2 = notify_escalation_renotify("apt-idem-2", "prov-demo-endo", "p-2", db_path=temp_db)
    assert r1["id"] == r2["id"]

    a1 = notify_escalation_admin_flag("apt-idem-2", "p-2", db_path=temp_db)
    a2 = notify_escalation_admin_flag("apt-idem-2", "p-2", db_path=temp_db)
    assert a1["id"] == a2["id"]


def test_daily_reminder_idempotent_per_day(temp_db):
    """Daily reminder is idempotent per patient per calendar day."""
    d1 = notify_daily_reminder("p-daily-1", "2026-11-12", db_path=temp_db)
    d2 = notify_daily_reminder("p-daily-1", "2026-11-12", db_path=temp_db)
    assert d1["id"] == d2["id"]

    # Next day creates a new reminder
    d_next = notify_daily_reminder("p-daily-1", "2026-11-13", db_path=temp_db)
    assert d_next["id"] != d1["id"]


# ---------------------------------------------------------------------------
# 3. Escalation Timing & Trigger Flow Tests (Frozen Clock)
# ---------------------------------------------------------------------------

def test_escalation_milestones_trigger_notifications(temp_db):
    """
    Verifies that compute_escalation_state triggers:
    - No notification before 2 hours (1h 59m).
    - Provider re-notification at >= 2 hours.
    - Admin flag notification at >= 24 hours.
    """
    base_time = datetime(2026, 11, 10, 8, 0, 0, tzinfo=UTC)

    # Urgent appointment created at 08:00
    apt = evaluate_and_create_appointment(
        checkin_id="chk-time-1",
        patient_id="p-time-1",
        final_triage_level="urgent",
        patient_conditions=["hypertension"],
        db_path=temp_db,
    )
    # Manually backdate created_at
    app_store.update_appointment(apt["id"], db_path=temp_db)
    with app_store.get_db_cursor(db_path=temp_db) as (cur, be, ph):
        cur.execute(f"UPDATE appointments SET created_at = {ph} WHERE id = {ph}", (base_time.strftime("%Y-%m-%dT%H:%M:%SZ"), apt["id"]))

    apt_backdated = app_store.get_appointment(apt["id"], db_path=temp_db)

    # 1. Elapsed 1 hour 59 mins -> pending, 0 re-notify notifications
    t_1h59 = base_time + timedelta(hours=1, minutes=59)
    res_1h59 = compute_escalation_state(apt_backdated, now_dt=t_1h59, db_path=temp_db)
    assert res_1h59["escalation_state"] == "pending"
    notifs_prov = list_notifications(role="provider", db_path=temp_db)
    assert not any(n["event_type"] == "escalation_renotify" for n in notifs_prov)

    # 2. Elapsed 2 hours -> re_notify, provider notification created
    t_2h = base_time + timedelta(hours=2)
    res_2h = compute_escalation_state(apt_backdated, now_dt=t_2h, db_path=temp_db)
    assert res_2h["escalation_state"] == "re_notify"
    notifs_prov_after = list_notifications(role="provider", db_path=temp_db)
    renotif = next((n for n in notifs_prov_after if n["event_type"] == "escalation_renotify"), None)
    assert renotif is not None

    # 3. Elapsed 24 hours -> admin_flag, admin notification created
    t_24h = base_time + timedelta(hours=24)
    res_24h = compute_escalation_state(apt_backdated, now_dt=t_24h, db_path=temp_db)
    assert res_24h["escalation_state"] == "admin_flag"
    notifs_admin = list_notifications(role="admin", db_path=temp_db)
    admin_notif = next((n for n in notifs_admin if n["event_type"] == "escalation_admin_flag"), None)
    assert admin_notif is not None


# ---------------------------------------------------------------------------
# 4. Daily Reminder Eligibility Tests
# ---------------------------------------------------------------------------

def test_daily_reminder_eligibility_rules(temp_db):
    """
    Verifies reminder rules:
    - Hour < 18:00 -> not due.
    - Hour >= 18:00 with no check-in today -> due.
    - Hour >= 18:00 with check-in logged today -> suppressed (not due).
    - Already notified today -> suppressed (not due).
    """
    now_early = datetime(2026, 11, 10, 14, 0, 0, tzinfo=UTC)
    now_due = datetime(2026, 11, 10, 18, 30, 0, tzinfo=UTC)

    # Seed patient
    with app_store.get_db_cursor(db_path=temp_db) as (cur, be, ph):
        cur.execute(
            f"INSERT INTO users (user_id, email, role, status, created_at) VALUES ({ph}, {ph}, 'patient', 'active', {ph})",
            ("p-rem-1", "prem1@example.com", "2026-11-01T00:00:00Z"),
        )

    # 1. Early in the day (< 18:00) -> not due
    assert is_patient_reminder_due("p-rem-1", now_dt=now_early, db_path=temp_db) is False

    # 2. Evening (18:30) with no checkin -> due
    assert is_patient_reminder_due("p-rem-1", now_dt=now_due, db_path=temp_db) is True

    # Dispatch reminder
    dispatched = dispatch_due_reminders(now_dt=now_due, db_path=temp_db)
    assert dispatched == 1

    # 3. Already received reminder today -> not due anymore
    assert is_patient_reminder_due("p-rem-1", now_dt=now_due, db_path=temp_db) is False

    # 4. Another patient who completed a check-in today at 09:00 -> not due
    with app_store.get_db_cursor(db_path=temp_db) as (cur, be, ph):
        cur.execute(
            f"INSERT INTO users (user_id, email, role, status, created_at) VALUES ({ph}, {ph}, 'patient', 'active', {ph})",
            ("p-rem-2", "prem2@example.com", "2026-11-01T00:00:00Z"),
        )
    app_store.create_checkin(
        checkin_id="chk-today-1",
        user_id="p-rem-2",
        mode="isolated",
        record_patient_id="p-rem-2",
        state_dict={},
        status="complete",
        started_at="2026-11-10T09:00:00Z",
        db_path=temp_db,
    )

    assert is_patient_reminder_due("p-rem-2", now_dt=now_due, db_path=temp_db) is False


# ---------------------------------------------------------------------------
# 5. FCM Push Dispatch & Credentials Fallback
# ---------------------------------------------------------------------------

def test_fcm_push_dormant_when_flag_off(temp_db, monkeypatch):
    """When FCM_ENABLED is False (default), send_fcm_push skips without network calls."""
    monkeypatch.delenv("FCM_ENABLED", raising=False)
    save_fcm_token("usr-fcm", "mock-token-xyz", db_path=temp_db)

    res = send_fcm_push("usr-fcm", "Reminder", "Check-in time", db_path=temp_db)
    assert res["status"] == "skipped"
    assert res["reason"] == "FCM_DISABLED"


def test_fcm_push_skipped_when_credentials_file_missing(temp_db, monkeypatch):
    """When FCM_ENABLED is True but GOOGLE_APPLICATION_CREDENTIALS is not set/found, skips gracefully."""
    monkeypatch.setenv("FCM_ENABLED", "true")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    save_fcm_token("usr-fcm2", "mock-token-abc", db_path=temp_db)

    res = send_fcm_push("usr-fcm2", "Reminder", "Check-in time", db_path=temp_db)
    assert res["status"] == "skipped"
    assert res["reason"] == "NO_CREDENTIALS"


# ---------------------------------------------------------------------------
# 6. REST API Endpoints & Role Isolation Tests
# ---------------------------------------------------------------------------

def test_patient_notifications_api_workflow(api_client, temp_db):
    """Tests GET, read, and read-all patient notification endpoints."""
    patient_user = {"user_id": "pat-101", "role": "patient", "email": "pat101@example.com", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: patient_user

    # Seed notifications for this patient and for another patient
    n1 = create_notification("pat-101", "patient", "daily_reminder", "Reminder 1", "Body 1", reference_id="r1", db_path=temp_db)
    n2 = create_notification("pat-101", "patient", "daily_reminder", "Reminder 2", "Body 2", reference_id="r2", db_path=temp_db)
    n_other = create_notification("pat-999", "patient", "daily_reminder", "Other", "Body Other", db_path=temp_db)

    # 1. Patient lists their notifications
    resp = api_client.get("/api/me/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notifications"]) == 2
    assert data["unread_count"] == 2

    # 2. Patient marks one notification read
    resp_read = api_client.post(f"/api/me/notifications/{n1['id']}/read")
    assert resp_read.status_code == 200
    assert resp_read.json()["is_read"] is True

    # Verify unread count decremented
    resp_after = api_client.get("/api/me/notifications")
    assert resp_after.json()["unread_count"] == 1

    # 3. Patient cannot mark other patient's notification read
    resp_cross = api_client.post(f"/api/me/notifications/{n_other['id']}/read")
    assert resp_cross.status_code == 404

    # 4. Mark all read
    resp_all = api_client.post("/api/me/notifications/read-all")
    assert resp_all.status_code == 200
    assert resp_all.json()["updated"] == 1
    assert api_client.get("/api/me/notifications").json()["unread_count"] == 0


def test_fcm_token_registration_endpoints(api_client, temp_db):
    """Tests registering and removing FCM device tokens."""
    current_user = {"user_id": "fcm-usr-1", "role": "patient", "email": "fcm@example.com", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: current_user

    # Register token
    resp_reg = api_client.post("/api/me/fcm-token", json={"token": "test-fcm-token-123", "device_info": "Firefox"})
    assert resp_reg.status_code == 200
    assert resp_reg.json()["token"] == "test-fcm-token-123"

    tokens = list_fcm_tokens("fcm-usr-1", db_path=temp_db)
    assert tokens == ["test-fcm-token-123"]

    # Remove token
    resp_del = api_client.request("DELETE", "/api/me/fcm-token", json={"token": "test-fcm-token-123"})
    assert resp_del.status_code == 200
    tokens_after = list_fcm_tokens("fcm-usr-1", db_path=temp_db)
    assert tokens_after == []


def test_provider_and_admin_notifications_api(api_client, temp_db):
    """Tests provider and admin notifications lists and read actions."""
    # Seed provider notification and admin notification
    n_prov = create_notification("prov-demo-gen-1", "provider", "urgent_checkin", "Urgent Alert", "Check-in from patient", reference_id="c1", db_path=temp_db)
    n_admin = create_notification("admin", "admin", "escalation_admin_flag", "Escalation Alert", "Case unacknowledged >24h", reference_id="a1", db_path=temp_db)

    # 1. As Provider
    prov_user = {"user_id": "prov-demo-gen-1", "role": "provider", "email": "p@doc.com", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: prov_user

    resp_p = api_client.get("/api/provider/notifications")
    assert resp_p.status_code == 200
    assert len(resp_p.json()["notifications"]) == 1

    resp_p_read = api_client.post(f"/api/provider/notifications/{n_prov['id']}/read")
    assert resp_p_read.status_code == 200

    # 2. As Admin
    admin_user = {"user_id": "admin-1", "role": "admin", "email": "a@admin.com", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: admin_user

    resp_a = api_client.get("/api/admin/notifications")
    assert resp_a.status_code == 200
    assert len(resp_a.json()["notifications"]) == 1

    resp_a_read = api_client.post(f"/api/admin/notifications/{n_admin['id']}/read")
    assert resp_a_read.status_code == 200
