"""
Unit tests for MIMIC-IV trend sanity script using strictly synthetic fake frames.

Ensures proper window calculation, refusal of in-repo paths, aggregate calculations,
and strict privacy enforcement (zero leakage of patient IDs or row-level data).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from ml.mimic.trend_sanity import (
    evaluate_mimic_trends,
    is_path_in_repo,
    main,
)


def _create_synthetic_omr_file(file_path: Path) -> None:
    """Helper to generate synthetic OMR data for unit testing."""
    records = [
        # Patient 1: Rising systolic (120 -> 130 -> 142) over 15 days
        {"subject_id": 10001, "chartdate": "2150-05-01", "seq_num": 1, "result_name": "Blood Pressure", "result_value": "120/80"},
        {"subject_id": 10001, "chartdate": "2150-05-08", "seq_num": 2, "result_name": "Blood Pressure", "result_value": "130/82"},
        {"subject_id": 10001, "chartdate": "2150-05-15", "seq_num": 3, "result_name": "Blood Pressure", "result_value": "142/85"},

        # Patient 2: Only 2 readings (not evaluable, requires >= 3)
        {"subject_id": 10002, "chartdate": "2150-06-01", "seq_num": 1, "result_name": "Blood Pressure", "result_value": "130/80"},
        {"subject_id": 10002, "chartdate": "2150-06-10", "seq_num": 2, "result_name": "Blood Pressure", "result_value": "132/82"},

        # Patient 3: Non-BP rows and unparseable/implausible rows
        {"subject_id": 10003, "chartdate": "2150-07-01", "seq_num": 1, "result_name": "Weight (Lbs)", "result_value": "175"},
        {"subject_id": 10003, "chartdate": "2150-07-02", "seq_num": 2, "result_name": "Blood Pressure", "result_value": "unparseable"},
        {"subject_id": 10003, "chartdate": "2150-07-03", "seq_num": 3, "result_name": "Blood Pressure", "result_value": "300/40"}, # SBP out of plausibility
        {"subject_id": 10003, "chartdate": "2150-07-04", "seq_num": 4, "result_name": "Blood Pressure", "result_value": "70/120"},  # SBP < DBP inverted

        # Patient 4: Falling diastolic (95 -> 88 -> 78) over 20 days
        {"subject_id": 10004, "chartdate": "2150-08-01", "seq_num": 1, "result_name": "Blood Pressure", "result_value": "125/95"},
        {"subject_id": 10004, "chartdate": "2150-08-10", "seq_num": 2, "result_name": "Blood Pressure", "result_value": "122/88"},
        {"subject_id": 10004, "chartdate": "2150-08-20", "seq_num": 3, "result_name": "Blood Pressure", "result_value": "120/78"},
    ]
    df = pd.DataFrame(records)
    df.to_csv(file_path, index=False)


def test_is_path_in_repo():
    repo_root = Path(__file__).resolve().parents[2]
    inside_file = repo_root / "fake_omr.csv"
    outside_file = Path("C:/arbitrary_external_dir/omr.csv")

    assert is_path_in_repo(inside_file) is True
    assert is_path_in_repo(outside_file) is False


def test_refuse_in_repo_file(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    in_repo_fake = repo_root / "test_scratch_in_repo_omr.csv"
    try:
        in_repo_fake.write_text("dummy")
        with pytest.raises(ValueError, match="Refusing to read OMR file located inside repository"):
            evaluate_mimic_trends(in_repo_fake)
    finally:
        if in_repo_fake.exists():
            in_repo_fake.unlink()


def test_file_not_found(tmp_path: Path):
    non_existent = tmp_path / "non_existent_omr.csv"
    with pytest.raises(FileNotFoundError):
        evaluate_mimic_trends(non_existent)


def test_synthetic_data_processing_and_privacy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Ensure tmp_path is treated as outside repo for this test if tmp_path happens to be in repo
    synth_file = tmp_path / "synthetic_omr.csv"
    _create_synthetic_omr_file(synth_file)

    # Mock is_path_in_repo to return False for synth_file
    monkeypatch.setattr("ml.mimic.trend_sanity.is_path_in_repo", lambda p: False)

    report = evaluate_mimic_trends(synth_file)

    # 1. Verification of Aggregates
    assert "subjects_with_evaluable_windows" in report
    assert "windows_evaluated" in report
    assert "systolic" in report
    assert "diastolic" in report
    assert "parse_failures" in report

    # Patient 1 and Patient 4 are evaluable (Patient 2 has only 2 readings, Patient 3 has invalid BP)
    assert report["subjects_with_evaluable_windows"] == 2
    assert report["windows_evaluated"] >= 2
    assert report["parse_failures"] >= 3  # "unparseable", "300/40", "70/120"

    # 2. Strict Privacy Verification: Zero row-level disclosure
    dumped = json.dumps(report)
    for forbidden in ["10001", "10002", "10003", "10004", "2150-05-01", "subject_id", "chartdate"]:
        assert forbidden not in dumped, f"Privacy violation: '{forbidden}' leaked in output JSON!"


def test_cli_execution_zero_leakage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    synth_file = tmp_path / "synthetic_omr.csv"
    _create_synthetic_omr_file(synth_file)

    monkeypatch.setattr("ml.mimic.trend_sanity.is_path_in_repo", lambda p: False)
    monkeypatch.setattr(sys, "argv", ["trend_sanity.py", "--omr", str(synth_file)])

    main()

    captured = capsys.readouterr()
    assert captured.err == ""
    output_json = json.loads(captured.out)
    assert "subjects_with_evaluable_windows" in output_json
    assert "10001" not in captured.out
    assert "2150-05" not in captured.out
