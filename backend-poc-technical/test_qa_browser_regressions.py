"""
Regression tests for QA Browser Test Findings (Q2-Q12).
Task: A3 (Part A) of 14 Nov Corrections.

Covers:
- Q2: Patient appointment list in isolated & connected modes; determine_specialty per condition.
- Q3: SOAP emergency danger category & medication source labels (FHIR vs self-reported).
- Q4: get_fhir_medications follows 'next' pagination links across multiple pages.
- Q5: /api/admin/stats and /api/admin/users RBAC (403 for patient/provider, 200 for admin) & counts.
- Q8/Q11: Two readings in same minute both kept; span < 2 days returns slope_per_week None.
- Q10: EHR demographic mismatch requires confirm_identity_mismatch and writes audit log.
- Q11: FHIR export bundle contains Condition resource.
- Q12: Profile language survives check-in lifecycle.
"""

from __future__ import annotations

import datetime
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from main import app, get_current_user, extract_bearer_token
from services.appointment_service import determine_specialty
from agents.soap_agent import build_soap
from data_sources import fhir_client
from data_sources.app_store import (
    get_db_cursor,
    create_user,
    upsert_patient_profile,
    set_patient_consent,
    set_patient_provider_notification_consent,
    record_ehr_connection,
    get_audit_logs,
    list_patient_appointments,
)
from data_sources.local_store import (
    add_local_observation,
    add_local_patient_if_missing,
    get_local_observations,
)
from agents.trend_agent import compute_trends

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# Q2: Appointments & Specialty Determination
# -----------------------------------------------------------------------------

def test_q2_determine_specialty():
    """determine_specialty returns dedicated specialties, never 'general'."""
    assert determine_specialty(["diabetes"]) == "endocrinology"
    assert determine_specialty(["hypertension"]) == "cardiology_im"
    assert determine_specialty(["diabetes", "hypertension"]) == "internal_medicine"
    assert determine_specialty(["hypertension", "diabetes"]) == "internal_medicine"


