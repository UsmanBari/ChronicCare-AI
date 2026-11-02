"""
Unit tests for agents/trend_agent.py (Iteration 2 - Day 4).
Validates deterministic trend computation, edge cases, thresholds,
median + Theil-Sen slope dual-agreement rule, glucose context tracking,
app plausibility ranges, and safety invariants.
"""
from __future__ import annotations

import inspect
from typing import Any, Dict, List
import pytest

import agents.trend_agent as ta
from agents.trend_agent import (
    DIRECTION_FALLING,
    DIRECTION_NOT_ENOUGH_HISTORY,
    DIRECTION_RISING,
    DIRECTION_STABLE,
    TREND_LABELS,
    TREND_THRESHOLDS,
    TYPE_DIASTOLIC,
    TYPE_GLUCOSE,
    TYPE_SYSTOLIC,
    compute_trends,
)
import agents.triage_protocol as tp

NOW = "2026-10-29T12:00:00Z"


def _make_readings(
    obs_type: str,
    values_and_days_ago: List[tuple[float, int]],
) -> List[Dict[str, Any]]:
    """Helper to create reading records at specified days before NOW."""
    items = []
    for val, days in values_and_days_ago:
        # Construct ISO timestamp (2026-10-29 minus days)
        day_num = 29 - days
        if day_num > 0:
            ts = f"2026-10-{day_num:02d}T10:00:00Z"
        else:
            # Fallback to September
            ts = f"2026-09-{30 + day_num:02d}T10:00:00Z"
        items.append({
            "observation_type": obs_type,
            "value": val,
            "timestamp": ts,
        })
    return items


# =============================================================================
# 1. History Count Thresholds (0, 1, 2 -> not_enough_history; exactly 3 -> direction)
# =============================================================================
@pytest.mark.parametrize("obs_type", [TYPE_SYSTOLIC, TYPE_DIASTOLIC, TYPE_GLUCOSE])
@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient_history_returns_not_enough_history(obs_type: str, count: int):
    raw = [(120.0 + i, 10 - i) for i in range(count)]
    history = _make_readings(obs_type, raw)
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][obs_type]
    assert t["direction"] == DIRECTION_NOT_ENOUGH_HISTORY
    assert t["n"] == count
    assert t["few_readings"] is False
    assert t["median_earlier"] is None
    assert t["median_recent"] is None
    assert t["change"] is None
    assert t["slope_per_week"] is None


@pytest.mark.parametrize("obs_type, base_val", [
    (TYPE_SYSTOLIC, 120.0),
    (TYPE_DIASTOLIC, 80.0),
    (TYPE_GLUCOSE, 110.0),
])
def test_exactly_three_readings_produces_evaluated_direction(obs_type: str, base_val: float):
    # 3 stable readings
    history = _make_readings(obs_type, [(base_val, 15), (base_val, 10), (base_val, 5)])
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][obs_type]
    assert t["direction"] == DIRECTION_STABLE
    assert t["n"] == 3
    assert t["few_readings"] is True
    assert t["median_earlier"] is not None
    assert t["median_recent"] is not None
    assert t["change"] == 0.0
    assert t["slope_per_week"] == 0.0


# =============================================================================
# 2. Clear Rising, Falling, Stable Directions per Monitored Type
# =============================================================================
@pytest.mark.parametrize("obs_type, values, expected_dir", [
    # Systolic (threshold 10)
    (TYPE_SYSTOLIC, [120.0, 122.0, 134.0, 138.0], DIRECTION_RISING),
    (TYPE_SYSTOLIC, [140.0, 138.0, 124.0, 120.0], DIRECTION_FALLING),
    (TYPE_SYSTOLIC, [120.0, 122.0, 121.0, 123.0], DIRECTION_STABLE),
    # Diastolic (threshold 5)
    (TYPE_DIASTOLIC, [75.0, 76.0, 83.0, 84.0], DIRECTION_RISING),
    (TYPE_DIASTOLIC, [85.0, 84.0, 77.0, 76.0], DIRECTION_FALLING),
    (TYPE_DIASTOLIC, [80.0, 81.0, 80.0, 81.0], DIRECTION_STABLE),
    # Glucose (threshold 20)
    (TYPE_GLUCOSE, [100.0, 105.0, 130.0, 135.0], DIRECTION_RISING),
    (TYPE_GLUCOSE, [140.0, 135.0, 110.0, 105.0], DIRECTION_FALLING),
    (TYPE_GLUCOSE, [110.0, 115.0, 112.0, 116.0], DIRECTION_STABLE),
])
def test_clear_directions_for_all_types(obs_type: str, values: List[float], expected_dir: str):
    # Days ago: 20, 15, 10, 5
    pairs = [(v, 20 - i * 5) for i, v in enumerate(values)]
    history = _make_readings(obs_type, pairs)
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][obs_type]
    assert t["direction"] == expected_dir


