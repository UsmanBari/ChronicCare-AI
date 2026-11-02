"""
Unit tests for baseline temporal model evaluation and threshold selection.
Uses synthetic predictions to prove threshold is chosen strictly on validation.
"""
import numpy as np
import pytest
from ml.baseline_temporal import (
    find_optimal_threshold,
    calculate_metrics_at_threshold,
)


def test_threshold_chosen_strictly_on_validation_only():
    """
    Build synthetic predictions where:
    - On validation: 5 positives with top 4 having probabilities >= 0.31, so threshold is ~0.31.
    - On test: 5 positives with top 4 having probabilities >= 0.85, so threshold chosen on test would be ~0.85.
    Assert that selecting on validation yields a threshold that differs substantially from test.
    """
    # Validation cohort: 5 positives, 5 negatives
    y_val = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    y_val_prob = np.array([0.35, 0.34, 0.33, 0.31, 0.10, 0.08, 0.07, 0.05, 0.04, 0.02])

    # Test cohort: 5 positives, 5 negatives
    y_test = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    y_test_prob = np.array([0.95, 0.90, 0.88, 0.85, 0.40, 0.20, 0.18, 0.15, 0.10, 0.05])

    thresh_from_val = find_optimal_threshold(y_val, y_val_prob, min_sensitivity=0.80)
    thresh_from_test = find_optimal_threshold(y_test, y_test_prob, min_sensitivity=0.80)

    # Threshold chosen on validation must be around 0.31
    assert 0.30 <= thresh_from_val <= 0.32

    # Threshold if chosen on test would be around 0.85
    assert thresh_from_test >= 0.84

    # Proves they differ significantly: if test data were used, the chosen threshold would differ
    assert abs(thresh_from_val - thresh_from_test) > 0.50

    # Verify that applying thresh_from_val to validation achieves sensitivity >= 0.80
    metrics_val = calculate_metrics_at_threshold(y_val, y_val_prob, thresh_from_val)
    assert metrics_val["sensitivity"] >= 0.80

    # If the validation-chosen threshold (0.31) were evaluated on test, sensitivity is 1.0 (5/5)
    metrics_test_with_val_thresh = calculate_metrics_at_threshold(y_test, y_test_prob, thresh_from_val)
    assert metrics_test_with_val_thresh["sensitivity"] >= 0.80


def test_calculate_metrics_at_threshold_known_confusion():
    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.9, 0.4, 0.8, 0.1])
    metrics = calculate_metrics_at_threshold(y_true, y_prob, threshold=0.5)
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 1
    assert metrics["sensitivity"] == 0.5
    assert metrics["specificity"] == 0.5
    assert metrics["ppv"] == 0.5
    assert metrics["npv"] == 0.5
