"""
Deterministic Interview Planner (Interview Engine v3).

Pure function:
    plan_next_step(
        known_slots: Dict[str, Any],
        findings: List[Finding],
        patient_record: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        bank: QuestionBank,
        budget: int = 8,
        hard_cap: int = 14
    ) -> PlanDecision

Prioritization Order:
1. Safety Priority Class (urgent symptom flags, hypo checks, acute sick day)
2. Contradicted Slots (e.g. record vs answer mismatch needing gentle clarification)
3. Probes for Newest Finding (up to 2 follow-ups per finding)
4. Historical Trend Triggers (rising BP, recurrent hypoglycemia, repeated missed doses, adherence barriers)
5. Access Barriers (glucometer/cuff availability, affordability, ran out of medicines)
6. Remaining Open Clinical Slots (readings, technique, lifestyle, free text)
7. Wellbeing Screens (optional mood / distress questions)
8. Summary and Confirmation (final review before completion)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from agents.interview_bank.loader import BankItem, QuestionBank
from agents.interview_findings import Finding, get_next_probe_for_finding


@dataclass
class PlanDecision:
    action: str  # "ask_bank_item", "ask_probe", "ask_clarification", "summary_confirm", "finish"
    item: Optional[BankItem] = None
    probe: Optional[Dict[str, Any]] = None
    clarification_slot: Optional[str] = None
    reason: str = ""
    question_count: int = 0
    max_budget: int = 8
    target_slot: Optional[str] = None


def detect_historical_trends(recent_checkins: List[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Analyzes up to the last 7 check-ins for clinical trends:
    - rising_bp: systolic readings steadily increasing or elevated in >= 2 recent sessions
    - recurrent_lows: >= 2 low glucose readings (< 70 mg/dL) in past 7 check-ins
    - repeated_missed_doses: >= 2 missed dose reports in past 7 check-ins
    - checkin_gap: gaps > 3 days between recent check-ins
    """
    trends = {
        "rising_bp": False,
        "recurrent_lows": False,
        "repeated_missed_doses": False,
        "checkin_gap": False,
    }
    if not recent_checkins:
        return trends

    # 1. Glucose lows count
    low_count = 0
    missed_count = 0
    sys_readings = []

    for c in recent_checkins[:7]:
        intakes = c.get("intakes") or []
        for it in intakes:
            # Check glucose
            for r in it.get("readings", []):
                if r.get("observation_type") == "glucose":
                    val = float(r.get("value", 0))
                    if 0 < val < 70:
                        low_count += 1
                elif r.get("observation_type") == "blood_pressure_systolic":
                    sys_val = float(r.get("value", 0))
                    if sys_val > 0:
                        sys_readings.append(sys_val)
            if it.get("adherence") is False:
                missed_count += 1

    if low_count >= 2:
        trends["recurrent_lows"] = True
    if missed_count >= 2:
        trends["repeated_missed_doses"] = True

    # Rising BP check: if last 3 systolic readings are increasing or >= 140
    if len(sys_readings) >= 3:
        if sys_readings[0] > sys_readings[1] > sys_readings[2] or (sys_readings[0] >= 140 and sys_readings[1] >= 140):
            trends["rising_bp"] = True

    return trends