# =============================================================================
# 3. Boundary Tests: Just Below vs. Just at Threshold
# =============================================================================
@pytest.mark.parametrize("obs_type, base, thresh", [
    (TYPE_SYSTOLIC, 120.0, 10.0),
    (TYPE_DIASTOLIC, 80.0, 5.0),
    (TYPE_GLUCOSE, 100.0, 20.0),
])
def test_threshold_boundary_rising(obs_type: str, base: float, thresh: float):
    # Just below threshold (change = thresh - 0.1) -> STABLE
    below_vals = [(base, 20), (base, 15), (base + thresh - 0.1, 10), (base + thresh - 0.1, 5)]
    res_below = compute_trends(_make_readings(obs_type, below_vals), now=NOW)
    assert res_below["trends"][obs_type]["direction"] == DIRECTION_STABLE

    # Exactly at threshold (change = thresh) -> RISING
    at_vals = [(base, 20), (base, 15), (base + thresh, 10), (base + thresh, 5)]
    res_at = compute_trends(_make_readings(obs_type, at_vals), now=NOW)
    assert res_at["trends"][obs_type]["direction"] == DIRECTION_RISING


@pytest.mark.parametrize("obs_type, base, thresh", [
    (TYPE_SYSTOLIC, 140.0, 10.0),
    (TYPE_DIASTOLIC, 90.0, 5.0),
    (TYPE_GLUCOSE, 140.0, 20.0),
])
def test_threshold_boundary_falling(obs_type: str, base: float, thresh: float):
    # Just above negative threshold (change = -(thresh - 0.1)) -> STABLE
    below_vals = [(base, 20), (base, 15), (base - thresh + 0.1, 10), (base - thresh + 0.1, 5)]
    res_below = compute_trends(_make_readings(obs_type, below_vals), now=NOW)
    assert res_below["trends"][obs_type]["direction"] == DIRECTION_STABLE

    # Exactly at negative threshold (change = -thresh) -> FALLING
    at_vals = [(base, 20), (base, 15), (base - thresh, 10), (base - thresh, 5)]
    res_at = compute_trends(_make_readings(obs_type, at_vals), now=NOW)
    assert res_at["trends"][obs_type]["direction"] == DIRECTION_FALLING


# =============================================================================
# 4. Outlier Resistance & Spike Behavior Across Sample Sizes (FIX 2)
# =============================================================================
@pytest.mark.parametrize("n, expected_direction, expected_few_readings", [
    (3, DIRECTION_RISING, True),
    (4, DIRECTION_RISING, True),
    (5, DIRECTION_STABLE, False),
    (7, DIRECTION_STABLE, False),
])
def test_spike_behavior_across_sample_sizes(n: int, expected_direction: str, expected_few_readings: bool):
    """
    Pins the current behavior documented in TREND_AGENT.md section 8:
    - With 3-4 readings, a single acute terminal spike to 200 pulls the median and slope to 'rising'.
    - At 5+ readings, median split and Theil-Sen resist the spike and evaluate to 'stable'.
    - 'few_readings' flag is True for 3 <= n < 5 and False for n >= 5.
    """
    history = [
        {"observation_type": TYPE_GLUCOSE, "value": 120.0, "timestamp": f"2026-10-{10+i:02d}T08:00:00Z"}
        for i in range(n - 1)
    ]
    history.append(
        {"observation_type": TYPE_GLUCOSE, "value": 200.0, "timestamp": f"2026-10-{10+n-1:02d}T08:00:00Z"}
    )
    res = compute_trends(history, now=NOW)
    t = res["trends"][TYPE_GLUCOSE]
    assert t["direction"] == expected_direction
    assert t["few_readings"] is expected_few_readings


def test_single_spike_outlier_does_not_flip_to_rising_at_n5():
    # Baseline systolic around 120-122 with a single acute stress spike of 165
    raw = [
        (120.0, 25),
        (122.0, 20),
        (121.0, 15),
        (165.0, 10),  # Single anomalous spike
        (122.0, 5),
    ]
    history = _make_readings(TYPE_SYSTOLIC, raw)
    res = compute_trends(history, now=NOW)
    t = res["trends"][TYPE_SYSTOLIC]
    # For n=5: earlier = [120, 122] (median 121); recent = [121, 165, 122] (median 122)
    # change = 122 - 121 = 1.0 mmHg (< 10.0 threshold) -> STABLE
    assert t["direction"] == DIRECTION_STABLE
    assert t["change"] == 1.0
    assert t["few_readings"] is False


