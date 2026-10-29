"""
Trend Agent Module (Iteration 2 - Day 4).

Deterministic, advisory-only medical decision-support module that evaluates
the directional trajectory (rising, stable, falling, not_enough_history) of
physiological readings over a recent window.

SAFETY INVARIANT:
- Pure stdlib only, no I/O, no DB access, no ML or scipy.
- Advisory only: NEVER sets, changes, escalates, or lowers any triage level.
- "The model proposes, the rules decide."
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Imported directly from triage_protocol (never hard-coded)
from agents.triage_protocol import BASELINE_MIN_READINGS

# Direction Constants
DIRECTION_RISING = "rising"
DIRECTION_FALLING = "falling"
DIRECTION_STABLE = "stable"
DIRECTION_NOT_ENOUGH_HISTORY = "not_enough_history"

VALID_DIRECTIONS = {
    DIRECTION_RISING,
    DIRECTION_FALLING,
    DIRECTION_STABLE,
    DIRECTION_NOT_ENOUGH_HISTORY,
}

# Monitored Observation Types
TYPE_SYSTOLIC = "blood_pressure_systolic"
TYPE_DIASTOLIC = "blood_pressure_diastolic"
TYPE_GLUCOSE = "glucose"

MONITORED_TYPES = (
    TYPE_SYSTOLIC,
    TYPE_DIASTOLIC,
    TYPE_GLUCOSE,
)

# PROPOSED - needs Usman + doctor review
TREND_THRESHOLDS: Dict[str, float] = {
    TYPE_SYSTOLIC: 10.0,   # mmHg delta between earlier and recent half
    TYPE_DIASTOLIC: 5.0,    # mmHg delta
    TYPE_GLUCOSE: 20.0,     # mg/dL delta
}

# Plausibility Ranges (readings outside these are excluded from trends)
PLAUSIBLE_RANGES: Dict[str, Tuple[float, float]] = {
    TYPE_SYSTOLIC: (50.0, 300.0),
    TYPE_DIASTOLIC: (30.0, 200.0),
    TYPE_GLUCOSE: (20.0, 1000.0),
}

# Multilingual Labels (English, Urdu Nastaliq, Roman Urdu)
# Marked needs_native_review for clinical terminology verification
TREND_LABELS: Dict[str, Dict[str, str]] = {
    DIRECTION_RISING: {
        "en": "Rising",
        "ur": "اوپر کی طرف",
        "roman_ur": "Upar ki taraf",
    },
    DIRECTION_FALLING: {
        "en": "Falling",
        "ur": "نیچے کی طرف",
        "roman_ur": "Neechay ki taraf",
    },
    DIRECTION_STABLE: {
        "en": "Stable",
        "ur": "مستحکم",
        "roman_ur": "Mustahkam",
    },
    DIRECTION_NOT_ENOUGH_HISTORY: {
        "en": "Not enough history",
        "ur": "ناکافی ریکارڈ",
        "roman_ur": "Na-kaafi record",
    },
    "summary_pattern": {
        "en": "{n} readings in {days} days",
        "ur": "{days} دنوں میں {n} ریکارڈنگز",
        "roman_ur": "{days} dino mein {n} readings",
    },
}

MAX_DISPLAY_VALUES = 14


def _parse_utc_iso(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string into a timezone-aware UTC datetime."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    cleaned = ts_str.strip()
    if not cleaned:
        return None
    try:
        # Normalize trailing Z to +00:00 for fromisoformat
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _format_utc_iso(dt: datetime) -> str:
    """Format a UTC datetime into ISO 8601 format ending with Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _calculate_theil_sen_slope(points: Sequence[Tuple[datetime, float]]) -> float:
    """
    Compute the Theil-Sen robust slope per week (7 days) in pure Python.
    Pairwise slope = (v_j - v_i) / (t_j - t_i in days) * 7.0.
    Returns the median of all pairwise slopes.
    """
    n = len(points)
    if n < 2:
        return 0.0

    slopes: List[float] = []
    for i in range(n):
        t_i, v_i = points[i]
        for j in range(i + 1, n):
            t_j, v_j = points[j]
            dt_seconds = (t_j - t_i).total_seconds()
            if dt_seconds > 0:
                dt_days = dt_seconds / 86400.0
                slope_week = ((v_j - v_i) / dt_days) * 7.0
                slopes.append(slope_week)

    if not slopes:
        return 0.0

    return statistics.median(slopes)


