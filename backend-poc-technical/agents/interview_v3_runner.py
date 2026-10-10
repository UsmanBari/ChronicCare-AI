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

from agents.interview_bank.loader import BankItem, get_default_bank
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


def is_v3_engine_enabled() -> bool:
    """Checks if Interview Engine v3 is enabled via environment variable."""
    return os.environ.get("INTERVIEW_ENGINE", "v2").strip().lower() == "v3"


# =============================================================================
# Helper Functions
# =============================================================================
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


def start_v3_session(
    checkin_id: str,
    patient_id: str,
    conditions: List[str],
    on_insulin_or_sulfonylurea: bool = False,
    is_cold_start: bool = False,
    baseline: Optional[Dict[str, Any]] = None,
    language: str = "en",
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

    if decision.item:
        step_id = decision.item.slot
        question_text = _get_localized_text(decision.item, lang)
        why_text = decision.item.why_text
        options = decision.item.choices
        can_skip = (decision.item.priority_class != "safety")
        can_say_unknown = True
    elif decision.probe:
        step_id = decision.probe.get("slot", "probe")
        question_text = _get_localized_text(decision.probe, lang)
        why_text = decision.probe.get("clinical_rationale", "")
        options = decision.probe.get("choices")
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
        session_state["system_note"] = "Emergency red flag detected. Please seek emergency medical care immediately."
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
            session_state["system_note"] = (
                "We understand you may need to step away. We have saved your responses so far for your care team."
                if lang == "en" else system_note
            )
            return session_state

        # Strike rule: 2 consecutive off-topic answers -> offer choices
        if odd_count >= 2:
            session_state["system_note"] = system_note
            session_state["options"] = ["Continue check-in", "Need urgent help", "Finish later"]
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
            session_state["possible_severe_low_guidance"] = (
                "Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, "
                "consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately."
            )
        else:
            # Unanswered / unclear unit: Treat as possible severe low per clinical rule
            readings["glucose"] = float(unclarified_val)
            known_slots["glucose_reading"] = float(unclarified_val)
            session_state["possible_severe_low"] = True
            session_state["possible_severe_low_guidance"] = (
                "Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, "
                "consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately."
            )
            session_state["needs_clinician_flag"] = True

    elif "glucose_reading" in current_slot or current_slot == "diabetes_glucose_reading":
        val_res: ValidationResult = validate_glucose_input(clean_answer)
        if val_res.needs_unit_clarification:
            session_state["awaiting_glucose_unit"] = True
            session_state["raw_unclarified_glucose"] = val_res.value
            session_state["current_question"] = (
                f"Did you mean {val_res.value:g} mmol/L or {val_res.value:g} mg/dL?"
            )
            session_state["why_text"] = "Clarifying unit to ensure patient safety against severe low blood sugar."
            session_state["options"] = ["mmol/L", "mg/dL"]
            return session_state
        elif val_res.valid and val_res.value is not None:
            clean_low = clean_answer.lower()
            has_unit = any(u in clean_low for u in ["mg", "dl", "mmol"])
            if not has_unit and 41.0 <= float(val_res.value) <= 54.0:
                session_state["awaiting_glucose_unit"] = True
                session_state["raw_unclarified_glucose"] = val_res.value
                session_state["current_question"] = (
                    f"Did you mean {val_res.value:g} mmol/L or {val_res.value:g} mg/dL?"
                )
                session_state["why_text"] = "Clarifying unit to ensure patient safety against severe low blood sugar."
                session_state["options"] = ["mmol/L", "mg/dL"]
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
        bp_res: ValidationResult = validate_bp_input(clean_answer)
        if bp_res.valid and bp_res.value is not None:
            readings["blood_pressure_systolic"] = bp_res.value[0]
            readings["blood_pressure_diastolic"] = bp_res.value[1]
            known_slots["bp_reading"] = bp_res.value
        else:
            known_slots["missing_reading"] = True

    # Record slot answer
    raw_answers[current_slot] = clean_answer
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

    # Check for confirmation answering
    if current_slot == "summary_confirmation":
        session_state["completed"] = True
        session_state["step"] = "COMPLETE"
        session_state["current_question"] = None
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

    if decision.item:
        session_state["is_probe"] = False
        step_id = decision.item.slot
        question_text = _get_localized_text(decision.item, lang)
        why_text = decision.item.why_text
        options = decision.item.choices
        can_skip = (decision.item.priority_class != "safety")
        can_say_unknown = True
    elif decision.probe:
        step_id = decision.probe.get("slot", "probe")
        question_text = _get_localized_text(decision.probe, lang)
        why_text = decision.probe.get("clinical_rationale", "")
        options = decision.probe.get("choices")
        can_skip = True
        can_say_unknown = True
        session_state.setdefault("probes_asked", []).append(decision.probe.get("probe_id") or step_id)
        session_state["is_probe"] = True
    elif decision.action == "summary_confirm":
        session_state["is_probe"] = False
        step_id = "summary_confirmation"
        if decision.item:
            question_text = _get_localized_text(decision.item, lang)
            why_text = decision.item.why_text
            options = decision.item.choices
        else:
            question_text = "Thank you. Would you like to confirm and submit your check-in?"
            options = ["Yes, submit", "Need to change something"]

    session_state["step"] = step_id
    session_state["current_question"] = question_text
    session_state["why_text"] = why_text
    session_state["options"] = options
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
    intakes = []

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

        intakes.append({
            "condition": cond,
            "readings": cond_readings,
            "symptoms": cond_symptoms,
            "notes": cond_notes,
            "emergency": session_state.get("emergency", False),
            "emergency_reason": session_state.get("emergency_reason"),
            "confidence": "Low" if session_state.get("ended_early_off_topic") or session_state.get("possible_severe_low") else "High",
        })

    return {
        "checkin_id": session_state.get("checkin_id"),
        "intakes": intakes,
        "emergency": session_state.get("emergency", False),
        "emergency_reason": session_state.get("emergency_reason"),
        "needs_review": session_state.get("needs_clinician_flag", False) or session_state.get("possible_severe_low", False),
        "findings": session_state.get("findings", []),
        "possible_severe_low": session_state.get("possible_severe_low", False),
    }


# Aliases for compatibility
v3_start_session = start_v3_session
v3_next_turn = next_turn
v3_finish = finish_v3_session
