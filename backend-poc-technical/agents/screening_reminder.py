"""
Preventive Care Screening Reminder Agent (Part E, Decision D15).
Evaluates dormant HbA1c screening reminders for hypertensive adults without diagnosed diabetes.

Citation:
HbA1c LOINC code '4548-4' is mapped in data_sources/fhir_adapter.py:35 ("4548-4": "hba1c").
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

HBA1C_LOINC_CODE = "4548-4"
SCREENING_REMINDER_INTERVAL_DAYS: int = 365


def get_screening_interval_from_env() -> Optional[int]:
    raw = os.environ.get("SCREENING_REMINDER_INTERVAL_DAYS")
    if raw is not None and raw.strip():
        try:
            return int(raw.strip())
        except ValueError:
            return None
    return None


def _parse_date(d: Any) -> Optional[date]:
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    if not isinstance(d, str) or not d.strip():
        return None
    clean = d.strip()
    try:
        return datetime.fromisoformat(clean.replace("Z", "+00:00")).date()
    except Exception:
        pass
    try:
        return datetime.strptime(clean[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def hba1c_reminder(
    conditions: Optional[List[Any]],
    record_observations: Optional[List[Dict[str, Any]]],
    today: Optional[Any] = None,
    interval_days: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether an HbA1c screening reminder is appropriate for a patient.

    Dormancy Rule (D15):
    - When interval_days is None, this function returns None immediately.
      It remains dormant until clinicians explicitly configure an interval.
      There is NO default interval hardcoded in code.

    Applicability:
    - Applies ONLY to patients with hypertension and WITHOUT diabetes.

    Parameters
    ----------
    conditions : list
        Patient's recorded health conditions.
    record_observations : list of dict
        Clinical observations from health records or FHIR adapters.
    today : str or date, optional
        Reference evaluation date. Defaults to current date.
    interval_days : int, optional
        Clinician-defined screening interval in days. If None, remains dormant.

    Returns
    -------
    dict or None
        Screening reminder payload if overdue, or None.
    """
    if interval_days is None:
        interval_days = get_screening_interval_from_env()

    # 1. Dormant Check: If interval is unset or not positive, do nothing
    if interval_days is None or interval_days <= 0:
        return None

    # 2. Applicability: Hypertension without Diabetes
    if not conditions:
        return None
    cond_set = {str(c).strip().lower() for c in conditions}
    has_htn = any("hyper" in c for c in cond_set)
    has_t2d = any("diabet" in c for c in cond_set)
    if not has_htn or has_t2d:
        return None

    # 3. Reference date
    ref_date = _parse_date(today) or date.today()

    # 4. Search for HbA1c observations by LOINC code '4548-4'
    obs_list = record_observations or []
    newest_hba1c_date: Optional[date] = None
    newest_hba1c_iso: Optional[str] = None

    for obs in obs_list:
        if not isinstance(obs, dict):
            continue

        # Check code / LOINC
        code = str(obs.get("code") or obs.get("loinc") or "").strip()
        name = str(obs.get("display") or obs.get("name") or obs.get("concept") or "").strip().lower()

        is_hba1c = (code == HBA1C_LOINC_CODE) or ("4548-4" in code) or ("hba1c" in name) or ("hemoglobin a1c" in name)
        if not is_hba1c:
            continue

        obs_raw_date = obs.get("date") or obs.get("effective_datetime") or obs.get("observed_at") or obs.get("at")
        obs_dt = _parse_date(obs_raw_date)
        if obs_dt is not None:
            if newest_hba1c_date is None or obs_dt > newest_hba1c_date:
                newest_hba1c_date = obs_dt
                newest_hba1c_iso = obs_dt.isoformat()

    # 5. If an HbA1c was completed within the interval, no reminder needed
    if newest_hba1c_date is not None:
        elapsed_days = (ref_date - newest_hba1c_date).days
        if 0 <= elapsed_days <= interval_days:
            return None

    # 6. Reminder required: None in interval or never performed
    return {
        "type": "hba1c_reminder",
        "text": {
            "en": "Ask your doctor whether you need an HbA1c (sugar) test.",
            "ur": "اپنے ڈاکٹر سے پوچھیں کہ کیا آپ کو HbA1c (شوگر) ٹیسٹ کی ضرورت ہے۔",
            "roman_ur": "Apne doctor se poochein ke kya aap ko HbA1c (sugar) test ki zaroorat hai.",
        },
        "needs_doctor_review": True,
        "last_hba1c_at": newest_hba1c_iso,
    }
