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
5. Dangerous reading (proposal section 27): check_dangerous_bp() reports a blood pressure with
   systolic >= 180 or diastolic >= 120 (AHA hypertensive-crisis benchmark cited in the proposal).
   A single number never ends the interview and never decides an emergency by itself: the
   reading is kept and the Triage Protocol (agents/triage_protocol.py) confirms it with a
   re-measure, a symptom check and the circumstances before any level is assigned. The limits
   are configuration constants (DANGEROUS_BP_*), illustrative and NOT clinical guidance; a
   clinician must confirm them before anyone relies on them.
6. Confidence is a COMPLETENESS label only: Low if the reading is missing, otherwise
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
from agents.answer_validation import validate_glucose_input

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
# Stage 1 dangerous-reading limits (proposal section 27). Illustrative; NOT clinical guidance.
DANGEROUS_BP_SYSTOLIC_MMHG = 180
DANGEROUS_BP_DIASTOLIC_MMHG = 120


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DiabetesStep(str, Enum):
    GREETING = "greeting"
    GLUCOSE_READING = "glucose_reading"
    MISSING_DATA_CHECKPOINT = "missing_data_checkpoint"
    GLUCOSE_CONTEXT = "glucose_context"
    HYPO_EVENTS_PAST_WEEK = "hypo_events_past_week"
    SICK_DAY_FLAGS = "sick_day_flags"
    HYPERGLYCEMIA_SYMPTOMS = "hyperglycemia_symptoms"
    HYPOGLYCEMIA_SYMPTOMS = "hypoglycemia_symptoms"
    FOOT_PROBLEMS = "foot_problems"
    ADHERENCE = "adherence"
    MISSED_DOSES_REASON = "missed_doses_reason"
    LIFESTYLE = "lifestyle"
    PATIENT_FREE_TEXT = "patient_free_text"
    COMPLETE = "complete"


class HypertensionStep(str, Enum):
    GREETING = "greeting"
    BP_READING = "bp_reading"
    MISSING_DATA_CHECKPOINT = "missing_data_checkpoint"
    BP_TECHNIQUE = "bp_technique"
    ASSOCIATED_SYMPTOMS = "associated_symptoms"
    OTC_MEDS_BP = "otc_meds_bp"
    ADHERENCE = "adherence"
    MISSED_DOSES_REASON = "missed_doses_reason"
    LIFESTYLE = "lifestyle"
    PATIENT_FREE_TEXT = "patient_free_text"
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
    interview_version: str = "v1"

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
                   "pain in my chest", "crushing chest", "crushing chest pain", "heavy chest", "سینے میں درد"],
    "breathing": ["can't breathe", "cant breathe", "cannot breathe", "struggling to breathe",
                  "severe shortness of breath", "gasping for air", "suffocating",
                  "سانس لینے میں دشواری", "سانس نہیں آ رہی"],
    "confusion": ["confused", "slurred speech", "can't speak clearly", "cant speak clearly"],
    "loss_of_consciousness": ["fainted", "passed out", "lost consciousness", "blacked out", "collapsed", "بے ہوش"],
    "one_sided_weakness": ["one side weak", "one-sided weakness", "can't move one side",
                           "cant move one side", "can't move my arm", "face drooping"],
    "unable_to_keep_fluids": ["can't keep anything down", "cant keep anything down",
                              "can't keep fluids down", "vomiting nonstop", "vomiting non-stop", "vomiting with high sugar"],
    "severe_headache": ["worst headache", "severe headache", "thunderclap headache", "worst headache of my life", "sudden severe headache"],
    "vision_loss": ["sudden vision loss", "lost my vision", "went blind",
                    "can't see at all", "cannot see at all"],
}

