"""
Tests for the Triage Protocol. Each vignette is a short clinical story with the level the
protocol must reach. They double as the first scenario suite for the evaluation chapter.
"""

import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

import agents.triage_protocol as tp

SYS, DIA, GLU = tp.SYSTOLIC, tp.DIASTOLIC, tp.GLUCOSE
NOW = "2026-10-06T09:00:00Z"


def history(values, kind=SYS, start_day=1):
    """One reading per day, the first value is start_day days before NOW."""
    base = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)
    return [{"observation_type": kind, "value": value,
             "timestamp": (base - timedelta(days=start_day + offset)).strftime("%Y-%m-%dT%H:%M:%SZ")}
            for offset, value in enumerate(values)]


def run(readings, answers, age=45, baseline=None):
    triggers = tp.evaluate_triggers(readings, baseline)
    assert triggers, "the readings did not start a protocol"
    state = tp.start_protocol(triggers[0], readings, age, baseline)
    for answer in answers:
        if state.complete:
            break
        state = tp.advance_protocol(state, answer)
    assert state.complete, f"protocol not finished; next question: {tp.current_protocol_question(state)}"
    return state.result


# ----------------------------------------------------------------------------
# age
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("age,band", [(18, "adult_18_64"), (64, "adult_18_64"), (65, "older_65_plus"), (90.5, "older_65_plus")])
def test_age_bands(age, band):
    assert tp.age_band(age) == band


@pytest.mark.parametrize("age", [17, 0, -3, 130, None, "40", True, float("nan")])
def test_invalid_or_paediatric_ages_are_refused(age):
    with pytest.raises(ValueError):
        tp.age_band(age)


def test_older_adults_get_one_extra_question():
    readings = {SYS: 150, DIA: 90}
    base = tp.Baseline(110, 70, 5)
    young = tp.start_protocol(tp.evaluate_triggers(readings, base)[0], readings, 40, base)
    old = tp.start_protocol(tp.evaluate_triggers(readings, base)[0], readings, 70, base)
    assert len(tp._questions(old)) == len(tp._questions(young)) + 1


# ----------------------------------------------------------------------------
# baseline
# ----------------------------------------------------------------------------
def test_baseline_is_the_median_of_recent_readings():
    base = tp.compute_baseline(history([110, 108, 112, 109, 111]), NOW)
    assert base.systolic == 110 and base.n == 5


def test_no_baseline_from_fewer_than_three_readings():
    assert tp.compute_baseline(history([110, 108]), NOW) is None
    assert tp.compute_baseline([], NOW) is None


def test_old_readings_do_not_count_and_only_the_latest_seven_are_used():
    old = [{"observation_type": SYS, "value": 200, "timestamp": "2026-08-01T08:00:00Z"}] * 5
    assert tp.compute_baseline(old, NOW) is None
    many = history([100] * 3 + [120] * 7)            # the three oldest (100) fall outside the last seven
    # days: offsets 0..9 -> 1..10 days ago, the last seven recent are the first seven entries
    assert tp.compute_baseline(many, NOW).n == 7


def test_baseline_ignores_garbage_rows():
    rows = history([110, 110, 110]) + [{"observation_type": SYS, "value": "x", "timestamp": NOW},
                                       {"observation_type": SYS, "value": 120, "timestamp": "not a date"},
                                       {"observation_type": "weight", "value": 80, "timestamp": NOW}]
    assert tp.compute_baseline(rows, NOW).n == 3


# ----------------------------------------------------------------------------
# triggers
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("readings,protocol", [
    ({SYS: 190, DIA: 100}, "bp_severe"),
    ({SYS: 150, DIA: 120}, "bp_severe"),
    ({GLU: 260}, "glucose_high"),
    ({GLU: 60}, "glucose_low"),
    ({SYS: 85, DIA: 55}, "bp_low"),
    ({SYS: 100, DIA: 58}, "bp_low"),
])
def test_what_starts_a_protocol(readings, protocol):
    assert tp.evaluate_triggers(readings)[0].protocol == protocol


