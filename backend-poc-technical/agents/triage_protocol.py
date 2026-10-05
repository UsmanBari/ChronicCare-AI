"""
Triage Protocol (Iteration 1)

A single number never decides an emergency. When a check-in contains a reading that needs
attention, the patient is asked a short, fixed series of confirmation questions, and only
then is a level assigned: re-measure after rest, warning symptoms, things that can raise or
lower the reading (medicines, caffeine, pain, exertion, a missed dose), and the patient's own
recent baseline. The method follows the shape of nurse telephone triage (red flags first,
symptom-specific questions, a graded outcome); no licensed protocol text is used. The
questions and rules are original and based on public guidance (ACC/AHA 2017 blood-pressure
guideline, ADA Standards of Care, and Sections 14, 15 and 27 of the project proposal).

EVERY THRESHOLD BELOW IS ILLUSTRATIVE, NOT CLINICAL GUIDANCE. A clinician must review the
table before anyone relies on it (see docs/CLINICAL_RULES.md).

A warning symptom that already settles an emergency ends the questions at once (a person who
may be in danger is not asked about medicines). Deterministic and rule based. No diagnosis,
no risk score, no language model. One call
advances the protocol by one answer and returns a NEW state, so a stateless API can store it
as JSON (TriageProtocolState.to_dict() / from_dict()).

=============================================================================
LEVELS (what the system tells the patient and the clinician)
=============================================================================
  emergency  Call the local emergency number now. Provider alerted at once.
  urgent     Contact the clinician today. Provider review, highest priority after emergencies.
  review     A clinician looks at it in the normal review queue.
  routine    Nothing to flag.

=============================================================================
WHAT STARTS A PROTOCOL (evaluate_triggers; highest priority first)
=============================================================================
  bp_severe     systolic >= 180 or diastolic >= 120
  glucose_high  glucose >= 250 mg/dL
  glucose_low   glucose <  70 mg/dL
  bp_low        systolic < 90 or diastolic < 60
  bp_change     systolic at least 20 mmHg above the patient's own recent median
                (needs at least 3 readings in the last 14 days, last 7 used); a rise
                of 40 or more is a "marked" change

AGE. Adults only (18 and over): paediatric blood pressure is judged against age, sex and
height percentiles and is out of scope. For adults the ACC/AHA categories and the crisis
limits do not change with age; age band changes the questions (people of 65 and over are
also asked about dizziness on standing and about falls) and is shown to the clinician.
=============================================================================
"""

from __future__ import annotations

import copy
import re
import statistics
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.adaptive_interview_agent import (
    DANGEROUS_BP_DIASTOLIC_MMHG,
    DANGEROUS_BP_SYSTOLIC_MMHG,
    _looks_affirmative,
    _normalize,
    _try_parse_bp,
    run_stage1_red_flag_screen,
)

# Illustrative thresholds (see the module docstring).
MIN_ADULT_AGE = 18
OLDER_ADULT_AGE = 65
MAX_PLAUSIBLE_AGE = 120
BP_STAGE2_SYSTOLIC_MMHG = 140
BP_STAGE2_DIASTOLIC_MMHG = 90
BP_LOW_SYSTOLIC_MMHG = 90
BP_LOW_DIASTOLIC_MMHG = 60
BP_CHANGE_NOTABLE_MMHG = 20
BP_CHANGE_MARKED_MMHG = 40
BASELINE_MIN_READINGS = 3
BASELINE_MAX_READINGS = 7
BASELINE_WINDOW_DAYS = 14
GLUCOSE_HIGH_MG_DL = 250
GLUCOSE_URGENT_MG_DL = 300
GLUCOSE_LOW_MG_DL = 70
GLUCOSE_VERY_LOW_MG_DL = 54

SYSTOLIC = "blood_pressure_systolic"
DIASTOLIC = "blood_pressure_diastolic"
GLUCOSE = "glucose"


