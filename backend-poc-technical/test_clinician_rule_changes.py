"""
Unit & Integration Tests for Clinician-Approved Rule Changes (13 Oct 2026).
Decisions by Dr Shaiza Jabbar (Hearts International Hospital) and Capt Dr Talha Yasin (CMH Rawalpindi).

Covers:
1. Chest pain radiating to left arm/jaw, crushing chest pain (EN, Roman Urdu, Urdu) = emergency;
   negations ("no chest pain") not triggered; past events ("chest pain last year") = not emergency.
2. "Cannot keep fluids down" / "vomiting nonstop" = URGENT (not emergency).
3. "Confused by my morning pills" = not emergency; orientation question gate (no/unclear -> emergency, yes -> review).
4. Stroke extras (dizziness, blurred vision, headache):
   - with weakness/droop = emergency;
   - alone, age >= 65 with heart/brain history OR >= 2 conditions (HTN, DM, IHD) = urgent with CT scan advice;
   - alone, anyone else = review;
   - age 64 vs 65 boundary test.
5. Narrative answers: hypo_events_past_week and associated_symptoms = review; sick_day_flags and foot_problems = routine.
6. Monotonic level invariant: levels never fall inside one check-in.
"""

import copy
import pytest
from agents.adaptive_interview_agent import (
    RED_FLAG_LEVELS,
    adaptive_interview_node,
    get_red_flag_level,
    run_stage1_red_flag_screen as screen_rf,
    InterviewState,
    DiabetesStep,
    HypertensionStep,
    INTERVIEW_COMPLETE,
)
from agents.input_triage import classify_input, screen_multilingual_danger_phrases
from agents.triage_protocol import (
    Trigger,
    start_protocol,
    advance_protocol,
    current_protocol_question,
    evaluate_stroke_extras,
    _raise_level,
    LEVEL_RANK,
    GLUCOSE,
)


# =============================================================================
# 1. Decision 1: Radiating and Crushing Chest Pain & Negation / Past Event Guards
# =============================================================================
def test_chest_pain_radiating_and_crushing_phrases_trigger_emergency():
    """Crushing chest pain and pain radiating to left arm/jaw must trigger emergency in EN, Roman Urdu, and Urdu."""
    emergency_phrases = [
        # English
        "crushing chest pain",
        "crushing pain in my chest",
        "pain going down my left arm",
        "pain in my left arm and jaw",
        "left jaw pain with pressure",
        "pain in my left arm",
        "left arm pain",
        "left jaw pain",
        # Roman Urdu
        "bayein bazu me dard",
        "bayein bazu mein dard",
        "bayein bazu aur jabray me dard",
        "bayein jabray me dard",
        "baayein baazu me dard",
        "seene me dabao aur bayein bazu me dard",
        "seene mein shadeed dabao aur bayein baazu me dard",
        # Urdu Script
        "بائیں بازو میں درد",
        "بائیں جبڑے میں درد",
        "بائیں بازو اور جبڑے میں درد",
        "سینے میں شدید درد اور بائیں بازو میں درد",
        "سینے پر شدید دباؤ اور بائیں بازو میں درد",
    ]
    for phrase in emergency_phrases:
        triggered, reason = screen_rf(phrase)
        assert triggered is True, f"Failed to flag emergency red-flag for: '{phrase}'"
        assert reason == "chest_pain", f"Expected category chest_pain for: '{phrase}', got '{reason}'"
        assert get_red_flag_level(reason) == "emergency"

        res = classify_input(phrase)
        assert res.is_emergency is True, f"classify_input failed emergency for: '{phrase}'"


def test_chest_pain_negations_and_past_events():
    """Negation ('no chest pain') and past events ('chest pain last year') must NOT trigger emergency."""
    negated_phrases = [
        "no chest pain",
        "I have no chest pain",
        "denies chest pain",
        "never had chest pain",
        "without chest pain",
    ]
    for phrase in negated_phrases:
        triggered, reason = screen_rf(phrase)
        assert triggered is False, f"Erroneously flagged negated phrase: '{phrase}' (reason: {reason})"

    past_phrases = [
        "chest pain last year",
        "I had chest pain last year",
        "had pain in my left arm months ago",
        "crushing chest pain years ago",
        "seene me dard pichle saal tha",
        "seene me dard pehle tha",
        "سینے میں درد گزشتہ سال تھا",
    ]
    for phrase in past_phrases:
        triggered, reason = screen_rf(phrase)
        assert triggered is False, f"Past event erroneously triggered emergency red-flag: '{phrase}'"

        res = classify_input(phrase)
        assert res.is_emergency is False, f"Past event flagged as emergency in classify_input: '{phrase}'"


