"""
Reconciliation Agent (Milestone 3)

Deterministic, rule-based reconciliation between two normalized patient bundles
(Connected Mode and Isolated Mode) for the SAME patient.

Performs NO clinical interpretation, risk calculation, trust scoring, human-review flagging,
or LLM processing. Identifies agreement, conflict, missing data, or insufficient data.

=============================================================================
RECONCILIATION CONFIGURATION & THRESHOLDS
=============================================================================
- MATCH WINDOW: 48 Hours (1-to-1, nearest-neighbor timestamp matching)
- CONFLICT THRESHOLDS:
    glucose: 15.0 mg/dL
    hba1c: 0.5 %
    blood_pressure_systolic: 10.0 mmHg
    blood_pressure_diastolic: 10.0 mmHg
    weight: 2.0 kg
* Note: Illustrative POC threshold values only — NOT clinical guidance.
=============================================================================
"""

import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

# Dataclass Schemas for Reconciliation Results
@dataclass
class ObservationComparison:
    observation_type: str
    value_a: Optional[float]
    value_b: Optional[float]
    unit_a: Optional[str]
    unit_b: Optional[str]
    source_a: Optional[str]
    source_b: Optional[str]
    source_record_id_a: Optional[str]
    source_record_id_b: Optional[str]
    timestamp_a: Optional[str]
    timestamp_b: Optional[str]
    status: str  # "agree" | "conflict" | "missing_in_a" | "missing_in_b" | "insufficient_data"
    delta: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MedicationComparison:
    medication_name: str
    status_a: Optional[str]
    status_b: Optional[str]
    dosage_a: Optional[str]
    dosage_b: Optional[str]
    source_a: Optional[str]
    source_b: Optional[str]
    source_record_id_a: Optional[str]
    source_record_id_b: Optional[str]
    comparison_status: str  # "agree" | "conflict" | "missing_in_a" | "missing_in_b"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ReconciliationResult:
    patient_id: str
    observation_comparisons: List[ObservationComparison]
    medication_comparisons: List[MedicationComparison]
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# Rule Constants
OBSERVATION_MATCH_WINDOW_HOURS = 48.0

# Illustrative POC threshold values only — NOT clinical guidance
OBSERVATION_CONFLICT_THRESHOLDS = {
    "glucose": 15.0,
    "hba1c": 0.5,
    "blood_pressure_systolic": 10.0,
    "blood_pressure_diastolic": 10.0,
    "weight": 2.0,
}

def _parse_iso_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str or ts_str == "unknown_time":
        return None
    try:
        # Handle trailing 'Z' for UTC
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _time_diff_hours(ts1: Optional[str], ts2: Optional[str]) -> Optional[float]:
    dt1 = _parse_iso_timestamp(ts1)
    dt2 = _parse_iso_timestamp(ts2)
    if not dt1 or not dt2:
        return None
    diff_sec = abs((dt1 - dt2).total_seconds())
    return diff_sec / 3600.0

def _match_observations(
    obs_a_list: List[Any],
    obs_b_list: List[Any]
) -> Tuple[List[Tuple[Any, Any]], List[Any], List[Any]]:
    """
    Step 1a: Matching Observations.
    Implements 1-to-1 nearest-neighbor matching within OBSERVATION_MATCH_WINDOW_HOURS.
    Returns (matched_pairs, unmatched_a, unmatched_b).
    """
    matched_pairs = []
    used_b_indices = set()
    unmatched_a = []

    for obs_a in obs_a_list:
        best_b = None
        best_b_idx = None
        best_diff = float("inf")

        for idx, obs_b in enumerate(obs_b_list):
            if idx in used_b_indices:
                continue
            if obs_a.observation_type != obs_b.observation_type:
                continue
            
            diff_h = _time_diff_hours(obs_a.timestamp, obs_b.timestamp)
            if diff_h is not None and diff_h <= OBSERVATION_MATCH_WINDOW_HOURS:
                if diff_h < best_diff:
                    best_diff = diff_h
                    best_b = obs_b
                    best_b_idx = idx

        if best_b is not None:
            matched_pairs.append((obs_a, best_b))
            used_b_indices.add(best_b_idx)
        else:
            unmatched_a.append(obs_a)

    unmatched_b = [obs_b for idx, obs_b in enumerate(obs_b_list) if idx not in used_b_indices]
    return matched_pairs, unmatched_a, unmatched_b

def _match_medications(
    med_a_list: List[Any],
    med_b_list: List[Any]
) -> Tuple[List[Tuple[Any, Any]], List[Any], List[Any]]:
    """
    Step 1b: Matching Medications.
    Matches by normalized medication name (trimmed, lowercased).
    Returns (matched_pairs, unmatched_a, unmatched_b).
    """
    matched_pairs = []
    used_b_indices = set()
    unmatched_a = []

    for med_a in med_a_list:
        clean_a_name = med_a.medication_name.strip().lower()
        matched_b = None
        matched_b_idx = None

        for idx, med_b in enumerate(med_b_list):
            if idx in used_b_indices:
                continue
            clean_b_name = med_b.medication_name.strip().lower()
            if clean_a_name == clean_b_name:
                matched_b = med_b
                matched_b_idx = idx
                break

        if matched_b is not None:
            matched_pairs.append((med_a, matched_b))
            used_b_indices.add(matched_b_idx)
        else:
            unmatched_a.append(med_a)

    unmatched_b = [med_b for idx, med_b in enumerate(med_b_list) if idx not in used_b_indices]
    return matched_pairs, unmatched_a, unmatched_b

