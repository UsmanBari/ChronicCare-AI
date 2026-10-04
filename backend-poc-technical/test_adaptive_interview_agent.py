"""
Tests for the Adaptive Interview Agent (Iteration 1).

Pure unit tests need no network, database or environment variables, so they run in CI
as-is. The integration tests at the bottom push the interview's output through the real
Reconciliation and Verification agents.
"""

import copy
import json

import pytest

from agents.adaptive_interview_agent import (
    INTERVIEW_COMPLETE,
    RED_FLAG_PATTERNS,
    InterviewState,
    _looks_affirmative,
    _try_parse_bp,
    _try_parse_float,
    adaptive_interview_node,
    build_checkin_bundle,
    build_checkin_origins,
    get_current_question,
    run_stage1_red_flag_screen as screen_red_flags,
)
from agents.reconciliation_agent import reconcile_bundles
from agents.verification_agent import verify_reconciliation
from data_sources.models import NormalizedObservation, NormalizedPatient


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def start(conditions, **kwargs):
    state = InterviewState(patient_id="P-1", conditions_on_file=list(conditions), **kwargs)
    return adaptive_interview_node(state)


def feed(state, *answers):
    for answer in answers:
        state = adaptive_interview_node(state, answer)
    return state


DIABETES_FULL = ["Feeling okay, a little tired", "142 fasting",
                 "A bit more thirsty than usual", "Yes, took it this morning", "No real changes"]
HTN_FULL = ["Mild headache today", "150/95", "A little dizzy, nothing severe",
            "Yes", "Sodium has been high this week"]


# ----------------------------------------------------------------------------
# Stage 1 red-flag screen
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("category,pattern",
                         [(c, p) for c, ps in RED_FLAG_PATTERNS.items() for p in ps])
def test_every_red_flag_phrase_triggers_its_own_category(category, pattern):
    assert screen_red_flags(f"I have {pattern}") == (True, category)


def test_ordinary_symptom_is_not_a_red_flag():
    assert screen_red_flags("I feel a bit dizzy today") == (False, None)


@pytest.mark.parametrize("text", [
    "No chest pain today",
    "I don't have chest pain",
    "without any chest pain",
    "I have never had chest pain",
    "no chest pain, no headache",
])
def test_negated_red_flag_is_not_flagged(text):
    assert screen_red_flags(text) == (False, None)


def test_negation_does_not_hide_a_second_symptom():
    assert screen_red_flags("no chest pain but I can't breathe") == (True, "breathing")


def test_unclear_negation_flags_conservatively():
    # the negation cue is more than 3 words before the phrase: flag, don't guess
    assert screen_red_flags("I am not sure what this is but it feels like chest pain") == (True, "chest_pain")


def test_curly_apostrophe_is_normalised():
    assert screen_red_flags("I can\u2019t breathe") == (True, "breathing")


def test_red_flag_screen_runs_on_every_answer_not_just_the_first():
    """FR-3: a red flag mentioned late in the interview must still end it."""
    state = feed(start(["diabetes"]), *DIABETES_FULL[:4])
    assert state.step == "lifestyle"
    state = adaptive_interview_node(state, "Actually I have chest pain right now")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "chest_pain"
    assert state.step == INTERVIEW_COMPLETE
    assert get_current_question(state) is None


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------
GLUCOSE = dict(minimum=20.0, maximum=600.0, reject_units=("mmol",))


@pytest.mark.parametrize("text,expected", [
    ("142 fasting", 142.0),
    ("it was 98.5", 98.5),
    ("at 10:30 am it was 140", 140.0),     # clock time must not be read as a reading
    ("5.6 mmol/L", None),                   # unit conversion is not guessed
    ("my sugar is 5", None),                # below plausible mg/dL range
    ("1000", None),                         # above plausible range
    ("fasting 95 and after lunch 140", None),   # two plausible numbers: ambiguous
    ("I don't have a glucometer", None),
])
def test_glucose_parsing(text, expected):
    assert _try_parse_float(text, **GLUCOSE) == expected


@pytest.mark.parametrize("text,expected", [
    ("150/95", [150, 95]),
    ("my bp is 130 over 85", [130, 85]),
    ("95/150", None),                       # systolic must exceed diastolic
    ("300/90", None),                       # implausible
    ("120/80 and then 125/82", None),       # ambiguous
    ("no cuff at home", None),
])
def test_bp_parsing(text, expected):
    assert _try_parse_bp(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("Yes", True),
    ("Yes, I took it this morning", True),
    ("I took it", True),
    ("no", False),
    ("I didn't take it", False),
    ("I did not take my medicine", False),
    ("I'm not taking it", False),
    ("No problem, I took it", True),        # idiom, not a refusal
    ("yesterday I forgot", False),          # 'yes' inside another word must not count
    ("yes but I forgot the evening dose", None),
    ("maybe", None),
])
def test_adherence_parsing(text, expected):
    assert _looks_affirmative(text) is expected


