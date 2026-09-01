"""
Agents package initializer for ChronicCare AI.
Exports Reconciliation Agent and Verification Agent functions and dataclasses.
"""

from agents.reconciliation_agent import (
    reconcile_bundles,
    ReconciliationResult,
    ObservationComparison,
    MedicationComparison,
    OBSERVATION_MATCH_WINDOW_HOURS,
    OBSERVATION_CONFLICT_THRESHOLDS
)

from agents.verification_agent import (
    verify_reconciliation,
    VerificationResult,
    ObservationVerification,
    MedicationVerification,
    TRUST_LEVELS,
    derive_trust_level
)

__all__ = [
    "reconcile_bundles",
    "ReconciliationResult",
    "ObservationComparison",
    "MedicationComparison",
    "OBSERVATION_MATCH_WINDOW_HOURS",
    "OBSERVATION_CONFLICT_THRESHOLDS",
    "verify_reconciliation",
    "VerificationResult",
    "ObservationVerification",
    "MedicationVerification",
    "TRUST_LEVELS",
    "derive_trust_level"
]
