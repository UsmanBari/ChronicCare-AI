"""
Pytest integration suite for Engine Equivalence (Stage 9A-4 Task A).
Asserts that v2 and v3 produce identical, clinically safe triage levels
matching established test baselines across all 7 POC scenarios.
"""

import pytest
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.engine_equivalence import run_scenario as _run_scenario, SCENARIOS


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_engine_equivalence_scenarios(scenario):
    res_v2 = _run_scenario("v2", scenario)
    res_v3 = _run_scenario("v3", scenario)

    # Assert expected level
    assert res_v2["level"] == scenario["expected"], (
        f"v2 produced {res_v2['level']}, expected {scenario['expected']} for {scenario['id']}"
    )
    assert res_v3["level"] == scenario["expected"], (
        f"v3 produced {res_v3['level']}, expected {scenario['expected']} for {scenario['id']}"
    )

    # Assert mutual equivalence
    assert res_v2["level"] == res_v3["level"], (
        f"v2 ({res_v2['level']}) != v3 ({res_v3['level']}) for {scenario['id']}"
    )
    assert res_v2["is_emergency"] == res_v3["is_emergency"], (
        f"v2 emergency ({res_v2['is_emergency']}) != v3 emergency ({res_v3['is_emergency']}) for {scenario['id']}"
    )


def test_harness_can_fail_on_wrong_expectation():
    wrong_sc = dict(SCENARIOS[0])
    wrong_sc["expected"] = "emergency"  # Intentionally wrong expected level for routine scenario
    res_v2 = _run_scenario("v2", wrong_sc)
    assert res_v2["level"] != wrong_sc["expected"], "Harness failed to detect mismatch on wrong expectation"