def test_single_dip_outlier_does_not_flip_to_falling_at_n5():
    # Baseline glucose around 125 with a single spurious dip of 60
    raw = [
        (125.0, 25),
        (126.0, 20),
        (124.0, 15),
        (60.0, 10),  # Single acute dip
        (125.0, 5),
    ]
    history = _make_readings(TYPE_GLUCOSE, raw)
    res = compute_trends(history, now=NOW)
    t = res["trends"][TYPE_GLUCOSE]
    assert t["direction"] == DIRECTION_STABLE
    assert t["few_readings"] is False


# =============================================================================
# 5. Dual Agreement: Median vs. Slope Disagreement Must Yield Stable
# =============================================================================
def test_conflict_median_positive_slope_non_positive_yields_stable():
    """
    CRITICAL MUTATION KILLER TEST (M-S4-1):
    Construct a scenario where median delta >= threshold but Theil-Sen slope is <= 0.
    Under the dual-agreement rule, direction must be STABLE.
    A mutated algorithm using median alone will falsely report RISING.
    """
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 100.0, "timestamp": "2026-10-01T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 150.0, "timestamp": "2026-10-02T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 145.0, "timestamp": "2026-10-03T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 140.0, "timestamp": "2026-10-04T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 135.0, "timestamp": "2026-10-05T10:00:00Z"},
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][TYPE_SYSTOLIC]
    assert t["change"] == 15.0  # change is >= 10.0 threshold
    assert t["slope_per_week"] < 0  # but slope is negative (-35.0)
    # Must be STABLE because median delta and slope disagree!
    assert t["direction"] == DIRECTION_STABLE


# =============================================================================
# 6. Window Boundaries & Exclusion Logic (App PLAUSIBILITY_RANGES, FIX 1)
# =============================================================================
def test_window_boundary_filtering():
    # now = 2026-10-29T12:00:00Z, window_days = 30 -> cutoff = 2026-09-29T12:00:00Z
    history = [
        # 31 days old: should be excluded
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-09-28T10:00:00Z"},
        # Inside 30 days:
        {"observation_type": TYPE_SYSTOLIC, "value": 122.0, "timestamp": "2026-10-01T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 124.0, "timestamp": "2026-10-15T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 126.0, "timestamp": "2026-10-28T10:00:00Z"},
        # Future reading (beyond NOW): should be excluded
        {"observation_type": TYPE_SYSTOLIC, "value": 180.0, "timestamp": "2026-11-01T10:00:00Z"},
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][TYPE_SYSTOLIC]
    assert t["n"] == 3
    assert t["values"][0]["value"] == 122.0
    assert t["values"][-1]["value"] == 126.0


@pytest.mark.parametrize("bad_val", [None, True, False, "invalid", "120mmHg", float("nan"), 15.0, 50.0, 270.0, 350.0])
def test_invalid_and_out_of_range_readings_excluded(bad_val: Any):
    # App bounds for systolic are 60.0 to 260.0 mmHg
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": bad_val, "timestamp": "2026-10-10T10:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-10-15T10:00:00Z"},
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    assert res["excluded_count"] >= 1
    assert res["trends"][TYPE_SYSTOLIC]["n"] == 1


def test_monkeypatch_plausibility_bound_alters_exclusion(monkeypatch: pytest.MonkeyPatch):
    """
    FIX 1: Proves that the app's imported PLAUSIBILITY_RANGES is actively used.
    A reading of 220 mmHg is normally valid (<= 260).
    When monkeypatched to max 200, it is excluded.
    """
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 220.0, "timestamp": "2026-10-15T08:00:00Z"},
    ]
    # Normal: 220 is valid
    res_normal = compute_trends(history, now=NOW)
    assert res_normal["excluded_count"] == 0
    assert res_normal["trends"][TYPE_SYSTOLIC]["n"] == 1

    # Monkeypatch max to 200
    monkeypatch.setitem(ta.PLAUSIBILITY_RANGES["bp_systolic_mmhg"], "max", 200.0)
    res_patched = compute_trends(history, now=NOW)
    assert res_patched["excluded_count"] == 1
    assert res_patched["trends"][TYPE_SYSTOLIC]["n"] == 0


