"""
Verification Agent (Milestone 4)

Deterministic, rule-based verification layer sitting directly on top of Milestone 3's
Reconciliation Agent output (ReconciliationResult).

Evaluates trust levels, risk severity, and review necessity (requires_human_review)
with full provenance preservation. Performs NO conflict resolution (no value selection)
and NO clinical/triage decision making.

=============================================================================
TRUST LEVEL CONFIGURATION & RULES
=============================================================================
TRUST_LEVELS = {
    "fhir_clinician_entered": "high",
    "local_clinician_entered": "high",
    "local_ocr_or_upload": "medium",
    "local_self_reported": "low",
}
Default source-based rule:
- source == "fhir" -> "high" trust
- source == "local" -> "medium" trust (by default)
- missing side (source is None) -> trust_level is None
- optional fixture origin tag (e.g. "self_reported") -> "low" trust

=============================================================================
SEVERITY & REVIEW DECISION TABLE
=============================================================================
1. reconciliation_status == "agree":
   - Both trust levels present & at least one NOT "low" -> severity "none", requires_human_review = False
   - Both trust levels present & BOTH "low" -> severity "low", requires_human_review = True, reason: "agreement only between low-trust sources"

2. reconciliation_status == "conflict":
   - Observations:
     - delta <= 2x threshold -> severity "moderate", requires_human_review = True
     - delta > 2x threshold -> severity "high", requires_human_review = True
   - Medications:
     - status conflict involving "active" vs "stopped" -> severity "high", requires_human_review = True
     - other status or dosage conflict -> severity "moderate", requires_human_review = True

3. reconciliation_status in ("missing_in_a", "missing_in_b"):
   - Present side is "high" trust -> severity "low", requires_human_review = False (auto-resolved)
   - Present side is "medium" or "low" trust -> severity "moderate", requires_human_review = True

4. reconciliation_status == "insufficient_data":
   - severity "moderate" unconditionally, requires_human_review = True

5. Unconditional Summary Rules:
   - ANY severity "high" or "moderate" -> requires_human_review = True unconditionally.
   - Auto-resolution (requires_human_review = False) is ONLY possible for severity "none",
     or severity "low" when explicitly set False by Rule 3 (high-trust missing data).
=============================================================================
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from agents.reconciliation_agent import (
    ReconciliationResult,
    ObservationComparison,
    MedicationComparison,
    OBSERVATION_CONFLICT_THRESHOLDS
)

# Trust Level configuration dictionary
TRUST_LEVELS = {
    "fhir_clinician_entered": "high",
    "local_clinician_entered": "high",
    "local_ocr_or_upload": "medium",
    "local_self_reported": "low",
    "self_reported": "low",
    "ocr_or_upload": "medium",
    "clinician_entered": "high",
}

@dataclass
class ObservationVerification:
    observation_type: str
    reconciliation_status: str
    trust_level_a: Optional[str]
    trust_level_b: Optional[str]
    source_a: Optional[str]
    source_b: Optional[str]
    source_record_id_a: Optional[str]
    source_record_id_b: Optional[str]
    severity: str  # "none" | "low" | "moderate" | "high"
    requires_human_review: bool
    review_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MedicationVerification:
    medication_name: str
    reconciliation_status: str
    trust_level_a: Optional[str]
    trust_level_b: Optional[str]
    source_a: Optional[str]
    source_b: Optional[str]
    source_record_id_a: Optional[str]
    source_record_id_b: Optional[str]
    severity: str  # "none" | "low" | "moderate" | "high"
    requires_human_review: bool
    review_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class VerificationResult:
    patient_id: str
    observation_verifications: List[ObservationVerification]
    medication_verifications: List[MedicationVerification]
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def derive_trust_level(
    source: Optional[str],
    source_record_id: Optional[str],
    origins: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Step 1: Trust Assignment.
    Assigns trust level for a record based on source and optional origin tag.
    For a missing side (source is None), returns None.
    """
    if not source:
        return None

    # Check optional fixture origin lookup first
    if origins and source_record_id and source_record_id in origins:
        origin_val = origins[source_record_id]
        if origin_val in TRUST_LEVELS:
            return TRUST_LEVELS[origin_val]
        if origin_val.lower() in ["high", "medium", "low"]:
            return origin_val.lower()

    # Default source-based rule
    src_clean = source.strip().lower()
    if src_clean == "fhir":
        return "high"
    elif src_clean == "local":
        return "medium"

    return "medium"

def _verify_observation(
    comp: ObservationComparison,
    trust_a: Optional[str],
    trust_b: Optional[str]
) -> ObservationVerification:
    """
    Step 2 & 3: Risk Classification & Review Decision for Observations.
    Implements exact deterministic decision table.
    """
    status = comp.status
    obs_type = comp.observation_type
    delta = comp.delta

    severity = "none"
    requires_review = False
    reason = ""

    # Rule 1: Agreement
    if status == "agree":
        if trust_a == "low" and trust_b == "low":
            severity = "low"
            requires_review = True
            reason = "agreement only between low-trust sources"
        else:
            severity = "none"
            requires_review = False
            reason = "Agreement between trusted sources (auto-resolved)"

    # Rule 2: Conflict
    elif status == "conflict":
        threshold = OBSERVATION_CONFLICT_THRESHOLDS.get(obs_type, 0.0)
        double_threshold = 2.0 * threshold

        if delta is not None and delta > double_threshold:
            severity = "high"
            requires_review = True
            reason = f"Observation conflict exceeding 2x threshold (delta {delta} > 2x threshold {double_threshold})"
        else:
            severity = "moderate"
            requires_review = True
            reason = f"Observation conflict within 1x-2x threshold (delta {delta} <= 2x threshold {double_threshold})"

    # Rule 3: Missing in A or B
    elif status in ("missing_in_a", "missing_in_b"):
        present_trust = trust_a if status == "missing_in_b" else trust_b
        if present_trust == "high":
            severity = "low"
            requires_review = False
            reason = f"Record missing in one source ({status}); present side is high-trust (auto-resolved)"
        else:
            severity = "moderate"
            requires_review = True
            reason = f"Record missing in one source ({status}); present side is {present_trust}-trust"

    # Rule 4: Insufficient Data
    elif status == "insufficient_data":
        severity = "moderate"
        requires_review = True
        reason = "Insufficient data or unresolvable measurement"

    else:
        severity = "moderate"
        requires_review = True
        reason = f"Unhandled observation reconciliation status '{status}'"

    return ObservationVerification(
        observation_type=obs_type,
        reconciliation_status=status,
        trust_level_a=trust_a,
        trust_level_b=trust_b,
        source_a=comp.source_a,
        source_b=comp.source_b,
        source_record_id_a=comp.source_record_id_a,
        source_record_id_b=comp.source_record_id_b,
        severity=severity,
        requires_human_review=requires_review,
        review_reason=reason
    )

