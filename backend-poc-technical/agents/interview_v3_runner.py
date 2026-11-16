"""
Interview Engine v3 Runner (Stage 9A-2).

Connects the modular Question Bank, Findings Extractor, Adaptive Planner,
Answer Validation, and Deterministic Input Triage into the check-in lifecycle.

Controlled by server flag: INTERVIEW_ENGINE (values: 'v2' default, 'v3').
Deterministic: The Model Proposes, The Rules Decide.
"""

from __future__ import annotations

import os
import re
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
    detect_caregiver_phrase,
    is_unclear_adherence_answer,
)
from agents.answer_validation import (
    ValidationResult,
    check_contradiction,
    detect_meter_lo_hi,
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


def _build_dual_summary_text(
    known_slots: Dict[str, Any],
    lang: str,
    asked_slots: Optional[List[str]] = None,
    session_state: Optional[Dict[str, Any]] = None,
) -> str:
    """
    R8: Constructs a structured summary listing captured readings and values
    for both diabetes and hypertension in the session language.
    """
    if "known_slots" in known_slots and isinstance(known_slots["known_slots"], dict):
        if asked_slots is None and "asked_slots" in known_slots:
            asked_slots = known_slots["asked_slots"]
        session_dict = known_slots
        if session_state is None:
            session_state = session_dict
        known_slots = session_dict["known_slots"]

    if asked_slots is None:
        asked_slots = []
    """
    R8: Constructs a structured summary listing captured readings and values
    for both diabetes and hypertension in the session language.
    """
    # 1. Glucose
    gluc = known_slots.get("glucose_reading")
    f_gluc = None
    if gluc is not None and not isinstance(gluc, bool):
        try:
            f_gluc = float(gluc)
        except (ValueError, TypeError):
            f_gluc = None

    if f_gluc is not None:
        ctx = known_slots.get("glucose_context", "")
        ctx_map_en = {"after_meal": "after meal", "fasting": "fasting", "random": "random", "bedtime": "bedtime"}
        ctx_map_ur = {"after_meal": "کھانے کے بعد", "fasting": "نہار منہ", "random": "کسی بھی وقت", "bedtime": "سونے سے پہلے"}
        ctx_map_ro = {"after_meal": "khane ke baad", "fasting": "nihar munh", "random": "aam waqt", "bedtime": "sone se pehle"}

        ctx_en = f" ({ctx_map_en.get(ctx, ctx.replace('_', ' '))})" if ctx else ""
        ctx_ur = f" ({ctx_map_ur.get(ctx, ctx)})" if ctx else ""
        ctx_ro = f" ({ctx_map_ro.get(ctx, ctx.replace('_', ' '))})" if ctx else ""

        gluc_en = f"Blood Glucose: {f_gluc:g} mg/dL{ctx_en}"
        gluc_ur = f"شوگر: {f_gluc:g} mg/dL{ctx_ur}"
        gluc_ro = f"Sugar: {f_gluc:g} mg/dL{ctx_ro}"
    else:
        gluc_en = "Blood Glucose: Not provided"
        gluc_ur = "شوگر: درج نہیں کی گئی"
        gluc_ro = "Sugar: Darj nahi ki gayi"

    # 2. Blood Pressure
    bp = known_slots.get("bp_reading")
    if bp and isinstance(bp, (list, tuple)) and len(bp) >= 2:
        try:
            bp_sys = int(bp[0]) if float(bp[0]).is_integer() else bp[0]
            bp_dia = int(bp[1]) if float(bp[1]).is_integer() else bp[1]
            bp_en = f"Blood Pressure: {bp_sys}/{bp_dia} mmHg"
            bp_ur = f"بلڈ پریشر: {bp_sys}/{bp_dia} mmHg"
            bp_ro = f"Blood Pressure: {bp_sys}/{bp_dia} mmHg"
        except (ValueError, TypeError):
            bp_en = "Blood Pressure: Not provided"
            bp_ur = "بلڈ پریشر: درج نہیں کیا گیا"
            bp_ro = "Blood Pressure: Darj nahi kiya gaya"
    else:
        bp_en = "Blood Pressure: Not provided"
        bp_ur = "بلڈ پریشر: درج نہیں کیا گیا"
        bp_ro = "Blood Pressure: Darj nahi kiya gaya"

    # 3. Symptoms
    findings = []
    if session_state and isinstance(session_state, dict):
        findings = session_state.get("findings", [])
    if not findings and isinstance(known_slots, dict):
        findings = known_slots.get("findings", [])

    if findings:
        from agents.interview_findings import format_finding_label
        formatted_list = [format_finding_label(f, lang) for f in findings]
        joined = ", ".join(formatted_list)
        symp_en = f"Symptoms: {joined}"
        if lang == "ur":
            symp_ur = f"علامات: {joined}"
        elif lang == "roman_ur":
            symp_ro = f"Alamaat: {joined}"
        else:
            symp_ur = f"علامات: {joined}"
            symp_ro = f"Alamaat: {joined}"
    else:
        symptoms = []
        if known_slots.get("hyperglycemia_symptoms") is True or known_slots.get("associated_symptoms") is True:
            symptoms.append("reported symptoms")
        if known_slots.get("foot_problems") is True:
            symptoms.append("foot numbness or sores")

        symptoms_denied = (
            known_slots.get("symptoms_denied") is True
            or known_slots.get("hyperglycemia_symptoms") is False
            or known_slots.get("associated_symptoms") is False
            or known_slots.get("foot_problems") is False
        )

        if symptoms:
            symp_en = f"Symptoms: {', '.join(symptoms)}"
            symp_ur = "علامات: علامات کی اطلاع دی گئی"
            symp_ro = "Alamaat: Alamaat report ki gayi hain"
        elif symptoms_denied:
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
    elif adh == "unclear":
        adh_en = "Medication: Adherence unclear"
        adh_ur = "ادویات: استعمال واضح نہیں"
        adh_ro = "Dawai: Istemal wazeh nahi"
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
    opening_note: Optional[str] = None,
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
        "baseline": baseline.to_dict() if hasattr(baseline, "to_dict") else (baseline or {}),
    }

    known_slots: Dict[str, Any] = {}
    asked_slots: List[str] = []
    findings: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []
    recent_checkins = (baseline.get("recent_history", []) if isinstance(baseline, dict) else getattr(baseline, "recent_history", [])) if baseline else []
    readings: Dict[str, Any] = {}

    clean_note = opening_note.strip() if (opening_note and isinstance(opening_note, str) and opening_note.strip()) else None
    if clean_note:
        temp_state = {"known_slots": known_slots, "readings": readings}
        _extract_early_slots(clean_note, temp_state, lang)
        known_slots["greeting"] = True

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
        "readings": readings,
        "opening_note": clean_note,
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
        "turn_count": 0,
        "step_attempt_counts": {},
    }

    return session_state