class TriageLevel(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    REVIEW = "review"
    ROUTINE = "routine"


LEVEL_RANK = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}

GUIDANCE = {
    "emergency": "Call your local emergency number now. Your care team is being alerted.",
    "urgent": "Please contact your clinician today. If you feel worse, call your local emergency number.",
    "review": "A clinician will review this. Please measure again later today and at the same time tomorrow.",
    "routine": "",
}


def _raise_level(current: str, minimum: str) -> str:
    return minimum if LEVEL_RANK[minimum] > LEVEL_RANK[current] else current


# -----------------------------------------------------------------------------
# Age
# -----------------------------------------------------------------------------
def age_band(age_years: Any) -> str:
    if isinstance(age_years, bool) or not isinstance(age_years, (int, float)) or age_years != age_years:
        raise ValueError("A valid age is required.")
    if age_years < MIN_ADULT_AGE:
        raise ValueError("ChronicCare AI is for adults (18 and over) in this release.")
    if age_years > MAX_PLAUSIBLE_AGE:
        raise ValueError("Implausible age.")
    return "older_65_plus" if age_years >= OLDER_ADULT_AGE else "adult_18_64"


# -----------------------------------------------------------------------------
# The patient's own recent baseline
# -----------------------------------------------------------------------------
@dataclass
class Baseline:
    systolic: Optional[float] = None
    diastolic: Optional[float] = None
    n: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def compute_baseline(history: List[Dict[str, Any]], now: Optional[str] = None) -> Optional[Baseline]:
    """Median of the patient's own recent readings.

    `history` items: {"observation_type": SYSTOLIC | DIASTOLIC, "value": number, "timestamp": ISO}.
    Uses the most recent BASELINE_MAX_READINGS readings of each type inside the last
    BASELINE_WINDOW_DAYS days. Returns None unless there are at least BASELINE_MIN_READINGS
    systolic readings, so a baseline is never invented from one or two values."""
    current = _parse_time(now) or datetime.now(timezone.utc)
    earliest = current - timedelta(days=BASELINE_WINDOW_DAYS)
    by_type: Dict[str, List[tuple]] = {SYSTOLIC: [], DIASTOLIC: []}
    for item in history or []:
        kind = item.get("observation_type")
        when = _parse_time(item.get("timestamp"))
        value = item.get("value")
        if kind in by_type and when and isinstance(value, (int, float)) and earliest <= when <= current:
            by_type[kind].append((when, float(value)))
    medians: Dict[str, Optional[float]] = {}
    counts: Dict[str, int] = {}
    for kind, rows in by_type.items():
        rows.sort(key=lambda r: r[0], reverse=True)
        values = [v for _, v in rows[:BASELINE_MAX_READINGS]]
        counts[kind] = len(values)
        medians[kind] = statistics.median(values) if len(values) >= BASELINE_MIN_READINGS else None
    if medians[SYSTOLIC] is None:
        return None
    return Baseline(systolic=medians[SYSTOLIC], diastolic=medians[DIASTOLIC], n=counts[SYSTOLIC])


