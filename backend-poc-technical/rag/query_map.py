"""
Deterministic query mapper for ChronicCare AI RAG.
Constructs targeted search queries from triage protocol results and check-in readings
without relying on unconstrained user free text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryMapping:
    """Represents a deterministic search query configuration."""
    trigger_category: str
    condition: str
    topic_slugs: list[str]
    query_text: str
    min_priority: int


# Canonical table mapping triage trigger categories / clinical reasons to RAG queries
TRIAGE_QUERY_TABLE: dict[str, QueryMapping] = {
    "bp_severe": QueryMapping(
        trigger_category="bp_severe",
        condition="hypertension",
        topic_slugs=["crisis", "emergency", "bp_targets"],
        query_text="blood pressure 180 120 mmhg hypertensive crisis emergency organ damage",
        min_priority=1,
    ),
    "bp_crisis": QueryMapping(
        trigger_category="bp_crisis",
        condition="hypertension",
        topic_slugs=["crisis", "emergency", "bp_targets"],
        query_text="blood pressure 180 120 mmhg hypertensive emergency crisis severe elevation",
        min_priority=1,
    ),
    "glucose_low": QueryMapping(
        trigger_category="glucose_low",
        condition="diabetes",
        topic_slugs=["hypoglycemia", "emergency"],
        query_text="glucose hypoglycemia 70 54 mgdl fast acting carbohydrate 15 grams rule of 15",
        min_priority=1,
    ),
    "glucose_very_low": QueryMapping(
        trigger_category="glucose_very_low",
        condition="diabetes",
        topic_slugs=["hypoglycemia", "emergency"],
        query_text="severe hypoglycemia 54 mgdl emergency glucose glucagon urgent medical attention",
        min_priority=1,
    ),
    "glucose_high": QueryMapping(
        trigger_category="glucose_high",
        condition="diabetes",
        topic_slugs=["hyperglycemia", "emergency"],
        query_text="glucose high blood sugar 250 300 mgdl hyperglycemia hydration follow up",
        min_priority=1,
    ),
    "glucose_urgent_high": QueryMapping(
        trigger_category="glucose_urgent_high",
        condition="diabetes",
        topic_slugs=["hyperglycemia", "emergency"],
        query_text="severe hyperglycemia 300 400 mgdl diabetic ketoacidosis dka symptoms ketones",
        min_priority=1,
    ),
    "bp_low": QueryMapping(
        trigger_category="bp_low",
        condition="hypertension",
        topic_slugs=["hypotension", "bp_targets"],
        query_text="low blood pressure 90 60 mmhg hypotension dizziness orthostatic standing",
        min_priority=1,
    ),
    "bp_change": QueryMapping(
        trigger_category="bp_change",
        condition="hypertension",
        topic_slugs=["bp_targets", "lifestyle"],
        query_text="blood pressure rise notable change 20 mmhg home blood pressure measurement",
        min_priority=1,
    ),
    "bp_urgent": QueryMapping(
        trigger_category="bp_urgent",
        condition="hypertension",
        topic_slugs=["bp_targets", "stage2"],
        query_text="blood pressure stage 2 hypertension 140 90 mmhg re-check seated rest 5 minutes",
        min_priority=1,
    ),
    "ramadan_fasting": QueryMapping(
        trigger_category="ramadan_fasting",
        condition="diabetes",
        topic_slugs=["ramadan", "risk_stratification"],
        query_text="ramadan fasting risk categories type 2 diabetes insulin when to break fast",
        min_priority=1,
    ),
    "pregnancy_hypertension": QueryMapping(
        trigger_category="pregnancy_hypertension",
        condition="hypertension",
        topic_slugs=["pregnancy", "bp_targets"],
        query_text="hypertension in pregnancy preeclampsia blood pressure monitoring safe treatment",
        min_priority=1,
    ),
    "routine": QueryMapping(
        trigger_category="routine",
        condition="both",
        topic_slugs=["lifestyle", "bp_targets"],
        query_text="lifestyle modification salt sodium reduction physical activity blood pressure glucose targets",
        min_priority=1,
    ),
}


def build_query_from_triage(
    triage_result: dict[str, Any],
    readings: dict[str, Any] | None = None,
) -> QueryMapping:
    """
    Construct a deterministic query mapping from a triage result and optional readings.
    Evaluates:
    1. Direct 'trigger_category' in triage_result
    2. Specific flags in 'reasons' list
    3. Critical numerical thresholds in 'readings'
    4. General triage level fallback (emergency, urgent, review, routine)
    """
    # 1. Direct trigger_category match
    trig = str(triage_result.get("trigger_category", "")).lower().strip()
    if trig in TRIAGE_QUERY_TABLE:
        return TRIAGE_QUERY_TABLE[trig]

    # 2. Check reasons strings
    reasons = [str(r).lower() for r in triage_result.get("reasons", [])]
    for r in reasons:
        if "bp_severe" in r or "180" in r or "crisis" in r:
            return TRIAGE_QUERY_TABLE["bp_severe"]
        if "hypoglycemia" in r or "glucose_low" in r or ("glucose" in r and "low" in r):
            return TRIAGE_QUERY_TABLE["glucose_low"]
        if "glucose_high" in r or ("glucose" in r and "high" in r):
            return TRIAGE_QUERY_TABLE["glucose_high"]
        if "bp_low" in r or "hypotension" in r:
            return TRIAGE_QUERY_TABLE["bp_low"]
        if "bp_change" in r:
            return TRIAGE_QUERY_TABLE["bp_change"]
        if "ramadan" in r or "fasting" in r:
            return TRIAGE_QUERY_TABLE["ramadan_fasting"]
        if "pregnancy" in r:
            return TRIAGE_QUERY_TABLE["pregnancy_hypertension"]

    # 3. Check readings directly if provided
    if readings:
        sbp = readings.get("blood_pressure_systolic")
        dbp = readings.get("blood_pressure_diastolic")
        gluc = readings.get("glucose")

        if (sbp is not None and sbp >= 180) or (dbp is not None and dbp >= 120):
            return TRIAGE_QUERY_TABLE["bp_severe"]
        if gluc is not None and gluc < 54:
            return TRIAGE_QUERY_TABLE["glucose_very_low"]
        if gluc is not None and gluc < 70:
            return TRIAGE_QUERY_TABLE["glucose_low"]
        if gluc is not None and gluc >= 300:
            return TRIAGE_QUERY_TABLE["glucose_urgent_high"]
        if gluc is not None and gluc >= 250:
            return TRIAGE_QUERY_TABLE["glucose_high"]
        if (sbp is not None and sbp < 90) or (dbp is not None and dbp < 60):
            return TRIAGE_QUERY_TABLE["bp_low"]
        if (sbp is not None and sbp >= 140) or (dbp is not None and dbp >= 90):
            return TRIAGE_QUERY_TABLE["bp_urgent"]

    # 4. Check level
    lvl = str(triage_result.get("level", "")).lower().strip()
    if lvl == "emergency":
        return TRIAGE_QUERY_TABLE["bp_severe"]
    if lvl == "urgent":
        return TRIAGE_QUERY_TABLE["bp_urgent"]

    # 5. Fallback to routine
    return TRIAGE_QUERY_TABLE["routine"]
