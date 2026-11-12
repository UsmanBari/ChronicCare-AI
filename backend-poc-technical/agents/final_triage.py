"""
backend-poc-technical/agents/final_triage.py — Stage-2 Final Triage & Escalation Agent

Combines deterministic clinical protocol rules, risk predictive models, and
longitudinal physiological trends to produce the authoritative final triage level,
color chip mapping, escalation tracking, and patient/provider reasoning.

Adheres strictly to the core safety motto:
"The model proposes, the rules decide."

=============================================================================
STAGE-2 FINAL TRIAGE RULES TABLE (Proposal Sections 13.1 Agent 10, 15, 17)
=============================================================================
Rule ID | Condition                                          | Result Level | Result Color | Raised? | Authority
--------|----------------------------------------------------|--------------|--------------|---------|-------------------------
R-S2-0  | rules_level in ('emergency', 'urgent', 'review')   | rules_level  | mapped color | False   | Invariant: Never lower
R-S2-1  | rules_level == 'routine' AND risk model 'high'     | review       | yellow       | True    | Clinician Approved 8 Nov
        | AND RISK_CAN_RAISE=true                            |              |              |         | (Subject to cooldown)
R-S2-2  | rules_level == 'routine' AND trend rising with     | review       | yellow       | True    | Clinician Approved 8 Nov
        | >= 5 points (TREND_MIN_POINTS) AND latest value    |              |              |         | (5 check-in min)
        | above target range AND TREND_CAN_RAISE=true        |              |              |         |
R-S2-3  | Any raise                                          | review at    | yellow at    | True    | Invariant: At most 1 step
        |                                                    | most         | most         |         | (never to urgent/emerg)
R-S2-4  | rules_level == 'routine' AND no readings entered   | review       | yellow       | True    | Pending Clinician Sign-off
        | AND patient reported feeling unwell                |              |              |         | (proposal Sec 15 yellow)
        | AND NO_READING_SYMPTOM_RAISE=true                  |              |              |         |
=============================================================================
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Single source of truth for triage colors (Proposal Section 15)
LEVEL_TO_COLOUR_MAP = {
    "routine": "green",
    "review": "yellow",
    "urgent": "red",
    "emergency": "red",
}

# Trend escalation constant approved by doctor on 8 Nov 2026
# "5 check-ins / BP charting to be done before referring pt for review"
TREND_MIN_POINTS = 5

# Target physiological boundaries from existing rules (triage_protocol.py & interview_planner.py)
# Systolic target: BP_STAGE2_SYSTOLIC_MMHG = 140 (triage_protocol.py:72)
# Glucose target: 180 mg/dL (interview_planner.py:143 / ADA general target)
TARGET_THRESHOLDS = {
    "blood_pressure_systolic": 140.0,
    "systolic": 140.0,
    "glucose": 180.0,
}


def level_to_colour(level: str) -> str:
    """
    Maps clinical triage level to single source of truth color string.

    Parameters
    ----------
    level : str
        Clinical level ('routine', 'review', 'urgent', 'emergency')

    Returns
    -------
    str
        'green' for routine, 'yellow' for review, 'red' for urgent or emergency.

    Raises
    ------
    ValueError
        If the level is unknown (never guesses a color).
    """
    if not isinstance(level, str):
        raise ValueError(f"Unknown level: {level!r}")
    cleaned = level.strip().lower()
    if cleaned not in LEVEL_TO_COLOUR_MAP:
        raise ValueError(f"Unknown level: {level!r}")
    return LEVEL_TO_COLOUR_MAP[cleaned]


def check_unwell_symptoms(state: Any) -> bool:
    """
    Detects if the patient reported feeling unwell in free text or narrative answers.
    Reuses existing severity and danger patterns from interview_findings.py and danger_wordgroups.
    """
    from agents.interview_findings import SEVERITY_LEVEL_PATTERNS

    text_to_scan: List[str] = []

    # 1. State answers dict
    answers = getattr(state, "answers", None)
    if isinstance(answers, dict):
        for v in answers.values():
            if isinstance(v, str):
                text_to_scan.append(v)
            elif isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, str):
                        text_to_scan.append(sub_v)

    # 2. Intake symptom payloads
    intakes = getattr(state, "intakes", None) or []
    for it in intakes:
        if isinstance(it, dict):
            symp = it.get("symptoms")
            if isinstance(symp, dict):
                for val in symp.values():
                    if isinstance(val, str):
                        text_to_scan.append(val)
            free_text = it.get("patient_free_text") or it.get("narrative")
            if isinstance(free_text, str):
                text_to_scan.append(free_text)

    combined_text = " ".join(text_to_scan).lower()
    if not combined_text.strip():
        return False

    # Check for severe/moderate keywords from interview_findings.py
    for level, words in SEVERITY_LEVEL_PATTERNS:
        if level in ("severe", "moderate"):
            if any(w in combined_text for w in words):
                return True

    # Common unwell phrases
    unwell_phrases = [
        "not feeling well", "feeling unwell", "feeling bad", "very bad",
        "tabiyat theek nahi", "tabiyat kharab", "kharaab", "bura lag raha hai",
        "طبیعت خراب", "طبیعت ٹھیک نہیں", "بیمار"
    ]
    return any(p in combined_text for p in unwell_phrases)


def decide_stage2(
    rules_level: str,
    risk_results: Optional[Any] = None,
    trends: Optional[Dict[str, Any]] = None,
    flags: Optional[Dict[str, Any]] = None,
    state: Optional[Any] = None,
    has_readings: bool = True,
    cooldown_active: bool = False,
) -> Dict[str, Any]:
    """
    Stage-2 Final Triage Decision Engine.

    Parameters
    ----------
    rules_level : str
        Initial level determined by deterministic clinical rules ('routine', 'review', 'urgent', 'emergency').
    risk_results : dict or list of dict, optional
        Evaluated risk model output(s) from risk_agent.assess().
    trends : dict, optional
        Longitudinal trends computed by compute_trends().
    flags : dict, optional
        System configuration flags (RISK_CAN_RAISE, TREND_CAN_RAISE, NO_READING_SYMPTOM_RAISE, etc.).
    state : InterviewState, optional
        Check-in interview state.
    has_readings : bool
        Whether this check-in has valid BP or glucose readings.
    cooldown_active : bool
        Whether risk raise cooldown is active for this patient.

    Returns
    -------
    dict
        {
            "final_level": str,
            "triage_colour": str,
            "raised": bool,
            "raised_by": list of dict,
            "patient_reason_key": Optional[str],
            "triggered_rules": list of str,
        }
    """
    if flags is None:
        flags = {
            "RISK_ENABLED": os.environ.get("RISK_ENABLED", "").strip().lower() == "true",
            "RISK_CAN_RAISE": os.environ.get("RISK_CAN_RAISE", "").strip().lower() == "true",
            "TREND_CAN_RAISE": os.environ.get("TREND_CAN_RAISE", "").strip().lower() == "true",
            "NO_READING_SYMPTOM_RAISE": os.environ.get("NO_READING_SYMPTOM_RAISE", "").strip().lower() == "true",
        }

    # Normalize inputs
    norm_rules_level = str(rules_level).strip().lower()
    if norm_rules_level not in LEVEL_TO_COLOUR_MAP:
        raise ValueError(f"Invalid rules_level for Stage-2: {rules_level!r}")

    # R-S2-0: Invariant — Emergency, urgent, or review never lowered, emergency never touched
    if norm_rules_level in ("emergency", "urgent", "review"):
        return {
            "final_level": norm_rules_level,
            "triage_colour": level_to_colour(norm_rules_level),
            "raised": False,
            "raised_by": [],
            "patient_reason_key": None,
            "triggered_rules": ["R-S2-0"],
        }

    # At this point, norm_rules_level is strictly 'routine'
    raised = False
    raised_by: List[Dict[str, Any]] = []
    triggered_rules: List[str] = []
    patient_reason_key: Optional[str] = None

    # Normalise risk_results to a list
    model_list: List[Dict[str, Any]] = []
    if isinstance(risk_results, dict) and "models" in risk_results and isinstance(risk_results["models"], list):
        model_list = [m for m in risk_results["models"] if isinstance(m, dict)]
    elif isinstance(risk_results, list):
        model_list = [m for m in risk_results if isinstance(m, dict)]
    elif isinstance(risk_results, dict):
        model_list = [risk_results]

    # R-S2-1: Risk model raise (routine -> review)
    # Reuses risk_rules apply_risk_to_level logic
    if flags.get("RISK_ENABLED", True) and flags.get("RISK_CAN_RAISE") and not cooldown_active:
        from agents.risk_rules import apply_risk_to_level
        orig_en = os.environ.get("RISK_ENABLED")
        orig_can = os.environ.get("RISK_CAN_RAISE")
        try:
            os.environ["RISK_ENABLED"] = "true"
            os.environ["RISK_CAN_RAISE"] = "true"
            for m_res in model_list:
                if m_res.get("status") == "ok" and m_res.get("band") == "high":
                    _, can_raise = apply_risk_to_level("routine", m_res)
                    if can_raise:
                        raised = True
                        m_name = m_res.get("model_name") or m_res.get("disease") or "risk_model"
                        raised_by.append({
                            "source": "risk_model",
                            "model": m_name,
                            "band": "high",
                            "detail": f"Risk model '{m_name}' assessed HIGH risk",
                        })
                        triggered_rules.append("R-S2-1")
                        # Do not break; record all high models
        finally:
            if orig_en is not None:
                os.environ["RISK_ENABLED"] = orig_en
            else:
                os.environ.pop("RISK_ENABLED", None)
            if orig_can is not None:
                os.environ["RISK_CAN_RAISE"] = orig_can
            else:
                os.environ.pop("RISK_CAN_RAISE", None)

    # R-S2-2: Trend raise (routine -> review)
    # Doctor's Answer 2: >= 5 points, rising, latest reading above target range
    if flags.get("TREND_CAN_RAISE") and trends and isinstance(trends, dict):
        trends_dict = trends.get("trends", {}) if "trends" in trends else trends
        for obs_key in ("blood_pressure_systolic", "glucose"):
            s_data = trends_dict.get(obs_key)
            if not isinstance(s_data, dict):
                continue

            direction = s_data.get("direction")
            n_points = s_data.get("n", 0)
            values = s_data.get("values") or []

            if direction == "rising" and n_points >= TREND_MIN_POINTS and values:
                # Get the latest reading value
                latest_point = values[-1]
                latest_val = latest_point.get("value") if isinstance(latest_point, dict) else latest_point
                target_thresh = TARGET_THRESHOLDS.get(obs_key, 140.0)

                try:
                    latest_val_float = float(latest_val)
                    if latest_val_float >= target_thresh:
                        raised = True
                        label = "systolic blood pressure" if "systolic" in obs_key else "blood glucose"
                        raised_by.append({
                            "source": "trend",
                            "observation_type": obs_key,
                            "direction": "rising",
                            "n": n_points,
                            "latest_value": latest_val_float,
                            "target_threshold": target_thresh,
                            "detail": f"Rising {label} trend ({n_points} readings, latest {latest_val_float} >= target {target_thresh})",
                        })
                        triggered_rules.append("R-S2-2")
                        patient_reason_key = "trend_rising"
                except (ValueError, TypeError):
                    pass

    # R-S2-4: No readings with ambiguous symptom picture (routine -> review)
    # Proposal Section 15 yellow row. Pending clinician sign-off.
    if flags.get("NO_READING_SYMPTOM_RAISE") and not has_readings and state:
        if check_unwell_symptoms(state):
            raised = True
            raised_by.append({
                "source": "symptoms_no_readings",
                "detail": "Patient reported feeling unwell without objective vital readings available",
            })
            triggered_rules.append("R-S2-4")
            patient_reason_key = "symptoms_without_readings"

    # R-S2-3: Invariant — At most one step escalation (routine -> review)
    final_level = "review" if raised else "routine"

    return {
        "final_level": final_level,
        "triage_colour": level_to_colour(final_level),
        "raised": raised,
        "raised_by": raised_by,
        "patient_reason_key": patient_reason_key,
        "triggered_rules": triggered_rules if triggered_rules else ["ROUTINE_UNCHANGED"],
    }