# =============================================================================
# 7. Deduplication of Identical Timestamps
# =============================================================================
def test_duplicate_timestamps_keeps_latest():
    history = [
        {"observation_type": TYPE_GLUCOSE, "value": 100.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_GLUCOSE, "value": 110.0, "timestamp": "2026-10-10T08:00:00Z"},  # latest
        {"observation_type": TYPE_GLUCOSE, "value": 115.0, "timestamp": "2026-10-15T08:00:00Z"},
        {"observation_type": TYPE_GLUCOSE, "value": 120.0, "timestamp": "2026-10-20T08:00:00Z"},
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][TYPE_GLUCOSE]
    assert t["n"] == 3
    # The duplicate at 2026-10-10T08:00:00Z should have kept 110.0, not 100.0
    assert t["values"][0]["value"] == 110.0


# =============================================================================
# 8. Capping Display Values at 14 (Oldest -> Newest)
# =============================================================================
def test_display_values_capped_at_14():
    # 20 readings across 20 days
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0 + i, "timestamp": f"2026-10-{i+1:02d}T08:00:00Z"}
        for i in range(20)
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    t = res["trends"][TYPE_SYSTOLIC]
    assert t["n"] == 20
    assert len(t["values"]) == 14
    # Oldest -> newest among the last 14
    assert t["values"][0]["value"] == 126.0  # index 6 (day 7)
    assert t["values"][-1]["value"] == 139.0  # index 19 (day 20)


# =============================================================================
# 9. Odd vs. Even Sample Splitting Rule
# =============================================================================
def test_odd_even_split_rule():
    # Even n=4: [120, 122, 134, 136] -> earlier = [120, 122] (med 121), recent = [134, 136] (med 135)
    even_hist = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-10-01T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 122.0, "timestamp": "2026-10-05T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 134.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 136.0, "timestamp": "2026-10-15T08:00:00Z"},
    ]
    res_even = compute_trends(even_hist, now=NOW)
    t_even = res_even["trends"][TYPE_SYSTOLIC]
    assert t_even["median_earlier"] == 121.0
    assert t_even["median_recent"] == 135.0
    assert t_even["change"] == 14.0

    # Odd n=5: [120, 122, 128, 134, 136] -> earlier = [120, 122] (med 121), recent = [128, 134, 136] (med 134)
    odd_hist = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-10-01T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 122.0, "timestamp": "2026-10-05T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 128.0, "timestamp": "2026-10-08T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 134.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 136.0, "timestamp": "2026-10-15T08:00:00Z"},
    ]
    res_odd = compute_trends(odd_hist, now=NOW)
    t_odd = res_odd["trends"][TYPE_SYSTOLIC]
    assert t_odd["median_earlier"] == 121.0
    assert t_odd["median_recent"] == 134.0
    assert t_odd["change"] == 13.0


# =============================================================================
# 10. Schema Keys & Metadata Assertions (including few_readings, glucose context)
# =============================================================================
def test_output_schema_keys_and_advisory_flag():
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 122.0, "timestamp": "2026-10-15T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 124.0, "timestamp": "2026-10-20T08:00:00Z"},
        {"observation_type": TYPE_GLUCOSE, "value": 110.0, "timestamp": "2026-10-20T08:00:00Z", "glucose_context": "fasting"},
    ]
    res = compute_trends(history, now=NOW, window_days=30)
    # Top-level schema
    assert set(res.keys()) == {"generated_at", "advisory", "window_days", "excluded_count", "trends"}
    assert res["advisory"] is True
    assert res["window_days"] == 30
    assert res["generated_at"].endswith("Z")

    # Base per-type schema
    expected_base_keys = {
        "direction",
        "n",
        "window_days",
        "few_readings",
        "first_at",
        "last_at",
        "median_earlier",
        "median_recent",
        "change",
        "slope_per_week",
        "values",
    }
    for obs_type in [TYPE_SYSTOLIC, TYPE_DIASTOLIC]:
        assert set(res["trends"][obs_type].keys()) == expected_base_keys

    # Glucose has contexts_seen and mixed_contexts
    expected_glucose_keys = expected_base_keys | {"contexts_seen", "mixed_contexts"}
    assert set(res["trends"][TYPE_GLUCOSE].keys()) == expected_glucose_keys


