"""
Hermetic ML unit tests for Clinical Guideline Explainer evaluation harness (Day 2).

Tests explainer evaluation logic with scripted fake LLMs:
- Good answer passes validators and is accepted (mode="llm").
- Banned pattern answer (dose number) fails V4 and falls back to template.
- Timed-out answer trips budget and falls back with reason="budget_timeout".
- Token tracking counts tokens in/out and halts at cap.
- Urdu Arabic-script share and English leak detection.
- Metrics aggregation, percentiles, and bootstrap CIs.

Runs completely offline without network calls or external data directories.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from rag.store import ChunkStore

from scripts.eval_explainer import (
    TokenTrackingLLM,
    check_arabic_script_share,
    compute_summary_metrics,
    evaluate_single_case,
)


class FakeMiniChunkStore(ChunkStore):
    """Hermetic in-memory chunk store with 2 valid chunks."""

    def __init__(self) -> None:
        self.chunks = {
            "chunk_001": {
                "chunk_id": "chunk_001",
                "source_id": "who_2021_htn",
                "condition": "hypertension",
                "priority": 1,
                "text": "For non-pregnant adults with hypertension, initial treatment includes lifestyle intervention and antihypertensive medication.",
                "section_path": "Treatment/Thresholds",
                "section_title": "BP Targets",
            },
            "chunk_002": {
                "chunk_id": "chunk_002",
                "source_id": "ish_2020_htn",
                "condition": "hypertension",
                "priority": 1,
                "text": "Adults diagnosed with hypertension should maintain blood pressure below 140/90 mmHg through combination therapy.",
                "section_path": "Management/Goals",
                "section_title": "Target Blood Pressure",
            },
        }

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self.chunks.get(chunk_id)

    def list_chunks(
        self,
        condition: str | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        res = list(self.chunks.values())
        if condition:
            res = [c for c in res if c["condition"] == condition]
        if source_id:
            res = [c for c in res if c["source_id"] == source_id]
        return res[:limit]

    def total_chunks(self) -> int:
        return len(self.chunks)

    def all_chunks(self) -> list[dict[str, Any]]:
        return list(self.chunks.values())


@pytest.fixture
def mini_store() -> FakeMiniChunkStore:
    return FakeMiniChunkStore()


@pytest.fixture
def sample_case() -> dict[str, Any]:
    return {
        "case_id": "TEST_CASE_01",
        "persona_id": "p01_test",
        "condition": "hypertension",
        "language": "en",
        "triage_level": "routine",
        "readings": {"blood_pressure_systolic": 135, "blood_pressure_diastolic": 88},
        "triage_result": {
            "level": "routine",
            "reasons": ["Blood pressure is in routine range"],
            "guidance": "Continue regular habits",
            "trigger_category": "routine",
        },
    }


def test_fake_llm_good_answer_accepted(sample_case: dict[str, Any], mini_store: FakeMiniChunkStore) -> None:
    """Verifies that a valid grounded LLM response passes all validators and mode is 'llm'."""
    def fake_good_llm(messages: Any, **kwargs: Any) -> tuple[str, int]:
        valid_json = json.dumps({
            "sentences": [
                {
                    "text": "Your blood pressure of 135/88 is within the target range for routine monitoring.",
                    "cites": ["chunk_001"],
                },
                {
                    "text": "Maintaining a healthy lifestyle helps prevent blood pressure elevation over time.",
                    "cites": ["chunk_002"],
                },
            ]
        })
        return valid_json, 165

    res = evaluate_single_case(sample_case, store=mini_store, llm=fake_good_llm, budget_seconds=5.0)
    assert res["mode"] == "llm"
    assert res["reason"] == "unknown" or res["reason"] == "llm" or not res["rejected_reasons"]
    assert len(res["cites"]) >= 1


def test_fake_llm_banned_dose_rejected_to_template(sample_case: dict[str, Any], mini_store: FakeMiniChunkStore) -> None:
    """Verifies that an ungrounded medication dose response is caught by V4 and falls back to template."""
    def fake_bad_dose_llm(messages: Any, **kwargs: Any) -> tuple[str, int]:
        bad_json = json.dumps({
            "sentences": [
                {
                    "text": "Your blood pressure of 135/88 is elevated so please increase your dose of amlodipine 10 mg immediately.",
                    "cites": ["chunk_001"],
                },
                {
                    "text": "Make sure to monitor your blood pressure closely every morning.",
                    "cites": ["chunk_002"],
                },
            ]
        })
        return bad_json, 150

    res = evaluate_single_case(sample_case, store=mini_store, llm=fake_bad_dose_llm, budget_seconds=5.0)
    assert res["mode"] == "template"
    assert res["reason"] == "validation_failed"
    assert any("V4" in r or "banned" in r.lower() or "500mg" in r.lower() or "take" in r.lower() for r in res["rejected_reasons"])


def test_fake_llm_timeout_triggers_budget_fallback(sample_case: dict[str, Any], mini_store: FakeMiniChunkStore) -> None:
    """Verifies that an LLM call exceeding the time budget falls back with 'budget_timeout'."""
    def fake_slow_llm(messages: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        time.sleep(0.4)
        return json.dumps({"sentences": []}), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}

    res = evaluate_single_case(sample_case, store=mini_store, llm=fake_slow_llm, budget_seconds=0.05)
    assert res["mode"] == "template"
    assert res["reason"] == "budget_timeout"
    assert any("budget" in r.lower() or "timeout" in r.lower() for r in res["rejected_reasons"])


def test_token_tracking_counts_and_stops_at_cap() -> None:
    """Verifies that TokenTrackingLLM accurately counts tokens and halts when reaching token cap."""
    def fake_api(messages: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        return "{}", {"prompt_tokens": 500, "completion_tokens": 500, "total_tokens": 1000}

    # Set cap at 2,500 tokens
    tracker = TokenTrackingLLM(real_client_fn=fake_api, token_cap=2500)
    assert tracker.cumulative_total_tokens == 0

    # Call 1: 1000 tokens
    tracker("msg1")
    assert tracker.cumulative_total_tokens == 1000
    assert not tracker.cap_reached

    # Call 2: 1000 tokens -> 2000 total
    tracker("msg2")
    assert tracker.cumulative_total_tokens == 2000
    assert not tracker.cap_reached

    # Call 3: 1000 tokens -> 3000 total >= 2500 cap
    tracker("msg3")
    assert tracker.cumulative_total_tokens == 3000
    assert tracker.cap_reached

    # Call 4: should raise error because cap is reached
    with pytest.raises(RuntimeError, match="Token cap reached"):
        tracker("msg4")


def test_arabic_script_share_and_leak_detection() -> None:
    """Verifies character ratio computation for Urdu text and English leak detection."""
    # 1. Pure Urdu sentence
    urdu_text = "آپ کا بلڈ پریشر معمول کے مطابق ہے اور ادویات باقاعدگی سے لیں۔"
    ratio, ar_cnt, lat_cnt = check_arabic_script_share(urdu_text)
    assert ratio > 0.90
    assert ar_cnt > 20
    assert lat_cnt == 0

    # 2. English leak sentence
    leak_text = "Your blood pressure is normal, please continue taking your medications."
    leak_ratio, _ar_cnt_leak, lat_cnt_leak = check_arabic_script_share(leak_text)
    assert leak_ratio == 0.0
    assert lat_cnt_leak > 30

    # 3. Empty text edge case
    empty_ratio, _, _ = check_arabic_script_share("")
    assert empty_ratio == 0.0


def test_compute_summary_metrics() -> None:
    """Verifies summary metric aggregation, percentiles, and confidence intervals."""
    cases = [
        {"case_id": "C1", "language": "en", "triage_level": "routine"},
        {"case_id": "C2", "language": "ur", "triage_level": "review"},
    ]
    llm_results = [
        {"case_id": "C1", "language": "en", "triage_level": "routine", "mode": "llm", "reason": "unknown", "rejected_reasons": [], "latency_ms": 500.0, "explanation_text": "Normal text"},
        {"case_id": "C2", "language": "ur", "triage_level": "review", "mode": "template", "reason": "validation_failed", "rejected_reasons": ["V1: length"], "latency_ms": 200.0, "explanation_text": "آپ کا بلڈ پریشر"},
    ]
    template_results = [
        {"case_id": "C1", "language": "en", "triage_level": "routine", "mode": "template", "reason": "baseline", "rejected_reasons": [], "latency_ms": 1.0, "explanation_text": "Tmpl 1"},
        {"case_id": "C2", "language": "ur", "triage_level": "review", "mode": "template", "reason": "baseline", "rejected_reasons": [], "latency_ms": 1.5, "explanation_text": "Tmpl 2"},
    ]

    summary = compute_summary_metrics(
        cases=cases,
        llm_results=llm_results,
        template_results=template_results,
        tracking_llm=None,
        model_name="test-model",
    )

    assert summary["n_cases"] == 2
    assert summary["has_llm_run"] is True
    assert summary["acceptance"][0] == 0.5
    assert summary["fallback_rate"] == 0.5
    assert summary["validator_rejections"]["V1"] == 1
    assert summary["latency_llm"]["p50_ms"] == 350.0
