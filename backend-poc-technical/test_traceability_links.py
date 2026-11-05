"""
Traceability Link Verification Test (Day 6, Part U2).

Parses docs/TRACEABILITY.md and enforces:
1. Every file path referenced under 'Where Built' exists on disk.
2. Every file path referenced under 'Evidence Doc' exists on disk.
3. Every test node referenced under 'Test' has the format 'path/to/file.py::test_func_name'.
4. Every test file exists on disk.
5. Every test function is physically defined as a function in that test file's AST.
"""

import ast
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACEABILITY_MD = REPO_ROOT / "docs" / "TRACEABILITY.md"


def parse_traceability_table():
    assert TRACEABILITY_MD.exists(), f"docs/TRACEABILITY.md not found at {TRACEABILITY_MD}"
    content = TRACEABILITY_MD.read_text(encoding="utf-8")

    rows = []
    in_table = False
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue

        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) != 5:
            continue

        # Header or divider
        if "Objective / Requirement" in cols[0] or re.match(r"^:?-+:?$", cols[0]):
            in_table = True
            continue

        if not in_table:
            continue

        # Clean backticks and extra markdown
        clean_cols = [re.sub(r"[`*]", "", c).strip() for c in cols]
        rows.append({
            "objective": clean_cols[0],
            "where_built": clean_cols[1],
            "test_node": clean_cols[2],
            "evidence_doc": clean_cols[3],
            "status": clean_cols[4],
        })

    return rows


def test_traceability_matrix_links():
    rows = parse_traceability_table()
    assert len(rows) >= 15, f"Expected at least 15 rows in docs/TRACEABILITY.md, found {len(rows)}"

    for row in rows:
        obj = row["objective"]
        built_file = REPO_ROOT / row["where_built"]
        evidence_file = REPO_ROOT / row["evidence_doc"]
        test_node = row["test_node"]

        # Check where_built file exists
        assert built_file.exists(), (
            f"Traceability failure for '{obj}': built file '{row['where_built']}' does not exist"
        )

        # Check evidence doc exists
        assert evidence_file.exists(), (
            f"Traceability failure for '{obj}': evidence doc '{row['evidence_doc']}' does not exist"
        )

        # Check test node format and existence
        assert "::" in test_node, (
            f"Traceability failure for '{obj}': test node '{test_node}' must be in 'file::test_name' format"
        )

        test_file_rel, test_fn_name = test_node.split("::", 1)
        test_file = REPO_ROOT / test_file_rel
        assert test_file.exists(), (
            f"Traceability failure for '{obj}': test file '{test_file_rel}' does not exist"
        )

        # Parse test file AST and confirm function exists
        source_code = test_file.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(test_file))
        func_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        assert test_fn_name in func_names, (
            f"Traceability failure for '{obj}': test function '{test_fn_name}' "
            f"not found in '{test_file_rel}' (available: {sorted([f for f in func_names if f.startswith('test_')])[:5]}...)"
        )

        # Validate status enum (supports qualifiers like 'BUILT (OCR v1...)' and 'PLANNED (FYP-2)')
        valid_prefixes = ("BUILT", "PENDING", "CUT", "PLANNED", "Delivered", "Partial", "Not started")
        assert any(row["status"].startswith(p) for p in valid_prefixes), (
            f"Invalid status '{row['status']}' for '{obj}': must start with BUILT, PENDING, CUT, or PLANNED"
        )