def _has_clinical_content(text: str, lang: str = "en") -> bool:
    """Returns True if text contains a numeric value, BP, yes/no, or symptom cue."""
    if not text:
        return False
    # Numeric or BP or meter tokens
    if re.search(r"\d+", text):
        return True
    if detect_meter_lo_hi(text) is not None:
        return True
    p_num = parse_number(text)
    if p_num.get("value") is not None:
        return True
    p_bp = parse_bp(text)
    if p_bp.get("value") is not None:
        return True
    # Yes / No
    p_yn = parse_yes_no(text, lang=lang)
    if p_yn.get("value") in ("yes", "no"):
        return True
    # Symptoms / findings
    findings = extract_findings_from_answer(text)
    if findings:
        return True
    return False


def _extract_early_slots(answer_text: str, session_state: Dict[str, Any], lang: str) -> None:
    """
    Extracts clinical slots that the patient provides early (e.g. in greeting or free text)
    across English, Urdu, and Roman Urdu, avoiding redundant questions.
    Only populates known_slots and readings; never alters asked_slots turn counter.
    """
    if not answer_text or not isinstance(answer_text, str):
        return

    known_slots = session_state.setdefault("known_slots", {})
    readings = session_state.setdefault("readings", {})
    lower_ans = answer_text.lower().strip()

    # 1. Early Blood Pressure Extraction
    if "bp_reading" not in known_slots and "hypertension_bp_reading" not in known_slots:
        bp_res = parse_bp(answer_text)
        bp_parsed = bp_res.get("value") if isinstance(bp_res, dict) else bp_res
        if not bp_parsed:
            bp_patterns = [
                r'(?:(?:bp|blood\s*pressure|b\.p\.?|بلڈ\s*پریشر)\s*(?:was|is|tha|thi|hai|:)?\s*)?([0-9\u0660-\u0669\u06F0-\u06F9]{2,3})\s*(?:[/]|over|by|bata|بٹہ|پر)\s*([0-9\u0660-\u0669\u06F0-\u06F9]{2,3})\b',
                r'\b(?:bp|blood\s*pressure|b\.p\.?|بلڈ\s*پریشر)\s*(?:was|is|tha|thi|hai|:)?\s*([0-9\u0660-\u0669\u06F0-\u06F9]{2,3})\s+([0-9\u0660-\u0669\u06F0-\u06F9]{2,3})\b',
            ]
            for pat in bp_patterns:
                m = re.search(pat, answer_text, re.IGNORECASE)
                if m:
                    candidate = f"{m.group(1)}/{m.group(2)}"
                    cand_res = parse_bp(candidate)
                    val = cand_res.get("value") if isinstance(cand_res, dict) else cand_res
                    if val and isinstance(val, (list, tuple)) and len(val) >= 2:
                        bp_parsed = val
                        break

        if bp_parsed and isinstance(bp_parsed, (list, tuple)) and len(bp_parsed) >= 2:
            sys_val, dia_val = float(bp_parsed[0]), float(bp_parsed[1])
            if 40 <= sys_val <= 300 and 30 <= dia_val <= 200:
                sys_num = int(sys_val) if sys_val.is_integer() else sys_val
                dia_num = int(dia_val) if dia_val.is_integer() else dia_val
                known_slots["bp_reading"] = [sys_num, dia_num]
                readings["bp"] = f"{sys_num}/{dia_num}"
                readings["blood_pressure_systolic"] = sys_num
                readings["blood_pressure_diastolic"] = dia_num
                session_state["readings"] = readings

    # 2. Early Blood Glucose Extraction
    if "glucose_reading" not in known_slots and "diabetes_glucose_reading" not in known_slots:
        has_glucose_hint = any(k in lower_ans for k in [
            "glucose", "sugar", "shugar", "mg/dl", "mg / dl", "mmol", "mmol/l", "fasting", "nahar",
            "شوگر", "گلوکوز", "نہار منہ", "نہار"
        ])
        is_pure_med_dose = bool(re.search(r'\b(metformin|glimepiride|insulin|tablet|tab|pill|dose|capsule)\s+\d+\s*mg\b', lower_ans))
        if has_glucose_hint and not is_pure_med_dose:
            meter_tok = detect_meter_lo_hi(answer_text)
            if not meter_tok:
                today_match = re.search(r'\b(?:today|aaj|ab|now|آج|اب)\s*(?:it\s*(?:is|was)|is|hai|tha|thi|ko)?\s*(\d{2,3})\b', lower_ans)
                if today_match:
                    try:
                        g_val = float(today_match.group(1))
                        if 20 <= g_val <= 600:
                            known_slots["glucose_reading"] = g_val
                            readings["glucose"] = g_val
                            session_state["readings"] = readings
                    except Exception:
                        pass
                else:
                    from agents.answer_understanding import strip_duration_phrases, detect_glucose_context
                    ans_no_dur = strip_duration_phrases(lower_ans)
                    mmol_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mmol(?:/l)?)', ans_no_dur)
                    if mmol_match:
                        try:
                            mmol_val = float(mmol_match.group(1))
                            mg_val = round(mmol_val * 18.0, 1)
                            if 20 <= mg_val <= 600:
                                known_slots["glucose_reading"] = mg_val
                                readings["glucose"] = mg_val
                                session_state["readings"] = readings
                                known_slots.pop("missing_reading", None)
                        except Exception:
                            pass
                    else:
                        mg_match = re.search(r'(\d{2,3})\s*(?:mg(?:/dl)?)', ans_no_dur)
                        if mg_match:
                            try:
                                g_val = float(mg_match.group(1))
                                if 20 <= g_val <= 600:
                                    known_slots["glucose_reading"] = g_val
                                    readings["glucose"] = g_val
                                    session_state["readings"] = readings
                                    known_slots.pop("missing_reading", None)
                            except Exception:
                                pass
                        else:
                            past_match = re.search(r'(?:sugar|glucose|shugar|شوگر|گلوکوز)\s*(?:was|thi|tha)?\s*(\d{2,3})\s*(?:last\s+week|yesterday|pichle\s+hafte|kal\b)', ans_no_dur)
                            if not past_match:
                                sug_match = re.search(r'(?:sugar|glucose|shugar|شوگر|گلوکوز|lunch|dinner|breakfast|meal|khana|khane|nashta|nashtay|khali\s*pait|khali\s*pet|nahar|fasting|کھانے|ناشتے|خالی\s*پیٹ|نہار).*?(\d{2,3})\b', ans_no_dur)
                                if sug_match:
                                    try:
                                        g_val = float(sug_match.group(1))
                                        if 20 <= g_val <= 600:
                                            known_slots["glucose_reading"] = g_val
                                            readings["glucose"] = g_val
                                            session_state["readings"] = readings
                                            known_slots.pop("missing_reading", None)
                                    except Exception:
                                        pass

    # 3. Early Glucose Context (Fasting / After meal)
    if "glucose_context" not in known_slots and "diabetes_glucose_context" not in known_slots:
        from agents.answer_understanding import detect_glucose_context
        ctx = detect_glucose_context(lower_ans)
        if ctx:
            known_slots["glucose_context"] = ctx
        elif any(w in lower_ans for w in ["fasting", "nahar munh", "nahar", "before meal", "khali pet", "before eating", "نہار منہ"]):
            known_slots["glucose_context"] = "fasting"
        elif any(w in lower_ans for w in ["after meal", "after eating", "post meal", "khany k baad", "khane ke baad", "کھانے کے بعد"]):
            known_slots["glucose_context"] = "after_meal"

    # 4. Early BP Technique (Rested / Seated)
    if "bp_technique" not in known_slots and "hypertension_bp_technique" not in known_slots:
        if any(w in lower_ans for w in ["rested", "sat quietly", "seated", "baith kar", "araam se", "rest for 5", "5 minutes", "بیٹھ کر"]):
            known_slots["bp_technique"] = "seated_rested"

    # 5. Early Adherence Extraction
    has_adh_reported = False
    pos_adh_patterns = [
        r"\btook\s+(?:all\s+)?(?:my\s+)?(?:med|meds|medicine|medicines|medication|medications|pills|tablets|metformin|insulin)\b",
        r"\b(?:all\s+)?(?:meds|medicines|medications|pills|tablets)\s+taken\b",
        r"\b(?:taking|taken)\s+(?:all\s+)?(?:prescribed|my\s+meds)\b",
        r"\b(?:dawa|dawain|dawai|goli|goliyan)\s+(?:le\s+li|kha\s+li|leli|khali)\b",
        r"\bsab\s+(?:dawa|dawain|dawai|goliyan|adwiyat)\b",
        r"(?:تمام\s+ادویات|دوائیاں\s+لے\s+لی\s+ہیں|دوا\s+لے\s+لی)",
    ]
    neg_adh_patterns = [
        r"\bmissed\s+(?:my\s+)?(?:med|meds|medicine|medicines|medication|medications|pills|tablets|insulin|dose|doses)\b",
        r"\b(?:dawa|dawain|dawai|goli|goliyan)\s+(?:nahi\s+li|chhoot\s+gayi|bhool\s+gaya)\b",
        r"\bforgot\s+(?:to\s+take\s+)?(?:my\s+)?(?:meds|pills|medicine)\b",
    ]

    if any(re.search(pat, lower_ans) for pat in pos_adh_patterns):
        known_slots["adherence_diabetes"] = True
        known_slots["adherence_hypertension"] = True
        known_slots["adherence"] = True
        has_adh_reported = True
    elif any(re.search(pat, lower_ans) for pat in neg_adh_patterns):
        if "blood pressure" in lower_ans or "bp" in lower_ans:
            known_slots["adherence_hypertension"] = False
        if "insulin" in lower_ans or "metformin" in lower_ans or "sugar" in lower_ans:
            known_slots["adherence_diabetes"] = False
        has_adh_reported = True

    # 6. Early Symptoms Denial & Recognition (P2-5)
    symptom_denial_patterns = [
        r"\bno\s+symptoms?\b",
        r"\bno\s+symptoms?,\s*all\s+good\b",
        r"\bno\s+(?:issues?|trouble|problems?|complaints?)\b",
        r"\bkoi\s+(?:alamaat|masla|takleef)\s+nahi\b",
        r"(?:کوئی\s+علامت\s+نہیں|کوئی\s+مسئلہ\s+نہیں|کوئی\s+تکلیف\s+نہیں)",
    ]
    if any(re.search(pat, lower_ans) for pat in symptom_denial_patterns):
        known_slots["symptoms_denied"] = True

    # 7. Early Greeting / Wellbeing Detection (P3-24)
    wellbeing_patterns = [
        r"\b(?:feeling|feel|doing)\s+(?:fine|good|well|great|okay|ok|alright|better)\b",
        r"\bi\s*(?:am|'m)\s+(?:fine|good|well|great|okay|ok|alright)\b",
        r"\ball\s+good\b",
        r"\btheek\s+(?:hoon|hain|thaak|thak)\b",
        r"\bsab\s+theek\s*(?:hai)?\b",
        r"\btabiyat\s+theek\s*(?:hai)?\b",
        r"\bshukar\s+hai\b",
        r"(?:ٹھیک\s+ہوں|سب\s+ٹھیک\s*ہے|طبیعت\s+ٹھیک\s*ہے|شکر\s+ہے)",
    ]
    if any(re.search(pat, lower_ans) for pat in wellbeing_patterns):
        known_slots["greeting"] = True

    # 8. Early Fasting & Broke Fast Detection
    broke_fast_patterns = [
        r"\b(?:broke|break|broken)\s+(?:my\s+)?fast\b",
        r"\broza\s+(?:tod|toda|tode|toor|tora|khol|khola|kholi|tor)\b",
        r"(?:روزہ\s+توڑا|روزہ\s+توڑ|روزہ\s+کھولا|روزہ\s+کھول)",
    ]
    if any(re.search(pat, lower_ans) for pat in broke_fast_patterns):
        known_slots["fasting_broke_fast"] = True
        session_state["fasting_broke_fast"] = True
        known_slots["fasting_broke_fast_reason"] = answer_text.strip()
        known_slots["is_fasting_today"] = True


