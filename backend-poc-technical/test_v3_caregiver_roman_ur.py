"""
Tests for G-14: Roman Urdu & Urdu Caregiver Detection in Interview Engine v3.

Verifies:
1. All 9 target caregiver phrases in Roman Urdu, Urdu script, and English set
   answered_by="caregiver" and lower interview confidence to Medium.
2. 6 look-alike distractor phrases (third-party advice / action reports)
   must NOT trigger caregiver classification (including "main apni ammi ke liye dawai lata hoon").
3. Clinical content preservation:
   - "ammi ki taraf se sugar 45 hai" -> glucose 45 recorded, low-sugar rules fire
   - "ammi ki taraf se sugar 250 hai" -> glucose 250 recorded
   - "abbu ke liye: BP 185/125" -> BP recorded, crisis path
   - "ammi ki taraf se haan dawai li" on adherence -> adherent + caregiver
   - Caregiver prefix on every answer for a whole check-in -> completes normally,
     readings kept, ended_early_off_topic is not set.
   Each compared with the same answers WITHOUT caregiver phrase: final level identical or higher, never lower.
"""

import pytest
from agents.answer_understanding import detect_caregiver_phrase
from agents.interview_v3_runner import start_v3_session, next_turn, finish_v3_session


CAREGIVER_POSITIVE_PHRASES = [
    "ammi ki taraf se",
    "abbu ke liye",
    "main apni walida ke liye jawab de raha hoon",
    "میں اپنی امی کی طرف سے",
    "walid sahab ki taraf se",
    "apni ammi ke liye check in kar raha hoon",
    "mere abbu ki checking hai",
    "walida ke liye check in",
    "میں اپنے والد کے لیے جواب دے رہا ہوں",
]

LOOKALIKE_NEGATIVE_PHRASES = [
    "ammi ne kaha tha dawai lo",
    "abbu ne bola doctor ke paas jao",
    "walida ne kaha sugar check karo",
    "walid ne dawai mangwai thi",
    "ammi kehti hain meetha kam khao",
    "main apni ammi ke liye dawai lata hoon",
]

LEVEL_ORDER = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}


@pytest.mark.parametrize("phrase", CAREGIVER_POSITIVE_PHRASES)
def test_caregiver_detector_accepts_all_positive_phrases(phrase: str):
    assert detect_caregiver_phrase(phrase) is True, f"Failed to detect caregiver phrase: {phrase}"


@pytest.mark.parametrize("distractor", LOOKALIKE_NEGATIVE_PHRASES)
def test_caregiver_detector_rejects_lookalike_distractors(distractor: str):
    assert detect_caregiver_phrase(distractor) is False, f"Lookalike erroneously triggered caregiver: {distractor}"


@pytest.mark.parametrize("phrase", CAREGIVER_POSITIVE_PHRASES)
def test_v3_runner_sets_caregiver_and_lowers_confidence(phrase: str):
    """When a patient submits an isolated caregiver statement, runner records answered_by='caregiver' and confidence=Medium."""
    state = start_v3_session(
        checkin_id="chk-cg-test-1",
        patient_id="pat-cg-1",
        conditions=["diabetes"],
        language="roman_ur",
    )
    next_state = next_turn(state, phrase)

    assert next_state.get("answered_by") == "caregiver"
    assert next_state.get("known_slots", {}).get("answered_by") == "caregiver"

    summary = finish_v3_session(next_state)
    assert summary.get("answered_by") == "caregiver"
    for intake in summary.get("intakes", []):
        assert intake.get("answered_by") == "caregiver"
        assert intake.get("confidence") == "Medium"


@pytest.mark.parametrize("distractor", LOOKALIKE_NEGATIVE_PHRASES)
def test_v3_runner_preserves_patient_for_distractors(distractor: str):
    """Look-alike phrases mentioning parents giving advice do not alter answered_by to caregiver."""
    state = start_v3_session(
        checkin_id="chk-cg-distractor-1",
        patient_id="pat-cg-2",
        conditions=["diabetes"],
        language="roman_ur",
    )
    next_state = next_turn(state, distractor)

    assert next_state.get("answered_by") != "caregiver"
    assert next_state.get("known_slots", {}).get("answered_by") != "caregiver"


