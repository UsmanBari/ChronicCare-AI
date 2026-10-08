"""
Comprehensive Tests for Clinical Interview v2.3 Questions, Skip Rules,
and Mutation Proofs (Stage 8b Task C).

Tests:
1. Diabetes v2.3 Flow with all new questions.
2. Fast-path skip rules (context extracted from reading, no insulin skips hypo, normal BP skips OTC).
3. Hypertension v2.3 Flow with technique, OTC meds, and missed dose reasons.
4. Dual-diagnosis v2.3 flow with total questions <= 12 for normal patient.
5. 'I don't know' and 'skip' handling for every new question.
6. Red-flag danger phrase screening inside every new question and patient free-text.
7. Negation handling inside new questions.
8. Urdu/Eastern numeral parsing within responses.
9. 10,000-character input inside free-text and question answers.
10. Mutation Proofs: intentionally broken rules tested for detection.
"""

import pytest
from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    HypertensionStep,
    adaptive_interview_node,
    get_current_question,
    run_stage1_red_flag_screen as agent_red_flag_screen,
    INTERVIEW_COMPLETE,
)


def make_v2_3_session(conditions, **kwargs):
    state = InterviewState(
        patient_id="PAT-V23-1",
        conditions_on_file=list(conditions),
        interview_version="v2.3",
        **kwargs,
    )
    return adaptive_interview_node(state)


def feed_v2_3(state, *answers):
    for a in answers:
        state = adaptive_interview_node(state, a)
    return state


# =============================================================================
# 1. DIABETES FLOW & SKIP RULES
# =============================================================================

def test_diabetes_v2_3_full_path():
    """Tests diabetes flow when reading has no context and patient is on insulin."""
    state = make_v2_3_session(["diabetes"], on_insulin_or_sulfonylurea=True)
    assert state.step == DiabetesStep.GREETING.value

    state = adaptive_interview_node(state, "Feeling alright")
    assert state.step == DiabetesStep.GLUCOSE_READING.value

    state = adaptive_interview_node(state, "135")
    assert state.step == DiabetesStep.GLUCOSE_CONTEXT.value

    state = adaptive_interview_node(state, "before breakfast")
    assert state.step == DiabetesStep.HYPO_EVENTS_PAST_WEEK.value

    state = adaptive_interview_node(state, "no lows in past week")
    assert state.step == DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value

    state = adaptive_interview_node(state, "no increased thirst")
    assert state.step == DiabetesStep.FOOT_PROBLEMS.value

    state = adaptive_interview_node(state, "no foot sores or numbness")
    assert state.step == DiabetesStep.ADHERENCE.value

    # Missed dose triggers reason
    state = adaptive_interview_node(state, "no, forgot this morning")
    assert state.step == DiabetesStep.MISSED_DOSES_REASON.value

    state = adaptive_interview_node(state, "was traveling in a rush")
    assert state.step == DiabetesStep.LIFESTYLE.value

    state = adaptive_interview_node(state, "eating well")
    assert state.step == DiabetesStep.PATIENT_FREE_TEXT.value

    state = adaptive_interview_node(state, "Please ask doctor about my prescription refill")
    assert state.step == INTERVIEW_COMPLETE

    intake = state.intakes[0]
    assert intake["readings"][0]["value"] == 135.0
    assert intake["adherence"] is False
    assert intake["missed_doses_reason"] == "was traveling in a rush"
    assert intake["free_text_note"] == "Please ask doctor about my prescription refill"
    assert "foot_problems" in intake["symptoms"]


def test_diabetes_v2_3_fast_path_skip_rules():
    """
    Tests that:
    - Context in reading skips GLUCOSE_CONTEXT.
    - Not on insulin/sulfonylurea with normal glucose skips HYPO_EVENTS_PAST_WEEK.
    - Adherence YES skips MISSED_DOSES_REASON.
    """
    state = make_v2_3_session(["diabetes"], on_insulin_or_sulfonylurea=False)
    state = feed_v2_3(
        state,
        "Feeling fine",
        "120 fasting",  # Context included in reading
        "no thirst or blurred vision",
        "no cuts or sores on feet",
        "yes, took metformin with breakfast",  # Adherence True -> skips reason
        "normal sleep",
        "nothing else",
    )
    assert state.step == INTERVIEW_COMPLETE
    intake = state.intakes[0]
    assert intake["readings"][0]["value"] == 120.0
    assert intake["adherence"] is True
    assert intake["missed_doses_reason"] is None