_NEGATION_CUES = frozenset({
    "no", "not", "never", "without", "denies", "deny",
    "don't", "dont", "doesn't", "doesnt", "didn't", "didnt",
    "haven't", "havent", "hasn't", "hasnt", "isn't", "isnt",
})
_CLAUSE_BREAK = re.compile(r"[.;,:!?\n]+|\b(?:but|however|although|though|and|while)\b")
_EASTERN_DIGITS_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _normalize(text: str) -> str:
    return (text or "").replace("\u2019", "'").replace("\u2018", "'").translate(_EASTERN_DIGITS_TABLE).lower()


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
    lowered = (text or "").replace("\u2019", "'").replace("\u2018", "'").translate(_EASTERN_DIGITS_TABLE).lower()
    if any(unit in lowered for unit in reject_units) or _has_negative_number(lowered) or "mmol" in lowered:
        return None
    cleaned = _TIME_OF_DAY.sub(" ", lowered)
    cleaned = re.sub(r"(?<=\d),(?=\d)", ".", cleaned)
    values = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", cleaned)]
    plausible = [v for v in values
                 if (minimum is None or v >= minimum) and (maximum is None or v <= maximum)]
    return plausible[0] if len(plausible) == 1 else None


def _try_parse_bp(text: str) -> Optional[List[int]]:
    """Returns [systolic, diastolic] if exactly one plausible pair is present, else None."""
    if _has_negative_number(text):
        return None
    lowered = (text or "").replace("\u2019", "'").replace("\u2018", "'").translate(_EASTERN_DIGITS_TABLE).lower()
    cleaned = _TIME_OF_DAY.sub(" ", lowered)
    pairs = []
    for sys_s, dia_s in re.findall(r"(\d{2,3})\s*(?:/|over)\s*(\d{2,3})", cleaned):
        sys_v, dia_v = int(sys_s), int(dia_s)
        if (SYSTOLIC_RANGE_MMHG[0] <= sys_v <= SYSTOLIC_RANGE_MMHG[1]
                and DIASTOLIC_RANGE_MMHG[0] <= dia_v <= DIASTOLIC_RANGE_MMHG[1]
                and sys_v > dia_v):
            pairs.append([sys_v, dia_v])
    return pairs[0] if len(pairs) == 1 else None


def check_dangerous_bp(reading: Optional[List[int]]) -> Optional[str]:
    """Returns "bp_crisis_range" if either component reaches its limit, else None."""
    if reading and (reading[0] >= DANGEROUS_BP_SYSTOLIC_MMHG
                    or reading[1] >= DANGEROUS_BP_DIASTOLIC_MMHG):
        return "bp_crisis_range"
    return None


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
        DiabetesStep.GLUCOSE_CONTEXT:
            "Was this blood sugar reading fasting (before breakfast), before a meal, after a meal, or at bedtime?",
        DiabetesStep.HYPO_EVENTS_PAST_WEEK:
            "In the past 7 days, have you had any low blood sugar episodes, like shakiness, sweating, or feeling faint?",
        DiabetesStep.SICK_DAY_FLAGS:
            "Are you currently experiencing vomiting, diarrhoea, high fever, or unable to drink fluids?",
        DiabetesStep.HYPERGLYCEMIA_SYMPTOMS:
            "Have you noticed increased thirst, frequent urination, or blurred vision?",
        DiabetesStep.HYPOGLYCEMIA_SYMPTOMS:
            "Any shakiness, sweating, or confusion that improved after eating?",
        DiabetesStep.FOOT_PROBLEMS:
            "Do you have any new cuts, sores, blisters, pain, or numbness in your feet?",
        DiabetesStep.ADHERENCE:
            "Have you taken your diabetes medication as prescribed today?",
        DiabetesStep.MISSED_DOSES_REASON:
            "Can you share what caused you to miss your medication dose (for example side effects, running out, or forgot)?",
        DiabetesStep.LIFESTYLE:
            "Any changes in your diet, exercise, or stress levels recently?",
        DiabetesStep.PATIENT_FREE_TEXT:
            "Is there anything else you would like your clinician to know about your health today?",
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
        HypertensionStep.BP_TECHNIQUE:
            "Before taking your blood pressure, did you rest quietly for 5 minutes with your back and arm supported?",
        HypertensionStep.ASSOCIATED_SYMPTOMS:
            "Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations?",
        HypertensionStep.OTC_MEDS_BP:
            "Have you taken any anti-inflammatory painkillers (like ibuprofen), cold/decongestant medicines, or herbal supplements recently?",
        HypertensionStep.ADHERENCE:
            "Did you take your blood pressure medication today?",
        HypertensionStep.MISSED_DOSES_REASON:
            "Can you share what caused you to miss your medication dose (for example side effects, running out, or forgot)?",
        HypertensionStep.LIFESTYLE:
            "How has your sodium intake, sleep, or stress been recently?",
        HypertensionStep.PATIENT_FREE_TEXT:
            "Is there anything else you would like your clinician to know about your health today?",
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
def _has_glucose_context_in_text(text: str) -> bool:
    lowered = _normalize(text)
    return any(w in lowered for w in ["fasting", "before meal", "before breakfast", "after meal", "after lunch", "after dinner", "bedtime", "random"])


