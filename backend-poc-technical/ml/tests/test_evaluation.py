"""
Unit tests for ML evaluation toolkit (backend-poc-technical/ml/evaluation.py).
Strictly uses synthetic data arrays (never real patient or survey datasets).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.evaluation import (
    LeakageError,
    auprc,
    auroc,
    bootstrap_ci,
    calibration,
    check_leakage,
    choose_threshold,
    metrics_at_threshold,
    subgroup_report,
    write_eval_report,
)


# =====================================================================
# 1. Threshold Selection Tests
# =====================================================================

def test_choose_threshold_policies_synthetic():
    # 10 samples: 5 positive (1), 5 negative (0)
    # y: 0, 0, 0, 0, 0, 1, 1, 1, 1, 1
    # p: 0.1, 0.2, 0.3, 0.4, 0.45, 0.6, 0.7, 0.8, 0.9, 0.95
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    p = np.array([0.1, 0.2, 0.3, 0.4, 0.45, 0.6, 0.7, 0.8, 0.9, 0.95])

    # Fixed policy at t=0.50 (perfect separation)
    res_fixed = choose_threshold(y, p, policy={"type": "fixed", "value": 0.50})
    assert res_fixed["threshold"] == 0.50
    assert res_fixed["met"] is True
    assert res_fixed["val_sensitivity"] == 1.0
    assert res_fixed["val_specificity"] == 1.0

    # Youden policy (perfect separation at 0.50-0.60)
    res_youden = choose_threshold(y, p, policy={"type": "youden"})
    assert res_youden["met"] is True
    assert res_youden["val_sensitivity"] == 1.0
    assert res_youden["val_specificity"] == 1.0
    assert 0.45 < res_youden["threshold"] <= 0.60

    # Minimum sensitivity policy: target 0.80 (4/5 positives)
    # At t=0.7, positives >= 0.7 are [0.7, 0.8, 0.9, 0.95] -> 4/5 = 80% sensitivity
    res_min = choose_threshold(y, p, policy={"type": "min_sensitivity", "value": 0.80})
    assert res_min["met"] is True
    assert res_min["val_sensitivity"] >= 0.80
    assert res_min["threshold"] == pytest.approx(0.70, abs=0.01)


def test_choose_threshold_unmet_policy():
    # Target 1.5 sensitivity which cannot be reached
    y = np.array([0, 0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    res = choose_threshold(y, p, policy={"type": "min_sensitivity", "value": 1.5})
    assert res["met"] is False
    assert res["val_sensitivity"] == 1.0


def test_choose_threshold_tie_breaking():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.2, 0.4, 0.6, 0.8])
    res = choose_threshold(y, p, policy={"type": "min_sensitivity", "value": 0.80})
    assert res["met"] is True
    assert res["threshold"] >= 0.5


# =====================================================================
# 2. Metrics at Threshold Tests
# =====================================================================

def test_metrics_at_threshold_known_confusion_matrix():
    # 10 rows:
    # 3 TP (y=1, p>=0.5): indices 0, 1, 2
    # 2 FN (y=1, p<0.5): indices 3, 4
    # 4 TN (y=0, p<0.5): indices 5, 6, 7, 8
    # 1 FP (y=0, p>=0.5): index 9
    y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1, 0.2, 0.3, 0.4, 0.6])

    m = metrics_at_threshold(y, p, t=0.5)

    assert m["n"] == 10
    assert m["tp"] == 3
    assert m["fp"] == 1
    assert m["tn"] == 4
    assert m["fn"] == 2
    assert m["prevalence"] == pytest.approx(0.50)
    assert m["sensitivity"] == pytest.approx(3 / 5)
    assert m["specificity"] == pytest.approx(4 / 5)
    assert m["ppv"] == pytest.approx(3 / 4)
    assert m["npv"] == pytest.approx(4 / 6)
    expected_f1 = 2 * (3 / 4) * (3 / 5) / ((3 / 4) + (3 / 5))
    assert m["f1"] == pytest.approx(expected_f1)


def test_metrics_at_threshold_zero_denominators():
    y_zeros = np.array([0, 0, 0, 0])
    p_zeros = np.array([0.1, 0.2, 0.3, 0.4])

    m = metrics_at_threshold(y_zeros, p_zeros, t=0.5)
    assert m["sensitivity"] is None
    assert m["prevalence"] == 0.0
    assert m["ppv"] is None
    assert m["specificity"] == 1.0


# =====================================================================
# 3. Bootstrap CI Tests
# =====================================================================

def test_bootstrap_ci_reproducibility_and_stratification():
    rng = np.random.default_rng(100)
    y = np.array([0] * 50 + [1] * 50)
    p = rng.uniform(0.0, 1.0, size=100)

    ci_1 = bootstrap_ci(y, p, metric_fn=auroc, n_boot=200, seed=42)
    ci_2 = bootstrap_ci(y, p, metric_fn=auroc, n_boot=200, seed=42)

    assert ci_1[0] == pytest.approx(ci_2[0])
    assert ci_1[1] == pytest.approx(ci_2[1])
    assert ci_1[2] == pytest.approx(ci_2[2])

    ci_3 = bootstrap_ci(y, p, metric_fn=auroc, n_boot=200, seed=99)
    assert (ci_1[1], ci_1[2]) != (ci_3[1], ci_3[2])

    assert hasattr(ci_1, "skipped_count")
    assert ci_1.skipped_count == 0


def test_bootstrap_ci_single_class_skip_count():
    y = np.array([1, 1, 1, 1])
    p = np.array([0.5, 0.6, 0.7, 0.8])

    ci = bootstrap_ci(y, p, metric_fn=auroc, n_boot=50, seed=42, stratified=True)
    assert ci.skipped_count == 50


# =====================================================================
# 4. Calibration Tests
# =====================================================================

def test_calibration_perfectly_calibrated():
    rng = np.random.default_rng(42)
    n = 20000
    p = rng.uniform(0.01, 0.99, size=n)
    y = rng.binomial(1, p)

    cal = calibration(y, p, n_bins=10)

    assert 0.90 <= cal["slope"] <= 1.10
    assert -0.10 <= cal["intercept"] <= 0.10
    assert cal["brier"] is not None
    assert len(cal["reliability_table"]) > 0


def test_calibration_squeezed_underconfident():
    rng = np.random.default_rng(42)
    n = 20000
    p_true = rng.uniform(0.01, 0.99, size=n)
    y = rng.binomial(1, p_true)

    p_squeezed = 0.5 + 0.4 * (p_true - 0.5)

    cal = calibration(y, p_squeezed, n_bins=10)
    assert cal["slope"] > 1.2


# =====================================================================
# 5. Subgroup Report Tests
# =====================================================================

def test_subgroup_report_min_n_and_threshold():
    df = pd.DataFrame({
        "sex_male": [1] * 100 + [0] * 30,
        "told_diabetes": [1] * 20 + [0] * 80 + [1] * 5 + [0] * 25,
        "prob": np.linspace(0.1, 0.9, 130),
    })

    rows = subgroup_report(
        df,
        y_col="told_diabetes",
        p_col="prob",
        threshold=0.5,
        groups=["sex_male"],
        min_n=50,
    )

    male_row = next(r for r in rows if r["group_value"] == "Male")
    female_row = next(r for r in rows if r["group_value"] == "Female")

    assert male_row["n"] == 100
    assert isinstance(male_row["auroc"], float)
    assert isinstance(male_row["sensitivity"], float)

    assert female_row["n"] == 30
    assert female_row["auroc"] == "too few"
    assert female_row["sensitivity"] == "too few"


# =====================================================================
# 6. Leakage Check Tests
# =====================================================================

def test_check_leakage_detects_forbidden_features():
    with pytest.raises(LeakageError, match="hba1c"):
        check_leakage("diabetes_measured", ["age", "sex_male", "hba1c"])

    check_leakage("diabetes_told", ["age", "sex_male", "bmi"])


def test_check_leakage_detects_unknown_features_and_labels():
    with pytest.raises(ValueError, match="not recognized"):
        check_leakage("diabetes_told", ["age", "unreal_fake_marker"])

    with pytest.raises(KeyError, match="Unknown label"):
        check_leakage("fake_disease_label", ["age", "bmi"])


# =====================================================================
# 7. Write Evaluation Report Tests
# =====================================================================

def test_write_eval_report_sections(tmp_path):
    report_file = tmp_path / "test_report.md"

    sections = {
        "Config": "Model: LogisticRegression",
        "Data": "NHANES 2017-2023",
        "Test": "AUROC = 0.770",
    }

    write_eval_report(report_file, sections)
    content = report_file.read_text(encoding="utf-8")

    for heading in ["Config", "Data", "Validation", "Test", "Calibration", "Subgroups", "Limitations"]:
        assert f"## {heading}" in content

    assert "NOT RUN" in content
    assert "US Survey Population" in content
    assert "Survey Weights Omitted" in content


# =====================================================================
# 8. No Test Peeking Guard Test
# =====================================================================

def test_no_test_peeking_guard(monkeypatch):
    received_y_len = []

    from ml import evaluation
    original_choose = evaluation.choose_threshold

    def spy_choose_threshold(y_val, p_val, policy):
        received_y_len.append(len(y_val))
        return original_choose(y_val, p_val, policy)

    monkeypatch.setattr(evaluation, "choose_threshold", spy_choose_threshold)

    y_train = np.array([0, 1] * 50)
    p_train = np.array([0.2, 0.8] * 50)

    y_val = np.array([0, 1] * 20)  # len 40
    p_val = np.array([0.3, 0.7] * 20)

    y_test = np.array([0, 1] * 30)  # len 60
    p_test = np.array([0.4, 0.6] * 30)

    res = evaluation.choose_threshold(y_val, p_val, policy={"type": "min_sensitivity", "value": 0.80})

    assert len(received_y_len) == 1
    assert received_y_len[0] == 40