# =============================================================================
# 2. Decision 2: Vomiting / Fluids Inability = URGENT (Not Emergency)
# =============================================================================
def test_vomiting_fluids_down_maps_to_urgent_not_emergency():
    """Vomiting nonstop and unable to keep fluids down must map to urgent, never emergency."""
    vomiting_phrases = [
        # English
        "vomiting nonstop",
        "vomiting non-stop",
        "cannot keep fluids down",
        "can't keep fluids down",
        "unable to keep fluids down",
        "cannot keep anything down",
        "can't keep anything down",
        "throwing up everything",
        # Roman Urdu
        "musalsal ultiyan",
        "ulti ruk nahi rahi",
        "paani bhi nahi rukta",
        # Urdu Script
        "مسلسل الٹیاں",
        "الٹی رک نہیں رہی",
        "پانی بھی نہیں رک رہا",
    ]
    for phrase in vomiting_phrases:
        triggered, reason = screen_rf(phrase)
        assert triggered is True, f"Expected red flag screen to catch vomiting: '{phrase}'"
        assert reason in ("unable_to_keep_fluids", "dka_vomiting_high_glucose")

        level = get_red_flag_level(reason)
        assert level == "urgent", f"Expected level 'urgent' for vomiting '{phrase}', got '{level}'"

        res = classify_input(phrase)
        assert res.is_emergency is False, f"Vomiting phrase should not be emergency: '{phrase}'"
        assert res.is_urgent_safety is True, f"Vomiting phrase should be urgent safety: '{phrase}'"


def test_vomiting_in_triage_protocol_produces_urgent_result():
    """In advance_protocol, reporting cannot keep fluids down produces urgent triage level."""
    trigger = Trigger("bp_severe", "crisis_bp", 1)
    state = start_protocol(trigger, readings={"blood_pressure_systolic": 190.0, "blood_pressure_diastolic": 110.0}, age_years=50)
    next_state = advance_protocol(state, "I have been vomiting nonstop and cannot keep fluids down")

    assert next_state.complete is True
    assert next_state.result is not None
    assert next_state.result["level"] == "urgent"
    assert "unable to keep fluids" in next_state.result["reasons"][0]


# =============================================================================
# 3. Decision 3: "Confused" Removed from Word Screen & Orientation Gate
# =============================================================================
def test_confused_by_my_morning_pills_does_not_trigger_emergency():
    """The word 'confused' alone (e.g. conversational medication confusion) must not trigger emergency."""
    phrase = "I am confused by my morning pills"
    triggered, reason = screen_rf(phrase)
    assert triggered is False, f"Conversational 'confused' must not trigger red-flag emergency: reason={reason}"

    res = classify_input(phrase)
    assert res.is_emergency is False


def test_free_text_disorientation_wording_triggers_emergency():
    """Disorientation wording ('don't know where I am', 'samajh nahi aa raha main kahan hoon') must trigger emergency."""
    # 1. English acute disorientation
    phrase_en = "I feel confused and I don't know where I am"
    trig_en, reason_en = screen_rf(phrase_en)
    assert trig_en is True, "Disorientation phrase was silently ignored"
    assert reason_en == "confusion"
    assert get_red_flag_level(reason_en) == "emergency"
    res_en = classify_input(phrase_en)
    assert res_en.is_emergency is True

    # 2. Urdu acute disorientation
    phrase_ur = "mujhe samajh nahi aa raha main kahan hoon"
    trig_ur, reason_ur = screen_rf(phrase_ur)
    assert trig_ur is True, "Urdu disorientation phrase was silently ignored"
    assert reason_ur == "confusion"
    assert get_red_flag_level(reason_ur) == "emergency"
    res_ur = classify_input(phrase_ur)
    assert res_ur.is_emergency is True

    # 3. Conversational medication confusion remains non-emergency
    phrase_med = "I am confused by my morning pills"
    trig_med, reason_med = screen_rf(phrase_med)
    assert trig_med is False, "Conversational pill confusion must not trigger emergency"
    res_med = classify_input(phrase_med)
    assert res_med.is_emergency is False