def _has_bp_technique_in_text(text: str) -> bool:
    lowered = _normalize(text)
    return any(w in lowered for w in ["rested", "sitting", "seated", "clinic", "home"])


def _process_glucose_input(answer: str, previously_asked: bool = False, allow_mmol_conversion: bool = True) -> Tuple[Optional[float], Optional[str], bool, Optional[str], Optional[str]]:
    v_res = validate_glucose_input(answer, previously_asked_unit=previously_asked)
    if v_res.valid:
        val = v_res.value
        if v_res.unit == "mmol/L":
            if allow_mmol_conversion:
                val_mgdl = round(float(val) * 18.0182, 1)
                return val_mgdl, "mg/dL", False, None, None
            return None, None, True, None, None
        return float(val), v_res.unit, False, None, None
    if v_res.needs_unit_clarification:
        return None, None, True, None, None
    if v_res.is_possible_severe_low or (previously_asked and v_res.value is not None and float(v_res.value) <= 54):
        val = float(v_res.value) if v_res.value is not None else 35.0
        guidance = v_res.safety_guidance or "Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, consume 15g fast-acting sugar immediately."
        reason = v_res.review_reason or "glucose value unit unclear, possible low"
        return val, "unclear", False, guidance, reason
    return None, None, False, None, None


def _diabetes_advance_v2_3(state: InterviewState, answer: str) -> InterviewState:
    step = DiabetesStep(state.step)
    answers = state.answers

    if step == DiabetesStep.GREETING:
        answers["greeting_response"] = answer
        state.step = DiabetesStep.GLUCOSE_READING.value
    elif step == DiabetesStep.GLUCOSE_READING:
        reading, unit, needs_clarify, guidance, rev_reason = _process_glucose_input(answer, previously_asked=False)
        if needs_clarify and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            answers["_glucose_pending_raw"] = answer
            state.step = DiabetesStep.MISSING_DATA_CHECKPOINT.value
        elif reading is None and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            state.step = DiabetesStep.MISSING_DATA_CHECKPOINT.value
        else:
            answers["glucose_reading"] = reading
            if guidance:
                answers["possible_severe_low"] = True
                answers["safety_guidance"] = guidance
                answers["review_reason"] = rev_reason
            if _has_glucose_context_in_text(answer):
                answers["glucose_context"] = "extracted_from_reading"
                if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):
                    state.step = DiabetesStep.HYPO_EVENTS_PAST_WEEK.value
                elif reading is not None and reading >= 250:
                    state.step = DiabetesStep.SICK_DAY_FLAGS.value
                else:
                    state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
            else:
                state.step = DiabetesStep.GLUCOSE_CONTEXT.value
    elif step == DiabetesStep.MISSING_DATA_CHECKPOINT:
        pending_raw = answers.pop("_glucose_pending_raw", None)
        combined_answer = f"{pending_raw} {answer}" if pending_raw else answer
        reading, unit, _, guidance, rev_reason = _process_glucose_input(combined_answer, previously_asked=True)
        if reading is None and pending_raw:
            reading, unit, _, guidance, rev_reason = _process_glucose_input(answer, previously_asked=True)

        answers["glucose_reading"] = reading
        if guidance:
            answers["possible_severe_low"] = True
            answers["safety_guidance"] = guidance
            answers["review_reason"] = rev_reason

        if reading is None and not answers.get("possible_severe_low"):
            answers["symptom_only_note"] = answer
            state.step = DiabetesStep.SICK_DAY_FLAGS.value
        else:
            if _has_glucose_context_in_text(answer):
                answers["glucose_context"] = "extracted_from_reading"
                state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
            else:
                state.step = DiabetesStep.GLUCOSE_CONTEXT.value
    elif step == DiabetesStep.GLUCOSE_CONTEXT:
        answers["glucose_context"] = answer
        reading = answers.get("glucose_reading")
        if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):
            state.step = DiabetesStep.HYPO_EVENTS_PAST_WEEK.value
        elif reading is not None and reading >= 250:
            state.step = DiabetesStep.SICK_DAY_FLAGS.value
        else:
            state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.HYPO_EVENTS_PAST_WEEK:
        answers["hypo_events_past_week"] = answer
        state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.SICK_DAY_FLAGS:
        answers["sick_day_flags"] = answer
        state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.HYPERGLYCEMIA_SYMPTOMS:
        answers["hyperglycemia_symptoms"] = answer
        state.step = DiabetesStep.FOOT_PROBLEMS.value
    elif step == DiabetesStep.FOOT_PROBLEMS:
        answers["foot_problems"] = answer
        state.step = DiabetesStep.ADHERENCE.value
    elif step == DiabetesStep.ADHERENCE:
        adh = _looks_affirmative(answer)
        answers["adherence"] = adh
        if adh is False:
            state.step = DiabetesStep.MISSED_DOSES_REASON.value
        else:
            state.step = DiabetesStep.LIFESTYLE.value
    elif step == DiabetesStep.MISSED_DOSES_REASON:
        answers["missed_doses_reason"] = answer
        state.step = DiabetesStep.LIFESTYLE.value
    elif step == DiabetesStep.LIFESTYLE:
        answers["lifestyle_notes"] = answer
        state.step = DiabetesStep.PATIENT_FREE_TEXT.value
    elif step == DiabetesStep.PATIENT_FREE_TEXT:
        answers["patient_free_text"] = answer
        state.step = DiabetesStep.COMPLETE.value
    return state


