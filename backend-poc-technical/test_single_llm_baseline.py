"""
Hermetic Unit Tests for Single-LLM Baseline Benchmark Comparison (RQ3, Proposal Objective 5).

Verifies:
1. Environment credential enforcement (prints NOT SET and refuses when keys missing).
2. Triage direction classification (under-triage, over-triage, exact match).
3. Invented numbers detection (hallucinated numbers in model reasons).
4. Comparative metrics computation and multi-run consistency.
5. End-to-end benchmark execution with a fake in-memory LLM.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval.single_llm_baseline import (
    check_env_credentials,
    classify_triage_direction,
    detect_invented_numbers,
    compute_metrics,
    parse_llm_json_response,
    build_baseline_prompt,
    run_benchmark as _run_benchmark,
)


def test_env_credentials_refuses_when_missing(capsys):
    """Refuses execution and prints NOT SET when GROQ_API_KEY or GROQ_MODEL is missing."""
    with patch.dict(os.environ, {}, clear=True):
        valid, key, model = check_env_credentials()
        captured = capsys.readouterr()
        assert not valid
        assert "GROQ_API_KEY: NOT SET" in captured.out
        assert "GROQ_MODEL: NOT SET" in captured.out

    with patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}, clear=True):
        valid, key, model = check_env_credentials()
        captured = capsys.readouterr()
        assert not valid
        assert "GROQ_MODEL: NOT SET" in captured.out

    with patch.dict(os.environ, {"GROQ_MODEL": "dummy_model"}, clear=True):
        valid, key, model = check_env_credentials()
        captured = capsys.readouterr()
        assert not valid
        assert "GROQ_API_KEY: NOT SET" in captured.out


def test_env_credentials_accepts_when_present(capsys):
    """Accepts execution when both variables are populated in the environment."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key", "GROQ_MODEL": "fake_model"}, clear=True):
        valid, key, model = check_env_credentials()
        assert valid
        assert key == "fake_key"
        assert model == "fake_model"


def test_classify_triage_direction():
    """Validates exact matches, under-triage (dangerous), and over-triage."""
    # Exact
    assert classify_triage_direction("routine", "routine") == "exact"
    assert classify_triage_direction("emergency", "emergency") == "exact"
    assert classify_triage_direction("review", "review") == "exact"

    # Under-triage (predicted rank < expected rank)
    assert classify_triage_direction("routine", "emergency") == "under_triage"
    assert classify_triage_direction("review", "emergency") == "under_triage"
    assert classify_triage_direction("urgent", "emergency") == "under_triage"
    assert classify_triage_direction("routine", "review") == "under_triage"
    assert classify_triage_direction("routine", "urgent") == "under_triage"

    # Over-triage (predicted rank > expected rank)
    assert classify_triage_direction("emergency", "routine") == "over_triage"
    assert classify_triage_direction("review", "routine") == "over_triage"
    assert classify_triage_direction("emergency", "review") == "over_triage"


def test_detect_invented_numbers():
    """Identifies fabricated numbers in LLM reasons that never existed in patient answers."""
    # No hallucination
    answers = ["140 mg/dL", "130/85", "feeling fine"]
    reason = "Patient glucose is 140 mg/dL and BP is 130/85, within stable range."
    assert detect_invented_numbers(answers, reason) == []

    # Severe hallucination (the HOTFIX 2 failure mode: patient skipped reading, model invents 35)
    answers_skip = ["feeling very bad", "skip", "skip"]
    reason_hallucinated = "Patient has severe hypoglycemia with glucose of 35 mg/dL."
    assert detect_invented_numbers(answers_skip, reason_hallucinated) == ["35"]

    # Formatting noise (1, 2) ignored
    answers_clean = ["no symptoms"]
    reason_clean = "Follow up in 1-2 weeks."
    assert detect_invented_numbers(answers_clean, reason_clean) == []