def test_free_text_confusion_in_normal_checkin_flow_outside_glucose_low():
    """Through normal check-in flow outside glucose_low, disorientation triggers emergency while pill confusion does not."""
    # Hypertension check-in (completely outside glucose_low protocol)
    # A. Patient reports disorientation: triggers emergency
    st_en = InterviewState(patient_id="p_disorient_1", conditions_on_file=["hypertension"], interview_version="v2.3")
    st_en = adaptive_interview_node(st_en, patient_response=None)
    st_en = adaptive_interview_node(st_en, "I feel confused and I don't know where I am")
    assert st_en.stage1_red_flag is True
    assert st_en.stage1_reason == "confusion"
    assert st_en.step == INTERVIEW_COMPLETE
    assert st_en.intake["emergency"] is True

    # B. Patient reports Urdu disorientation: triggers emergency
    st_ur = InterviewState(patient_id="p_disorient_2", conditions_on_file=["hypertension"], interview_version="v2.3")
    st_ur = adaptive_interview_node(st_ur, patient_response=None)
    st_ur = adaptive_interview_node(st_ur, "mujhe samajh nahi aa raha main kahan hoon")
    assert st_ur.stage1_red_flag is True
    assert st_ur.stage1_reason == "confusion"
    assert st_ur.step == INTERVIEW_COMPLETE
    assert st_ur.intake["emergency"] is True

    # C. Patient reports pill confusion: does NOT trigger emergency
    st_med = InterviewState(patient_id="p_med_conf", conditions_on_file=["hypertension"], interview_version="v2.3")
    st_med = adaptive_interview_node(st_med, patient_response=None)
    st_med = adaptive_interview_node(st_med, "I am confused by my morning pills")
    assert st_med.stage1_red_flag is False
    assert st_med.step != INTERVIEW_COMPLETE  # check-in continues to next question


def test_orientation_gate_glucose_low():
    """When neuro symptoms/confusion are reported in glucose_low, orientation question gates emergency vs review."""
    trigger = Trigger("glucose_low", "low_glucose", 3)

    # Case A: Oriented = YES -> review (NOT emergency)
    state_a = start_protocol(trigger, readings={GLUCOSE: 60.0}, age_years=50)
    q0 = current_protocol_question(state_a)
    assert "confused" in q0 or "neuro" in q0
    # Patient answers Yes to neuro
    state_a = advance_protocol(state_a, "yes")
    # Orientation question must now be asked
    q1 = current_protocol_question(state_a)
    assert "oriented in time, place and person" in q1

    # Patient answers YES (oriented)
    state_a = advance_protocol(state_a, "yes")
    assert state_a.complete is False  # continues to can_swallow
    # Answer can_swallow = yes, symptoms = no, context = missed meal
    state_a = advance_protocol(state_a, "yes")
    state_a = advance_protocol(state_a, "no")
    state_a = advance_protocol(state_a, "missed meal")
    assert state_a.complete is True
    assert state_a.result["level"] == "review"
    assert any("oriented" in r for r in state_a.result["reasons"])

    # Case B: Oriented = NO -> EMERGENCY
    state_b = start_protocol(trigger, readings={GLUCOSE: 60.0}, age_years=50)
    state_b = advance_protocol(state_b, "yes")  # neuro = yes
    state_b = advance_protocol(state_b, "no")   # orientation = no
    assert state_b.complete is True
    assert state_b.result["level"] == "emergency"

    # Case C: Unclear / Unknown orientation -> EMERGENCY ("unknown is never no")
    state_c = start_protocol(trigger, readings={GLUCOSE: 60.0}, age_years=50)
    state_c = advance_protocol(state_c, "yes")       # neuro = yes
    state_c = advance_protocol(state_c, "maybe idk")  # attempt 1 unclear
    state_c = advance_protocol(state_c, "still not sure")  # attempt 2 unclear -> treated as unknown
    assert state_c.complete is True
    assert state_c.result["level"] == "emergency"


# =============================================================================
# 4. Decision 4: Stroke Extras (Dizziness, Blurred Vision, Headache)
# =============================================================================
def test_stroke_extras_with_droop_or_weakness():
    """Stroke extras combined with weakness or droop must trigger emergency."""
    res1 = evaluate_stroke_extras({"dizziness": True, "droop": True})
    assert res1 is not None
    assert res1["level"] == "emergency"
    assert any("dizziness" in r for r in res1["reasons"])

    res2 = evaluate_stroke_extras("I have sudden one-sided weakness and a severe headache")
    assert res2 is not None
    assert res2["level"] == "emergency"
    assert any("headache" in r for r in res2["reasons"])