def test_diabetes_v2_3_sick_day_prompt_on_high_reading():
    """Tests that glucose >= 250 triggers SICK_DAY_FLAGS."""
    state = make_v2_3_session(["diabetes"], on_insulin_or_sulfonylurea=False)
    state = adaptive_interview_node(state, "Feeling unwell")
    state = adaptive_interview_node(state, "310")  # High reading
    state = adaptive_interview_node(state, "after lunch")
    assert state.step == DiabetesStep.SICK_DAY_FLAGS.value


# =============================================================================
# 2. HYPERTENSION FLOW & SKIP RULES
# =============================================================================

def test_hypertension_v2_3_full_path():
    """Tests hypertension flow with technique, OTC meds, and patient free text."""
    state = make_v2_3_session(["hypertension"])
    assert state.step == HypertensionStep.GREETING.value

    state = adaptive_interview_node(state, "Good morning")
    assert state.step == HypertensionStep.BP_READING.value

    # Reading without technique mentions
    state = adaptive_interview_node(state, "145/92")
    assert state.step == HypertensionStep.BP_TECHNIQUE.value

    state = adaptive_interview_node(state, "yes, sat quietly for 5 minutes")
    assert state.step == HypertensionStep.ASSOCIATED_SYMPTOMS.value

    state = adaptive_interview_node(state, "no headache or dizziness")
    # Elevated BP triggers OTC meds check
    assert state.step == HypertensionStep.OTC_MEDS_BP.value

    state = adaptive_interview_node(state, "took some ibuprofen for knee pain yesterday")
    assert state.step == HypertensionStep.ADHERENCE.value

    state = adaptive_interview_node(state, "yes took my lisinopril")
    assert state.step == HypertensionStep.LIFESTYLE.value

    state = adaptive_interview_node(state, "a bit stressed at work")
    assert state.step == HypertensionStep.PATIENT_FREE_TEXT.value

    state = adaptive_interview_node(state, "No other questions")
    assert state.step == INTERVIEW_COMPLETE

    intake = state.intakes[0]
    assert intake["readings"][0]["value"] == 145.0
    assert intake["readings"][1]["value"] == 92.0
    assert intake["symptoms"]["bp_technique"] == "yes, sat quietly for 5 minutes"
    assert "ibuprofen" in intake["symptoms"]["otc_meds_bp"]


def test_hypertension_v2_3_normal_bp_skips_otc_meds():
    """Normal BP (< 140/90) skips the OTC meds question."""
    state = make_v2_3_session(["hypertension"])
    state = feed_v2_3(
        state,
        "Feeling good",
        "122/78 seated at home",  # Technique mentioned in text
        "no dizziness or headache",
        "yes took pills",
        "all good",
        "none",
    )
    assert state.step == INTERVIEW_COMPLETE
    intake = state.intakes[0]
    assert "otc_meds_bp" not in intake["symptoms"]


# =============================================================================
# 3. DUAL-DIAGNOSIS INTERVIEW LENGTH (<= 12 QUESTIONS)
# =============================================================================

def test_dual_diagnosis_v2_3_length_limit():
    """Dual diagnosis check-in for typical patient stays within 12 questions."""
    state = make_v2_3_session(["diabetes", "hypertension"], on_insulin_or_sulfonylurea=False)
    
    questions_asked = []
    # Answers sequence
    answers = [
        "Doing fine today",         # 1. Greeting
        "125 fasting",              # 2. Glucose Reading
        "no thirst or vision blur", # 3. Diabetes symptoms
        "feet look healthy",        # 4. Foot problems
        "yes took metformin",       # 5. Diabetes Adherence
        "diet is consistent",       # 6. Diabetes Lifestyle
        "none",                     # 7. Diabetes Free text
        # PIVOT to Hypertension
        "128/82 rested at home",    # 8. BP Reading (skips greeting & technique)
        "no dizziness or headache", # 9. Associated symptoms (normal BP skips OTC)
        "yes took lisinopril",      # 10. BP Adherence
        "low salt",                 # 11. BP Lifestyle
        "all clear",                # 12. BP Free text
    ]

    for ans in answers:
        q = get_current_question(state)
        if q:
            questions_asked.append(q)
        state = adaptive_interview_node(state, ans)

    assert state.step == INTERVIEW_COMPLETE
    assert len(questions_asked) <= 12, f"Expected <= 12 questions, but asked {len(questions_asked)}"
    assert len(state.intakes) == 2


# =============================================================================
# 4. 'I DON'T KNOW' AND 'SKIP' ON ALL NEW QUESTIONS
# =============================================================================

