"""
Adaptive Interview Agent (Iteration 1)

Deterministic, rule-based structured check-in interview for Type 2 Diabetes and
Hypertension (Proposal Section 14). One call advances the interview by exactly one
patient answer, so a stateless API can round-trip the whole session as JSON
(InterviewState.to_dict() / InterviewState.from_dict()).

Performs NO diagnosis, risk scoring, trust scoring or language-model processing.
Free-text understanding is limited to the keyword/regex rules below. Those rules are
the intended swap-in point for a learned classifier in a later iteration; the state
machine around them does not need to change.

=============================================================================
RULES
=============================================================================
1. Stage-1 red-flag screen runs on EVERY answer, before any other processing (FR-3).
   A match ends the interview at once (emergency bypass).
   A phrase is ignored only if a negation cue ("no", "not", "never", "without", ...)
   appears within 3 words before it in the same clause. When in doubt the screen
   flags: a false alarm is safer than a missed emergency.
2. A lone non-specific symptom such as "dizzy" never triggers a red flag (FR-4).
3. Missing-Data Checkpoint (FR-8): if the required reading is missing or unusable,
   ask ONE clarifying question, then proceed. The intake is tagged missing_data=True
   with confidence Low. A usable reading given at the checkpoint is accepted.
   Unusable means: no number, a negative number, outside the plausible range, ambiguous
   (several plausible numbers), or given in mmol/L. Unit conversion is deliberately not
   guessed, and a minus sign is never dropped.
4. Dual diagnosis (FR-7): when the first condition finishes, the second condition's
   reading is asked next (greeting is not repeated). Every finished condition is kept
   in InterviewState.intakes; InterviewState.intake is the most recent one.
5. Confidence is a COMPLETENESS label only: Low if the reading is missing, otherwise
   Medium on a first-ever check-in (cold start), otherwise High. Source trust is NOT
   decided here: build_checkin_origins() tags every reading "self_reported" so the
   Verification Agent assigns it low trust.

Intake schema (one per finished condition):
    {"condition": "diabetes" | "hypertension",
     "emergency": False,
     "readings": [{"observation_type": "glucose", "value": 142.0, "unit": "mg/dL"}]
                 or [{"observation_type": "blood_pressure_systolic", ...},
                     {"observation_type": "blood_pressure_diastolic", ...}]
                 or []                                  # reading missing
     "symptoms": {...free text by question...},
     "adherence": True | False | None,                  # None = answer unclear
     "lifestyle_notes": str | None,
     "confidence": "High" | "Medium" | "Low",
     "missing_data": bool}
An emergency intake is {"condition": ..., "emergency": True, "reason": <category>}.
=============================================================================
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from data_sources.models import NormalizedObservation, NormalizedPatient

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SUPPORTED_CONDITIONS = ("diabetes", "hypertension")
INTERVIEW_COMPLETE = "interview_complete"
SELF_REPORTED_ORIGIN = "self_reported"

# Illustrative plausibility bounds only; NOT clinical guidance.
GLUCOSE_RANGE_MG_DL = (20.0, 600.0)
SYSTOLIC_RANGE_MMHG = (60, 260)
DIASTOLIC_RANGE_MMHG = (30, 160)
NEGATION_WINDOW_WORDS = 3


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DiabetesStep(str, Enum):
    GREETING = "greeting"
    GLUCOSE_READING = "glucose_reading"
    MISSING_DATA_CHECKPOINT = "missing_data_checkpoint"
    HYPERGLYCEMIA_SYMPTOMS = "hyperglycemia_symptoms"
    HYPOGLYCEMIA_SYMPTOMS = "hypoglycemia_symptoms"
    ADHERENCE = "adherence"
    LIFESTYLE = "lifestyle"
    COMPLETE = "complete"


class HypertensionStep(str, Enum):
    GREETING = "greeting"
    BP_READING = "bp_reading"
    MISSING_DATA_CHECKPOINT = "missing_data_checkpoint"
    ASSOCIATED_SYMPTOMS = "associated_symptoms"
    ADHERENCE = "adherence"
    LIFESTYLE = "lifestyle"
    COMPLETE = "complete"


@dataclass
class InterviewState:
    patient_id: str
    conditions_on_file: List[str]
    on_insulin_or_sulfonylurea: bool = False
    is_cold_start: bool = False  # set by the caller once it knows no prior record exists
    active_condition: Optional[str] = None
    step: str = ""
    missing_data_asked_once: bool = False
    answers: Dict[str, Any] = field(default_factory=dict)
    intake: Dict[str, Any] = field(default_factory=dict)  # most recent finished intake
    intakes: List[Dict[str, Any]] = field(default_factory=list)  # every finished intake
    stage1_red_flag: bool = False
    stage1_reason: Optional[str] = None
    dual_diagnosis_pending: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewState":
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown InterviewState fields: {sorted(unknown)}")
        return cls(**copy.deepcopy(data))


# -----------------------------------------------------------------------------
# Stage 1: red-flag screen
# -----------------------------------------------------------------------------
# Phrases must not contain punctuation or the clause words "and/but/while/though".
# The Urdu phrases are UNREVIEWED: they need a native-speaker / clinical check before
# anyone relies on them. Urdu negation is NOT handled, so an Urdu match always flags.
RED_FLAG_PATTERNS: Dict[str, List[str]] = {
    "chest_pain": ["chest pain", "chest tightness", "chest pressure", "chest hurts",
                   "pain in my chest", "crushing chest", "سینے میں درد"],
    "breathing": ["can't breathe", "cant breathe", "cannot breathe", "struggling to breathe",
                  "severe shortness of breath", "gasping for air",
                  "سانس لینے میں دشواری", "سانس نہیں آ رہی"],
    "confusion": ["confused", "slurred speech", "can't speak clearly", "cant speak clearly"],
    "loss_of_consciousness": ["fainted", "passed out", "lost consciousness", "blacked out", "بے ہوش"],
    "one_sided_weakness": ["one side weak", "one-sided weakness", "can't move one side",
                           "cant move one side", "face drooping"],
    "unable_to_keep_fluids": ["can't keep anything down", "cant keep anything down",
                              "can't keep fluids down", "vomiting nonstop", "vomiting non-stop"],
    "severe_headache": ["worst headache", "severe headache", "thunderclap headache"],
    "vision_loss": ["sudden vision loss", "lost my vision", "went blind",
                    "can't see at all", "cannot see at all"],
}

_NEGATION_CUES = frozenset({
    "no", "not", "never", "without", "denies", "deny",
    "don't", "dont", "doesn't", "doesnt", "didn't", "didnt",
    "haven't", "havent", "hasn't", "hasnt", "isn't", "isnt",
})
_CLAUSE_BREAK = re.compile(r"[.;,:!?\n]+|\b(?:but|however|although|though|and|while)\b")


def _normalize(text: str) -> str:
    return (text or "").replace("\u2019", "'").replace("\u2018", "'").lower()


def _is_negated(clause: str, start: int) -> bool:
    preceding = re.findall(r"[a-z']+", clause[:start])
    return any(word in _NEGATION_CUES for word in preceding[-NEGATION_WINDOW_WORDS:])


def run_stage1_red_flag_screen(free_text: str) -> Tuple[bool, Optional[str]]:
    """Returns (triggered, category). Runs before any other processing of an answer."""
    for clause in _CLAUSE_BREAK.split(_normalize(free_text)):
        if not clause.strip():
            continue
        for category, patterns in RED_FLAG_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(re.escape(pattern), clause):
                    if not _is_negated(clause, match.start()):
                        return True, category
    return False, None


# -----------------------------------------------------------------------------
# Answer parsing (deliberately conservative: unclear means "missing", never a guess)
# -----------------------------------------------------------------------------
_TIME_OF_DAY = re.compile(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b")
_NO_CUES = re.compile(
    r"\b(?:no|nope|nah|not|never|didn't|didnt|haven't|havent|hasn't|hasnt|"
    r"missed|skipped|forgot|forgotten|nahi|nahin)\b")
_STRONG_YES = re.compile(r"\b(?:yes|yeah|yep|yup|haan)\b")
_WEAK_YES = re.compile(r"\b(?:ji|took|taken|taking|i did|sure|ok|okay)\b")
_NO_PROBLEM = re.compile(r"\bno (?:problem|worries)\b")
_NEGATIVE_NUMBER = re.compile(r"(?<![\w.])[-\u2212\u2013]\s*\d")


def _has_negative_number(text: str) -> bool:
    """True for "-120" / "\u2212120": the sign must not be silently dropped."""
    return bool(_NEGATIVE_NUMBER.search(text))


def _try_parse_float(text: str, minimum: Optional[float] = None,
                     maximum: Optional[float] = None,
                     reject_units: Tuple[str, ...] = ()) -> Optional[float]:
    """Returns the single plausible number in `text`, else None.

    None is returned when there is no number, a rejected unit is present, no number is
    inside [minimum, maximum], or MORE THAN ONE number is inside it (ambiguous)."""
    lowered = text.lower()
    if any(unit in lowered for unit in reject_units) or _has_negative_number(lowered):
        return None
    cleaned = _TIME_OF_DAY.sub(" ", lowered)
    values = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", cleaned)]
    plausible = [v for v in values
                 if (minimum is None or v >= minimum) and (maximum is None or v <= maximum)]
    return plausible[0] if len(plausible) == 1 else None


def _try_parse_bp(text: str) -> Optional[List[int]]:
    """Returns [systolic, diastolic] if exactly one plausible pair is present, else None."""
    if _has_negative_number(text):
        return None
    pairs = []
    for sys_s, dia_s in re.findall(r"(\d{2,3})\s*(?:/|over)\s*(\d{2,3})", text.lower()):
        sys_v, dia_v = int(sys_s), int(dia_s)
        if (SYSTOLIC_RANGE_MMHG[0] <= sys_v <= SYSTOLIC_RANGE_MMHG[1]
                and DIASTOLIC_RANGE_MMHG[0] <= dia_v <= DIASTOLIC_RANGE_MMHG[1]
                and sys_v > dia_v):
            pairs.append([sys_v, dia_v])
    return pairs[0] if len(pairs) == 1 else None


def _looks_affirmative(text: str) -> Optional[bool]:
    """True = yes, False = no, None = unclear. A negation cue wins over a weak yes
    ("I didn't take it" is False) but conflicts with an explicit yes ("yes, but I
    forgot ...") are returned as None."""
    lowered = _NO_PROBLEM.sub(" ", _normalize(text))
    negative = bool(_NO_CUES.search(lowered))
    strong = bool(_STRONG_YES.search(lowered))
    weak = bool(_WEAK_YES.search(lowered))
    if negative and strong:
        return None
    if negative:
        return False
    if strong or weak:
        return True
    return None


# -----------------------------------------------------------------------------
# Questions
# -----------------------------------------------------------------------------
def _diabetes_next_question(step: DiabetesStep) -> str:
    return {
        DiabetesStep.GREETING:
            "How are you feeling today? Any symptoms you'd like to report?",
        DiabetesStep.GLUCOSE_READING:
            "Have you measured your blood sugar today? If so, what was the reading in "
            "mg/dL (and was it fasting or after a meal)?",
        DiabetesStep.MISSING_DATA_CHECKPOINT:
            "No problem. Can you tell me roughly how you've been feeling instead (for "
            "example more thirsty than usual, tired, or dizzy)? If you do have a "
            "reading, please give it in mg/dL.",
        DiabetesStep.HYPERGLYCEMIA_SYMPTOMS:
            "Have you noticed increased thirst, frequent urination, or blurred vision?",
        DiabetesStep.HYPOGLYCEMIA_SYMPTOMS:
            "Any shakiness, sweating, or confusion that improved after eating?",
        DiabetesStep.ADHERENCE:
            "Have you taken your diabetes medication as prescribed today?",
        DiabetesStep.LIFESTYLE:
            "Any changes in your diet, exercise, or stress levels recently?",
    }[step]


def _hypertension_next_question(step: HypertensionStep) -> str:
    return {
        HypertensionStep.GREETING:
            "How are you feeling today? Any symptoms you'd like to report?",
        HypertensionStep.BP_READING:
            "Have you measured your blood pressure today? If so, what was the reading "
            "(for example 130/85)?",
        HypertensionStep.MISSING_DATA_CHECKPOINT:
            "That's okay. Can you describe how you've been feeling instead (for example "
            "headaches, dizziness, or palpitations)? If you do have a reading, please "
            "give it like 130/85.",
        HypertensionStep.ASSOCIATED_SYMPTOMS:
            "Any dizziness, blurred vision, shortness of breath, or palpitations along "
            "with that?",
        HypertensionStep.ADHERENCE:
            "Did you take your blood pressure medication today?",
        HypertensionStep.LIFESTYLE:
            "How has your sodium intake, sleep, or stress been recently?",
    }[step]


def get_current_question(state: InterviewState) -> Optional[str]:
    """The question the UI should show now, or None if not started / finished."""
    if not state.step or state.step == INTERVIEW_COMPLETE:
        return None
    if state.active_condition == "diabetes":
        return _diabetes_next_question(DiabetesStep(state.step))
    return _hypertension_next_question(HypertensionStep(state.step))


# -----------------------------------------------------------------------------
# State machine (mutates the copy made by adaptive_interview_node)
# -----------------------------------------------------------------------------
def _diabetes_advance(state: InterviewState, answer: str) -> InterviewState:
    triggered, reason = run_stage1_red_flag_screen(answer)
    if triggered:
        state.stage1_red_flag = True
        state.stage1_reason = reason
        state.step = DiabetesStep.COMPLETE.value
        return state

    step = DiabetesStep(state.step)
    answers = state.answers
    if step == DiabetesStep.GREETING:
        answers["greeting_response"] = answer
        state.step = DiabetesStep.GLUCOSE_READING.value
    elif step == DiabetesStep.GLUCOSE_READING:
        reading = _try_parse_float(answer, *GLUCOSE_RANGE_MG_DL, reject_units=("mmol",))
        if reading is None and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            state.step = DiabetesStep.MISSING_DATA_CHECKPOINT.value
        else:
            answers["glucose_reading"] = reading
            state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.MISSING_DATA_CHECKPOINT:
        reading = _try_parse_float(answer, *GLUCOSE_RANGE_MG_DL, reject_units=("mmol",))
        answers["glucose_reading"] = reading
        if reading is None:
            answers["symptom_only_note"] = answer
        state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.HYPERGLYCEMIA_SYMPTOMS:
        answers["hyperglycemia_symptoms"] = answer
        state.step = (DiabetesStep.HYPOGLYCEMIA_SYMPTOMS.value
                      if state.on_insulin_or_sulfonylurea else DiabetesStep.ADHERENCE.value)
    elif step == DiabetesStep.HYPOGLYCEMIA_SYMPTOMS:
        answers["hypoglycemia_symptoms"] = answer
        state.step = DiabetesStep.ADHERENCE.value
    elif step == DiabetesStep.ADHERENCE:
        answers["adherence"] = _looks_affirmative(answer)
        state.step = DiabetesStep.LIFESTYLE.value
    elif step == DiabetesStep.LIFESTYLE:
        answers["lifestyle_notes"] = answer
        state.step = DiabetesStep.COMPLETE.value
    return state


def _hypertension_advance(state: InterviewState, answer: str) -> InterviewState:
    triggered, reason = run_stage1_red_flag_screen(answer)
    if triggered:
        state.stage1_red_flag = True
        state.stage1_reason = reason
        state.step = HypertensionStep.COMPLETE.value
        return state

    step = HypertensionStep(state.step)
    answers = state.answers
    if step == HypertensionStep.GREETING:
        answers["greeting_response"] = answer
        state.step = HypertensionStep.BP_READING.value
    elif step == HypertensionStep.BP_READING:
        reading = _try_parse_bp(answer)
        if reading is None and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            state.step = HypertensionStep.MISSING_DATA_CHECKPOINT.value
        else:
            answers["bp_reading"] = reading
            state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
    elif step == HypertensionStep.MISSING_DATA_CHECKPOINT:
        reading = _try_parse_bp(answer)
        answers["bp_reading"] = reading
        if reading is None:
            answers["symptom_only_note"] = answer
        state.step = HypertensionStep.ASSOCIATED_SYONOM_ONLY_NOTE if False else HypertensionStep.ASSOCIATED_SYMPTOMS.value
    elif step == HypertensionStep.ASSOCIATED_SYMPTOMS:
        answers["associated_symptoms"] = answer
        state.step = HypertensionStep.ADHERENCE.value
    elif step == HypertensionStep.ADHERENCE:
        answers["adherence"] = _looks_affirmative(answer)
        state.step = HypertensionStep.LIFESTYLE.value
    elif step == HypertensionStep.LIFESTYLE:
        answers["lifestyle_notes"] = answer
        state.step = HypertensionStep.COMPLETE.value
    return state


def _compute_confidence(state: InterviewState, missing_reading: bool) -> Confidence:
    """Completeness label. A missing reading is Low even on a cold start; a complete
    first-ever check-in is capped at Medium (nothing yet to confirm it against)."""
    if missing_reading:
        return Confidence.LOW
    if state.is_cold_start:
        return Confidence.MEDIUM
    return Confidence.HIGH


def _start_condition_flow(state: InterviewState, condition: str) -> InterviewState:
    state.active_condition = condition
    state.step = (DiabetesStep.GREETING.value if condition == "diabetes"
                  else HypertensionStep.GREETING.value)
    state.missing_data_asked_once = False
    state.answers = {}
    return state


def _pivot_to_next_condition(state: InterviewState, condition: str) -> InterviewState:
    """Dual diagnosis: keep the symptom the patient already described and go straight
    to the second condition's reading. Stage 1 runs on every answer, so nothing is
    skipped by not repeating the greeting."""
    previous_symptom = state.answers.get("greeting_response", "")
    state.active_condition = condition
    state.missing_data_asked_once = False
    state.answers = {"greeting_response": previous_symptom}
    state.step = (DiabetesStep.GLUCOSE_READING.value if condition == "diabetes"
                  else HypertensionStep.BP_READING.value)
    return state


def _finalize_intake(state: InterviewState) -> InterviewState:
    condition = state.active_condition
    answers = state.answers

    if state.stage1_red_flag:
        intake: Dict[str, Any] = {"condition": condition, "emergency": True,
                                  "reason": state.stage1_reason}
    else:
        if condition == "diabetes":
            value = answers.get("glucose_reading")
            readings = ([] if value is None else
                        [{"observation_type": "glucose", "value": value, "unit": "mg/dL"}])
            symptom_keys = ("hyperglycemia_symptoms", "hypoglycemia_symptoms", "symptom_only_note")
        else:
            bp = answers.get("bp_reading")
            readings = ([] if bp is None else [
                {"observation_type": "blood_pressure_systolic", "value": float(bp[0]), "unit": "mmHg"},
                {"observation_type": "blood_pressure_diastolic", "value": float(bp[1]), "unit": "mmHg"},
            ])
            symptom_keys = ("associated_symptoms", "symptom_only_note")
        missing = not readings
        intake = {
            "condition": condition,
            "emergency": False,
            "readings": readings,
            "symptoms": {k: answers[k] for k in symptom_keys if k in answers},
            "adherence": answers.get("adherence"),
            "lifestyle_notes": answers.get("lifestyle_notes"),
            "confidence": _compute_confidence(state, missing).value,
            "missing_data": missing,
        }

    state.intake = intake
    state.intakes.append(copy.deepcopy(intake))

    if state.dual_diagnosis_pending and not state.stage1_red_flag:
        return _pivot_to_next_condition(state, state.dual_diagnosis_pending.pop(0))
    state.dual_diagnosis_pending = []
    state.step = INTERVIEW_COMPLETE
    return state


def _validate_new_session(state: InterviewState) -> None:
    if not state.patient_id or not str(state.patient_id).strip():
        raise ValueError("patient_id is required.")
    cleaned: List[str] = []
    for condition in state.conditions_on_file:
        name = str(condition).strip().lower()
        if name not in SUPPORTED_CONDITIONS:
            raise ValueError(f"Unsupported condition '{condition}'. Supported: {SUPPORTED_CONDITIONS}.")
        if name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        raise ValueError("conditions_on_file must contain at least one condition.")
    state.conditions_on_file = cleaned


# -----------------------------------------------------------------------------
# Public entry point
# -----------------------------------------------------------------------------
def adaptive_interview_node(state: InterviewState,
                            patient_response: Optional[str] = None) -> InterviewState:
    """Advances the interview by one answer and returns a NEW state (input untouched).

    * patient_response=None on a fresh state starts the session (first question ready).
    * patient_response=None on a started state returns it unchanged.
    * A blank answer does not advance the interview.
    * Answering before the start, or after completion, raises ValueError.
    """
    state = copy.deepcopy(state)

    if patient_response is None:
        if not state.step:
            _validate_new_session(state)
            state.dual_diagnosis_pending = list(state.conditions_on_file[1:])
            state.stage1_red_flag = False
            state.stage1_reason = None
            return _start_condition_flow(state, state.conditions_on_file[0])
        return state

    if not state.step:
        raise ValueError("Interview not started: call with patient_response=None first.")
    if state.step == INTERVIEW_COMPLETE:
        raise ValueError("Interview already complete.")

    answer = patient_response.strip()
    if not answer:
        return state

    if state.active_condition == "diabetes":
        state = _diabetes_advance(state, answer)
    else:
        state = _hypertension_advance(state, answer)

    if state.step == DiabetesStep.COMPLETE.value or state.step == HypertensionStep.COMPLETE.value:
        state = _finalize_intake(state)
    return state


# -----------------------------------------------------------------------------
# Bridge into Reconciliation / Verification
# -----------------------------------------------------------------------------
def build_checkin_bundle(state: InterviewState, source: str, patient_name: str,
                         checkin_timestamp: Optional[str] = None) -> Dict[str, Any]:
    """Turns the finished interview's readings into a bundle for reconcile_bundles()
    (as bundle_b, the new check-in).

    `source` must be the SAME store as the prior record ("fhir" in Connected Mode,
    "local" in Isolated Mode) or reconcile_bundles() raises its Store Invariant
    ValueError. A patient with no usable readings gets an empty observation list, which
    reconciliation reports as "missing" rather than guessing.
    Emergency sessions bypass reconciliation entirely, so no bundle is built for them."""
    if state.step != INTERVIEW_COMPLETE:
        raise ValueError("Interview is not complete.")
    if state.stage1_red_flag:
        raise ValueError("Emergency sessions bypass reconciliation; no check-in bundle is built.")
    clean_source = (source or "").strip().lower()
    if clean_source not in ("fhir", "local"):
        raise ValueError(f"source must be 'fhir' or 'local', got '{source}'.")

    timestamp = checkin_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = re.sub(r"[^0-9A-Za-z]", "", timestamp)
    observations = [
        NormalizedObservation(
            patient_id=state.patient_id,
            observation_type=reading["observation_type"],
            value=reading["value"],
            unit=reading["unit"],
            timestamp=timestamp,
            source=clean_source,
            source_record_id=f"CHECKIN-{state.patient_id}-{stamp}-{reading['observation_type']}",
        )
        for intake in state.intakes
        for reading in intake.get("readings", [])
    ]
    return {
        "patient": NormalizedPatient(patient_id=state.patient_id, name=patient_name),
        "observations": observations,
        "medications": [],
    }


def build_checkin_origins(bundle: Dict[str, Any]) -> Dict[str, str]:
    """Origin tags for verify_reconciliation(): every check-in reading is self-reported."""
    return {obs.source_record_id: SELF_REPORTED_ORIGIN for obs in bundle["observations"]}
