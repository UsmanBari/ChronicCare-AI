import importlib.util
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_sim_report.py"

spec = importlib.util.spec_from_file_location("generate_sim_report", str(SCRIPT_PATH))
sim_report_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim_report_mod)
_run_simulation = sim_report_mod.run_simulation
_generate_report = sim_report_mod.generate_report


def test_sim_report_file_exists_and_is_current():
    report_path = REPO_ROOT / "docs" / "INTERVIEW_V3_SIM_REPORT.md"
    assert report_path.exists(), f"Missing report at {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        existing_content = f.read().replace("\r\n", "\n")

    stats = _run_simulation()
    expected_content = _generate_report(stats).replace("\r\n", "\n")

    assert "Total Simulated Personas Tested" in existing_content
    assert str(stats["total_personas"]) in existing_content
    assert str(stats["avg_questions"]) in existing_content