def _units_compatible(unit_a: Optional[str], unit_b: Optional[str]) -> bool:
    if not unit_a or not unit_b:
        return True
    u1 = unit_a.strip().lower().replace("[", "").replace("]", "")
    u2 = unit_b.strip().lower().replace("[", "").replace("]", "")
    return u1 == u2

def _classify_observations(
    matched_pairs: List[Tuple[Any, Any]],
    unmatched_a: List[Any],
    unmatched_b: List[Any]
) -> List[ObservationComparison]:
    """
    Step 2a: Classifying Observations into ObservationComparison list.
    Categories: "agree", "conflict", "missing_in_a", "missing_in_b", "insufficient_data".
    """
    comparisons = []

    # Process Matched Pairs
    for obs_a, obs_b in matched_pairs:
        val_a = obs_a.value
        val_b = obs_b.value
        
        # 1. Check for insufficient data (missing/non-numeric value)
        if val_a is None or val_b is None or math.isnan(val_a) or math.isnan(val_b):
            comparisons.append(ObservationComparison(
                observation_type=obs_a.observation_type,
                value_a=val_a,
                value_b=val_b,
                unit_a=obs_a.unit,
                unit_b=obs_b.unit,
                source_a=obs_a.source,
                source_b=obs_b.source,
                source_record_id_a=obs_a.source_record_id,
                source_record_id_b=obs_b.source_record_id,
                timestamp_a=obs_a.timestamp,
                timestamp_b=obs_b.timestamp,
                status="insufficient_data",
                delta=None
            ))
            continue

        # 2. Check for unknown observation type without configured threshold
        if obs_a.observation_type not in OBSERVATION_CONFLICT_THRESHOLDS:
            comparisons.append(ObservationComparison(
                observation_type=obs_a.observation_type,
                value_a=val_a,
                value_b=val_b,
                unit_a=obs_a.unit,
                unit_b=obs_b.unit,
                source_a=obs_a.source,
                source_b=obs_b.source,
                source_record_id_a=obs_a.source_record_id,
                source_record_id_b=obs_b.source_record_id,
                timestamp_a=obs_a.timestamp,
                timestamp_b=obs_b.timestamp,
                status="insufficient_data",
                delta=None
            ))
            continue

        # 3. Check for unit incompatibility
        if not _units_compatible(obs_a.unit, obs_b.unit):
            comparisons.append(ObservationComparison(
                observation_type=obs_a.observation_type,
                value_a=val_a,
                value_b=val_b,
                unit_a=obs_a.unit,
                unit_b=obs_b.unit,
                source_a=obs_a.source,
                source_b=obs_b.source,
                source_record_id_a=obs_a.source_record_id,
                source_record_id_b=obs_b.source_record_id,
                timestamp_a=obs_a.timestamp,
                timestamp_b=obs_b.timestamp,
                status="insufficient_data",
                delta=None
            ))
            continue

        # 4. Compare delta against threshold
        delta = abs(val_a - val_b)
        threshold = OBSERVATION_CONFLICT_THRESHOLDS[obs_a.observation_type]
        status = "conflict" if delta > threshold else "agree"

        comparisons.append(ObservationComparison(
            observation_type=obs_a.observation_type,
            value_a=val_a,
            value_b=val_b,
            unit_a=obs_a.unit,
            unit_b=obs_b.unit,
            source_a=obs_a.source,
            source_b=obs_b.source,
            source_record_id_a=obs_a.source_record_id,
            source_record_id_b=obs_b.source_record_id,
            timestamp_a=obs_a.timestamp,
            timestamp_b=obs_b.timestamp,
            status=status,
            delta=round(delta, 4)
        ))

    # Process Unmatched A (Missing in B)
    for obs_a in unmatched_a:
        comparisons.append(ObservationComparison(
            observation_type=obs_a.observation_type,
            value_a=obs_a.value,
            value_b=None,
            unit_a=obs_a.unit,
            unit_b=None,
            source_a=obs_a.source,
            source_b=None,
            source_record_id_a=obs_a.source_record_id,
            source_record_id_b=None,
            timestamp_a=obs_a.timestamp,
            timestamp_b=None,
            status="missing_in_b",
            delta=None
        ))

    # Process Unmatched B (Missing in A)
    for obs_b in unmatched_b:
        comparisons.append(ObservationComparison(
            observation_type=obs_b.observation_type,
            value_a=None,
            value_b=obs_b.value,
            unit_a=None,
            unit_b=obs_b.unit,
            source_a=None,
            source_b=obs_b.source,
            source_record_id_a=None,
            source_record_id_b=obs_b.source_record_id,
            timestamp_a=None,
            timestamp_b=obs_b.timestamp,
            status="missing_in_a",
            delta=None
        ))

    return comparisons

