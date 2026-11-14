"""
Seed script for local demo environment (SQLite only).
Proposal Sections 13.1, 15, 16, 17, 21.1, 23.

Seeds 9 demo personas, 1 provider, and 1 admin through the real API pipeline:
1. Demo Patient HTN (demo_patient_htn@demo.care):
   5+ check-ins with worsening BP trend -> Yellow (review) with trend reason & BP chart.
   Includes OCR-imported unverified prescription medication (Medium trust / Unverified badge).
2. Demo Patient DM (demo_patient_dm@demo.care):
   Glucose history + High DM risk band -> Stage-2 raise to Yellow (provider sees probability + SHAP drivers,
   patient sees band sentence only).
3. Demo Patient Dual (demo_patient_dual@demo.care):
   Both risk models (diabetes full NHANES + CHD10 Framingham), and structured SOAP clinical summary.
4. Demo Patient Urdu (demo_patient_ur@demo.care):
   Urdu-script patient (ur) with check-in history and reviewed Urdu template explanation.
5. Demo Patient Roman Urdu (demo_patient_roman_ur@demo.care):
   Roman Urdu patient (roman_ur) with check-in history and reviewed Roman Urdu template explanation.
6. Demo Patient Emergency (demo_patient_emg@demo.care):
   Red-flag acute chest pain -> immediate emergency trigger & 1122 bypass screen record.
7. Demo Patient No-Readings (demo_patient_norx@demo.care):
   Check-in without vital readings -> Rule R8 routine monitoring template wording.
8. Demo Patient FHIR (demo_patient_fhir@demo.care):
   Connected-mode patient on FhirSim ('demo-hospital' / 'sim-bilal').
9. Demo Patient New (demo_patient_new@demo.care):
   Cold start: strictly 0 check-ins.
Plus Demo Provider (provider.demo@demo.care) and Demo Admin (admin.demo@demo.care).

Strictly refuses to run against MySQL or any remote database.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-poc-technical")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from data_sources.db_config import get_db_backend, get_sqlite_path
from data_sources.app_store import (
    get_db_cursor,
    migrate,
    get_user_by_email,
    create_user,
    upsert_patient_profile,
    set_patient_consent,
    set_patient_provider_notification_consent,
    record_ehr_connection,
    get_user_checkins,
    get_checkin_result,
    get_user_reading_history,
)


def check_sqlite_local_guard() -> None:
    """Refuses execution if DB_BACKEND is mysql or MYSQL_URL is set."""
    backend = get_db_backend()
    mysql_url = os.environ.get("MYSQL_URL", "").strip()
    if backend == "mysql" or (mysql_url and mysql_url.lower() != "none"):
        raise RuntimeError(
            f"REFUSING TO RUN ON MYSQL: seed_demo_local.py is strictly restricted to local SQLite. "
            f"DB_BACKEND='{backend}', MYSQL_URL={'SET' if mysql_url else 'NOT SET'}."
        )


def _drive_api_checkin(
    client: Any,
    condition: str,
    answers: List[str],
    user_id: str,
    target_dt: datetime,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Drives a check-in through the real FastAPI TestClient endpoints (/start, /answer, /complete).
    Never hardcodes triage levels, risk bands, or explanations.
    Updates timestamps to target_dt for longitudinal history tracking.
    """
    dt_iso = target_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Start check-in
    r_start = client.post("/api/checkins/start", json={"condition": condition})
    if r_start.status_code != 200:
        raise RuntimeError(f"Checkin start failed ({r_start.status_code}): {r_start.text}")
    chk_id = r_start.json()["checkin_id"]

    # 2. Answer turn-by-turn until complete or emergency
    data = {}
    for ans in answers:
        r_ans = client.post(f"/api/checkins/{chk_id}/answer", json={"answer": ans})
        if r_ans.status_code != 200:
            raise RuntimeError(f"Answer failed ({r_ans.status_code}): {r_ans.text}")
        data = r_ans.json()
        if data.get("complete") or data.get("emergency"):
            break

    # If still not complete (e.g. connected mode medication confirmation), provide affirmative answers
    max_extra_turns = 5
    while not data.get("complete") and not data.get("emergency") and max_extra_turns > 0:
        max_extra_turns -= 1
        r_ans = client.post(f"/api/checkins/{chk_id}/answer", json={"answer": "Yes"})
        if r_ans.status_code == 200:
            data = r_ans.json()
        else:
            break

    # 3. Call /complete
    r_comp = client.post(f"/api/checkins/{chk_id}/complete")
    if r_comp.status_code != 200:
        raise RuntimeError(f"Complete failed ({r_comp.status_code}): {r_comp.text}")
    comp_data = r_comp.json()

    # 4. Update timestamps in DB for historical accuracy
    with get_db_cursor(backend="sqlite", db_path=db_path) as (cursor, _be, ph):
        cursor.execute(
            f"UPDATE checkins SET started_at = {ph}, completed_at = {ph} WHERE checkin_id = {ph}",
            (dt_iso, dt_iso, chk_id),
        )
        cursor.execute(
            f"UPDATE checkin_results SET created_at = {ph} WHERE checkin_id = {ph}",
            (dt_iso, chk_id),
        )

    return comp_data


