"""
Interview Engine v3 Runner (Stage 9A-2).

Connects the modular Question Bank, Findings Extractor, Adaptive Planner,
Answer Validation, and Deterministic Input Triage into the check-in lifecycle.

Controlled by server flag: INTERVIEW_ENGINE (values: 'v2' default, 'v3').
Deterministic: The Model Proposes, The Rules Decide.
"""

from __future__ import annotations

import os
import copy
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from agents.interview_bank.loader import BankItem, get_default_bank, get_message
from agents.interview_findings import (
    Finding,
    extract_findings_from_answer,
    get_next_probe_for_finding,
)
from agents.interview_planner import (
    PlanDecision,
    detect_historical_trends,
    plan_next_step,
)
from agents.answer_understanding import (
    parse_yes_no,
    parse_number,
    parse_bp,
)
from agents.answer_validation import (
    ValidationResult,
    check_contradiction,
    validate_bp_input,
    validate_glucose_input,
)
from agents.input_triage import (
    TriageInputResult,
    classify_input,
)

logger = logging.getLogger(__name__)


CANONICAL_STRIKE_OPTIONS = ["Continue check-in", "Need urgent help", "Finish later"]
CANONICAL_SUMMARY_CORRECTION_OPTIONS = ["Blood Glucose", "Blood Pressure", "Symptoms", "Medication Adherence"]

def is_v3_engine_enabled() -> bool:
    """Checks if Interview Engine v3 is enabled via environment variable."""
    return os.environ.get("INTERVIEW_ENGINE", "v2").strip().lower() == "v3"


# =============================================================================
# Helper Functions
# =============================================================================
def _get_localized_why_text(item: Any, lang: str = "en") -> str:
    """Retrieves localized why-text/rationale for a bank item or probe."""
    if isinstance(item, BankItem):
        if lang == "ur":
            return item.why_text_ur or item.why_text
        if lang == "roman_ur":
            return item.why_text_roman_ur or item.why_text
        return item.why_text
    if isinstance(item, dict):
        if lang == "ur":
            return item.get("why_text_ur") or item.get("clinical_rationale_ur") or item.get("clinical_rationale") or item.get("why_text") or ""
        if lang == "roman_ur":
            return item.get("why_text_roman_ur") or item.get("clinical_rationale_roman_ur") or item.get("clinical_rationale") or item.get("why_text") or ""
        return item.get("clinical_rationale") or item.get("why_text") or ""
    return ""


def _build_option_items(item: Any, lang: str = "en") -> Optional[List[Dict[str, str]]]:
    """Constructs additive localized option_items with canonical value and localized label."""
    if isinstance(item, BankItem):
        if not item.choices:
            return None
        canonical = item.choices
        if lang == "ur" and item.choices_ur and len(item.choices_ur) == len(canonical):
            labels = item.choices_ur
        elif lang == "roman_ur" and item.choices_roman_ur and len(item.choices_roman_ur) == len(canonical):
            labels = item.choices_roman_ur
        else:
            labels = canonical
        return [{"value": str(c), "label": str(lbl)} for c, lbl in zip(canonical, labels)]
    if isinstance(item, dict):
        choices = item.get("choices")
        if not choices or not isinstance(choices, list):
            return None
        if lang == "ur" and item.get("choices_ur") and len(item.get("choices_ur")) == len(choices):
            labels = item.get("choices_ur")
        elif lang == "roman_ur" and item.get("choices_roman_ur") and len(item.get("choices_roman_ur")) == len(choices):
            labels = item.get("choices_roman_ur")
        else:
            labels = choices
        return [{"value": str(c), "label": str(lbl)} for c, lbl in zip(choices, labels)]
    return None


def _get_localized_text(item: Any, lang: str = "en") -> str:
    """Retrieves localized text for a bank item or response dictionary."""
    if isinstance(item, BankItem):
        if lang == "ur":
            return item.template_ur or item.template_en
        if lang == "roman_ur":
            return item.template_roman_ur or item.template_en
        return item.template_en
    if isinstance(item, dict):
        if lang == "ur":
            return item.get("template_ur") or item.get("reply_ur") or item.get("template_en") or item.get("reply_en") or ""
        if lang == "roman_ur":
            return item.get("template_roman_ur") or item.get("reply_roman_ur") or item.get("template_en") or item.get("reply_en") or ""
        return item.get("template_en") or item.get("reply_en") or item.get("text") or ""
    return str(item) if item else ""


