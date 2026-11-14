"""
Hermetic Unit Tests for Single-LLM Baseline Benchmark Comparison (RQ3, Proposal Objective 5).

Verifies:
1. Environment credential enforcement (prints NOT SET and refuses when keys missing).
2. Triage direction classification (under-triage, over-triage, exact match).
3. Invented numbers detection (hallucinated numbers in model reasons).
4. Comparative metrics computation and multi-run consistency.
5. End-to-end benchmark execution with a fake in-memory LLM.
6. F6: A failed /complete is counted 'incomplete' (never routine).
7. F6: A 403 pregnancy exit is counted 'excluded'.
8. F6: summary_confirmation gets the multilingual yes answer.
9. F6: Comparative table metrics display under-triage first with split counts.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    run_pipeline_persona as _run_pipeline_persona,
    format_markdown_table,
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

    # Special statuses
    assert classify_triage_direction("excluded", "routine") == "excluded"
    assert classify_triage_direction("incomplete", "urgent") == "incomplete"


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
    """Ensures prompt contains profile and paired dialogue transcript with ZERO guideline text."""
    transcript = [
        {"turn": 1, "step": "greeting", "question": "How are you feeling?", "answer": "feeling fine"},
        {"turn": 2, "step": "glucose_reading", "question": "Have you measured glucose?", "answer": "120 mg/dL"},
    ]
    prompt = build_baseline_prompt(
        conditions=["diabetes"],
        transcript=transcript,
    )
    assert len(prompt) == 2
    user_content = prompt[1]["content"]
    assert "Conditions: diabetes" in user_content
    assert "120 mg/dL" in user_content
    assert "How are you feeling?" in user_content
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
        {
            "id": "sc3_excluded",
            "expected_level": "review",
            "pipeline_level": "excluded",
            "baseline_runs": [],
        },
    ]

    metrics = compute_metrics(mock_results, runs_per_scenario=3)
    p = metrics["pipeline"]
    b = metrics["baseline"]

    assert metrics["total_scenarios"] == 3
    assert metrics["evaluable_scenarios"] == 2
    assert metrics["excluded_count"] == 1
    assert metrics["incomplete_count"] == 0

    # Pipeline
    assert p["accuracy"] == 1.0
    assert p["under_triage_count"] == 0
    assert p["emergency_recall"] == 1.0
    assert p["consistency"] == 1.0

    # Baseline
    assert b["evaluable_evaluations"] == 6
    assert b["exact_matches"] == 5
    assert b["under_triage_count"] == 1
    assert b["under_triage_rate"] == round(1 / 6, 4)
    assert b["emergency_recall"] == round(2 / 3, 4)
    assert b["invented_numbers_count"] == 1
    assert b["consistency"] == 0.5


def test_f6_failed_complete_counted_as_incomplete():
    """F6: Verify a non-200 /complete or missing level is counted 'incomplete', never routine."""
    import scripts.run_v3_personas as runner

    mock_start_resp = MagicMock()
    mock_start_resp.status_code = 200
    mock_start_resp.json.return_value = {"checkin_id": "mock_chk_1", "question": None, "step": None}

    mock_comp_resp = MagicMock()
    mock_comp_resp.status_code = 409  # Conflict / incomplete
    mock_comp_resp.json.return_value = {"error": "Interview not finished"}

    with patch.object(runner.client, "post", side_effect=[mock_start_resp, mock_comp_resp]):
        with patch.object(runner, "bootstrap_patient", return_value={"Authorization": "Bearer fake"}):
            res = _run_pipeline_persona({"id": "mock_p", "conditions": ["hypertension"], "language": "en"})

    assert res["status"] == "incomplete"
    assert res["level"] == "incomplete"
    assert res["level"] != "routine"


def test_f6_pregnancy_exit_counted_as_excluded():
    """F6: Verify a 403 pregnancy response is counted 'excluded', never scored as routine."""
    import scripts.run_v3_personas as runner

    mock_start_resp = MagicMock()
    mock_start_resp.status_code = 200
    mock_start_resp.json.return_value = {
        "checkin_id": "mock_chk_p",
        "question": "Are you pregnant?",
        "step": "pregnancy_screening",
    }

    mock_ans_resp = MagicMock()
    mock_ans_resp.status_code = 403
    mock_ans_resp.text = "Patient is pregnant; check-in discontinued"

    with patch.object(runner.client, "post", side_effect=[mock_start_resp, mock_ans_resp]):
        with patch.object(runner, "bootstrap_patient", return_value={"Authorization": "Bearer fake"}):
            with patch.object(runner, "build_persona_facts", return_value={}):
                with patch.object(runner, "pick_answer", return_value=("yes", False)):
                    res = _run_pipeline_persona({"id": "p31_reports_pregnant_exit", "conditions": ["diabetes"], "language": "en"})

    assert res["status"] == "excluded"
    assert res["level"] == "excluded"
    assert res["level"] != "routine"


def test_f6_summary_confirmation_gets_yes_answer():
    """F6: Verify summary_confirmation step receives multilingual 'yes' answer."""
    import scripts.run_v3_personas as runner

    for lang, expected_yes in [("en", "yes"), ("roman_ur", "haan"), ("ur", "ہاں")]:
        mock_start_resp = MagicMock()
        mock_start_resp.status_code = 200
        mock_start_resp.json.return_value = {
            "checkin_id": f"mock_chk_{lang}",
            "question": "Please confirm summary",
            "step": "summary_confirmation",
        }

        mock_ans_resp = MagicMock()
        mock_ans_resp.status_code = 200
        mock_ans_resp.json.return_value = {"complete": True}

        mock_comp_resp = MagicMock()
        mock_comp_resp.status_code = 200
        mock_comp_resp.json.return_value = {"triage": {"level": "routine"}}

        recorded_answers = []

        def capture_post(url, *args, **kwargs):
            if "answer" in url:
                recorded_answers.append(kwargs.get("json", {}).get("answer"))
                return mock_ans_resp
            elif "complete" in url:
                return mock_comp_resp
            return mock_start_resp

        with patch.object(runner.client, "post", side_effect=capture_post):
            with patch.object(runner, "bootstrap_patient", return_value={"Authorization": "Bearer fake"}):
                res = _run_pipeline_persona({"id": f"p_{lang}", "conditions": ["hypertension"], "language": lang})

        assert res["status"] == "completed"
        assert len(recorded_answers) == 1
        assert recorded_answers[0] == expected_yes


def test_f6_comparison_sentence_under_triage_split():
    """F4/F6: Verify table displays under-triage split by expected level without misleading spin."""
    mock_metrics = {
        "total_scenarios": 10,
        "evaluable_scenarios": 9,
        "incomplete_count": 0,
        "excluded_count": 1,
        "pipeline": {
            "accuracy": 0.8889,
            "exact_matches": 8,
            "under_triage_count": 1,
            "under_triage_rate": 0.1111,
            "under_triage_split": {
                "expected_emergency_missed": 0,
                "expected_emergency_total": 2,
                "expected_urgent_missed": 0,
                "expected_urgent_total": 3,
                "expected_review_missed": 1,
                "expected_review_total": 4,
            },
            "over_triage_count": 0,
            "over_triage_rate": 0.0,
            "emergency_expected_count": 2,
            "emergency_recalled_count": 2,
            "emergency_recall": 1.0,
        },
        "baseline": {
            "accuracy": 0.7778,
            "exact_matches": 7,
            "under_triage_count": 2,
            "under_triage_rate": 0.2222,
            "under_triage_split": {
                "expected_emergency_missed": 1,
                "expected_emergency_total": 6,
                "expected_urgent_missed": 1,
                "expected_urgent_total": 9,
                "expected_review_missed": 0,
                "expected_review_total": 12,
            },
            "over_triage_count": 0,
            "over_triage_rate": 0.0,
            "emergency_expected_count": 6,
            "emergency_recalled_count": 5,
            "emergency_recall": 0.8333,
            "invented_numbers_count": 3,
            "consistency": 0.6667,
        },
    }

    table_md = format_markdown_table(mock_metrics, model_name="test_model", n_scenarios=9)
    # Check that under-triage appears first and includes split rows
    assert "Under-Triage Total (Dangerous: predicted < expected)" in table_md
    assert "Expected Emergency Missed" in table_md
    assert "Expected Urgent Missed" in table_md
    assert "Expected Review Missed" in table_md
    # Ensure spin phrase was removed
    assert "Advantage / Safety Margin" not in table_md
    assert "fewer missed escalations" not in table_md


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