def _verify_medication(
    comp: MedicationComparison,
    trust_a: Optional[str],
    trust_b: Optional[str]
) -> MedicationVerification:
    """
    Step 2 & 3: Risk Classification & Review Decision for Medications.
    Implements exact deterministic decision table.
    """
    status = comp.comparison_status
    med_name = comp.medication_name

    severity = "none"
    requires_review = False
    reason = ""

    # Rule 1: Agreement
    if status == "agree":
        if trust_a == "low" and trust_b == "low":
            severity = "low"
            requires_review = True
            reason = "agreement only between low-trust sources"
        else:
            severity = "none"
            requires_review = False
            reason = "Medication agreement between trusted sources (auto-resolved)"

    # Rule 2: Conflict
    elif status == "conflict":
        stat_a = (comp.status_a or "").strip().lower()
        stat_b = (comp.status_b or "").strip().lower()

        # Check for active vs stopped conflict
        is_active_vs_stopped = ("active" in (stat_a, stat_b)) and ("stopped" in (stat_a, stat_b))

        if is_active_vs_stopped:
            severity = "high"
            requires_review = True
            reason = f"Medication status conflict involving active vs stopped ('{comp.status_a}' vs '{comp.status_b}')"
        else:
            severity = "moderate"
            requires_review = True
            reason = f"Medication dosage or status mismatch (A: status={comp.status_a}, dosage='{comp.dosage_a}' vs B: status={comp.status_b}, dosage='{comp.dosage_b}')"

    # Rule 3: Missing in A or B
    elif status in ("missing_in_a", "missing_in_b"):
        present_trust = trust_a if status == "missing_in_b" else trust_b
        if present_trust == "high":
            severity = "low"
            requires_review = False
            reason = f"Medication missing in one source ({status}); present side is high-trust (auto-resolved)"
        else:
            severity = "moderate"
            requires_review = True
            reason = f"Medication missing in one source ({status}); present side is {present_trust}-trust"

    else:
        severity = "moderate"
        requires_review = True
        reason = f"Unhandled medication reconciliation status '{status}'"

    return MedicationVerification(
        medication_name=med_name,
        reconciliation_status=status,
        trust_level_a=trust_a,
        trust_level_b=trust_b,
        source_a=comp.source_a,
        source_b=comp.source_b,
        source_record_id_a=comp.source_record_id_a,
        source_record_id_b=comp.source_record_id_b,
        severity=severity,
        requires_human_review=requires_review,
        review_reason=reason
    )

def verify_reconciliation(
    reconciliation_result: ReconciliationResult,
    origins: Optional[Dict[str, str]] = None
) -> VerificationResult:
    """
    Main Verification Entry Point.

    Takes M3's ReconciliationResult and assigns trust levels, severity,
    requires_human_review boolean, and review_reason string for each comparison.

    Executes 4 separable steps:
      1. Trust assignment
      2. Risk classification
      3. Review decision (requires_human_review + review_reason)
      4. Result construction & Summary calculation
    """
    obs_verifications = []
    for obs_comp in reconciliation_result.observation_comparisons:
        trust_a = derive_trust_level(obs_comp.source_a, obs_comp.source_record_id_a, origins)
        trust_b = derive_trust_level(obs_comp.source_b, obs_comp.source_record_id_b, origins)
        verification = _verify_observation(obs_comp, trust_a, trust_b)
        obs_verifications.append(verification)

    med_verifications = []
    for med_comp in reconciliation_result.medication_comparisons:
        trust_a = derive_trust_level(med_comp.source_a, med_comp.source_record_id_a, origins)
        trust_b = derive_trust_level(med_comp.source_b, med_comp.source_record_id_b, origins)
        verification = _verify_medication(med_comp, trust_a, trust_b)
        med_verifications.append(verification)

    summary = {
        "auto_resolved": 0,
        "requires_review": 0,
        "severity_none": 0,
        "severity_low": 0,
        "severity_moderate": 0,
        "severity_high": 0,
    }

    for v in obs_verifications + med_verifications:
        if v.requires_human_review:
            summary["requires_review"] += 1
        else:
            summary["auto_resolved"] += 1

        if v.severity == "none":
            summary["severity_none"] += 1
        elif v.severity == "low":
            summary["severity_low"] += 1
        elif v.severity == "moderate":
            summary["severity_moderate"] += 1
        elif v.severity == "high":
            summary["severity_high"] += 1

    return VerificationResult(
        patient_id=reconciliation_result.patient_id,
        observation_verifications=obs_verifications,
        medication_verifications=med_verifications,
        summary=summary
    )
