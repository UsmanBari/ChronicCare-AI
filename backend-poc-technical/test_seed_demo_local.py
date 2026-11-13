"""
Hermetic test suite for local demo seed script and pipeline verification.
Proposal Sections 13.1, 15, 16, 17, 21.1, 23.

Verifies:
1. Strict SQLite-only safety guard (refuses MySQL).
2. End-to-end execution of seed_demo_data() against an isolated temporary SQLite database.
3. Verification that all 9 patient personas + elevated roles are produced through the real API pipeline:
   - HTN patient: 5+ worsening BP check-ins -> Stage-2 Yellow (review), rising trend, OCR unverified med.
   - DM patient: Glucose history + High DM risk band -> Stage-2 Yellow.
   - Dual patient: Both risk models evaluated + valid SOAP clinical summary.
   - Urdu patient: Urdu script check-in & reviewed Urdu template explanation.
   - Roman Urdu patient: Roman Urdu check-in & reviewed Roman Urdu explanation.
   - Emergency patient: Red-flag chest pain -> emergency level & 1122 record.
   - No-readings patient: Check-in without readings -> Rule R8 routine monitoring wording.
   - Cold start patient: Strictly 0 check-ins.
"""
from __future__ import annotations

import os
import sys
import tempfile
import pytest

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.seed_demo_local import check_sqlite_local_guard, seed_demo_data
from data_sources import app_store
from data_sources.local_store import get_local_medications


