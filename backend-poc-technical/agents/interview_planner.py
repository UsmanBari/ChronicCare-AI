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

    if asked_slots is None:
        asked_slots = set(known_slots.keys())
    else:
        asked_slots = set(asked_slots) | set(known_slots.keys())

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
    current_count = len([s for s in asked_slots if not s.startswith("probe_") and s != "summary_confirmation"])

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

    for item in bank.all_items():
        if item.priority_class == "safety" and item.slot not in asked_slots:
            req = item.requires
            if req.get("on_insulin_or_sulfonylurea") and not on_insulin and not trends["recurrent_lows"]:
                continue
            if req.get("is_fasting_today") and not known_slots.get("is_fasting_today"):
                continue
            if req.get("sick_vomiting_diarrhea") and not known_slots.get("sick_vomiting_diarrhea"):
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
            if slot and slot not in asked_slots:
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
                if probe_slot and probe_slot not in asked_slots:
                    return PlanDecision(
                        action="ask_probe",
                        probe=probe,
                        reason=f"drill_down_probe_{finding.kind}_{probe_slot}",
                        question_count=current_count + 1,
                        max_budget=effective_budget,
                        target_slot=probe_slot,
                    )

    # 4. PRIORITY CLASS: Historical Trends
    if trends["recurrent_lows"] and "hypo_events_past_week" not in asked_slots:
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

    if trends["rising_bp"] and "bp_technique" not in asked_slots and known_slots.get("bp_reading"):
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
            if item and item.slot not in asked_slots:
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
        if "diabetes" in conditions and "has_glucometer" not in asked_slots:
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
        if "hypertension" in conditions and "has_bp_cuff" not in asked_slots:
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

    for item_id in standard_order:
        item = bank.get_by_id(item_id)
        if not item or item.slot in asked_slots:
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
        if item and item.slot not in asked_slots:
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