# -----------------------------------------------------------------------------
# What starts a protocol
# -----------------------------------------------------------------------------
@dataclass
class Trigger:
    protocol: str
    reason: str
    priority: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_triggers(readings: Dict[str, float], baseline: Optional[Baseline] = None) -> List[Trigger]:
    """Which protocols this check-in needs, highest priority first. Empty means routine."""
    sys_v, dia_v, glu = readings.get(SYSTOLIC), readings.get(DIASTOLIC), readings.get(GLUCOSE)
    triggers: List[Trigger] = []
    severe_bp = ((sys_v is not None and sys_v >= DANGEROUS_BP_SYSTOLIC_MMHG)
                 or (dia_v is not None and dia_v >= DANGEROUS_BP_DIASTOLIC_MMHG))
    if severe_bp:
        triggers.append(Trigger("bp_severe", f"Blood pressure {_fmt_bp(sys_v, dia_v)} is in the crisis range.", 1))
    if glu is not None and glu >= GLUCOSE_HIGH_MG_DL:
        triggers.append(Trigger("glucose_high", f"Glucose {glu:g} mg/dL is high.", 2))
    if glu is not None and glu < GLUCOSE_LOW_MG_DL:
        triggers.append(Trigger("glucose_low", f"Glucose {glu:g} mg/dL is low.", 3))
    if ((sys_v is not None and sys_v < BP_LOW_SYSTOLIC_MMHG)
            or (dia_v is not None and dia_v < BP_LOW_DIASTOLIC_MMHG)):
        triggers.append(Trigger("bp_low", f"Blood pressure {_fmt_bp(sys_v, dia_v)} is low.", 4))
    if (not severe_bp and baseline is not None and baseline.systolic is not None and sys_v is not None
            and sys_v - baseline.systolic >= BP_CHANGE_NOTABLE_MMHG):
        rise = sys_v - baseline.systolic
        triggers.append(Trigger(
            "bp_change",
            f"Systolic pressure is {rise:g} mmHg above your usual ({baseline.systolic:g}).", 5))
    return sorted(triggers, key=lambda t: t.priority)


def _fmt_bp(sys_v: Optional[float], dia_v: Optional[float]) -> str:
    return f"{sys_v:g}/{dia_v:g}" if sys_v is not None and dia_v is not None else f"{(sys_v or dia_v):g}"


# -----------------------------------------------------------------------------
# Questions (ordered, fixed). kind: "bp" re-measured pair, "yesno" yes or no with detail.
# -----------------------------------------------------------------------------
_SYMPTOMS_CRISIS = ("chest pain or pressure, trouble breathing, back pain, numbness or weakness, "
                    "a change in your vision, trouble speaking, a severe headache, or confusion")

_BP_SEVERE_QUESTIONS = [
    ("recheck", "bp", "Please sit down, rest quietly for 5 minutes, then measure your blood pressure "
                      "again. What is the new reading? If you cannot measure again, type: cannot"),
    ("symptoms", "yesno", f"Right now, do you have any of these: {_SYMPTOMS_CRISIS}? Answer yes or no."),
    ("substances", "yesno", "In the last few hours, did you take cold or flu medicine, painkillers such as "
                            "ibuprofen, steroids, or stimulants such as energy drinks, strong coffee or tea, "
                            "or nicotine, or did you miss your blood pressure medicine? Answer yes or no, "
                            "and tell me which."),
    ("circumstances", "yesno", "Just before the first reading, were you in pain, very upset or anxious, "
                               "or physically active? Answer yes or no."),
]
_BP_CHANGE_QUESTIONS = [
    ("symptoms", "yesno", "Do you have a headache, dizziness, a pounding heartbeat, blurred vision or "
                          "shortness of breath right now? Answer yes or no."),
    ("substances", "yesno", "In the last few hours, did you take cold or flu medicine, painkillers such as "
                            "ibuprofen, steroids, or stimulants such as energy drinks, strong coffee or tea, "
                            "or nicotine? Answer yes or no, and tell me which."),
    ("adherence", "yesno", "Did you take your blood pressure medicine as prescribed over the last two days? "
                           "Answer yes or no."),
    ("circumstances", "yesno", "Just before the reading, were you in pain, very upset or anxious, or "
                               "physically active? Answer yes or no."),
]
_BP_LOW_QUESTIONS = [
    ("symptoms", "yesno", "Do you feel dizzy, faint, very weak or unusually tired right now? Answer yes or no."),
    ("medicines", "yesno", "Did you recently start, stop or change a medicine, or have you been vomiting, "
                           "had diarrhoea, or been drinking very little? Answer yes or no, and tell me which."),
]
_GLUCOSE_HIGH_QUESTIONS = [
    ("dka_symptoms", "yesno", "Do you have nausea or vomiting, stomach pain, fast or deep breathing, "
                              "breath that smells fruity, or feel very drowsy? Answer yes or no."),
    ("thirst", "yesno", "Are you very thirsty and passing urine much more than usual? Answer yes or no."),
    ("context", "yesno", "Did you eat a large meal just before, miss your insulin or diabetes medicine, or "
                         "have an illness or infection? Answer yes or no, and tell me which."),
]
_GLUCOSE_LOW_QUESTIONS = [
    ("neuro", "yesno", "Are you confused, very drowsy, or having trouble speaking or staying awake? "
                       "Answer yes or no."),
    ("can_swallow", "yesno", "Can you swallow and eat or drink safely right now? Answer yes or no."),
    ("symptoms", "yesno", "Do you feel shaky, sweaty, hungry or have a pounding heartbeat? Answer yes or no."),
    ("context", "yesno", "Did you take insulin or diabetes tablets, skip or delay a meal, or exercise a lot? "
                         "Answer yes or no, and tell me which."),
]
_OLDER_EXTRA = {
    "bp_change": ("orthostatic", "yesno", "Do you feel dizzy or faint when you stand up? Answer yes or no."),
    "bp_low": ("falls", "yesno", "Have you fallen or nearly fallen today? Answer yes or no."),
}
_QUESTION_SETS = {
    "bp_severe": _BP_SEVERE_QUESTIONS,
    "bp_change": _BP_CHANGE_QUESTIONS,
    "bp_low": _BP_LOW_QUESTIONS,
    "glucose_high": _GLUCOSE_HIGH_QUESTIONS,
    "glucose_low": _GLUCOSE_LOW_QUESTIONS,
}

