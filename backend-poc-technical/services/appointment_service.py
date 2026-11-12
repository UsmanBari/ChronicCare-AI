"""
Appointment Service (Deterministic, Clinical Rules Engine).
Proposal Section 15, Section 35, Section 37.

Rules:
1. Colour -> Action:
   - Green (routine): No appointment created.
   - Yellow (review): Routine appointment OFFERED, bookable within 3 days, telehealth allowed.
   - Red (urgent): Urgent appointment created as BOOKED for earliest available slot today, provider alerted immediately.
   - Red (emergency): Patient's emergency screen (1122) comes first; urgent appointment record also created with status 'booked', provider alerted.
2. Specialty Mapping:
   - Hypertension only -> cardiology_im
   - Diabetes only -> endocrinology
   - Both -> internal_medicine (Doctor sign-off, 8 Nov 2026, docs/CLINICIAN_RESPONSES.md item 4)
   - Other / Neither -> general
   - Fallback: If designated specialty has no available provider -> general; if none at all -> provider 'unassigned' with status 'offered' and admin flag.
3. Escalation Timeout (Section 15):
   - Computed on read (no background daemon).
   - Urgent appointment with acknowledged_at empty:
     * >= 2 h -> escalation_state 're_notify'
     * >= 24 h -> 'admin_flag' (surfaced in admin view, logged once to audit log)
   - Acknowledge clears escalation.
4. Idempotent per checkin_id.
5. Audit log updated without PHI.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from data_sources.app_store import (
    append_audit,
    create_appointment,
    get_appointment,
    get_appointment_by_checkin,
    list_providers,
    update_appointment,
)

logger = logging.getLogger("appointment_service")


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parses ISO timestamp into timezone-aware UTC datetime."""
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def determine_specialty(conditions: Optional[List[str]]) -> str:
    """
    Determines provider specialty from patient chronic conditions:
    - Hypertension only -> cardiology_im
    - Diabetes only -> endocrinology
    - Both diabetes + hypertension -> internal_medicine (docs/CLINICIAN_RESPONSES.md item 4)
    - Otherwise -> general
    """
    cond_set = {str(c).strip().lower() for c in (conditions or [])}
    has_diabetes = any(
        k in c
        for c in cond_set
        for k in ("diabetes", "t2d", "sugar", "diabetic")
    )
    has_hypertension = any(
        k in c
        for c in cond_set
        for k in ("hypertension", "htn", "blood_pressure", "high_bp")
    )

    if has_diabetes and has_hypertension:
        return "internal_medicine"
    if has_hypertension:
        return "cardiology_im"
    if has_diabetes:
        return "endocrinology"
    return "general"


