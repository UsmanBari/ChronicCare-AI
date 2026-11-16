"""
Tests for P1-5: Explainer query map & D6 target claims validator (V6).
Ensures explanations never falsely claim readings are high/low/outside target
when readings are inside the D6 reference target ranges.
"""
from __future__ import annotations

import pytest
from rag.query_map import build_query_from_triage, TRIAGE_QUERY_TABLE
from rag.explainer import (
    explain,
    get_template_explanation,
    is_template_consistent,
    validate_reading_target_claims,
)
from rag.explain_guards import guarded_explain


def test_triage_query_table_contains_new_categories():
    """Verify all 4 new categories exist in TRIAGE_QUERY_TABLE."""
    for cat in ("medication_discrepancy", "first_checkin", "symptom_finding", "no_reading_unwell"):
        assert cat in TRIAGE_QUERY_TABLE, f"Missing {cat} in TRIAGE_QUERY_TABLE"
        qm = TRIAGE_QUERY_TABLE[cat]
        assert qm.trigger_category == cat
        assert qm.query_text
        assert qm.condition == "both"


def test_build_query_from_triage_medication_discrepancy():
    """Triage with medication discrepancy maps to medication_discrepancy query mapping."""
    triage_result = {
        "level": "review",
        "reasons": ["first_checkin", "medication_discrepancy: amlodipine dose changed", "glimepiride stopped"],
    }
    readings = {"blood_pressure_systolic": 124, "blood_pressure_diastolic": 80, "glucose": 110}
    qm = build_query_from_triage(triage_result, readings)
    assert qm.trigger_category == "medication_discrepancy"


def test_build_query_from_triage_first_checkin():
    """Triage with first_checkin maps to first_checkin query mapping."""
    triage_result = {
        "level": "review",
        "reasons": ["first_checkin: initial patient baseline"],
    }
    readings = {"blood_pressure_systolic": 120, "blood_pressure_diastolic": 78, "glucose": 105}
    qm = build_query_from_triage(triage_result, readings)
    assert qm.trigger_category == "first_checkin"


def test_build_query_from_triage_symptom_finding():
    """Triage with symptom_finding maps to symptom_finding query mapping."""
    triage_result = {
        "level": "review",
        "raised_by": [{"source": "symptom_finding", "detail": "Foot ulcer reported"}],
    }
    qm = build_query_from_triage(triage_result)
    assert qm.trigger_category == "symptom_finding"


def test_build_query_from_triage_no_reading_unwell():
    """Triage with no_reading_unwell maps to no_reading_unwell query mapping."""
    triage_result = {
        "level": "review",
        "reasons": ["symptoms_without_readings"],
    }
    qm = build_query_from_triage(triage_result)
    assert qm.trigger_category == "no_reading_unwell"


def test_v6_rejects_high_bp_claim_when_bp_in_target():
    """
    Exact P1-5 scenario: BP 124/80 (inside target 90-139 / 60-89).
    Sentence claiming BP is slightly above target MUST be rejected by V6.
    """
    readings = {
        "blood_pressure_systolic": 124,
        "blood_pressure_diastolic": 80,
        "glucose": 110,
    }
    sentences = [
        {"text": "Your blood pressure is slightly above the target [S1].", "cites": ["S1"]},
        {"text": "Clinical guidelines advise regular follow-up [S2].", "cites": ["S2"]},
    ]
    errors = validate_reading_target_claims(sentences, readings)
    assert errors, "V6 validator should have caught false high BP claim"
    assert any("falsely claims blood pressure is high/above target" in e for e in errors)


def test_v6_rejects_high_glucose_claim_when_glucose_in_fasting_target():
    """
    Glucose 110 fasting (inside target 90-125).
    Sentence claiming high blood sugar must be rejected.
    """
    readings = {
        "glucose": 110,
        "glucose_context": "fasting",
    }
    sentences = [
        {"text": "Your blood sugar reading is elevated [S1].", "cites": ["S1"]},
    ]
    errors = validate_reading_target_claims(sentences, readings)
    assert errors, "V6 validator should have caught false high glucose claim"
    assert any("falsely claims blood glucose is high/above target" in e for e in errors)


def test_v6_allows_abnormal_claims_when_readings_truly_abnormal():
    """When BP is genuinely 160/100, V6 does NOT reject claims that BP is high."""
    readings = {
        "blood_pressure_systolic": 160,
        "blood_pressure_diastolic": 100,
    }
    sentences = [
        {"text": "Your blood pressure reading of 160/100 mmHg is elevated [S1].", "cites": ["S1"]},
    ]
    errors = validate_reading_target_claims(sentences, readings)
    assert not errors, "V6 should not flag legitimate high BP claims when reading is outside target"


def test_safe_template_returned_on_p1_5_exact_case():
    """
    Full pipeline test with exact prompt case:
    110 fasting + BP 124/80, Yellow because of first check-in + amlodipine dose change + glimepiride stopped.
    A mock LLM generating 'Your blood pressure is slightly above the target' is rejected
    and safely falls back to the medication_discrepancy template.
    """
    readings = {
        "blood_pressure_systolic": 124,
        "blood_pressure_diastolic": 80,
        "glucose": 110,
        "glucose_context": "fasting",
    }
    triage_result = {
        "level": "review",
        "reasons": [
            "first_checkin",
            "medication_discrepancy: amlodipine dose change",
            "glimepiride stopped",
        ],
    }

    # Mock LLM that hallucinates the exact problematic sentence
    def hallucinating_llm(**kwargs):
        return '{"sentences": [{"text": "Your blood pressure is slightly above the target [S1].", "cites": ["S1"]}, {"text": "A clinician review is scheduled to evaluate your care [S1].", "cites": ["S1"]}]}'

    res = explain(
        triage_result=triage_result,
        readings=readings,
        language="en",
        llm=hallucinating_llm,
    )

    assert res["mode"] == "template"
    assert any("V6" in r for r in res["rejected_reasons"])
    # Verify the fallback template is the safe medication_discrepancy template
    text_content = " ".join(s["text"] for s in res["sentences"])
    assert "medication" in text_content.lower()
    assert "above the target" not in text_content.lower()


def test_templates_exist_across_all_languages():
    """Check that all 4 new categories have valid sentences in en, ur, roman_ur."""
    for cat in ("medication_discrepancy", "first_checkin", "symptom_finding", "no_reading_unwell"):
        for lang in ("en", "ur", "roman_ur"):
            tmpl = get_template_explanation(
                trigger_category=cat,
                readings={"blood_pressure_systolic": 120, "blood_pressure_diastolic": 80},
                triage_result={"level": "review"},
                language=lang,
                candidate_chunks=[],
                rejected_reasons=[],
            )
            assert len(tmpl["sentences"]) >= 2
            for s in tmpl["sentences"]:
                assert s["text"]
                assert s["cites"]