# What the patient took or did (matched in free text). Labels go to the clinician.
_FACTOR_PATTERNS = [
    ("cold or flu medicine", r"\b(?:cold|flu|decongestants?|pseudoephedrine|sudafed|cough syrup)\b"),
    ("painkiller (NSAID)", r"\b(?:ibuprofen|brufen|diclofenac|voltaren|naproxen|nsaids?|pain ?killers?)\b"),
    ("steroid", r"\b(?:steroids?|prednisolone|prednisone|dexamethasone|hydrocortisone)\b"),
    ("caffeine or stimulant", r"\b(?:energy drinks?|coffee|caffeine|chai|tea|red bull|stimulants?)\b"),
    ("nicotine", r"\b(?:cigarettes?|smok\w*|nicotine|naswar|vape)\b"),
    ("missed medicine", r"\b(?:missed|skipped|forgot|forgotten|ran out|did not take|didn'?t take)\b"),
    ("large meal", r"\b(?:large meal|big meal|heavy meal|dessert|sweets?|ate (?:a lot|too much))\b"),
    ("illness or infection", r"\b(?:ill|sick|infection|fever|vomit\w*|diarrh\w*)\b"),
    ("insulin or diabetes tablets", r"\b(?:insulin|metformin|glimepiride|gliclazide|tablets?|dose)\b"),
    ("skipped or delayed meal", r"\b(?:skipped (?:a )?meal|delayed (?:a )?meal|did not eat|didn'?t eat|no food|fasting)\b"),
    ("exercise or exertion", r"\b(?:exercis\w*|gym|walk\w*|run\w*|sport\w*|lifting|climb\w*)\b"),
    ("pain", r"\bpain\b"),
    ("stress or anxiety", r"\b(?:stress\w*|anxi\w*|upset|angry|worried|panic\w*)\b"),
]
_CANNOT = re.compile(r"\b(?:cannot|can'?t|unable|no cuff|don'?t have|do not have|not able)\b")
_CONTRADICTION = re.compile(r"\b(?:but|except|only|although)\b")


def _detect_factors(text: str) -> List[str]:
    lowered = _normalize(text)
    return [label for label, pattern in _FACTOR_PATTERNS if re.search(pattern, lowered)]


