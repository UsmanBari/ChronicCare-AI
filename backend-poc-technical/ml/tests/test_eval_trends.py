"""
Hermetic Unit Tests for Trend Agent Evaluation & Decision D9 Sensitivity.

Tests:
1. Synthetic series generator determinism and reproducibility.
2. Metric evaluator on hand-crafted toy physiological series (flat, rising, falling, outlier).
3. Glucose mixed-context detection invariant.
4. Consecutive-window sliding flip calculation.
5. Decision D9 sensitivity matrix generation.
6. Zero network, zero external DB, guaranteed to pass WITHOUT $env:CHRONICCARE_DATA_DIR.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import random
import sys
from typing import Any, Dict, List

import pytest

# Ensure repo and backend directories are in python path
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agents.trend_agent as trend_agent
from agents.trend_agent import (
    DIRECTION_FALLING,
    DIRECTION_NOT_ENOUGH_HISTORY,
    DIRECTION_RISING,
    DIRECTION_STABLE,
    TYPE_DIASTOLIC,
    TYPE_GLUCOSE,
    TYPE_SYSTOLIC,
    compute_trends,
)
from scripts.eval_trends import (
    OBSERVATION_CONFIGS,
    SCENARIO_FLAT,
    SCENARIO_MILD_FALLING,
    SCENARIO_MILD_RISING,
    SCENARIO_MIXED_CONTEXTS,
    SCENARIO_OUTLIER,
    evaluate_decision_d9_sensitivity,
    evaluate_scenario_performance,
    evaluate_sliding_window_flips,
    generate_synthetic_series,
    patch_trend_config,
)


def test_series_generator_deterministic() -> None:
    """Verifies that identical RNG seeds yield identical synthetic series."""
    ref_dt = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
    
    series_a = generate_synthetic_series(
        obs_type=TYPE_SYSTOLIC,
        scenario_key=SCENARIO_FLAT,
        n_readings=5,
        ref_dt=ref_dt,
        rng=random.Random(42),
    )
    series_b = generate_synthetic_series(
        obs_type=TYPE_SYSTOLIC,
        scenario_key=SCENARIO_FLAT,
        n_readings=5,
        ref_dt=ref_dt,
        rng=random.Random(42),
    )
    assert series_a == series_b
    assert len(series_a) == 5

    # Different seed produces different values
    series_c = generate_synthetic_series(
        obs_type=TYPE_SYSTOLIC,
        scenario_key=SCENARIO_FLAT,
        n_readings=5,
        ref_dt=ref_dt,
        rng=random.Random(999),
    )
    assert series_a != series_c


def test_hand_crafted_toy_series_evaluations() -> None:
    """
    Evaluates compute_trends on hand-crafted deterministic toy series:
    1. Strictly flat series -> STABLE (100% correct, 0% false alarms)
    2. Strictly rising series -> RISING (100% correct, 0% missed)
    3. Strictly falling series -> FALLING (100% correct, 0% missed)
    4. Single outlier spike -> STABLE (median resilience)
    """
    now_str = "2026-10-30T12:00:00Z"

    # 1. Strictly Flat Series (5 points at 120.0 mmHg)
    flat_history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": f"2026-10-{10+i:02d}T10:00:00Z"}
        for i in range(5)
    ]
    res_flat = compute_trends(flat_history, now=now_str, window_days=30)
    assert res_flat["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_STABLE
    assert res_flat["trends"][TYPE_SYSTOLIC]["change"] == 0.0

    # 2. Strictly Rising Series (120 -> 140 over 5 points, delta = +20 > 10.0 threshold)
    rising_history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0 + (i * 5.0), "timestamp": f"2026-10-{10+i:02d}T10:00:00Z"}
        for i in range(5)
    ]
    res_rising = compute_trends(rising_history, now=now_str, window_days=30)
    assert res_rising["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_RISING
    assert res_rising["trends"][TYPE_SYSTOLIC]["change"] > 0
    assert res_rising["trends"][TYPE_SYSTOLIC]["slope_per_week"] > 0

    # 3. Strictly Falling Series (140 -> 120 over 5 points, delta = -20 < -10.0 threshold)
    falling_history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 140.0 - (i * 5.0), "timestamp": f"2026-10-{10+i:02d}T10:00:00Z"}
        for i in range(5)
    ]
    res_falling = compute_trends(falling_history, now=now_str, window_days=30)
    assert res_falling["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_FALLING
    assert res_falling["trends"][TYPE_SYSTOLIC]["change"] < 0
    assert res_falling["trends"][TYPE_SYSTOLIC]["slope_per_week"] < 0

    # 4. Outlier Spike at n=5: [120, 120, 120, 120, 160] (median recent = 120, change = 0)
    outlier_history = [
        {"observation_type": TYPE_SYSTOLIC, "value": 120.0, "timestamp": f"2026-10-{10+i:02d}T10:00:00Z"}
        for i in range(4)
    ]
    outlier_history.append({"observation_type": TYPE_SYSTOLIC, "value": 160.0, "timestamp": "2026-10-15T10:00:00Z"})
    res_outlier = compute_trends(outlier_history, now=now_str, window_days=30)
    assert res_outlier["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_STABLE
    assert res_outlier["trends"][TYPE_SYSTOLIC]["change"] == 0.0


def test_glucose_mixed_context_detection() -> None:
    """Verifies that mixed fasting and postprandial glucose contexts trigger mixed_contexts=True."""
    now_str = "2026-10-30T12:00:00Z"
    mixed_history = [
        {"observation_type": TYPE_GLUCOSE, "value": 100.0, "timestamp": "2026-10-10T08:00:00Z", "glucose_context": "fasting"},
        {"observation_type": TYPE_GLUCOSE, "value": 150.0, "timestamp": "2026-10-11T13:00:00Z", "glucose_context": "after_meal"},
        {"observation_type": TYPE_GLUCOSE, "value": 102.0, "timestamp": "2026-10-12T08:00:00Z", "glucose_context": "fasting"},
        {"observation_type": TYPE_GLUCOSE, "value": 155.0, "timestamp": "2026-10-13T13:00:00Z", "glucose_context": "after_meal"},
    ]
    res = compute_trends(mixed_history, now=now_str, window_days=30)
    glu = res["trends"][TYPE_GLUCOSE]
    assert glu["mixed_contexts"] is True
    assert "after_meal" in glu["contexts_seen"]
    assert "fasting" in glu["contexts_seen"]

    # Uniform context
    uniform_history = [
        {"observation_type": TYPE_GLUCOSE, "value": 100.0 + i, "timestamp": f"2026-10-{10+i:02d}T08:00:00Z", "glucose_context": "fasting"}
        for i in range(4)
    ]
    res_uni = compute_trends(uniform_history, now=now_str, window_days=30)
    assert res_uni["trends"][TYPE_GLUCOSE]["mixed_contexts"] is False
    assert res_uni["trends"][TYPE_GLUCOSE]["contexts_seen"] == ["fasting"]


def test_patch_trend_config_isolation() -> None:
    """Verifies that patch_trend_config restores module state cleanly even on error."""
    orig_thresh = dict(trend_agent.TREND_THRESHOLDS)
    orig_min = trend_agent.BASELINE_MIN_READINGS

    with pytest.raises(RuntimeError):
        with patch_trend_config({TYPE_SYSTOLIC: 99.0}, min_readings=10):
            assert trend_agent.TREND_THRESHOLDS[TYPE_SYSTOLIC] == 99.0
            assert trend_agent.BASELINE_MIN_READINGS == 10
            raise RuntimeError("Test error inside context")

    assert trend_agent.TREND_THRESHOLDS == orig_thresh
    assert trend_agent.BASELINE_MIN_READINGS == orig_min


def test_sliding_window_flips_metrics() -> None:
    """Verifies sliding window flip calculator properly counts hard flips and returns schema."""
    flips = evaluate_sliding_window_flips(
        obs_type=TYPE_SYSTOLIC,
        n_patients=4,
        total_days=40,
        window_days=30,
        seed=123,
    )
    assert "n_patients" in flips
    assert flips["n_patients"] == 4
    assert "total_transitions" in flips
    assert flips["total_transitions"] > 0
    assert "flip_rate_pct" in flips
    assert 0.0 <= flips["flip_rate_pct"] <= 100.0


def test_sensitivity_matrix_execution() -> None:
    """Verifies that Decision D9 sensitivity matrix executes and formats all required metrics."""
    res = evaluate_decision_d9_sensitivity(n_series=10, seed=77)
    assert TYPE_SYSTOLIC in res
    assert TYPE_DIASTOLIC in res
    assert TYPE_GLUCOSE in res

    for row in res[TYPE_SYSTOLIC]:
        assert "threshold" in row
        assert "min_readings" in row
        assert "false_alarm_pct" in row
        assert "missed_trend_pct" in row
        assert "outlier_alarm_pct" in row
        assert "is_proposed" in row
        assert "is_current_operational" in row

    # Verify proposed setting is identified
    proposed_rows = [r for r in res[TYPE_SYSTOLIC] if r["is_proposed"]]
    assert len(proposed_rows) == 1
    assert proposed_rows[0]["threshold"] == 10.0
    assert proposed_rows[0]["min_readings"] == 5


def test_noise_free_straight_line_half_split_behavior() -> None:
    """Verifies straight-line series behavior against half-split median delta logic (T1).

    For an evenly spaced series with total rise D over n=15 readings:
    - total rise = 4x threshold (40 mmHg for SBP with threshold 10 mmHg):
      half-split delta ≈ 2x threshold (20 mmHg) -> evaluates to RISING.
    - total rise = 1x threshold (10 mmHg for SBP with threshold 10 mmHg):
      half-split delta ≈ 0.5x threshold (5 mmHg) -> evaluates to STABLE.
    """
    now_str = "2026-10-31T12:00:00Z"
    threshold = trend_agent.TREND_THRESHOLDS[TYPE_SYSTOLIC]  # 10.0 mmHg
    n = 15

    # 1. Total rise = 4x threshold (40.0 mmHg) -> RISING
    rise_4x = [
        {
            "observation_type": TYPE_SYSTOLIC,
            "value": 120.0 + (i * (4.0 * threshold) / (n - 1)),
            "timestamp": f"2026-10-{1+i:02d}T10:00:00Z",
        }
        for i in range(n)
    ]
    res_4x = compute_trends(rise_4x, now=now_str, window_days=30)
    assert res_4x["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_RISING

    # 2. Total rise = 1x threshold (10.0 mmHg) -> STABLE (half-split delta ≈ 5.7 mmHg < 10.0 threshold)
    rise_1x = [
        {
            "observation_type": TYPE_SYSTOLIC,
            "value": 120.0 + (i * (1.0 * threshold) / (n - 1)),
            "timestamp": f"2026-10-{1+i:02d}T10:00:00Z",
        }
        for i in range(n)
    ]
    res_1x = compute_trends(rise_1x, now=now_str, window_days=30)
    assert res_1x["trends"][TYPE_SYSTOLIC]["direction"] == DIRECTION_STABLE