def test_caregiver_glucose_45_low_sugar_rules_fire_and_compares_clean():
    """'ammi ki taraf se sugar 45 hai' -> glucose 45 recorded, low-sugar rules fire, matches baseline level."""
    # Caregiver run
    s_cg = start_v3_session("chk-cg-g45", "pat-1", ["diabetes"], language="roman_ur")
    s_cg = next_turn(s_cg, "ammi ki taraf se theek hain")  # greeting
    s_cg = next_turn(s_cg, "ammi ki taraf se sugar 45 hai")  # reading
    assert s_cg.get("answered_by") == "caregiver"
    if s_cg.get("awaiting_glucose_unit"):
        s_cg = next_turn(s_cg, "mg/dL")
    assert s_cg["readings"].get("glucose") == 45.0
    assert s_cg.get("possible_severe_low") is True

    # Baseline run without caregiver phrase
    s_base = start_v3_session("chk-base-g45", "pat-1", ["diabetes"], language="roman_ur")
    s_base = next_turn(s_base, "theek hain")
    s_base = next_turn(s_base, "sugar 45 hai")
    assert s_base.get("answered_by") != "caregiver"
    if s_base.get("awaiting_glucose_unit"):
        s_base = next_turn(s_base, "mg/dL")
    assert s_base["readings"].get("glucose") == 45.0
    assert s_base.get("possible_severe_low") is True

    sum_cg = finish_v3_session(s_cg)
    sum_base = finish_v3_session(s_base)

    lvl_cg = LEVEL_ORDER.get(sum_cg["intakes"][0]["level"], 0)
    lvl_base = LEVEL_ORDER.get(sum_base["intakes"][0]["level"], 0)
    assert lvl_cg >= lvl_base, "Caregiver level must be identical or higher, never lower"
    assert sum_cg["intakes"][0]["readings"][0]["value"] == 45.0


def test_caregiver_glucose_250_recorded_and_compares_clean():
    """'ammi ki taraf se sugar 250 hai' -> glucose 250 recorded, level identical to clean answer."""
    s_cg = start_v3_session("chk-cg-g250", "pat-2", ["diabetes"], language="roman_ur")
    s_cg = next_turn(s_cg, "ammi ki taraf se theek hain")
    s_cg = next_turn(s_cg, "ammi ki taraf se sugar 250 hai")
    assert s_cg.get("answered_by") == "caregiver"
    assert s_cg["readings"].get("glucose") == 250.0

    s_base = start_v3_session("chk-base-g250", "pat-2", ["diabetes"], language="roman_ur")
    s_base = next_turn(s_base, "theek hain")
    s_base = next_turn(s_base, "sugar 250 hai")
    assert s_base["readings"].get("glucose") == 250.0

    sum_cg = finish_v3_session(s_cg)
    sum_base = finish_v3_session(s_base)

    lvl_cg = LEVEL_ORDER.get(sum_cg["intakes"][0]["level"], 0)
    lvl_base = LEVEL_ORDER.get(sum_base["intakes"][0]["level"], 0)
    assert lvl_cg >= lvl_base
    assert sum_cg["intakes"][0]["readings"][0]["value"] == 250.0


def test_caregiver_bp_crisis_185_125_recorded_and_compares_clean():
    """'abbu ke liye: BP 185/125' -> BP recorded, crisis path, level identical or higher."""
    s_cg = start_v3_session("chk-cg-bp", "pat-3", ["hypertension"], language="roman_ur")
    s_cg = next_turn(s_cg, "abbu ke liye: theek hain")
    s_cg = next_turn(s_cg, "abbu ke liye: BP 185/125")
    assert s_cg.get("answered_by") == "caregiver"
    assert s_cg["readings"].get("blood_pressure_systolic") == 185
    assert s_cg["readings"].get("blood_pressure_diastolic") == 125

    s_base = start_v3_session("chk-base-bp", "pat-3", ["hypertension"], language="roman_ur")
    s_base = next_turn(s_base, "theek hain")
    s_base = next_turn(s_base, "BP 185/125")
    assert s_base["readings"].get("blood_pressure_systolic") == 185
    assert s_base["readings"].get("blood_pressure_diastolic") == 125

    sum_cg = finish_v3_session(s_cg)
    sum_base = finish_v3_session(s_base)

    lvl_cg = LEVEL_ORDER.get(sum_cg["intakes"][0]["level"], 0)
    lvl_base = LEVEL_ORDER.get(sum_base["intakes"][0]["level"], 0)
    assert lvl_cg >= lvl_base
    assert lvl_cg >= LEVEL_ORDER["review"], "Crisis BP must escalate to review or higher"


def test_caregiver_adherence_affirmative():
    """'ammi ki taraf se haan dawai li' on adherence question -> adherent + caregiver."""
    state = start_v3_session("chk-cg-adh", "pat-4", ["diabetes"], language="roman_ur")
    state["step"] = "adherence_diabetes"
    state["current_question"] = "Kya aap ne dawai li?"

    next_st = next_turn(state, "ammi ki taraf se haan dawai li")
    assert next_st.get("answered_by") == "caregiver"
    assert next_st["known_slots"].get("adherence_diabetes") is True
    assert next_st.get("awaiting_adherence_clarification") is None