def test_stroke_extras_alone_high_risk_elderly():
    """Stroke extras alone in age >= 65 with heart/brain history or >=2 conditions get urgent with CT scan advice."""
    ct_advice = "Please go for an urgent CT scan today."

    # Age 70 with hypertension + diabetes -> urgent with CT text
    profile_htn_dm = {
        "date_of_birth": "1956-01-01",
        "conditions": ["hypertension", "diabetes"],
        "comorbidities": {},
    }
    res_70_multicond = evaluate_stroke_extras({"dizziness": True}, patient_profile=profile_htn_dm, age_years=70)
    assert res_70_multicond is not None
    assert res_70_multicond["level"] == "urgent"
    assert ct_advice in res_70_multicond["advice"]
    assert any(ct_advice in r for r in res_70_multicond["reasons"])

    # Age 70 with prior stroke history -> urgent with CT text
    profile_prior_stroke = {
        "date_of_birth": "1956-01-01",
        "conditions": ["hypertension"],
        "comorbidities": {"stroke_or_tia": True},
    }
    res_70_prior_stroke = evaluate_stroke_extras({"headache": True}, patient_profile=profile_prior_stroke, age_years=70)
    assert res_70_prior_stroke is not None
    assert res_70_prior_stroke["level"] == "urgent"
    assert ct_advice in res_70_prior_stroke["advice"]


def test_stroke_extras_alone_general_patient_and_boundary_64_vs_65():
    """Stroke extras alone in younger or low-risk patient = review; age 64 vs 65 boundary."""
    ct_advice = "Please go for an urgent CT scan today."

    # Age 40 healthy -> review
    profile_young = {"conditions": [], "comorbidities": {}}
    res_40 = evaluate_stroke_extras({"dizziness": True}, patient_profile=profile_young, age_years=40)
    assert res_40 is not None
    assert res_40["level"] == "review"
    assert ct_advice not in res_40["advice"]

    # Boundary: Age 64 with HTN + DM -> review (under 65)
    profile_conds = {"conditions": ["hypertension", "diabetes"], "comorbidities": {}}
    res_64 = evaluate_stroke_extras({"blurred_vision": True}, patient_profile=profile_conds, age_years=64)
    assert res_64 is not None
    assert res_64["level"] == "review"
    assert ct_advice not in res_64["advice"]

    # Boundary: Age 65 with HTN + DM -> urgent (65 boundary met)
    res_65 = evaluate_stroke_extras({"blurred_vision": True}, patient_profile=profile_conds, age_years=65)
    assert res_65 is not None
    assert res_65["level"] == "urgent"
    assert ct_advice in res_65["advice"]


# =============================================================================
# 5. Decision 5: Narrative Answers (hypo_events_past_week, associated_symptoms)
# =============================================================================
def test_narrative_answers_review_escalation():
    """Affirmative hypo_events_past_week and associated_symptoms raise level to review; sick-day and foot stay routine."""
    # 1. Diabetes flow with on_insulin_or_sulfonylurea=True -> hypo_events_past_week is asked
    state_dm = InterviewState(patient_id="p1", conditions_on_file=["diabetes"], on_insulin_or_sulfonylurea=True, interview_version="v2.3")
    state_dm = adaptive_interview_node(state_dm, patient_response=None)
    state_dm = adaptive_interview_node(state_dm, "Hello, feeling okay")   # greeting -> glucose_reading
    state_dm = adaptive_interview_node(state_dm, "120")                    # glucose_reading -> glucose_context
    state_dm = adaptive_interview_node(state_dm, "fasting")                # glucose_context -> hypo_events_past_week
    state_dm = adaptive_interview_node(state_dm, "Yes, I had low sugar twice last week") # hypo_events -> hyperglycemia_symptoms
    state_dm = adaptive_interview_node(state_dm, "no")                     # hyperglycemia_symptoms -> foot_problems
    state_dm = adaptive_interview_node(state_dm, "no")                     # foot_problems -> adherence
    state_dm = adaptive_interview_node(state_dm, "yes")                    # adherence -> lifestyle
    state_dm = adaptive_interview_node(state_dm, "normal")                 # lifestyle -> patient_free_text
    state_dm = adaptive_interview_node(state_dm, "none")                   # patient_free_text -> COMPLETE

    assert state_dm.step == INTERVIEW_COMPLETE
    assert state_dm.intake["requires_review"] is True
    assert state_dm.intake["level"] == "review"

    # 2. Hypertension flow -> associated_symptoms is asked
    state_htn = InterviewState(patient_id="p1_htn", conditions_on_file=["hypertension"], interview_version="v2.3")
    state_htn = adaptive_interview_node(state_htn, patient_response=None)
    state_htn = adaptive_interview_node(state_htn, "Hello")                # greeting -> bp_reading
    state_htn = adaptive_interview_node(state_htn, "125/80")               # bp_reading -> bp_technique
    state_htn = adaptive_interview_node(state_htn, "sitting quietly")      # bp_technique -> associated_symptoms
    state_htn = adaptive_interview_node(state_htn, "yes, slight headache and palpitations") # associated_symptoms -> adherence
    state_htn = adaptive_interview_node(state_htn, "yes")                  # adherence -> lifestyle
    state_htn = adaptive_interview_node(state_htn, "fine")                 # lifestyle -> patient_free_text
    state_htn = adaptive_interview_node(state_htn, "none")                 # patient_free_text -> COMPLETE

    assert state_htn.step == INTERVIEW_COMPLETE
    assert state_htn.intake["requires_review"] is True
    assert state_htn.intake["level"] == "review"


