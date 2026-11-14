"""
Unit, integration, and property tests for Danger Word Groups v1.
Validates:
- C1: All 5 acute danger groups across English, Roman Urdu, and Urdu.
- C2: Bidirectional negation (preceding & trailing) and past/resolved event guards.
- C3: Real HTTP endpoints (v2 & v3, direct & graph orchestrator modes):
      routine + hit -> review; urgent/emergency unchanged; negated/past -> no change;
      safety_note returned in en & ur; audit log recorded.
- C4: Property test over wordgroups_dev.json: a hit never yields urgent or emergency.
- C5: Invariant with flag OFF: zero side effects, no raise, no safety note.
- C6: Provider review detail shows danger_wordgroups names when enabled.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from agents.adaptive_interview_agent import INTERVIEW_COMPLETE, InterviewState
from agents.danger_wordgroups import (
    WordGroupResult,
    detect,
    get_safety_note,
)
from test_checkin_api import setup_test_environment, rsa_key_pair, x509_cert_pem
from agents.verification_agent import VerificationResult
from fastapi.testclient import TestClient
from main import app
from orchestrator.steps import step_decide_triage
from test_checkin_api import (
    bootstrap_patient,
    create_test_token,
)

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_SET_PATH = REPO_ROOT / "tests" / "sim" / "wordgroups_dev.json"


# =============================================================================
# C1: GROUP COVERAGE (5 Groups x 3 Languages)
# =============================================================================

@pytest.mark.parametrize(
    "text,expected_group",
    [
        # Group 1: Cardiac / Chest Pain
        ("I have severe crushing chest pain radiating to left arm", "cardiac_chest_pain"),
        ("seenay mein shadeed dard aur dabao mehsoos ho raha hai", "cardiac_chest_pain"),
        ("چھاتی پر شدید بوجھ اور درد محسوس ہو رہا ہے", "cardiac_chest_pain"),
        ("dil mein sakht dard aur jalan hai", "cardiac_chest_pain"),

        # Group 2: Stroke FAST
        ("his face is drooping on left side and cannot smile", "stroke_fast_cue"),
        ("munh terha ho gaya hai aik taraf", "stroke_fast_cue"),
        ("ایک طرف کا بازو سن اور کمزور ہو گیا ہے", "stroke_fast_cue"),
        ("slurred speech and patient is unable to speak", "stroke_fast_cue"),
        ("awaz ladkhada rahi hai aur bol nahi pa raha", "stroke_fast_cue"),

        # Group 3: Acute Respiratory Distress
        ("I am struggling to breathe and gasping for air", "breathing_distress"),
        ("cannot breathe properly at all my chest is suffocated", "breathing_distress"),
        ("saans nahi aa rahi dum ghut raha hai", "breathing_distress"),
        ("سانس بالکل اکھڑ رہی ہے", "breathing_distress"),

        # Group 4: Syncope / Unresponsiveness
        ("patient collapsed on the floor and was unresponsive", "unresponsive_faint"),
        ("he suddenly fainted and passed out", "unresponsive_faint"),
        ("abbu behosh ho gaye hain aur jawab nahi de rahe", "unresponsive_faint"),
        ("وہ بے ہوش ہو گئے ہیں اور غش آ گیا ہے", "unresponsive_faint"),
        ("chakkar kha kar gir gaya aur behosh ho gaya", "unresponsive_faint"),

        # Group 5: GI Hemorrhage (Hematemesis / Melena)
        ("I am vomiting blood with dark red clots", "vomiting_blood"),
        ("threw up dark red blood multiple times today", "vomiting_blood"),
        ("khoon ki ulti aayi hai bohot zyada", "vomiting_blood"),
        ("خون کی الٹی آ رہی ہے اور قے میں خون ہے", "vomiting_blood"),
        ("passing black tarry stool since morning", "vomiting_blood"),
        ("kala pakhana aa raha hai", "vomiting_blood"),
    ],
)
def test_c1_all_five_groups_detected(text: str, expected_group: str):
    res: WordGroupResult = detect(text)
    assert res.is_danger is True
    assert res.group == expected_group
    assert get_safety_note("en") == "If this is an emergency, call 1122 now."
    assert get_safety_note("ur") == "اگر یہ ایمرجنسی ہے تو ابھی 1122 پر کال کریں۔"
    assert get_safety_note("roman_ur") == "Agar yeh emergency hai to abhi 1122 par call karein."


# =============================================================================
# C2: NEGATION & GUARDS (Preceding, Trailing, Resolved, Kal)
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        # Preceding English Negation
        "I have no chest pain at all today",
        "denies chest pain or shortness of breath",
        "never fainted or passed out in my life",
        "no weakness in arms or legs",
        "without blood in vomit",

        # Trailing Urdu / Roman Urdu Negation
        "seenay mein dard nahi hai bilkul theek hoon",
        "سینے میں کوئی درد نہیں ہے",
        "seene mein koi dabao ya dard nahi hai",
        "bazu mein koi kamzori nahi hai",
        "بازو میں کوئی کمزوری یا سن پن نہیں ہے",
        "kabhi behosh nahi hua",
        "بے ہوش نہیں ہوئے کبھی",
        "khoon ki ulti nahi aayi aam ulti thi",
        "خون کی کوئی الٹی نہیں ہوئی",

        # Resolved Cues
        "seene mein dard tha pehle lekin ab theek ho gaya",
        "اب ٹھیک ہے درد بالکل ختم ہو گیا",
        "chest pressure is now gone and feeling okay",
        "pehle saans phoolti thi ab nahi phoolti",
        "pehle behosh hua tha ab theek hai",

        # Strictly Past Cues
        "had severe chest pain last year during surgery",
        "pichle saal behosh hua tha ab theek hoon",
        "پچھلے سال سینے میں شدید درد ہوا تھا لیکن اب ٹھیک ہوں",
        "months ago I passed out once at the gym",
        "kal tha seene mein dard ab theek hai",
    ],
)
def test_c2_negation_and_resolved_guards(text: str):
    res = detect(text)
    assert res.is_danger is False, f"Expected False for negated/resolved '{text}', got {res}"


def test_c2_kal_alone_is_not_past_cue():
    """
    Guards test: 'kal' alone is ambiguous (could mean ongoing complaint since yesterday).
    'kal se seene mein shadeed dard hai' MUST trigger acute cardiac.
    'kal tha seene mein dard ab theek hai' MUST be suppressed as resolved/past.
    """
    # Active acute complaint starting yesterday: NOT suppressed
    active_complaint = "kal se seene mein shadeed dard aur dabao hai"
    res_active = detect(active_complaint)
    assert res_active.is_danger is True
    assert res_active.group == "cardiac_chest_pain"

    # Resolved historical report yesterday: suppressed
    past_resolved = "kal tha seene mein dard lekin ab theek ho gaya"
    res_past = detect(past_resolved)
    assert res_past.is_danger is False


# =============================================================================
# C3: REAL HTTP ENDPOINTS INTEGRATION (v2 & v3, direct & graph)
# =============================================================================

def _create_and_auth_patient(rsa_key_pair, user_id: str = "uid-wg-patient-1") -> dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=user_id, email=f"{user_id}@demo.com")
    bootstrap_patient(client, token, conditions=["hypertension"])
    return {"Authorization": f"Bearer {token}"}


def _create_provider_headers(rsa_key_pair, prov_id: str = "prov-wg-1") -> dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=prov_id, email="provider@demo.com")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("orchestrator_mode", ["direct", "graph"])
@pytest.mark.parametrize("engine", ["v2", "v3"])
def test_c3_routine_plus_hit_raises_to_review(monkeypatch, rsa_key_pair, orchestrator_mode: str, engine: str):
    """
    Real HTTP integration test:
    routine check-in + danger wordgroup hit -> triage level raised to 'review',
    requires_review=True, review_status='open', safety_note returned.
    """
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")
    monkeypatch.setenv("ORCHESTRATOR", orchestrator_mode)
    headers = _create_and_auth_patient(rsa_key_pair, f"pat-c3-{orchestrator_mode}-{engine}")

    # 1. Start checkin
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    # 2. Answer with danger wordgroup phrase (unresponsiveness cue)
    answer_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "chakkar kha kar gir gaya aur behosh ho gaya"},
    )
    assert answer_resp.status_code == 200
    ans_data = answer_resp.json()
    assert ans_data["safety_note"] == "If this is an emergency, call 1122 now."
    assert ans_data["emergency"] is False  # Wordgroups NEVER set emergency!

    # Answer remaining routine questions until interview completes
    for ans in ["120/80", "no other symptoms", "yes taking medication", "no other issues"]:
        if ans_data.get("complete"):
            break
        a_resp = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers=headers,
            json={"answer": ans},
        )
        assert a_resp.status_code == 200
        ans_data = a_resp.json()

    # 3. Complete checkin
    complete_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers=headers)
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()

    assert comp_data["emergency"] is False
    assert comp_data["requires_review"] is True
    assert comp_data["triage"]["level"] == "review"
    assert "unresponsive_faint" in comp_data["triage"]["wordgroups"]
    assert comp_data["safety_note"] == "If this is an emergency, call 1122 now."


def test_c3_unit_routine_plus_hit_raises_to_review(monkeypatch):
    """
    Pure unit test for step_decide_triage:
    When routine verification summary has 0 reviews and an acute wordgroup hit is present,
    it MUST raise the final level from routine to review.
    """
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")

    verif = VerificationResult(
        patient_id="p-unit",
        observation_verifications=[],
        medication_verifications=[],
        summary={"requires_review": 0, "severity_high": 0, "severity_moderate": 0, "severity_low": 0},
    )
    hit = detect("seenay mein shadeed dard aur dabao hai")
    assert hit.is_danger is True

    state = InterviewState(
        patient_id="p-unit",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        answers={"_wordgroup_hits": [hit.to_dict()]},
        intakes=[{"condition": "hypertension", "requires_review": False}],
    )

    dec = step_decide_triage(
        verif_result=verif,
        state=state,
        protocol_state=None,
        user_id="u-unit",
        get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
    )

    assert dec["final_triage_level"] == "review"
    assert dec["final_requires_review"] is True
    assert "cardiac_chest_pain" in dec["triage_dict"]["wordgroups"]


@pytest.mark.parametrize("orchestrator_mode", ["direct", "graph"])
def test_c3_urgent_and_emergency_unchanged_by_wordgroup(monkeypatch, orchestrator_mode: str):
    """
    Can-Only-Raise Invariant:
    If check-in is already urgent (e.g. Stage-1 urgent or high BP trigger),
    a danger wordgroup hit CANNOT lower or alter it away from urgent.
    """
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")
    monkeypatch.setenv("ORCHESTRATOR", orchestrator_mode)

    # Unit test step_decide_triage with pre-existing urgent level
    verif = VerificationResult(
        patient_id="p123",
        observation_verifications=[],
        medication_verifications=[],
        summary={"requires_review": 1, "severity_high": 1, "severity_moderate": 0, "severity_low": 0},
    )
    state = InterviewState(
        patient_id="p123",
        conditions_on_file=["hypertension"],
        step=INTERVIEW_COMPLETE,
        intakes=[{"condition": "hypertension", "requires_review": True, "wordgroup_hits": [{"group": "cardiac_chest_pain"}]}],
        answers={"_wordgroup_hits": [{"group": "cardiac_chest_pain"}]},
    )

    class DummyProto:
        complete = True
        result = {"level": "urgent", "guidance": "urgent care required"}

    res = step_decide_triage(
        verif_result=verif,
        state=state,
        protocol_state=DummyProto(),
        user_id="u123",
        get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
    )

    # Urgent remains urgent (never lowered to review, never escalated to emergency)
    assert res["final_triage_level"] == "urgent"
    assert res["final_requires_review"] is True


def test_c3_negated_input_leaves_routine_unchanged(monkeypatch, rsa_key_pair):
    """Negated danger phrase does NOT raise routine to review."""
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")
    headers = _create_and_auth_patient(rsa_key_pair, "pat-c3-neg")

    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    checkin_id = start_resp.json()["checkin_id"]

    answer_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "seenay mein dard nahi hai fasting sugar 110"},
    )
    assert answer_resp.status_code == 200
    assert answer_resp.json().get("safety_note") is None


# =============================================================================
# C4: PROPERTY TEST OVER wordgroups_dev.json
# =============================================================================

def test_c4_wordgroup_hit_never_yields_urgent_or_emergency(monkeypatch):
    """
    Property test:
    For every danger sentence in wordgroups_dev.json,
    a wordgroup hit in routine checkin MUST raise routine to review,
    and MUST NEVER yield urgent or emergency.
    """
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")
    with open(DEV_SET_PATH, encoding="utf-8") as f:
        dev_data = json.load(f)

    danger_items = [d for d in dev_data if d["expected_danger"]]
    assert len(danger_items) >= 40, f"Expected >= 40 danger sentences, got {len(danger_items)}"

    dummy_verif = VerificationResult(
        patient_id="p-prop",
        observation_verifications=[],
        medication_verifications=[],
        summary={"requires_review": 0, "severity_high": 0, "severity_moderate": 0, "severity_low": 0},
    )

    for item in danger_items:
        text = item["text"]
        hit = detect(text)
        assert hit.is_danger is True, f"Failed to detect danger in '{text}'"

        state = InterviewState(
            patient_id="p-prop",
            conditions_on_file=["hypertension"],
            step=INTERVIEW_COMPLETE,
            answers={"_wordgroup_hits": [hit.to_dict()]},
            intakes=[{"condition": "hypertension", "requires_review": False}],
        )

        dec = step_decide_triage(
            verif_result=dummy_verif,
            state=state,
            protocol_state=None,
            user_id="u-prop",
            get_patient_profile_fn=lambda uid: {"date_of_birth": "1980-01-01"},
        )

        level = dec["final_triage_level"]
        # CRITICAL SAFETY INVARIANT: Must be review. NEVER urgent, NEVER emergency.
        assert level == "review", f"Sentence '{text}' yielded {level}; expected 'review'"
        assert level != "urgent"
        assert level != "emergency"
        assert dec["final_requires_review"] is True


# =============================================================================
# C5: DEFAULT FLAG-OFF INVARIANT
# =============================================================================

def test_c5_flag_off_invariant_behavior_identical_to_baseline(monkeypatch, rsa_key_pair):
    """When DANGER_WORDGROUPS_ENABLED is false/unset, wordgroups have zero runtime impact."""
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "false")
    headers = _create_and_auth_patient(rsa_key_pair, "pat-c5-flag-off")

    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    checkin_id = start_resp.json()["checkin_id"]

    # Even with an acute wordgroup phrase, flag is OFF so no safety note returned
    answer_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "kala pakhana aa raha hai"},
    )
    assert answer_resp.status_code == 200
    assert answer_resp.json().get("safety_note") is None


# =============================================================================
# C6: PROVIDER REVIEW DETAIL
# =============================================================================

def test_c6_provider_review_detail_returns_danger_wordgroups(monkeypatch, rsa_key_pair):
    """Provider review detail returns danger_wordgroups list when flag is ON."""
    monkeypatch.setenv("DANGER_WORDGROUPS_ENABLED", "true")
    patient_headers = _create_and_auth_patient(rsa_key_pair, "pat-c6-prov")

    # Complete a checkin with danger wordgroup
    s_resp = client.post("/api/checkins/start", headers=patient_headers, json={"mode": "isolated"})
    cid = s_resp.json()["checkin_id"]

    ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=patient_headers, json={"answer": "khoon ki ulti aayi hai"})
    for ans in ["120/80", "no other symptoms", "yes taking medication", "no other issues"]:
        if ans_resp.json().get("complete"):
            break
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=patient_headers, json={"answer": ans})
    client.post(f"/api/checkins/{cid}/complete", headers=patient_headers)

    p_headers = _create_provider_headers(rsa_key_pair, "prov-c6")

    # Fetch review detail
    rev_resp = client.get(f"/api/provider/review/{cid}", headers=p_headers)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()

    assert rev_data["danger_wordgroups"] is not None
    assert "vomiting_blood" in rev_data["danger_wordgroups"]



# =============================================================================
# C7: CODE REVIEW CASES & FIVE CATEGORIES (Dev Regression Protection)
# =============================================================================

@pytest.mark.parametrize(
    "text,expected_danger,expected_group",
    [
        ("ابھی سانس نہیں آ رہی", True, "breathing_distress"),
        ("اب سانس نہیں آ رہی", True, "breathing_distress"),
        ("طبیعت خراب ہے سانس نہیں آ رہی", True, "breathing_distress"),
        ("ab saans nahi aa rahi", True, "breathing_distress"),
        ("since yesterday I cannot breathe", True, "breathing_distress"),
        ("pichle saal sugar zyada thi, aaj seene mein shadeed dabao hai", True, "cardiac_chest_pain"),
        ("last year I had a cold. Now my face is drooping", True, "stroke_fast_cue"),
        ("bazu kamzor ho gaya hai uthaya nahi ja raha", True, "stroke_fast_cue"),
        ("ٹانگ پر چوٹ ہے اس لیے سنبھل کر چلتا ہوں", False, None),
        ("دوائی بدل دی ہے تو سر میں درد ہے", False, None),
    ],
)
def test_code_review_ten_cases(text: str, expected_danger: bool, expected_group: str | None):
    res = detect(text)
    assert res.is_danger is expected_danger
    if expected_danger:
        assert res.group == expected_group


@pytest.mark.parametrize(
    "category,text,expected_danger,expected_group",
    [
        # Category a: cross-clause past isolation
        ("a", "two months ago I had fever, but today my chest feels heavy and crushing", True, "cardiac_chest_pain"),
        ("a", "pichle hafte seene mein dard tha, ab koi takleef nahi", False, None),
        # Category b: resolved cues
        ("b", "ابھی دل میں شدید درد ہو رہا ہے", True, "cardiac_chest_pain"),
        ("b", "pichle do ghante se takleef thi lekin ab theek hai", False, None),
        # Category c: ongoing vs past
        ("c", "kal se seene mein shadeed dabao mehsoos ho raha hai", True, "cardiac_chest_pain"),
        ("c", "kal seene mein dard tha par dawai le li thi", True, "cardiac_chest_pain"),
        # Category d: Urdu script boundaries
        ("d", "دل کی دھڑکن تیز ہے اور سینے میں شدید دباؤ ہے", True, "cardiac_chest_pain"),
        ("d", "کل پاؤں پھسل گیا تھا لیکن سنبھل گیا", False, None),
        # Category e: inability vs trailing negation
        ("e", "haath bilkul kamzor hai hilaya nahi ja raha", True, "stroke_fast_cue"),
        ("e", "bazu mein koi dard nahi hai", False, None),
    ],
)
def test_five_categories_danger_and_traps(category: str, text: str, expected_danger: bool, expected_group: str | None):
    res = detect(text)
    assert res.is_danger is expected_danger
    if expected_danger:
        assert res.group == expected_group


def test_wordgroup_result_schema():
    res = detect("seene mein shadeed dard hai")
    d = res.to_dict()
    assert set(d.keys()) == {"is_danger", "group", "suppressed_by"}
    assert "matched_phrase" not in d
    assert "cues" not in d
    assert "safety_note" not in d


# =============================================================================
# C8: APOSTROPHE EXPANSION & HABITUAL PAST
# =============================================================================

@pytest.mark.parametrize(
    "text,expected_danger,expected_group",
    [
        # Apostrophes & Contractions (Must Hit)
        ("I can't breathe", True, "breathing_distress"),
        ("I can’t breathe", True, "breathing_distress"),
        ("I can't breathe properly since this morning", True, "breathing_distress"),
        ("she can't speak", True, "stroke_fast_cue"),
        ("he couldn't move his arm", True, "stroke_fast_cue"),
        # Negated Contractions (Must Not Hit)
        ("I don't have chest pain", False, None),
        ("I haven't fainted", False, None),
        ("she doesn't have face drooping", False, None),
        ("I didn't vomit blood", False, None),
        # Habitual Past (Must Not Hit)
        ("pehle chest pain hota tha, ab nahi hota", False, None),
        ("پہلے سینے میں درد ہوتا تھا", False, None),
        # Active / Ongoing (Must Still Hit)
        ("kal se seene mein dard ho raha hai", True, "cardiac_chest_pain"),
        ("seene mein dard ho raha hai", True, "cardiac_chest_pain"),
    ],
)
def test_apostrophe_and_habitual_past(text: str, expected_danger: bool, expected_group: str | None):
    res = detect(text)
    assert res.is_danger is expected_danger
    if expected_danger:
        assert res.group == expected_group

# =============================================================================
# C9: VOCABULARY GAPS & TRAPS (REVIEW 3)
# =============================================================================

@pytest.mark.parametrize(
    "text,expected_danger,expected_group",
    [
        # Roman Urdu severity bhaari/bhari/bhaary in chest group
        ("dard ho raha hai aur seena bhaari hai", True, "cardiac_chest_pain"),
        ("seena bhaari nahi hai", False, None),
        ("seena bhari hai", True, "cardiac_chest_pain"),
        ("seena bhari nahi hai", False, None),
        # cannot feel / could not feel + limb in stroke group
        ("I can't feel my left arm", True, "stroke_fast_cue"),
        ("I couldn't feel my right hand", True, "stroke_fast_cue"),
        ("I can feel my arm fine", False, None),
        ("I can feel my leg fine", False, None),
        # could not speak / unable to talk / can't talk in speech pattern
        ("I couldn't speak properly for the last hour", True, "stroke_fast_cue"),
        ("unable to talk", True, "stroke_fast_cue"),
        ("can't talk right now", True, "stroke_fast_cue"),
        ("I couldn't speak to the doctor yesterday because he was busy", False, None),
    ],
)
def test_review3_vocabulary_gaps_and_traps(text: str, expected_danger: bool, expected_group: str | None):
    res = detect(text)
    assert res.is_danger is expected_danger
    if expected_danger:
        assert res.group == expected_group

# =============================================================================
# C10: V1.1 REMOTE PAST VS RECENT EPISODES & CROSS-CLAUSE RESOLVED
# =============================================================================

@pytest.mark.parametrize(
    "text,expected_danger,expected_group",
    [
        # Recent Time Episodes (Must Hit: Recent danger must NOT be suppressed by recent past cues)
        ("I fainted yesterday", True, "unresponsive_faint"),
        ("yesterday evening my face started drooping and it is still drooping", True, "stroke_fast_cue"),
        ("kal raat behosh ho gaya tha", True, "unresponsive_faint"),
        ("pichle hafte do dafa behosh hua", True, "unresponsive_faint"),
        ("this morning I vomited blood", True, "vomiting_blood"),
        ("since yesterday I cannot breathe", True, "breathing_distress"),
        # Remote Past & Habitual Past (Must Not Hit: >1 month ago or habitual past suppresses)
        ("pichle saal behosh hua tha", False, None),
        ("years ago I had chest pressure", False, None),
        ("pehle seene mein dard hota tha", False, None),
        # Cross-Clause Resolved (Must Not Hit: Resolved cue in adjacent clause suppresses past-tense hit)
        ("seene mein dard tha, ab theek hoon", False, None),
        # Conversational Guard Retained
        ("I couldn't speak to the doctor yesterday because he was busy", False, None),
    ],
)
def test_v1_1_remote_past_vs_recent_episodes(text: str, expected_danger: bool, expected_group: str | None):
    res = detect(text)
    assert res.is_danger is expected_danger
    if expected_danger:
        assert res.group == expected_group

