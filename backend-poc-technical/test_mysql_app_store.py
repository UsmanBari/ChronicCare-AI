"""
Opt-in Integration & Equivalence Tests for MySQL App Store Backend.

Runs ONLY when:
1. Environment variable RUN_MYSQL_TESTS=1
2. MYSQL_URL is configured
3. Database name ends in '_dev' (safety guardrail)

Otherwise skips all tests cleanly so default CI (which has no MySQL) remains green.
"""

import os
import sys
import uuid
import pytest
from dotenv import load_dotenv

# Ensure backend root is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

env_file = os.path.join(script_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

from data_sources.db_config import get_mysql_connection_params
from data_sources import app_store, local_store


def _should_run_mysql_tests() -> bool:
    if os.environ.get("RUN_MYSQL_TESTS") != "1":
        return False
    mysql_url = os.environ.get("MYSQL_URL")
    if not mysql_url:
        return False
    try:
        params = get_mysql_connection_params(mysql_url)
        return params["database"].endswith("_dev")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _should_run_mysql_tests(),
    reason="MySQL tests skipped: RUN_MYSQL_TESTS=1 not set or database does not end in '_dev'"
)


def test_mysql_app_store_migrations_and_full_crud():
    """
    Verifies that migrate() is idempotent on MySQL and all entity tables
    (users, audit_log, profiles, consent, EHR, checkins, results, reviews) function correctly.
    """
    # 1. Idempotent migrations
    app_store.migrate(backend="mysql")
    app_store.migrate(backend="mysql")

    test_uid = f"user-mysql-{uuid.uuid4().hex[:8]}"
    test_email = f"{test_uid}@test.local"

    # 2. Users & Roles
    user = app_store.create_user(
        user_id=test_uid,
        email=test_email,
        role="patient",
        display_name="MySQL Test User",
        status="active",
        backend="mysql",
    )
    assert user["user_id"] == test_uid
    assert user["role"] == "patient"

    # Role update
    updated = app_store.update_user_role(test_uid, "provider", backend="mysql")
    assert updated["role"] == "provider"

    # Retrieve by ID & Email
    by_id = app_store.get_user_by_id(test_uid, backend="mysql")
    assert by_id["email"] == test_email
    by_email = app_store.get_user_by_email(test_email, backend="mysql")
    assert by_email["user_id"] == test_uid

    # 3. Audit Logging (Append-Only)
    app_store.append_audit(
        actor_user_id=test_uid,
        action="mysql_test_audit_event",
        target="target-resource-1",
        outcome="ok",
        detail={"event_type": "unit_test", "counter": 42},
        backend="mysql",
    )
    logs = app_store.get_audit_logs(limit=20, backend="mysql")
    matching_logs = [l for l in logs if l["actor_user_id"] == test_uid and l["action"] == "mysql_test_audit_event"]
    assert len(matching_logs) >= 1
    assert matching_logs[0]["detail"]["counter"] == 42

    # 4. Patient Profile & Consent
    saved_prof = app_store.upsert_patient_profile(
        user_id=test_uid,
        conditions=["diabetes", "hypertension"],
        on_insulin_or_sulfonylurea=True,
        language="en",
        backend="mysql",
    )
    assert saved_prof["conditions"] == ["diabetes", "hypertension"]
    assert saved_prof["on_insulin_or_sulfonylurea"] is True
    assert saved_prof["language"] == "en"

    loaded_prof = app_store.get_patient_profile(test_uid, backend="mysql")
    assert loaded_prof["conditions"] == ["diabetes", "hypertension"]
    assert loaded_prof["on_insulin_or_sulfonylurea"] is True

    # Consent lifecycle
    consent_rec = app_store.set_patient_consent(test_uid, granted=True, backend="mysql")
    assert consent_rec["consent_granted_at"] is not None
    assert consent_rec["consent_revoked_at"] is None

    consent_rev = app_store.set_patient_consent(test_uid, granted=False, backend="mysql")
    assert consent_rev["consent_revoked_at"] is not None

    # 5. EHR Connections
    conn_id = f"conn-{uuid.uuid4().hex[:8]}"
    rec = app_store.record_ehr_connection(
        connection_id=conn_id,
        user_id=test_uid,
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-PATIENT-999",
        status="active",
        backend="mysql",
    )
    assert rec["status"] == "active"
    active_conn = app_store.get_active_ehr_connection(test_uid, backend="mysql")
    assert active_conn["connection_id"] == conn_id
    assert active_conn["external_patient_id"] == "EXT-PATIENT-999"

    app_store.revoke_ehr_connection(test_uid, backend="mysql")
    assert app_store.get_active_ehr_connection(test_uid, backend="mysql") is None

    # 6. Check-in Lifecycle & Review Queue
    chk_id = f"chk-{uuid.uuid4().hex[:8]}"
    rec_pid = f"local-{test_uid}"
    
    # Ensure local patient exists
    local_store.add_local_patient_if_missing(rec_pid, "MySQL Checkin Patient", "1975-05-15", backend="mysql")

    chk = app_store.create_checkin(
        checkin_id=chk_id,
        user_id=test_uid,
        mode="isolated",
        record_patient_id=rec_pid,
        state_dict={"step": "glucose_reading", "answers": {}},
        backend="mysql",
    )
    assert chk["checkin_id"] == chk_id
    assert chk["status"] == "in_progress"

    app_store.update_checkin_state(
        checkin_id=chk_id,
        state_dict={"step": "complete", "answers": {"glucose_reading": 155.0}},
        status="completed",
        backend="mysql",
    )

    result = app_store.create_checkin_result(
        checkin_id=chk_id,
        emergency=False,
        intakes=[{"condition": "diabetes", "readings": [{"observation_type": "glucose", "value": 155.0, "unit": "mg/dL"}]}],
        reconciliation={"summary": {"conflicts": 1}},
        verification={"summary": {"requires_review": 1, "severity_high": 1}},
        requires_review=True,
        max_severity="high",
        review_status="open",
        backend="mysql",
    )
    assert result["checkin_id"] == chk_id
    assert result["requires_review"] is True
    assert result["max_severity"] == "high"

    # Review Queue & Action
    queue = app_store.get_provider_review_queue(review_status="open", backend="mysql")
    queue_item = next((q for q in queue if q["checkin_id"] == chk_id), None)
    assert queue_item is not None
    assert queue_item["max_severity"] == "high"

    action = app_store.append_review_action(
        checkin_id=chk_id,
        provider_user_id=test_uid,
        action="escalated",
        note="Blood glucose elevated; escalated to clinical team.",
        backend="mysql",
    )
    assert action["action"] == "escalated"
    actions = app_store.get_review_actions(chk_id, backend="mysql")
    assert len(actions) == 1
    assert actions[0]["provider_user_id"] == test_uid