def test_q2_patient_appointments_isolated_and_connected_modes():
    """A patient's own appointment shows up in isolated mode (local- prefix) and connected mode (FHIR ID)."""
    uid_iso = "test_q2_iso_user"
    uid_conn = "test_q2_conn_user"

    for uid in (uid_iso, uid_conn):
        try:
            create_user(user_id=uid, email=f"{uid}@demo.care", role="patient")
        except Exception:
            pass
        set_patient_consent(user_id=uid, granted=True)
        set_patient_provider_notification_consent(user_id=uid, granted=True)
        upsert_patient_profile(
            user_id=uid,
            conditions=["hypertension"],
            date_of_birth="1975-01-01",
            inclusion_confirmed=True,
            language="en",
        )

    # 1. Isolated mode: appointment stored under local-test_q2_iso_user
    with get_db_cursor() as (cursor, be, ph):
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO appointments (id, patient_id, checkin_id, provider_id, specialty, urgency, mode, status, slot_date, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            ("apt-q2-iso-1", f"local-{uid_iso}", "chk-q2-1", "doc-1", "cardiology_im", "routine", "isolated", "booked", "2026-11-20", "2026-11-14T08:00:00Z"),
        )

    # Verify query for uid_iso finds the appointment
    iso_apts = list_patient_appointments(patient_id=uid_iso)
    assert any(a["id"] == "apt-q2-iso-1" for a in iso_apts), "Isolated mode appointment with local- prefix must be found"

    # 2. Connected mode: record an EHR connection with external_patient_id 'sim-q2-ext'
    record_ehr_connection(
        connection_id=f"conn-{uuid.uuid4()}",
        user_id=uid_conn,
        ehr_system_id="sim-hospital",
        external_patient_id="sim-q2-ext",
        status="active",
    )
    with get_db_cursor() as (cursor, be, ph):
        cursor.execute(
            f"""
            INSERT OR REPLACE INTO appointments (id, patient_id, checkin_id, provider_id, specialty, urgency, mode, status, slot_date, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            ("apt-q2-conn-1", "sim-q2-ext", "chk-q2-2", "doc-1", "endocrinology", "routine", "connected", "booked", "2026-11-21", "2026-11-14T08:30:00Z"),
        )

    conn_apts = list_patient_appointments(patient_id=uid_conn)
    assert any(a["id"] == "apt-q2-conn-1" for a in conn_apts), "Connected mode appointment with external FHIR ID must be found"


# -----------------------------------------------------------------------------
# Q3: SOAP Danger Category & Medication Source Labels
# -----------------------------------------------------------------------------

def test_q3_soap_emergency_danger_category_and_medication_sources():
    """SOAP for emergency check-in lists detected danger category (not 'None') and medication source labels."""
    emergency_checkin = {
        "checkin_id": "chk-q3-emg",
        "user_id": "u-q3",
        "patient_id": "u-q3",
        "condition": "hypertension",
        "mode": "connected",
        "state": {
            "symptoms": ["chest pain radiating to arm"],
            "stage1_reason": "chest_pain",
            "intakes": [
                {
                    "readings": [
                        {
                            "observation_type": "blood_pressure_systolic",
                            "value": 180,
                            "unit": "mmHg",
                            "source": "fhir",
                        },
                        {
                            "observation_type": "blood_pressure_diastolic",
                            "value": 110,
                            "unit": "mmHg",
                            "source": "self_reported",
                        },
                    ]
                }
            ],
        },
    }
    result = {
        "emergency": True,
        "triage_level": "emergency",
        "trigger_category": "chest_pain",
    }

    soap = build_soap(
        emergency_checkin,
        result=result,
    )

    subj_text = " ".join(soap["subjective"])
    assert "chest_pain" in subj_text or "Chest Pain" in subj_text
    assert "Danger words: None detected" not in subj_text

    obj_text = " ".join(soap["objective"])
    assert "Source: FHIR" in obj_text
    assert "Source: Self-Report" in obj_text


# -----------------------------------------------------------------------------
# Q4: FHIR Medications Pagination
# -----------------------------------------------------------------------------

def test_q4_get_fhir_medications_pagination():
    """get_fhir_medications follows 'next' links across pages to retrieve all medications."""
    page1_bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "MedicationRequest", "id": "med-1", "medicationCodeableConcept": {"text": "Amlodipine"}}},
            {"resource": {"resourceType": "MedicationRequest", "id": "med-2", "medicationCodeableConcept": {"text": "Lisinopril"}}},
        ],
        "link": [
            {"relation": "self", "url": "http://fhir.mock/MedicationRequest?patient=p1&_count=100"},
            {"relation": "next", "url": "http://fhir.mock/MedicationRequest?patient=p1&_count=100&page=2"},
        ],
    }
    page2_bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "MedicationRequest", "id": "med-3", "medicationCodeableConcept": {"text": "Metformin"}}},
        ],
        "link": [
            {"relation": "self", "url": "http://fhir.mock/MedicationRequest?patient=p1&_count=100&page=2"},
        ],
    }

    def mock_fhir_get(base_url, endpoint, **kwargs):
        if "page=2" in endpoint or (kwargs.get("params") and kwargs["params"].get("page") == 2):
            return page2_bundle
        return page1_bundle

    with patch.object(fhir_client, "fhir_get", side_effect=mock_fhir_get):
        meds = fhir_client.get_fhir_medications("p1", base_url="http://fhir.mock")
        assert len(meds) == 3
        med_ids = [m["id"] for m in meds]
        assert med_ids == ["med-1", "med-2", "med-3"]


# -----------------------------------------------------------------------------
# Q5: Admin Stats and Users RBAC & Counts
# -----------------------------------------------------------------------------

def test_q5_admin_endpoints_rbac_and_counts():
    """/api/admin/stats and /api/admin/users return 403 for patient & provider, 200 for admin with accurate counts."""
    # 1. Patient access -> 403
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u-pat", "email": "p@demo.care", "role": "patient"}
    app.dependency_overrides[extract_bearer_token] = lambda: "tok"

    r_stats_pat = client.get("/api/admin/stats")
    assert r_stats_pat.status_code == 403

    r_users_pat = client.get("/api/admin/users")
    assert r_users_pat.status_code == 403

    # 2. Provider access -> 403
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u-doc", "email": "d@demo.care", "role": "provider"}

    r_stats_doc = client.get("/api/admin/stats")
    assert r_stats_doc.status_code == 403

    r_users_doc = client.get("/api/admin/users")
    assert r_users_doc.status_code == 403

    # 3. Admin access -> 200
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u-adm", "email": "a@demo.care", "role": "admin"}

    r_stats_adm = client.get("/api/admin/stats")
    assert r_stats_adm.status_code == 200
    data = r_stats_adm.json()
    assert "total_users" in data
    assert "total_patients" in data
    assert "total_providers" in data
    assert data["total_users"] >= data["total_patients"]

    r_users_adm = client.get("/api/admin/users")
    assert r_users_adm.status_code == 200
    users = r_users_adm.json()["users"]
    assert isinstance(users, list)
    assert len(users) == data["total_users"]


# -----------------------------------------------------------------------------
# Q8/Q11: Reading Storage in Same Minute & Trend Span < 2 Days
# -----------------------------------------------------------------------------

def test_q8_two_readings_same_minute_kept():
    """Two readings saved within the exact same minute are both preserved in storage."""
    uid = "test_q8_same_minute_patient"
    try:
        create_user(user_id=uid, email=f"{uid}@demo.care", role="patient")
    except Exception:
        pass
    patient_id = f"local-{uid}"
    add_local_patient_if_missing(patient_id, name="Test Patient")

    ts1 = "2026-11-14T09:15:10Z"
    ts2 = "2026-11-14T09:15:45Z"

    id1 = f"local-obs-{uuid.uuid4()}"
    id2 = f"local-obs-{uuid.uuid4()}"

    add_local_observation(
        id=id1,
        patient_id=patient_id,
        observation_type="blood_pressure_systolic",
        value=130.0,
        unit="mmHg",
        timestamp=ts1,
    )
    add_local_observation(
        id=id2,
        patient_id=patient_id,
        observation_type="blood_pressure_systolic",
        value=134.0,
        unit="mmHg",
        timestamp=ts2,
    )

    obs = get_local_observations(patient_id=patient_id)
    systolics = [o for o in obs if o["type"] == "blood_pressure_systolic" and o["timestamp"].startswith("2026-11-14T09:15")]
    assert len(systolics) >= 2, "Both readings in the same minute must be stored without collision"


def test_q8_readings_under_two_days_gives_slope_none():
    """Readings spanning less than 2 days return slope_per_week as None."""
    history = [
        {"observation_type": "blood_pressure_systolic", "value": 130.0, "timestamp": "2026-11-14T00:00:00Z"},
        {"observation_type": "blood_pressure_systolic", "value": 134.0, "timestamp": "2026-11-14T12:00:00Z"},
        {"observation_type": "blood_pressure_systolic", "value": 138.0, "timestamp": "2026-11-15T06:00:00Z"},
    ]
    res = compute_trends(history=history, now="2026-11-15T08:00:00Z", window_days=30)
    trend = res["trends"]["blood_pressure_systolic"]
    assert trend["slope_per_week"] is None, "Span < 2 days must produce slope_per_week = None"


# -----------------------------------------------------------------------------
# Q10: EHR Demographic Mismatch & Confirmation
# -----------------------------------------------------------------------------

def test_q10_ehr_demographic_mismatch_and_audit():
    """DOB/gender mismatch on non-simulated EHR link requires confirm_identity_mismatch and logs audit row."""
    uid = "test_q10_ehr_patient"
    try:
        create_user(user_id=uid, email=f"{uid}@demo.care", role="patient")
    except Exception:
        pass
    set_patient_consent(user_id=uid, granted=True)
    set_patient_provider_notification_consent(user_id=uid, granted=True)
    upsert_patient_profile(
        user_id=uid,
        conditions=["hypertension"],
        date_of_birth="1960-01-01",  # Profile DOB
        sex_at_birth="male",
        inclusion_confirmed=True,
        language="en",
    )

    app.dependency_overrides[get_current_user] = lambda: {"user_id": uid, "email": f"{uid}@demo.care", "role": "patient"}
    app.dependency_overrides[extract_bearer_token] = lambda: "tok"

    # Mock non-simulated EHR returning patient with DOB 1980 (20-year mismatch)
    mock_system = {
        "id": "real-ehr-1",
        "system_name": "Hospital EHR",
        "display_name": "Hospital EHR",
        "fhir_base_url": "http://ehr.real.org",
        "kind": "epic",  # Non-simulated
        "enabled": True,
    }
    mock_fhir_patient = {
        "resourceType": "Patient",
        "id": "ext-10",
        "birthDate": "1980-05-15",
        "gender": "male",
    }

    with patch("main.get_ehr_system_by_id", return_value=mock_system), \
         patch("main.get_fhir_patient", return_value=mock_fhir_patient):

        # 1. Without confirmation -> 409 Conflict
        r_unconfirmed = client.post(
            "/api/ehr/connect",
            json={"ehr_system_id": "real-ehr-1", "external_patient_id": "ext-10", "confirm_identity_mismatch": False},
        )
        assert r_unconfirmed.status_code == 409
        assert "EHR demographic mismatch" in r_unconfirmed.json()["detail"]

        # 2. With confirm_identity_mismatch=True -> 200 OK + audit log
        r_confirmed = client.post(
            "/api/ehr/connect",
            json={"ehr_system_id": "real-ehr-1", "external_patient_id": "ext-10", "confirm_identity_mismatch": True},
        )
        assert r_confirmed.status_code == 200

        # Check audit event written
        audits = get_audit_logs(limit=50)
        mismatch_audits = [a for a in audits if a["action"] == "ehr_identity_mismatch_confirmed"]
        assert len(mismatch_audits) > 0, "Confirmation must write ehr_identity_mismatch_confirmed audit event"


# -----------------------------------------------------------------------------
# Q11: FHIR Export Bundle Condition Resource
# -----------------------------------------------------------------------------

def test_q11_fhir_export_bundle_contains_condition():
    """FHIR export bundle contains Condition resources for the patient's chronic conditions."""
    uid = "test_q11_export_patient"
    try:
        create_user(user_id=uid, email=f"{uid}@demo.care", role="patient")
    except Exception:
        pass
    upsert_patient_profile(
        user_id=uid,
        conditions=["hypertension", "diabetes"],
        date_of_birth="1970-01-01",
        inclusion_confirmed=True,
        language="en",
    )

    app.dependency_overrides[get_current_user] = lambda: {"user_id": uid, "email": f"{uid}@demo.care", "role": "patient"}
    app.dependency_overrides[extract_bearer_token] = lambda: "tok"

    resp = client.get("/api/me/record/export?format=fhir")
    assert resp.status_code == 200
    bundle = resp.json()
    assert bundle.get("resourceType") == "Bundle"
    entries = bundle.get("entry", [])

    conditions = [e["resource"] for e in entries if e.get("resource", {}).get("resourceType") == "Condition"]
    assert len(conditions) >= 2, "Export bundle must contain Condition resources for chronic conditions"
    cond_texts = [c["code"]["text"] for c in conditions]
    assert "hypertension" in cond_texts
    assert "diabetes" in cond_texts


# -----------------------------------------------------------------------------
# Q12: Profile Language Lifecycle
# -----------------------------------------------------------------------------

def test_q12_profile_language_survives_checkin():
    """Patient profile language ('ur') survives starting and completing a check-in."""
    uid = "test_q12_lang_patient"
    try:
        create_user(user_id=uid, email=f"{uid}@demo.care", role="patient")
    except Exception:
        pass
    set_patient_consent(user_id=uid, granted=True)
    set_patient_provider_notification_consent(user_id=uid, granted=True)
    upsert_patient_profile(
        user_id=uid,
        conditions=["hypertension"],
        date_of_birth="1968-04-10",
        inclusion_confirmed=True,
        language="ur",
    )

    app.dependency_overrides[get_current_user] = lambda: {"user_id": uid, "email": f"{uid}@demo.care", "role": "patient"}
    app.dependency_overrides[extract_bearer_token] = lambda: "tok"

    # Start check-in
    r_start = client.post("/api/checkins/start", json={"condition": "hypertension"})
    assert r_start.status_code == 200
    chk_id = r_start.json()["checkin_id"]

    # Answer turns until complete
    for _ in range(10):
        r_ans = client.post(f"/api/checkins/{chk_id}/answer", json={"answer": "120/80"})
        assert r_ans.status_code == 200
        if r_ans.json().get("complete"):
            break

    # Complete check-in
    r_comp = client.post(f"/api/checkins/{chk_id}/complete")
    assert r_comp.status_code == 200

    # Profile language must remain 'ur'
    from data_sources.app_store import get_patient_profile
    prof = get_patient_profile(user_id=uid)
    assert prof["language"] == "ur", "Profile language must be preserved as 'ur'"