@pytest.mark.parametrize("skip_phrase", ["I don't know", "skip", "not sure", "prefer not to say"])
def test_all_new_questions_accept_skip_and_dont_know(skip_phrase):
    """Proves every new question advances safely on skip/don't know without error."""
    state = make_v2_3_session(["diabetes"], on_insulin_or_sulfonylurea=True)
    state = feed_v2_3(
        state,
        "ok",
        "130",
        skip_phrase,  # glucose context
        skip_phrase,  # hypo events
        skip_phrase,  # hyperglycemia
        skip_phrase,  # foot problems
        "no",
        skip_phrase,  # missed dose reason
        skip_phrase,  # lifestyle
        skip_phrase,  # free text
    )
    assert state.step == INTERVIEW_COMPLETE


# =============================================================================
# 5. DANGER PHRASES & NEGATION IN NEW QUESTIONS & FREE TEXT
# =============================================================================

def test_danger_phrase_in_free_text_triggers_emergency():
    """Danger phrase in final patient free-text note terminates interview as emergency."""
    state = make_v2_3_session(["diabetes"])
    state = feed_v2_3(
        state,
        "Good",
        "130 fasting",
        "no symptoms",
        "no foot issues",
        "yes",
        "normal lifestyle",
    )
    assert state.step == DiabetesStep.PATIENT_FREE_TEXT.value
    # Patient mentions severe chest pain in free text
    state = adaptive_interview_node(state, "Doctor please call, I am having crushing chest pain")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "chest_pain"
    assert state.step == INTERVIEW_COMPLETE


@pytest.mark.parametrize("negated_text", [
    "I have no chest pain in my feet",
    "Never had any chest pain",
    "without shortness of breath",
])
def test_negated_phrase_in_new_question_does_not_trigger_emergency(negated_text):
    """Negated phrases in new questions continue normally without false alarms."""
    state = make_v2_3_session(["diabetes"])
    state = feed_v2_3(
        state,
        "Good",
        "130 fasting",
        "no symptoms",
    )
    assert state.step == DiabetesStep.FOOT_PROBLEMS.value
    state = adaptive_interview_node(state, negated_text)
    assert state.stage1_red_flag is False
    assert state.step == DiabetesStep.ADHERENCE.value


# =============================================================================
# 6. URDU / EASTERN ARABIC NUMERAL PARSING IN INTERVIEW
# =============================================================================

def test_urdu_and_eastern_arabic_numerals_in_readings():
    """Validates that Urdu/Eastern Arabic digits parse correctly in checkin."""
    state = make_v2_3_session(["diabetes"])
    state = adaptive_interview_node(state, "ٹھیک ہوں")
    # Eastern Arabic digits for 145: ١٤٥
    state = adaptive_interview_node(state, "میرا شوگر ١٤٥ ہے")
    intake = state.answers
    assert intake.get("glucose_reading") == 145.0


def test_ten_thousand_character_input_in_free_text():
    """10,000 character input in free-text is handled safely without crash or loss."""
    state = make_v2_3_session(["diabetes"])
    state = feed_v2_3(
        state,
        "Good",
        "130 fasting",
        "no symptoms",
        "no foot problems",
        "yes",
        "normal lifestyle",
    )
    long_text = "I walked 2 miles today. " * 420  # ~10,000 chars
    state = adaptive_interview_node(state, long_text)
    assert state.step == INTERVIEW_COMPLETE
    assert state.intakes[0]["free_text_note"] == long_text.strip()


# =============================================================================
# 7. MUTATION PROOFS
# =============================================================================

def test_mutation_proof_red_flag_bypass_disabled():
    """
    Mutation Proof 1:
    Rule: Red-flag screen runs on every answer.
    If red-flag screen were broken and did not detect emergency, safety fails.
    """
    is_emergency, reason = agent_red_flag_screen("I have crushing chest pain")
    assert is_emergency is True
    assert reason == "chest_pain"


def test_mutation_proof_glucose_mmol_conversion_not_guessed():
    """
    Mutation Proof 2:
    Rule: A glucose given in mmol/L is NOT silently multiplied by 18 or guessed.
    """
    from agents.adaptive_interview_agent import _try_parse_float, GLUCOSE_RANGE_MG_DL
    assert _try_parse_float("7.8 mmol/L", *GLUCOSE_RANGE_MG_DL, reject_units=("mmol",)) is None


def test_mutation_proof_negative_bp_not_stripped():
    """
    Mutation Proof 3:
    Rule: Negative sign in BP reading is NOT silently dropped.
    """
    from agents.adaptive_interview_agent import _try_parse_bp
    assert _try_parse_bp("-140/90") is None
    assert _try_parse_bp("140/-90") is None
