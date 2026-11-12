"""
Daily Check-in Reminder Service for ChronicCare AI (PR I4-H).
Handles:
1. Detecting overdue daily check-ins for enrolled patients after their reminder hour (default 18:00).
2. Generating idempotent patient reminder notifications.
3. In-process asyncio background task during FastAPI lifespan when REMINDERS_ENABLED=true.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from data_sources.app_store import get_db_cursor
from services.notification_service import notify_daily_reminder

logger = logging.getLogger("reminder_service")

DEFAULT_REMINDER_HOUR = 18


def is_reminders_enabled() -> bool:
    """Returns True only when explicitly enabled via REMINDERS_ENABLED environment variable."""
    return os.environ.get("REMINDERS_ENABLED", "").strip().lower() in ("true", "1", "yes")


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
    1. Current hour >= reminder_hour.
    2. Patient has NOT completed or started a check-in today (after midnight UTC).
    3. Patient has NOT already received a reminder notification today.
    """
    now = now_dt or datetime.now(UTC)
    if now.hour < reminder_hour:
        return False

    today_str = now.strftime("%Y-%m-%d")
    midnight_utc = f"{today_str}T00:00:00Z"

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
    now = now_dt or datetime.now(UTC)
    today_str = now.strftime("%Y-%m-%d")
    dispatched = 0

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute("SELECT user_id FROM users WHERE role = 'patient' AND status = 'active'")
        patient_rows = cursor.fetchall()

    for row in patient_rows:
        pid = row[0]
        if is_patient_reminder_due(
            user_id=pid,
            now_dt=now,
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
