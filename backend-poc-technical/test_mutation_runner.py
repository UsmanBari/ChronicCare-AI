"""
Hermetic test for the mutation runner in CI (Stage 9A-5 Task D).
Executes the mutation runner on 5 fast mutations and verifies:
- Exactly 1 occurrence matched
- Subprocess pytest fails on mutated code (KILLED)
- File byte integrity restored exactly to original SHA-256
"""

import sys
import time
from pathlib import Path

# Add repo root to sys.path to import scripts
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import verify_mutations


def test_mutation_runner_executes_and_kills_in_ci():
    """Verify that mutation harness executes and kills mutations in CI under 90s."""
    # Test at least 5 representative mutations across triage, planner, runner, and Stage 8b
    selected_ids = ["MUT-1", "MUT-4", "MUT-7", "MUT-10", "MUT-8B-1"]
    mutations_to_test = [m for m in verify_mutations.MUTATIONS if m["id"] in selected_ids]
    assert len(mutations_to_test) == 5

    t0 = time.time()
    for mut in mutations_to_test:
        res = verify_mutations.run_mutation(mut)
        assert res["killed"] is True, f"Mutation {mut['id']} was not killed by {mut['test_node']}"
        assert res["sha_before"] == res["sha_after"], f"Mutation {mut['id']} failed SHA-256 byte restoration"

    elapsed = time.time() - t0
    # Must complete well within 90 seconds
    assert elapsed < 90.0, f"Mutation runner took {elapsed:.2f}s (exceeded 90s limit)"