def _classify_medications(
    matched_pairs: List[Tuple[Any, Any]],
    unmatched_a: List[Any],
    unmatched_b: List[Any]
) -> List[MedicationComparison]:
    """
    Step 2b: Classifying Medications into MedicationComparison list.
    Categories: "agree", "conflict", "missing_in_a", "missing_in_b".
    """
    comparisons = []

    # Process Matched Pairs
    for med_a, med_b in matched_pairs:
        status_a_clean = (med_a.status or "").strip().lower()
        status_b_clean = (med_b.status or "").strip().lower()
        dosage_a_clean = (med_a.dosage or "").strip().lower()
        dosage_b_clean = (med_b.dosage or "").strip().lower()

        if status_a_clean != status_b_clean or dosage_a_clean != dosage_b_clean:
            comp_status = "conflict"
        else:
            comp_status = "agree"

        comparisons.append(MedicationComparison(
            medication_name=med_a.medication_name,
            status_a=med_a.status,
            status_b=med_b.status,
            dosage_a=med_a.dosage,
            dosage_b=med_b.dosage,
            source_a=med_a.source,
            source_b=med_b.source,
            source_record_id_a=med_a.source_record_id,
            source_record_id_b=med_b.source_record_id,
            comparison_status=comp_status
        ))

    # Process Unmatched A (Missing in B)
    for med_a in unmatched_a:
        comparisons.append(MedicationComparison(
            medication_name=med_a.medication_name,
            status_a=med_a.status,
            status_b=None,
            dosage_a=med_a.dosage,
            dosage_b=None,
            source_a=med_a.source,
            source_b=None,
            source_record_id_a=med_a.source_record_id,
            source_record_id_b=None,
            comparison_status="missing_in_b"
        ))

    # Process Unmatched B (Missing in A)
    for med_b in unmatched_b:
        comparisons.append(MedicationComparison(
            medication_name=med_b.medication_name,
            status_a=None,
            status_b=med_b.status,
            dosage_a=None,
            dosage_b=med_b.dosage,
            source_a=None,
            source_b=med_b.source,
            source_record_id_a=None,
            source_record_id_b=med_b.source_record_id,
            comparison_status="missing_in_a"
        ))

    return comparisons

def reconcile_bundles(bundle_a: Dict[str, Any], bundle_b: Dict[str, Any]) -> ReconciliationResult:
    """
    Main Reconciliation Entry Point.

    Enforces Patient Identity Contract: bundle_a["patient"].patient_id == bundle_b["patient"].patient_id
    Raises ValueError if patient IDs differ.

    Executes 3 separable steps:
      1. Matching (1-to-1 nearest-neighbor within 48h for obs; normalized name for meds)
      2. Classification (agree, conflict, missing_in_a, missing_in_b, insufficient_data)
      3. Result Construction (ReconciliationResult with summary counts and full provenance)
    """
    patient_a = bundle_a.get("patient")
    patient_b = bundle_b.get("patient")

    pid_a = getattr(patient_a, "patient_id", None) if patient_a else None
    pid_b = getattr(patient_b, "patient_id", None) if patient_b else None

    if not pid_a or not pid_b or pid_a != pid_b:
        raise ValueError(
            f"Patient Identity Contract Violation: Bundle A patient_id '{pid_a}' does not match Bundle B patient_id '{pid_b}'."
        )

    # 1. Matching Step
    obs_matched, obs_unmatched_a, obs_unmatched_b = _match_observations(
        bundle_a.get("observations", []),
        bundle_b.get("observations", [])
    )
    med_matched, med_unmatched_a, med_unmatched_b = _match_medications(
        bundle_a.get("medications", []),
        bundle_b.get("medications", [])
    )

    # 2. Classification Step
    obs_comparisons = _classify_observations(obs_matched, obs_unmatched_a, obs_unmatched_b)
    med_comparisons = _classify_medications(med_matched, med_unmatched_a, med_unmatched_b)

    # 3. Result Construction & Summary Statistics Calculation
    summary = {
        "agreements": 0,
        "conflicts": 0,
        "missing_in_a": 0,
        "missing_in_b": 0,
        "insufficient_data": 0
    }

    for comp in obs_comparisons:
        if comp.status == "agree":
            summary["agreements"] += 1
        elif comp.status == "conflict":
            summary["conflicts"] += 1
        elif comp.status == "missing_in_a":
            summary["missing_in_a"] += 1
        elif comp.status == "missing_in_b":
            summary["missing_in_b"] += 1
        elif comp.status == "insufficient_data":
            summary["insufficient_data"] += 1

    for comp in med_comparisons:
        if comp.comparison_status == "agree":
            summary["agreements"] += 1
        elif comp.comparison_status == "conflict":
            summary["conflicts"] += 1
        elif comp.comparison_status == "missing_in_a":
            summary["missing_in_a"] += 1
        elif comp.comparison_status == "missing_in_b":
            summary["missing_in_b"] += 1

    return ReconciliationResult(
        patient_id=pid_a,
        observation_comparisons=obs_comparisons,
        medication_comparisons=med_comparisons,
        summary=summary
    )