def test_parse_llm_json_response():
    """Robustly extracts triage level and reason from various model formats."""
    # Standard JSON
    raw1 = '{"triage_level": "routine", "reason": "Patient is stable."}'
    lvl1, r1 = parse_llm_json_response(raw1)
    assert lvl1 == "routine"
    assert r1 == "Patient is stable."

    # Markdown fenced JSON
    raw2 = '```json\n{"triage_level": "emergency", "reason": "Severe chest pain reported."}\n```'
    lvl2, r2 = parse_llm_json_response(raw2)
    assert lvl2 == "emergency"
    assert r2 == "Severe chest pain reported."

    # Malformed text with regex fallback
    raw3 = 'Based on the answers, "triage_level": "urgent", "reason": "High blood pressure 185/115."'
    lvl3, r3 = parse_llm_json_response(raw3)
    assert lvl3 == "urgent"


def test_build_baseline_prompt():
    """Ensures prompt contains profile and answers, with ZERO guideline text."""
    prompt = build_baseline_prompt(
        conditions=["diabetes"],
        answers=["feeling okay", "120 mg/dL", "no symptoms"],
    )
    assert len(prompt) == 2
    user_content = prompt[1]["content"]
    assert "Conditions: diabetes" in user_content
    assert "120 mg/dL" in user_content
    # Zero guideline text invariant (licence preservation)
    assert "ADA" not in user_content
    assert "AHA" not in user_content
    assert "ACC" not in user_content


def test_compute_metrics():
    """Verifies math for accuracy, under-triage, emergency recall, and consistency."""
    mock_results = [
        {
            "id": "sc1",
            "expected_level": "routine",
            "pipeline_level": "routine",
            "baseline_runs": [
                {"level": "routine", "reason": "normal", "invented_numbers": []},
                {"level": "routine", "reason": "normal", "invented_numbers": []},
                {"level": "routine", "reason": "normal", "invented_numbers": []},
            ],
        },
        {
            "id": "sc2",
            "expected_level": "emergency",
            "pipeline_level": "emergency",
            "baseline_runs": [
                {"level": "emergency", "reason": "chest pain", "invented_numbers": []},
                {"level": "review", "reason": "under-triage run", "invented_numbers": ["45"]},
                {"level": "emergency", "reason": "chest pain", "invented_numbers": []},
            ],
        },
    ]

    metrics = compute_metrics(mock_results, runs_per_scenario=3)
    p = metrics["pipeline"]
    b = metrics["baseline"]

    # Pipeline
    assert p["accuracy"] == 1.0
    assert p["under_triage_count"] == 0
    assert p["emergency_recall"] == 1.0
    assert p["consistency"] == 1.0

    # Baseline
    assert b["total_evaluations"] == 6
    # Exact matches: sc1 has 3, sc2 has 2 -> 5/6 = 0.8333
    assert b["exact_matches"] == 5
    assert b["under_triage_count"] == 1  # 1 under-triage on sc2
    assert b["under_triage_rate"] == round(1 / 6, 4)
    # Emergency expected count: 1 scenario * 3 runs = 3. Recalled: 2. -> 2/3 = 0.6667
    assert b["emergency_recall"] == round(2 / 3, 4)
    # Invented numbers: 1
    assert b["invented_numbers_count"] == 1
    # Consistency: sc1 is consistent (3/3 routine); sc2 is inconsistent (2 emergency, 1 review) -> 1/2 = 0.5
    assert b["consistency"] == 0.5


def test_hermetic_benchmark_with_mock_llm(tmp_path):
    """Executes benchmark end-to-end with an in-memory mock LLM."""
    def fake_llm(prompt):
        return "routine", "All stable, no issues."

    with patch.dict(os.environ, {"CHRONICCARE_DATA_DIR": str(tmp_path)}):
        res = _run_benchmark(limit=3, runs_per_scenario=2, mock_llm_fn=fake_llm)

    assert "metrics" in res
    assert "pipeline" in res["metrics"]
    assert "baseline" in res["metrics"]
    assert res["n_scenarios"] == 3
    assert res["runs_per_scenario"] == 2
    assert res["total_llm_calls"] == 6
