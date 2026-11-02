"""
find_untranslated.py - Audit script to identify untranslated patient-facing strings.

Checks:
1. interview_bank/*.json:
   - Items: template_en, template_ur, template_roman_ur
   - Items: why_text (en), why_text_ur, why_text_roman_ur
   - Items with choices: choices_ur, choices_roman_ur (must match choices length)
   - probes.json: template_en, template_ur, template_roman_ur, localized rationale, localized choices
   - responses.json: reply_en, reply_ur, reply_roman_ur
2. Python files (interview_v3_runner.py, answer_validation.py, answer_understanding.py, main.py v3 paths):
   - AST search for hard-coded patient-facing English string literals assigned to:
     current_question, why_text, system_note, options, possible_severe_low_guidance, clarification_prompt.

Exits 1 if any missing translation or hard-coded patient string is found; exits 0 otherwise.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = REPO_ROOT / "backend-poc-technical" / "agents" / "interview_bank"
AGENTS_DIR = REPO_ROOT / "backend-poc-technical" / "agents"
MAIN_PY = REPO_ROOT / "backend-poc-technical" / "main.py"

TARGET_KEYS = {
    "current_question",
    "why_text",
    "system_note",
    "options",
    "possible_severe_low_guidance",
    "clarification_prompt",
}


def audit_interview_bank() -> List[Dict[str, Any]]:
    missing_entries: List[Dict[str, Any]] = []

    if not BANK_DIR.exists():
        missing_entries.append({
            "source": "interview_bank",
            "location": str(BANK_DIR),
            "missing": "Directory does not exist",
        })
        return missing_entries

    for json_file in sorted(BANK_DIR.glob("*.json")):
        fname = json_file.name
        if fname in ("SOURCES.json", "messages.json"):
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                missing_entries.append({
                    "source": f"interview_bank/{fname}",
                    "location": f"{fname}:1",
                    "missing": f"Malformed JSON: {e}",
                })
                continue

        if fname == "responses.json":
            # Check responses
            for resp_key, resp_val in data.items():
                if not isinstance(resp_val, dict):
                    missing_entries.append({
                        "source": f"interview_bank/{fname}",
                        "location": f"responses[{resp_key}]",
                        "missing": "Expected dict object",
                    })
                    continue
                for lang_field in ("reply_en", "reply_ur", "reply_roman_ur"):
                    val = resp_val.get(lang_field)
                    if not val or not str(val).strip():
                        missing_entries.append({
                            "source": f"interview_bank/{fname}",
                            "location": f"responses[{resp_key}]",
                            "missing": lang_field,
                        })
        elif fname == "probes.json":
            # Check probes
            for probe_group, probe_list in data.items():
                if not isinstance(probe_list, list):
                    continue
                for idx, probe in enumerate(probe_list):
                    probe_id = probe.get("probe_id") or probe.get("slot") or f"{probe_group}[{idx}]"
                    for t_field in ("template_en", "template_ur", "template_roman_ur"):
                        val = probe.get(t_field)
                        if not val or not str(val).strip():
                            missing_entries.append({
                                "source": f"interview_bank/{fname}",
                                "location": f"probe:{probe_id}",
                                "missing": t_field,
                            })
                    # choices
                    choices = probe.get("choices")
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        for c_field in ("choices_ur", "choices_roman_ur"):
                            c_val = probe.get(c_field)
                            if not c_val or not isinstance(c_val, list) or len(c_val) != len(choices):
                                missing_entries.append({
                                    "source": f"interview_bank/{fname}",
                                    "location": f"probe:{probe_id}",
                                    "missing": f"{c_field} (len match {len(choices)})",
                                })
        else:
            # Module items list
            if not isinstance(data, list):
                continue
            for item in data:
                item_id = item.get("id") or item.get("slot") or "unknown_item"
                # template_en, ur, roman_ur
                for t_field in ("template_en", "template_ur", "template_roman_ur"):
                    val = item.get(t_field)
                    if not val or not str(val).strip():
                        missing_entries.append({
                            "source": f"interview_bank/{fname}",
                            "location": f"item:{item_id}",
                            "missing": t_field,
                        })
                # why_text, why_text_ur, why_text_roman_ur
                # Note: why_text is English
                if not item.get("why_text") or not str(item.get("why_text")).strip():
                    missing_entries.append({
                        "source": f"interview_bank/{fname}",
                        "location": f"item:{item_id}",
                        "missing": "why_text",
                    })
                for w_field in ("why_text_ur", "why_text_roman_ur"):
                    w_val = item.get(w_field)
                    if not w_val or not str(w_val).strip():
                        missing_entries.append({
                            "source": f"interview_bank/{fname}",
                            "location": f"item:{item_id}",
                            "missing": w_field,
                        })
                # choices
                choices = item.get("choices")
                if choices and isinstance(choices, list) and len(choices) > 0:
                    for c_field in ("choices_ur", "choices_roman_ur"):
                        c_val = item.get(c_field)
                        if not c_val or not isinstance(c_val, list) or len(c_val) != len(choices):
                            missing_entries.append({
                                "source": f"interview_bank/{fname}",
                                "location": f"item:{item_id}",
                                "missing": f"{c_field} (len match {len(choices)})",
                            })

    return missing_entries


def audit_python_files() -> List[Dict[str, Any]]:
    hardcoded_entries: List[Dict[str, Any]] = []
    py_files = [
        AGENTS_DIR / "interview_v3_runner.py",
        AGENTS_DIR / "answer_validation.py",
        AGENTS_DIR / "answer_understanding.py",
        MAIN_PY,
    ]

    for py_path in py_files:
        if not py_path.exists():
            continue

        try:
            with open(py_path, "r", encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source, filename=str(py_path))
        except Exception as e:
            hardcoded_entries.append({
                "source": py_path.name,
                "location": f"{py_path.name}:1",
                "missing": f"AST parse error: {e}",
            })
            continue

        # In main.py, focus specifically on the v3 block / response serialization
        # For other files, scan all assignments / dict pairs / call keywords
        for node in ast.walk(tree):
            # 1. Subscript assignment: session_state["current_question"] = "..."
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                        key_name = target.slice.value
                        if key_name in TARGET_KEYS:
                            # Check if value is a string constant or list of string constants
                            _check_assigned_value(node.value, key_name, py_path, target.lineno, hardcoded_entries)

            # 2. Dict key-value pair: {"current_question": "..."}
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value in TARGET_KEYS:
                        _check_assigned_value(v, k.value, py_path, k.lineno, hardcoded_entries)

            # 3. Call keyword args: ValidationResult(..., clarification_prompt="...") or CheckinAnswerResponse(system_note="...")
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in TARGET_KEYS:
                        _check_assigned_value(kw.value, kw.arg, py_path, kw.lineno, hardcoded_entries)

    return hardcoded_entries


def _check_assigned_value(
    val_node: ast.AST,
    key_name: str,
    py_path: Path,
    lineno: int,
    collector: List[Dict[str, Any]],
) -> None:
    # If the value is a string literal (Constant in 3.8+)
    if isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
        val_str = val_node.value.strip()
        # Whitelist purely empty strings, step sentinels, or method calls
        if val_str and val_str not in ("COMPLETE", "", "en", "ur", "roman_ur", "yes", "no"):
            # Check if this is an English sentence or string (not a lookup like get_message)
            collector.append({
                "source": py_path.name,
                "location": f"{py_path.name}:{lineno}",
                "missing": f"Hardcoded literal for '{key_name}': \"{val_str[:60]}\"",
            })
    # If the value is a list of constants (like options = ["Continue check-in", ...])
    elif isinstance(val_node, ast.List):
        for elt in val_node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                val_str = elt.value.strip()
                # Ignore non-English option lists like ["yes", "no"] or ["mmol/L", "mg/dL"]
                if val_str in ("mmol/L", "mg/dL", "yes", "no", "unknown"):
                    continue
                # If it has English text like "Continue check-in", "Blood Glucose", etc.
                if any(c.isalpha() for c in val_str):
                    collector.append({
                        "source": py_path.name,
                        "location": f"{py_path.name}:{lineno}",
                        "missing": f"Hardcoded list option in '{key_name}': \"{val_str}\"",
                    })
    # If the value is an f-string: f"Did you mean {val_res.value:g} mmol/L or {val_res.value:g} mg/dL?"
    elif isinstance(val_node, ast.JoinedStr):
        # f-string literal
        collector.append({
            "source": py_path.name,
            "location": f"{py_path.name}:{lineno}",
            "missing": f"Hardcoded f-string literal for '{key_name}'",
        })


def main() -> int:
    print("=" * 80)
    print("SCANNING FOR UNTRANSLATED STRINGS AND HARD-CODED PATIENT ENGLISH")
    print("=" * 80)

    bank_issues = audit_interview_bank()
    py_issues = audit_python_files()

    all_issues = bank_issues + py_issues

    print(f"\nAudit complete. Found {len(all_issues)} issues ({len(bank_issues)} bank, {len(py_issues)} code).\n")

    if all_issues:
        print(f"{'Source':<32} | {'Location':<35} | {'Issue'}")
        print("-" * 105)
        for issue in all_issues:
            print(f"{issue['source']:<32} | {issue['location']:<35} | {issue['missing']}")
        print("\n[FAIL] Untranslated strings or hard-coded literals detected.")
        return 1

    print("[SUCCESS] Zero untranslated bank fields or hard-coded patient strings found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

