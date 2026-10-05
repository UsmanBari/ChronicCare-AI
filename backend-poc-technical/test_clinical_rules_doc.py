"""
Unit Test for Clinical Rules Register (Stage 7D-1 P3).

Parses docs/CLINICAL_RULES.md and verifies that all constants defined in
agents/triage_protocol.py and agents/adaptive_interview_agent.py are documented.
"""

import ast
import os
import pytest

def extract_module_constants(filepath: str) -> list[str]:
    """Extracts all top-level assigned variable names in UPPER_CASE (or starting with _) from an AST."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    constants = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # Include standard uppercase constants or uppercase constants starting with _
                    clean = name.lstrip("_")
                    if clean.isupper():
                        constants.append(name)
    return constants


def test_all_clinical_constants_documented_in_rules_register():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    doc_path = os.path.join(repo_root, "docs", "CLINICAL_RULES.md")
    
    assert os.path.exists(doc_path), f"CLINICAL_RULES.md missing at {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        doc_content = f.read()

    triage_path = os.path.join(base_dir, "agents", "triage_protocol.py")
    interview_path = os.path.join(base_dir, "agents", "adaptive_interview_agent.py")

    triage_constants = extract_module_constants(triage_path)
    interview_constants = extract_module_constants(interview_path)

    all_constants = sorted(list(set(triage_constants + interview_constants)))
    assert len(all_constants) > 0, "No constants extracted from agent files"

    missing = []
    for const_name in all_constants:
        # Check if the constant name appears in the markdown document (e.g. `CONST_NAME`)
        if const_name not in doc_content:
            missing.append(const_name)

    assert not missing, f"The following constants are missing from docs/CLINICAL_RULES.md: {missing}"
