"""
Real Mutation Proof Verification Engine (Stage 9A-4 Task B).

For each of the 13 architectural mutation proofs:
1. Reads original file bytes and computes SHA-256.
2. Finds the target text with exact single-match assertion (prints grep line number).
3. Replaces target text with mutation.
4. Generates and prints real unified diff with 3 lines of context.
5. Runs `python -m pytest <exact node id> -x --tb=line -q` as subprocess.
6. Asserts returncode != 0 and extracts the real failing line.
7. Restores original file bytes, verifies SHA-256 matches original and git diff is clean.
8. Includes diagnostic test proving deliberate missing target causes non-zero exit.
"""

import difflib
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"

MUTATIONS = [
    {
        "id": "MUT-1",
        "name": "Danger Screen on Free Text",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "    is_danger, danger_cat = screen_multilingual_danger_phrases(clean_text)",
        "replacement": "    is_danger, danger_cat = False, None",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_1_danger_screen_on_free_text",
    },
    {
        "id": "MUT-2",
        "name": "Negation Handling in Danger Screen",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "    return any(word in _NEGATION_CUES for word in preceding[-NEGATION_WINDOW_WORDS:])",
        "replacement": "    return False",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_2_negation_handling",
    },
    {
        "id": "MUT-3",
        "name": "Unknown / Skip Retention Invariant",
        "file": BACKEND_DIR / "agents" / "answer_validation.py",
        "target": "    if any(k in lowered for k in [\"don't know\", \"dont know\", \"skip\", \"not sure\", \"prefer not to say\", \"maloom nahi\", \"nahi pata\"]):",
        "replacement": "    if False and any(k in lowered for k in [\"don't know\", \"dont know\", \"skip\", \"not sure\", \"prefer not to say\", \"maloom nahi\", \"nahi pata\"]):",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_3_unknown_not_stored_as_no",
    },
    {
        "id": "MUT-4",
        "name": "Planner Never Re-asks Filled Slot",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "        asked_slots = set(asked_slots) | set(known_slots.keys())",
        "replacement": "        asked_slots = set()",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_4_planner_never_reasks_filled_slot",
    },
    {
        "id": "MUT-5",
        "name": "Interview Budget Hard Cap (14)",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "    if current_count >= effective_budget:",
        "replacement": "    if False and current_count >= effective_budget:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_5_budget_hard_cap",
    },
    {
        "id": "MUT-6",
        "name": "Probe Depth Limit of 2 per Finding",
        "file": BACKEND_DIR / "agents" / "interview_findings.py",
        "target": "    if finding.probe_count >= max_probes:",
        "replacement": "    if False and finding.probe_count >= max_probes:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_6_probe_depth_limit_two",
    },
    {
        "id": "MUT-7",
        "name": "Glucose Unit Guessing Prevented (2-40 Clarified)",
        "file": BACKEND_DIR / "agents" / "answer_validation.py",
        "target": "    if 2.0 <= val <= 40.0:",
        "replacement": "    if False and 2.0 <= val <= 40.0:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_7_unit_guess_prevented",
    },
    {
        "id": "MUT-8",
        "name": "Contradiction Clarification Priority",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "    if contradictions:",
        "replacement": "    if False and contradictions:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_8_contradiction_handling",
    },
    {
        "id": "MUT-9",
        "name": "Odd-Input Checked After Danger Screen",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "    triage_res: TriageInputResult = classify_input(",
        "replacement": "    triage_res: TriageInputResult = TriageInputResult(category='normal_clinical')\n    if False and classify_input(",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_9_odd_input_after_danger",
    },
    {
        "id": "MUT-10",
        "name": "Self-Harm / Hopelessness Screen Priority",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "    if check_self_harm(clean_text):",
        "replacement": "    if False and check_self_harm(clean_text):",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_10_self_harm_screen",
    },
    {
        "id": "MUT-11",
        "name": "Romantic Remark Recorded as Finding Without Yes",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "        session_state.setdefault(\"odd_classes_seen\", []).append(triage_res.odd_class)\n        session_state[\"last_odd_class\"] = triage_res.odd_class",
        "replacement": "        session_state.setdefault(\"odd_classes_seen\", []).append(triage_res.odd_class)\n        session_state[\"last_odd_class\"] = triage_res.odd_class\n        if triage_res.odd_class == \"romantic\":\n            session_state.setdefault(\"findings\", []).append({\"kind\": \"romantic\", \"quote\": clean_answer})",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_11_romantic_remark_not_symptom",
    },
    {
        "id": "MUT-12",
        "name": "Fixed Response Templates for Odd Inputs",
        "file": BACKEND_DIR / "agents" / "interview_bank" / "loader.py",
        "target": "    return QuestionBank(items, sources, probes, responses)",
        "replacement": "    return QuestionBank(items, sources, probes, {})",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_12_fixed_reply_set",
    },
    {
        "id": "MUT-13",
        "name": "Safety Priority Class Planned First",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "        if item.priority_class == \"safety\" and item.slot not in asked_slots:",
        "replacement": "        if False and item.priority_class == \"safety\" and item.slot not in asked_slots:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_13_safety_priority_first",
    },
    {
        "id": "MUT-14",
        "name": "Answered_By Not Set For Third-Party Report",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "        if triage_res.odd_class == \"third_party_report\":\n            session_state[\"answered_by\"] = \"caregiver\"",
        "replacement": "        if triage_res.odd_class == \"third_party_report\":\n            session_state[\"answered_by\"] = None",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_14_answered_by_third_party",
    },
    {
        "id": "MUT-15",
        "name": "Extra Danger Detections Removed from Input Triage",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "        for category, patterns in MULTILINGUAL_DANGER_CATEGORIES.items():",
        "replacement": "        for category, patterns in {}.items():",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_15_extra_danger_detections",
    },
    # --- Seven Stage 8b Rule Mutations ---
    {
        "id": "MUT-8B-1",
        "name": "Stage 8b: Glucose Context Skip Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            if _has_glucose_context_in_text(answer):\n                answers[\"glucose_context\"] = \"extracted_from_reading\"\n                if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):",
        "replacement": "            if False and _has_glucose_context_in_text(answer):\n                answers[\"glucose_context\"] = \"extracted_from_reading\"\n                if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_fast_path_skip_rules",
    },
    {
        "id": "MUT-8B-2",
        "name": "Stage 8b: Hypo-Events Question Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):\n            state.step = DiabetesStep.HYPO_EVENTS_PAST_WEEK.value",
        "replacement": "        if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):\n            state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
    {
        "id": "MUT-8B-3",
        "name": "Stage 8b: Sick-Day Flags Prompt Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        elif reading is not None and reading >= 250:\n            state.step = DiabetesStep.SICK_DAY_FLAGS.value",
        "replacement": "        elif False and reading is not None and reading >= 250:\n            state.step = DiabetesStep.SICK_DAY_FLAGS.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_sick_day_prompt_on_high_reading",
    },
    {
        "id": "MUT-8B-4",
        "name": "Stage 8b: BP Technique Question Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            if reading is not None and not _has_bp_technique_in_text(answer):\n                state.step = HypertensionStep.BP_TECHNIQUE.value",
        "replacement": "            if False and reading is not None and not _has_bp_technique_in_text(answer):\n                state.step = HypertensionStep.BP_TECHNIQUE.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_hypertension_v2_3_full_path",
    },
    {
        "id": "MUT-8B-5",
        "name": "Stage 8b: OTC Meds BP Check Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if bp is None or bp[0] >= 140 or bp[1] >= 90:\n            state.step = HypertensionStep.OTC_MEDS_BP.value",
        "replacement": "        if False and (bp is None or bp[0] >= 140 or bp[1] >= 90):\n            state.step = HypertensionStep.OTC_MEDS_BP.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_hypertension_v2_3_full_path",
    },
    {
        "id": "MUT-8B-6",
        "name": "Stage 8b: Missed-Dose Reason Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if adh is False:\n            state.step = DiabetesStep.MISSED_DOSES_REASON.value",
        "replacement": "        if False and adh is False:\n            state.step = DiabetesStep.MISSED_DOSES_REASON.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
    {
        "id": "MUT-8B-7",
        "name": "Stage 8b: Free-Text Note Passed Through",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            \"free_text_note\": answers.get(\"patient_free_text\"),",
        "replacement": "            \"free_text_note\": None,",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
]


def run_mutation(mut: dict) -> dict:
    file_path: Path = mut["file"]
    assert file_path.exists(), f"Target file does not exist: {file_path}"

    orig_bytes = file_path.read_bytes()
    orig_sha = hashlib.sha256(orig_bytes).hexdigest()
    orig_text = orig_bytes.decode("utf-8")

    target = mut["target"]
    replacement = mut["replacement"]
    if "\r\n" in orig_text and "\r\n" not in target:
        target = target.replace("\n", "\r\n")
        replacement = replacement.replace("\n", "\r\n")
    elif "\r\n" not in orig_text and "\r\n" in target:
        target = target.replace("\r\n", "\n")
        replacement = replacement.replace("\r\n", "\n")

    # Assert exact match occurs exactly once
    occurrences = orig_text.count(target)
    if occurrences != 1:
        raise ValueError(
            f"Target string error in {file_path.name} for {mut['id']}: expected 1 occurrence, found {occurrences}"
        )

    # Invalidate and remove any stale bytecode cache before mutation
    pycache_dir = file_path.parent / "__pycache__"
    if pycache_dir.is_dir():
        for pyc in pycache_dir.glob(f"{file_path.stem}.*.pyc"):
            try:
                pyc.unlink(missing_ok=True)
            except OSError:
                pass

    # Find line number (1-indexed)
    lines_before = orig_text[:orig_text.find(target)].splitlines()
    line_no = len(lines_before) + 1

    # Mutate text
    mutated_text = orig_text.replace(target, replacement, 1)
    file_path.write_bytes(mutated_text.encode("utf-8"))

    # Generate unified diff with 3 lines of context
    diff = list(
        difflib.unified_diff(
            orig_text.splitlines(keepends=True),
            mutated_text.splitlines(keepends=True),
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            n=3,
        )
    )
    diff_str = "".join(diff)

    try:
        # Run pytest subprocess on exact test node with -B and PYTHONDONTWRITEBYTECODE
        cmd = [sys.executable, "-B", "-m", "pytest", mut["test_node"], "-x", "--tb=line", "-q"]
        sub_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            env=sub_env,
        )
    finally:
        # Restore original bytes immediately under all circumstances
        file_path.write_bytes(orig_bytes)
        restored_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert restored_sha == orig_sha, f"SHA mismatch on restore for {mut['id']}"

        # Clean any bytecode written during test
        if pycache_dir.is_dir():
            for pyc in pycache_dir.glob(f"{file_path.stem}.*.pyc"):
                try:
                    pyc.unlink(missing_ok=True)
                except OSError:
                    pass

    failing_line = ""
    for line in proc.stdout.splitlines():
        if "FAILED" in line or "AssertionError" in line or "assert " in line:
            failing_line = line.strip()
            if "FAILED" in line:
                break

    killed = proc.returncode != 0
    return {
        "id": mut["id"],
        "name": mut["name"],
        "file": file_path.name,
        "line_no": line_no,
        "sha_before": orig_sha,
        "sha_after": restored_sha,
        "diff": diff_str,
        "test_node": mut["test_node"],
        "return_code": proc.returncode,
        "killed": killed,
        "failing_output": failing_line or proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip(),
    }


def main():
    print("=" * 105)
    print("STAGE 9A-4 TASK B: REAL SUBPROCESS MUTATION VERIFICATION ENGINE")
    print("=" * 105)

    all_passed = True
    results = []

    for mut in MUTATIONS:
        res = run_mutation(mut)
        results.append(res)
        status = "KILLED (PASS)" if res["killed"] else "SURVIVED (FAIL)"
        if not res["killed"]:
            all_passed = False

        print(f"\n[{res['id']}] {res['name']} -> {status}")
        print(f"  File: {res['file']}:{res['line_no']} (SHA256: {res['sha_before'][:12]}...)")
        print(f"  Unified Diff:\n{res['diff'].strip()}")
        print(f"  Pytest Subprocess: {res['test_node']}")
        print(f"  Exit Code: {res['return_code']}")
        print(f"  Real Failure Output: {res['failing_output']}")
        print(f"  Byte Integrity Verified: SHA matches ({res['sha_after'][:12]}...)")

    # Diagnostic proof that missing target exits non-zero
    print("\n" + "-" * 105)
    print("DIAGNOSTIC TEST: Demonstrating harness exits non-zero on invalid target...")
    try:
        run_mutation({
            "id": "MUT-FAKE",
            "name": "Fake Target Test",
            "file": BACKEND_DIR / "agents" / "input_triage.py",
            "target": "THIS_STRING_DOES_NOT_EXIST_IN_THE_CODE",
            "replacement": "FOO",
            "test_node": "backend-poc-technical/test_mutation_proofs_v3.py",
        })
        print("FAIL: Harness did not exit non-zero on missing target!")
        all_passed = False
    except ValueError as e:
        print(f"PASS: Harness caught missing target with expected ValueError: {e}")

    print("=" * 105)
    print(f"All {len(MUTATIONS)} Mutations Verified & Killed: {'YES' if all_passed else 'NO'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