def _seed_ocr_prescription(
    client: Any,
    user_id: str,
    db_path: Optional[str] = None,
) -> Optional[str]:
    """
    Creates a fake script-generated prescription image and uploads it through the real OCR API.
    Saves the medication with origin 'ocr' (Medium trust / Unverified badge).
    """
    try:
        from PIL import Image, ImageDraw, PngImagePlugin
    except ImportError:
        return None

    # Synthetic doctor and clinic header per requirement
    doc_text = (
        "Dr. Test Fictional\n"
        "Test Clinic\n"
        "PMDC-00000-X\n"
        "Patient: Demo Patient HTN (fictional)\n"
        "Date: 10/11/2026\n\n"
        "Rx: Tab Amlodipine 5mg 1 tab OD\n"
        "Sig: Take 1 tablet once daily in the morning"
    )

    img = Image.new("RGB", (600, 320), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((25, 25), doc_text, fill=(0, 0, 0))

    meta = PngImagePlugin.PngInfo()
    meta.add_text("prescription", doc_text)

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta)
    png_bytes = buf.getvalue()

    # Upload via /api/me/record/uploads
    up_resp = client.post(
        "/api/me/record/uploads",
        headers={"Content-Type": "image/png"},
        content=png_bytes,
    )
    if up_resp.status_code != 200:
        return None

    upload_id = up_resp.json().get("upload_id")
    if not upload_id:
        return None

    # Confirm via /api/me/record/uploads/{upload_id}/confirm
    conf_resp = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        json={
            "items": [
                {
                    "type": "medication",
                    "name": "Amlodipine 5mg",
                    "dosage": "5mg",
                    "status": "active",
                }
            ]
        },
    )
    if conf_resp.status_code != 200:
        return None

    return upload_id


