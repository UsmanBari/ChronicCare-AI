"""
backend-poc-technical/agents/final_triage.py — Stage-2 Final Triage & Escalation Agent

Combines deterministic clinical protocol rules, risk predictive models, and
longitudinal physiological trends to produce the authoritative final triage level,
color chip mapping, escalation tracking, and patient/provider reasoning.

Adheres strictly to the core safety motto:
"The model proposes, the rules decide."

=============================================================================
STAGE-2 FINAL TRIAGE RULES TABLE (Proposal Sections 13.1 Agent 10, 15, 17)
=============================================================================
Rule ID | Condition                                          | Result Level | Result Color | Raised? | Authority
--------|----------------------------------------------------|--------------|--------------|---------|-------------------------
R-S2-0  | rules_level in ('emergency', 'urgent', 'review')   | rules_level  | mapped color | False   | Invariant: Never lower
R-S2-1  | rules_level == 'routine' AND risk model 'high'     | review       | yellow       | True    | Doctor on record (Nov 2026)
        | AND qualifying symptom reported in check-in        |              |              |         | (Subject to cooldown)
        | AND RISK_CAN_RAISE=true                            |              |              |         |
R-S2-2  | rules_level == 'routine' AND trend rising with     | review       | yellow       | True    | Clinician Approved 8 Nov
        | >= 5 points (TREND_MIN_POINTS) AND latest value    |              |              |         | (5 check-in min)
        | above target range AND TREND_CAN_RAISE=true        |              |              |         |
R-S2-3  | Any raise                                          | review at    | yellow at    | True    | Invariant: At most 1 step
        |                                                    | most         | most         |         | (never to urgent/emerg)
R-S2-4  | rules_level == 'routine' AND no readings entered   | review       | yellow       | True    | Approved by the doctor on record
        | AND patient reported feeling unwell                |              |              |         | (Nov 2026)
        | AND NO_READING_SYMPTOM_RAISE=true                  |              |              |         |
=============================================================================
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Single source of truth for triage colors (Proposal Section 15)
LEVEL_TO_COLOUR_MAP = {
    "routine": "green",
    "review": "yellow",
    "urgent": "red",
    "emergency": "red",
}

# Trend escalation constant approved by doctor on 8 Nov 2026
# "5 check-ins / BP charting to be done before referring pt for review"
TREND_MIN_POINTS = 5

# Target physiological boundaries from existing rules (triage_protocol.py & interview_planner.py)
# Systolic target: BP_STAGE2_SYSTOLIC_MMHG = 140 (triage_protocol.py:72)
# Glucose target: 180 mg/dL (interview_planner.py:143 / ADA general target)
TARGET_THRESHOLDS = {
    "blood_pressure_systolic": 140.0,
    "systolic": 140.0,
    "glucose": 180.0,
}


def level_to_colour(level: str) -> str:
    """
    Maps clinical triage level to single source of truth color string.

    Parameters
    ----------
    level : str
        Clinical level ('routine', 'review', 'urgent', 'emergency')

    Returns
    -------
    str
        'green' for routine, 'yellow' for review, 'red' for urgent or emergency.

    Raises
    ------
    ValueError
        If the level is unknown (never guesses a color).
    """
    if not isinstance(level, str):
        raise ValueError(f"Unknown level: {level!r}")
    cleaned = level.strip().lower()
    if cleaned not in LEVEL_TO_COLOUR_MAP:
        raise ValueError(f"Unknown level: {level!r}")
    return LEVEL_TO_COLOUR_MAP[cleaned]


def check_unwell_symptoms(state: Any) -> bool:
    """
    Detects if the patient reported feeling unwell in free text or narrative answers.
    Reuses existing severity and danger patterns from interview_findings.py and danger_wordgroups.
    """
    from agents.interview_findings import SEVERITY_LEVEL_PATTERNS

    text_to_scan: List[str] = []

    # 1. State answers dict
    answers = getattr(state, "answers", None)
    if isinstance(answers, dict):
        for v in answers.values():
            if isinstance(v, str):
                text_to_scan.append(v)
            elif isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, str):
                        text_to_scan.append(sub_v)

    # 2. Intake symptom payloads
    intakes = getattr(state, "intakes", None) or []
    for it in intakes:
        if isinstance(it, dict):
            symp = it.get("symptoms")
            if isinstance(symp, dict):
                for val in symp.values():
                    if isinstance(val, str):
                        text_to_scan.append(val)
            free_text = it.get("patient_free_text") or it.get("narrative")
            if isinstance(free_text, str):
                text_to_scan.append(free_text)

    combined_text = " ".join(text_to_scan).lower()
    if not combined_text.strip():
        return False

    # Check for severe/moderate keywords from interview_findings.py
    for level, words in SEVERITY_LEVEL_PATTERNS:
        if level in ("severe", "moderate"):
            if any(w in combined_text for w in words):
                return True

    # Common unwell phrases
    unwell_phrases = [
        "not feeling well", "feeling unwell", "feeling bad", "very bad",
        "tabiyat theek nahi", "tabiyat kharab", "kharaab", "bura lag raha hai",
        "طبیعت خراب", "طبیعت ٹھیک نہیں", "بیمار"
    ]
    return any(p in combined_text for p in unwell_phrases)


def check_has_qualifying_symptoms(
    state: Optional[Any] = None,
    symptoms: Optional[Any] = None,
) -> bool:
    """
    Determines whether a check-in contains at least one reported symptom justifying
    a Stage-2 cardiovascular risk triage escalation from routine (Green) to review (Yellow).

    Clinical rationale (Decision D2, approved by the doctor on record, Nov 2026):
    "just having heart risk doesn't need a review unless associated with any symptoms"

    A check-in is considered symptomatic if ANY of the following hold:
    1. Explicit symptoms parameter passed:
       - Boolean True.
       - Non-empty collection (list/tuple/set/dict) containing at least one non-negative symptom.
       - A string representing a non-negative symptom.
    2. Danger wordgroup hits detected on state or in answers (_wordgroup_hits or wordgroup_hits).
    3. General unwell / sick-day presentation detected by check_unwell_symptoms(state).
    4. Structured findings on state (e.g. state.findings) representing positive clinical symptoms
       (excluding non-symptom findings such as missed_dose).
    5. Positive symptom answers in state.answers or intake dictionaries (e.g. associated_symptoms,
       hyperglycemia_symptoms, hypoglycemia_symptoms, sick_day_flags, foot_problems) where the patient
       did not reply with a negative answer (e.g. 'no', 'none', 'nothing', 'fine').
    6. Multilingual symptom keywords (dizziness, headache, breathlessness, chest discomfort,
       vision change, thirst/urination, foot problem, swelling, nausea/vomiting, fever, etc.)
       detected in patient text answers or narratives.
    """
    import re
    from agents.interview_findings import SYMPTOM_KEYWORD_RULES

    # Negative responses indicating absence of symptoms
    NEGATIVE_WORDS = {
        "no", "none", "nothing", "nil", "na", "n/a", "no symptoms", "no symptom",
        "feeling fine", "fine", "normal", "all good", "good", "okay", "ok",
        "i am fine", "im fine", "i am feeling fine", "im feeling fine",
        "feeling completely fine", "theek", "theek hun", "theek hoon", "bilkul theek",
        "nahi", "nhi", "kuch nahi", "kuch nhi", "koi nahi", "koi nhi",
        "koi masla nahi", "koi masla nhi", "koi takleef nahi", "tabiyat theek hai",
    }

    def _is_negative_text(text: str) -> bool:
        if not text:
            return True
        clean = re.sub(r"[^\w\s]", "", str(text).strip().lower())
        if clean in NEGATIVE_WORDS:
            return True
        if re.match(r"^no\s+(?:symptoms?|pain|headache|dizziness|chest|issues?|problems?)$", clean):
            return True
        if (clean.endswith("fine") or clean.endswith("normal") or clean.endswith("all good") or clean.endswith("theek")) and not any(
            bad in clean for bad in ("not", "nahi", "nhi", "dard", "pain", "sick", "bad", "unwell", "kharaab", "kharab")
        ):
            return True
        return False

    # 1. Direct symptoms argument check
    if symptoms is not None:
        if isinstance(symptoms, bool):
            if symptoms:
                return True
        elif isinstance(symptoms, (list, tuple, set)):
            for s in symptoms:
                if isinstance(s, str) and not _is_negative_text(s):
                    return True
                elif isinstance(s, dict) and any(v for v in s.values() if v and not _is_negative_text(str(v))):
                    return True
        elif isinstance(symptoms, dict):
            for k, v in symptoms.items():
                if isinstance(v, bool) and v:
                    return True
                elif isinstance(v, str) and not _is_negative_text(v):
                    return True
                elif isinstance(v, (int, float)) and v > 0:
                    return True
        elif isinstance(symptoms, str):
            if not _is_negative_text(symptoms):
                return True

    if state is None:
        return False

    # Direct string state (e.g. from dummy test mocks)
    if isinstance(state, str):
        return not _is_negative_text(state)

    # 2. Danger wordgroup hits
    wordgroups: List[Any] = []
    if hasattr(state, "wordgroup_hits") and state.wordgroup_hits:
        wordgroups.extend(state.wordgroup_hits)
    if hasattr(state, "answers") and isinstance(state.answers, dict):
        if state.answers.get("_wordgroup_hits"):
            wordgroups.extend(state.answers["_wordgroup_hits"])
    if isinstance(state, dict):
        if state.get("wordgroup_hits"):
            wordgroups.extend(state["wordgroup_hits"])
        if isinstance(state.get("answers"), dict) and state["answers"].get("_wordgroup_hits"):
            wordgroups.extend(state["answers"]["_wordgroup_hits"])

    intakes = getattr(state, "intakes", None) or (state.get("intakes") if isinstance(state, dict) else None) or []
    for it in intakes:
        if isinstance(it, dict) and it.get("wordgroup_hits"):
            wordgroups.extend(it["wordgroup_hits"])

    if wordgroups:
        return True

    # 3. General unwell / sick-day presentation (D1 check)
    if check_unwell_symptoms(state):
        return True

    # 4. Structured clinical findings
    findings = getattr(state, "findings", None) or (state.get("findings") if isinstance(state, dict) else None) or []
    for f in findings:
        kind = getattr(f, "kind", None) if hasattr(f, "kind") else (f.get("kind") if isinstance(f, dict) else None)
        if kind and kind != "missed_dose":
            return True

    # 5. Symptom slot answers
    SYMPTOM_SLOT_KEYS = {
        "associated_symptoms", "hyperglycemia_symptoms", "hypoglycemia_symptoms",
        "sick_day_flags", "foot_problems", "symptom", "symptoms"
    }

    answers_dict = getattr(state, "answers", None) or (state.get("answers") if isinstance(state, dict) else None) or {}
    if isinstance(answers_dict, dict):
        for k, v in answers_dict.items():
            if str(k).lower() in SYMPTOM_SLOT_KEYS:
                if isinstance(v, str) and not _is_negative_text(v):
                    return True
                elif isinstance(v, dict) and any(sub_v for sub_v in v.values() if sub_v and not _is_negative_text(str(sub_v))):
                    return True
                elif isinstance(v, (list, tuple, set)) and any(sub_v for sub_v in v if not _is_negative_text(str(sub_v))):
                    return True

    # 6. Keyword matching on free text / answers against SYMPTOM_KEYWORD_RULES
    text_to_scan: List[str] = []
    if isinstance(answers_dict, dict):
        for v in answers_dict.values():
            if isinstance(v, str):
                text_to_scan.append(v)
            elif isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, str):
                        text_to_scan.append(sub_v)

    for it in intakes:
        if isinstance(it, dict):
            symp = it.get("symptoms")
            if isinstance(symp, dict):
                for val in symp.values():
                    if isinstance(val, str):
                        text_to_scan.append(val)
            free_text = it.get("patient_free_text") or it.get("narrative")
            if isinstance(free_text, str):
                text_to_scan.append(free_text)

    combined_text = " ".join(text_to_scan).lower()
    if combined_text.strip():
        for kind, patterns in SYMPTOM_KEYWORD_RULES:
            if kind == "missed_dose":
                continue
            for pat in patterns:
                pat_pos = combined_text.find(pat)
                if pat_pos != -1:
                    prefix = combined_text[max(0, pat_pos - 15):pat_pos]
                    if not any(neg in prefix for neg in ("no ", "without ", "nahi ", "nhi ")):
                        return True

    return False


STAGE2_PATIENT_REASON_TEXTS = {
    "symptom_reported_needs_review": {
        "en": "You reported clinical symptoms, medication concerns, or distress that need clinician review.",
        "ur": "آپ نے ایسی علامات، دوائی سے متعلق سوال یا پریشانی بتائی ہے جس کا ڈاکٹر کی طرف سے جائزہ ضروری ہے۔",
        "roman_ur": "Aap ne aisi alamat, dawai ka masla ya pareshani batai hai jis ka doctor se review zaroori hai.",
    },
    "symptoms_without_readings": {
        "en": "You reported feeling unwell without vital readings available for comparison.",
        "ur": "آپ نے علامات کی اطلاع دی ہے لیکن موازنہ کے لیے کوئی پیمائش دستیاب نہیں ہے۔",
        "roman_ur": "Aap ne tabiyat kharab hone ki itteha di hai magar readings maujood nahi hain.",
    },
    "high_heart_risk_with_symptoms": {
        "en": "Elevated cardiovascular risk combined with reported symptoms requires care team review.",
        "ur": "دل کی بیماری کا زیادہ خطرہ اور علامات کی موجودگی دیکھ بھال کی ٹیم کے جائزے کا تقاضا کرتی ہے۔",
        "roman_ur": "Heart risk zyada hone aur sath alamat hone ki wajah se care team ka review zaroori hai.",
    },
    "trend_rising": {
        "en": "Rising vital readings across multiple check-ins have exceeded target levels.",
        "ur": "مسلسل کئی چیک اِنز میں ریڈنگز میں اضافہ ہدف کی سطح سے تجاوز کر گیا ہے۔",
        "roman_ur": "Musalsal check-ins mein readings target se zyada barh rahi hain.",
    },
}


def get_stage2_patient_reason_text(reason_key: str, lang: str = "en") -> str:
    """Returns patient-facing explanation text in English, Urdu, or Roman Urdu."""
    entry = STAGE2_PATIENT_REASON_TEXTS.get(reason_key) or {}
    clean_lang = (lang or "en").strip().lower()
    return entry.get(clean_lang) or entry.get("en") or reason_key


def check_has_symptom_finding_triggers(state: Any = None, symptoms: Optional[Any] = None) -> Tuple[bool, Optional[str]]:
    """
    Detects positive clinical symptom findings, dose change requests, or low mood/distress
    that warrant Stage-2 triage escalation from routine (Green) to review (Yellow).

    Doctor Decision D7 (approved by the doctor on record, Nov 2026):
    'agar upar wale symptoms aate hain to woh phir yellow mein jayega review mein'

    Triggers:
    1. Positive answer to foot_problems, hypo_events_past_week, sick_day_flags,
       associated_symptoms, or orthostatic dizziness.
    2. Patient asks to change/stop/adjust a medicine dose.
    3. Patient reports low mood or diabetes distress.
    """
    import re
    if state is None and symptoms is None:
        return False, None

    # Check direct structured findings first
    findings = []
    if state is not None:
        findings = getattr(state, "findings", None) or (state.get("findings") if isinstance(state, dict) else None) or []
    for f in findings:
        kind = getattr(f, "kind", None) if hasattr(f, "kind") else (f.get("kind") if isinstance(f, dict) else None)
        if kind in (
            "foot_problems", "foot_ulcer", "hypo_events_past_week", "sick_day_flags",
            "orthostatic_dizziness", "dizziness_standing",
            "dose_change", "low_mood", "distress"
        ):
            return True, f"Positive clinical finding: {kind}"

    # Helper to check if text answer is explicitly negative / denying symptoms
    def _is_negated_answer(text: str) -> bool:
        t = text.lower().strip()
        if re.search(r"\b(?:no|without|never|zero|free\s+of)\s+(?:\w+\s+){0,3}(?:cut|cuts|wound|wounds|sore|sores|blister|blisters|ulcer|ulcers|pain|dizziness|problem|problems|symptom|symptoms|masla|takleef|flag|flags)\b", t):
            return True
        if re.search(r"\b(?:feet|foot|haath|pair|legs|arms)\s+(?:are\s+|is\s+)?(?:okay|fine|ok|theek|good|normal|healthy)\b", t):
            return True
        if re.search(r"\b(?:koi|kuch)\s+(?:\w+\s+){0,2}(?:masla|takleef|zakhm|kharabi|symptom|alamat)\s+(?:nahi|nhi)\b", t):
            return True
        if re.match(r"^(?:no|none|nothing|nahi|nhi|kuch\s+nahi|koi\s+nahi|fine|normal|all\s+good|theek|ok|okay|no\s+symptoms?|no\s+associated\s+symptoms?)$", t):
            return True
        return False

    # Extract all answers / text from state and symptoms
    text_answers: List[str] = []

    # Check explicit symptoms parameter
    if symptoms is not None:
        if isinstance(symptoms, str):
            text_answers.append(symptoms)
        elif isinstance(symptoms, (list, tuple, set)):
            for sym in symptoms:
                if isinstance(sym, str):
                    text_answers.append(sym)
                elif isinstance(sym, dict):
                    for sk, sv in sym.items():
                        if isinstance(sv, str):
                            text_answers.append(sv)
        elif isinstance(symptoms, dict):
            for sk, sv in symptoms.items():
                sk_lower = str(sk).lower()
                if isinstance(sv, str):
                    text_answers.append(sv)
                    clean_sv = sv.strip().lower()
                    if clean_sv in ("no", "none", "nothing", "fine", "normal", "ok", "okay", "nahi", "nhi", "kuch nahi", "koi nahi", "unknown", "false", "no symptoms", "no symptom") or _is_negated_answer(clean_sv):
                        continue
                    if sk_lower in ("foot_problems", "foot_ulcer", "hypo_events_past_week", "sick_day_flags", "orthostatic_dizziness", "dizziness_standing"):
                        return True, f"Reported {sk_lower}: {sv}"
                elif isinstance(sv, (int, float)) and sv > 0:
                    if sk_lower in ("hypo_events_past_week", "sick_day_flags"):
                        return True, f"Reported {sk_lower}: {sv}"
                elif isinstance(sv, bool) and sv:
                    if sk_lower in ("sick_day_flags", "foot_problems", "orthostatic_dizziness"):
                        return True, f"Reported {sk_lower}: True"

    answers_dict = {}
    if state is not None:
        answers_dict = getattr(state, "answers", None) or (state.get("answers") if isinstance(state, dict) else None) or {}
    if isinstance(answers_dict, dict):
        for k, v in answers_dict.items():
            k_lower = str(k).lower()
            if isinstance(v, str):
                text_answers.append(v)
                clean_v = v.strip().lower()
                if clean_v in ("no", "none", "nothing", "fine", "normal", "ok", "okay", "nahi", "nhi", "kuch nahi", "koi nahi", "unknown", "false", "no symptoms", "no symptom") or _is_negated_answer(clean_v):
                    continue
                if k_lower in ("foot_problems", "foot_ulcer", "hypo_events_past_week", "sick_day_flags", "orthostatic_dizziness", "dizziness_standing"):
                    return True, f"Reported {k_lower}: {v}"
            elif isinstance(v, (int, float)) and v > 0:
                if k_lower in ("hypo_events_past_week", "sick_day_flags"):
                    return True, f"Reported {k_lower}: {v}"
            elif isinstance(v, bool) and v:
                if k_lower in ("sick_day_flags", "foot_problems", "orthostatic_dizziness"):
                    return True, f"Reported {k_lower}: True"
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, str):
                        text_answers.append(sub_v)
                        sub_clean = sub_v.strip().lower()
                        if sub_clean in ("no", "none", "nothing", "fine", "normal", "ok", "okay", "nahi", "nhi", "kuch nahi", "koi nahi", "unknown", "false", "no symptoms", "no symptom") or _is_negated_answer(sub_clean):
                            continue
                        if str(sub_k).lower() in ("foot_problems", "foot_ulcer", "hypo_events_past_week", "sick_day_flags", "orthostatic_dizziness"):
                            return True, f"Reported {sub_k}: {sub_v}"

    # Extract narrative / free text from intakes if present
    intakes = []
    if state is not None:
        intakes = getattr(state, "intakes", None) or (state.get("intakes") if isinstance(state, dict) else None) or []
    for it in intakes:
        if isinstance(it, dict):
            free_text = it.get("patient_free_text") or it.get("narrative")
            if isinstance(free_text, str):
                text_answers.append(free_text)
            symp = it.get("symptoms")
            if isinstance(symp, dict):
                for sk, sv in symp.items():
                    if isinstance(sv, str):
                        text_answers.append(sv)

    # Scan un-negated text answers for the qualifying triggers
    for a in text_answers:
        if not a or not isinstance(a, str):
            continue
        if _is_negated_answer(a):
            continue
        al = a.lower()

        # 1. Foot ulcer / wound / sore / blister
        if re.search(r"\b(?:blister|open\s+sore|ulcer|wound|bleeding|pus|infection)\b.*?\b(?:foot|toe|feet|sole|heel)\b|\b(?:foot|toe|feet|sole|heel)\b.*?\b(?:blister|open\s+sore|ulcer|wound|bleeding|pus|infection|cut)\b|پاؤں\s*(?:میں\s*)?(?:زخم|چھالا)", al):
            return True, f"Foot problem reported: {a}"

        # 2. Dose change / adjust / stop request
        if re.search(r"\b(?:should\s+i|can\s+i|want\s+to|discuss)\s+(?:\w+\s+){0,3}(?:increase|decrease|change|stop|adjust|switch)\s+(?:\w+\s+){0,3}(?:dose|medication|metformin|insulin|medicine|pill)\b|\b(?:increase|decrease|change|stop|adjust)\s+(?:my\s+)?(?:dose|dosage|medication)\b|خوراک\s*(?:بڑھ|کم|تبدیل)", al):
            return True, f"Medication dose change advice requested: {a}"

        # 3. Orthostatic dizziness (dizzy getting out of bed / standing up)
        if re.search(r"\b(?:dizzy|dizziness)\b.*?\b(?:get\s+out\s+of\s+bed|stand\s+up|standing|getting\s+up)\b|\b(?:standing\s+up|getting\s+up|out\s+of\s+bed)\b.*?\b(?:dizzy|dizziness|fall|falling)\b|کھڑے\s*ہونے\s*پر\s*چکر", al):
            return True, f"Orthostatic dizziness reported: {a}"

        # 4. Low mood / diabetes distress / depression
        if re.search(r"\b(?:low\s+mood|feeling\s+sad|feeling\s+down|overwhelmed|depressed|depression|counselor|no\s+energy|sadness|exhausted)\b|اداس|مایوس|پریشان", al):
            return True, f"Low mood or diabetes distress reported: {a}"

        # 5. Hypo events past week in free text
        if re.search(r"\b(?:hypo\w*|low\s+sugar|sugar\s+low|sugar\s+gir)\b.*?\b(?:past\s+week|this\s+week|pichle\s+hafte|last\s+week|twice|times?)\b", al):
            return True, f"Recent hypoglycemia events reported: {a}"

        # 6. Sick day flags in free text
        if re.search(r"\b(?:sick\s+day|fever|infection|high\s+temperature|bukhar)\b", al):
            return True, f"Sick day flags reported: {a}"

    return False, None


def decide_stage2(
    rules_level: str,
    risk_results: Optional[Any] = None,
    trends: Optional[Dict[str, Any]] = None,
    flags: Optional[Dict[str, Any]] = None,
    state: Optional[Any] = None,
    has_readings: bool = True,
    cooldown_active: bool = False,
    symptoms: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Stage-2 Final Triage Decision Engine.

    Parameters
    ----------
    rules_level : str
        Initial level determined by deterministic clinical rules ('routine', 'review', 'urgent', 'emergency').
    risk_results : dict or list of dict, optional
        Evaluated risk model output(s) from risk_agent.assess().
    trends : dict, optional
        Longitudinal trends computed by compute_trends().
    flags : dict, optional
        System configuration flags (RISK_CAN_RAISE, TREND_CAN_RAISE, NO_READING_SYMPTOM_RAISE, etc.).
    state : InterviewState, optional
        Check-in interview state.
    has_readings : bool
        Whether this check-in has valid BP or glucose readings.
    cooldown_active : bool
        Whether risk raise cooldown is active for this patient.
    symptoms : Any, optional
        Explicit symptoms reported in this check-in.

    Returns
    -------
    dict
        {
            "final_level": str,
            "triage_colour": str,
            "raised": bool,
            "raised_by": list of dict,
            "patient_reason_key": Optional[str],
            "triggered_rules": list of str,
        }
    """
    if flags is None:
        flags = {
            "RISK_ENABLED": os.environ.get("RISK_ENABLED", "").strip().lower() == "true",
            "RISK_CAN_RAISE": os.environ.get("RISK_CAN_RAISE", "").strip().lower() == "true",
            "TREND_CAN_RAISE": os.environ.get("TREND_CAN_RAISE", "").strip().lower() == "true",
            "NO_READING_SYMPTOM_RAISE": os.environ.get("NO_READING_SYMPTOM_RAISE", "").strip().lower() == "true",
            "SYMPTOM_FINDING_RAISE": os.environ.get("SYMPTOM_FINDING_RAISE", "true").strip().lower() in ("true", "1", "yes"),
        }

    # Normalize inputs
    norm_rules_level = str(rules_level).strip().lower()
    if norm_rules_level not in LEVEL_TO_COLOUR_MAP:
        raise ValueError(f"Invalid rules_level for Stage-2: {rules_level!r}")

    # R-S2-0: Invariant — Emergency, urgent, or review never lowered, emergency never touched
    if norm_rules_level in ("emergency", "urgent", "review"):
        return {
            "final_level": norm_rules_level,
            "triage_colour": level_to_colour(norm_rules_level),
            "raised": False,
            "raised_by": [],
            "patient_reason_key": None,
            "triggered_rules": ["R-S2-0"],
        }

    # At this point, norm_rules_level is strictly 'routine'
    raised = False
    raised_by: List[Dict[str, Any]] = []
    triggered_rules: List[str] = []
    patient_reason_key: Optional[str] = None

    # Check qualifying symptoms for symptom-linked Stage-2 escalation
    has_symptoms = check_has_qualifying_symptoms(state=state, symptoms=symptoms)

    # Normalise risk_results to a list
    model_list: List[Dict[str, Any]] = []
    if isinstance(risk_results, dict) and "models" in risk_results and isinstance(risk_results["models"], list):
        model_list = [m for m in risk_results["models"] if isinstance(m, dict)]
    elif isinstance(risk_results, list):
        model_list = [m for m in risk_results if isinstance(m, dict)]
    elif isinstance(risk_results, dict):
        model_list = [risk_results]

    # R-S2-1: Risk model raise (routine -> review)
    # Doctor Decision D2 (Nov 2026): "just having heart risk doesn't need a review unless associated with any symptoms"
    if flags.get("RISK_ENABLED", True) and flags.get("RISK_CAN_RAISE") and not cooldown_active:
        if has_symptoms:
            from agents.risk_rules import apply_risk_to_level
            orig_en = os.environ.get("RISK_ENABLED")
            orig_can = os.environ.get("RISK_CAN_RAISE")
            try:
                os.environ["RISK_ENABLED"] = "true"
                os.environ["RISK_CAN_RAISE"] = "true"
                for m_res in model_list:
                    if m_res.get("status") == "ok" and m_res.get("band") == "high":
                        _, can_raise = apply_risk_to_level("routine", m_res)
                        if can_raise:
                            raised = True
                            m_name = m_res.get("model_name") or m_res.get("disease") or "risk_model"
                            raised_by.append({
                                "source": "risk_model",
                                "model": m_name,
                                "band": "high",
                                "detail": f"High heart risk with symptoms ({m_name})",
                            })
                            triggered_rules.append("R-S2-1")
                            patient_reason_key = "high_heart_risk_with_symptoms"
                            # Do not break; record all high models
            finally:
                if orig_en is not None:
                    os.environ["RISK_ENABLED"] = orig_en
                else:
                    os.environ.pop("RISK_ENABLED", None)
                if orig_can is not None:
                    os.environ["RISK_CAN_RAISE"] = orig_can
                else:
                    os.environ.pop("RISK_CAN_RAISE", None)

    # R-S2-2: Trend raise (routine -> review)
    # Doctor's Answer 2: >= 5 points, rising, latest reading above target range
    if flags.get("TREND_CAN_RAISE") and trends and isinstance(trends, dict):
        trends_dict = trends.get("trends", {}) if "trends" in trends else trends
        for obs_key in ("blood_pressure_systolic", "glucose"):
            s_data = trends_dict.get(obs_key)
            if not isinstance(s_data, dict):
                continue

            direction = s_data.get("direction")
            n_points = s_data.get("n", 0)
            values = s_data.get("values") or []

            if direction == "rising" and n_points >= TREND_MIN_POINTS and values:
                # Get the latest reading value
                latest_point = values[-1]
                latest_val = latest_point.get("value") if isinstance(latest_point, dict) else latest_point
                target_thresh = TARGET_THRESHOLDS.get(obs_key, 140.0)

                try:
                    latest_val_float = float(latest_val)
                    if latest_val_float >= target_thresh:
                        raised = True
                        label = "systolic blood pressure" if "systolic" in obs_key else "blood glucose"
                        raised_by.append({
                            "source": "trend",
                            "observation_type": obs_key,
                            "direction": "rising",
                            "n": n_points,
                            "latest_value": latest_val_float,
                            "target_threshold": target_thresh,
                            "detail": f"Rising {label} trend ({n_points} readings, latest {latest_val_float} >= target {target_thresh})",
                        })
                        triggered_rules.append("R-S2-2")
                        patient_reason_key = "trend_rising"
                except (ValueError, TypeError):
                    pass

    # R-S2-4: No readings with ambiguous symptom picture (routine -> review)
    # Proposal Section 15 yellow row. Approved by the doctor on record (Nov 2026).
    if flags.get("NO_READING_SYMPTOM_RAISE") and not has_readings and state:
        if check_unwell_symptoms(state):
            raised = True
            raised_by.append({
                "source": "symptoms_no_readings",
                "detail": "Patient reported feeling unwell without objective vital readings available",
            })
            triggered_rules.append("R-S2-4")
            patient_reason_key = "symptoms_without_readings"

    # R-S2-5: Symptom finding raise (routine -> review)
    # Doctor Decision D7 (approved by the doctor on record, Nov 2026):
    # 'agar upar wale symptoms aate hain to woh phir yellow mein jayega review mein'
    # Triggers: foot problems, hypo events past week, sick day flags, associated symptoms,
    # orthostatic dizziness, dose change requests, low mood/distress.
    symptom_finding_enabled = flags.get("SYMPTOM_FINDING_RAISE")
    if symptom_finding_enabled is None:
        symptom_finding_enabled = os.environ.get("SYMPTOM_FINDING_RAISE", "true").strip().lower() in ("true", "1", "yes")

    if symptom_finding_enabled and (state is not None or symptoms is not None):
        has_finding, finding_detail = check_has_symptom_finding_triggers(state=state, symptoms=symptoms)
        if has_finding:
            raised = True
            raised_by.append({
                "source": "symptom_finding",
                "detail": finding_detail or "Patient reported clinical symptom, medication concern, or distress needing review",
            })
            triggered_rules.append("R-S2-5")
            if not patient_reason_key:
                patient_reason_key = "symptom_reported_needs_review"

    # R-S2-3: Invariant — At most one step escalation (routine -> review)
    final_level = "review" if raised else "routine"

    return {
        "final_level": final_level,
        "triage_colour": level_to_colour(final_level),
        "raised": raised,
        "raised_by": raised_by,
        "patient_reason_key": patient_reason_key,
        "triggered_rules": triggered_rules if triggered_rules else ["ROUTINE_UNCHANGED"],
    }