def _hypertension_advance_v2_3(state: InterviewState, answer: str) -> InterviewState:
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
            if reading is not None and not _has_bp_technique_in_text(answer):
                state.step = HypertensionStep.BP_TECHNIQUE.value
            else:
                answers["bp_technique"] = "extracted_or_missing"
                state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
    elif step == HypertensionStep.MISSING_DATA_CHECKPOINT:
        reading = _try_parse_bp(answer)
        answers["bp_reading"] = reading
        if reading is None:
            answers["symptom_only_note"] = answer
            state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
        else:
            if not _has_bp_technique_in_text(answer):
                state.step = HypertensionStep.BP_TECHNIQUE.value
            else:
                answers["bp_technique"] = "extracted_or_missing"
                state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
    elif step == HypertensionStep.BP_TECHNIQUE:
        answers["bp_technique"] = answer
        state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
    elif step == HypertensionStep.ASSOCIATED_SYMPTOMS:
        answers["associated_symptoms"] = answer
        bp = answers.get("bp_reading")
        if bp is None or bp[0] >= 140 or bp[1] >= 90:
            state.step = HypertensionStep.OTC_MEDS_BP.value
        else:
            state.step = HypertensionStep.ADHERENCE.value
    elif step == HypertensionStep.OTC_MEDS_BP:
        answers["otc_meds_bp"] = answer
        state.step = HypertensionStep.ADHERENCE.value
    elif step == HypertensionStep.ADHERENCE:
        adh = _looks_affirmative(answer)
        answers["adherence"] = adh
        if adh is False:
            state.step = HypertensionStep.MISSED_DOSES_REASON.value
        else:
            state.step = HypertensionStep.LIFESTYLE.value
    elif step == HypertensionStep.MISSED_DOSES_REASON:
        answers["missed_doses_reason"] = answer
        state.step = HypertensionStep.LIFESTYLE.value
    elif step == HypertensionStep.LIFESTYLE:
        answers["lifestyle_notes"] = answer
        state.step = HypertensionStep.PATIENT_FREE_TEXT.value
    elif step == HypertensionStep.PATIENT_FREE_TEXT:
        answers["patient_free_text"] = answer
        state.step = HypertensionStep.COMPLETE.value
    return state


