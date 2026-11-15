"""
Tests for P1-4: Symptom finding extraction with intervening words and retention in summary & SOAP.
Ensures:
1. Finding extractor handles words between "sar ... dard", "سر ... درد", etc. in EN, UR, Roman UR.
2. Negated symptoms are not extracted as affirmative findings.
3. Check-in summary lists findings with attributes (e.g. "Headache (mild, gradual)").
4. Summary shows "None reported" / "Alamaat: Koi nahi" ONLY when there are no findings AND symptoms denied.
5. SOAP Subjective lists findings and NEVER shows "Reported symptoms: False".
"""
import pytest
from agents.interview_findings import extract_findings_from_answer, format_finding_label
from agents.interview_v3_runner import start_v3_session, next_turn, _build_dual_summary_text
from agents.soap_agent import build_soap


def test_finding_extractor_intervening_words_multilingual():
    """Verify finding extractor handles intervening words like 'sar mein halka dard' in 3 languages."""
    # 1. Roman Urdu: "subah se sar mein halka dard hai, baqi theek"
    rur_findings = extract_findings_from_answer("subah se sar mein halka dard hai, baqi theek")
    assert len(rur_findings) == 1, f"Expected 1 finding, got {rur_findings}"
    assert rur_findings[0].kind == "headache"
    assert rur_findings[0].attributes.get("severity") == "mild"
    assert rur_findings[0].attributes.get("onset") == "today"

    # 2. Urdu Script: "صبح سے سر میں ہلکا درد ہے"
    ur_findings = extract_findings_from_answer("صبح سے سر میں ہلکا درد ہے")
    assert len(ur_findings) == 1, f"Expected 1 finding, got {ur_findings}"
    assert ur_findings[0].kind == "headache"
    assert ur_findings[0].attributes.get("severity") == "mild"
    assert ur_findings[0].attributes.get("onset") == "today"

    # 3. English: "I have had a mild headache since morning"
    en_findings = extract_findings_from_answer("I have had a mild headache since morning")
    assert len(en_findings) == 1, f"Expected 1 finding, got {en_findings}"
    assert en_findings[0].kind == "headache"
    assert en_findings[0].attributes.get("severity") == "mild"
    assert en_findings[0].attributes.get("onset") == "today"

    # 4. English: "mild, gradual headache"
    en_gradual = extract_findings_from_answer("I have had a mild, gradual headache")
    assert len(en_gradual) == 1
    assert en_gradual[0].kind == "headache"
    assert en_gradual[0].attributes.get("severity") == "mild"
    assert en_gradual[0].attributes.get("onset") == "gradual"

    # 5. Roman Urdu chest discomfort: "seene mein thoda dard hai"
    rur_chest = extract_findings_from_answer("seene mein thoda dard hai")
    assert len(rur_chest) == 1
    assert rur_chest[0].kind == "chest_discomfort"

    # 6. Urdu script chest discomfort: "سینے میں ہلکا درد ہے"
    ur_chest = extract_findings_from_answer("سینے میں ہلکا درد ہے")
    assert len(ur_chest) == 1
    assert ur_chest[0].kind == "chest_discomfort"

    # 7. Roman Urdu foot problem: "paon mein halka dard hai"
    rur_foot = extract_findings_from_answer("paon mein halka dard hai")
    assert len(rur_foot) == 1
    assert rur_foot[0].kind == "foot_problem"

    # 8. Urdu script foot problem: "پاؤں میں ہلکا درد ہے"
    ur_foot = extract_findings_from_answer("پاؤں میں ہلکا درد ہے")
    assert len(ur_foot) == 1
    assert ur_foot[0].kind == "foot_problem"


def test_finding_extractor_negation_guards():
    """Verify negated mentions are not extracted as affirmative findings."""
    assert len(extract_findings_from_answer("sar mein dard nahi hai")) == 0
    assert len(extract_findings_from_answer("no headache today")) == 0
    assert len(extract_findings_from_answer("سر میں درد نہیں ہے")) == 0
    assert len(extract_findings_from_answer("koi chakkar nahi hai")) == 0

    # Mixed: negated symptom + affirmative symptom in different clauses
    mixed = extract_findings_from_answer("no vomiting, but sar mein halka dard hai")
    kinds = [f.kind for f in mixed]
    assert "headache" in kinds
    assert "nausea_or_vomiting" not in kinds