SLOT_EQUIVALENCES: Dict[str, Set[str]] = {
    "glucose_reading": {"diabetes_glucose_reading", "glucose_reading"},
    "diabetes_glucose_reading": {"diabetes_glucose_reading", "glucose_reading"},
    "bp_reading": {"hypertension_bp_reading", "bp_reading"},
    "hypertension_bp_reading": {"hypertension_bp_reading", "bp_reading"},
    "glucose_context": {"diabetes_glucose_context", "glucose_context"},
    "diabetes_glucose_context": {"diabetes_glucose_context", "glucose_context"},
    "bp_technique": {"hypertension_bp_technique", "bp_technique"},
    "hypertension_bp_technique": {"hypertension_bp_technique", "bp_technique"},
    "hyperglycemia_symptoms": {"diabetes_hyperglycemia_symptoms", "hyperglycemia_symptoms"},
    "diabetes_hyperglycemia_symptoms": {"diabetes_hyperglycemia_symptoms", "hyperglycemia_symptoms"},
    "associated_symptoms": {"hypertension_associated_symptoms", "associated_symptoms"},
    "hypertension_associated_symptoms": {"hypertension_associated_symptoms", "associated_symptoms"},
    "foot_problems": {"diabetes_foot_problems", "foot_problems"},
    "diabetes_foot_problems": {"diabetes_foot_problems", "foot_problems"},
    "adherence_diabetes": {"diabetes_adherence", "adherence_diabetes", "adherence_all", "adherence"},
    "diabetes_adherence": {"diabetes_adherence", "adherence_diabetes", "adherence_all", "adherence"},
    "adherence_hypertension": {"hypertension_adherence", "adherence_hypertension", "adherence_all", "adherence"},
    "hypertension_adherence": {"hypertension_adherence", "adherence_hypertension", "adherence_all", "adherence"},
    "missed_doses_reason_diabetes": {"diabetes_missed_doses_reason", "missed_doses_reason_diabetes"},
    "missed_doses_reason_hypertension": {"hypertension_missed_doses_reason", "missed_doses_reason_hypertension"},
    "lifestyle_diabetes": {"diabetes_lifestyle", "lifestyle_diabetes"},
    "lifestyle_hypertension": {"hypertension_lifestyle", "lifestyle_hypertension"},
    "hypo_symptoms_acute": {"insulin_hypo_symptoms_acute", "hypo_symptoms_acute"},
    "hypo_events_past_week": {"insulin_hypo_events_past_week", "hypo_events_past_week"},
    "fasting_symptoms": {"fasting_symptoms", "fasting_ramadan"},
}


def is_slot_already_satisfied(
    slot: str,
    asked_slots: Set[str],
    known_slots: Dict[str, Any],
    bank: QuestionBank,
) -> bool:
    """
    R3/R6 Centralized De-duplication Guard.
    A slot is already satisfied if:
    1. It (or any equivalent alias) has been asked directly (in asked_slots), OR
    2. Any bank item whose also_fills includes this slot has already been asked or populated.
    Note: asked_slots contains set(asked_slots) | set(known_slots.keys()) in plan_next_step.
    """
    eq_slots = SLOT_EQUIVALENCES.get(slot, {slot})
    if any(s in asked_slots for s in eq_slots):
        return True

    for it in bank.all_items():
        if it.also_fills and slot in it.also_fills:
            if it.slot in asked_slots or it.id in asked_slots:
                return True
    return False


def get_dual_readings_order(
    recent_checkins: List[Dict[str, Any]],
    patient_record: Dict[str, Any],
) -> List[str]:
    """
    R2: Determines reading presentation order for dual-diagnosis patients.
    If recent history shows one condition was abnormal more recently,
    ask that reading first; otherwise default to glucose first.
    """
    bp_abnormal = False
    glucose_abnormal = False

    if recent_checkins:
        for it in (recent_checkins[0].get("intakes") or []):
            for r in it.get("readings", []):
                obs_t = r.get("observation_type")
                val = float(r.get("value", 0))
                if obs_t == "blood_pressure_systolic" and (val >= 140 or (0 < val < 90)):
                    bp_abnormal = True
                elif obs_t == "blood_pressure_diastolic" and (val >= 90 or (0 < val < 60)):
                    bp_abnormal = True
                elif obs_t == "glucose" and (0 < val < 70 or val >= 180):
                    glucose_abnormal = True

    if bp_abnormal and not glucose_abnormal:
        return ["hypertension_bp_reading", "diabetes_glucose_reading"]
    return ["diabetes_glucose_reading", "hypertension_bp_reading"]