# ----------------------------------------------------------------------------
# Empty, zero, null and garbage input
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["0", "null", "N/A", "none", "nothing", "undefined", ".", "-5", "-120", "\u2212120", ""])
def test_unusable_glucose_inputs_count_as_missing(text):
    assert _try_parse_float(text, **GLUCOSE) is None


@pytest.mark.parametrize("text", ["0/0", "0", "null", "none", "-120/-80", "-120/80", "120/", "/80", "120-80", ""])
def test_unusable_bp_inputs_count_as_missing(text):
    assert _try_parse_bp(text) is None


@pytest.mark.parametrize("text", ["0", "null", "N/A", "none", "?", "..."])
def test_unclear_adherence_is_none_not_a_guess(text):
    assert _looks_affirmative(text) is None


def test_all_zero_answers_finish_safely_as_missing_data():
    """A patient who types 0 for everything must not crash the interview or create a reading."""
    state = feed(start(["diabetes"]), "0", "0", "0", "0", "0", "0")
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake["readings"] == []
    assert state.intake["missing_data"] is True
    assert state.intake["adherence"] is None
    assert state.intake["confidence"] == "Low"
    assert state.stage1_red_flag is False


def test_all_null_answers_finish_safely_for_hypertension():
    state = feed(start(["hypertension"]), "null", "null", "none", "none", "N/A", "null")
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake["readings"] == []
    assert state.intake["missing_data"] is True
    assert state.intake["adherence"] is None
    assert state.intake["confidence"] == "Low"


def test_zero_reading_never_reaches_reconciliation_as_a_value():
    state = feed(start(["diabetes"]), "Okay", "0", "0", "No", "Yes", "No changes")
    bundle = build_checkin_bundle(state, source="fhir", patient_name="T",
                                  checkin_timestamp="2026-10-05T09:00:00Z")
    assert bundle["observations"] == []


# ----------------------------------------------------------------------------
# Diabetes flow
# ----------------------------------------------------------------------------
def test_diabetes_full_flow():
    state = feed(start(["diabetes"]), *DIABETES_FULL)
    assert state.step == INTERVIEW_COMPLETE
    intake = state.intake
    assert intake["condition"] == "diabetes"
    assert intake["readings"] == [{"observation_type": "glucose", "value": 142.0, "unit": "mg/dL"}]
    assert intake["adherence"] is True
    assert intake["missing_data"] is False
    assert intake["confidence"] == "High"
    assert state.stage1_red_flag is False


def test_isolated_dizzy_symptom_never_triggers_red_flag():
    """FR-4: a single vague symptom is investigated, not escalated."""
    state = adaptive_interview_node(start(["diabetes"]), "I feel a bit dizzy")
    assert state.stage1_red_flag is False
    assert state.step == "glucose_reading"
    assert get_current_question(state) is not None


def test_hypoglycemia_branch_only_for_insulin_or_sulfonylurea():
    on_insulin = feed(start(["diabetes"], on_insulin_or_sulfonylurea=True),
                      "Fine", "110", "No unusual thirst")
    assert on_insulin.step == "hypoglycemia_symptoms"
    assert "shakiness" in get_current_question(on_insulin).lower()

    not_on_insulin = feed(start(["diabetes"]), "Fine", "110", "No unusual thirst")
    assert not_on_insulin.step == "adherence"


def test_adherence_no_is_recorded_as_false():
    answers = list(DIABETES_FULL)
    answers[3] = "No, I forgot this morning"
    assert feed(start(["diabetes"]), *answers).intake["adherence"] is False


# ----------------------------------------------------------------------------
# Missing-Data Checkpoint (FR-8)
# ----------------------------------------------------------------------------
def test_missing_reading_asks_once_then_proceeds_with_low_confidence():
    state = feed(start(["diabetes"]), "Feeling okay", "I don't have a glucometer")
    assert state.step == "missing_data_checkpoint"
    assert state.missing_data_asked_once is True

    state = feed(state, "Just feeling a little off", "No thirst or vision changes", "Yes", "No changes")
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake["missing_data"] is True
    assert state.intake["confidence"] == "Low"
    assert state.intake["readings"] == []
    assert state.intake["symptoms"]["symptom_only_note"] == "Just feeling a little off"


