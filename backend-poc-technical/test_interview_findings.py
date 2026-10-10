"""
Unit Tests for Findings & Symptom Drill-Down Engine (Stage 9A Task C).

Verifies:
1. Extraction of closed-vocabulary findings across symptoms.
2. Clinical attribute extraction (onset, duration, severity 0-10, pattern, trigger) in EN, UR, Roman UR.
3. Minimiser detection flags ("just a little", "bas thora sa").
4. Follow-up probe chain limits (max 2 probes per finding).
5. Exact patient quote preservation.
"""

import pytest
from agents.interview_findings import (
    Finding,
    extract_findings_from_answer,
    get_next_probe_for_finding,
    FINDING_KINDS,
)
from agents.interview_bank.loader import get_default_bank


def test_finding_kinds_coverage():
    assert "dizziness" in FINDING_KINDS
    assert "headache" in FINDING_KINDS
    assert "breathlessness" in FINDING_KINDS
    assert "foot_problem" in FINDING_KINDS
    assert "low_sugar_episode" in FINDING_KINDS


def test_dizziness_drilldown_chain():
    bank = get_default_bank()
    probes = bank.get_probes()

    # Patient reports dizziness on standing
    text = "I feel dizzy when I stand up from bed"
    findings = extract_findings_from_answer(text, step_id="greeting")
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == "dizziness"
    assert f.raw_quote == text
    assert f.attributes.get("trigger") == "standing_up"

    # Follow-up probe 1
    p1 = get_next_probe_for_finding(f, probes, max_probes=2)
    assert p1 is not None
    assert p1["probe_id"] == "probe_dizziness_postural"
    f.probe_count += 1
    f.probed_slots.append(p1["slot"])

    # Follow-up probe 2
    p2 = get_next_probe_for_finding(f, probes, max_probes=2)
    assert p2 is not None
    assert p2["probe_id"] == "probe_dizziness_falls"
    f.probe_count += 1
    f.probed_slots.append(p2["slot"])

    # Follow-up probe 3 should be None (capped at max 2)
    p3 = get_next_probe_for_finding(f, probes, max_probes=2)
    assert p3 is None


def test_severity_attributes_numeric_and_verbal():
    # 1. Numeric 8 out of 10
    f1 = extract_findings_from_answer("Throbbing headache 8 out of 10 since morning")[0]
    assert f1.kind == "headache"
    assert f1.attributes.get("severity_score") == 8
    assert f1.attributes.get("severity") == "severe"
    assert f1.attributes.get("onset") == "today"

    # 2. Minimiser in English: "just a little"
    f2 = extract_findings_from_answer("Just a little dizzy today")[0]
    assert f2.kind == "dizziness"
    assert f2.attributes.get("severity") == "mild"
    assert f2.attributes.get("is_minimiser") is True

    # 3. Minimiser in Roman Urdu: "bas thora sa"
    f3 = extract_findings_from_answer("Bas thora sa sar me dard hai")[0]
    assert f3.kind == "headache"
    assert f3.attributes.get("severity") == "mild"
    assert f3.attributes.get("is_minimiser") is True


def test_multilingual_finding_extraction():
    # Urdu script
    f_ur = extract_findings_from_answer("پاؤں پر زخم اور شدید درد ہے")[0]
    assert f_ur.kind == "foot_problem"

    # Roman Urdu
    f_rur = extract_findings_from_answer("Kal se saans phool rahi hai chalnay par")[0]
    assert f_rur.kind == "breathlessness"
    assert f_rur.attributes.get("onset") == "since_yesterday"
    assert f_rur.attributes.get("trigger") == "exertion"
