"""
Tests for Medication Confirmation. Pure unit tests need no network or database; the
integration tests push the answers through the real Reconciliation and Verification agents.
"""

import copy
import json

import pytest

import agents.medication_confirmation as mc
from agents.reconciliation_agent import reconcile_bundles
from agents.verification_agent import verify_reconciliation
from data_sources.models import NormalizedMedication, NormalizedPatient

METFORMIN = {"medication_name": "Metformin 500mg", "status": "active", "dosage": "1 tablet twice daily"}
LISINOPRIL = {"medication_name": "Lisinopril 10mg", "status": "active", "dosage": "1 tablet once daily"}


def check(meds):
    return mc.start_medication_check(meds)


def feed(state, *answers):
    for answer in answers:
        state = mc.advance_medication_check(state, answer)
    return state


# ----------------------------------------------------------------------------
# which medications are asked about
# ----------------------------------------------------------------------------
def test_only_active_medications_are_asked_in_record_order():
    stopped = {"medication_name": "Glibenclamide", "status": "stopped", "dosage": "5mg"}
    state = check([METFORMIN, stopped, LISINOPRIL])
    assert [i["name"] for i in state.items] == ["Metformin 500mg", "Lisinopril 10mg"]


def test_duplicates_are_removed_after_normalising_the_name():
    state = check([METFORMIN, dict(METFORMIN, medication_name="  metformin 500MG ")])
    assert len(state.items) == 1


def test_start_accepts_dataclass_objects_and_empty_input():
    obj = NormalizedMedication("P-1", "Aspirin 81mg", "active", "1 daily", "2026-10-05T09:00:00Z", "local", "R1")
    assert check([obj]).items == [{"name": "Aspirin 81mg", "dosage": "1 daily"}]
    assert check(None).items == [] and check([]).complete is True


def test_the_list_is_capped():
    many = [{"medication_name": f"Drug {i}", "status": "active", "dosage": "1"} for i in range(50)]
    assert len(check(many).items) == mc.MAX_MEDICATIONS


def test_nameless_records_are_skipped():
    assert check([{"medication_name": " ", "status": "active", "dosage": "1"}]).items == []


# ----------------------------------------------------------------------------
# how answers are understood
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("answer,status,changed", [
    ("yes", "active", False),
    ("Yes, took it this morning", "active", False),
    ("yeah still taking it", "active", False),
    ("no", "stopped", False),
    ("nope", "stopped", False),
    ("I stopped it last week", "stopped", False),
    ("my doctor discontinued it", "stopped", False),
    ("I no longer take it", "stopped", False),
    ("not taking it", "stopped", False),
    ("1 tablet twice daily", "active", False),            # same dose repeated
    ("yes, 1 tablet twice daily", "active", False),
    ("yes but only half a tablet", "active", True),
    ("I take 2 tablets now", "active", True),
    ("500mg once a day", "active", True),
    ("Yes, since 2020", "active", False),                 # a year is not a dose
])
def test_answer_interpretation(answer, status, changed):
    state = feed(check([METFORMIN]), answer)
    assert state.complete is True
    result = state.results[0]
    assert (result["status"], result["changed"]) == (status, changed)


def test_a_changed_dose_is_recorded_without_the_leading_yes():
    state = feed(check([METFORMIN]), "Yes, 2 tablets now")
    assert state.results[0]["dosage"] == "2 tablets now"


def test_a_stopped_medication_keeps_the_recorded_dose():
    state = feed(check([METFORMIN]), "no")
    assert state.results[0]["dosage"] == "1 tablet twice daily"


@pytest.mark.parametrize("answer", ["I missed today's dose", "I didn't take it today", "forgot this morning", "maybe", "hmm", "?", "0", "2", "null"])
def test_unclear_answers_are_asked_once_more_then_recorded_as_unknown(answer):
    state = check([METFORMIN])
    state = mc.advance_medication_check(state, answer)
    assert state.complete is False and state.attempts == 1
    assert "didn't catch that" in mc.current_medication_question(state)
    state = mc.advance_medication_check(state, answer)
    assert state.complete is True
    assert state.results[0]["status"] == "unknown"


def test_a_clear_answer_to_the_second_try_is_accepted():
    state = feed(check([METFORMIN]), "maybe", "no")
    assert state.results[0]["status"] == "stopped"


def test_blank_answers_do_not_advance():
    state = check([METFORMIN])
    assert mc.advance_medication_check(state, "   ").to_dict() == state.to_dict()


def test_zero_null_and_garbage_are_handled_without_error():
    state = check([METFORMIN, LISINOPRIL])
    state = feed(state, "0", "0", "null", "null")
    assert state.complete is True
    assert [r["status"] for r in state.results] == ["unknown", "unknown"]


def test_advance_does_not_mutate_its_input():
    state = check([METFORMIN])
    before = copy.deepcopy(state.to_dict())
    mc.advance_medication_check(state, "yes")
    assert state.to_dict() == before


def test_cannot_advance_a_finished_check():
    done = feed(check([METFORMIN]), "yes")
    with pytest.raises(ValueError, match="complete"):
        mc.advance_medication_check(done, "yes")


def test_questions_follow_the_record_order_and_end_with_none():
    state = check([METFORMIN, LISINOPRIL])
    assert "Metformin 500mg (1 tablet twice daily)" in mc.current_medication_question(state)
    state = feed(state, "yes")
    assert "Lisinopril 10mg" in mc.current_medication_question(state)
    state = feed(state, "yes")
    assert mc.current_medication_question(state) is None