def _build_dual_summary_text(known_slots: Dict[str, Any], lang: str, asked_slots: Optional[List[str]] = None) -> str:
    """
    R8: Constructs a structured summary listing captured readings and values
    for both diabetes and hypertension in the session language.
    """
    if asked_slots is None:
        asked_slots = []
    """
    R8: Constructs a structured summary listing captured readings and values
    for both diabetes and hypertension in the session language.
    """
    # 1. Glucose
    gluc = known_slots.get("glucose_reading")
    if gluc is not None:
        ctx = known_slots.get("glucose_context", "")
        ctx_str = f" ({ctx})" if ctx else ""
        gluc_en = f"Blood Glucose: {gluc:g} mg/dL{ctx_str}"
        gluc_ur = f"شوگر: {gluc:g} mg/dL{ctx_str}"
        gluc_ro = f"Sugar: {gluc:g} mg/dL{ctx_str}"
    else:
        gluc_en = "Blood Glucose: Not provided"
        gluc_ur = "شوگر: درج نہیں کی گئی"
        gluc_ro = "Sugar: Darj nahi ki gayi"

    # 2. Blood Pressure
    bp = known_slots.get("bp_reading")
    if bp and isinstance(bp, (list, tuple)) and len(bp) >= 2:
        bp_en = f"Blood Pressure: {bp[0]}/{bp[1]} mmHg"
        bp_ur = f"بلڈ پریشر: {bp[0]}/{bp[1]} mmHg"
        bp_ro = f"Blood Pressure: {bp[0]}/{bp[1]} mmHg"
    else:
        bp_en = "Blood Pressure: Not provided"
        bp_ur = "بلڈ پریشر: درج نہیں کیا گیا"
        bp_ro = "Blood Pressure: Darj nahi kiya gaya"

    # 3. Symptoms
    symptoms = []
    if known_slots.get("hyperglycemia_symptoms") is True or known_slots.get("associated_symptoms") is True:
        symptoms.append("reported symptoms")
    if known_slots.get("foot_problems") is True:
        symptoms.append("foot numbness or sores")

    symptoms_asked = any(
        k in known_slots for k in ("hyperglycemia_symptoms", "associated_symptoms", "foot_problems")
    ) or any(
        s in asked_slots for s in ("hyperglycemia_symptoms", "associated_symptoms", "foot_problems")
    )

    if symptoms:
        symp_en = f"Symptoms: {', '.join(symptoms)}"
        symp_ur = "علامات: علامات کی اطلاع دی گئی"
        symp_ro = "Alamaat: Alamaat report ki gayi hain"
    elif symptoms_asked:
        symp_en = "Symptoms: None reported"
        symp_ur = "علامات: کوئی نہیں"
        symp_ro = "Alamaat: Koi nahi"
    else:
        symp_en = "Symptoms: not asked"
        symp_ur = "علامات: پوچھی نہیں گئیں"
        symp_ro = "Symptoms: nahi poochay gaye"

    # 4. Adherence
    adh = known_slots.get("adherence_diabetes")
    if adh is None:
        adh = known_slots.get("adherence_hypertension")
    if adh is True:
        adh_en = "Medication: Taken as prescribed"
        adh_ur = "ادویات: باقاعدگی سے لیں"
        adh_ro = "Dawai: Time par li"
    elif adh is False:
        adh_en = "Medication: Missed doses reported"
        adh_ur = "ادویات: خوراک چھوٹنے کی اطلاع"
        adh_ro = "Dawai: Dose miss hone ki ittila"
    else:
        adh_en = "Medication: Not recorded"
        adh_ur = "ادویات: درج نہیں"
        adh_ro = "Dawai: Record nahi hui"

    if lang == "ur":
        return f"ہم نے آج یہ معلومات درج کی ہیں:\n- {gluc_ur}\n- {bp_ur}\n- {symp_ur}\n- {adh_ur}\nکیا سب کچھ ٹھیک ہے؟"
    if lang == "roman_ur":
        return f"Hum ne aaj yeh record kiya hai:\n- {gluc_ro}\n- {bp_ro}\n- {symp_ro}\n- {adh_ro}\nKya sab theek hai?"
    return f"Here is what we recorded today:\n- {gluc_en}\n- {bp_en}\n- {symp_en}\n- {adh_en}\nDoes everything look right to you?"