def test_usable_reading_given_at_the_checkpoint_is_accepted():
    state = feed(start(["diabetes"]), "Okay", "no meter", "Oh wait, my sugar was 135")
    assert state.step == "hyperglycemia_symptoms"
    state = feed(state, "No", "Yes", "No changes")
    assert state.intake["missing_data"] is False
    assert state.intake["readings"][0]["value"] == 135.0


def test_mmol_reading_is_treated_as_missing_not_converted():
    state = feed(start(["diabetes"]), "Okay", "5.6 mmol/L")
    assert state.step == "missing_data_checkpoint"


def test_hypertension_missing_reading_follows_the_same_rule():
    state = feed(start(["hypertension"]), "Headache", "no cuff", "still no cuff, just tired",
                 "Nothing else", "Yes", "Fine")
    assert state.intake["missing_data"] is True
    assert state.intake["confidence"] == "Low"
    assert state.intake["readings"] == []


# ----------------------------------------------------------------------------
# Hypertension flow
# ----------------------------------------------------------------------------
def test_hypertension_full_flow():
    state = feed(start(["hypertension"]), *HTN_FULL)
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake["readings"] == [
        {"observation_type": "blood_pressure_systolic", "value": 150.0, "unit": "mmHg"},
        {"observation_type": "blood_pressure_diastolic", "value": 95.0, "unit": "mmHg"},
    ]
    assert state.intake["adherence"] is True
    assert state.intake["confidence"] == "High"


# ----------------------------------------------------------------------------
# Dual diagnosis (FR-7)
# ----------------------------------------------------------------------------
def test_dual_diagnosis_asks_both_and_keeps_both_intakes():
    state = start(["diabetes", "hypertension"])
    assert state.active_condition == "diabetes"
    assert state.dual_diagnosis_pending == ["hypertension"]

    state = feed(state, "Feeling dizzy today", "130", "No thirst changes", "Yes", "No changes")
    # pivoted straight to the blood pressure reading: greeting not repeated
    assert state.active_condition == "hypertension"
    assert state.step == "bp_reading"
    assert "blood pressure" in get_current_question(state).lower()
    assert len(state.intakes) == 1

    state = feed(state, "150/95", "A little dizzy", "Yes", "Sodium high")
    assert state.step == INTERVIEW_COMPLETE
    assert [i["condition"] for i in state.intakes] == ["diabetes", "hypertension"]
    assert state.intake["condition"] == "hypertension"
    assert state.intakes[0]["readings"][0]["value"] == 130.0   # first intake survived the pivot


def test_duplicate_conditions_are_asked_once():
    state = start(["Diabetes", "diabetes", " HYPERTENSION "])
    assert state.conditions_on_file == ["diabetes", "hypertension"]


# ----------------------------------------------------------------------------
# Confidence (completeness)
# ----------------------------------------------------------------------------
def test_cold_start_with_full_data_is_capped_at_medium():
    assert feed(start(["diabetes"], is_cold_start=True), *DIABETES_FULL).intake["confidence"] == "Medium"


def test_cold_start_with_missing_reading_is_low_not_medium():
    answers = ["Okay", "no meter", "feeling off", "No", "Yes", "No changes"]
    assert feed(start(["diabetes"], is_cold_start=True), *answers).intake["confidence"] == "Low"


# ----------------------------------------------------------------------------
# Emergency bypass
# ----------------------------------------------------------------------------
def test_emergency_ends_interview_and_clears_pending_condition():
    state = feed(start(["diabetes", "hypertension"]), "I have severe chest pain and can't breathe")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "chest_pain"
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake == {"condition": "diabetes", "emergency": True, "reason": "chest_pain"}
    assert state.dual_diagnosis_pending == []
    assert get_current_question(state) is None


def test_no_bundle_for_emergency_sessions():
    state = feed(start(["hypertension"]), "worst headache of my life")
    with pytest.raises(ValueError, match="bypass"):
        build_checkin_bundle(state, source="local", patient_name="Test")


# ----------------------------------------------------------------------------
# Session handling (stateless API requirements)
# ----------------------------------------------------------------------------
def test_node_does_not_mutate_its_input():
    state = start(["diabetes"])
    before = copy.deepcopy(state.to_dict())
    adaptive_interview_node(state, "Feeling okay")
    assert state.to_dict() == before


def test_session_survives_a_json_round_trip_mid_interview():
    uninterrupted = feed(start(["diabetes", "hypertension"]),
                         *DIABETES_FULL, *HTN_FULL[1:])
    state = start(["diabetes", "hypertension"])
    for answer in DIABETES_FULL + HTN_FULL[1:]:
        state = InterviewState.from_dict(json.loads(json.dumps(state.to_dict())))
        state = adaptive_interview_node(state, answer)
    assert state.to_dict() == uninterrupted.to_dict()


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Unknown"):
        InterviewState.from_dict({"patient_id": "P", "conditions_on_file": ["diabetes"], "oops": 1})