# -----------------------------------------------------------------------------
# State
# -----------------------------------------------------------------------------
@dataclass
class TriageProtocolState:
    protocol: str
    age_band: str
    readings: Dict[str, float] = field(default_factory=dict)
    trigger_reason: str = ""
    baseline: Optional[Dict[str, Any]] = None
    index: int = 0
    attempts: int = 0
    answers: Dict[str, Any] = field(default_factory=dict)
    factors: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None

    @property
    def complete(self) -> bool:
        return self.result is not None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriageProtocolState":
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown TriageProtocolState fields: {sorted(unknown)}")
        return cls(**copy.deepcopy(data))


def _questions(state: TriageProtocolState) -> List[tuple]:
    base = list(_QUESTION_SETS[state.protocol])
    if state.age_band == "older_65_plus" and state.protocol in _OLDER_EXTRA:
        base.append(_OLDER_EXTRA[state.protocol])
    return base


def start_protocol(trigger: Trigger, readings: Dict[str, float], age_years: Any,
                   baseline: Optional[Baseline] = None) -> TriageProtocolState:
    if trigger.protocol not in _QUESTION_SETS:
        raise ValueError(f"Unknown protocol '{trigger.protocol}'.")
    return TriageProtocolState(
        protocol=trigger.protocol,
        age_band=age_band(age_years),
        readings={k: float(v) for k, v in (readings or {}).items() if isinstance(v, (int, float))},
        trigger_reason=trigger.reason,
        baseline=baseline.to_dict() if baseline else None,
    )


def current_protocol_question(state: TriageProtocolState) -> Optional[str]:
    if state.complete:
        return None
    key, kind, text = _questions(state)[state.index]
    return ("Sorry, I didn't catch that. " + text) if state.attempts else text


def current_protocol_step(state: TriageProtocolState) -> Optional[str]:
    """The step string the client must echo back: triage:<protocol>:<index>:<attempts>."""
    if state.complete:
        return None
    return f"triage:{state.protocol}:{state.index}:{state.attempts}"


# -----------------------------------------------------------------------------
# Answers
# -----------------------------------------------------------------------------
def _yes_no(text: str, ask_for_detail: bool) -> Optional[bool]:
    lowered = _normalize(text)
    factors = _detect_factors(text) if ask_for_detail else []
    verdict = _looks_affirmative(text)
    if verdict is False and _CONTRADICTION.search(lowered):
        return None
    if verdict is False and factors and ask_for_detail:
        return True          # "no, only coffee" still names something
    if verdict is None and factors and ask_for_detail:
        return True
    return verdict


def advance_protocol(state: TriageProtocolState, answer: str) -> TriageProtocolState:
    """Consumes one answer and returns a NEW state (the input is untouched)."""
    state = copy.deepcopy(state)
    if state.complete:
        raise ValueError("Triage protocol already complete.")
    text = (answer or "").strip()
    if not text:
        return state

    flagged, category = run_stage1_red_flag_screen(text)
    if flagged:
        state.result = _result(state, TriageLevel.EMERGENCY.value,
                               [f"A warning symptom was reported ({category.replace('_', ' ')})."])
        return state

    key, kind, _ = _questions(state)[state.index]
    if kind == "bp":
        reading = _try_parse_bp(text)
        if reading is not None:
            state.answers[key] = {"systolic": reading[0], "diastolic": reading[1]}
        elif _CANNOT.search(_normalize(text)):
            state.answers[key] = {"cannot": True}
        elif state.attempts == 0:
            state.attempts = 1
            return state
        else:
            state.answers[key] = {"cannot": True, "unclear": True}
    else:
        detail_expected = key in ("substances", "medicines", "context", "circumstances")
        verdict = _yes_no(text, detail_expected)
        if verdict is None and state.attempts == 0:
            state.attempts = 1
            return state
        state.answers[key] = verdict          # True, False, or None (still unclear)
        for factor in _detect_factors(text):
            if factor not in state.factors and (verdict or key in ("substances", "medicines", "context")):
                state.factors.append(factor)
        if verdict and detail_expected and not _detect_factors(text) and "unspecified" not in state.factors:
            state.factors.append("something taken or done (not specified)")

    early = _early_emergency(state)
    if early is not None:               # someone who may be in danger is not asked further questions
        state.result = early
        return state
    state.index += 1
    state.attempts = 0
    if state.index >= len(_questions(state)):
        state.result = _decide(state)
    return state