def compute_trends(
    history: List[Dict[str, Any]],
    now: Optional[str] = None,
    window_days: int = 30,
) -> Dict[str, Any]:
    """
    Pure deterministic trend agent evaluation.

    Args:
        history: List of reading records, each containing:
                 {"observation_type": str, "value": float | int, "timestamp": str}
        now: Optional ISO string representing evaluation reference time.
        window_days: Observation window in days (default 30).

    Returns:
        Structured dict with:
        {
          "generated_at": str,
          "advisory": True,
          "window_days": int,
          "excluded_count": int,
          "trends": {
             <observation_type>: {
                 "direction": "rising" | "falling" | "stable" | "not_enough_history",
                 "n": int,
                 "window_days": int,
                 "first_at": str | None,
                 "last_at": str | None,
                 "median_earlier": float | None,
                 "median_recent": float | None,
                 "change": float | None,
                 "slope_per_week": float | None,
                 "values": [{"value": float, "at": str}]  # max 14, oldest -> newest
             }
          }
        }
    """
    ref_dt = _parse_utc_iso(now) if now else None
    if ref_dt is None:
        ref_dt = datetime.now(timezone.utc)
    else:
        ref_dt = ref_dt.astimezone(timezone.utc)

    window_start = ref_dt - timedelta(days=window_days)
    generated_at_str = _format_utc_iso(ref_dt)

    excluded_count = 0
    raw_by_type: Dict[str, List[Tuple[datetime, float]]] = {t: [] for t in MONITORED_TYPES}

    for item in history or []:
        if not isinstance(item, dict):
            excluded_count += 1
            continue

        obs_type = item.get("observation_type")
        if obs_type not in raw_by_type:
            # Not a monitored observation type
            continue

        raw_val = item.get("value")
        raw_ts = item.get("timestamp")

        # Exclude None or boolean values (in Python bool is an int subclass)
        if raw_val is None or isinstance(raw_val, bool):
            excluded_count += 1
            continue

        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            excluded_count += 1
            continue

        # Check plausible clinical bounds
        min_p, max_p = PLAUSIBLE_RANGES[obs_type]
        if not (min_p <= val <= max_p):
            excluded_count += 1
            continue

        dt = _parse_utc_iso(raw_ts)
        if dt is None:
            excluded_count += 1
            continue

        # Check time window: window_start <= dt <= ref_dt
        if not (window_start <= dt <= ref_dt):
            # Outside observation window
            continue

        raw_by_type[obs_type].append((dt, val))

    trends: Dict[str, Any] = {}

    for obs_type in MONITORED_TYPES:
        entries = raw_by_type[obs_type]

        # 1. Sort by time ascending
        entries.sort(key=lambda x: x[0])

        # 2. De-duplicate identical timestamps (keep the latest observed value)
        deduped: List[Tuple[datetime, float]] = []
        for dt, val in entries:
            if deduped and deduped[-1][0] == dt:
                deduped[-1] = (dt, val)
            else:
                deduped.append((dt, val))

        n = len(deduped)
        threshold = TREND_THRESHOLDS[obs_type]

        # Form values list (capped at MAX_DISPLAY_VALUES, oldest -> newest)
        display_entries = deduped[-MAX_DISPLAY_VALUES:] if n > MAX_DISPLAY_VALUES else deduped
        values_list = [{"value": round(v, 2), "at": _format_utc_iso(t)} for t, v in display_entries]

        first_at = _format_utc_iso(deduped[0][0]) if n > 0 else None
        last_at = _format_utc_iso(deduped[-1][0]) if n > 0 else None

        if n < BASELINE_MIN_READINGS:
            trends[obs_type] = {
                "direction": DIRECTION_NOT_ENOUGH_HISTORY,
                "n": n,
                "window_days": window_days,
                "first_at": first_at,
                "last_at": last_at,
                "median_earlier": None,
                "median_recent": None,
                "change": None,
                "slope_per_week": None,
                "values": values_list,
            }
            continue

        # Split into earlier half and recent half
        # For odd n, middle reading index n // 2 goes to recent half
        split_idx = n // 2
        earlier_vals = [v for _, v in deduped[:split_idx]]
        recent_vals = [v for _, v in deduped[split_idx:]]

        median_earlier = statistics.median(earlier_vals)
        median_recent = statistics.median(recent_vals)
        change = round(median_recent - median_earlier, 2)

        slope_per_week = round(_calculate_theil_sen_slope(deduped), 4)

        # Dual-Agreement Direction Rule:
        # Rising only if change >= +threshold AND slope_per_week > 0
        # Falling only if change <= -threshold AND slope_per_week < 0
        # Otherwise stable
        if change >= threshold and slope_per_week > 0:
            direction = DIRECTION_RISING
        elif change <= -threshold and slope_per_week < 0:
            direction = DIRECTION_FALLING
        else:
            direction = DIRECTION_STABLE

        trends[obs_type] = {
            "direction": direction,
            "n": n,
            "window_days": window_days,
            "first_at": first_at,
            "last_at": last_at,
            "median_earlier": round(median_earlier, 2),
            "median_recent": round(median_recent, 2),
            "change": change,
            "slope_per_week": slope_per_week,
            "values": values_list,
        }

    return {
        "generated_at": generated_at_str,
        "advisory": True,
        "window_days": window_days,
        "excluded_count": excluded_count,
        "trends": trends,
    }