def test_format_finding_label_multilingual():
    """Verify format_finding_label formats name and attributes in EN, UR, Roman UR."""
    f = extract_findings_from_answer("I have had a mild, gradual headache")[0]
    label_en = format_finding_label(f, "en")
    assert label_en == "Headache (mild, gradual)"

    f_ur = extract_findings_from_answer("صبح سے سر میں ہلکا درد ہے")[0]
    label_ur = format_finding_label(f_ur, "ur")
    assert "سر درد" in label_ur
    assert "ہلکا" in label_ur

    f_ro = extract_findings_from_answer("subah se sar mein halka dard hai, baqi theek")[0]
    label_ro = format_finding_label(f_ro, "roman_ur")
    assert "Sar dard" in label_ro
    assert "mild" in label_ro


def test_summary_retains_findings_in_all_languages():
    """Verify _build_dual_summary_text lists findings and avoids 'None reported' when finding exists."""
    # 1. EN with finding
    f_en = extract_findings_from_answer("I have had a mild, gradual headache")
    state_en = {"findings": f_en, "known_slots": {"glucose_reading": 115, "bp_reading": [120, 80]}}
    summary_en = _build_dual_summary_text(state_en["known_slots"], "en", session_state=state_en)
    assert "Symptoms: Headache (mild, gradual)" in summary_en
    assert "Symptoms: None reported" not in summary_en

    # 2. Roman UR with finding
    f_ro = extract_findings_from_answer("subah se sar mein halka dard hai, baqi theek")
    state_ro = {"findings": f_ro, "known_slots": {"glucose_reading": 115, "bp_reading": [120, 80]}}
    summary_ro = _build_dual_summary_text(state_ro["known_slots"], "roman_ur", session_state=state_ro)
    assert "Alamaat: Sar dard" in summary_ro
    assert "Alamaat: Koi nahi" not in summary_ro

    # 3. Urdu with finding
    f_ur = extract_findings_from_answer("صبح سے سر میں ہلکا درد ہے")
    state_ur = {"findings": f_ur, "known_slots": {"glucose_reading": 115, "bp_reading": [120, 80]}}
    summary_ur = _build_dual_summary_text(state_ur["known_slots"], "ur", session_state=state_ur)
    assert "علامات: سر درد" in summary_ur
    assert "علامات: کوئی نہیں" not in summary_ur

    # 4. Denied symptoms -> "None reported"
    state_denied = {"findings": [], "known_slots": {"glucose_reading": 115, "symptoms_denied": True}}
    sum_denied_en = _build_dual_summary_text(state_denied["known_slots"], "en", session_state=state_denied)
    assert "Symptoms: None reported" in sum_denied_en

    sum_denied_ro = _build_dual_summary_text(state_denied["known_slots"], "roman_ur", session_state=state_denied)
    assert "Alamaat: Koi nahi" in sum_denied_ro

    sum_denied_ur = _build_dual_summary_text(state_denied["known_slots"], "ur", session_state=state_denied)
    assert "علامات: کوئی نہیں" in sum_denied_ur


def test_soap_note_lists_findings_and_never_shows_false():
    """Verify build_soap includes findings in Subjective and never outputs 'Reported symptoms: False'."""
    f = extract_findings_from_answer("I have had a mild, gradual headache")

    # Case 1: Findings present, yes/no slot might be False or None
    checkin_with_finding = {
        "checkin_id": "chk_soap_1",
        "user_id": "pat_1",
        "state": {
            "findings": f,
            "answers": {
                "hyperglycemia_symptoms": False,  # Should NOT output "Reported symptoms: False"
            },
            "known_slots": {"findings": f},
        },
    }
    soap_1 = build_soap(checkin_with_finding)
    subj_1 = " ".join(soap_1.get("subjective", []))
    assert "Reported symptoms: Headache (mild, gradual)" in subj_1
    assert "Reported symptoms: False" not in subj_1
    assert "Reported symptoms: None reported" not in subj_1

    # Case 2: No findings, symptoms denied
    checkin_denied = {
        "checkin_id": "chk_soap_2",
        "user_id": "pat_2",
        "state": {
            "findings": [],
            "symptoms_denied": True,
            "answers": {
                "hyperglycemia_symptoms": False,
            },
        },
    }
    soap_2 = build_soap(checkin_denied)
    subj_2 = " ".join(soap_2.get("subjective", []))
    assert "Reported symptoms: None reported" in subj_2
    assert "Reported symptoms: False" not in subj_2