def test_sick_day_and_foot_problems_alone_stay_routine():
    """sick_day_flags and foot_problems affirmative alone stay routine (clinician has not decided)."""
    # Test foot_problems affirmative alone:
    state_dm = InterviewState(patient_id="p2", conditions_on_file=["diabetes"], interview_version="v2.3")
    state_dm = adaptive_interview_node(state_dm, patient_response=None)
    state_dm = adaptive_interview_node(state_dm, "Feeling fine")    # greeting -> glucose_reading
    state_dm = adaptive_interview_node(state_dm, "120")             # glucose_reading -> glucose_context
    state_dm = adaptive_interview_node(state_dm, "fasting")         # glucose_context -> hyperglycemia_symptoms
    state_dm = adaptive_interview_node(state_dm, "no")              # hyperglycemia_symptoms -> foot_problems
    state_dm = adaptive_interview_node(state_dm, "yes, small cut on left toe") # foot_problems -> adherence
    state_dm = adaptive_interview_node(state_dm, "yes")             # adherence -> lifestyle
    state_dm = adaptive_interview_node(state_dm, "fine")            # lifestyle -> patient_free_text
    state_dm = adaptive_interview_node(state_dm, "nothing")         # patient_free_text -> COMPLETE

    assert state_dm.step == INTERVIEW_COMPLETE
    assert state_dm.intake["requires_review"] is False
    assert state_dm.intake["level"] == "routine"

    # Test sick_day_flags affirmative alone (glucose >= 250):
    state_sick = InterviewState(patient_id="p3", conditions_on_file=["diabetes"], interview_version="v2.3")
    state_sick = adaptive_interview_node(state_sick, patient_response=None)
    state_sick = adaptive_interview_node(state_sick, "Hello")       # greeting -> glucose_reading
    state_sick = adaptive_interview_node(state_sick, "260")         # glucose_reading -> glucose_context
    state_sick = adaptive_interview_node(state_sick, "fasting")     # glucose_context -> sick_day_flags (since reading >= 250)
    state_sick = adaptive_interview_node(state_sick, "yes, mild cold and cough") # sick_day_flags -> hyperglycemia_symptoms
    state_sick = adaptive_interview_node(state_sick, "no")          # hyperglycemia_symptoms -> foot_problems
    state_sick = adaptive_interview_node(state_sick, "no")          # foot_problems -> adherence
    state_sick = adaptive_interview_node(state_sick, "yes")         # adherence -> lifestyle
    state_sick = adaptive_interview_node(state_sick, "eating ok")   # lifestyle -> patient_free_text
    state_sick = adaptive_interview_node(state_sick, "none")        # patient_free_text -> COMPLETE

    assert state_sick.step == INTERVIEW_COMPLETE
    assert state_sick.intake["requires_review"] is False
    assert state_sick.intake["level"] == "routine"


# =============================================================================
# 6. Safety Invariant: Triage Levels Only Rise, Never Fall
# =============================================================================
def test_triage_levels_never_fall_monotonic_check():
    """Triage levels only rise inside one check-in: routine < review < urgent < emergency."""
    levels = ["routine", "review", "urgent", "emergency"]
    for i, base_lvl in enumerate(levels):
        for j, candidate_lvl in enumerate(levels):
            raised = _raise_level(base_lvl, candidate_lvl)
            expected_rank = max(LEVEL_RANK[base_lvl], LEVEL_RANK[candidate_lvl])
            assert LEVEL_RANK[raised] == expected_rank
            assert LEVEL_RANK[raised] >= LEVEL_RANK[base_lvl]
