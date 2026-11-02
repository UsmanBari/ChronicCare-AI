"""
Pytest integration for RAG retrieval test set validation.
Runs scripts/rag/validate_test_set.py logic against docs/rag/retrieval_test_set.json.
"""
import sys
from pathlib import Path

# Ensure repository root is in sys.path to import validation script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rag.validate_test_set import validate_retrieval_test_set


def test_rag_retrieval_test_set_valid():
    """Verify that docs/rag/retrieval_test_set.json passes all schema, count, and clinical constraints."""
    test_set_file = REPO_ROOT / "docs" / "rag" / "retrieval_test_set.json"
    assert test_set_file.exists(), f"Retrieval test set missing at {test_set_file}"

    summary = validate_retrieval_test_set(test_set_file)

    assert summary["total_items"] == 60
    assert summary["conditions"]["diabetes"] == 25
    assert summary["conditions"]["hypertension"] == 25
    assert summary["conditions"]["both"] == 10
    assert summary["kinds"]["safety_redirect"] >= 12
    assert summary["kinds"]["explain"] + summary["kinds"]["safety_redirect"] == 60
