"""
Reference Ranges Module (Doctor Decisions D5 & D6 / Nov 2026).

One single source of truth for target reference ranges used by Chronicare.
All thresholds are derived from the application's clinical rules and doctor-approved guidance.

Sources:
- Systolic Blood Pressure: 90.0 to < 140.0 mmHg (Target: 90–139 mmHg)
    CLINICAL_RULES.md Section 2 Priority 1 (Stage 2 threshold >= 140 mmHg) &
    Section 2 Priority 4 (Low BP threshold < 90 mmHg); Section 8 Table
    (BP_LOW_SYSTOLIC_MMHG = 90, BP_STAGE2_SYSTOLIC_MMHG = 140).
    Guideline: 2025 AHA/ACC Guideline.
- Diastolic Blood Pressure: 60.0 to < 90.0 mmHg (Target: 60–89 mmHg)
    CLINICAL_RULES.md Section 2 Priority 1 (Stage 2 threshold >= 90 mmHg) &
    Section 2 Priority 4 (Low BP threshold < 60 mmHg); Section 8 Table
    (BP_LOW_DIASTOLIC_MMHG = 60, BP_STAGE2_DIASTOLIC_MMHG = 90).
    Guideline: 2025 AHA/ACC Guideline.
- Fasting Blood Glucose: 90.0 to 125.0 mg/dL (5.0 to 6.9 mmol/L)
    Doctor Decision D6 (Nov 2026): fasting target 90–125 mg/dL. Values < 90 mg/dL
    pose dizziness risk and are below target; values > 125 mg/dL are above target.
- Post-Meal Blood Glucose: 125.0 to 200.0 mg/dL (6.9 to 11.1 mmol/L)
    Doctor Decision D6 (Nov 2026): after meals target 125–200 mg/dL.
    Values 90–124 post-meal are accepted as In target and auto-resolve under D5.
- Random / General Blood Glucose: 90.0 to 200.0 mg/dL (5.0 to 11.1 mmol/L)
    Doctor Decision D6 (Nov 2026): overall target band 90–200 mg/dL.

Unspecified / Undefined Vitals:
- Weight, Heart Rate, HbA1c: Routine / normal ranges are NOT defined in CLINICAL_RULES.md.
  They are blocked from normal auto-resolution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


# Canonical conversion factor: 18.0 mg/dL per 1.0 mmol/L
MMOL_CONVERSION_FACTOR = 18.0


@dataclass(frozen=True)
class ReferenceRange:
    key: str
    label: str
    unit: str
    low: float
    high: float
    clinical_rules_section: str
    source_label: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Target reference ranges defined strictly from CLINICAL_RULES.md and Doctor Decision D6
REFERENCE_RANGES: Dict[str, ReferenceRange] = {
    "blood_pressure_systolic": ReferenceRange(
        key="blood_pressure_systolic",
        label="Systolic Blood Pressure",
        unit="mmHg",
        low=90.0,
        high=140.0,
        clinical_rules_section="Section 2 Priority 1 & 4; Section 8 (BP_LOW_SYSTOLIC_MMHG=90, BP_STAGE2_SYSTOLIC_MMHG=140)",
        source_label="2025 AHA/ACC Guideline",
    ),
    "blood_pressure_diastolic": ReferenceRange(
        key="blood_pressure_diastolic",
        label="Diastolic Blood Pressure",
        unit="mmHg",
        low=60.0,
        high=90.0,
        clinical_rules_section="Section 2 Priority 1 & 4; Section 8 (BP_LOW_DIASTOLIC_MMHG=60, BP_STAGE2_DIASTOLIC_MMHG=90)",
        source_label="2025 AHA/ACC Guideline",
    ),
    "glucose_fasting": ReferenceRange(
        key="glucose_fasting",
        label="Fasting Blood Glucose",
        unit="mg/dL",
        low=90.0,
        high=125.0,
        clinical_rules_section="Doctor Decision D6 (Nov 2026): fasting target 90–125 mg/dL; <90 dizziness risk",
        source_label="Approved by the doctor on record (Nov 2026)",
    ),
    "glucose_post_meal": ReferenceRange(
        key="glucose_post_meal",
        label="Post-Meal Blood Glucose",
        unit="mg/dL",
        low=125.0,
        high=200.0,
        clinical_rules_section="Doctor Decision D6 (Nov 2026): after meals target 125–200 mg/dL; 90–124 accepted as in-target",
        source_label="Approved by the doctor on record (Nov 2026)",
    ),
    "glucose_random": ReferenceRange(
        key="glucose_random",
        label="Random Blood Glucose",
        unit="mg/dL",
        low=90.0,
        high=200.0,
        clinical_rules_section="Doctor Decision D6 (Nov 2026): random / general target 90–200 mg/dL",
        source_label="Approved by the doctor on record (Nov 2026)",
    ),
}

# Explicitly documented blocked vitals where no reference range is defined in CLINICAL_RULES.md
BLOCKED_VITALS: Dict[str, str] = {
    "weight": "Range not defined in CLINICAL_RULES.md (evidence: only conflict threshold exists in reconciliation_agent.py, no physiological normal range defined in CLINICAL_RULES.md)",
    "heart_rate": "Range not defined in CLINICAL_RULES.md (evidence: pulse/heart rate not bounded in CLINICAL_RULES.md)",
    "hba1c": "Range not defined in CLINICAL_RULES.md for routine auto-resolution (evidence: only 365-day screening interval in Rule R5 and conflict threshold 0.5% in reconciliation_agent.py)",
}


def normalize_obs_type(obs_type: str) -> str:
    """Normalize aliases for observation types."""
    t = (obs_type or "").strip().lower()
    if t in ("systolic", "blood_pressure_systolic", "sbp"):
        return "blood_pressure_systolic"
    if t in ("diastolic", "blood_pressure_diastolic", "dbp"):
        return "blood_pressure_diastolic"
    if t in ("glucose", "blood_glucose", "blood_sugar"):
        return "glucose"
    return t


def is_reading_in_normal_range(
    observation_type: str,
    value: Optional[float],
    context: Optional[str] = None,
) -> bool:
    """
    Check if a self-reported reading is within the target reference range (Doctor Decision D6).

    Parameters
    ----------
    observation_type : str
        The observation type (e.g. 'blood_pressure_systolic', 'glucose')
    value : Optional[float]
        The numeric value of the observation
    context : Optional[str]
        Optional context (e.g. 'fasting', 'after_meal', 'random')

    Returns
    -------
    bool
        True if the reading is within the target range, False otherwise.
    """
    if value is None:
        return False

    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return False

    norm_type = normalize_obs_type(observation_type)

    if norm_type == "blood_pressure_systolic":
        ref = REFERENCE_RANGES["blood_pressure_systolic"]
        return ref.low <= val_float < ref.high

    if norm_type == "blood_pressure_diastolic":
        ref = REFERENCE_RANGES["blood_pressure_diastolic"]
        return ref.low <= val_float < ref.high

    if norm_type == "glucose":
        # Below 90 mg/dL in any context is below target (dizziness risk per D6)
        # D5 does NOT auto-resolve it -> self-reported value below 90 goes to review
        if val_float < 90.0:
            return False

        ctx = (context or "").strip().lower()
        if ctx in ("fasting", "before_breakfast", "before_meal"):
            ref = REFERENCE_RANGES["glucose_fasting"]
            return ref.low <= val_float <= ref.high
        elif ctx in ("after_meal", "post_meal", "postprandial", "after_breakfast", "after_lunch", "after_dinner"):
            # Post-meal target is 125–200 mg/dL.
            # Decision to record: 90–124 post-meal is accepted as In target and does NOT review under D5
            # Values > 200 are above target and do NOT auto-resolve
            return 90.0 <= val_float <= 200.0
        else:
            # Random / unspecified context target: 90.0 to 200.0 mg/dL
            return 90.0 <= val_float <= 200.0

    # Other observation types are blocked from normal auto-resolution
    return False


is_reading_in_target_range = is_reading_in_normal_range


def get_all_reference_ranges(preferred_unit: str = "mg/dL") -> List[Dict[str, Any]]:
    """
    Return all defined reference ranges for the API / UI.
    If preferred_unit is mmol/L, converts glucose thresholds.
    """
    is_mmol = preferred_unit.strip().lower() in ("mmol/l", "mmol")
    results = []

    for key, ref in REFERENCE_RANGES.items():
        item = {
            "key": ref.key,
            "label": ref.label,
            "unit": ref.unit,
            "low": ref.low,
            "high": ref.high,
            "clinical_rules_section": ref.clinical_rules_section,
            "source_label": ref.source_label,
        }
        if "glucose" in key and is_mmol:
            item["unit"] = "mmol/L"
            item["low"] = round(ref.low / MMOL_CONVERSION_FACTOR, 1)
            item["high"] = round(ref.high / MMOL_CONVERSION_FACTOR, 1)
            item["low_mg_dl"] = ref.low
            item["high_mg_dl"] = ref.high
        elif "glucose" in key:
            item["low_mmol_l"] = round(ref.low / MMOL_CONVERSION_FACTOR, 1)
            item["high_mmol_l"] = round(ref.high / MMOL_CONVERSION_FACTOR, 1)

        results.append(item)

    return results


def get_all_reference_ranges(preferred_unit: str = "mg/dL") -> List[Dict[str, Any]]:
    """
    Return all defined reference ranges for the API / UI.
    If preferred_unit is mmol/L, converts glucose thresholds.
    """
    is_mmol = preferred_unit.strip().lower() in ("mmol/l", "mmol")
    results = []

    for key, ref in REFERENCE_RANGES.items():
        item = {
            "key": ref.key,
            "label": ref.label,
            "unit": ref.unit,
            "low": ref.low,
            "high": ref.high,
            "clinical_rules_section": ref.clinical_rules_section,
            "source_label": ref.source_label,
        }
        if "glucose" in key and is_mmol:
            item["unit"] = "mmol/L"
            item["low"] = round(ref.low / MMOL_CONVERSION_FACTOR, 1)
            item["high"] = round(ref.high / MMOL_CONVERSION_FACTOR, 1)
            item["low_mg_dl"] = ref.low
            item["high_mg_dl"] = ref.high
        elif "glucose" in key:
            item["low_mmol_l"] = round(ref.low / MMOL_CONVERSION_FACTOR, 1)
            item["high_mmol_l"] = round(ref.high / MMOL_CONVERSION_FACTOR, 1)

        results.append(item)

    return results