def select_provider(
    specialty: str,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Tuple[str, bool]:
    """
    Selects the first available provider for the chosen specialty.
    Fallback:
    1. If chosen specialty has no available provider -> check 'general'.
    2. If no available provider in general -> return ('unassigned', True).
    Returns (provider_id, is_unassigned).
    """
    # 1. Primary specialty search
    providers = list_providers(
        specialty=specialty,
        available_only=True,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    if providers:
        return providers[0]["id"], False

    # 2. General fallback
    if specialty != "general":
        gen_providers = list_providers(
            specialty="general",
            available_only=True,
            backend=backend,
            db_path=db_path,
            mysql_url=mysql_url,
            ssl_ca=ssl_ca,
        )
        if gen_providers:
            return gen_providers[0]["id"], False

    # 3. None available -> unassigned
    return "unassigned", True


def compute_escalation_state(
    appointment: Dict[str, Any],
    now_dt: Optional[datetime] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes the escalation state on read (Section 15):
    - Urgent appointment with acknowledged_at empty:
      * < 2 hours -> 'pending'
      * >= 2 hours and < 24 hours -> 're_notify'
      * >= 24 hours -> 'admin_flag' (written once to audit log)
    - Acknowledged -> 'acknowledged'
    - Routine urgency -> 'none'
    """
    appt = dict(appointment)
    urgency = appt.get("urgency", "routine")

    if urgency != "urgent":
        appt["escalation_state"] = "none"
        return appt

    if appt.get("acknowledged_at"):
        appt["escalation_state"] = "acknowledged"
        return appt

    now = now_dt or datetime.now(UTC)
    created_at_str = appt.get("created_at") or _utc_now_iso()
    try:
        created_dt = _parse_iso_datetime(created_at_str)
        elapsed_seconds = max(0.0, (now - created_dt).total_seconds())
    except Exception:
        elapsed_seconds = 0.0

    if elapsed_seconds >= 86400:  # 24 hours
        escalation_state = "admin_flag"
        # Write to audit log once if not flagged yet
        if not appt.get("admin_flagged_at"):
            now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            update_appointment(
                appt["id"],
                admin_flagged_at=now_iso,
                backend=backend,
                db_path=db_path,
                mysql_url=mysql_url,
                ssl_ca=ssl_ca,
            )
            appt["admin_flagged_at"] = now_iso
            append_audit(
                actor_user_id="system",
                action="appointment_admin_flag",
                target=appt["id"],
                outcome="ok",
                detail={
                    "checkin_id": appt.get("checkin_id"),
                    "urgency": "urgent",
                    "elapsed_hours": round(elapsed_seconds / 3600.0, 1),
                },
                backend=backend,
                db_path=db_path,
                mysql_url=mysql_url,
                ssl_ca=ssl_ca,
            )
    elif elapsed_seconds >= 7200:  # 2 hours
        escalation_state = "re_notify"
    else:
        escalation_state = "pending"

    appt["escalation_state"] = escalation_state
    return appt


def evaluate_and_create_appointment(
    checkin_id: str,
    patient_id: str,
    final_triage_level: str,
    patient_conditions: Optional[List[str]] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
    now_iso: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Main deterministic entrypoint called after triage level is finalized.
    - Routine (Green): None
    - Review (Yellow): Routine appointment OFFERED, bookable within 3 days, telehealth allowed
    - Urgent / Emergency (Red): Urgent appointment BOOKED today, provider alerted immediately
    Idempotent: if appointment already exists for this checkin_id, returns it.
    """
    level = (final_triage_level or "routine").strip().lower()
    if level == "routine":
        return None

    # Idempotency check:
    existing = get_appointment_by_checkin(
        checkin_id=checkin_id,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    if existing:
        return compute_escalation_state(
            existing,
            backend=backend,
            db_path=db_path,
            mysql_url=mysql_url,
            ssl_ca=ssl_ca,
        )

    now_str = now_iso or _utc_now_iso()
    today_date = now_str[:10]
    specialty = determine_specialty(patient_conditions)
    provider_id, is_unassigned = select_provider(
        specialty=specialty,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    appt_id = f"appt-{uuid.uuid4()}"

    if level == "review":
        urgency = "routine"
        mode = "telehealth"
        status = "offered"
        slot_date = None  # Patient selects slot within 3 days
    else:
        # urgent or emergency
        urgency = "urgent"
        mode = "in_person"
        status = "offered" if is_unassigned else "booked"
        slot_date = today_date  # Earliest slot today

    appt = create_appointment(
        appointment_id=appt_id,
        patient_id=patient_id,
        checkin_id=checkin_id,
        provider_id=provider_id,
        specialty=specialty,
        urgency=urgency,
        mode=mode,
        status=status,
        slot_date=slot_date,
        created_at=now_str,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    append_audit(
        actor_user_id=patient_id,
        action="appointment_created",
        target=appt_id,
        outcome="ok",
        detail={
            "checkin_id": checkin_id,
            "urgency": urgency,
            "specialty": specialty,
            "status": status,
            "is_unassigned": is_unassigned,
        },
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    return compute_escalation_state(
        appt,
        now_dt=_parse_iso_datetime(now_str) if now_iso else None,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )


def book_appointment_slot(
    appointment_id: str,
    patient_id: str,
    slot_date: str,
    mode: Optional[str] = None,
    now_dt: Optional[datetime] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Patient books an offered routine appointment within the allowed 3-day window.
    """
    appt = get_appointment(appointment_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")
    if appt["patient_id"] != patient_id:
        raise PermissionError("Patient cannot modify another patient's appointment")
    if appt["status"] != "offered":
        raise ValueError(f"Cannot book appointment in status '{appt['status']}'")

    created_iso = appt["created_at"]
    created_date = _parse_iso_datetime(created_iso).date()
    max_date = created_date + timedelta(days=3)

    try:
        requested_date = datetime.strptime(slot_date.strip(), "%Y-%m-%d").date()
    except Exception as exc:
        raise ValueError(f"Invalid slot_date format: {slot_date}, expected YYYY-MM-DD") from exc

    if requested_date < created_date or requested_date > max_date:
        raise ValueError(
            f"slot_date {slot_date} is outside the allowed booking window ({created_date} to {max_date})"
        )

    updated = update_appointment(
        appointment_id=appointment_id,
        status="booked",
        slot_date=slot_date.strip(),
        mode=mode or appt.get("mode") or "telehealth",
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    append_audit(
        actor_user_id=patient_id,
        action="appointment_booked",
        target=appointment_id,
        outcome="ok",
        detail={"slot_date": slot_date.strip(), "mode": mode or "telehealth"},
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    return compute_escalation_state(updated or appt, now_dt=now_dt)


def cancel_appointment(
    appointment_id: str,
    patient_id: str,
    now_dt: Optional[datetime] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """Patient cancels their appointment."""
    appt = get_appointment(appointment_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")
    if appt["patient_id"] != patient_id:
        raise PermissionError("Patient cannot cancel another patient's appointment")
    if appt["status"] == "attended":
        raise ValueError("Cannot cancel an appointment that was already attended")
    if appt["status"] == "cancelled":
        return compute_escalation_state(appt, now_dt=now_dt)

    updated = update_appointment(
        appointment_id=appointment_id,
        status="cancelled",
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    append_audit(
        actor_user_id=patient_id,
        action="appointment_cancelled",
        target=appointment_id,
        outcome="ok",
        detail={"previous_status": appt["status"]},
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    return compute_escalation_state(updated or appt, now_dt=now_dt)


def acknowledge_appointment(
    appointment_id: str,
    provider_id: str,
    now_dt: Optional[datetime] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """Provider acknowledges an appointment, clearing the escalation timeout."""
    appt = get_appointment(appointment_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")

    now = now_dt or datetime.now(UTC)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    updated = update_appointment(
        appointment_id=appointment_id,
        acknowledged_at=now_iso,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    append_audit(
        actor_user_id=provider_id,
        action="appointment_acknowledged",
        target=appointment_id,
        outcome="ok",
        detail={"acknowledged_by": provider_id},
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    return compute_escalation_state(updated or appt, now_dt=now_dt)


def mark_appointment_attended(
    appointment_id: str,
    provider_id: str,
    now_dt: Optional[datetime] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """Provider marks an appointment as attended."""
    appt = get_appointment(appointment_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
    if not appt:
        raise ValueError(f"Appointment {appointment_id} not found")

    updated = update_appointment(
        appointment_id=appointment_id,
        status="attended",
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    append_audit(
        actor_user_id=provider_id,
        action="appointment_attended",
        target=appointment_id,
        outcome="ok",
        detail={"attended_at": (now_dt or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")},
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )
    return compute_escalation_state(updated or appt, now_dt=now_dt)
