"""
Daily Check-in Reminder Service for ChronicCare AI (PR I4-H).
Handles:
1. Detecting overdue daily check-ins for enrolled patients after their reminder hour (default 18:00 PKT).
2. Generating idempotent patient reminder notifications.
3. In-process asyncio background task during FastAPI lifespan when REMINDERS_ENABLED=true.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from data_sources.app_store import get_db_cursor
from services.notification_service import notify_daily_reminder

logger = logging.getLogger("reminder_service")

DEFAULT_REMINDER_HOUR = 18
REMINDER_UTC_OFFSET_HOURS = int(os.environ.get("REMINDER_UTC_OFFSET_HOURS", "5"))
DEFAULT_REMINDER_TZ = timezone(timedelta(hours=REMINDER_UTC_OFFSET_HOURS))


def is_reminders_enabled() -> bool:
    """Returns True only when explicitly enabled via REMINDERS_ENABLED environment variable."""
    return os.environ.get("REMINDERS_ENABLED", "").strip().lower() in ("true", "1", "yes")


def get_now_utc() -> datetime:
    """Returns the current UTC datetime (mockable for testing)."""
    return datetime.now(timezone.utc)


def get_local_now(now_dt: Optional[datetime] = None) -> datetime:
    """Converts now_dt (or current UTC time) into local Pakistan timezone."""
    if now_dt is None:
        now_dt = get_now_utc()
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    return now_dt.astimezone(DEFAULT_REMINDER_TZ)


def get_local_today_bounds(now_dt: Optional[datetime] = None) -> Tuple[str, str]:
    """
    Returns (today_str, midnight_utc_iso) in the local Pakistan timezone:
    today_str: 'YYYY-MM-DD' representing the calendar day in Pakistan.
    midnight_utc_iso: ISO UTC string of Pakistan midnight (00:00:00 local) for check-in queries.
    """
    local_dt = get_local_now(now_dt)
    today_str = local_dt.strftime("%Y-%m-%d")
    midnight_local = datetime(local_dt.year, local_dt.month, local_dt.day, 0, 0, 0, tzinfo=DEFAULT_REMINDER_TZ)
    midnight_utc = midnight_local.astimezone(timezone.utc)
    midnight_utc_iso = midnight_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return today_str, midnight_utc_iso


def is_patient_reminder_due(
    user_id: str,
    now_dt: Optional[datetime] = None,
    reminder_hour: int = DEFAULT_REMINDER_HOUR,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> bool:
    """
    Evaluates whether a daily check-in reminder is due for the given patient:
    1. Current local Pakistan hour >= reminder_hour.
    2. Patient has NOT completed or started a check-in today (after midnight local time).
    3. Patient has NOT already received a reminder notification today.
    """
    local_now = get_local_now(now_dt)
    if local_now.hour < reminder_hour:
        return False

    today_str, midnight_utc = get_local_today_bounds(now_dt)

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        # Check if patient already completed a check-in today
        checkin_q = f"SELECT checkin_id FROM checkins WHERE user_id = {ph} AND started_at >= {ph} LIMIT 1"
        cursor.execute(checkin_q, (user_id, midnight_utc))
        if cursor.fetchone():
            return False

        # Check if reminder already generated today
        ref_id = f"reminder_{user_id}_{today_str}"
        notif_q = f"SELECT id FROM notifications WHERE recipient_id = {ph} AND event_type = 'daily_reminder' AND reference_id = {ph} LIMIT 1"
        cursor.execute(notif_q, (user_id, ref_id))
        if cursor.fetchone():
            return False

    return True


def dispatch_due_reminders(
    now_dt: Optional[datetime] = None,
    reminder_hour: int = DEFAULT_REMINDER_HOUR,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> int:
    """
    Scans all active enrolled patients and dispatches daily check-in reminders
    for any whose reminder is due. Returns the number of reminders created.
    """
    today_str, _ = get_local_today_bounds(now_dt)
    dispatched = 0

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute("SELECT user_id FROM users WHERE role = 'patient' AND status = 'active'")
        patient_rows = cursor.fetchall()

    for row in patient_rows:
        pid = row[0]
        if is_patient_reminder_due(
            user_id=pid,
            now_dt=now_dt,
            reminder_hour=reminder_hour,
            backend=backend,
            db_path=db_path,
            mysql_url=mysql_url,
            ssl_ca=ssl_ca,
        ):
            notify_daily_reminder(
                patient_id=pid,
                reminder_date_iso=today_str,
                backend=backend,
                db_path=db_path,
                mysql_url=mysql_url,
                ssl_ca=ssl_ca,
            )
            dispatched += 1

    return dispatched


async def reminder_worker_loop(interval_seconds: int = 60) -> None:
    """In-process periodic background task running while the app is live."""
    logger.info("Starting reminder background worker loop...")
    try:
        while True:
            try:
                dispatched = dispatch_due_reminders()
                if dispatched > 0:
                    logger.info(f"Dispatched {dispatched} daily check-in reminder(s).")
            except Exception as e:
                logger.warning(f"Error during reminder dispatch pass: {e}")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Reminder background worker task cancelled cleanly.")