def reset_demo_data(db_path: Optional[str] = None) -> None:
    """Removes all demo users, test users (la.%@demo.care), profiles, and associated records for a clean reset."""
    check_sqlite_local_guard()
    demo_emails = [
        "demo_patient_htn@demo.care",
        "demo_patient_dm@demo.care",
        "demo_patient_dual@demo.care",
        "demo_patient_ur@demo.care",
        "demo_patient_roman_ur@demo.care",
        "demo_patient_emg@demo.care",
        "demo_patient_norx@demo.care",
        "demo_patient_fhir@demo.care",
        "demo_patient_new@demo.care",
        "provider.demo@demo.care",
        "admin.demo@demo.care",
    ]

    with get_db_cursor(backend="sqlite", db_path=db_path) as (cursor, _be, ph):
        placeholders = ", ".join([ph] * len(demo_emails))
        cursor.execute(
            f"SELECT user_id FROM users WHERE email IN ({placeholders}) OR email LIKE 'la.%@demo.care'",
            tuple(demo_emails),
        )
        user_ids = [r["user_id"] for r in cursor.fetchall()]

        if user_ids:
            uid_ph = ", ".join([ph] * len(user_ids))
            # Delete checkin results, appointments, notifications and checkins
            cursor.execute(f"SELECT checkin_id FROM checkins WHERE user_id IN ({uid_ph})", tuple(user_ids))
            c_ids = [r["checkin_id"] for r in cursor.fetchall()]
            if c_ids:
                c_ph = ", ".join([ph] * len(c_ids))
                cursor.execute(f"DELETE FROM checkin_results WHERE checkin_id IN ({c_ph})", tuple(c_ids))
                cursor.execute(f"DELETE FROM appointments WHERE checkin_id IN ({c_ph})", tuple(c_ids))
                cursor.execute(f"DELETE FROM notifications WHERE checkin_id IN ({c_ph})", tuple(c_ids))
                cursor.execute(f"DELETE FROM checkins WHERE checkin_id IN ({c_ph})", tuple(c_ids))

            # Delete local observations and medications
            pat_ids = [f"local-{uid}" for uid in user_ids] + user_ids
            pid_ph = ", ".join([ph] * len(pat_ids))
            cursor.execute(f"DELETE FROM appointments WHERE patient_id IN ({pid_ph})", tuple(pat_ids))
            cursor.execute(f"DELETE FROM notifications WHERE user_id IN ({uid_ph})", tuple(user_ids))
            cursor.execute(f"DELETE FROM observations WHERE patient_id IN ({pid_ph})", tuple(pat_ids))
            cursor.execute(f"DELETE FROM medications WHERE patient_id IN ({pid_ph})", tuple(pat_ids))
            cursor.execute(f"DELETE FROM allergies WHERE user_id IN ({uid_ph})", tuple(user_ids))
            cursor.execute(f"DELETE FROM patient_profiles WHERE user_id IN ({uid_ph})", tuple(user_ids))
            cursor.execute(f"DELETE FROM ehr_connections WHERE user_id IN ({uid_ph})", tuple(user_ids))
            cursor.execute(f"DELETE FROM users WHERE user_id IN ({uid_ph})", tuple(user_ids))