def start_v3_session(
    checkin_id: str,
    patient_id: str,
    conditions: List[str],
    on_insulin_or_sulfonylurea: bool = False,
    is_cold_start: bool = False,
    baseline: Optional[Dict[str, Any]] = None,
    language: str = "en",
    answered_by: str = "patient",
) -> Dict[str, Any]:
    """
    Initializes a new v3 check-in session using the Question Bank and Adaptive Planner.
    """
    bank = get_default_bank()
    patient_conditions = [c.lower() for c in conditions]
    lang = language if language in ("en", "ur", "roman_ur") else "en"

    patient_record = {
        "patient_id": patient_id,
        "conditions": patient_conditions,
        "on_insulin_or_sulfonylurea": on_insulin_or_sulfonylurea,
        "is_cold_start": is_cold_start,
        "baseline": baseline or {},
    }

    known_slots: Dict[str, Any] = {}
    asked_slots: List[str] = []
    findings: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []
    recent_checkins = baseline.get("recent_history", []) if baseline else []

    # Get first question from planner
    decision: PlanDecision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient_record,
        recent_checkins=recent_checkins,
        bank=bank,
        asked_slots=set(asked_slots),
        contradictions=contradictions,
        base_budget=8,
        hard_cap=14,
    )

    question_text = ""
    why_text = ""
    options = None
    can_skip = True
    can_say_unknown = True
    step_id = "greeting"

    option_items = None
    if decision.item:
        step_id = decision.item.slot
        question_text = _get_localized_text(decision.item, lang)
        why_text = _get_localized_why_text(decision.item, lang)
        options = decision.item.choices
        option_items = _build_option_items(decision.item, lang)
        can_skip = (decision.item.priority_class != "safety")
        can_say_unknown = True
    elif decision.probe:
        step_id = decision.probe.get("slot", "probe")
        question_text = _get_localized_text(decision.probe, lang)
        why_text = _get_localized_why_text(decision.probe, lang)
        options = decision.probe.get("choices")
        option_items = _build_option_items(decision.probe, lang)
        can_skip = True
        can_say_unknown = True

    session_state = {
        "engine": "v3",
        "checkin_id": checkin_id,
        "patient_id": patient_id,
        "conditions_on_file": patient_conditions,
        "language": lang,
        "step": step_id,
        "current_question": question_text,
        "why_text": why_text,
        "options": options,
        "option_items": option_items,
        "can_skip": can_skip,
        "can_say_unknown": can_say_unknown,
        "system_note": None,
        "progress_hint": f"{decision.question_count}/{decision.max_budget}",
        "consecutive_odd_count": 0,
        "patient_record": patient_record,
        "known_slots": known_slots,
        "asked_slots": asked_slots,
        "findings": findings,
        "contradictions": contradictions,
        "recent_checkins": recent_checkins,
        "readings": {},
        "raw_answers": {},
        "patient_questions": [],
        "possible_severe_low": False,
        "possible_severe_low_guidance": None,
        "awaiting_glucose_unit": False,
        "raw_unclarified_glucose": None,
        "completed": False,
        "emergency": False,
        "emergency_reason": None,
        "urgent_safety": False,
        "needs_clinician_flag": False,
        "ended_early_off_topic": False,
        "current_decision_target": decision.target_slot,
        "answered_by": answered_by,
        "summary_correction_rounds": 0,
        "awaiting_correction_slot": False,
        "patient_notes": [],
    }

    return session_state