def test_session_survives_a_json_round_trip():
    state = check([METFORMIN, LISINOPRIL])
    state = mc.advance_medication_check(state, "yes")
    again = mc.MedicationCheckState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert again.to_dict() == state.to_dict()
    assert feed(again, "no").to_dict() == feed(state, "no").to_dict()


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Unknown"):
        mc.MedicationCheckState.from_dict({"items": [], "oops": 1})


# ----------------------------------------------------------------------------
# bundle items and origin tags
# ----------------------------------------------------------------------------
def test_bundle_items_origins_and_unknown_are_left_out():
    state = feed(check([METFORMIN, LISINOPRIL]), "yes", "maybe", "maybe")
    items = mc.build_medication_bundle_items(state, "P-1", "local", "2026-10-05T09:00:00Z")
    assert [(m.medication_name, m.status, m.dosage) for m in items] == [
        ("Metformin 500mg", "active", "1 tablet twice daily")]
    assert items[0].source == "local" and items[0].patient_id == "P-1"
    ids = [m.source_record_id for m in items]
    assert mc.build_medication_origins(items) == {i: "self_reported" for i in ids}


def test_bundle_items_need_a_finished_check_and_a_valid_source():
    with pytest.raises(ValueError, match="not complete"):
        mc.build_medication_bundle_items(check([METFORMIN]), "P-1", "local", "2026-10-05T09:00:00Z")
    done = feed(check([METFORMIN]), "yes")
    with pytest.raises(ValueError, match="source"):
        mc.build_medication_bundle_items(done, "P-1", "mysql", "2026-10-05T09:00:00Z")


def test_restrict_to_asked_drops_historical_records():
    old = {"medication_name": "Glibenclamide", "status": "stopped", "dosage": "5mg"}
    state = check([METFORMIN, old])
    kept = mc.restrict_to_asked([METFORMIN, old], state)
    assert [m["medication_name"] for m in kept] == ["Metformin 500mg"]


# ----------------------------------------------------------------------------
# integration: answers -> Reconciliation -> Verification (the real agents)
# ----------------------------------------------------------------------------
def _meds(source, *records):
    return [NormalizedMedication("P-1", r["medication_name"], r["status"], r["dosage"],
                                 "2026-10-01T09:00:00Z", source, f"REC-{i}")
            for i, r in enumerate(records)]


def _run(source, prior_records, answers, prior_origins=None):
    prior = _meds(source, *prior_records)
    state = feed(check(prior), *answers)
    checkin_meds = mc.build_medication_bundle_items(state, "P-1", source, "2026-10-05T09:00:00Z")
    a = {"patient": NormalizedPatient("P-1", "T"), "observations": [], "medications": mc.restrict_to_asked(prior, state)}
    b = {"patient": NormalizedPatient("P-1", "T"), "observations": [], "medications": checkin_meds}
    origins = dict(prior_origins or {})
    origins.update(mc.build_medication_origins(checkin_meds))
    recon = reconcile_bundles(a, b)
    return recon, verify_reconciliation(recon, origins=origins)


def test_still_taking_everything_is_auto_resolved_against_a_trusted_record():
    recon, verif = _run("fhir", [METFORMIN, LISINOPRIL], ["yes", "yes"])
    assert recon.summary["agreements"] == 2 and recon.summary["conflicts"] == 0
    assert verif.summary["requires_review"] == 0


def test_a_stopped_medication_is_a_high_severity_review_item():
    recon, verif = _run("fhir", [METFORMIN, LISINOPRIL], ["yes", "no"])
    lisinopril = [v for v in verif.medication_verifications if v.medication_name == "Lisinopril 10mg"][0]
    assert lisinopril.reconciliation_status == "conflict"
    assert lisinopril.severity == "high" and lisinopril.requires_human_review is True


def test_a_changed_dose_is_a_moderate_review_item():
    recon, verif = _run("fhir", [METFORMIN], ["yes but only half a tablet"])
    only = verif.medication_verifications[0]
    assert only.severity == "moderate" and only.requires_human_review is True


def test_an_unknown_answer_is_not_reported_today_and_auto_resolved_for_a_trusted_record():
    recon, verif = _run("fhir", [METFORMIN], ["maybe", "maybe"])
    assert recon.summary["missing_in_b"] == 1
    assert verif.medication_verifications[0].requires_human_review is False


def test_historical_medications_never_raise_review_items():
    old = {"medication_name": "Glibenclamide", "status": "stopped", "dosage": "5mg"}
    recon, verif = _run("fhir", [METFORMIN, old], ["yes"])
    assert recon.summary["agreements"] == 1 and recon.summary["missing_in_b"] == 0
    assert verif.summary["requires_review"] == 0


def test_isolated_mode_with_a_self_reported_record_is_checked_with_low_trust():
    origins = {"REC-0": "self_reported", "REC-1": "self_reported"}
    recon, verif = _run("local", [METFORMIN, LISINOPRIL], ["yes", "no"], prior_origins=origins)
    by_name = {v.medication_name: v for v in verif.medication_verifications}
    assert by_name["Lisinopril 10mg"].severity == "high"
    # both sides self-reported and agreeing: still reviewed, nobody trusted confirms it
    assert by_name["Metformin 500mg"].requires_human_review is True


def test_store_invariant_still_applies():
    prior = _meds("fhir", METFORMIN)
    state = feed(check(prior), "yes")
    items = mc.build_medication_bundle_items(state, "P-1", "local", "2026-10-05T09:00:00Z")
    a = {"patient": NormalizedPatient("P-1", "T"), "observations": [], "medications": prior}
    b = {"patient": NormalizedPatient("P-1", "T"), "observations": [], "medications": items}
    with pytest.raises(ValueError, match="Store Invariant"):
        reconcile_bundles(a, b)