# -----------------------------------------------------------------------------
# Decisions
# -----------------------------------------------------------------------------
def _result(state: TriageProtocolState, level: str, reasons: List[str]) -> Dict[str, Any]:
    readings = state.readings
    parts = []
    if SYSTOLIC in readings or DIASTOLIC in readings:
        parts.append(f"blood pressure {_fmt_bp(readings.get(SYSTOLIC), readings.get(DIASTOLIC))}")
    if GLUCOSE in readings:
        parts.append(f"glucose {readings[GLUCOSE]:g} mg/dL")
    recheck = state.answers.get("recheck")
    if isinstance(recheck, dict) and "systolic" in recheck:
        parts.append(f"after 5 minutes of rest {recheck['systolic']}/{recheck['diastolic']}")
    summary = f"{state.protocol.replace('_', ' ')}: " + "; ".join(parts + reasons)
    if state.factors:
        summary += f". Possible contributing factors: {', '.join(state.factors)}"
    return {
        "level": level,
        "protocol": state.protocol,
        "age_band": state.age_band,
        "reasons": reasons,
        "factors": list(state.factors),
        "readings": dict(readings),
        "recheck": recheck if isinstance(recheck, dict) else None,
        "guidance": GUIDANCE[level],
        "summary": summary,
    }


def _still_severe(reading: Dict[str, Any]) -> bool:
    return (reading["systolic"] >= DANGEROUS_BP_SYSTOLIC_MMHG
            or reading["diastolic"] >= DANGEROUS_BP_DIASTOLIC_MMHG)


def _early_emergency(state: TriageProtocolState) -> Optional[Dict[str, Any]]:
    """An emergency that the answers so far already settle; the remaining questions are skipped."""
    a = state.answers
    if state.protocol == "bp_severe" and a.get("symptoms") is True:
        return _result(state, "emergency", ["Blood pressure in the crisis range with warning symptoms."])
    if state.protocol == "glucose_high" and a.get("dka_symptoms") is True:
        return _result(state, "emergency", ["High glucose with warning symptoms."])
    if state.protocol == "glucose_low" and a.get("neuro") is True:
        return _result(state, "emergency", ["Low glucose with confusion or drowsiness."])
    if state.protocol == "glucose_low" and a.get("can_swallow") is False:
        return _result(state, "emergency", ["Low glucose and unable to eat or drink safely."])
    return None


def _decide(state: TriageProtocolState) -> Dict[str, Any]:
    return {
        "bp_severe": _decide_bp_severe, "bp_change": _decide_bp_change, "bp_low": _decide_bp_low,
        "glucose_high": _decide_glucose_high, "glucose_low": _decide_glucose_low,
    }[state.protocol](state)


def _decide_bp_severe(state: TriageProtocolState) -> Dict[str, Any]:
    a = state.answers
    symptoms, recheck = a.get("symptoms"), a.get("recheck") or {"cannot": True}
    if symptoms is True:
        return _result(state, "emergency", ["Blood pressure in the crisis range with warning symptoms."])
    level, reasons = "review", []
    if symptoms is None:
        level = _raise_level(level, "urgent")
        reasons.append("Warning symptoms could not be ruled out.")
    if "systolic" not in recheck:
        level = _raise_level(level, "urgent")
        reasons.append("The reading could not be confirmed with a second measurement.")
    elif _still_severe(recheck):
        level = _raise_level(level, "urgent")
        reasons.append("Blood pressure is still in the crisis range after 5 minutes of rest.")
    elif recheck["systolic"] >= BP_STAGE2_SYSTOLIC_MMHG or recheck["diastolic"] >= BP_STAGE2_DIASTOLIC_MMHG:
        reasons.append("Improved after rest but still high.")
    else:
        reasons.append("The first reading was in the crisis range but normal after rest.")
    if a.get("circumstances"):
        reasons.append("Pain, stress or activity before the first reading.")
    return _result(state, level, reasons)


