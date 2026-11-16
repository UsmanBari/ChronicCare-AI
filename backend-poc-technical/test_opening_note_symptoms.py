"""
Unit & Integration Tests for Symptoms in Opening Note (FIX5 Item 1).

Verifies:
1. English opening with mild headache: finding stored, summary shows "Symptoms: Headache (mild, since morning)", SOAP shows "Reported symptoms: Headache (mild, since morning)".
2. Roman Urdu opening with mild headache: finding stored, summary shows "Alamaat: Sar dard (mild, since morning)", SOAP shows "Reported symptoms: Headache (mild, since morning)".
3. Urdu script opening with mild headache: finding stored, summary shows "علامات: سر درد (ہلکا, صبح سے)", SOAP shows "Reported symptoms: Headache (mild, since morning)".
4. Opening without symptoms: summary shows "Symptoms: None reported" (never "Symptoms: not asked"), SOAP shows "Reported symptoms: None reported" (never "Reported symptoms: not answered").
"""
import pytest
from agents.interview_v3_runner import start_v3_session, _build_dual_summary_text
from agents.soap_agent import build_soap


def test_opening_note_symptoms_stored_and_recap_and_soap_en():
    """English opening note extracts headache, stores in findings, appears in summary and SOAP."""
    opening = "Feeling okay overall. Sugar 2 hours after lunch was 165, BP 124/80. Took all my medicines. Mild headache since morning."
    state = start_v3_session(
        checkin_id="chk-open-en-1",
        patient_id="pat-open-en",
        conditions=["diabetes", "hypertension"],
        language="en",
        opening_note=opening,
    )

    # 1. Finding stored
    findings = state.get("findings", [])
    assert len(findings) >= 1, f"Expected at least 1 finding, got {findings}"
    kinds = [f.get("kind") if isinstance(f, dict) else f.kind for f in findings]
    assert "headache" in kinds, f"Expected 'headache' in findings, got {kinds}"

    # 2. Summary shows formatted finding
    summary_text = _build_dual_summary_text(state["known_slots"], "en", session_state=state)
    assert "Symptoms: Headache (mild, since morning)" in summary_text, f"Expected headache in summary, got: {summary_text}"
    assert "not asked" not in summary_text.lower()

    # 3. SOAP shows formatted finding
    soap = build_soap({"state": state}, {})
    subj_str = "\n".join(soap.get("subjective", []))
    assert "Reported symptoms: Headache (mild, since morning)" in subj_str, f"Expected headache in SOAP subjective, got: {subj_str}"


def test_opening_note_symptoms_stored_and_recap_and_soap_roman_ur():
    """Roman Urdu opening note extracts headache, stores in findings, appears in summary and SOAP."""
    opening = "theek hoon subah se sar mein halka dard hai"
    state = start_v3_session(
        checkin_id="chk-open-ro-1",
        patient_id="pat-open-ro",
        conditions=["diabetes", "hypertension"],
        language="roman_ur",
        opening_note=opening,
    )

    findings = state.get("findings", [])
    assert len(findings) >= 1, f"Expected at least 1 finding, got {findings}"
    kinds = [f.get("kind") if isinstance(f, dict) else f.kind for f in findings]
    assert "headache" in kinds, f"Expected 'headache' in findings, got {kinds}"

    summary_text = _build_dual_summary_text(state["known_slots"], "roman_ur", session_state=state)
    assert "Alamaat: Sar dard (mild, since morning)" in summary_text, f"Expected Sar dard in summary, got: {summary_text}"
    assert "nahi poochay gaye" not in summary_text.lower()

    soap = build_soap({"state": state}, {})
    subj_str = "\n".join(soap.get("subjective", []))
    assert "Reported symptoms: Headache (mild, since morning)" in subj_str, f"Expected headache in SOAP subjective, got: {subj_str}"


def test_opening_note_symptoms_stored_and_recap_and_soap_urdu_script():
    """Urdu script opening note extracts headache, stores in findings, appears in summary and SOAP."""
    opening = "طبیعت ٹھیک ہے۔ صبح سے سر میں ہلکا درد ہے"
    state = start_v3_session(
        checkin_id="chk-open-ur-1",
        patient_id="pat-open-ur",
        conditions=["diabetes", "hypertension"],
        language="ur",
        opening_note=opening,
    )

    findings = state.get("findings", [])
    assert len(findings) >= 1, f"Expected at least 1 finding, got {findings}"
    kinds = [f.get("kind") if isinstance(f, dict) else f.kind for f in findings]
    assert "headache" in kinds, f"Expected 'headache' in findings, got {kinds}"

    summary_text = _build_dual_summary_text(state["known_slots"], "ur", session_state=state)
    assert "علامات: سر درد (ہلکا, صبح سے)" in summary_text, f"Expected Urdu headache in summary, got: {summary_text}"
    assert "پوچھی نہیں گئیں" not in summary_text

    soap = build_soap({"state": state}, {})
    subj_str = "\n".join(soap.get("subjective", []))
    assert "Reported symptoms: Headache (mild, since morning)" in subj_str, f"Expected headache in SOAP subjective, got: {subj_str}"


def test_opening_note_no_symptoms_never_not_asked():
    """Opening note without symptoms uses 'None reported' and never 'not asked' / 'not answered'."""
    opening = "Feeling okay overall. Sugar 2 hours after lunch was 165, BP 124/80. Took all my medicines."
    state = start_v3_session(
        checkin_id="chk-open-none-1",
        patient_id="pat-open-none",
        conditions=["diabetes", "hypertension"],
        language="en",
        opening_note=opening,
    )

    findings = state.get("findings", [])
    assert len(findings) == 0, f"Expected 0 findings, got {findings}"

    summary_text = _build_dual_summary_text(state["known_slots"], "en", session_state=state)
    assert "Symptoms: None reported" in summary_text, f"Expected 'Symptoms: None reported' in summary, got: {summary_text}"
    assert "not asked" not in summary_text.lower(), f"Unexpected 'not asked' in summary: {summary_text}"

    soap = build_soap({"state": state}, {})
    subj_str = "\n".join(soap.get("subjective", []))
    assert "Reported symptoms: None reported" in subj_str, f"Expected 'Reported symptoms: None reported' in SOAP, got: {subj_str}"
    assert "Reported symptoms: not answered" not in subj_str, f"Unexpected 'not answered' in SOAP: {subj_str}"
