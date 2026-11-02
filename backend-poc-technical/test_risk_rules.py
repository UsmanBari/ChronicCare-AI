"""
Hermetic Tests for Risk Rules (Part D & F).
Verifies that apply_risk_to_level never lowers a triage level,
and only raises routine -> review when band == 'high' and both flags are true.
"""
from __future__ import annotations

import itertools
import pytest

from agents.risk_rules import apply_risk_to_level
from agents.triage_protocol import LEVEL_RANK

LEVELS = ["routine", "review", "urgent", "emergency"]
BANDS = ["low", "moderate", "high", None]
FLAGS = [(False, False), (True, False), (False, True), (True, True)]

COMBINATIONS = [
    (lvl, bnd, en, cr)
    for lvl in LEVELS
    for bnd in BANDS
    for en, cr in FLAGS
]



@pytest.mark.parametrize("level, band, enabled, can_raise", COMBINATIONS)
def test_apply_risk_to_level_matrix(monkeypatch, level, band, enabled, can_raise):
    """
    Parametrized matrix of every level x band x flag combination.
    Invariants:
    1. Resulting level rank is NEVER less than original level rank (never lowers).
    2. ONLY raises routine -> review when band == 'high' AND both flags are True.
    3. In all other combinations, resulting level == original level and raised == False.
    """
    monkeypatch.setenv("RISK_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("RISK_CAN_RAISE", "true" if can_raise else "false")

    risk_payload = {"status": "ok", "band": band} if band is not None else None

    result_level, raised = apply_risk_to_level(level, risk_payload)

    # Invariant 1: Never lowers
    assert LEVEL_RANK[result_level] >= LEVEL_RANK[level], (
        f"Rule lowered level from {level} to {result_level} (band={band}, enabled={enabled}, can_raise={can_raise})"
    )

    # Invariant 2: Exactly one condition triggers an escalation
    should_raise = (level == "routine" and band == "high" and enabled is True and can_raise is True)

    if should_raise:
        assert result_level == "review"
        assert raised is True
    else:
        assert result_level == level
        assert raised is False


def test_invalid_level_and_corrupt_risk(monkeypatch):
    """Unknown levels and malformed risk payloads are handled safely without raising."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "true")

    # 1. Invalid level string
    res, raised = apply_risk_to_level("unrecognized_level", {"status": "ok", "band": "high"})
    assert res == "unrecognized_level"
    assert raised is False

    # 2. Corrupt risk payload (not a dict)
    res2, raised2 = apply_risk_to_level("routine", "not_a_dict")
    assert res2 == "routine"
    assert raised2 is False

    # 3. Status not ok
    res3, raised3 = apply_risk_to_level("routine", {"status": "not_enough_information", "band": "high"})
    assert res3 == "routine"
    assert raised3 is False