@pytest.mark.parametrize("readings", [{SYS: 135, DIA: 85}, {GLU: 140}, {GLU: 70}, {GLU: 249}, {SYS: 179, DIA: 119}, {}])
def test_ordinary_readings_start_nothing(readings):
    assert tp.evaluate_triggers(readings) == []


def test_priority_order_when_several_apply():
    names = [t.protocol for t in tp.evaluate_triggers({SYS: 200, DIA: 100, GLU: 40})]
    assert names == ["bp_severe", "glucose_low"]


def test_a_rise_of_twenty_from_the_personal_baseline_starts_a_change_protocol():
    """Supervisor's example: usually about 110, two days later 130."""
    base = tp.compute_baseline(history([110, 109, 111, 110]), NOW)
    triggers = tp.evaluate_triggers({SYS: 130, DIA: 80}, base)
    assert [t.protocol for t in triggers] == ["bp_change"]
    assert "20" in triggers[0].reason


def test_a_smaller_rise_or_no_baseline_starts_nothing():
    base = tp.Baseline(110, 70, 5)
    assert tp.evaluate_triggers({SYS: 128, DIA: 80}, base) == []
    assert tp.evaluate_triggers({SYS: 130, DIA: 80}, None) == []


def test_the_baseline_is_not_used_when_the_reading_is_already_severe():
    names = [t.protocol for t in tp.evaluate_triggers({SYS: 190, DIA: 100}, tp.Baseline(110, 70, 5))]
    assert names == ["bp_severe"]


# ----------------------------------------------------------------------------
# vignettes: severe blood pressure
# ----------------------------------------------------------------------------
SEVERE = {SYS: 200, DIA: 118}


def test_severe_bp_with_warning_symptoms_is_an_emergency():
    result = run(SEVERE, ["190/115", "yes, my chest feels tight and I am short of breath", "no", "no"])
    assert result["level"] == "emergency"


def test_severe_bp_with_symptoms_stays_an_emergency_even_if_a_medicine_could_explain_it():
    """The medicine questions never downgrade a warning symptom."""
    result = run(SEVERE, ["188/112", "yes, my vision is blurry", "yes cold medicine", "no"])
    assert result["level"] == "emergency"


def test_a_confirmed_emergency_stops_the_questions_at_once():
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    state = tp.advance_protocol(state, "190/115")
    state = tp.advance_protocol(state, "yes, my vision is blurry")
    assert state.complete is True and state.result["level"] == "emergency"
    assert tp.current_protocol_question(state) is None and tp.current_protocol_step(state) is None


def test_severe_bp_that_stays_high_without_symptoms_is_urgent_not_an_emergency():
    result = run(SEVERE, ["196/119", "no", "no", "no"])
    assert result["level"] == "urgent"
    assert "still in the crisis range" in " ".join(result["reasons"])


def test_a_200_caused_by_a_decongestant_is_flagged_with_the_factor_and_goes_to_a_clinician():
    """Supervisor's example: BP 200 because of a medicine. The cause is recorded; the case is still reviewed."""
    result = run(SEVERE, ["150/92", "no", "yes, a decongestant for my cold", "no"])
    assert result["level"] == "review"
    assert "cold or flu medicine" in result["factors"]
    assert "Improved after rest" in " ".join(result["reasons"])


def test_a_first_reading_that_normalises_after_rest_is_still_reviewed_but_not_urgent():
    result = run(SEVERE, ["128/82", "no", "no", "yes, I was rushing and anxious"])
    assert result["level"] == "review"
    assert "stress or anxiety" in result["factors"]
    assert "normal after rest" in " ".join(result["reasons"])


def test_severe_bp_that_cannot_be_rechecked_is_urgent():
    result = run(SEVERE, ["cannot", "no", "no", "no"])
    assert result["level"] == "urgent"


def test_unclear_symptom_answers_are_never_read_as_no():
    result = run(SEVERE, ["150/90", "maybe", "maybe", "no", "no"])
    # "maybe" is asked once more, then recorded as unknown, which raises the level
    assert result["level"] == "urgent"
    assert "could not be ruled out" in " ".join(result["reasons"])


def test_missed_medicine_is_recorded_as_a_factor():
    result = run(SEVERE, ["160/95", "no", "yes, I forgot my tablet this morning", "no"])
    assert "missed medicine" in result["factors"]