def evaluate_severe_low_sugar(
    text: Optional[str] = None,
    session_state: Optional[Any] = None,
    current_readings: Optional[Dict[str, Any]] = None,
    current_question: Optional[str] = None,
    current_step: Optional[str] = None,
    lang: str = "en",
) -> Dict[str, Any]:
    """
    Evaluates acute severe hypoglycemia (< 54 mg/dL or < 3.0 mmol/L) with confusion,
    disorientation, inability to eat/drink, or fainting/seizure turn-by-turn.
    Deterministic: Calls triage_protocol._decide_glucose_low without duplicating thresholds.
    If glucose < 70 without neuro symptoms, returns approved low-sugar guidance.
    """
    from agents.triage_protocol import (
        GLUCOSE_VERY_LOW_MG_DL,
        GLUCOSE_LOW_MG_DL,
        _decide_glucose_low,
        TriageProtocolState,
        GLUCOSE,
    )
    from agents.interview_bank.loader import get_message

    text_clean = (text or "").strip()
    lower_ans = text_clean.lower()
    glucose_val = None

    # 1. Check text for current reading
    today_match = re.search(r'\b(?:today|aaj|ab|now|آج|اب)\s*(?:it\s*(?:is|was)|is|hai|tha|thi|ko)?\s*(\d{2,3})\b', lower_ans)
    if today_match:
        val = float(today_match.group(1))
        if 20 <= val <= 600:
            glucose_val = val
    else:
        mmol_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mmol(?:/l)?)', lower_ans)
        if mmol_match:
            val = round(float(mmol_match.group(1)) * 18.0, 1)
            if 20 <= val <= 600:
                glucose_val = val
        else:
            mg_match = re.search(r'(\d{2,3})\s*(?:mg(?:/dl)?)', lower_ans)
            if mg_match:
                val = float(mg_match.group(1))
                if 20 <= val <= 600:
                    glucose_val = val
            else:
                past_match = re.search(r'(?:sugar|glucose|shugar|شوگر|گلوکوز)\s*(?:was|thi|tha)?\s*(\d{2,3})\s*(?:last\s+week|yesterday|pichle\s+hafte|kal\b)', lower_ans)
                if not past_match:
                    sug_match = re.search(r'(?:sugar|glucose|shugar|شوگر|گلوکوز).*?(\d{2,3})\b', lower_ans)
                    if sug_match:
                        val = float(sug_match.group(1))
                        if 20 <= val <= 600:
                            glucose_val = val

    # 2. Check if answer is a pure numeric response to glucose question
    if glucose_val is None and current_step in ("glucose_reading", "fasting_blood_sugar", "diabetes_glucose_reading") and text_clean.isdigit():
        val = float(text_clean)
        if 20 <= val <= 600:
            glucose_val = val

    # 3. Check current readings dict
    if glucose_val is None and current_readings and isinstance(current_readings, dict):
        val = current_readings.get("glucose")
        if val is not None:
            glucose_val = float(val)

    # 4. Check session state
    if glucose_val is None and session_state:
        if isinstance(session_state, dict):
            val = session_state.get("readings", {}).get("glucose")
            if val is None:
                val = session_state.get("known_slots", {}).get("glucose_reading")
            if val is None:
                val = session_state.get("known_slots", {}).get("diabetes_glucose_reading")
            if val is not None:
                try:
                    glucose_val = float(val)
                except Exception:
                    pass
        elif hasattr(session_state, "answers") and isinstance(session_state.answers, dict):
            val = session_state.answers.get("glucose_reading")
            if val is not None:
                try:
                    glucose_val = float(val)
                except Exception:
                    pass

    # Threshold checks against triage_protocol constants
    if glucose_val is None or glucose_val >= GLUCOSE_LOW_MG_DL:
        return {"is_emergency": False, "needs_low_guidance": False, "glucose_val": glucose_val}

    if glucose_val >= GLUCOSE_VERY_LOW_MG_DL:
        return {
            "is_emergency": False,
            "needs_low_guidance": True,
            "glucose_val": glucose_val,
            "guidance": get_message("v3_possible_low_guidance", lang),
        }

    # glucose_val < GLUCOSE_VERY_LOW_MG_DL (< 54 mg/dL or < 3.0 mmol/L)
    # Check confusion / neuro symptoms in EN, Urdu, Roman Urdu
    NEURO_PATTERNS = [
        r'\b(?:confus\w*|disorient\w*|can\'?t think(?:\s+straight)?|cannot think(?:\s+straight)?|unable to think|trouble thinking|mind is foggy|drows\w*|trouble staying awake)\b',
        r'(?:\u0627\u0644\u062c\u06be\u0646|\u0633\u0645\u062c\u06be \u0646\u06c1\u06cc\u06ba|\u06a9\u0686\u06be \u0633\u0645\u062c\u06be \u0646\u06c1\u06cc\u06ba|\u0630\u06c1\u0646 \u06a9\u0627\u0645 \u0646\u06c1\u06cc\u06ba|\u062f\u0645\u0627\u063a \u06a9\u0627\u0645 \u0646\u06c1\u06cc\u06ba|\u0633\u0648\u0686 \u0646\u06c1\u06cc\u06ba \u067e\u0627 \u0631\u06c1|\u063a\u0646\u0648\u062f\u06af\u06cc)',
        r'\b(?:kuch samajh nahi|samajh nahi aa rah|samajh nahi arah|samajh nahi aari|samajh nahi aa rahi|zehn kaam nahi|dimagh kaam nahi|soch nahi pa rah|soch nahi pa rahi|socha nahi ja rah|uljhan|ghunoodgi)\b',
    ]
    SWALLOW_PATTERNS = [
        r'\b(?:unable to (?:eat|drink|swallow)|can(?:\'?t|not) (?:eat|drink|swallow)|not able to (?:eat|drink|swallow))\b',
        r'(?:\u06a9\u06be\u0627 \u067e\u06cc \u0646\u06c1\u06cc\u06ba|\u067e\u0627\u0646\u06cc \u0646\u06c1\u06cc\u06ba \u067e\u06cc|\u0646\u06af\u0644 \u0646\u06c1\u06cc\u06ba)',
        r'\b(?:kha pi nahi|kuch kha pi nahi|pani nahi pee|nigal nahi|kha pee nahi)\b',
    ]
    SEIZURE_PATTERNS = [
        r'\b(?:faint\w*|passed out|passing out|blacked out|blacking out|collaps\w*|unconscious\w*|loss of consciousness|seizur\w*|fits|convuls\w*)\b',
        r'(?:\u0628\u06d2 \u06c1\u0648\u0634|\u0628\u06cc\u06c1\u0648\u0634|\u063a\u0634|\u062f\u0648\u0631\u06c1|\u062f\u0648\u0631\u06d2|\u062c\u06be\u0679\u06a9\u06d2)',
        r'\b(?:behosh|be hosh|gash|daura|daure|jhatke|gir gay[ai])\b',
    ]

    def has_active_symptom(t: str, patterns: List[str]) -> bool:
        for pat in patterns:
            for m in re.finditer(pat, t, re.IGNORECASE):
                start = m.start()
                end = m.end()
                pre = t[max(0, start-20):start].lower()
                post = t[end:min(len(t), end+20)].lower()
                is_neg = any(w in pre or w in post for w in ['no', 'not', 'nahi', 'nahin', 'نہیں', 'koi'])
                if not is_neg:
                    return True
        return False

    texts_to_check = [text_clean]
    if session_state and isinstance(session_state, dict):
        if session_state.get('opening_note'):
            texts_to_check.append(session_state['opening_note'])
        texts_to_check.extend(session_state.get('raw_answers', []))
        for v in session_state.get('answers', {}).values():
            if isinstance(v, str):
                texts_to_check.append(v)
    elif session_state and hasattr(session_state, 'answers') and isinstance(session_state.answers, dict):
        for v in session_state.answers.values():
            if isinstance(v, str):
                texts_to_check.append(v)

    has_neuro = any(has_active_symptom(t, NEURO_PATTERNS) or has_active_symptom(t, SEIZURE_PATTERNS) for t in texts_to_check)
    has_swallow = any(has_active_symptom(t, SWALLOW_PATTERNS) for t in texts_to_check)

    # Check affirmative answer to neuro question
    if not has_neuro and current_question:
        q_low = current_question.lower()
        if re.search(r'\b(?:confus\w*|shakin\w*|sweat\w*|dizz\w*|الجھن|چکر|پسینہ|uljhan|chakkar|paseena)\b', q_low):
            if re.search(r'\b(?:yes|haan|jee|ji|yep|yeah|جی|ہاں)\b', lower_ans):
                has_neuro = True

    if has_neuro or has_swallow:
        st = TriageProtocolState(
            protocol='glucose_low',
            age_band='adult_18_64',
            readings={GLUCOSE: glucose_val},
            answers={'orientation': False} if has_neuro else {'can_swallow': False},
        )
        t_res = _decide_glucose_low(st)
        return {
            'is_emergency': True,
            'needs_low_guidance': False,
            'emergency_reason': t_res.get('summary') or f"glucose low: glucose {glucose_val:g} mg/dL; Low glucose with disorientation or acute confusion.",
            'triage_dict': t_res,
            'glucose_val': glucose_val,
            'guidance': t_res.get('guidance'),
        }

    return {
        'is_emergency': False,
        'needs_low_guidance': True,
        'emergency_reason': None,
        'triage_dict': None,
        'glucose_val': glucose_val,
        'guidance': get_message('v3_possible_low_guidance', lang),
    }


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
    session_state["turn_count"] = session_state.get("turn_count", 0) + 1
    current_slot = session_state.get("step", "greeting")
    step_counts = session_state.setdefault("step_attempt_counts", {})
    step_counts[current_slot] = step_counts.get(current_slot, 0) + 1

    # Global Loop Guard: same step asked at most 2 times (original + 1 clarify)
    # If a step is somehow entered for a 3rd time, mark unclear and bypass it
    if step_counts.get(current_slot, 0) > 2:
        known_slots = session_state.setdefault("known_slots", {})
        known_slots[current_slot] = "unclear"
        known_slots[f"{current_slot}__evidence"] = clean_answer
        session_state["needs_clinician_flag"] = True
        session_state.setdefault("patient_notes", []).append(
            f"Step '{current_slot}' reached maximum attempts ({step_counts[current_slot]}). Moved forward with clinician flag."
        )
        asked_slots = session_state.setdefault("asked_slots", [])
        if current_slot not in asked_slots:
            asked_slots.append(current_slot)
        from agents.interview_planner import SLOT_EQUIVALENCES
        for eq in SLOT_EQUIVALENCES.get(current_slot, set()):
            if eq not in asked_slots:
                asked_slots.append(eq)
        session_state["safety_clarify_slot"] = None
        session_state["awaiting_adherence_clarification"] = None
        session_state["awaiting_glucose_unit"] = False
        session_state["awaiting_meter_lo_hi_confirmation"] = None

    from agents.answer_understanding import detect_caregiver_phrase, strip_caregiver_phrase
    is_caregiver = detect_caregiver_phrase(clean_answer)
    clinical_remainder = strip_caregiver_phrase(clean_answer) if is_caregiver else clean_answer
    eff_answer = clinical_remainder if (is_caregiver and clinical_remainder) else clean_answer

    # =========================================================================
    # 1. INPUT TRIAGE & RED-FLAG SCREEN FIRST (Authoritative Deterministic Safety)
    # =========================================================================
    if session_state.get("awaiting_vomiting_followup"):
        session_state.pop("awaiting_vomiting_followup", None)
        yn_res = parse_yes_no(eff_answer, lang=lang)
        if yn_res["value"] == "yes":
            session_state["emergency"] = True
            session_state["emergency_reason"] = "unable_to_keep_fluids"
            session_state["completed"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            session_state["system_note"] = get_message("emergency_red_flag_note", lang)
            from agents.danger_wordgroups import get_safety_note
            session_state["safety_note"] = get_safety_note(lang)
            return session_state
        else:
            session_state["needs_clinician_flag"] = True
            session_state["urgent"] = True
            session_state["completed"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            session_state["system_note"] = "Check-in flagged for urgent clinician review."
            return session_state

    from agents.adaptive_interview_agent import run_stage1_red_flag_screen
    rf_screen_flagged, rf_screen_reason = run_stage1_red_flag_screen(clean_answer)
    if rf_screen_flagged:
        if rf_screen_reason == "non_stop_vomiting":
            session_state["awaiting_vomiting_followup"] = True
            session_state["current_question"] = get_message("vomiting_followup_question", lang)
            session_state["options"] = ["yes", "no"]
            session_state["option_items"] = [
                {"value": "yes", "label": "ہاں" if lang == "ur" else ("haan" if lang == "roman_ur" else "yes")},
                {"value": "no", "label": "نہیں" if lang == "ur" else ("nahi" if lang == "roman_ur" else "no")},
            ]
            return session_state
        elif rf_screen_reason == "unable_to_keep_fluids":
            session_state["emergency"] = True
            session_state["emergency_reason"] = "unable_to_keep_fluids"
            session_state["completed"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            session_state["system_note"] = get_message("emergency_red_flag_note", lang)
            from agents.danger_wordgroups import get_safety_note
            session_state["safety_note"] = get_safety_note(lang)
            return session_state

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

    # 1b. DANGER WORD GROUPS SCREEN (behind DANGER_WORDGROUPS_ENABLED flag)
    from agents.danger_wordgroups import is_danger_wordgroups_enabled, detect as detect_wordgroups, get_safety_note
    if is_danger_wordgroups_enabled() and clean_answer:
        wg_hit = detect_wordgroups(clean_answer)
        if wg_hit.is_danger:
            session_state.setdefault("wordgroup_hits", []).append({"group": wg_hit.group, "step": current_slot})
            session_state["safety_note"] = get_safety_note(lang)




    # G-14: Caregiver detection across Urdu, Roman Urdu, and English
    from agents.answer_understanding import is_only_caregiver_statement, strip_caregiver_phrase
    is_caregiver = detect_caregiver_phrase(clean_answer) or (triage_res.odd_class == "third_party_report")
    if is_caregiver:
        session_state["answered_by"] = "caregiver"
        session_state.setdefault("known_slots", {})["answered_by"] = "caregiver"

    clinical_remainder = strip_caregiver_phrase(clean_answer) if is_caregiver else clean_answer

    if is_caregiver and (is_only_caregiver_statement(clean_answer) or triage_res.odd_class == "third_party_report"):
        if not clinical_remainder or is_only_caregiver_statement(clean_answer):
            # Answer is ONLY a caregiver statement (no number, no yes/no, no symptom).
            # Treat as odd_input, but NEVER end interview through strike rule.
            triage_res = TriageInputResult(
                category="odd_input",
                odd_class="third_party_report",
                response_key="third_party_report",
                is_off_topic=False,
            )
        else:
            # Clinical remainder exists! Keep processing normally.
            triage_res = TriageInputResult(
                category="normal_clinical",
                odd_class=None,
                trigger_detail=None,
                response_key=None,
                is_emergency=triage_res.is_emergency,
                is_urgent_safety=triage_res.is_urgent_safety,
                needs_clinician_flag=False,
                is_off_topic=False,
            )

    if triage_res.category == "odd_input":
        is_third_party = (triage_res.odd_class == "third_party_report")
        if not is_third_party:
            odd_count = session_state.get("consecutive_odd_count", 0) + 1
            session_state["consecutive_odd_count"] = odd_count
        else:
            odd_count = session_state.get("consecutive_odd_count", 0)
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
        # (Caregiver statements alone must NEVER end the interview through the strike rule)
        if not is_third_party and odd_count >= 4:
            session_state["ended_early_off_topic"] = True
            session_state["completed"] = True
            session_state["step"] = "COMPLETE"
            session_state["current_question"] = None
            session_state["system_note"] = get_message("strike_rule_offtopic_done", lang)
            return session_state

        # Strike rule: 2 consecutive off-topic answers -> offer choices
        # (Caregiver statements alone must NEVER trigger strike options menu)
        if not is_third_party and odd_count >= 2:
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
    eff_answer = clinical_remainder if (is_caregiver and clinical_remainder) else clean_answer
    _extract_early_slots(eff_answer, session_state, lang)

    # P0-2: Immediate severe low sugar check right after early slot extraction
    early_low_eval = evaluate_severe_low_sugar(
        text=eff_answer,
        session_state=session_state,
        current_readings=session_state.get("readings"),
        current_question=session_state.get("current_question"),
        current_step=current_slot,
        lang=lang,
    )
    if early_low_eval.get("is_emergency"):
        session_state["emergency"] = True
        session_state["emergency_reason"] = early_low_eval["emergency_reason"]
        session_state["completed"] = True
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
        session_state["system_note"] = get_message("emergency_red_flag_note", lang)
        from agents.danger_wordgroups import get_safety_note
        session_state["safety_note"] = get_safety_note(lang)
        session_state["triage"] = early_low_eval.get("triage_dict")
        return session_state
    elif early_low_eval.get("needs_low_guidance"):
        session_state["safety_note"] = early_low_eval["guidance"]
        session_state["system_note"] = early_low_eval["guidance"]

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
            session_state["possible_severe_low_guidance"] = get_message("v3_possible_low_guidance", lang)
        else:
            # Unanswered / unclear unit: Treat as possible severe low per clinical rule
            readings["glucose"] = float(unclarified_val)
            known_slots["glucose_reading"] = float(unclarified_val)
            session_state["possible_severe_low"] = True
            session_state["possible_severe_low_guidance"] = get_message("v3_possible_low_guidance", lang)
            session_state["needs_clinician_flag"] = True

    elif "glucose_reading" in current_slot or current_slot == "diabetes_glucose_reading":
        if session_state.get("awaiting_meter_lo_hi_confirmation"):
            token = session_state.pop("awaiting_meter_lo_hi_confirmation")
            yn_res = parse_yes_no(eff_answer, lang=lang)
            if yn_res["value"] == "yes":
                reason = "meter_lo" if token == "LO" else "meter_hi"
                session_state["emergency"] = True
                session_state["emergency_reason"] = reason
                session_state["completed"] = True
                session_state["step"] = "COMPLETE"
                session_state["current_question"] = None
                session_state["system_note"] = get_message("emergency_red_flag_note", lang)
                from agents.danger_wordgroups import get_safety_note
                session_state["safety_note"] = get_safety_note(lang)
                if token == "LO":
                    session_state["possible_severe_low"] = True
                    session_state["possible_severe_low_guidance"] = get_message("glucose_unclear_unit_safety_guidance", lang)
                return session_state
            else:
                session_state["current_question"] = (
                    "براہ کرم شوگر کی ریڈنگ نمبر میں بتائیں (mg/dL یا mmol/L)۔" if lang == "ur"
                    else ("Barah-e-karam sugar ki reading number mein batayein (mg/dL ya mmol/L)." if lang == "roman_ur"
                    else "Please enter your numeric blood sugar reading in mg/dL (or mmol/L).")
                )
                session_state["options"] = None
                session_state["option_items"] = None
                return session_state

        meter_token = detect_meter_lo_hi(eff_answer)
        if meter_token:
            session_state["awaiting_meter_lo_hi_confirmation"] = meter_token
            session_state["current_question"] = get_message("meter_lo_hi_confirmation", lang)
            session_state["options"] = ["yes", "no"]
            session_state["option_items"] = [
                {"value": "yes", "label": "ہاں" if lang == "ur" else ("haan" if lang == "roman_ur" else "yes")},
                {"value": "no", "label": "نہیں" if lang == "ur" else ("nahi" if lang == "roman_ur" else "no")},
            ]
            return session_state

        p_num = parse_number(eff_answer)
        cleaned_for_val = eff_answer
        if p_num["value"] is not None and p_num["kind"] == "words":
            import re as _re
            unit_match = _re.search(r"\b(mmol/l|mmol|mg/dl|mgdl|mg)\b", eff_answer.lower())
            if unit_match:
                cleaned_for_val = f"{p_num['value']:g} {unit_match.group(1)}"
            else:
                cleaned_for_val = f"{p_num['value']:g}"
        val_res: ValidationResult = validate_glucose_input(cleaned_for_val)
        if val_res.needs_unit_clarification:
            session_state["awaiting_glucose_unit"] = True
            session_state["raw_unclarified_glucose"] = val_res.value
            session_state["current_question"] = get_message("unit_clarification_question", lang)
            session_state["why_text"] = get_message("unit_clarification_why", lang)
            session_state["options"] = ["mmol/L", "mg/dL"]
            session_state["option_items"] = [
                {"value": "mmol/L", "label": "mmol/L"},
                {"value": "mg/dL", "label": "mg/dL"},
            ]
            return session_state
        elif val_res.valid and val_res.value is not None:
            clean_low = eff_answer.lower()
            has_unit = any(u in clean_low for u in ["mg", "dl", "mmol"])
            if not has_unit and 41.0 <= float(val_res.value) <= 54.0:
                session_state["awaiting_glucose_unit"] = True
                session_state["raw_unclarified_glucose"] = val_res.value
                session_state["current_question"] = get_message("unit_clarification_question", lang)
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
            known_slots.pop("missing_reading", None)

            # P1-3: Extract glucose_context if attached to reading answer
            from agents.answer_understanding import detect_glucose_context
            attached_ctx = detect_glucose_context(eff_answer)
            if attached_ctx and "glucose_context" not in known_slots and "diabetes_glucose_context" not in known_slots:
                known_slots["glucose_context"] = attached_ctx

            if val_res.is_possible_severe_low:
                session_state["possible_severe_low"] = True
                session_state["possible_severe_low_guidance"] = val_res.safety_guidance
                session_state["needs_clinician_flag"] = True
        else:
            known_slots["missing_reading"] = True

    elif "glucose_context" in current_slot or current_slot == "diabetes_glucose_context":
        from agents.answer_understanding import detect_glucose_context
        ctx = detect_glucose_context(eff_answer)
        if ctx:
            known_slots["glucose_context"] = ctx

    elif "bp_reading" in current_slot or current_slot == "hypertension_bp_reading":
        p_bp = parse_bp(eff_answer)
        cleaned_for_bp = eff_answer
        if p_bp["value"] is not None:
            cleaned_for_bp = f"{p_bp['value'][0]}/{p_bp['value'][1]}"
        bp_res: ValidationResult = validate_bp_input(cleaned_for_bp)
        if bp_res.valid and bp_res.value is not None:
            readings["blood_pressure_systolic"] = bp_res.value[0]
            readings["blood_pressure_diastolic"] = bp_res.value[1]
            known_slots["bp_reading"] = bp_res.value
            known_slots["bp_reading__evidence"] = p_bp.get("evidence", clean_answer)
            if bp_res.value[0] >= 180 or bp_res.value[1] >= 120:
                session_state["needs_clinician_flag"] = True
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
        yn_res = parse_yes_no(eff_answer, lang=lang)
        target_slot = bank_item.slot if bank_item else current_slot
        lower_ans = clean_answer.lower()

        # Slot-specific semantic yes/no resolution before safety clarification
        if target_slot in ("fasting_symptoms", "fasting_ramadan") or current_slot in ("fasting_symptoms", "fasting_ramadan"):
            broke_fast_patterns = [
                r"\b(?:broke|break|broken)\s+(?:my\s+)?fast\b",
                r"\broza\s+(?:tod|toda|tode|toor|tora|khol|khola|kholi|tor)\b",
                r"(?:روزہ\s+توڑا|روزہ\s+توڑ|روزہ\s+کھولا|روزہ\s+کھول)",
            ]
            fast_symptom_kws = [
                "shakiness", "shaky", "sweat", "sweating", "dizzy", "dizziness",
                "confusion", "confused", "thirst", "thirsty", "hunger", "hungry",
                "headache", "tremor", "trembling", "lightheaded", "faint", "fainting",
                "weakness", "weak", "palpitation", "palpitations", "paseena",
                "paseenay", "chakkar", "uljhan", "pyas", "thakawat", "bhook",
                "kapkapi", "kapkapahat", "پسینہ", "چکر", "الجھن", "پیاس", "تھکاوٹ",
                "بھوک", "کپکپاہٹ", "کمزوری"
            ]
            if any(re.search(pat, lower_ans) for pat in broke_fast_patterns):
                session_state["fasting_broke_fast"] = True
                known_slots["fasting_broke_fast"] = True
                known_slots["fasting_broke_fast_reason"] = clean_answer
                yn_res = {"value": "yes", "evidence": clean_answer, "partial": False}
            elif yn_res.get("value") not in ("yes", "no"):
                extracted_f = extract_findings_from_answer(clean_answer)
                if extracted_f or any(k in lower_ans for k in fast_symptom_kws):
                    yn_res = {"value": "yes", "evidence": clean_answer, "partial": False}
                    if not extracted_f:
                        f_kind = "low_sugar_episode" if any(k in lower_ans for k in ["shakiness", "shaky", "sweat", "sweating", "paseena", "kapkapi"]) else "dizziness"
                        extracted_f.append(
                            Finding(
                                id=f"fnd_fasting_symptom_{len(session_state.get('findings', [])) + 1}",
                                kind=f_kind,
                                label=f_kind.replace("_", " ").title(),
                                raw_quote=clean_answer,
                                confidence="High",
                                source_step=current_slot,
                            )
                        )
                    curr_findings_list = [Finding(**f) if isinstance(f, dict) else f for f in session_state.get("findings", [])]
                    curr_kinds = {f.kind for f in curr_findings_list}
                    for f in extracted_f:
                        if f.kind not in curr_kinds:
                            curr_findings_list.append(f)
                            curr_kinds.add(f.kind)
                    session_state["findings"] = [asdict(f) for f in curr_findings_list]

        elif (target_slot == "is_fasting_today" or current_slot == "is_fasting_today") and yn_res.get("value") not in ("yes", "no"):
            if any(k in lower_ans for k in ["roza", "fasting", "fast"]):
                yn_res = {"value": "yes", "evidence": clean_answer, "partial": False}

        elif (target_slot == "sick_vomiting_diarrhea" or current_slot == "sick_vomiting_diarrhea") and yn_res.get("value") not in ("yes", "no"):
            if any(k in lower_ans for k in ["ulti", "dast", "vomit", "diarrhea"]):
                yn_res = {"value": "yes", "evidence": clean_answer, "partial": False}

        is_adh_slot = (
            current_slot in ("adherence_diabetes", "adherence_hypertension", "diabetes_adherence", "hypertension_adherence")
            or (bank_item and bank_item.slot in ("adherence_diabetes", "adherence_hypertension"))
        )

        # G-02: Adherence clarification flow
        if is_adh_slot and session_state.get("awaiting_adherence_clarification") == current_slot:
            session_state["awaiting_adherence_clarification"] = None
            if is_unclear_adherence_answer(eff_answer):
                known_slots[target_slot] = "unclear"
                known_slots[f"{target_slot}__evidence"] = clean_answer
                known_slots[f"{target_slot}__partial"] = False
                session_state["needs_clinician_flag"] = True
                session_state.setdefault("patient_notes", []).append("Medication adherence answer was unclear after clarification. Flagged for review.")
            else:
                yn_clarified = parse_yes_no(clean_answer, lang=lang)
                if yn_clarified["value"] == "yes":
                    known_slots[target_slot] = True
                    known_slots[f"{target_slot}__evidence"] = clean_answer
                elif yn_clarified["value"] == "no":
                    known_slots[target_slot] = False
                    known_slots[f"{target_slot}__evidence"] = clean_answer
                else:
                    known_slots[target_slot] = "unclear"
                    known_slots[f"{target_slot}__evidence"] = clean_answer
                    session_state["needs_clinician_flag"] = True
                    session_state.setdefault("patient_notes", []).append("Medication adherence answer was unclear after clarification. Flagged for review.")
        elif is_adh_slot:
            if is_unclear_adherence_answer(eff_answer):
                session_state["awaiting_adherence_clarification"] = current_slot
                session_state["current_question"] = get_message("adherence_clarification_question", lang)
                session_state["why_text"] = get_message("adherence_clarification_why", lang)
                session_state["options"] = ["yes", "no"]
                session_state["option_items"] = [
                    {"value": "yes", "label": "ہاں" if lang == "ur" else ("haan" if lang == "roman_ur" else "yes")},
                    {"value": "no", "label": "نہیں" if lang == "ur" else ("nahi" if lang == "roman_ur" else "no")},
                ]
                return session_state
            else:
                yn_res = parse_yes_no(eff_answer, lang=lang)
                if yn_res["value"] == "yes":
                    known_slots[target_slot] = True
                elif yn_res["value"] == "no":
                    known_slots[target_slot] = False
                else:
                    known_slots[target_slot] = "unclear"
                    session_state["needs_clinician_flag"] = True
                known_slots[f"{target_slot}__evidence"] = yn_res.get("evidence", clean_answer)
                known_slots[f"{target_slot}__partial"] = yn_res.get("partial", False)
        # B3: Safety-class item answered unknown -> re-ask ONCE with clarification
        elif bank_item and bank_item.priority_class == "safety" and yn_res.get("value") == "unknown":
            # P2-4: If opening free-text message with multi-intent readings arrived on first turn,
            # do not trigger safety clarify; handle as slot extraction and ask safety item normally.
            is_opening_free_text = (
                (len(session_state.get("asked_slots", [])) <= 1 and session_state.get("turn_count", 0) <= 1)
                and (readings or any(k in known_slots for k in ("glucose_reading", "bp_reading", "adherence", "adherence_diabetes")))
                and step_counts.get(current_slot, 0) < 2
            )
            if is_opening_free_text and session_state.get("safety_clarify_slot") != current_slot:
                known_slots["greeting"] = True
                session_state["step"] = bank_item.slot or bank_item.id
                session_state["current_question"] = _get_localized_text(bank_item, lang)
                session_state["why_text"] = _get_localized_why_text(bank_item, lang)
                session_state["options"] = bank_item.choices
                session_state["option_items"] = _build_option_items(bank_item, lang)
                session_state["can_skip"] = False
                session_state["can_say_unknown"] = True
                return session_state

            if session_state.get("safety_clarify_slot") == current_slot or step_counts.get(current_slot, 0) >= 2:
                # Second time unknown -> keep unknown, set needs_clinician_flag, move on
                session_state["safety_clarify_slot"] = None
                known_slots[current_slot] = "unknown"
                known_slots[f"{current_slot}__evidence"] = yn_res["evidence"]
                known_slots[f"{current_slot}__partial"] = yn_res["partial"]
                session_state["needs_clinician_flag"] = True
                session_state.setdefault("patient_notes", []).append(
                    f"Safety question '{current_slot}' remained unknown after clarification. Flagged for clinician review."
                )
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
    if current_findings:
        known_slots.pop("symptoms_denied", None)

    # R8: Summary Confirmation & Correction Loop
    if current_slot == "summary_confirmation":
        yn_res = parse_yes_no(eff_answer, lang=lang)
        lower_raw = clean_answer.lower()
        is_confirm_intent = (
            yn_res.get("value") in (True, "yes")
            or any(w in lower_raw for w in ["confirm", "submit", "all good", "correct", "theek", "theek hai", "ji haan", "done", "haan", "tasdeeq", "ٹھیک", "صحیح", "ہاں", "تصدیق"])
        )
        is_change_intent = (
            not is_confirm_intent and (
                yn_res.get("value") in (False, "no")
                or any(w in lower_raw for w in ["change", "tabdeel", "galat", "wrong", "need to change", "edit", "nahi"])
            )
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
        question_text = _build_dual_summary_text(known_slots, lang, asked_slots=asked_slots, session_state=session_state)
        why_text = get_message("summary_confirm_why", lang)
        options = [
            get_message("summary_confirm_option_submit", lang),
            get_message("summary_confirm_option_change", lang),
        ]
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

    # Loop guard: ensure planner target has not already reached max attempts
    attempts = 0
    while decision.action not in ("finish", "summary_confirm") and step_counts.get(decision.target_slot, 0) >= 2 and attempts < 10:
        attempts += 1
        if decision.target_slot not in asked_slots:
            asked_slots.append(decision.target_slot)
        from agents.interview_planner import SLOT_EQUIVALENCES
        for eq in SLOT_EQUIVALENCES.get(decision.target_slot, set()):
            if eq not in asked_slots:
                asked_slots.append(eq)
        decision = plan_next_step(
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
        question_text = _build_dual_summary_text(known_slots, lang, asked_slots=asked_slots, session_state=session_state)
        why_text = get_message("summary_confirm_why", lang)
        options = [
            get_message("summary_confirm_option_submit", lang),
            get_message("summary_confirm_option_change", lang),
        ]
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

    # P0-2: Turn-end severe low sugar check
    low_eval = evaluate_severe_low_sugar(
        text=eff_answer,
        session_state=session_state,
        current_readings=session_state.get("readings"),
        current_question=session_state.get("current_question"),
        current_step=session_state.get("step"),
        lang=lang,
    )
    if low_eval.get("is_emergency"):
        session_state["emergency"] = True
        session_state["emergency_reason"] = low_eval["emergency_reason"]
        session_state["completed"] = True
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
        session_state["system_note"] = get_message("emergency_red_flag_note", lang)
        from agents.danger_wordgroups import get_safety_note
        session_state["safety_note"] = get_safety_note(lang)
        session_state["triage"] = low_eval.get("triage_dict")
        return session_state
    elif low_eval.get("needs_low_guidance"):
        session_state["safety_note"] = low_eval["guidance"]
        session_state["system_note"] = low_eval["guidance"]

    return session_state


def finish_v3_session(session_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the v3 session into canonical checkin intake structures
    for downstream reconciliation, verification, and clinical safety review.
    """
    conditions = session_state.get("conditions_on_file", ["diabetes"])
    readings_dict = session_state.get("readings", {})
    raw_answers = session_state.get("raw_answers", {})
    known_slots = session_state.get("known_slots", {})
    lang = session_state.get("language") or "en"
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

        # Rule R8: symptom reported evaluation
        cond_symptom_reported = False
        if cond_symptoms:
            for s in cond_symptoms:
                from agents.adaptive_interview_agent import _looks_affirmative
                if parse_yes_no(str(s), lang=lang).get("value") == "yes" or _looks_affirmative(str(s)) is True:
                    cond_symptom_reported = True
                    break
        for sk in ("hyperglycemia_symptoms", "associated_symptoms", "foot_problems", "sick_vomiting_diarrhea"):
            if known_slots.get(sk) is True:
                cond_symptom_reported = True
                break
        if session_state.get("findings"):
            cond_symptom_reported = True

        cond_requires_review = bool(
            session_state.get("possible_severe_low")
            or (not cond_readings and cond_symptom_reported)
            or (cond_readings and session_state.get("needs_clinician_flag"))
            or known_slots.get("adherence_diabetes") == "unclear"
            or known_slots.get("adherence_hypertension") == "unclear"
        )

        intakes.append({
            "condition": cond,
            "level": "review" if cond_requires_review else "routine",
            "readings": cond_readings,
            "symptoms": cond_symptoms,
            "notes": cond_notes,
            "emergency": session_state.get("emergency", False),
            "emergency_reason": session_state.get("emergency_reason"),
            "confidence": confidence,
            "answered_by": answered_by,
            "requires_review": cond_requires_review,
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