def test_sqlite_mysql_app_store_equivalence(tmp_path):
    """
    Equivalence Test: executes identical sequences of profile, consent, and audit operations
    on SQLite and MySQL and verifies observable state parity.
    """
    test_db_path = str(tmp_path / "equiv_test.db")
    app_store.migrate(backend="sqlite", db_path=test_db_path)
    app_store.migrate(backend="mysql")

    uid = f"user-equiv-{uuid.uuid4().hex[:8]}"
    email = f"{uid}@equiv.local"

    # 1. Create User
    u_sql = app_store.create_user(uid, email, "patient", "Equiv Patient", "active", backend="sqlite", db_path=test_db_path)
    u_my = app_store.create_user(uid, email, "patient", "Equiv Patient", "active", backend="mysql")
    assert u_sql["user_id"] == u_my["user_id"]
    assert u_sql["email"] == u_my["email"]
    assert u_sql["role"] == u_my["role"]

    # 2. Upsert Profile
    p_sql = app_store.upsert_patient_profile(
        user_id=uid,
        conditions=["hypertension"],
        on_insulin_or_sulfonylurea=False,
        language="ur",
        backend="sqlite",
        db_path=test_db_path,
    )
    p_my = app_store.upsert_patient_profile(
        user_id=uid,
        conditions=["hypertension"],
        on_insulin_or_sulfonylurea=False,
        language="ur",
        backend="mysql",
    )
    assert p_sql["conditions"] == p_my["conditions"]
    assert p_sql["on_insulin_or_sulfonylurea"] == p_my["on_insulin_or_sulfonylurea"]
    assert p_sql["language"] == p_my["language"]

    # 3. Consent
    c_sql = app_store.set_patient_consent(uid, granted=True, backend="sqlite", db_path=test_db_path)
    c_my = app_store.set_patient_consent(uid, granted=True, backend="mysql")
    assert (c_sql["consent_granted_at"] is not None) == (c_my["consent_granted_at"] is not None)