def _diabetes_advance(state: InterviewState, answer: str) -> InterviewState:
    triggered, reason = run_stage1_red_flag_screen(answer)
    if triggered:
        state.stage1_red_flag = True
        state.stage1_reason = reason
        state.step = DiabetesStep.COMPLETE.value
        return state

    if state.interview_version == "v2.3":
        return _diabetes_advance_v2_3(state, answer)

    step = DiabetesStep(state.step)
    answers = state.answers
    if step == DiabetesStep.GREETING:
        answers["greeting_response"] = answer
        state.step = DiabetesStep.GLUCOSE_READING.value
    elif step == DiabetesStep.GLUCOSE_READING:
        reading, unit, needs_clarify, guidance, rev_reason = _process_glucose_input(answer, previously_asked=False)
        if needs_clarify and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            answers["_glucose_pending_raw"] = answer
            state.step = DiabetesStep.MISSING_DATA_CHECKPOINT.value
        elif reading is None and not state.missing_data_asked_once:
            state.missing_data_asked_once = True
            state.step = DiabetesStep.MISSING_DATA_CHECKPOINT.value
        else:
            answers["glucose_reading"] = reading
            if guidance:
                answers["possible_severe_low"] = True
                answers["safety_guidance"] = guidance
                answers["review_reason"] = rev_reason
            state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value
    elif step == DiabetesStep.MISSING_DATA_CHECKPOINT:
        pending_raw = answers.pop("_glucose_pending_raw", None)
        combined_answer = f"{pending_raw} {answer}" if pending_raw else answer
        reading, unit, _, guidance, rev_reason = _process_glucose_input(combined_answer, previously_asked=True)
        if reading is None and pending_raw:
            reading, unit, _, guidance, rev_reason = _process_glucose_input(answer, previously_asked=True)

        answers["glucose_reading"] = reading
        if guidance:
            answers["possible_severe_low"] = True
            answers["safety_guidance"] = guidance
            answers["review_reason"] = rev_reason

        if reading is None and not answers.get("possible_severe_low"):
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

    if state.interview_version == "v2.3":
        return _hypertension_advance_v2_3(state, answer)

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
        state.step = HypertensionStep.ASSOCIATED_SYMPTOMS.value
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
            symptom_keys = (
                "hyperglycemia_symptoms", "hypoglycemia_symptoms", "symptom_only_note",
                "glucose_context", "hypo_events_past_week", "sick_day_flags", "foot_problems"
            )
            symptoms = {k: answers[k] for k in symptom_keys if k in answers}
            if answers.get("possible_severe_low"):
                symptoms["possible_severe_low"] = True
                symptoms["safety_guidance"] = answers.get("safety_guidance")
                symptoms["review_reason"] = answers.get("review_reason")
        else:
            bp = answers.get("bp_reading")
            readings = ([] if bp is None else [
                {"observation_type": "blood_pressure_systolic", "value": float(bp[0]), "unit": "mmHg"},
                {"observation_type": "blood_pressure_diastolic", "value": float(bp[1]), "unit": "mmHg"},
            ])
            symptom_keys = (
                "associated_symptoms", "symptom_only_note",
                "bp_technique", "otc_meds_bp"
            )
            symptoms = {k: answers[k] for k in symptom_keys if k in answers}
        missing = not readings
        confidence = _compute_confidence(state, missing).value
        if answers.get("possible_severe_low"):
            confidence = Confidence.LOW.value
        intake = {
            "condition": condition,
            "emergency": False,
            "readings": readings,
            "symptoms": symptoms,
            "adherence": answers.get("adherence"),
            "missed_doses_reason": answers.get("missed_doses_reason"),
            "lifestyle_notes": answers.get("lifestyle_notes"),
            "free_text_note": answers.get("patient_free_text"),
            "confidence": confidence,
            "missing_data": missing,
            "requires_review": True if answers.get("possible_severe_low") else False,
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