@pytest.mark.parametrize("conditions", [[], ["asthma"]])
def test_invalid_conditions_are_rejected(conditions):
    with pytest.raises(ValueError):
        adaptive_interview_node(InterviewState(patient_id="P-1", conditions_on_file=conditions))


def test_patient_id_is_required():
    with pytest.raises(ValueError, match="patient_id"):
        adaptive_interview_node(InterviewState(patient_id=" ", conditions_on_file=["diabetes"]))


def test_answering_before_start_or_after_completion_is_an_error():
    fresh = InterviewState(patient_id="P-1", conditions_on_file=["diabetes"])
    with pytest.raises(ValueError, match="not started"):
        adaptive_interview_node(fresh, "hello")
    done = feed(start(["diabetes"]), *DIABETES_FULL)
    with pytest.raises(ValueError, match="already complete"):
        adaptive_interview_node(done, "one more thing")


def test_blank_answer_does_not_advance():
    state = start(["diabetes"])
    assert adaptive_interview_node(state, "   ").to_dict() == state.to_dict()


def test_restarting_a_started_session_is_a_no_op():
    state = feed(start(["diabetes"]), "Feeling okay")
    assert adaptive_interview_node(state).to_dict() == state.to_dict()


# ----------------------------------------------------------------------------
# Bridge: interview -> bundle
# ----------------------------------------------------------------------------
def test_checkin_bundle_contents_and_origins():
    state = feed(start(["diabetes", "hypertension"]),
                 "Dizzy", "130", "No", "Yes", "No changes", "150/95", "A little dizzy", "Yes", "Sodium high")
    bundle = build_checkin_bundle(state, source="local", patient_name="Test Patient",
                                  checkin_timestamp="2026-10-05T09:00:00Z")
    assert bundle["patient"].patient_id == "P-1"
    assert bundle["medications"] == []
    observed = {(o.observation_type, o.value, o.unit) for o in bundle["observations"]}
    assert observed == {("glucose", 130.0, "mg/dL"),
                        ("blood_pressure_systolic", 150.0, "mmHg"),
                        ("blood_pressure_diastolic", 95.0, "mmHg")}
    assert {o.source for o in bundle["observations"]} == {"local"}
    assert {o.timestamp for o in bundle["observations"]} == {"2026-10-05T09:00:00Z"}
    ids = [o.source_record_id for o in bundle["observations"]]
    assert len(set(ids)) == 3
    assert build_checkin_origins(bundle) == {i: "self_reported" for i in ids}


def test_bundle_requires_completed_interview_and_valid_source():
    with pytest.raises(ValueError, match="not complete"):
        build_checkin_bundle(start(["diabetes"]), source="local", patient_name="T")
    done = feed(start(["diabetes"]), *DIABETES_FULL)
    with pytest.raises(ValueError, match="source"):
        build_checkin_bundle(done, source="mysql", patient_name="T")


# ----------------------------------------------------------------------------
# Integration: Interview -> Reconciliation -> Verification
# ----------------------------------------------------------------------------
def _baseline(source, glucose, systolic=None, diastolic=None):
    def obs(kind, value, unit):
        return NormalizedObservation(patient_id="P-1", observation_type=kind, value=value, unit=unit,
                                     timestamp="2026-10-04T09:00:00Z", source=source,
                                     source_record_id=f"BASE-{kind}")
    observations = [obs("glucose", glucose, "mg/dL")]
    if systolic is not None:
        observations += [obs("blood_pressure_systolic", systolic, "mmHg"),
                         obs("blood_pressure_diastolic", diastolic, "mmHg")]
    return {"patient": NormalizedPatient(patient_id="P-1", name="Test Patient"),
            "observations": observations, "medications": []}


def _pipeline(interview_state, baseline, source):
    checkin = build_checkin_bundle(interview_state, source=source, patient_name="Test Patient",
                                   checkin_timestamp="2026-10-05T09:00:00Z")
    reconciliation = reconcile_bundles(baseline, checkin)
    verification = verify_reconciliation(reconciliation, origins=build_checkin_origins(checkin))
    return reconciliation, verification


