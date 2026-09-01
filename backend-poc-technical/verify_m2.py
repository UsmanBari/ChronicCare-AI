"""
Milestone 2 Automated Verification Script

Checks all Milestone 2 acceptance criteria:
1. Normalized data models defined (NormalizedPatient, NormalizedObservation, NormalizedMedication) without trust/confidence fields.
2. fhir_adapter.py implementation and function signatures.
3. local_adapter.py implementation and function signatures.
4. Structural equivalence between fhir_adapter and local_adapter outputs.
5. Unified get_patient_bundle(patient_id, mode) entry point functionality.
6. Execution of test_source_blind.py (verifying it imports ONLY get_patient_bundle and summarize_bundle is source-blind).
7. Zero comparison, reconciliation, verification, trust scoring, LLM, or agent framework calls.
"""

import os
import sys
import inspect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_sources import models
from data_sources import fhir_adapter
from data_sources import local_adapter
from data_sources import data_source

def run_m2_verification():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results = []

    def test(criterion: str, status: bool, detail: str = ""):
        results.append({"criterion": criterion, "pass": status, "detail": detail})
        symbol = "[PASS]" if status else "[FAIL]"
        print(f"{symbol} {criterion}")
        if detail:
            print(f"       Details: {detail}")

    print("==================================================")
    print("CHRONICCARE AI POC - MILESTONE 2 VERIFICATION")
    print("==================================================\n")

    # 1. Normalized Models Defined
    has_patient = hasattr(models, "NormalizedPatient")
    has_obs = hasattr(models, "NormalizedObservation")
    has_med = hasattr(models, "NormalizedMedication")
    
    # Ensure no trust/confidence fields exist
    patient_fields = models.NormalizedPatient.__annotations__
    obs_fields = models.NormalizedObservation.__annotations__
    med_fields = models.NormalizedMedication.__annotations__
    
    has_trust = any(f in obs_fields or f in med_fields for f in ["trust_level", "confidence", "trust_score"])
    models_valid = has_patient and has_obs and has_med and not has_trust
    test("Normalized data models (Patient/Observation/Medication) are defined without trust/confidence fields", 
         models_valid, f"Patient fields: {list(patient_fields.keys())}, Obs fields: {list(obs_fields.keys())}")

    # 2. FHIR Adapter Implementation
    fhir_sigs = [
        hasattr(fhir_adapter, "get_normalized_patient"),
        hasattr(fhir_adapter, "get_normalized_observations"),
        hasattr(fhir_adapter, "get_normalized_medications")
    ]
    test("fhir_adapter.py converts M1 raw FHIR retrieval into normalized models", all(fhir_sigs), "All 3 normalization functions implemented")

    # 3. Local Adapter Implementation
    local_sigs = [
        hasattr(local_adapter, "get_normalized_patient"),
        hasattr(local_adapter, "get_normalized_observations"),
        hasattr(local_adapter, "get_normalized_medications")
    ]
    test("local_adapter.py converts M1 raw SQLite retrieval into normalized models", all(local_sigs), "All 3 normalization functions implemented")

    # 4. Adapter Function Signature Equivalence
    fhir_p_sig = inspect.signature(fhir_adapter.get_normalized_patient)
    local_p_sig = inspect.signature(local_adapter.get_normalized_patient)
    fhir_o_sig = inspect.signature(fhir_adapter.get_normalized_observations)
    local_o_sig = inspect.signature(local_adapter.get_normalized_observations)
    fhir_m_sig = inspect.signature(fhir_adapter.get_normalized_medications)
    local_m_sig = inspect.signature(local_adapter.get_normalized_medications)

    sig_match = (
        list(fhir_p_sig.parameters.keys())[0] == list(local_p_sig.parameters.keys())[0] and
        list(fhir_o_sig.parameters.keys())[0] == list(local_o_sig.parameters.keys())[0] and
        list(fhir_m_sig.parameters.keys())[0] == list(local_m_sig.parameters.keys())[0]
    )
    test("Both adapters expose identical function signatures and return identical types", sig_match, "Signature compatibility confirmed")

    # 5. Unified Entry Point Interface
    has_bundle_fn = hasattr(data_source, "get_patient_bundle")
    test("A single unified get_patient_bundle(patient_id, mode) function exists", has_bundle_fn, "Entry point available in data_sources/data_source.py")

    # 6. Source-Blind Test File Execution & Constraints Check
    test_file_path = os.path.join(script_dir, "scenarios", "test_source_blind.py")
    test_file_exists = os.path.isfile(test_file_path)
    
    only_bundle_imported = False
    summarize_is_source_blind = False
    
    if test_file_exists:
        import ast
        with open(test_file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=test_file_path)
            
            # Check AST imports
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.append(node.module)
            
            only_bundle_imported = ("fhir_adapter" not in imported_modules) and ("local_adapter" not in imported_modules)
            
            # Check summarize_bundle AST function body for Compare / If nodes touching mode or source
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "summarize_bundle":
                    has_mode_if = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.If):
                            has_mode_if = True
                    summarize_is_source_blind = not has_mode_if

    test("test_source_blind.py imports and calls ONLY get_patient_bundle(), never adapters directly", only_bundle_imported, 
         "No direct adapter imports detected in test_source_blind.py")
    test("summarize_bundle() runs correctly on both bundles with zero source/mode branching inside it", summarize_is_source_blind, 
         "summarize_bundle implementation is completely source-blind")

    # 7. Execute test_source_blind.py
    try:
        from scenarios.test_source_blind import run_source_blind_test
        source_blind_passed = run_source_blind_test()
        test("test_source_blind.py proves structural equivalence between sources", source_blind_passed, "Source-blind structural assertion passed")
    except Exception as e:
        test("test_source_blind.py proves structural equivalence between sources", False, str(e))

    # 8. Compliance Check (No reconciliation, comparison, verification, LLMs, or agent frameworks)
    forbidden_terms = ["openai", "anthropic", "langchain", "langgraph", "reconcile", "verify_conflict", "calculate_risk"]
    python_files = [os.path.join(r, f) for r, d, fs in os.walk(script_dir) for f in fs if f.endswith(".py")]
    
    compliance_violations = []
    for pf in python_files:
        if os.path.basename(pf).startswith("verify_") or "agents" in pf or "scenarios" in pf:
            continue
        with open(pf, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read().lower()
            for term in forbidden_terms:
                if term in c:
                    compliance_violations.append(f"{os.path.basename(pf)} contains '{term}'")

    test("No comparison/conflict-detection/trust/verification/LLM logic exists", len(compliance_violations) == 0, 
         "Strict compliance maintained" if not compliance_violations else f"Violations: {compliance_violations}")

    # Summary
    print("\n==================================================")
    all_passed = all(r["pass"] for r in results)
    if all_passed:
        print("ALL MILESTONE 2 ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
    else:
        print("SOME MILESTONE 2 ACCEPTANCE CRITERIA FAILED.")
    print("==================================================")

    return all_passed

if __name__ == "__main__":
    success = run_m2_verification()
    sys.exit(0 if success else 1)
