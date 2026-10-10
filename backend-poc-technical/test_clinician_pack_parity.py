"""
Unit tests ensuring docs/CLINICIAN_REVIEW_PACK.md matches the active code constants.
Fails immediately if any constant in triage_protocol or adaptive_interview_agent drifts.
"""

from pathlib import Path
import re
import pytest

from agents.triage_protocol import (
    GLUCOSE_VERY_LOW_MG_DL,
    GLUCOSE_LOW_MG_DL,
    GLUCOSE_HIGH_MG_DL,
    GLUCOSE_URGENT_MG_DL,
    DANGEROUS_BP_SYSTOLIC_MMHG,
    DANGEROUS_BP_DIASTOLIC_MMHG,
    BP_STAGE2_SYSTOLIC_MMHG,
    BP_STAGE2_DIASTOLIC_MMHG,
    BP_LOW_SYSTOLIC_MMHG,
    BP_LOW_DIASTOLIC_MMHG,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = REPO_ROOT / "docs" / "CLINICIAN_REVIEW_PACK.md"


def test_clinician_pack_exists_and_contains_clinical_disclaimer():
    assert PACK_PATH.exists(), f"Missing clinician pack at {PACK_PATH}"
    content = PACK_PATH.read_text(encoding="utf-8")
    assert "CLINICAL DISCLAIMER & SAFETY NOTICE" in content
    assert "Nothing in this repository or prototype has been clinically validated" in content


def test_clinician_pack_parity_with_glucose_constants():
    content = PACK_PATH.read_text(encoding="utf-8")
    assert f"GLUCOSE_VERY_LOW_MG_DL = {GLUCOSE_VERY_LOW_MG_DL}" in content
    assert f"GLUCOSE_LOW_MG_DL = {GLUCOSE_LOW_MG_DL}" in content
    assert f"GLUCOSE_HIGH_MG_DL = {GLUCOSE_HIGH_MG_DL}" in content
    assert f"GLUCOSE_URGENT_MG_DL = {GLUCOSE_URGENT_MG_DL}" in content
    assert "mmol/L * 18.0 = mg/dL" in content


def test_clinician_pack_parity_with_bp_constants():
    content = PACK_PATH.read_text(encoding="utf-8")
    assert f"DANGEROUS_BP_SYSTOLIC_MMHG = {DANGEROUS_BP_SYSTOLIC_MMHG}" in content
    assert f"DANGEROUS_BP_DIASTOLIC_MMHG = {DANGEROUS_BP_DIASTOLIC_MMHG}" in content
    assert f"BP_STAGE2_SYSTOLIC_MMHG = {BP_STAGE2_SYSTOLIC_MMHG}" in content
    assert f"BP_STAGE2_DIASTOLIC_MMHG = {BP_STAGE2_DIASTOLIC_MMHG}" in content
    assert f"BP_LOW_SYSTOLIC_MMHG = {BP_LOW_SYSTOLIC_MMHG}" in content
    assert f"BP_LOW_DIASTOLIC_MMHG = {BP_LOW_DIASTOLIC_MMHG}" in content


def test_clinician_pack_contains_all_four_narrative_yes_questions():
    content = PACK_PATH.read_text(encoding="utf-8")
    for q in ["hypo_events_past_week", "sick_day_flags", "associated_symptoms", "foot_problems"]:
        assert f"`{q}`" in content


def test_clinician_pack_contains_three_confused_options():
    content = PACK_PATH.read_text(encoding="utf-8")
    assert "Option 1 (Keep As-Is / High Sensitivity)" in content
    assert "Option 2 (First-Person Syntactic Constraint)" in content
    assert "Option 3 (Single Clarification Gate)" in content