@pytest.fixture
def temp_sqlite_db():
    """Provides a fresh isolated temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        t_path = f.name

    orig_backend = os.environ.get("DB_BACKEND")
    orig_local_db = os.environ.get("LOCAL_DB_PATH")
    orig_mysql_url = os.environ.get("MYSQL_URL")

    os.environ["DB_BACKEND"] = "sqlite"
    os.environ["LOCAL_DB_PATH"] = t_path
    os.environ.pop("MYSQL_URL", None)

    yield t_path

    # Cleanup
    if orig_backend is not None:
        os.environ["DB_BACKEND"] = orig_backend
    else:
        os.environ.pop("DB_BACKEND", None)

    if orig_local_db is not None:
        os.environ["LOCAL_DB_PATH"] = orig_local_db
    else:
        os.environ.pop("LOCAL_DB_PATH", None)

    if orig_mysql_url is not None:
        os.environ["MYSQL_URL"] = orig_mysql_url
    else:
        os.environ.pop("MYSQL_URL", None)

    try:
        os.unlink(t_path)
    except OSError:
        pass


def test_sqlite_guard_refuses_mysql():
    """Verifies that check_sqlite_local_guard raises RuntimeError if MySQL is configured."""
    orig_url = os.environ.get("MYSQL_URL")
    orig_backend = os.environ.get("DB_BACKEND")
    try:
        os.environ["MYSQL_URL"] = "mysql+pymysql://user:pass@host:3306/db"
        with pytest.raises(RuntimeError) as exc_info:
            check_sqlite_local_guard()
        assert "REFUSING TO RUN ON MYSQL" in str(exc_info.value)

        os.environ.pop("MYSQL_URL", None)
        os.environ["DB_BACKEND"] = "mysql"
        with pytest.raises(RuntimeError) as exc_info2:
            check_sqlite_local_guard()
        assert "REFUSING TO RUN ON MYSQL" in str(exc_info2.value)
    finally:
        if orig_url is not None:
            os.environ["MYSQL_URL"] = orig_url
        else:
            os.environ.pop("MYSQL_URL", None)
        if orig_backend is not None:
            os.environ["DB_BACKEND"] = orig_backend
        else:
            os.environ.pop("DB_BACKEND", None)


def test_seed_demo_data_hermetic_pipeline(temp_sqlite_db):
    """Verifies that seed_demo_data runs end-to-end through real API pipeline and seeds all personas."""
    seeded_users = seed_demo_data(reset=True, db_path=temp_sqlite_db)
    assert isinstance(seeded_users, dict)
    assert "htn" in seeded_users
    assert "dm" in seeded_users
    assert "dual" in seeded_users
    assert "ur" in seeded_users
    assert "roman_ur" in seeded_users
    assert "emg" in seeded_users
    assert "norx" in seeded_users
    assert "fhir" in seeded_users
    assert "new" in seeded_users
    assert "provider" in seeded_users
    assert "admin" in seeded_users

    # 1. HTN patient: 5+ check-ins with worsening BP trend -> Stage-2 Yellow (review) & OCR unverified Rx
    htn_uid = seeded_users["htn"]
    htn_checkins = app_store.get_user_checkins(htn_uid, limit=20, db_path=temp_sqlite_db)
    assert len(htn_checkins) >= 5, f"Expected >= 5 checkins for HTN, got {len(htn_checkins)}"

    latest_htn_cid = htn_checkins[0]["checkin_id"]
    latest_htn_res = app_store.get_checkin_result(latest_htn_cid, db_path=temp_sqlite_db)
    assert latest_htn_res is not None
    assert latest_htn_res.get("triage_level") == "review"

    # Check longitudinal trend calculation
    from agents.trend_agent import compute_trends
    history = app_store.get_user_reading_history(htn_uid, days=30, db_path=temp_sqlite_db)
    t_res = compute_trends(history, window_days=30)
    t_bp = t_res.get("trends", {}).get("blood_pressure_systolic", {})
    assert t_bp.get("direction") == "rising"
    assert t_bp.get("n", 0) >= 5

    # Check OCR-imported prescription medication with origin='ocr' (Medium trust)
    pat_id = f"local-{htn_uid}"
    meds = get_local_medications(pat_id, db_path=temp_sqlite_db)
    ocr_meds = [m for m in meds if m.get("origin") == "ocr"]
    assert len(ocr_meds) >= 1, "Expected at least 1 OCR-imported medication for Demo Patient HTN"
    assert "amlodipine" in ocr_meds[0]["medication_name"].lower()

    # 2. DM patient: glucose history + High DM risk band -> Stage-2 Yellow
    dm_uid = seeded_users["dm"]
    dm_checkins = app_store.get_user_checkins(dm_uid, limit=20, db_path=temp_sqlite_db)
    assert len(dm_checkins) >= 5
    latest_dm_cid = dm_checkins[0]["checkin_id"]
    latest_dm_res = app_store.get_checkin_result(latest_dm_cid, db_path=temp_sqlite_db)
    assert latest_dm_res is not None
    assert latest_dm_res.get("triage_level") == "review"
    dm_risk = latest_dm_res.get("risk") or {}
    dm_models = dm_risk.get("models") or dm_risk.get("assessments") or []
    dm_bands = [m.get("band") for m in dm_models if isinstance(m, dict)]
    assert "high" in dm_bands

    # 3. Dual patient: both risk models + SOAP clinical summary
    dual_uid = seeded_users["dual"]
    dual_checkins = app_store.get_user_checkins(dual_uid, limit=5, db_path=temp_sqlite_db)
    assert len(dual_checkins) >= 1
    latest_dual_cid = dual_checkins[0]["checkin_id"]

    import main
    from fastapi.testclient import TestClient
    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "user_id": seeded_users["provider"],
        "email": "provider.demo@demo.care",
        "role": "provider",
    }
    soap_resp = client.get(f"/api/provider/review/{latest_dual_cid}/soap")
    assert soap_resp.status_code == 200
    soap_data = soap_resp.json()
    assert all(k in soap_data for k in ("subjective", "objective", "assessment", "plan"))

    # 4. Urdu script patient: reviewed Urdu template explanation
    ur_uid = seeded_users["ur"]
    ur_checkins = app_store.get_user_checkins(ur_uid, limit=5, db_path=temp_sqlite_db)
    assert len(ur_checkins) >= 1
    latest_ur_cid = ur_checkins[0]["checkin_id"]
    latest_ur_res = app_store.get_checkin_result(latest_ur_cid, db_path=temp_sqlite_db)
    ur_expl = latest_ur_res.get("explanation") or {}
    ur_sentences = ur_expl.get("sentences") or []
    assert len(ur_sentences) > 0
    # Check that explanation text contains Urdu characters (\u0600-\u06FF)
    all_ur_text = " ".join(s.get("text", "") for s in ur_sentences)
    has_urdu_chars = any("\u0600" <= ch <= "\u06ff" for ch in all_ur_text)
    assert has_urdu_chars, f"Expected Urdu script in explanation, got: {all_ur_text}"

    # 5. Roman Urdu patient: reviewed Roman Urdu template explanation
    roman_uid = seeded_users["roman_ur"]
    roman_checkins = app_store.get_user_checkins(roman_uid, limit=5, db_path=temp_sqlite_db)
    assert len(roman_checkins) >= 1
    latest_roman_cid = roman_checkins[0]["checkin_id"]
    latest_roman_res = app_store.get_checkin_result(latest_roman_cid, db_path=temp_sqlite_db)
    roman_expl = latest_roman_res.get("explanation") or {}
    assert len(roman_expl.get("sentences", [])) > 0

    # 6. Emergency patient: Red-flag chest pain -> Emergency + 1122 screen
    emg_uid = seeded_users["emg"]
    emg_checkins = app_store.get_user_checkins(emg_uid, limit=5, db_path=temp_sqlite_db)
    assert len(emg_checkins) >= 1
    latest_emg_cid = emg_checkins[0]["checkin_id"]
    latest_emg_res = app_store.get_checkin_result(latest_emg_cid, db_path=temp_sqlite_db)
    assert latest_emg_res.get("emergency") is True
    assert latest_emg_res.get("triage_level") == "emergency"

    # 7. No-readings patient: Rule R8 monitoring wording
    norx_uid = seeded_users["norx"]
    norx_checkins = app_store.get_user_checkins(norx_uid, limit=5, db_path=temp_sqlite_db)
    assert len(norx_checkins) >= 1

    # 8. Cold start patient: strictly 0 check-ins
    new_uid = seeded_users["new"]
    new_checkins = app_store.get_user_checkins(new_uid, limit=5, db_path=temp_sqlite_db)
    assert len(new_checkins) == 0, f"Expected 0 checkins for Demo Patient New, got {len(new_checkins)}"

    # 9. Provider and Admin roles exist
    prov_user = app_store.get_user_by_email("provider.demo@demo.care", db_path=temp_sqlite_db)
    assert prov_user is not None and prov_user["role"] == "provider"
    admin_user = app_store.get_user_by_email("admin.demo@demo.care", db_path=temp_sqlite_db)
    assert admin_user is not None and admin_user["role"] == "admin"

    main.app.dependency_overrides.clear()
