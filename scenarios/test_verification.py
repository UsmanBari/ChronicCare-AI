"""
Verification Agent Acceptance Test Script (Milestone 4)

Executes end-to-end reconciliation and verification pipeline:
  reconcile_bundles() -> verify_reconciliation()

Tests against synthetic paired test fixtures:
- Clean Agree Pair (Trusted sources -> auto-resolved)
- Conflict Pair (Far-over-threshold delta & active vs stopped med -> high severity)
- Missing Data Pair (High-trust present side -> auto-resolved; Medium-trust -> requires review)
- Insufficient Data Pair (Unusable measurement -> moderate severity, requires review)
- Negative Control Pair (100% agreement, high trust -> auto-resolved, severity none)
- Near-Threshold Conflict Pair (1x-2x threshold delta -> moderate severity, requires review)
- Low-Trust Agree Pair (Self-reported both sides -> low severity, requires review)

Asserts provenance preservation and trust_level == None on missing side.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.reconciliation_agent import reconcile_bundles
from agents.verification_agent import verify_reconciliation, TRUST_LEVELS
from scenarios.fixtures import (
    CLEAN_AGREE_PAIR,
    CONFLICT_PAIR,
    MISSING_DATA_PAIR,
    INSUFFICIENT_DATA_PAIR,
    NEGATIVE_CONTROL_PAIR,
    NEAR_THRESHOLD_CONFLICT_PAIR,
    LOW_TRUST_AGREE_PAIR,
    ALL_FIXTURE_PAIRS,
    FIXTURE_ORIGINS
)

def print_verification_summary(fixture_name: str, v_res):
    print(f"\n==================================================")
    print(f"FIXTURE: {fixture_name} (Patient ID: {v_res.patient_id})")
    print(f"==================================================")
    print(f"Verification Summary: {v_res.summary}")

    print("\n--- Observation Verifications ---")
    for o in v_res.observation_verifications:
        review_tag = "REVIEW_REQUIRED" if o.requires_human_review else "AUTO_RESOLVED"
        trust_str = f"Trust A: {o.trust_level_a} ({o.source_a}:{o.source_record_id_a}) vs Trust B: {o.trust_level_b} ({o.source_b}:{o.source_record_id_b})"
        print(f"  • [{review_tag:<15}] [{o.severity.upper():<8}] {o.observation_type:<25} (Recon: {o.reconciliation_status}) | {trust_str}")
        print(f"    Reason: {o.review_reason}")

    print("\n--- Medication Verifications ---")
    for m in v_res.medication_verifications:
        review_tag = "REVIEW_REQUIRED" if m.requires_human_review else "AUTO_RESOLVED"
        trust_str = f"Trust A: {m.trust_level_a} ({m.source_a}:{m.source_record_id_a}) vs Trust B: {m.trust_level_b} ({m.source_b}:{m.source_record_id_b})"
        print(f"  • [{review_tag:<15}] [{m.severity.upper():<8}] {m.medication_name:<25} (Recon: {m.reconciliation_status}) | {trust_str}")
        print(f"    Reason: {m.review_reason}")

def run_verification_tests():
    print("==================================================")
    print("CHRONICCARE AI POC - MILESTONE 4 VERIFICATION TESTS")
    print("==================================================")

    # 1. Run Pipeline End-to-End for All Fixture Pairs
    for fixture in ALL_FIXTURE_PAIRS:
        name = fixture["name"]
        recon_res = reconcile_bundles(fixture["bundle_a"], fixture["bundle_b"])
        v_res = verify_reconciliation(recon_res, origins=FIXTURE_ORIGINS)
        print_verification_summary(name, v_res)

        # Assert Provenance & Missing-Side Trust Nullability
        for o in v_res.observation_verifications:
            if o.source_a is None:
                assert o.trust_level_a is None, f"Expected trust_level_a to be None when source_a is None for {o}"
            else:
                assert o.source_record_id_a is not None and o.trust_level_a is not None

            if o.source_b is None:
                assert o.trust_level_b is None, f"Expected trust_level_b to be None when source_b is None for {o}"
            else:
                assert o.source_record_id_b is not None and o.trust_level_b is not None

        for m in v_res.medication_verifications:
            if m.source_a is None:
                assert m.trust_level_a is None
            else:
                assert m.source_record_id_a is not None and m.trust_level_a is not None

            if m.source_b is None:
                assert m.trust_level_b is None
            else:
                assert m.source_record_id_b is not None and m.trust_level_b is not None

    # 2. Specific Assertions & Key Checks
    print("\n--------------------------------------------------")
    print("EXECUTING MILESTONE 4 SPECIFIC ASSERTIONS")
    print("--------------------------------------------------")

    # Check 1: Negative Control Fixture (All agree, high trust both sides)
    # Must produce requires_human_review = False for all comparisons (severity "none")
    print("Check 1: Negative Control Auto-Resolution Check...")
    r_neg = reconcile_bundles(NEGATIVE_CONTROL_PAIR["bundle_a"], NEGATIVE_CONTROL_PAIR["bundle_b"])
    v_neg = verify_reconciliation(r_neg, origins=FIXTURE_ORIGINS)
    assert v_neg.summary["requires_review"] == 0, f"Negative control should have 0 requires_review, got {v_neg.summary['requires_review']}"
    assert v_neg.summary["auto_resolved"] == 3, f"Negative control should have 3 auto_resolved, got {v_neg.summary['auto_resolved']}"
    assert all(o.severity == "none" and not o.requires_human_review for o in v_neg.observation_verifications)
    assert all(m.severity == "none" and not m.requires_human_review for m in v_neg.medication_verifications)
    print("[PASS] Negative control produces 0 requires_human_review (100% auto-resolved, severity 'none').")

    # Check 2: High-Trust Missing Data Case
    # High-trust present side (FHIR) with missing local data -> severity "low", requires_human_review = False
    print("Check 2: High-Trust Missing Data Auto-Resolution Check...")
    r_missing = reconcile_bundles(MISSING_DATA_PAIR["bundle_a"], MISSING_DATA_PAIR["bundle_b"])
    v_missing = verify_reconciliation(r_missing, origins=FIXTURE_ORIGINS)
    
    # Weight is in FHIR (high trust), missing in Local
    weight_v = [o for o in v_missing.observation_verifications if o.observation_type == "weight"][0]
    assert weight_v.reconciliation_status == "missing_in_b"
    assert weight_v.trust_level_a == "high" and weight_v.trust_level_b is None
    assert weight_v.severity == "low", f"Expected severity 'low' for high-trust missing data, got {weight_v.severity}"
    assert weight_v.requires_human_review is False, "High-trust missing data must have requires_human_review = False"

    # HbA1c is in Local (medium trust), missing in FHIR -> moderate severity, requires_human_review = True
    hba1c_v = [o for o in v_missing.observation_verifications if o.observation_type == "hba1c"][0]
    assert hba1c_v.reconciliation_status == "missing_in_a"
    assert hba1c_v.trust_level_b == "medium" and hba1c_v.trust_level_a is None
    assert hba1c_v.severity == "moderate" and hba1c_v.requires_human_review is True
    print("[PASS] High-trust missing data case demonstrates genuine auto-resolution (severity 'low', requires_human_review = False).")

    # Check 3: Near-Threshold Conflict Fixture (1x-2x threshold)
    # Must classify as "moderate" specifically, proving severity is threshold-derived
    print("Check 3: Near-Threshold Conflict Classification Check...")
    r_near = reconcile_bundles(NEAR_THRESHOLD_CONFLICT_PAIR["bundle_a"], NEAR_THRESHOLD_CONFLICT_PAIR["bundle_b"])
    v_near = verify_reconciliation(r_near, origins=FIXTURE_ORIGINS)
    glucose_near = v_near.observation_verifications[0]
    assert glucose_near.reconciliation_status == "conflict"
    assert glucose_near.severity == "moderate", f"Expected 'moderate' severity for 1x-2x threshold conflict, got '{glucose_near.severity}'"
    assert glucose_near.requires_human_review is True
    print("[PASS] Near-threshold conflict fixture correctly classified as 'moderate' (distinct from >2x 'high' conflict).")

    # Additional Check 4: Far-over-threshold Conflict (Conflict Pair)
    print("Check 4: Far-Over-Threshold & Active vs Stopped Conflict Check...")
    r_conf = reconcile_bundles(CONFLICT_PAIR["bundle_a"], CONFLICT_PAIR["bundle_b"])
    v_conf = verify_reconciliation(r_conf, origins=FIXTURE_ORIGINS)
    glucose_conf = [o for o in v_conf.observation_verifications if o.observation_type == "glucose"][0]
    assert glucose_conf.severity == "high", f"Expected 'high' severity for delta 55 > 2x15=30, got {glucose_conf.severity}"
    
    med_conf = v_conf.medication_verifications[0]
    assert med_conf.severity == "high" and "active vs stopped" in med_conf.review_reason
    print("[PASS] Far-over-threshold conflict & active vs. stopped med conflict correctly classified as 'high' severity.")

    # Additional Check 5: Low-Trust Agreement Rule (Rule 1 low-trust case)
    print("Check 5: Low-Trust Agreement Rule Check...")
    r_low = reconcile_bundles(LOW_TRUST_AGREE_PAIR["bundle_a"], LOW_TRUST_AGREE_PAIR["bundle_b"])
    v_low = verify_reconciliation(r_low, origins=FIXTURE_ORIGINS)
    glucose_low = v_low.observation_verifications[0]
    assert glucose_low.reconciliation_status == "agree"
    assert glucose_low.trust_level_a == "low" and glucose_low.trust_level_b == "low"
    assert glucose_low.severity == "low", f"Expected severity 'low' for low-trust agreement, got {glucose_low.severity}"
    assert glucose_low.requires_human_review is True, "Low-trust agreement MUST require human review"
    print("[PASS] Low-trust agreement correctly requires human review (severity 'low', requires_human_review = True).")

    print("\n==================================================")
    print("ALL VERIFICATION FIXTURE AND SPECIFIC CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")
    return True

if __name__ == "__main__":
    run_verification_tests()