def test_a_danger_phrase_in_any_answer_is_an_immediate_emergency():
    triggers = tp.evaluate_triggers(SEVERE)
    state = tp.start_protocol(triggers[0], SEVERE, 50)
    state = tp.advance_protocol(state, "I have chest pain now")
    assert state.complete and state.result["level"] == "emergency"


def test_a_negated_danger_phrase_is_not_an_emergency():
    triggers = tp.evaluate_triggers(SEVERE)
    state = tp.start_protocol(triggers[0], SEVERE, 50)
    state = tp.advance_protocol(state, "150/90 and no chest pain")
    assert state.complete is False and state.answers["recheck"] == {"systolic": 150, "diastolic": 90}


# ----------------------------------------------------------------------------
# vignettes: change from the patient's own baseline
# ----------------------------------------------------------------------------
BASE = tp.Baseline(systolic=110, diastolic=70, n=5)


def test_a_rise_from_110_to_130_without_symptoms_is_reviewed():
    result = run({SYS: 130, DIA: 80}, ["no", "no", "yes", "no"], baseline=BASE)
    assert result["level"] == "review"
    assert "20 mmHg above your usual" in result["reasons"][0]


def test_the_same_rise_with_symptoms_is_urgent():
    result = run({SYS: 130, DIA: 80}, ["yes, a pounding headache", "no", "yes", "no"], baseline=BASE)
    assert result["level"] == "urgent"


def test_a_marked_rise_is_urgent_even_without_symptoms():
    result = run({SYS: 152, DIA: 92}, ["no", "no", "yes", "no"], baseline=BASE)
    assert result["level"] == "urgent"


def test_a_rise_after_missed_medicine_is_annotated():
    result = run({SYS: 131, DIA: 82}, ["no", "no", "no, I missed it for two days", "no"], baseline=BASE)
    assert "missed medicine" in result["factors"]
    assert result["level"] == "review"


def test_dizziness_on_standing_in_an_older_adult_raises_the_level():
    result = run({SYS: 131, DIA: 82}, ["no", "no", "yes", "no", "yes"], age=72, baseline=BASE)
    assert result["level"] == "urgent"


# ----------------------------------------------------------------------------
# vignettes: low blood pressure and glucose
# ----------------------------------------------------------------------------
def test_low_bp_without_symptoms_is_reviewed():
    assert run({SYS: 88, DIA: 58}, ["no", "no"])["level"] == "review"


def test_low_bp_with_dizziness_is_urgent():
    assert run({SYS: 88, DIA: 58}, ["yes dizzy", "no"])["level"] == "urgent"


def test_low_bp_with_a_fall_in_an_older_adult_is_urgent():
    assert run({SYS: 88, DIA: 58}, ["no", "no", "yes"], age=75)["level"] == "urgent"


def test_high_glucose_with_warning_symptoms_is_an_emergency():
    assert run({GLU: 320}, ["yes, I am vomiting and my stomach hurts"])["level"] == "emergency"


def test_high_glucose_without_symptoms_is_reviewed_below_300_and_urgent_from_300():
    assert run({GLU: 270}, ["no", "no", "yes, I ate a large meal"])["level"] == "review"
    assert run({GLU: 310}, ["no", "no", "no"])["level"] == "urgent"


def test_high_glucose_context_is_recorded():
    result = run({GLU: 270}, ["no", "yes", "yes, I missed my insulin"])
    assert "missed medicine" in result["factors"]


def test_low_glucose_with_confusion_is_an_emergency():
    assert run({GLU: 45}, ["yes"])["level"] == "emergency"


def test_low_glucose_and_unable_to_swallow_is_an_emergency():
    assert run({GLU: 60}, ["no", "no"])["level"] == "emergency"


def test_low_glucose_that_the_patient_can_treat_is_reviewed_or_urgent_by_depth():
    assert run({GLU: 65}, ["no", "yes", "yes, shaky", "yes insulin"])["level"] == "review"
    assert run({GLU: 50}, ["no", "yes", "yes, shaky", "yes insulin"])["level"] == "urgent"


