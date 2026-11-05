"""
Hermetic Unit Test Suite for Evaluation Numbers Master Harness (Day 4 - Rework).

Verifies that scripts/collect_eval_numbers.py:
1. Runs completely offline without network, database, or external data dependencies.
2. Formats all 9 required sections conforming strictly to FYP-1 evidence standards.
3. Contains NO hardcoded numeric results dictionaries (parses from artifacts/commands).
4. Accurately quotes docs/V3_READINESS.md (NO-GO recommendation, 4 misses, 8 both, 1 demotion).
5. Lists held-out evaluation sets first in the danger phrase benchmark.
6. Emits only repo-relative paths (zero absolute drive paths).
7. Validates that load benchmark is marked as PENDING #115 re-run and mutations as Day 6 checker fix.
8. Confirms no 'explanation_jobs' table claim exists in schema reconciliation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.collect_eval_numbers import (
    collect_section_1_tests,
    collect_section_2_safety,
    collect_section_3_danger_phrases,
    collect_section_4_orchestrator,
    collect_section_5_ml,
    collect_section_6_rag,
    collect_section_7_load,
    collect_section_8_coverage,
    collect_section_9_stale_reconciliation,
    generate_markdown,
    to_repo_rel,
)


def test_no_hardcoded_result_numbers():
    """Validates that scripts/collect_eval_numbers.py contains zero hard-coded results dictionaries."""
    script_path = REPO_ROOT / "scripts/collect_eval_numbers.py"
    text = script_path.read_text(encoding="utf-8")

    # Prohibited patterns where numbers were formerly typed in directly
    prohibited_patterns = [
        r'"backend_direct_passed":\s*\d+',
        r'"backend_graph_passed":\s*\d+',
        r'"vitest_passed":\s*\d+',
        r'"v2_demotions":\s*0',
        r'"v3_demotions":\s*0',
        r'"gold_set_emergency_recall":\s*100',
        r'"clean_n_train":\s*\d+',
        r'"metrics_en":\s*\{"hit_1":\s*[\d.]+',
        r'"worst_server_rss_peak_mb":\s*[\d.]+',
        r'"overall_backend_coverage_pct":\s*\d+',
    ]

    for pattern in prohibited_patterns:
        match = re.search(pattern, text)
        assert match is None, f"Found hard-coded result literal matching '{pattern}' in collect_eval_numbers.py: {match.group(0)}"


def test_section_1_test_counts_dynamic():
    """Section 1 must dynamically report CI targets and pending mutation status."""
    res = collect_section_1_tests()
    assert res["backend_ci_targets_count"] >= 80
    assert "PENDING: Usman's Day 6 checker fix" in res["mutation_proofs_status"]
    assert "ci.yml" in res["backend_direct_citation"]


def test_section_2_quotes_v3_readiness():
    """Section 2 must quote docs/V3_READINESS.md and report 4 misses, 8 both, and 1 demotion."""
    res = collect_section_2_safety()
    assert res["recommendation"] == "NO-GO"
    assert "4 V3 misses" in res["executive_quote"]
    assert "8 both misses" in res["executive_quote"]
    assert "1 demotions" in res["executive_quote"]
    assert res["total_personas"] == 64
    assert res["v3_misses"] == 4
    assert res["both_miss"] == 8
    assert res["demotions"] == 1


def test_section_3_held_out_sets_lead():
    """Section 3 must lead with held-out evaluation sets before tuning sets."""
    rows = collect_section_3_danger_phrases()
    assert len(rows) >= 5

    # Find first tuning set index
    first_tuning_idx = next(i for i, r in enumerate(rows) if not r["is_held_out"])
    # Find last held-out set index
    last_held_out_idx = max(i for i, r in enumerate(rows) if r["is_held_out"])

    assert last_held_out_idx < first_tuning_idx, "All held-out evaluation sets must appear before tuning sets"


def test_section_4_orchestrator_equivalence():
    """Section 4 must report total cases and 100% equivalence rate."""
    res = collect_section_4_orchestrator()
    assert res["total_cases_evaluated"] >= 78
    assert res["identical_cases"] == res["total_cases_evaluated"]
    assert res["equivalence_pct"] == 100.0


def test_section_5_ml_metrics():
    """Section 5 must parse AUROC and external validation from committed markdown docs."""
    res = collect_section_5_ml()
    pm = res["primary_model"]
    assert pm["model_name"] == "diabetes_full_nhanes"
    assert "0.7527" in pm["test_auroc_ci"]
    assert len(res["external_validation"]) >= 3


def test_section_6_rag_ada_notice():
    """Section 6 must include the 5 Nov ADA permission corpus notice."""
    res = collect_section_6_rag()
    assert "ADA permission for 6 sections arrived 5 Nov" in res["retrieval"]["ada_permission_notice"]
    assert res["explainer"]["test_cases_count"] == 40
    assert res["explainer"]["acceptance_rate_pct"] == 100.0


def test_section_7_load_pending():
    """Section 7 must be marked as PENDING: #115 re-run."""
    res = collect_section_7_load()
    assert "PENDING: #115 re-run" in res["status"]


def test_section_8_coverage_labeled_stale():
    """Section 8 must be labeled as 1 Nov, 1,440 tests (stale)."""
    res = collect_section_8_coverage()
    assert "1 Nov, 1,440 tests (stale)" in res["label"]


def test_section_9_no_explanation_jobs_table():
    """Section 9 must not claim that an 'explanation_jobs' table exists in SQLite schema."""
    rows = collect_section_9_stale_reconciliation()
    schema_row = next(r for r in rows if "Schema" in r["metric_name"])
    assert "explanation_jobs" not in schema_row["today_value"]
    assert "checkin_results.explanation_json" in schema_row["today_value"]


def test_no_absolute_paths_in_markdown():
    """Generated markdown must contain zero absolute drive paths."""
    s1 = collect_section_1_tests()
    s2 = collect_section_2_safety()
    s3 = collect_section_3_danger_phrases()
    s4 = collect_section_4_orchestrator()
    s5 = collect_section_5_ml()
    s6 = collect_section_6_rag()
    s7 = collect_section_7_load()
    s8 = collect_section_8_coverage()
    s9 = collect_section_9_stale_reconciliation()

    md = generate_markdown(s1, s2, s3, s4, s5, s6, s7, s8, s9)
    assert "C:\\" not in md, "Found Windows absolute path in generated markdown"
    assert "/Users/" not in md, "Found Unix absolute path in generated markdown"
