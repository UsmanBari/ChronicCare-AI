"""
Unit tests for NHANES temporal data splits.
Uses synthetic DataFrames (no real survey data).
"""
import pytest
import pandas as pd
from ml.splits import (
    generate_nhanes_temporal_splits,
    compute_split_summary,
    TRAIN_CORE_CYCLES,
    VALIDATION_CYCLES,
    TEST_CYCLES,
)


def test_splits_disjoint_and_union():
    rows = []
    seqn = 1000
    for cycle in TRAIN_CORE_CYCLES:
        rows.append({"seqn": seqn, "cycle": cycle, "age": 45, "told_diabetes": 0, "hba1c": 5.4, "fasting_glucose": 95, "sbp": 120, "dbp": 80})
        seqn += 1
    for cycle in VALIDATION_CYCLES:
        rows.append({"seqn": seqn, "cycle": cycle, "age": 50, "told_diabetes": 1, "hba1c": 7.0, "fasting_glucose": 130, "sbp": 135, "dbp": 85})
        seqn += 1
    for cycle in TEST_CYCLES:
        rows.append({"seqn": seqn, "cycle": cycle, "age": 60, "told_diabetes": 0, "hba1c": 5.8, "fasting_glucose": 105, "sbp": 125, "dbp": 78})
        seqn += 1
    # Minor (< 18)
    rows.append({"seqn": seqn, "cycle": "2017-2018", "age": 12, "told_diabetes": 0, "hba1c": 5.0, "fasting_glucose": 90, "sbp": 110, "dbp": 70})

    df = pd.DataFrame(rows)

    splits = generate_nhanes_temporal_splits(df)

    train_set = set(splits["train_core"])
    val_set = set(splits["validation"])
    test_set = set(splits["test"])

    # Disjointness
    assert train_set.isdisjoint(val_set)
    assert train_set.isdisjoint(test_set)
    assert val_set.isdisjoint(test_set)

    # Union equals all adults
    adult_seqns = set(df[df["age"] >= 18]["seqn"].astype(int))
    assert (train_set | val_set | test_set) == adult_seqns

    # Child excluded
    assert seqn not in (train_set | val_set | test_set)

    # Counts match cycles
    assert len(splits["train_core"]) == len(TRAIN_CORE_CYCLES)
    assert len(splits["validation"]) == len(VALIDATION_CYCLES)
    assert len(splits["test"]) == len(TEST_CYCLES)


def test_split_summary_calculation():
    df = pd.DataFrame([
        {"seqn": 1, "cycle": "1999-2000", "age": 30, "told_diabetes": 0, "hba1c": 5.2, "fasting_glucose": 90, "sbp": 120, "dbp": 70},
        {"seqn": 2, "cycle": "2013-2014", "age": 40, "told_diabetes": 1, "hba1c": 6.8, "fasting_glucose": 140, "sbp": 135, "dbp": 82},
        {"seqn": 3, "cycle": "2017-2018", "age": 50, "told_diabetes": 0, "hba1c": 6.6, "fasting_glucose": 110, "sbp": 145, "dbp": 95},
    ])
    splits = {
        "train_core": [1],
        "validation": [2],
        "test": [3],
    }
    summary = compute_split_summary(df, splits)
    assert len(summary) == 3
    assert "train_core" in summary["Split"].values
    assert "validation" in summary["Split"].values
    assert "test" in summary["Split"].values
