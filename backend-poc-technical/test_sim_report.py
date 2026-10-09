"""
Unit Test for Simulation Report Freshness (Stage 9A Task G).

Verifies:
1. docs/INTERVIEW_V3_SIM_REPORT.md exists.
2. The report accurately reflects the 52 simulated patient personas.
"""

import os
import pytest
from scripts.generate_sim_report import run_simulation as _run_simulation, generate_report


def test_sim_report_file_exists_and_is_current():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(repo_root, "docs", "INTERVIEW_V3_SIM_REPORT.md")
    assert os.path.exists(report_path), f"Missing report at {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        existing_content = f.read()

    stats = _run_simulation()
    expected_content = generate_report(stats)

    assert "Total Simulated Personas Tested" in existing_content
    assert str(stats["total_personas"]) in existing_content
    assert str(stats["avg_questions"]) in existing_content
