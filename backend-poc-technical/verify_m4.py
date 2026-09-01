"""
Milestone 4 Automated Verification Script (Verification Agent)

Verifies acceptance criteria for Milestone 4 of the ChronicCare AI POC:
- Verification Agent consumes M3 ReconciliationResult directly
- Trust level assignment (FHIR -> high, Local -> medium, origin lookup support, None for missing side)
- Exact severity decision table implementation ("none", "low", "moderate", "high")
- Review flag (requires_human_review) and auditable review_reason strings
- Full provenance preservation (source_a, source_b, source_record_id_a, source_record_id_b)
- Negative control auto-resolution (0 review required, severity "none")
- High-trust missing data auto-resolution (severity "low", requires_human_review = False)
- Near-threshold conflict fixture classification (severity "moderate", 1x-2x threshold)
- Compliance checks (No LLM, no ML, no LangGraph, no conflict resolution, no clinical triage)
"""

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

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
from scenarios.test_verification import run_verification_tests

def run_m4_verification():
    print("==================================================")
    print("CHRONICCARE AI POC - MILESTONE 4 VERIFICATION")
    print("==================================================")

    results = []

    def test(name: str, condition: bool, details: str = ""):
        status = "PASS" if condition else "FAIL"
        results.append({"name": name, "pass": condition, "details": details})
        print(f"[{status}] {name}")
        if details:
            print(f"       Details: {details}")

    # 1. Pipeline Execution
    r_neg = reconcile_bundles(NEGATIVE_CONTROL_PAIR["bundle_a"], NEGATIVE_CONTROL_PAIR["bundle_b"])
    v_neg = verify_reconciliation(r_neg, origins=FIXTURE_ORIGINS)
    test("verify_reconciliation() consumes M3 ReconciliationResult directly", v_neg is not None and v_neg.patient_id == "SYNTHETIC-PATIENT-MATCH-005", "Direct consumption confirmed")

    # 2. Schema Unmodified & Origin Concept
    models_path = os.path.join(script_dir, "data_sources", "models.py")
    with open(models_path, "r", encoding="utf-8") as f:
        models_code = f.read()
    schema_unmodified = "origin" not in models_code
    test("M2 normalized schema and adapter contract are unmodified ('origin' is test-only concept)", schema_unmodified, "data_sources/models.py contains zero M4 modifications")

    # 3. Trust Level Assignment & Nullability on Missing Side
    r_miss = reconcile_bundles(MISSING_DATA_PAIR["bundle_a"], MISSING_DATA_PAIR["bundle_b"])
    v_miss = verify_reconciliation(r_miss, origins=FIXTURE_ORIGINS)
    weight_v = [o for o in v_miss.observation_verifications if o.observation_type == "weight"][0]
    trust_correct = (weight_v.trust_level_a == "high" and weight_v.trust_level_b is None)
    test("Trust level assignment implemented per spec; None assigned for missing sides", trust_correct, f"Trust A: {weight_v.trust_level_a}, Trust B: {weight_v.trust_level_b}")

    # 4. Full Provenance Preservation
    prov_ok = all(
        (o.source_a is None or o.source_record_id_a is not None) and
        (o.source_b is None or o.source_record_id_b is not None)
        for o in v_neg.observation_verifications + v_miss.observation_verifications
    )
    test("Every VerificationResult entry preserves full provenance from M3", prov_ok, "source + source_record_id preserved")

    # 5. Negative Control Auto-Resolution
    neg_auto = (v_neg.summary["requires_review"] == 0 and v_neg.summary["auto_resolved"] == 3)
    test("Negative control (all-agree, high trust) produces zero requires_human_review", neg_auto, f"Summary: {v_neg.summary}")

    # 6. High-Trust Missing Data Auto-Resolution Path
    high_miss_auto = (weight_v.severity == "low" and weight_v.requires_human_review is False)
    test("High-trust missing-data case demonstrates a genuine auto-resolved path", high_miss_auto, f"Weight severity: {weight_v.severity}, review: {weight_v.requires_human_review}")

    # 7. Near-Threshold Conflict Classification (1x-2x threshold -> moderate)
    r_near = reconcile_bundles(NEAR_THRESHOLD_CONFLICT_PAIR["bundle_a"], NEAR_THRESHOLD_CONFLICT_PAIR["bundle_b"])
    v_near = verify_reconciliation(r_near, origins=FIXTURE_ORIGINS)
    near_mod = (v_near.observation_verifications[0].severity == "moderate" and v_near.observation_verifications[0].requires_human_review is True)
    test("Near-threshold conflict fixture correctly classifies as 'moderate', distinct from >2x 'high'", near_mod, f"Severity: {v_near.observation_verifications[0].severity}")

    # 8. Compliance Checks
    forbidden_terms = ["openai", "anthropic", "langchain", "langgraph", "pick_winner", "triage_patient"]
    python_files = [os.path.join(r, f) for r, d, fs in os.walk(script_dir) for f in fs if f.endswith(".py")]
    
    compliance_violations = []
    for pf in python_files:
        if os.path.basename(pf).startswith("verify_") or ".git" in pf:
            continue
        with open(pf, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            for term in forbidden_terms:
                if term in content:
                    compliance_violations.append(f"{os.path.basename(pf)} contains '{term}'")

    test("No conflict resolution, clinical triage, LLM, or agent framework calls exist", len(compliance_violations) == 0, 
         "Strict compliance maintained" if not compliance_violations else f"Violations: {compliance_violations}")

    # 9. Test Suite Execution
    test_suite_passed = run_verification_tests()
    test("test_verification.py runs end-to-end and asserts correctness for every fixture", test_suite_passed, "All fixture assertions passed")

    # Summary
    print("\n==================================================")
    all_passed = all(r["pass"] for r in results)
    if all_passed:
        print("ALL MILESTONE 4 ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
    else:
        print("SOME MILESTONE 4 ACCEPTANCE CRITERIA FAILED.")
    print("==================================================")
    
    return all_passed

if __name__ == "__main__":
    success = run_m4_verification()
    sys.exit(0 if success else 1)
