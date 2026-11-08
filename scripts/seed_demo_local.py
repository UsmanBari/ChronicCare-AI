"""
Seed script for local demo environment (SQLite only).
Proposal Sections 13.1, 15, and 17.

Seeds 5 fake patient personas, 1 provider, and 1 admin:
1. Demo Patient HTN (demo_patient_htn@demo.care): hypertension only, complete profile,
   14 days of BP readings rising above target range (>140 mmHg) to trigger trend escalation.
2. Demo Patient DM (demo_patient_dm@demo.care): diabetes only, glucose history.
3. Demo Patient Dual (demo_patient_dual@demo.care): both conditions, both risk models apply.
4. Demo Patient New (demo_patient_new@demo.care): cold start (zero check-ins).
5. Demo Patient FHIR (demo_patient_fhir@demo.care): connected-mode patient on FhirSim.
Plus Demo Provider (provider.demo@demo.care) and Demo Admin (admin.demo@demo.care).

Strictly refuses to run against MySQL or any non-local store.
"""
from __future__ import annotations

import json
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
    create_checkin,
    create_checkin_result,
    record_ehr_connection,
    get_user_checkins,
    get_checkin_result,
    get_user_reading_history,
)
from agents.final_triage import level_to_colour, decide_stage2, TREND_MIN_POINTS, TARGET_THRESHOLDS
from agents import risk_agent


def check_sqlite_local_guard() -> None:
    """Refuses execution if DB_BACKEND is mysql or MYSQL_URL is set."""
    backend = get_db_backend()
    mysql_url = os.environ.get("MYSQL_URL", "").strip()
    if backend == "mysql" or (mysql_url and mysql_url.lower() != "none"):
        raise RuntimeError(
            f"REFUSING TO RUN ON MYSQL: seed_demo_local.py is strictly restricted to local SQLite. "
            f"DB_BACKEND='{backend}', MYSQL_URL={'SET' if mysql_url else 'NOT SET'}."
        )


def _seed_patient_checkin(
    user_id: str,
    checkin_id: str,
    dt_iso: str,
    readings: List[Dict[str, Any]],
    rules_level: str = "routine",
    condition: str = "hypertension",
    profile: Optional[Dict[str, Any]] = None,
    mode: str = "isolated",
    source: str = "manual",
) -> Dict[str, Any]:
    """Helper to create checkin and result with stage-2 final triage evaluation."""
    intakes = [{
        "step": "readings",
        "readings": readings,
        "source": source,
    }]
    
    # Create checkin session
    create_checkin(
        checkin_id=checkin_id,
        user_id=user_id,
        mode=mode,
        record_patient_id=f"local-{user_id}",
        state_dict={"step": "complete", "answers": {}},
        status="complete",
        started_at=dt_iso,
    )
    
    # Complete checkin at dt_iso
    with get_db_cursor() as (cursor, be, ph):
        cursor.execute(
            f"UPDATE checkins SET completed_at = {ph} WHERE checkin_id = {ph}",
            (dt_iso, checkin_id)
        )
        
    # Evaluate risk models if profile provided
    risk_results = []
    if profile:
        conditions = profile.get("conditions", [condition])
        risk_results = risk_agent.assess_all_models(
            profile=profile,
            readings=readings,
            conditions=conditions,
            reading_source="fhir" if source == "fhir" else "manual",
            is_first_checkin=False,
        )
        
    # Query history for trends
    history = get_user_reading_history(user_id=user_id, days=30)
    from agents.trend_agent import compute_trends
    trends_res = compute_trends(history, window_days=30)
    
    # Flags for local demo
    flags = {
        "RISK_CAN_RAISE": True,
        "TREND_CAN_RAISE": True,
        "NO_READING_SYMPTOM_RAISE": True,
        "RISK_RAISE_COOLDOWN_DAYS": 0,
    }
    
    stage2 = decide_stage2(
        rules_level=rules_level,
        risk_results=risk_results,
        trends=trends_res,
        flags=flags,
        has_readings=bool(readings),
    )
    
    # Trace item
    trace = [{
        "agent": "final_triage",
        "rules_level": rules_level,
        "final_level": stage2["final_level"],
        "triage_colour": stage2["triage_colour"],
        "raised": stage2["raised"],
        "raised_by": stage2["raised_by"],
    }]
    
    # Create result
    create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=intakes,
        triage_level=stage2["final_level"],
        triage={
            "level": stage2["final_level"],
            "colour": stage2["triage_colour"],
            "rules_level": rules_level,
            "raised_by": stage2["raised_by"],
            "patient_reason_key": stage2.get("patient_reason_key"),
        },
        risk={"assessments": risk_results} if risk_results else None,
        trace=trace,
        created_at=dt_iso,
    )
    return stage2