def _decide_bp_change(state: TriageProtocolState) -> Dict[str, Any]:
    a = state.answers
    base = (state.baseline or {}).get("systolic")
    sys_v = state.readings.get(SYSTOLIC)
    rise = (sys_v - base) if (base is not None and sys_v is not None) else 0
    level, reasons = "review", [f"Systolic pressure is {rise:g} mmHg above your usual ({base:g})."] if base is not None else []
    if rise >= BP_CHANGE_MARKED_MMHG:
        level = _raise_level(level, "urgent")
        reasons.append("A large change from your usual.")
    if a.get("symptoms") is True:
        level = _raise_level(level, "urgent")
        reasons.append("Symptoms reported with the rise.")
    elif a.get("symptoms") is None:
        level = _raise_level(level, "urgent")
        reasons.append("Symptoms could not be ruled out.")
    if a.get("adherence") is False:
        reasons.append("Blood pressure medicine was not taken as prescribed.")
        if "missed medicine" not in state.factors:
            state.factors.append("missed medicine")
    if a.get("orthostatic"):
        level = _raise_level(level, "urgent")
        reasons.append("Dizziness on standing (age 65 and over).")
    return _result(state, level, reasons)


def _decide_bp_low(state: TriageProtocolState) -> Dict[str, Any]:
    a = state.answers
    level, reasons = "review", ["Blood pressure is low."]
    if a.get("symptoms") is True:
        level = _raise_level(level, "urgent")
        reasons.append("Symptoms reported with low blood pressure.")
    elif a.get("symptoms") is None:
        level = _raise_level(level, "urgent")
        reasons.append("Symptoms could not be ruled out.")
    if a.get("falls"):
        level = _raise_level(level, "urgent")
        reasons.append("A fall or near-fall today (age 65 and over).")
    return _result(state, level, reasons)


def _decide_glucose_high(state: TriageProtocolState) -> Dict[str, Any]:
    a = state.answers
    glucose = state.readings.get(GLUCOSE, 0)
    if a.get("dka_symptoms") is True:
        return _result(state, "emergency", ["High glucose with warning symptoms."])
    level, reasons = "review", ["Glucose is high."]
    if a.get("dka_symptoms") is None:
        level = _raise_level(level, "urgent")
        reasons.append("Warning symptoms could not be ruled out.")
    if glucose >= GLUCOSE_URGENT_MG_DL:
        level = _raise_level(level, "urgent")
        reasons.append(f"Glucose is {GLUCOSE_URGENT_MG_DL} mg/dL or more.")
    if a.get("thirst"):
        reasons.append("Marked thirst and frequent urination.")
    return _result(state, level, reasons)


def _decide_glucose_low(state: TriageProtocolState) -> Dict[str, Any]:
    a = state.answers
    glucose = state.readings.get(GLUCOSE, 0)
    if a.get("neuro") is True:
        return _result(state, "emergency", ["Low glucose with confusion or drowsiness."])
    if a.get("can_swallow") is False:
        return _result(state, "emergency", ["Low glucose and unable to eat or drink safely."])
    level, reasons = "review", ["Glucose is low."]
    if glucose < GLUCOSE_VERY_LOW_MG_DL:
        level = _raise_level(level, "urgent")
        reasons.append(f"Glucose is below {GLUCOSE_VERY_LOW_MG_DL} mg/dL.")
    if a.get("neuro") is None or a.get("can_swallow") is None:
        level = _raise_level(level, "urgent")
        reasons.append("Warning signs could not be ruled out.")
    if a.get("symptoms"):
        reasons.append("Symptoms of low glucose.")
    return _result(state, level, reasons)
