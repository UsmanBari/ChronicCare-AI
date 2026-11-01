"""
Hermetic Tests for Preventive Screening Reminder Agent (Part E & F).
Verifies dormancy rules, LOINC 4548-4 detection, interval calculations,
and exact approved wording.
"""
from __future__ import annotations

from datetime import date, timedelta

from agents.screening_reminder import HBA1C_LOINC_CODE, hba1c_reminder


def test_dormant_by_default_when_interval_none():
    """Reminder remains strictly dormant (returns None) when interval_days is None or not positive."""
    conditions = ["hypertension"]
    obs = []

    assert hba1c_reminder(conditions, obs, interval_days=None) is None
    assert hba1c_reminder(conditions, obs, interval_days=0) is None
    assert hba1c_reminder(conditions, obs, interval_days=-30) is None


def test_applicability_hypertension_without_diabetes_only():
    """Reminder applies only to hypertension without diabetes."""
    interval = 365
    obs = []

    # 1. Diabetes only -> None
    assert hba1c_reminder(["diabetes"], obs, interval_days=interval) is None

    # 2. Dual diagnosis -> None
    assert hba1c_reminder(["hypertension", "diabetes"], obs, interval_days=interval) is None

    # 3. Neither -> None
    assert hba1c_reminder([], obs, interval_days=interval) is None
    assert hba1c_reminder(None, obs, interval_days=interval) is None

    # 4. Hypertension only -> triggers reminder when no HbA1c
    res = hba1c_reminder(["hypertension"], obs, interval_days=interval)
    assert res is not None
    assert res["type"] == "hba1c_reminder"


def test_hba1c_overdue_or_missing_triggers_reminder():
    """Hypertensive patient with missing or overdue HbA1c receives screening reminder."""
    ref_date = date(2026, 10, 30)
    interval = 365

    # Case 1: No observations at all
    res_no_obs = hba1c_reminder(["hypertension"], [], today=ref_date, interval_days=interval)
    assert res_no_obs is not None
    assert res_no_obs["type"] == "hba1c_reminder"
    assert res_no_obs["last_hba1c_at"] is None
    assert res_no_obs["needs_doctor_review"] is True
    assert res_no_obs["text"]["en"] == "Ask your doctor whether you need an HbA1c (sugar) test."
    assert "HbA1c" in res_no_obs["text"]["ur"]
    assert "HbA1c" in res_no_obs["text"]["roman_ur"]

    # Case 2: Observation older than interval (e.g. 400 days old)
    old_date = (ref_date - timedelta(days=400)).isoformat()
    old_obs = [{"code": HBA1C_LOINC_CODE, "date": old_date, "value": 5.8}]
    res_old = hba1c_reminder(["hypertension"], old_obs, today=ref_date, interval_days=interval)
    assert res_old is not None
    assert res_old["last_hba1c_at"] == old_date[:10]


def test_recent_hba1c_suppresses_reminder():
    """Recent HbA1c within interval suppresses reminder (returns None)."""
    ref_date = date(2026, 10, 30)
    interval = 365

    # HbA1c 60 days ago
    recent_date = (ref_date - timedelta(days=60)).isoformat()
    recent_obs = [
        {"loinc": "4548-4", "display": "Hemoglobin A1c", "effective_datetime": recent_date, "value": 5.9}
    ]
    res = hba1c_reminder(["hypertension"], recent_obs, today=ref_date, interval_days=interval)
    assert res is None