def seed_demo_data(reset: bool = False) -> Dict[str, Any]:
    """Seeds the local SQLite database with the 5 demo personas, 1 provider, 1 admin."""
    check_sqlite_local_guard()
    
    print("\n[INFO] Initializing and migrating SQLite database schema...")
    migrate(backend="sqlite")
    
    now = datetime.now(timezone.utc)
    
    personas = [
        # 1. Demo Patient HTN
        {
            "key": "htn",
            "email": "demo_patient_htn@demo.care",
            "name": "Demo Patient HTN",
            "role": "patient",
            "conditions": ["hypertension"],
            "profile": {
                "date_of_birth": "1970-01-01",
                "sex_at_birth": "male",
                "height_cm": 175.0,
                "weight_kg": 80.0,
                "waist_cm": 90.0,
                "smoking_status": "current",
                "conditions": ["hypertension"],
            },
        },
        # 2. Demo Patient DM
        {
            "key": "dm",
            "email": "demo_patient_dm@demo.care",
            "name": "Demo Patient DM",
            "role": "patient",
            "conditions": ["diabetes"],
            "profile": {
                "date_of_birth": "1968-05-10",
                "sex_at_birth": "female",
                "height_cm": 165.0,
                "weight_kg": 72.0,
                "waist_cm": 86.0,
                "smoking_status": "never",
                "on_insulin_or_sulfonylurea": False,
                "conditions": ["diabetes"],
            },
        },
        # 3. Demo Patient Dual
        {
            "key": "dual",
            "email": "demo_patient_dual@demo.care",
            "name": "Demo Patient Dual",
            "role": "patient",
            "conditions": ["hypertension", "diabetes"],
            "profile": {
                "date_of_birth": "1962-08-14",
                "sex_at_birth": "male",
                "height_cm": 172.0,
                "weight_kg": 84.0,
                "waist_cm": 96.0,
                "smoking_status": "current",
                "conditions": ["hypertension", "diabetes"],
            },
        },
        # 4. Demo Patient New (cold start)
        {
            "key": "new",
            "email": "demo_patient_new@demo.care",
            "name": "Demo Patient New",
            "role": "patient",
            "conditions": ["hypertension"],
            "profile": {
                "date_of_birth": "1985-02-14",
                "sex_at_birth": "female",
                "conditions": ["hypertension"],
            },
        },
        # 5. Demo Patient FHIR
        {
            "key": "fhir",
            "email": "demo_patient_fhir@demo.care",
            "name": "Demo Patient FHIR",
            "role": "patient",
            "conditions": ["hypertension"],
            "profile": {
                "date_of_birth": "1957-04-12",
                "sex_at_birth": "male",
                "conditions": ["hypertension"],
            },
        },
        # 6. Provider
        {
            "key": "provider",
            "email": "provider.demo@demo.care",
            "name": "Demo Provider",
            "role": "provider",
        },
        # 7. Admin
        {
            "key": "admin",
            "email": "admin.demo@demo.care",
            "name": "Demo Admin",
            "role": "admin",
        },
    ]
    
    seeded_users: Dict[str, str] = {}
    
    print("\n[INFO] Seeding users and patient profiles...")
    for p in personas:
        email = p["email"]
        existing = get_user_by_email(email)
        if existing:
            user_id = existing["user_id"]
            print(f"  - User {email} already exists (user_id={user_id}). Reusing.")
        else:
            user_id = f"demo_user_{p['key']}"
            create_user(
                user_id=user_id,
                email=email,
                role=p["role"],
                display_name=p["name"],
                status="active",
            )
            print(f"  - Created user {email} (user_id={user_id}, role={p['role']}).")
        
        seeded_users[p["key"]] = user_id
        
        # Upsert profile if patient
        if p["role"] == "patient":
            prof = p.get("profile", {})
            upsert_patient_profile(
                user_id=user_id,
                conditions=p.get("conditions", []),
                language="en",
                date_of_birth=prof.get("date_of_birth"),
                inclusion_confirmed=True,
                sex_at_birth=prof.get("sex_at_birth"),
                height_cm=prof.get("height_cm"),
                weight_kg=prof.get("weight_kg"),
                waist_cm=prof.get("waist_cm"),
                smoking_status=prof.get("smoking_status"),
                on_insulin_or_sulfonylurea=prof.get("on_insulin_or_sulfonylurea"),
            )
            set_patient_consent(user_id=user_id, granted=True)
            set_patient_provider_notification_consent(user_id=user_id, granted=True)
            
    # Seed check-in histories
    print("\n[INFO] Seeding check-in histories and readings...")
    
    # 1. Demo Patient HTN: 14 days of rising BP readings (124 -> 152 mmHg systolic, above 140 target)
    htn_uid = seeded_users["htn"]
    htn_prof = personas[0]["profile"]
    for day in range(14, 0, -1):
        dt = now - timedelta(days=day)
        sbp = 124.0 + (14 - day) * 2.0
        dbp = 80.0 + (14 - day) * 1.0
        _seed_patient_checkin(
            user_id=htn_uid,
            checkin_id=f"chk_htn_hist_d{day}_{int(dt.timestamp())}",
            dt_iso=dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            readings=[
                {"observation_type": "blood_pressure_systolic", "value": sbp},
                {"observation_type": "blood_pressure_diastolic", "value": dbp},
            ],
            rules_level="routine",
            condition="hypertension",
            profile=htn_prof,
        )
    # Today's checkin for HTN: sbp=152.0 (triggers trend raise to Yellow / review)
    _seed_patient_checkin(
        user_id=htn_uid,
        checkin_id=f"chk_htn_latest_{int(now.timestamp())}",
        dt_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        readings=[
            {"observation_type": "blood_pressure_systolic", "value": 152.0},
            {"observation_type": "blood_pressure_diastolic", "value": 94.0},
        ],
        rules_level="routine",
        condition="hypertension",
        profile=htn_prof,
    )
    print("  - Seeded 14 days of rising BP readings for Demo Patient HTN.")

    # 2. Demo Patient DM: 5 days of glucose readings
    dm_uid = seeded_users["dm"]
    dm_prof = personas[1]["profile"]
    glucose_vals = [105.0, 110.0, 115.0, 118.0, 122.0]
    for i, gval in enumerate(glucose_vals):
        dt = now - timedelta(days=len(glucose_vals) - i)
        _seed_patient_checkin(
            user_id=dm_uid,
            checkin_id=f"chk_dm_hist_{i}_{int(dt.timestamp())}",
            dt_iso=dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            readings=[
                {"observation_type": "glucose", "value": gval, "glucose_context": "fasting"},
            ],
            rules_level="routine",
            condition="diabetes",
            profile=dm_prof,
        )
    print("  - Seeded 5 days of glucose history for Demo Patient DM.")

    # 3. Demo Patient Dual: 5 days of dual readings (both models apply)
    dual_uid = seeded_users["dual"]
    dual_prof = personas[2]["profile"]
    for i in range(5, 0, -1):
        dt = now - timedelta(days=i)
        _seed_patient_checkin(
            user_id=dual_uid,
            checkin_id=f"chk_dual_hist_{i}_{int(dt.timestamp())}",
            dt_iso=dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            readings=[
                {"observation_type": "blood_pressure_systolic", "value": 136.0},
                {"observation_type": "blood_pressure_diastolic", "value": 86.0},
                {"observation_type": "glucose", "value": 130.0, "glucose_context": "fasting"},
            ],
            rules_level="routine",
            condition="hypertension",
            profile=dual_prof,
        )
    print("  - Seeded 5 days of dual readings for Demo Patient Dual.")

    # 4. Demo Patient New: Zero check-ins (cold start)
    print("  - Demo Patient New configured with 0 check-ins (cold start).")

    # 5. Demo Patient FHIR: Link to FhirSim (demo-hospital / sim-bilal) and seed 1 FHIR checkin
    fhir_uid = seeded_users["fhir"]
    fhir_prof = personas[4]["profile"]
    record_ehr_connection(
        connection_id=f"conn_demo_fhir_{int(now.timestamp())}",
        user_id=fhir_uid,
        ehr_system_id="demo-hospital",
        external_patient_id="sim-bilal",
        status="active",
        last_verified_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    _seed_patient_checkin(
        user_id=fhir_uid,
        checkin_id=f"chk_fhir_latest_{int(now.timestamp())}",
        dt_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        readings=[
            {"observation_type": "blood_pressure_systolic", "value": 114.0},
            {"observation_type": "blood_pressure_diastolic", "value": 72.0},
        ],
        rules_level="routine",
        condition="hypertension",
        profile=fhir_prof,
        mode="connected",
        source="fhir",
    )
    print("  - Connected Demo Patient FHIR to FhirSim ('sim-bilal') with FHIR reading.")

    return seeded_users


def print_summary_table(seeded_users: Dict[str, str]) -> None:
    """Queries real database endpoints/stores and prints a formatted summary table."""
    from agents.trend_agent import compute_trends
    
    print("\n" + "=" * 115)
    print("LOCAL DEMO PERSONAS SUMMARY TABLE")
    print("=" * 115)
    
    headers = [
        "Patient", "Conditions", "Rules", "Final", "Colour", "Raised By",
        "Models & Bands", "Trend Dir", "Conf"
    ]
    row_fmt = "{:<18} | {:<16} | {:<7} | {:<7} | {:<7} | {:<20} | {:<20} | {:<10} | {:<6}"
    print(row_fmt.format(*headers))
    print("-" * 115)
    
    personas_info = [
        ("Demo Patient HTN", "htn", ["hypertension"]),
        ("Demo Patient DM", "dm", ["diabetes"]),
        ("Demo Patient Dual", "dual", ["hypertension", "diabetes"]),
        ("Demo Patient New", "new", ["hypertension"]),
        ("Demo Patient FHIR", "fhir", ["hypertension"]),
    ]
    
    for label, key, conds in personas_info:
        uid = seeded_users.get(key)
        checkins = get_user_checkins(uid, limit=1)
        if not checkins:
            print(row_fmt.format(
                label, ",".join(conds), "-", "-", "-", "none",
                "no data", "none", "-"
            ))
            continue
            
        chk = checkins[0]
        cid = chk["checkin_id"]
        res = get_checkin_result(cid)
        
        triage_info = res.get("triage") or {}
        rules_lvl = triage_info.get("rules_level", "routine")
        final_lvl = res.get("triage_level") or triage_info.get("level", "routine")
        colour = triage_info.get("colour") or level_to_colour(final_lvl)
        
        raised_list = triage_info.get("raised_by", [])
        if raised_list:
            raised_by_str = f"{raised_list[0].get('source')}: {raised_list[0].get('detail', '')}"[:20]
        else:
            raised_by_str = "none"
            
        risk_info = res.get("risk") or {}
        assessments = risk_info.get("assessments", [])
        if assessments:
            bands = [f"{a.get('model_name', 'model')}:{a.get('band', 'unk')}" for a in assessments]
            models_str = ", ".join(bands)[:20]
            conf = assessments[0].get("confidence", "Medium")
        else:
            models_str = "none"
            conf = "-"
            
        history = get_user_reading_history(uid, days=30)
        t_res = compute_trends(history, window_days=30)
        t_bp = t_res.get("trends", {}).get("blood_pressure_systolic", {})
        trend_str = f"{t_bp.get('direction', 'none')} ({t_bp.get('n', 0)})"
        
        print(row_fmt.format(
            label, ",".join(conds), rules_lvl, final_lvl, colour,
            raised_by_str, models_str, trend_str, conf
        ))
        
    print("=" * 115)
    print("\nFIREBASE LOGIN INSTRUCTIONS:")
    print("To log in as these demo personas in the web browser, create these accounts in the")
    print("Firebase Console (Authentication > Users > Add user) with any password of your choice:")
    print("  - demo_patient_htn@demo.care   (Hypertension only, rising BP -> Stage-2 review)")
    print("  - demo_patient_dm@demo.care    (Diabetes only, glucose history)")
    print("  - demo_patient_dual@demo.care  (Dual T2D & HTN, both risk models)")
    print("  - demo_patient_new@demo.care   (Cold start, 0 check-ins)")
    print("  - demo_patient_fhir@demo.care  (Connected mode on FhirSim 'sim-bilal')")
    print("  - provider.demo@demo.care      (Provider role in DEMO_ROLE_MAP)")
    print("  - admin.demo@demo.care         (Admin role in DEMO_ROLE_MAP)")
    print("Note: Passwords are never stored in the repo. Any password set in Firebase works locally.\n")


def main() -> None:
    try:
        check_sqlite_local_guard()
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
        
    users = seed_demo_data()
    print_summary_table(users)


if __name__ == "__main__":
    main()