def plan_next_step(
    known_slots: Dict[str, Any],
    findings: List[Finding],
    patient_record: Dict[str, Any],
    recent_checkins: Optional[List[Dict[str, Any]]] = None,
    bank: Optional[QuestionBank] = None,
    asked_slots: Optional[Set[str]] = None,
    contradictions: Optional[List[Dict[str, Any]]] = None,
    base_budget: int = 8,
    hard_cap: int = 14,
) -> PlanDecision:
    """
    Pure deterministic planner selecting the next clinical question.
    """
    from agents.interview_bank.loader import get_default_bank
    if bank is None:
        bank = get_default_bank()

    clean_known = {k for k in known_slots.keys() if not k.endswith("__evidence") and not k.endswith("__partial")}
    if asked_slots is None:
        asked_slots = clean_known
    else:
        asked_slots = set(asked_slots) | clean_known

    if recent_checkins is None:
        recent_checkins = []

    # Dynamic budget expansion: if patient reported concerning symptoms or elevated readings, expand budget up to 12
    concerning = False
    if findings:
        for f in findings:
            if f.kind in ("dizziness", "headache", "breathlessness", "foot_problem", "low_sugar_episode", "nausea_or_vomiting"):
                concerning = True
                break

    bp_val = known_slots.get("bp_reading")
    if isinstance(bp_val, (list, tuple)) and len(bp_val) >= 1 and bp_val[0] >= 140:
        concerning = True

    gluc_val = known_slots.get("glucose_reading")
    if isinstance(gluc_val, (int, float)) and (gluc_val < 70 or gluc_val >= 250):
        concerning = True

    effective_budget = min(12 if concerning else base_budget, hard_cap)
    current_count = len([
        s for s in asked_slots 
        if not s.startswith("probe_") 
        and not s.endswith("__evidence") 
        and not s.endswith("__partial") 
        and s != "summary_confirmation"
    ])

    # Hard cap check
    if current_count >= effective_budget:
        if "summary_confirmation" not in asked_slots:
            sum_item = bank.get_by_id("core_summary_confirm")
            return PlanDecision(
                action="summary_confirm",
                item=sum_item,
                reason="budget_reached_requesting_confirmation",
                question_count=current_count,
                max_budget=effective_budget,
                target_slot="summary_confirmation",
            )
        return PlanDecision(
            action="finish",
            reason="budget_and_confirmation_complete",
            question_count=current_count,
            max_budget=effective_budget,
        )

    # 1. PRIORITY CLASS: Safety
    # Check safety items whose conditions are met and not yet asked
    conditions = set(patient_record.get("conditions", []))
    on_insulin = bool(patient_record.get("on_insulin_or_sulfonylurea", False))
    trends = detect_historical_trends(recent_checkins)

    gluc_val = known_slots.get("glucose_reading")
    bp_val = known_slots.get("bp_reading")

    for item in bank.all_items():
        if item.priority_class == "safety" and item.slot not in asked_slots:
            eq_s = SLOT_EQUIVALENCES.get(item.slot, {item.slot})
            if any(s in asked_slots for s in eq_s):
                continue
            req = item.requires
            if req.get("condition") and req["condition"] not in conditions:
                continue
            if req.get("on_insulin_or_sulfonylurea") and not on_insulin and not trends["recurrent_lows"]:
                continue
            if req.get("is_fasting_today") is True and known_slots.get("is_fasting_today") is not True:
                continue
            if req.get("sick_vomiting_diarrhea") is True and known_slots.get("sick_vomiting_diarrhea") is not True:
                continue

            # Clinical Branching: obey glucose reading if known
            if gluc_val is not None and isinstance(gluc_val, (int, float)):
                if gluc_val >= 180 and item.slot in ("hypo_symptoms_acute", "hypo_events_past_week", "hypo_recovery_food"):
                    continue
                if gluc_val < 70 and item.slot == "hyperglycemia_symptoms":
                    continue

            return PlanDecision(
                action="ask_bank_item",
                item=item,
                reason=f"safety_priority_{item.slot}",
                question_count=current_count + 1,
                max_budget=effective_budget,
                target_slot=item.slot,
            )

    # 2. PRIORITY CLASS: Contradictions
    if contradictions:
        for contra in contradictions:
            slot = contra.get("slot")
            if slot and not is_slot_already_satisfied(slot, asked_slots, known_slots, bank):
                return PlanDecision(
                    action="ask_clarification",
                    clarification_slot=slot,
                    reason=f"contradiction_clarification_{slot}",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=slot,
                )

    # 3. PRIORITY CLASS: Probes for Newest Finding (drill-down)
    if findings:
        for finding in reversed(findings):
            probe = get_next_probe_for_finding(finding, bank.get_probes(), max_probes=2)
            if probe:
                probe_slot = probe.get("slot")
                # R6: Probes drill into newest finding but never repeat an asked/satisfied slot
                if probe_slot and not is_slot_already_satisfied(probe_slot, asked_slots, known_slots, bank):
                    return PlanDecision(
                        action="ask_probe",
                        probe=probe,
                        reason=f"drill_down_probe_{finding.kind}_{probe_slot}",
                        question_count=current_count + 1,
                        max_budget=effective_budget,
                        target_slot=probe_slot,
                    )

    # 4. PRIORITY CLASS: Historical Trends
    if trends["recurrent_lows"] and not is_slot_already_satisfied("hypo_events_past_week", asked_slots, known_slots, bank):
        if gluc_val is None or (isinstance(gluc_val, (int, float)) and gluc_val < 180):
            item = bank.get_by_id("insulin_hypo_events_past_week")
            if item:
                return PlanDecision(
                    action="ask_bank_item",
                    item=item,
                    reason="trend_trigger_recurrent_hypoglycemia",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=item.slot,
                )

    if trends["rising_bp"] and not is_slot_already_satisfied("bp_technique", asked_slots, known_slots, bank) and known_slots.get("bp_reading"):
        item = bank.get_by_id("hypertension_bp_technique")
        if item:
            return PlanDecision(
                action="ask_bank_item",
                item=item,
                reason="trend_trigger_rising_bp_technique_check",
                question_count=current_count + 1,
                max_budget=effective_budget,
                target_slot=item.slot,
            )

    if trends["repeated_missed_doses"]:
        for bar_id in ("barrier_affordability_meds", "barrier_ran_out_meds", "barrier_side_effects"):
            item = bank.get_by_id(bar_id)
            if item and not is_slot_already_satisfied(item.slot, asked_slots, known_slots, bank):
                return PlanDecision(
                    action="ask_bank_item",
                    item=item,
                    reason="trend_trigger_repeated_missed_doses_barrier_check",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=item.slot,
                )

    # 5. PRIORITY CLASS: Access Barriers
    if known_slots.get("missing_reading"):
        if "diabetes" in conditions and not is_slot_already_satisfied("has_glucometer", asked_slots, known_slots, bank):
            item = bank.get_by_id("barrier_has_glucometer")
            if item:
                return PlanDecision(
                    action="ask_bank_item",
                    item=item,
                    reason="missing_glucose_reading_device_barrier_check",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=item.slot,
                )
        if "hypertension" in conditions and not is_slot_already_satisfied("has_bp_cuff", asked_slots, known_slots, bank):
            item = bank.get_by_id("barrier_has_bp_cuff")
            if item:
                return PlanDecision(
                    action="ask_bank_item",
                    item=item,
                    reason="missing_bp_reading_device_barrier_check",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=item.slot,
                )

    # 6. PRIORITY CLASS: Remaining Open Clinical Slots
    # Order: Core Greeting -> Readings -> Symptoms -> Adherence -> Missed Doses -> Lifestyle -> Patient Free Text
    standard_order = [
        "core_greeting",
        "diabetes_glucose_reading",
        "diabetes_glucose_context",
        "hypertension_bp_reading",
        "hypertension_bp_technique",
        "diabetes_hyperglycemia_symptoms",
        "diabetes_foot_problems",
        "hypertension_associated_symptoms",
        "hypertension_otc_meds_bp",
        "diabetes_adherence",
        "hypertension_adherence",
        "diabetes_missed_doses_reason",
        "hypertension_missed_doses_reason",
        "diabetes_lifestyle",
        "hypertension_lifestyle",
        "fasting_is_fasting",
        "core_patient_free_text",
    ]

    # R2 Dual Diagnosis Reading Priority: If both conditions are on file and greeting has been asked,
    # ask BOTH readings before any symptom question.
    is_dual_diagnosis = ("diabetes" in conditions and "hypertension" in conditions)
    if is_dual_diagnosis and "greeting" in asked_slots:
        dual_order = get_dual_readings_order(recent_checkins, patient_record)
        for r_item_id in dual_order:
            r_item = bank.get_by_id(r_item_id)
            if r_item and not is_slot_already_satisfied(r_item.slot, asked_slots, known_slots, bank):
                return PlanDecision(
                    action="ask_bank_item",
                    item=r_item,
                    reason=f"dual_diagnosis_reading_priority_{r_item.slot}",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=r_item.slot,
                )

    # Hypoglycemia Active Branching (< 70 mg/dL):
    # If glucose is low, prioritize acute hypo symptom check and recovery food before high sugar symptoms
    if gluc_val is not None and isinstance(gluc_val, (int, float)) and gluc_val < 70 and "diabetes" in conditions:
        if not is_slot_already_satisfied("hypo_symptoms_acute", asked_slots, known_slots, bank):
            h_item = bank.get_by_id("insulin_hypo_symptoms_acute")
            if h_item:
                return PlanDecision(
                    action="ask_bank_item",
                    item=h_item,
                    reason="hypo_reading_acute_symptoms_check",
                    question_count=current_count + 1,
                    max_budget=effective_budget,
                    target_slot=h_item.slot,
                )

    for item_id in standard_order:
        item = bank.get_by_id(item_id)
        if not item:
            continue

        # Centralized De-duplication Guard (R3/R6): check if slot is already satisfied
        if is_slot_already_satisfied(item.slot, asked_slots, known_slots, bank):
            continue

        req = item.requires
        if req.get("condition") and req["condition"] not in conditions:
            continue
        if req.get("has_glucose_reading") and not known_slots.get("glucose_reading"):
            continue
        if req.get("has_bp_reading") and not known_slots.get("bp_reading"):
            continue
        if req.get("bp_elevated"):
            bp_r = known_slots.get("bp_reading")
            if not (isinstance(bp_r, (list, tuple)) and len(bp_r) >= 2 and (bp_r[0] >= 140 or bp_r[1] >= 90)):
                continue
        if req.get("adherence_diabetes") is False and known_slots.get("adherence_diabetes") is not False:
            continue
        if req.get("adherence_hypertension") is False and known_slots.get("adherence_hypertension") is not False:
            continue

        # Condition Isolation:
        if "diabetes" not in conditions and item.slot in (
            "glucose_reading", "glucose_context", "hyperglycemia_symptoms", "foot_problems",
            "adherence_diabetes", "missed_doses_reason_diabetes", "lifestyle_diabetes",
            "hypo_symptoms_acute", "hypo_events_past_week", "hypo_recovery_food"
        ):
            continue

        if "hypertension" not in conditions and item.slot in (
            "bp_reading", "bp_technique", "associated_symptoms", "otc_meds_bp",
            "adherence_hypertension", "missed_doses_reason_hypertension", "lifestyle_hypertension"
        ):
            continue

        # Clinical Reading Branching:
        if gluc_val is not None and isinstance(gluc_val, (int, float)):
            # Hypo (< 70): Never ask hyperglycemia symptoms!
            if gluc_val < 70 and item.slot == "hyperglycemia_symptoms":
                continue
            # Hyper (>= 250): Never ask acute hypo questions!
            if gluc_val >= 250 and item.slot in ("hypo_symptoms_acute", "hypo_events_past_week", "hypo_recovery_food"):
                continue

        if bp_val is not None and isinstance(bp_val, (list, tuple)) and len(bp_val) >= 2:
            sys_bp, dia_bp = bp_val[0], bp_val[1]
            # Hypotension (< 90/60): Never ask high BP symptoms or OTC meds!
            if (sys_bp < 90 or dia_bp < 60) and item.slot in ("associated_symptoms", "otc_meds_bp"):
                continue

        # Dual Diagnosis Lifestyle Deduplication: ask lifestyle once
        if is_dual_diagnosis:
            if item.slot == "lifestyle_hypertension" and is_slot_already_satisfied("lifestyle_diabetes", asked_slots, known_slots, bank):
                continue
            if item.slot == "lifestyle_diabetes" and is_slot_already_satisfied("lifestyle_hypertension", asked_slots, known_slots, bank):
                continue

        return PlanDecision(
            action="ask_bank_item",
            item=item,
            reason=f"standard_open_slot_{item.slot}",
            question_count=current_count + 1,
            max_budget=effective_budget,
            target_slot=item.slot,
        )

    # 7. PRIORITY CLASS: Wellbeing (optional, if room in budget)
    for w_id in ("wellbeing_depressed_mood", "wellbeing_little_interest", "wellbeing_overwhelmed"):
        item = bank.get_by_id(w_id)
        if item and not is_slot_already_satisfied(item.slot, asked_slots, known_slots, bank):
            return PlanDecision(
                action="ask_bank_item",
                item=item,
                reason="optional_wellbeing_screen",
                question_count=current_count + 1,
                max_budget=effective_budget,
                target_slot=item.slot,
            )
            return PlanDecision(
                action="ask_bank_item",
                item=item,
                reason="optional_wellbeing_screen",
                question_count=current_count + 1,
                max_budget=effective_budget,
                target_slot=item.slot,
            )

    # 8. Summary & Confirmation
    if "summary_confirmation" not in asked_slots:
        sum_item = bank.get_by_id("core_summary_confirm")
        return PlanDecision(
            action="summary_confirm",
            item=sum_item,
            reason="interview_complete_requesting_confirmation",
            question_count=current_count,
            max_budget=effective_budget,
            target_slot="summary_confirmation",
        )

    return PlanDecision(
        action="finish",
        reason="all_slots_and_confirmation_complete",
        question_count=current_count,
        max_budget=effective_budget,
    )
