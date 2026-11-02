"""
Risk Triage Modification Rules (Part D).
Applies the can-only-raise rule to check-in triage levels based on risk assessment.

Note on Clinical Deployment (D12):
Per Decision D12, both RISK_ENABLED and RISK_CAN_RAISE remain default FALSE in FYP-1
until supervising clinicians and doctors formally sign off on automated triage level adjustments.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from agents.triage_protocol import LEVEL_RANK


def apply_risk_to_level(
    level: str,
    risk: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bool]:
    """
    Applies the risk assessment to a check-in triage level.

    Safety Invariant:
    - CAN ONLY RAISE: Never returns a lower triage level.
    - Specifically, ONLY raises routine -> review when risk.band == 'high'
      AND RISK_ENABLED == 'true' AND RISK_CAN_RAISE == 'true'.
    - If current level is already 'review', 'urgent', or 'emergency', it is never altered.
    - If either feature flag is unset or false, the triage level remains strictly unchanged.

    Parameters
    ----------
    level : str
        Current triage level ('routine', 'review', 'urgent', 'emergency').
    risk : dict, optional
        Risk assessment output from risk_agent.assess().

    Returns
    -------
    tuple[str, bool]
        (resulting_level, raised_flag)
    """
    if level not in LEVEL_RANK:
        return level, False

    risk_enabled = os.environ.get("RISK_ENABLED", "").strip().lower() == "true"
    risk_can_raise = os.environ.get("RISK_CAN_RAISE", "").strip().lower() == "true"

    if not (risk_enabled and risk_can_raise):
        return level, False

    if not isinstance(risk, dict):
        return level, False

    if risk.get("status") != "ok" or risk.get("band") != "high":
        return level, False

    # The only permitted escalation: routine -> review
    if level == "routine":
        target = "review"
        if LEVEL_RANK[target] > LEVEL_RANK[level]:
            return target, True

    return level, False


def is_risk_applicable(conditions: Optional[Any]) -> bool:
    """
    Checks if diabetes risk assessment applies:
    Patient must have hypertension and NOT have diabetes.
    """
    if not conditions:
        return False
    conds_lower = [str(c).strip().lower() for c in conditions]
    has_htn = any("hyper" in c for c in conds_lower)
    has_diabetes = any("diabet" in c for c in conds_lower)
    return bool(has_htn and not has_diabetes)