def test_agreeing_checkin_is_auto_resolved():
    state = feed(start(["diabetes", "hypertension"]),
                 "Fine", "142", "No", "Yes", "No changes", "130/84", "No", "Yes", "Fine")
    recon, verif = _pipeline(state, _baseline("fhir", 140, 128, 82), source="fhir")
    assert recon.summary["agreements"] == 3
    assert recon.summary["conflicts"] == 0
    assert verif.summary["requires_review"] == 0
    # baseline FHIR is high trust, the self-reported check-in is low trust
    first = verif.observation_verifications[0]
    assert (first.trust_level_a, first.trust_level_b) == ("high", "low")


def test_conflicting_glucose_is_routed_to_review_with_high_severity():
    """The demo's Scenario B: patient reports 180, the record says 140."""
    state = feed(start(["diabetes"]), "Thirsty", "180", "Very thirsty", "Yes", "No changes")
    recon, verif = _pipeline(state, _baseline("fhir", 140), source="fhir")
    assert recon.summary["conflicts"] == 1
    glucose = verif.observation_verifications[0]
    assert glucose.severity == "high"          # delta 40 > 2 x 15
    assert glucose.requires_human_review is True
    assert verif.summary["requires_review"] == 1


def test_missing_reading_keeps_the_trusted_baseline_without_review():
    state = feed(start(["diabetes"]), "Okay", "no meter", "feeling off", "No", "Yes", "No changes")
    assert state.intake["confidence"] == "Low"
    recon, verif = _pipeline(state, _baseline("fhir", 140), source="fhir")
    assert recon.summary["missing_in_b"] == 1
    glucose = verif.observation_verifications[0]
    assert glucose.requires_human_review is False   # present side is high-trust
    assert glucose.severity == "low"


def test_isolated_mode_pipeline_works_with_the_local_source():
    state = feed(start(["diabetes"]), "Okay", "175", "Thirsty", "Yes", "No changes")
    recon, verif = _pipeline(state, _baseline("local", 115), source="local")
    assert recon.summary["conflicts"] == 1
    assert verif.summary["requires_review"] == 1


def test_store_invariant_is_enforced_when_the_source_does_not_match_the_baseline():
    state = feed(start(["diabetes"]), *DIABETES_FULL)
    with pytest.raises(ValueError, match="Store Invariant"):
        _pipeline(state, _baseline("fhir", 140), source="local")


# ----------------------------------------------------------------------------
# Dangerous reading (proposal section 27: BP at or above 180/120 is a Stage 1 trigger)
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("reading", ["190/125", "180/80", "150/120", "180/120", "260/160"])
def test_bp_crisis_range_reading_triggers_emergency(reading):
    state = feed(start(["hypertension"]), "Feeling fine", reading)
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "bp_crisis_range"
    assert state.step == INTERVIEW_COMPLETE
    assert state.intake["emergency"] is True
    assert state.intake["trigger_reading"]["unit"] == "mmHg"
    assert get_current_question(state) is None


@pytest.mark.parametrize("reading", ["179/119", "170/115", "150/95", "130/85"])
def test_bp_just_below_crisis_is_not_an_emergency(reading):
    state = feed(start(["hypertension"]), "Feeling fine", reading)
    assert state.stage1_red_flag is False
    assert state.step == "associated_symptoms"


def test_bp_crisis_given_at_the_checkpoint_also_triggers():
    state = feed(start(["hypertension"]), "Fine", "no cuff", "Oh, I just measured 200/130")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "bp_crisis_range"
    assert state.intake["trigger_reading"] == {"systolic": 200, "diastolic": 130, "unit": "mmHg"}


def test_bp_crisis_in_second_condition_keeps_the_first_intake():
    state = feed(start(["diabetes", "hypertension"]),
                 "Fine", "130", "No", "Yes", "No changes", "190/125")
    assert state.stage1_red_flag is True
    assert [i["condition"] for i in state.intakes] == ["diabetes", "hypertension"]
    assert state.intakes[0]["emergency"] is False
    assert state.intakes[1]["emergency"] is True
    assert state.dual_diagnosis_pending == []


def test_bp_crisis_never_builds_a_checkin_bundle():
    state = feed(start(["hypertension"]), "Fine", "190/125")
    with pytest.raises(ValueError, match="bypass"):
        build_checkin_bundle(state, source="local", patient_name="T")


def test_implausible_bp_is_asked_again_not_treated_as_a_crisis():
    state = feed(start(["hypertension"]), "Fine", "300/200")
    assert state.stage1_red_flag is False
    assert state.step == "missing_data_checkpoint"


def test_chest_pain_still_wins_over_a_high_reading_in_the_same_answer():
    state = feed(start(["hypertension"]), "Fine", "190/125 and I have chest pain")
    assert state.stage1_reason == "chest_pain"