# ----------------------------------------------------------------------------
# mechanics
# ----------------------------------------------------------------------------
def test_questions_come_in_order_with_a_step_string():
    triggers = tp.evaluate_triggers(SEVERE)
    state = tp.start_protocol(triggers[0], SEVERE, 40)
    assert tp.current_protocol_step(state) == "triage:bp_severe:0:0"
    assert "rest quietly for 5 minutes" in tp.current_protocol_question(state)
    state = tp.advance_protocol(state, "190/115")
    assert tp.current_protocol_step(state) == "triage:bp_severe:1:0"


def test_an_unclear_answer_is_asked_once_more():
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    state = tp.advance_protocol(state, "hmm")
    assert tp.current_protocol_step(state) == "triage:bp_severe:0:1"
    assert tp.current_protocol_question(state).startswith("Sorry, I didn't catch that.")


@pytest.mark.parametrize("junk", ["0", "null", "none", "?", "...", "-5"])
def test_zero_null_and_garbage_never_crash_the_protocol(junk):
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    for _ in range(12):
        if state.complete:
            break
        state = tp.advance_protocol(state, junk)
    assert state.complete and state.result["level"] in ("urgent", "emergency", "review")


def test_blank_answers_do_not_advance():
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    assert tp.advance_protocol(state, "   ").to_dict() == state.to_dict()


def test_advance_does_not_mutate_its_input_and_cannot_continue_when_complete():
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    before = copy.deepcopy(state.to_dict())
    tp.advance_protocol(state, "190/115")
    assert state.to_dict() == before
    done = tp.advance_protocol(state, "I have chest pain")
    with pytest.raises(ValueError, match="complete"):
        tp.advance_protocol(done, "yes")


def test_the_state_survives_a_json_round_trip_mid_protocol():
    state = tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 40)
    state = tp.advance_protocol(state, "190/115")
    again = tp.TriageProtocolState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert again.to_dict() == state.to_dict()
    assert tp.advance_protocol(again, "no").to_dict() == tp.advance_protocol(state, "no").to_dict()


def test_from_dict_rejects_unknown_fields_and_start_rejects_unknown_protocols():
    with pytest.raises(ValueError, match="Unknown"):
        tp.TriageProtocolState.from_dict({"protocol": "bp_severe", "age_band": "adult_18_64", "oops": 1})
    with pytest.raises(ValueError):
        tp.start_protocol(tp.Trigger("made_up", "x", 1), {}, 40)


def test_a_minor_cannot_start_a_protocol():
    with pytest.raises(ValueError, match="adults"):
        tp.start_protocol(tp.evaluate_triggers(SEVERE)[0], SEVERE, 15)


def test_results_carry_guidance_a_summary_and_no_free_text():
    result = run(SEVERE, ["196/119", "no", "yes cold medicine", "no"])
    assert result["guidance"].startswith("Please contact your clinician today")
    assert "after 5 minutes of rest 196/119" in result["summary"]
    assert "cold or flu medicine" in result["summary"]
    assert "decongestant" not in json.dumps(result)           # the patient's wording is not stored


def test_the_emergency_guidance_text():
    assert tp.GUIDANCE["emergency"].startswith("Call your local emergency number now")


# ----------------------------------------------------------------------------
# the final decision is safe even if it is reached without the early rule
# ----------------------------------------------------------------------------
def _state(protocol, readings, answers, band="adult_18_64"):
    state = tp.TriageProtocolState(protocol=protocol, age_band=band, readings=readings)
    state.answers = answers
    return state


def test_decisions_are_safe_when_called_directly():
    recheck = {"systolic": 150, "diastolic": 90}
    assert tp._decide(_state("bp_severe", {SYS: 200, DIA: 100}, {"symptoms": True, "recheck": recheck}))["level"] == "emergency"
    assert tp._decide(_state("glucose_low", {GLU: 60}, {"neuro": False, "can_swallow": False}))["level"] == "emergency"
    assert tp._decide(_state("glucose_low", {GLU: 60}, {"neuro": True, "can_swallow": True}))["level"] == "emergency"
    assert tp._decide(_state("glucose_high", {GLU: 300}, {"dka_symptoms": True}))["level"] == "emergency"