def next_turn(session_state: Dict[str, Any], answer_text: str) -> Dict[str, Any]:
    """
    Processes a patient turn in Interview Engine v3:
    1. Deterministic Input Triage & Red-Flag Screen FIRST
    2. Answer validation & range parsing
    3. Clinical findings extraction & probe management
    4. Adaptive Planner scoring for next question
    """
    bank = get_default_bank()
    lang = session_state.get("language", "en")
    clean_answer = (answer_text or "").strip()
    current_slot = session_state.get("step", "greeting")

    # =========================================================================
    # 1. INPUT TRIAGE & RED-FLAG SCREEN FIRST (Authoritative Deterministic Safety)
    # =========================================================================
    triage_res: TriageInputResult = classify_input(
        clean_answer,
        consecutive_odd_count=session_state.get("consecutive_odd_count", 0),
    )

    if triage_res.is_emergency:
        session_state["emergency"] = True
        session_state["emergency_reason"] = triage_res.trigger_detail or "danger_phrase"
        session_state["completed"] = True
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
        session_state["system_note"] = get_message("emergency_red_flag_note", lang)
        return session_state

    if triage_res.is_urgent_safety:
        resp_key = triage_res.response_key or "self_harm"
        reply_dict = bank.get_responses().get(resp_key, {})
        system_note = _get_localized_text(reply_dict, lang)
        session_state["urgent_safety"] = True
        session_state["needs_clinician_flag"] = True
        session_state["emergency"] = True
        session_state["emergency_reason"] = "self_harm_statement"
        session_state["completed"] = True
        session_state["system_note"] = system_note
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
        return session_state

    if triage_res.category == "odd_input":
        odd_count = session_state.get("consecutive_odd_count", 0) + 1
        session_state["consecutive_odd_count"] = odd_count
        session_state.setdefault("odd_classes_seen", []).append(triage_res.odd_class)
        session_state["last_odd_class"] = triage_res.odd_class

        if triage_res.odd_class == "third_party_report":
            session_state["answered_by"] = "caregiver"
            session_state.setdefault("known_slots", {})["answered_by"] = "caregiver"

        resp_key = triage_res.response_key or triage_res.odd_class or "chitchat_joke"
        reply_dict = bank.get_responses().get(resp_key, {})
        system_note = _get_localized_text(reply_dict, lang)

        if triage_res.needs_clinician_flag:
            session_state["needs_clinician_flag"] = True
            session_state["patient_questions"].append({
                "category": triage_res.odd_class,
                "text": clean_answer,
            })

        # Strike rule: 4 consecutive off-topic answers -> finish politely without lowering triage
        if odd_count >= 4:
            session_state["ended_early_off_topic"] = True
            session_state["completed"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            session_state["system_note"] = get_message("strike_rule_offtopic_done", lang)
            return session_state

        # Strike rule: 2 consecutive off-topic answers -> offer choices
        if odd_count >= 2:
            session_state["system_note"] = system_note
            session_state["options"] = list(CANONICAL_STRIKE_OPTIONS)
            session_state["option_items"] = [
                {"value": "Continue check-in", "label": get_message("strike_rule_option_continue", lang)},
                {"value": "Need urgent help", "label": get_message("strike_rule_option_urgent", lang)},
                {"value": "Finish later", "label": get_message("strike_rule_option_finish_later", lang)},
            ]
            return session_state

        session_state["system_note"] = system_note
        return session_state

    # Valid / substantive answer received -> reset odd input counter & system note
    session_state["consecutive_odd_count"] = 0
    session_state["system_note"] = None
    session_state["last_odd_class"] = None

    # =========================================================================
    # 2. GLUCOSE UNIT SAFETY & CLINICAL ANSWER VALIDATION
    # =========================================================================
    known_slots = session_state.get("known_slots", {})
    raw_answers = session_state.get("raw_answers", {})
    readings = session_state.get("readings", {})
    asked_slots = session_state.get("asked_slots", [])

    # Check if we were awaiting glucose unit clarification
    if session_state.get("awaiting_glucose_unit"):
        unclarified_val = session_state.get("raw_unclarified_glucose")
        session_state["awaiting_glucose_unit"] = False
        session_state["raw_unclarified_glucose"] = None

        ans_lower = clean_answer.lower()
        if "mmol" in ans_lower:
            # Patient confirmed mmol/L -> convert to mg/dL
            mg_dl_val = round(float(unclarified_val) * 18.0, 1)
            readings["glucose"] = mg_dl_val
            known_slots["glucose_reading"] = mg_dl_val
            if mg_dl_val < 70:
                session_state["possible_severe_low"] = True
        elif "mg" in ans_lower or "dl" in ans_lower:
            # Patient confirmed mg/dL (severe hypoglycemia <= 54)
            readings["glucose"] = float(unclarified_val)
            known_slots["glucose_reading"] = float(unclarified_val)
            session_state["possible_severe_low"] = True
            session_state["possible_severe_low_guidance"] = get_message("glucose_low_safety_guidance", lang)
        else:
            # Unanswered / unclear unit: Treat as possible severe low per clinical rule
            readings["glucose"] = float(unclarified_val)
            known_slots["glucose_reading"] = float(unclarified_val)
            session_state["possible_severe_low"] = True
            session_state["possible_severe_low_guidance"] = get_message("glucose_low_safety_guidance", lang)
            session_state["needs_clinician_flag"] = True

    elif "glucose_reading" in current_slot or current_slot == "diabetes_glucose_reading":
        p_num = parse_number(clean_answer)
        cleaned_for_val = clean_answer
        if p_num["value"] is not None and p_num["kind"] == "words":
            import re as _re
            unit_match = _re.search(r"\b(mmol/l|mmol|mg/dl|mgdl|mg)\b", clean_answer.lower())
            if unit_match:
                cleaned_for_val = f"{p_num['value']:g} {unit_match.group(1)}"
            else:
                cleaned_for_val = f"{p_num['value']:g}"
        val_res: ValidationResult = validate_glucose_input(cleaned_for_val)
        if val_res.needs_unit_clarification:
            session_state["awaiting_glucose_unit"] = True
            session_state["raw_unclarified_glucose"] = val_res.value
            session_state["current_question"] = get_message("unit_clarification_question", lang, value=f"{val_res.value:g}")
            session_state["why_text"] = get_message("unit_clarification_why", lang)
            session_state["options"] = ["mmol/L", "mg/dL"]
            session_state["option_items"] = [
                {"value": "mmol/L", "label": "mmol/L"},
                {"value": "mg/dL", "label": "mg/dL"},
            ]
            return session_state
        elif val_res.valid and val_res.value is not None:
            clean_low = clean_answer.lower()
            has_unit = any(u in clean_low for u in ["mg", "dl", "mmol"])
            if not has_unit and 41.0 <= float(val_res.value) <= 54.0:
                session_state["awaiting_glucose_unit"] = True
                session_state["raw_unclarified_glucose"] = val_res.value
                session_state["current_question"] = get_message("unit_clarification_question", lang, value=f"{val_res.value:g}")
                session_state["why_text"] = get_message("unit_clarification_why", lang)
                session_state["options"] = ["mmol/L", "mg/dL"]
                session_state["option_items"] = [
                    {"value": "mmol/L", "label": "mmol/L"},
                    {"value": "mg/dL", "label": "mg/dL"},
                ]
                return session_state

            if val_res.unit == "mmol/L":
                glucose_val = round(float(val_res.value) * 18.0, 1)
            else:
                glucose_val = float(val_res.value)

            readings["glucose"] = glucose_val
            known_slots["glucose_reading"] = glucose_val
            if val_res.is_possible_severe_low:
                session_state["possible_severe_low"] = True
                session_state["possible_severe_low_guidance"] = val_res.safety_guidance
                session_state["needs_clinician_flag"] = True
        else:
            known_slots["missing_reading"] = True

    elif "bp_reading" in current_slot or current_slot == "hypertension_bp_reading":
        p_bp = parse_bp(clean_answer)
        cleaned_for_bp = clean_answer
        if p_bp["value"] is not None:
            cleaned_for_bp = f"{p_bp['value'][0]}/{p_bp['value'][1]}"
        bp_res: ValidationResult = validate_bp_input(cleaned_for_bp)
        if bp_res.valid and bp_res.value is not None:
            readings["blood_pressure_systolic"] = bp_res.value[0]
            readings["blood_pressure_diastolic"] = bp_res.value[1]
            known_slots["bp_reading"] = bp_res.value
            known_slots["bp_reading__evidence"] = p_bp.get("evidence", clean_answer)
        else:
            known_slots["missing_reading"] = True

    # Yes/No bank items & probes handling (B1 & B3)
    bank_item = bank.get_by_slot(current_slot) or bank.get_by_id(current_slot)
    is_yes_no = False
    if bank_item and bank_item.answer_type == "yes_no":
        is_yes_no = True
    elif session_state.get("is_probe") and session_state.get("options") in (["yes", "no"], ["haan", "nahi"], ["ہاں", "نہیں"]):
        is_yes_no = True

    if is_yes_no:
        yn_res = parse_yes_no(clean_answer, lang=lang)
        # B3: Safety-class item answered unknown -> re-ask ONCE with clarification
        if bank_item and bank_item.priority_class == "safety" and yn_res["value"] == "unknown":
            if session_state.get("safety_clarify_slot") == current_slot:
                # Second time unknown -> keep unknown, set needs_clinician_flag, move on
                session_state["safety_clarify_slot"] = None
                known_slots[current_slot] = "unknown"
                known_slots[f"{current_slot}__evidence"] = yn_res["evidence"]
                known_slots[f"{current_slot}__partial"] = yn_res["partial"]
                session_state["needs_clinician_flag"] = True
            else:
                # First time unknown -> re-ask ONCE
                session_state["safety_clarify_slot"] = current_slot
                resp_dict = bank.get_responses().get("safety_unknown_clarify", {})
                clarify_text = _get_localized_text(resp_dict, lang)
                session_state["current_question"] = clarify_text
                session_state["why_text"] = _get_localized_why_text(bank_item, lang)
                session_state["options"] = ["yes", "no", "unknown"]
                session_state["option_items"] = _build_option_items(bank_item, lang) or [
                    {"value": "yes", "label": "ہاں" if lang == "ur" else ("haan" if lang == "roman_ur" else "yes")},
                    {"value": "no", "label": "نہیں" if lang == "ur" else ("nahi" if lang == "roman_ur" else "no")},
                    {"value": "unknown", "label": "معلوم نہیں" if lang == "ur" else ("maloom nahi" if lang == "roman_ur" else "unknown")},
                ]
                session_state["can_skip"] = False
                session_state["can_say_unknown"] = True
                return session_state
        else:
            if session_state.get("safety_clarify_slot") == current_slot:
                session_state["safety_clarify_slot"] = None
            if yn_res["value"] == "yes":
                known_slots[current_slot] = True
            elif yn_res["value"] == "no":
                known_slots[current_slot] = False
            else:
                # Slot-specific symptom affirmations (e.g. sick day vomiting/diarrhea or fasting)
                lower_ans = clean_answer.lower()
                if current_slot == "sick_vomiting_diarrhea" and any(k in lower_ans for k in ["ulti", "dast", "vomit", "diarrhea"]):
                    known_slots[current_slot] = True
                    yn_res["evidence"] = clean_answer
                elif current_slot == "is_fasting_today" and any(k in lower_ans for k in ["roza", "fasting"]):
                    known_slots[current_slot] = True
                    yn_res["evidence"] = clean_answer
                else:
                    known_slots[current_slot] = "unknown"
            known_slots[f"{current_slot}__evidence"] = yn_res["evidence"]
            known_slots[f"{current_slot}__partial"] = yn_res["partial"]

            # R3: Propagate answers to shared slots via also_fills
            if bank_item and bank_item.also_fills:
                for extra_s in bank_item.also_fills:
                    known_slots[extra_s] = known_slots[current_slot]
                    known_slots[f"{extra_s}__evidence"] = yn_res["evidence"]
                    known_slots[f"{extra_s}__partial"] = yn_res["partial"]

    # Record slot answer
    raw_answers[current_slot] = clean_answer
    if bank_item and bank_item.also_fills:
        for extra_s in bank_item.also_fills:
            raw_answers[extra_s] = clean_answer
    if current_slot not in asked_slots:
        asked_slots.append(current_slot)

    # =========================================================================
    # 3. CLINICAL FINDINGS EXTRACTION
    # =========================================================================
    extracted_findings = extract_findings_from_answer(clean_answer)
    current_findings = [Finding(**f) if isinstance(f, dict) else f for f in session_state.get("findings", [])]
    existing_kinds = {f.kind for f in current_findings}

    for f in extracted_findings:
        if f.kind not in existing_kinds:
            current_findings.append(f)
            existing_kinds.add(f.kind)

    session_state["findings"] = [asdict(f) for f in current_findings]

    # R8: Summary Confirmation & Correction Loop
    if current_slot == "summary_confirmation":
        yn_res = parse_yes_no(clean_answer, lang=lang)
        lower_raw = clean_answer.lower()
        is_change_intent = (
            yn_res["value"] is False
            or any(w in lower_raw for w in ["change", "tabdeel", "galat", "wrong", "need to change", "nahi", "no", "edit"])
        )
        if is_change_intent:
            rounds = session_state.get("summary_correction_rounds", 0)
            if rounds < 2:
                session_state["summary_correction_rounds"] = rounds + 1
                session_state["awaiting_correction_slot"] = True
                session_state["step"] = "summary_correction_select"
                session_state["current_question"] = get_message("summary_correction_prompt", lang)
                session_state["why_text"] = get_message("summary_confirm_why", lang)
                session_state["options"] = list(CANONICAL_SUMMARY_CORRECTION_OPTIONS)
                session_state["option_items"] = [
                    {"value": "Blood Glucose", "label": get_message("summary_correction_option_glucose", lang)},
                    {"value": "Blood Pressure", "label": get_message("summary_correction_option_bp", lang)},
                    {"value": "Symptoms", "label": get_message("summary_correction_option_symptoms", lang)},
                    {"value": "Medication Adherence", "label": get_message("summary_correction_option_meds", lang)},
                ]
                return session_state
            else:
                session_state["needs_clinician_flag"] = True
                session_state.setdefault("patient_notes", []).append("Patient requested corrections beyond maximum rounds (2). Submitting with clinician review flag.")
                session_state["completed"] = True
                session_state["complete"] = True
                session_state["step"] = "COMPLETE"
                session_state["current_question"] = None
                return session_state
        else:
            session_state["completed"] = True
            session_state["complete"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            return session_state

    # Handling slot selection during summary correction
    if session_state.get("awaiting_correction_slot"):
        session_state["awaiting_correction_slot"] = False
        lower_ans = clean_answer.lower()
        if any(k in lower_ans for k in ["blood pressure", "bp", "presher", "pressure"]):
            target_id = "hypertension_bp_reading"
            target_slot = "bp_reading"
        elif any(k in lower_ans for k in ["glucose", "sugar", "blood sugar"]):
            target_id = "diabetes_glucose_reading"
            target_slot = "glucose_reading"
        elif any(k in lower_ans for k in ["symptom", "alamaat", "takleef"]):
            target_id = "diabetes_hyperglycemia_symptoms"
            target_slot = "hyperglycemia_symptoms"
        elif any(k in lower_ans for k in ["adherence", "med", "dawa", "goli"]):
            target_id = "diabetes_adherence"
            target_slot = "adherence_diabetes"
        else:
            target_id = "diabetes_glucose_reading"
            target_slot = "glucose_reading"

        target_item = bank.get_by_id(target_id)
        if target_item:
            session_state["asked_slots"] = [s for s in asked_slots if s not in (target_slot, target_id)]
            if target_slot in known_slots:
                del known_slots[target_slot]
            if target_item.also_fills:
                for ex_s in target_item.also_fills:
                    if ex_s in known_slots:
                        del known_slots[ex_s]
            session_state["correcting_slot"] = target_slot
            session_state["step"] = target_item.slot
            session_state["current_question"] = _get_localized_text(target_item, lang)
            session_state["why_text"] = _get_localized_why_text(target_item, lang)
            session_state["options"] = target_item.choices
            session_state["option_items"] = _build_option_items(target_item, lang)
            return session_state

    if session_state.get("correcting_slot"):
        session_state["correcting_slot"] = None
        # R8: Re-show summary confirmation immediately after the corrected slot is answered
        session_state["is_probe"] = False
        step_id = "summary_confirmation"
        question_text = _build_dual_summary_text(known_slots, lang, asked_slots=asked_slots)
        why_text = get_message("summary_confirm_why", lang)
        options = ["Confirm and submit", "Need to change something"]
        option_items = [
            {"value": "Confirm and submit", "label": get_message("summary_confirm_option_submit", lang)},
            {"value": "Need to change something", "label": get_message("summary_confirm_option_change", lang)},
        ]

        session_state["step"] = step_id
        session_state["current_question"] = question_text
        session_state["why_text"] = why_text
        session_state["options"] = options
        session_state["option_items"] = option_items
        session_state["can_skip"] = False
        session_state["can_say_unknown"] = False
        return session_state

    # =========================================================================
    # 4. ADAPTIVE PLANNER: DECIDE NEXT QUESTION
    # =========================================================================
    patient_record = session_state.get("patient_record", {})
    recent_checkins = session_state.get("recent_checkins", [])
    contradictions = session_state.get("contradictions", [])

    decision: PlanDecision = plan_next_step(
        known_slots=known_slots,
        findings=current_findings,
        patient_record=patient_record,
        recent_checkins=recent_checkins,
        bank=bank,
        asked_slots=set(asked_slots),
        contradictions=contradictions,
        base_budget=8,
        hard_cap=14,
    )

    if decision.action == "finish":
        session_state["completed"] = True
        session_state["complete"] = True
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
        return session_state

    # Format next question
    question_text = ""
    why_text = ""
    options = None
    can_skip = True
    can_say_unknown = True
    step_id = decision.target_slot or "question"

    option_items = None
    if decision.action == "summary_confirm":
        session_state["is_probe"] = False
        step_id = "summary_confirmation"
        question_text = _build_dual_summary_text(known_slots, lang, asked_slots=asked_slots)
        why_text = get_message("summary_confirm_why", lang)
        options = ["Confirm and submit", "Need to change something"]
        option_items = [
            {"value": "Confirm and submit", "label": get_message("summary_confirm_option_submit", lang)},
            {"value": "Need to change something", "label": get_message("summary_confirm_option_change", lang)},
        ]
    elif decision.item:
        session_state["is_probe"] = False
        step_id = decision.item.slot
        question_text = _get_localized_text(decision.item, lang)
        why_text = _get_localized_why_text(decision.item, lang)
        options = decision.item.choices
        option_items = _build_option_items(decision.item, lang)
        can_skip = (decision.item.priority_class != "safety")
        can_say_unknown = True
    elif decision.probe:
        step_id = decision.probe.get("slot", "probe")
        question_text = _get_localized_text(decision.probe, lang)
        why_text = _get_localized_why_text(decision.probe, lang)
        options = decision.probe.get("choices")
        option_items = _build_option_items(decision.probe, lang)
        can_skip = True
        can_say_unknown = True
        session_state.setdefault("probes_asked", []).append(decision.probe.get("probe_id") or step_id)
        session_state["is_probe"] = True

    session_state["step"] = step_id
    session_state["current_question"] = question_text
    session_state["why_text"] = why_text
    session_state["options"] = options
    session_state["option_items"] = option_items
    session_state["can_skip"] = can_skip
    session_state["can_say_unknown"] = can_say_unknown
    session_state["progress_hint"] = f"{decision.question_count}/{decision.max_budget}"
    session_state["current_decision_target"] = decision.target_slot

    return session_state


def finish_v3_session(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the v3 session into canonical checkin intake structures
    for downstream reconciliation, verification, and clinical safety review.
    """
    conditions = session_state.get("conditions_on_file", ["diabetes"])
    readings_dict = session_state.get("readings", {})
    raw_answers = session_state.get("raw_answers", {})
    answered_by = session_state.get("answered_by", "patient")
    intakes = []

    # R9: Confidence calculation (lowered by one level if caregiver)
    base_confidence = "High"
    if session_state.get("ended_early_off_topic") or session_state.get("possible_severe_low"):
        base_confidence = "Low"

    if answered_by == "caregiver":
        if base_confidence == "High":
            confidence = "Medium"
        elif base_confidence == "Medium":
            confidence = "Low"
        else:
            confidence = "Low"
    else:
        confidence = base_confidence

    for cond in conditions:
        cond_readings = []
        cond_symptoms = []
        cond_notes = []

        if cond in ("diabetes", "type_2_diabetes"):
            if "glucose" in readings_dict:
                cond_readings.append({
                    "observation_type": "glucose",
                    "value": readings_dict["glucose"],
                    "unit": "mg/dL",
                    "source": "patient_checkin",
                })
            for k in ("diabetes_hypo_symptoms", "diabetes_hyper_symptoms", "hypo_symptoms_acute"):
                if k in raw_answers:
                    cond_symptoms.append(raw_answers[k])

        if cond == "hypertension":
            if "blood_pressure_systolic" in readings_dict:
                cond_readings.append({
                    "observation_type": "blood_pressure_systolic",
                    "value": readings_dict["blood_pressure_systolic"],
                    "unit": "mmHg",
                    "source": "patient_checkin",
                })
            if "blood_pressure_diastolic" in readings_dict:
                cond_readings.append({
                    "observation_type": "blood_pressure_diastolic",
                    "value": readings_dict["blood_pressure_diastolic"],
                    "unit": "mmHg",
                    "source": "patient_checkin",
                })
            if "bp_symptoms" in raw_answers:
                cond_symptoms.append(raw_answers["bp_symptoms"])

        if session_state.get("possible_severe_low"):
            cond_notes.append("glucose value unit unclear, possible low")

        for pq in session_state.get("patient_questions", []):
            cond_notes.append(f"Patient question: {pq.get('text')}")

        if answered_by == "caregiver":
            cond_notes.append("answers are from a caregiver")
        for pn in session_state.get("patient_notes", []):
            cond_notes.append(pn)

        intakes.append({
            "condition": cond,
            "readings": cond_readings,
            "symptoms": cond_symptoms,
            "notes": cond_notes,
            "emergency": session_state.get("emergency", False),
            "emergency_reason": session_state.get("emergency_reason"),
            "confidence": confidence,
            "answered_by": answered_by,
        })

    return {
        "checkin_id": session_state.get("checkin_id"),
        "intakes": intakes,
        "emergency": session_state.get("emergency", False),
        "emergency_reason": session_state.get("emergency_reason"),
        "needs_review": session_state.get("needs_clinician_flag", False) or session_state.get("possible_severe_low", False),
        "findings": session_state.get("findings", []),
        "possible_severe_low": session_state.get("possible_severe_low", False),
        "answered_by": answered_by,
    }


# Aliases for compatibility
v3_start_session = start_v3_session
v3_next_turn = next_turn
v3_finish = finish_v3_session