# =============================================================================
# 11. Glucose Context Tracking & Mixed Series Flag (FIX 3)
# =============================================================================
def test_glucose_contexts_seen_and_mixed_contexts_flag():
    # Case 1: Single context (fasting)
    h_single = [
        {"observation_type": TYPE_GLUCOSE, "value": 110.0, "timestamp": "2026-10-10T08:00:00Z", "glucose_context": "fasting"},
        {"observation_type": TYPE_GLUCOSE, "value": 112.0, "timestamp": "2026-10-15T08:00:00Z", "glucose_context": "fasting"},
        {"observation_type": TYPE_GLUCOSE, "value": 114.0, "timestamp": "2026-10-20T08:00:00Z", "glucose_context": "fasting"},
    ]
    res_single = compute_trends(h_single, now=NOW)
    t_single = res_single["trends"][TYPE_GLUCOSE]
    assert t_single["contexts_seen"] == ["fasting"]
    assert t_single["mixed_contexts"] is False

    # Case 2: Mixed contexts (fasting + post_meal)
    h_mixed = [
        {"observation_type": TYPE_GLUCOSE, "value": 110.0, "timestamp": "2026-10-10T08:00:00Z", "glucose_context": "fasting"},
        {"observation_type": TYPE_GLUCOSE, "value": 140.0, "timestamp": "2026-10-15T08:00:00Z", "glucose_context": "post_meal"},
        {"observation_type": TYPE_GLUCOSE, "value": 112.0, "timestamp": "2026-10-20T08:00:00Z", "glucose_context": "fasting"},
    ]
    res_mixed = compute_trends(h_mixed, now=NOW)
    t_mixed = res_mixed["trends"][TYPE_GLUCOSE]
    assert t_mixed["contexts_seen"] == ["fasting", "post_meal"]
    assert t_mixed["mixed_contexts"] is True

    # Case 3: No contexts specified
    h_none = [
        {"observation_type": TYPE_GLUCOSE, "value": 110.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_GLUCOSE, "value": 112.0, "timestamp": "2026-10-15T08:00:00Z"},
        {"observation_type": TYPE_GLUCOSE, "value": 114.0, "timestamp": "2026-10-20T08:00:00Z"},
    ]
    res_none = compute_trends(h_none, now=NOW)
    t_none = res_none["trends"][TYPE_GLUCOSE]
    assert t_none["contexts_seen"] == []
    assert t_none["mixed_contexts"] is False


# =============================================================================
# 12. Multilingual Presentation Labels & Review Catalog (FIX 4)
# =============================================================================
@pytest.mark.parametrize("direction_key", [
    DIRECTION_RISING,
    DIRECTION_FALLING,
    DIRECTION_STABLE,
    DIRECTION_NOT_ENOUGH_HISTORY,
])
def test_multilingual_labels_contain_en_ur_roman_ur(direction_key: str):
    labels = TREND_LABELS[direction_key]
    assert "en" in labels and len(labels["en"]) > 0
    assert "ur" in labels and len(labels["ur"]) > 0
    assert "roman_ur" in labels and len(labels["roman_ur"]) > 0


def test_summary_pattern_label_updated_simple_urdu():
    pattern = TREND_LABELS["summary_pattern"]
    assert pattern["en"] == "{n} readings in {days} days"
    assert pattern["ur"] == "{days} دن میں {n} ریڈنگ"
    assert pattern["roman_ur"] == "{days} din mein {n} reading"


def test_trend_labels_review_metadata():
    assert hasattr(ta, "TREND_LABELS_REVIEW")
    for key, item in ta.TREND_LABELS_REVIEW.items():
        assert item.get("needs_native_review") is True
        assert "en" in item and "ur" in item and "roman_ur" in item


# =============================================================================
# 13. Monkeypatch Proves Imported BASELINE_MIN_READINGS is Used
# =============================================================================
def test_monkeypatched_baseline_min_readings_changes_behavior(monkeypatch: pytest.MonkeyPatch):
    # Provide exactly 3 readings (normally enough for an evaluated direction)
    history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": "2026-10-10T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 122.0, "timestamp": "2026-10-15T08:00:00Z"},
        {"observation_type": TYPE_SYSTOLIC, "value": 124.0, "timestamp": "2026-10-20T08:00:00Z"},
    ]
    # Without patch: n=3 gives STABLE
    res_normal = compute_trends(history, now=NOW)
    assert res_normal["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_STABLE

    # Monkeypatch BASELINE_MIN_READINGS in trend_agent module to 4
    monkeypatch.setattr(ta, "BASELINE_MIN_READINGS", 4)
    res_patched = compute_trends(history, now=NOW)
    assert res_patched["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_NOT_ENOUGH_HISTORY


# =============================================================================
# 14. Architectural Invariant: Module Exposes NO Triage Modification
# =============================================================================
def test_trend_agent_exposes_no_triage_modifications():
    for name, obj in inspect.getmembers(ta):
        if inspect.isfunction(obj):
            # Check function names and docstrings do not modify triage
            assert not name.startswith("triage_")
            assert not name.startswith("escalate_")
            assert not name.startswith("lower_")
            sig = inspect.signature(obj)
            for param in sig.parameters.values():
                assert param.name != "triage_level"