def test_caregiver_prefix_on_every_answer_whole_checkin():
    """Caregiver prefix on every answer for a whole check-in completes normally, readings kept, ended_early_off_topic is False."""
    cg_answers = [
        "ammi ki taraf se theek hain",
        "ammi ki taraf se sugar 120 hai",
        "ammi ki taraf se haan glucometer hai",
        "ammi ki taraf se koi alamat nahi",
        "ammi ki taraf se paon theek hain",
        "ammi ki taraf se haan dawai li",
        "ammi ki taraf se walk karti hain",
        "ammi ki taraf se sab theek hai",
    ]
    base_answers = [
        "theek hain",
        "sugar 120 hai",
        "haan glucometer hai",
        "koi alamat nahi",
        "paon theek hain",
        "haan dawai li",
        "walk karti hain",
        "sab theek hai",
    ]

    # Caregiver check-in
    s_cg = start_v3_session("chk-cg-full", "pat-5", ["diabetes"], language="roman_ur")
    for ans in cg_answers:
        if s_cg.get("completed"):
            break
        s_cg = next_turn(s_cg, ans)

    sum_cg = finish_v3_session(s_cg)
    assert s_cg.get("ended_early_off_topic") is False
    assert sum_cg.get("answered_by") == "caregiver"
    assert sum_cg["intakes"][0]["confidence"] == "Medium"
    assert len(sum_cg["intakes"][0]["readings"]) >= 1
    assert sum_cg["intakes"][0]["readings"][0]["value"] == 120.0

    # Clean check-in
    s_base = start_v3_session("chk-base-full", "pat-5", ["diabetes"], language="roman_ur")
    for ans in base_answers:
        if s_base.get("completed"):
            break
        s_base = next_turn(s_base, ans)

    sum_base = finish_v3_session(s_base)
    assert s_base.get("ended_early_off_topic") is False
    assert sum_base.get("answered_by") == "patient"
    assert sum_base["intakes"][0]["confidence"] == "High"

    lvl_cg = LEVEL_ORDER.get(sum_cg["intakes"][0]["level"], 0)
    lvl_base = LEVEL_ORDER.get(sum_base["intakes"][0]["level"], 0)
    assert lvl_cg >= lvl_base


def test_caregiver_only_statement_never_triggers_strike_rule():
    """Answering ONLY a caregiver statement repeatedly must acknowledge but NEVER terminate via strike rule."""
    state = start_v3_session("chk-cg-strike", "pat-6", ["diabetes"], language="roman_ur")
    for i in range(5):
        state = next_turn(state, "ammi ki taraf se")
        assert state.get("ended_early_off_topic") is False, f"Ended early on turn {i+1}!"
        assert state.get("answered_by") == "caregiver"
        assert state.get("options") != ["Continue check-in", "Need urgent help", "Finish later"]


def test_caregiver_intro_alone_for_whole_checkin_records_no_yes_no():
    """Usman R2: An intro alone for a whole check-in must never record yes/no for any slot."""
    intro = "I am answering for my mother"
    s = start_v3_session("chk-cg-intro-only", "pat-intro-1", ["diabetes"], language="en")
    for _ in range(6):
        if s.get("completed"):
            break
        s = next_turn(s, intro)

    assert s.get("answered_by") == "caregiver"
    known = s.get("known_slots", {})
    # No slot should be set to boolean True or False from the intro
    for slot, val in known.items():
        if slot == "answered_by":
            continue
        assert val not in (True, False), f"Slot '{slot}' was incorrectly recorded as {val} from caregiver intro!"


def test_caregiver_english_adherence_affirmative():
    """Usman R2: 'I'm answering for my mother, yes she took her medicine' -> adherent + caregiver."""
    state = start_v3_session("chk-cg-adh-en", "pat-adh-en", ["diabetes"], language="en")
    state["step"] = "adherence_diabetes"
    state["current_question"] = "Did you take your diabetes medication as prescribed?"

    next_st = next_turn(state, "I'm answering for my mother, yes she took her medicine")
    assert next_st.get("answered_by") == "caregiver"
    assert next_st["known_slots"].get("adherence_diabetes") is True
    assert next_st.get("awaiting_adherence_clarification") is None


def test_caregiver_english_glucose_45():
    """Usman R2: 'I am answering for my father, sugar 45' -> glucose 45."""
    s = start_v3_session("chk-cg-g45-en", "pat-g45-en", ["diabetes"], language="en")
    s = next_turn(s, "hello")
    s = next_turn(s, "I am answering for my father, sugar 45")
    assert s.get("answered_by") == "caregiver"
    if s.get("awaiting_glucose_unit"):
        s = next_turn(s, "mg/dL")
    assert s["readings"].get("glucose") == 45.0
    assert s.get("possible_severe_low") is True
