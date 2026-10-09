"""
Unit Test running and verifying mutation proofs (Stage 9A-2).
"""

import os
import sys
from pathlib import Path

# Load verify_mutations from scripts
scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(scripts_dir))

from verify_mutations import run_all_mutation_proofs


def test_mutation_proofs_execution():
    # Executes all real mutation proofs with diffs
    run_all_mutation_proofs()