def seed_demo_data(reset: bool = False, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Seeds local SQLite database using real FastAPI endpoints.
    Idempotent: Replaces demo records if reset=True.
    """
    check_sqlite_local_guard()

    # Configure local demo environment flags
    os.environ["APP_ENV"] = "local"
    os.environ["DB_BACKEND"] = "sqlite"
    if db_path:
        os.environ["LOCAL_DB_PATH"] = db_path
    os.environ["RISK_ENABLED"] = "true"
    os.environ["RISK_CAN_RAISE"] = "true"
    os.environ["RISK_PATIENT_VISIBLE"] = "true"
    os.environ["RISK_RAISE_COOLDOWN_DAYS"] = "0"
    os.environ["TREND_CAN_RAISE"] = "true"
    os.environ["NO_READING_SYMPTOM_RAISE"] = "true"
    os.environ["DANGER_WORDGROUPS_ENABLED"] = "true"
    os.environ["OCR_ENABLED"] = "true"
    os.environ["OCR_PROVIDER"] = "fake"
    os.environ["EXPLAIN_ENABLED"] = "true"
    os.environ["EXPLAIN_MODE"] = "inline"

    resolved_db = get_sqlite_path(db_path)
    print(f"\n[INFO] Initializing SQLite database at: {resolved_db}")
    migrate(backend="sqlite", db_path=resolved_db)

    if reset:
        print("[INFO] Reset switch active. Clearing existing demo accounts...")
        reset_demo_data(db_path=resolved_db)

    import main
    from fastapi.testclient import TestClient
    client = TestClient(main.app)

    now = datetime.now(timezone.utc)

    personas = [
        # 1. HTN patient: worsening BP trend -> Yellow (review), BP chart
        {
            "key": "htn",
            "email": "demo_patient_htn@demo.care",
            "name": "Demo Patient HTN",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "en",
            "profile": {
                "date_of_birth": "1974-06-12",
                "sex_at_birth": "male",
                "height_cm": 175.0,
                "weight_kg": 78.0,
                "waist_cm": 86.0,
                "smoking_status": "never",
            },
        },
        # 2. DM patient: glucose history + High DM risk band -> Stage-2 Yellow
        {
            "key": "dm",
            "email": "demo_patient_dm@demo.care",
            "name": "Demo Patient DM",
            "role": "patient",
            "conditions": ["hypertension"],  # Evaluates diabetes_full_nhanes risk model
            "language": "en",
            "profile": {
                "date_of_birth": "1960-02-14",
                "sex_at_birth": "male",
                "height_cm": 168.0,
                "weight_kg": 95.0,
                "waist_cm": 110.0,
                "smoking_status": "current",
            },
        },
        # 3. Dual patient: both risk models + SOAP summary
        {
            "key": "dual",
            "email": "demo_patient_dual@demo.care",
            "name": "Demo Patient Dual",
            "role": "patient",
            "conditions": ["hypertension"],  # Evaluates both NHANES DM & Framingham CHD10
            "language": "en",
            "profile": {
                "date_of_birth": "1962-08-14",
                "sex_at_birth": "male",
                "height_cm": 172.0,
                "weight_kg": 85.0,
                "waist_cm": 98.0,
                "smoking_status": "current",
            },
        },
        # 4. Urdu script patient
        {
            "key": "ur",
            "email": "demo_patient_ur@demo.care",
            "name": "Demo Patient Urdu",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "ur",
            "profile": {
                "date_of_birth": "1968-11-20",
                "sex_at_birth": "female",
                "height_cm": 160.0,
                "weight_kg": 68.0,
                "waist_cm": 84.0,
                "smoking_status": "never",
            },
        },
        # 5. Roman Urdu patient
        {
            "key": "roman_ur",
            "email": "demo_patient_roman_ur@demo.care",
            "name": "Demo Patient Roman Urdu",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "roman_ur",
            "profile": {
                "date_of_birth": "1972-04-10",
                "sex_at_birth": "female",
                "height_cm": 162.0,
                "weight_kg": 70.0,
                "waist_cm": 85.0,
                "smoking_status": "never",
            },
        },
        # 6. Past emergency check-in (1122 screen record)
        {
            "key": "emg",
            "email": "demo_patient_emg@demo.care",
            "name": "Demo Patient Emergency",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "en",
            "profile": {
                "date_of_birth": "1965-09-05",
                "sex_at_birth": "male",
                "height_cm": 170.0,
                "weight_kg": 75.0,
                "waist_cm": 88.0,
                "smoking_status": "former",
            },
        },
        # 7. No readings check-in (Rule R8 wording)
        {
            "key": "norx",
            "email": "demo_patient_norx@demo.care",
            "name": "Demo Patient No-Readings",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "en",
            "profile": {
                "date_of_birth": "1980-03-25",
                "sex_at_birth": "female",
                "height_cm": 165.0,
                "weight_kg": 62.0,
                "waist_cm": 76.0,
                "smoking_status": "never",
            },
        },
        # 8. Connected mode on FhirSim
        {
            "key": "fhir",
            "email": "demo_patient_fhir@demo.care",
            "name": "Demo Patient FHIR",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "en",
            "profile": {
                "date_of_birth": "1957-04-12",
                "sex_at_birth": "male",
                "height_cm": 170.0,
                "weight_kg": 74.0,
                "waist_cm": 88.0,
                "smoking_status": "former",
            },
        },
        # 9. Cold start: strictly 0 check-ins
        {
            "key": "new",
            "email": "demo_patient_new@demo.care",
            "name": "Demo Patient New",
            "role": "patient",
            "conditions": ["hypertension"],
            "language": "en",
            "profile": {
                "date_of_birth": "1988-12-01",
                "sex_at_birth": "female",
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "waist_cm": 74.0,
                "smoking_status": "never",
            },
        },
        # 10. Provider
        {
            "key": "provider",
            "email": "provider.demo@demo.care",
            "name": "Demo Provider",
            "role": "provider",
        },
        # 11. Admin
        {
            "key": "admin",
            "email": "admin.demo@demo.care",
            "name": "Demo Admin",
            "role": "admin",
        },
    ]

    seeded_users: Dict[str, str] = {}

    print("\n[INFO] Creating demo users and clinical profiles in local database...")
    for p in personas:
        email = p["email"]
        existing = get_user_by_email(email, db_path=resolved_db)
        if existing:
            uid = existing["user_id"]
        else:
            uid = f"demo_user_{p['key']}"
            create_user(
                user_id=uid,
                email=email,
                role=p["role"],
                display_name=p["name"],
                status="active",
                db_path=resolved_db,
            )
        seeded_users[p["key"]] = uid

        if p["role"] == "patient":
            prof = p.get("profile", {})
            upsert_patient_profile(
                user_id=uid,
                conditions=p.get("conditions", []),
                language=p.get("language", "en"),
                date_of_birth=prof.get("date_of_birth"),
                inclusion_confirmed=True,
                sex_at_birth=prof.get("sex_at_birth"),
                height_cm=prof.get("height_cm"),
                weight_kg=prof.get("weight_kg"),
                waist_cm=prof.get("waist_cm"),
                smoking_status=prof.get("smoking_status"),
                db_path=resolved_db,
            )
            set_patient_consent(user_id=uid, granted=True, db_path=resolved_db)
            set_patient_provider_notification_consent(user_id=uid, granted=True, db_path=resolved_db)

    print("\n[INFO] Driving real check-ins through FastAPI TestClient API pipeline...")

    # Helper to authenticate TestClient for a user
    def set_auth(u_key: str) -> str:
        u_id = seeded_users[u_key]
        u_rec = next(x for x in personas if x["key"] == u_key)
        main.app.dependency_overrides[main.get_current_user] = lambda: {
            "user_id": u_id,
            "email": u_rec["email"],
            "role": u_rec["role"],
        }
        main.app.dependency_overrides[main.extract_bearer_token] = lambda: "demo_token"
        return u_id

    # 1. Demo Patient HTN: 5 past days of rising BP + today's checkin (sbp=146) -> Stage-2 Yellow
    htn_uid = set_auth("htn")
    # Historical readings 5 days ago to yesterday
    hist_bps = ["122/80", "126/82", "130/84", "136/86", "142/88"]
    for day_idx, bp_val in enumerate(hist_bps):
        dt = now - timedelta(days=5 - day_idx)
        _drive_api_checkin(
            client=client,
            condition="hypertension",
            answers=["Feeling fine", bp_val, "No symptoms", "Yes took meds", "Normal diet", "None"],
            user_id=htn_uid,
            target_dt=dt,
            db_path=resolved_db,
        )
    # Today's check-in: 146/90 (rising trend with latest >= 140 -> triggers Stage-2 Yellow)
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Feeling fine", "146/90", "No symptoms", "Yes took meds", "Normal diet", "None"],
        user_id=htn_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    # OCR fake prescription upload for HTN patient
    _seed_ocr_prescription(client=client, user_id=htn_uid, db_path=resolved_db)
    print("  - Seeded 6 check-ins (rising BP -> Yellow) & unverified OCR Rx for Demo Patient HTN.")

    # 2. Demo Patient DM: 5 past days of glucose readings + today's High DM risk band -> Yellow
    dm_uid = set_auth("dm")
    hist_glucoses = ["112", "118", "124", "128", "132"]
    for day_idx, g_val in enumerate(hist_glucoses):
        dt = now - timedelta(days=5 - day_idx)
        _drive_api_checkin(
            client=client,
            condition="hypertension",
            answers=["Feeling fine", f"128/82, glucose {g_val}", "Mild thirst", "Yes took meds", "Normal diet", "None"],
            user_id=dm_uid,
            target_dt=dt,
            db_path=resolved_db,
        )
    # Today's check-in: 132/84 + high DM risk band from profile -> Stage-2 raise to Yellow
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Feeling fine", "132/84, glucose 135", "No symptoms", "Yes took meds", "Normal diet", "None"],
        user_id=dm_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded glucose history + High DM risk band -> Stage-2 Yellow for Demo Patient DM.")

    # 3. Demo Patient Dual: Both risk models (DM + CHD10) + SOAP summary
    dual_uid = set_auth("dual")
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Feeling slightly tired", "136/86", "Mild fatigue", "Yes took meds", "Normal diet", "None"],
        user_id=dual_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded dual-risk check-in with SOAP note generation for Demo Patient Dual.")

    # 4. Demo Patient Urdu: Urdu script check-in
    ur_uid = set_auth("ur")
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["طبیعت ٹھیک ہے", "125/82", "کوئی علامت نہیں", "جی دوائی لی", "معمول کی خوراک", "کچھ نہیں"],
        user_id=ur_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded Urdu script check-in & reviewed Urdu template for Demo Patient Urdu.")

    # 5. Demo Patient Roman Urdu: Roman Urdu check-in
    roman_uid = set_auth("roman_ur")
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Tabiyat theek hai", "128/84", "Koi masla nahi", "Ji dawai li", "Mamooli khana", "Kuch nahi"],
        user_id=roman_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded Roman Urdu check-in & reviewed Roman Urdu template for Demo Patient Roman Urdu.")

    # 6. Demo Patient Emergency: Red flag danger phrase -> Emergency + 1122 screen
    emg_uid = set_auth("emg")
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["severe chest pain radiating to left arm"],
        user_id=emg_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded red-flag emergency check-in (1122 record) for Demo Patient Emergency.")

    # 7. Demo Patient No-Readings: Check-in without readings -> Rule R8 wording
    norx_uid = set_auth("norx")
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Feeling fine", "no readings today", "No symptoms", "Yes took meds", "Normal diet", "None"],
        user_id=norx_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Seeded no-readings check-in (Rule R8 wording) for Demo Patient No-Readings.")

    # 8. Demo Patient FHIR: Link to FhirSim (demo-hospital / sim-bilal)
    fhir_uid = set_auth("fhir")
    record_ehr_connection(
        connection_id=f"conn_demo_fhir_{int(now.timestamp())}",
        user_id=fhir_uid,
        ehr_system_id="demo-hospital",
        external_patient_id="sim-bilal",
        status="active",
        last_verified_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        db_path=resolved_db,
    )
    _drive_api_checkin(
        client=client,
        condition="hypertension",
        answers=["Feeling fine", "116/74", "No symptoms", "Yes took meds", "Normal diet", "None"],
        user_id=fhir_uid,
        target_dt=now,
        db_path=resolved_db,
    )
    print("  - Connected Demo Patient FHIR to FhirSim ('sim-bilal') with connected check-in.")

    # 9. Demo Patient New: 0 check-ins (cold start)
    print("  - Demo Patient New configured with strictly 0 check-ins (cold start).")

    # Clear dependency overrides
    main.app.dependency_overrides.clear()

    return seeded_users


def print_summary_table(seeded_users: Dict[str, str], db_path: Optional[str] = None) -> None:
    """Queries real database endpoints and prints a formatted summary table for the 17 Nov demo."""
    from agents.trend_agent import compute_trends
    resolved_db = get_sqlite_path(db_path)

    print("\n" + "=" * 125)
    print("CHRONICCARE AI — 17 NOV LOCAL DEMO PERSONAS SUMMARY TABLE")
    print("=" * 125)

    headers = [
        "Persona", "Email", "What to Show", "LA ID", "Level", "Colour", "Band / Trend"
    ]
    row_fmt = "{:<24} | {:<28} | {:<32} | {:<7} | {:<7} | {:<7} | {:<10}"
    print(row_fmt.format(*headers))
    print("-" * 125)

    personas_display = [
        ("Demo Patient HTN", "htn", "5+ worsening BP trend, BP chart", "LA-22"),
        ("Demo Patient DM", "dm", "Glucose history, High DM band -> Y", "LA-21"),
        ("Demo Patient Dual", "dual", "Dual risk models & SOAP summary", "LA-24/26"),
        ("Demo Patient Urdu", "ur", "Urdu script & reviewed Urdu template", "LA-10"),
        ("Demo Patient Roman Urdu", "roman_ur", "Roman Urdu checkin & template", "LA-11"),
        ("Demo Patient Emergency", "emg", "Red-flag chest pain -> 1122 screen", "LA-05"),
        ("Demo Patient No-Readings", "norx", "No readings checkin (Rule R8)", "LA-08"),
        ("Demo Patient FHIR", "fhir", "Connected mode on FhirSim", "LA-09"),
        ("Demo Patient New", "new", "Cold start: strictly 0 check-ins", "LA-00"),
        ("Demo Provider", "provider", "Clinical review queue, SOAP notes", "LA-01/26"),
        ("Demo Admin", "admin", "Admin config-status (pure SQLite)", "LA-01"),
    ]

    for label, key, show_desc, la_id in personas_display:
        uid = seeded_users.get(key)
        if key in ("provider", "admin"):
            email = f"{key}.demo@demo.care"
            print(row_fmt.format(label, email, show_desc, la_id, "-", "-", "elevated"))
            continue

        email = f"demo_patient_{key}@demo.care"
        checkins = get_user_checkins(uid, limit=1, db_path=resolved_db)
        if not checkins:
            print(row_fmt.format(label, email, show_desc, la_id, "-", "-", "0 checkins"))
            continue

        cid = checkins[0]["checkin_id"]
        res = get_checkin_result(cid, db_path=resolved_db) or {}

        lvl = res.get("triage_level", "-")
        triage_dict = res.get("triage") or {}
        from agents.final_triage import level_to_colour
        colour = (
            triage_dict.get("triage_colour")
            or triage_dict.get("colour")
            or res.get("triage_colour")
            or (level_to_colour(lvl) if lvl in ("routine", "review", "urgent", "emergency") else "-")
        )

        # Band / trend detail
        history = get_user_reading_history(uid, days=30, db_path=resolved_db)
        t_res = compute_trends(history, window_days=30)
        t_bp = t_res.get("trends", {}).get("blood_pressure_systolic", {})
        direction = t_bp.get("direction", "none")
        n_pts = t_bp.get("n", 0)

        risk_dict = res.get("risk") or {}
        assessments = risk_dict.get("assessments") or []
        if not assessments and isinstance(risk_dict, dict) and "models" in risk_dict:
            assessments = risk_dict.get("models") or []
        bands = [a.get("band") for a in assessments if isinstance(a, dict) and a.get("band")]

        detail_str = ""
        if direction in ("rising", "falling"):
            detail_str = f"{direction[:4]}(n={n_pts})"
        elif bands:
            detail_str = f"band:{bands[0]}"
        elif res.get("emergency"):
            detail_str = "1122 emg"
        else:
            detail_str = "stable"

        print(row_fmt.format(label, email, show_desc, la_id, lvl, colour, detail_str))

    print("=" * 125)
    print("\nFIREBASE & LOCAL DEMO LOGIN INSTRUCTIONS:")
    print("To log in as these personas in the web browser, use any password of your choice in")
    print("Firebase Console (or local test auth). Roles are deterministically resolved:")
    print("  - Provider: provider.demo@demo.care (resolved to 'provider' via DEMO_ROLE_MAP)")
    print("  - Admin:    admin.demo@demo.care    (resolved to 'admin' via DEMO_ROLE_MAP)")
    print("  - Patients: all demo_patient_*@demo.care accounts default to 'patient' role.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local SQLite demo database for ChronicCare AI.")
    parser.add_argument("--reset", action="store_true", help="Clear and re-seed all demo accounts and records.")
    parser.add_argument("--db-path", type=str, default=None, help="Explicit path to SQLite database file.")
    args = parser.parse_args()

    try:
        check_sqlite_local_guard()
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    users = seed_demo_data(reset=args.reset, db_path=args.db_path)
    print_summary_table(users, db_path=args.db_path)


if __name__ == "__main__":
    main()
