from __future__ import annotations

import os
from typing import Dict, Any, Optional, Tuple, List
from fastapi import HTTPException, status
from pydantic import BaseModel

from data_sources.app_store import (
    get_checkin_result,
    create_checkin_result,
    update_checkin_state,
    get_patient_profile,
    get_active_ehr_connection,
    get_ehr_system_by_id,
    _utc_now_iso,
)
from data_sources.local_store import (
    add_local_observation,
    get_local_observation_origins,
    get_local_medication_origins,
)
from agents.adaptive_interview_agent import (
    InterviewState,
    INTERVIEW_COMPLETE,
    build_checkin_bundle,
    build_checkin_origins,
)
from agents.interview_v3_runner import finish_v3_session
from agents.triage_protocol import (
    evaluate_triggers,
    evaluate_stroke_extras,
    _raise_level,
    TriageProtocolState,
    _decide,
    GLUCOSE,
    SYSTOLIC,
    DIASTOLIC,
)
from agents.medication_confirmation import (
    MedicationCheckState,
    build_medication_origins,
    build_medication_bundle_items,
    restrict_to_asked,
)
from agents.reconciliation_agent import (
    reconcile_bundles,
    ReconciliationResult,
)
from agents.verification_agent import (
    verify_reconciliation,
    VerificationResult,
)
from data_sources.data_source import get_patient_bundle


class CheckinCompleteResponse(BaseModel):
    emergency: bool
    intakes: List[Dict[str, Any]]
    reconciliation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    requires_review: bool
    max_severity: Optional[str] = None
    triage: Optional[Dict[str, Any]] = None
    record_source_label: Optional[str] = None
    answered_by: Optional[str] = None
    risk: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None
    safety_note: Optional[str] = None


def _build_patient_risk_view(risk: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Patient-facing risk view: band + reasons, NO probability."""
    if not risk or not isinstance(risk, dict):
        return None
    if risk.get("status") != "ok":
        return {
            "status": risk.get("status", "unknown"),
            "band": None,
            "reasons": [],
            "advisory": "Advisory risk assessment, not a clinical diagnosis. Consult your healthcare provider.",
        }
    return {
        "status": "ok",
        "band": risk.get("band"),
        "reasons": risk.get("reasons", []),
        "advisory": "Advisory risk assessment, not a clinical diagnosis. Consult your healthcare provider.",
    }


def _build_patient_explain_view(explanation: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Patient-facing explanation view: sentences + sources."""
    if not explanation or not isinstance(explanation, dict):
        return None
    if explanation.get("status") == "error":
        return {
            "status": "error",
            "sentences": [],
            "sources": [],
        }
    return {
        "sentences": explanation.get("sentences", []),
        "sources": explanation.get("sources", []),
    }


def _sanitize_trace_for_persistence(trace: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """Sanitizes trace for deterministic persistence across direct and graph modes."""
    if not trace:
        return None
    return [
        {
            "node": s.get("node", ""),
            "started_at": s.get("started_at", ""),
            "summary": s.get("summary", ""),
        }
        for s in trace
        if isinstance(s, dict)
    ]


def step_check_idempotency(checkin_id: str, record_label: str) -> Optional[CheckinCompleteResponse]:
    """
    Step 1: Idempotency check.
    If a completed check-in result already exists in the store, return it immediately.
    """
    stored_result = get_checkin_result(checkin_id)
    if stored_result:
        return CheckinCompleteResponse(
            emergency=stored_result["emergency"],
            intakes=stored_result["intakes"],
            reconciliation=stored_result.get("reconciliation"),
            verification=stored_result.get("verification"),
            requires_review=stored_result["requires_review"],
            max_severity=stored_result.get("max_severity"),
            triage=stored_result.get("triage"),
            record_source_label=record_label,
            answered_by=stored_result.get("answered_by"),
            risk=_build_patient_risk_view(stored_result.get("risk")),
            explanation=_build_patient_explain_view(stored_result.get("explanation")),
        )
    return None


def step_parse_and_validate_intake(
    checkin: Dict[str, Any],
    current_user: Dict[str, Any],
    record_label: str,
) -> Tuple[Dict[str, Any], Optional[CheckinCompleteResponse]]:
    """
    Step 2: Intake validation and emergency check.
    Validates interview completion or emergency state across both v2 and v3 engines.
    If emergency, persists emergency checkin result + state and returns CheckinCompleteResponse (early return).
    Otherwise returns parsed state context dictionary.
    """
    checkin_id = checkin["checkin_id"]
    raw_state = checkin.get("state") or {}
    is_v3_session = bool(raw_state.get("engine") == "v3" or raw_state.get("completed") is not None)

    if is_v3_session:
        is_completed = bool(raw_state.get("completed"))
        is_emergency = bool(raw_state.get("stage1_red_flag") or raw_state.get("emergency") or checkin["status"] == "emergency")
        if not is_completed and not is_emergency:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interview is not complete",
            )
        if is_emergency:
            emergency_reason = raw_state.get("emergency_reason") or raw_state.get("stage1_reason")
            intakes = raw_state.get("intakes") or ([{"condition": "general", "emergency": True, "reason": emergency_reason}] if emergency_reason else [])
            now_iso = _utc_now_iso()
            create_checkin_result(
                checkin_id=checkin_id,
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                review_status="open",
                trigger_category=emergency_reason or "emergency",
                trigger_text=None,
                escalated_at=now_iso,
                triage_level="emergency",
                triage=None,
            )
            update_checkin_state(
                checkin_id=checkin_id,
                state_dict=raw_state,
                status="emergency",
                completed_at=now_iso,
                med_state_dict=None,
                protocol_state_dict=None,
            )
            answered_by_val = None
            for it in intakes:
                if it.get("answered_by"):
                    answered_by_val = it["answered_by"]
                    break
            # Emergency early return for v3 (reproducing main.py:3373-3383)
            from agents.danger_wordgroups import get_safety_note
            return {}, CheckinCompleteResponse(
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                triage=None,
                record_source_label=record_label,
                answered_by=answered_by_val,
                safety_note=get_safety_note(raw_state.get("language") or "en"),
            )

        v3_summary = finish_v3_session(raw_state)
        intakes = v3_summary.get("intakes", [])
        state = InterviewState(
            patient_id=checkin["record_patient_id"],
            conditions_on_file=raw_state.get("conditions_on_file") or ["diabetes"],
            step=INTERVIEW_COMPLETE,
            intakes=intakes,
        )
        if raw_state.get("wordgroup_hits"):
            state.answers["_wordgroup_hits"] = list(raw_state["wordgroup_hits"])
        readings_map = {}
        for intake_item in intakes:
            for r_item in intake_item.get("readings", []):
                obs_t = r_item.get("observation_type")
                if obs_t == "glucose":
                    readings_map[GLUCOSE] = float(r_item["value"])
                elif obs_t == "blood_pressure_systolic":
                    readings_map[SYSTOLIC] = float(r_item["value"])
                elif obs_t == "blood_pressure_diastolic":
                    readings_map[DIASTOLIC] = float(r_item["value"])

        triggers = evaluate_triggers(readings_map)
        if triggers:
            primary_trig = triggers[0]
            findings = raw_state.get("findings", [])
            finding_labels = {f.get("finding_type") for f in findings if isinstance(f, dict)}

            proto_answers = {
                "dka_symptoms": bool("nausea_or_vomiting" in finding_labels),
                "can_swallow": True,
                "neuro": False,
                "symptoms": bool(finding_labels),
                "recheck": None,
                "substances": False,
                "circumstances": False,
            }
            p_state = TriageProtocolState(
                protocol=primary_trig.protocol,
                age_band="adult",
                trigger_reason=primary_trig.reason,
                readings=readings_map,
                answers=proto_answers,
            )
            p_state.result = _decide(p_state)
            protocol_state = p_state
        else:
            protocol_state = None
        med_state = None

    else:
        state = InterviewState.from_dict(checkin["state"])
        protocol_state_dict = checkin.get("protocol_state")
        protocol_state = TriageProtocolState.from_dict(protocol_state_dict) if protocol_state_dict else None
        med_state_dict = checkin.get("med_state")
        med_state = MedicationCheckState.from_dict(med_state_dict) if med_state_dict else None

        if not state.stage1_red_flag and checkin["status"] != "emergency":
            if state.step != INTERVIEW_COMPLETE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Interview is not complete",
                )
            if protocol_state and not protocol_state.complete:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="triage_incomplete",
                )
            if med_state and not med_state.complete:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="medication_check_incomplete",
                )

        if state.stage1_red_flag or checkin["status"] == "emergency":
            intakes = state.intakes if state.intakes else ([{"condition": state.active_condition or "general", "emergency": True, "reason": state.stage1_reason}] if state.stage1_reason else [])
            now_iso = _utc_now_iso()
            triage_dict = protocol_state.result if (protocol_state and protocol_state.complete) else None
            create_checkin_result(
                checkin_id=checkin_id,
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                review_status="open",
                trigger_category=state.stage1_reason or (f"triage:{protocol_state.protocol}" if protocol_state else None),
                trigger_text=triage_dict.get("summary") if triage_dict else None,
                escalated_at=now_iso,
                triage_level="emergency" if triage_dict else None,
                triage=triage_dict,
            )
            update_checkin_state(
                checkin_id=checkin_id,
                state_dict=state.to_dict(),
                status="emergency",
                completed_at=now_iso,
                med_state_dict=med_state.to_dict() if med_state else None,
                protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
            )
            answered_by_val = None
            for it in intakes:
                if it.get("answered_by"):
                    answered_by_val = it["answered_by"]
                    break
            # Emergency early return for v2 (reproducing main.py:3491-3501)
            from agents.danger_wordgroups import get_safety_note
            return {}, CheckinCompleteResponse(
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                triage=triage_dict,
                record_source_label=record_label,
                answered_by=answered_by_val,
                safety_note=get_safety_note(state.answers.get("language") or "en"),
            )

    return {
        "state": state,
        "protocol_state": protocol_state,
        "med_state": med_state,
        "raw_state": raw_state,
        "is_v3": is_v3_session,
    }, None


def step_fetch_prior_bundle(
    record_patient_id: str,
    mode: str,
    user_id: str,
    get_patient_bundle_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Step 3: EHR / Record source fetch.
    Retrieves baseline bundle from FHIR EHR or local store. Traps exceptions -> HTTP 502.
    """
    if get_patient_bundle_fn is None:
        import sys
        main_mod = sys.modules.get("main")
        if main_mod and hasattr(main_mod, "get_patient_bundle"):
            get_patient_bundle_fn = getattr(main_mod, "get_patient_bundle")
        else:
            get_patient_bundle_fn = get_patient_bundle

    base_url = None
    if mode == "connected":
        active_conn = get_active_ehr_connection(user_id)
        if active_conn:
            ehr_sys = get_ehr_system_by_id(active_conn["ehr_system_id"])
            base_url = ehr_sys["fhir_base_url"] if ehr_sys else None

    try:
        return get_patient_bundle_fn(record_patient_id, mode=mode, base_url=base_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Record source unavailable",
        )


def step_build_bundles(
    state: InterviewState,
    prior_bundle: Dict[str, Any],
    mode: str,
    patient_name: str,
    med_state: Optional[MedicationCheckState],
    record_patient_id: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Step 4: Bundle Assembly.
    Builds checkin bundle and attaches medication items if medication confirmation was performed.
    """
    source = "fhir" if mode == "connected" else "local"
    now_iso = _utc_now_iso()
    try:
        checkin_bundle = build_checkin_bundle(state, source=source, patient_name=patient_name, checkin_timestamp=now_iso)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if med_state and med_state.items:
        checkin_bundle["medications"] = build_medication_bundle_items(
            med_state,
            patient_id=record_patient_id,
            source=source,
            timestamp=now_iso,
        )
        prior_bundle["medications"] = restrict_to_asked(prior_bundle.get("medications", []), med_state)

    return prior_bundle, checkin_bundle


def step_reconcile(
    prior_bundle: Dict[str, Any],
    checkin_bundle: Dict[str, Any],
) -> ReconciliationResult:
    """
    Step 5: Reconciliation.
    Performs deterministic bundle reconciliation. Traps ValueError -> HTTP 400.
    """
    try:
        return reconcile_bundles(prior_bundle, checkin_bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


def step_verify(
    recon_result: ReconciliationResult,
    checkin_bundle: Dict[str, Any],
    med_state: Optional[MedicationCheckState],
    mode: str,
    record_patient_id: str,
) -> VerificationResult:
    """
    Step 6: Verification.
    Verifies reconciliation findings against provenance origins.
    """
    checkin_origins = build_checkin_origins(checkin_bundle)
    if med_state and med_state.items:
        checkin_origins.update(build_medication_origins(checkin_bundle["medications"]))

    if mode == "isolated":
        local_obs_origins = get_local_observation_origins(record_patient_id)
        local_med_origins = get_local_medication_origins(record_patient_id)
        combined_origins = {**local_obs_origins, **local_med_origins, **checkin_origins}
    else:
        combined_origins = checkin_origins

    return verify_reconciliation(recon_result, origins=combined_origins)


def step_persist_local_observations(
    checkin_bundle: Dict[str, Any],
    record_patient_id: str,
    mode: str,
) -> None:
    """
    Step 7: Local Store Write (isolated mode).
    Saves check-in observations tagged self_reported into local SQLite store.
    """
    if mode == "isolated":
        for obs in checkin_bundle.get("observations", []):
            add_local_observation(
                id=obs.source_record_id,
                patient_id=record_patient_id,
                observation_type=obs.observation_type,
                value=obs.value,
                unit=obs.unit,
                timestamp=obs.timestamp,
                source="local",
                origin="self_reported",
            )


def step_decide_triage(
    verif_result: VerificationResult,
    state: InterviewState,
    protocol_state: Optional[TriageProtocolState],
    user_id: str,
    get_patient_profile_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Step 8: Triage decision logic.
    Computes final triage level, review requirements, max severity, review status, and triage dictionary.
    """
    summary = verif_result.summary
    verif_requires_review = bool(summary.get("requires_review", 0) > 0)
    if summary.get("severity_high", 0) > 0:
        verif_max_severity = "high"
    elif summary.get("severity_moderate", 0) > 0:
        verif_max_severity = "moderate"
    elif summary.get("severity_low", 0) > 0:
        verif_max_severity = "low"
    else:
        verif_max_severity = "none"

    intake_requires_review = any(it.get("requires_review") for it in (state.intakes or []))
    if get_patient_profile_fn is None:
        import sys
        main_mod = sys.modules.get("main")
        if main_mod and hasattr(main_mod, "get_patient_profile"):
            get_patient_profile_fn = getattr(main_mod, "get_patient_profile")
        else:
            get_patient_profile_fn = get_patient_profile

    profile = get_patient_profile_fn(user_id) or {}

    if protocol_state and protocol_state.complete:
        triage_res = dict(protocol_state.result)
        if not profile.get("date_of_birth"):
            triage_res["age_assumed"] = True

        proto_level = triage_res.get("level", "routine")
        if verif_requires_review or intake_requires_review:
            final_triage_level = _raise_level(proto_level, "review")
        else:
            final_triage_level = proto_level

        stroke_eval = None
        for it in (state.intakes or []):
            eval_res = evaluate_stroke_extras(it.get("symptoms", {}), patient_profile=profile)
            if eval_res:
                stroke_eval = eval_res
                break
        if stroke_eval:
            final_triage_level = _raise_level(final_triage_level, stroke_eval["level"])
            if stroke_eval.get("advice"):
                triage_res["advice"] = stroke_eval["advice"]
                if stroke_eval["level"] == "urgent":
                    triage_res["guidance"] = stroke_eval["advice"]

        final_requires_review = bool(
            final_triage_level in ("review", "urgent", "emergency")
            or verif_requires_review
            or intake_requires_review
        )

        SEV_ORDER = {"none": 0, "low": 1, "moderate": 2, "high": 3}
        if final_triage_level == "urgent":
            final_max_sev = "high"
        elif final_triage_level == "review":
            if SEV_ORDER.get(verif_max_severity, 0) < SEV_ORDER["moderate"]:
                final_max_sev = "moderate"
            else:
                final_max_sev = verif_max_severity
        else:
            final_max_sev = verif_max_severity

        review_status = "open" if final_requires_review else "resolved"

        from agents.danger_wordgroups import is_danger_wordgroups_enabled
        if is_danger_wordgroups_enabled():
            wordgroup_hits = []
            if hasattr(state, "answers") and isinstance(state.answers, dict) and state.answers.get("_wordgroup_hits"):
                wordgroup_hits.extend(state.answers["_wordgroup_hits"])
            if hasattr(state, "wordgroup_hits") and state.wordgroup_hits:
                wordgroup_hits.extend(state.wordgroup_hits)
            for it in (getattr(state, "intakes", None) or []):
                if isinstance(it, dict) and it.get("wordgroup_hits"):
                    wordgroup_hits.extend(it["wordgroup_hits"])

            if wordgroup_hits:
                final_triage_level = _raise_level(final_triage_level, "review")
                final_requires_review = True
                review_status = "open"
                if final_max_sev == "none":
                    final_max_sev = "moderate"
                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))
                triage_res["wordgroups"] = groups_seen

        return {
            "final_triage_level": final_triage_level,
            "final_requires_review": final_requires_review,
            "final_max_sev": final_max_sev,
            "review_status": review_status,
            "triage_dict": triage_res,
        }
    else:
        stroke_eval = None
        for it in (state.intakes or []):
            eval_res = evaluate_stroke_extras(it.get("symptoms", {}), patient_profile=profile)
            if eval_res:
                stroke_eval = eval_res
                break

        final_requires_review = bool(verif_requires_review or intake_requires_review or (stroke_eval is not None))
        final_triage_level = "review" if final_requires_review else "routine"
        if stroke_eval:
            final_triage_level = _raise_level(final_triage_level, stroke_eval["level"])

        review_status = "open" if final_requires_review else "resolved"
        final_max_sev = "high" if final_triage_level == "urgent" else ("moderate" if (final_requires_review and verif_max_severity == "none") else verif_max_severity)
        if stroke_eval:
            triage_dict = {
                "level": stroke_eval["level"],
                "guidance": stroke_eval.get("advice", "Check-in flagged for clinician review."),
                "advice": stroke_eval.get("advice", "Check-in flagged for clinician review."),
                "summary": stroke_eval.get("advice", "Stroke extras evaluation: clinician review required."),
            }
        elif final_triage_level == "review":
            is_severe_low = any(
                (isinstance(it.get("symptoms"), dict) and it.get("symptoms", {}).get("possible_severe_low"))
                for it in (state.intakes or [])
            )
            guidance = (
                "Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."
                if is_severe_low
                else "Check-in flagged for clinician review."
            )
            triage_dict = {
                "level": "review",
                "guidance": guidance,
                "summary": "Check-in flagged for clinician review.",
            }
        elif final_triage_level == "routine":
            triage_dict = {
                "level": "routine",
                "guidance": "Continue routine self-monitoring and care plan.",
                "summary": "Routine check-in completed.",
            }
        else:
            triage_dict = None

        from agents.danger_wordgroups import is_danger_wordgroups_enabled
        if is_danger_wordgroups_enabled():
            wordgroup_hits = []
            if hasattr(state, "answers") and isinstance(state.answers, dict) and state.answers.get("_wordgroup_hits"):
                wordgroup_hits.extend(state.answers["_wordgroup_hits"])
            if hasattr(state, "wordgroup_hits") and state.wordgroup_hits:
                wordgroup_hits.extend(state.wordgroup_hits)
            for it in (getattr(state, "intakes", None) or []):
                if isinstance(it, dict) and it.get("wordgroup_hits"):
                    wordgroup_hits.extend(it["wordgroup_hits"])

            if wordgroup_hits:
                final_triage_level = _raise_level(final_triage_level, "review")
                final_requires_review = True
                review_status = "open"
                if final_max_sev == "none":
                    final_max_sev = "moderate"
                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))
                if triage_dict is None:
                    triage_dict = {
                        "level": final_triage_level,
                        "guidance": "Check-in flagged for clinician review.",
                        "summary": "Danger word-group detected: clinician review required.",
                        "wordgroups": groups_seen,
                    }
                else:
                    triage_dict["wordgroups"] = groups_seen

        return {
            "final_triage_level": final_triage_level,
            "final_requires_review": final_requires_review,
            "final_max_sev": final_max_sev,
            "review_status": review_status,
            "triage_dict": triage_dict,
        }


def step_risk(
    user_id: str,
    state: InterviewState,
    triage_decision: Dict[str, Any],
    trace: Optional[List[Dict[str, Any]]] = None,
    get_patient_profile_fn: Optional[Any] = None,
    get_reading_history_fn: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Step 9: Diabetes risk assessment (behind RISK_ENABLED flag).
    Runs only if RISK_ENABLED=true and patient has HTN and NOT diabetes.
    If RISK_CAN_RAISE=true, can only escalate routine -> review.
    Fails safely on any error without blocking check-in completion.
    """
    if os.environ.get("RISK_ENABLED", "").strip().lower() != "true":
        return None

    if get_patient_profile_fn is None:
        import sys
        main_mod = sys.modules.get("main")
        if main_mod and hasattr(main_mod, "get_patient_profile"):
            get_patient_profile_fn = getattr(main_mod, "get_patient_profile")
        else:
            from data_sources.app_store import get_patient_profile
            get_patient_profile_fn = get_patient_profile

    if get_reading_history_fn is None:
        from data_sources.app_store import get_user_reading_history
        get_reading_history_fn = get_user_reading_history

    try:
        profile = get_patient_profile_fn(user_id) or {}
        conditions = profile.get("conditions", [])
        from agents.risk_rules import is_risk_applicable, apply_risk_to_level
        if not is_risk_applicable(conditions):
            return None

        from agents.risk_agent import assess as assess_risk
        history = get_reading_history_fn(user_id, days=30) or []

        current_readings = []
        for it in (state.intakes or []):
            for r in it.get("readings", []):
                obs_t = r.get("observation_type")
                val = r.get("value")
                ts = r.get("at") or _utc_now_iso()
                if obs_t in ("blood_pressure_systolic", "blood_pressure_diastolic", "glucose") and val is not None:
                    current_readings.append({
                        "observation_type": obs_t,
                        "value": float(val),
                        "timestamp": ts,
                        "source": "checkin",
                    })
        combined_readings = current_readings + history
        risk_res = assess_risk(profile=profile, latest_readings=combined_readings, conditions=conditions)
        if not risk_res:
            return None

        import copy
        risk_res = copy.deepcopy(risk_res)
        new_level, raised = apply_risk_to_level(triage_decision["final_triage_level"], risk_res)
        risk_res["raised"] = raised

        if raised:
            triage_decision["final_triage_level"] = new_level
            triage_decision["final_requires_review"] = True
            triage_decision["review_status"] = "open"
            if triage_decision.get("triage_dict"):
                triage_decision["triage_dict"]["level"] = new_level
                triage_decision["triage_dict"]["requires_review"] = True
            else:
                triage_decision["triage_dict"] = {
                    "level": "review",
                    "summary": "Check-in flagged for clinician review by risk model.",
                    "guidance": "Check-in flagged for clinician review based on diabetes risk assessment.",
                }
            if triage_decision.get("final_max_sev") in (None, "none", "low"):
                triage_decision["final_max_sev"] = "moderate"

        return risk_res
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Risk step error: %s", type(e).__name__)
        return {"status": "error", "error_type": type(e).__name__}


def step_explain(
    user_id: str,
    state: InterviewState,
    triage_decision: Dict[str, Any],
    trace: Optional[List[Dict[str, Any]]] = None,
    get_patient_profile_fn: Optional[Any] = None,
    store: Optional[Any] = None,
    llm: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Step 10: Grounded clinical guideline explanation (behind EXPLAIN_ENABLED flag).
    Runs only if EXPLAIN_ENABLED=true.
    Fails safely on any error without blocking check-in completion.
    """
    if os.environ.get("EXPLAIN_ENABLED", "").strip().lower() != "true":
        return None

    if get_patient_profile_fn is None:
        import sys
        main_mod = sys.modules.get("main")
        if main_mod and hasattr(main_mod, "get_patient_profile"):
            get_patient_profile_fn = getattr(main_mod, "get_patient_profile")
        else:
            from data_sources.app_store import get_patient_profile
            get_patient_profile_fn = get_patient_profile

    try:
        profile = get_patient_profile_fn(user_id) or {}
        language = profile.get("language", "en")

        readings: Dict[str, Any] = {}
        for it in (state.intakes or []):
            it_readings = it.get("readings")
            if isinstance(it_readings, list):
                for r in it_readings:
                    if isinstance(r, dict):
                        k = r.get("observation_type")
                        v = r.get("value")
                        if k and v is not None:
                            try:
                                readings[k] = float(v)
                            except Exception:
                                readings[k] = v
            elif isinstance(it_readings, dict):
                for k, v in it_readings.items():
                    if v is not None:
                        try:
                            readings[k] = float(v)
                        except Exception:
                            readings[k] = v

        for it in (state.intakes or []):
            for k in ("glucose", "blood_pressure_systolic", "blood_pressure_diastolic", "fasting_glucose", "random_glucose"):
                if k in it and it[k] is not None:
                    try:
                        readings[k] = float(it[k])
                    except Exception:
                        readings[k] = it[k]

        if store is None:
            try:
                from rag.store import get_db_chunk_store
                store = get_db_chunk_store()
            except Exception:
                store = None

        if llm is None:
            try:
                from llm.groq_client import chat as groq_chat, is_configured
                if is_configured():
                    llm = groq_chat
            except Exception:
                llm = None

        import copy
        from rag.explainer import explain
        triage_copy = copy.deepcopy(triage_decision.get("triage_dict") or {"level": triage_decision.get("final_triage_level", "routine")})

        explain_res = explain(
            triage_result=triage_copy,
            readings=readings,
            language=language,
            store=store,
            llm=llm,
        )
        return explain_res
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Explain step error: %s", type(e).__name__)
        return {"status": "error", "error_type": type(e).__name__}


def build_direct_trace(
    state: InterviewState,
    prior_bundle: Dict[str, Any],
    checkin_bundle: Dict[str, Any],
    recon_result: ReconciliationResult,
    verif_result: VerificationResult,
    mode: str,
    triage_decision: Dict[str, Any],
    risk_res: Optional[Dict[str, Any]],
    explain_res: Optional[Dict[str, Any]],
    start_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Constructs the identical trace step sequence in direct mode as LangGraph mode."""
    now_iso = start_iso or _utc_now_iso()
    intake_count = len(state.intakes or [])
    obs_prior = len(prior_bundle.get("observations") or [])
    meds_prior = len(prior_bundle.get("medications") or [])
    obs_checkin = len(checkin_bundle.get("observations") or [])
    meds_checkin = len(checkin_bundle.get("medications") or [])
    obs_comp = len(recon_result.observation_comparisons)
    meds_comp = len(recon_result.medication_comparisons)
    confl = recon_result.summary.get("conflict", 0)
    req_rev_v = verif_result.summary.get("requires_review", 0)
    confl_v = verif_result.summary.get("conflict", 0)
    lvl = triage_decision["final_triage_level"]
    req_rev_f = triage_decision["final_requires_review"]

    trace = [
        {"node": "node_intake", "started_at": now_iso, "summary": f"intake validated; {intake_count} intakes, emergency=False"},
        {"node": "node_fetch_prior", "started_at": now_iso, "summary": f"prior bundle fetched; {obs_prior} obs, {meds_prior} meds"},
        {"node": "node_build_bundles", "started_at": now_iso, "summary": f"bundles built; {obs_checkin} obs, {meds_checkin} meds"},
        {"node": "node_reconcile", "started_at": now_iso, "summary": f"reconciled; {obs_comp} obs compared, {meds_comp} meds compared, {confl} conflicts"},
        {"node": "node_verify", "started_at": now_iso, "summary": f"verified; requires_review={req_rev_v}, conflicts={confl_v}"},
    ]
    if mode == "isolated":
        trace.append({"node": "node_persist_local", "started_at": now_iso, "summary": f"local observations persisted; {obs_checkin} obs"})

    trace.append({"node": "node_decide_triage", "started_at": now_iso, "summary": f"triage decided; level={lvl}, requires_review={req_rev_f}"})

    band_str = risk_res.get("band") if risk_res else "none"
    raised_bool = risk_res.get("raised", False) if risk_res else False
    status_r = risk_res.get("status", "skipped") if risk_res else "skipped"
    trace.append({"node": "node_risk", "started_at": now_iso, "summary": f"risk assessed; status={status_r}, band={band_str}, raised={raised_bool}"})

    mode_str = explain_res.get("mode") if explain_res else "skipped"
    status_e = explain_res.get("status", "ok") if explain_res else "skipped"
    trace.append({"node": "node_explain", "started_at": now_iso, "summary": f"explanation generated; status={status_e}, mode={mode_str}"})

    trace.append({"node": "node_persist", "started_at": now_iso, "summary": f"persisted checkin result; level={lvl}, status=complete"})

    return trace


def step_persist_and_respond(
    checkin_id: str,
    state: InterviewState,
    recon_result: ReconciliationResult,
    verif_result: VerificationResult,
    triage_decision: Dict[str, Any],
    med_state: Optional[MedicationCheckState],
    protocol_state: Optional[TriageProtocolState],
    record_label: str,
    risk: Optional[Dict[str, Any]] = None,
    explanation: Optional[Dict[str, Any]] = None,
    trace: Optional[List[Dict[str, Any]]] = None,
) -> CheckinCompleteResponse:
    """
    Step 9: Database persistence & API response construction.
    Writes checkin result and final completed state to app store and returns CheckinCompleteResponse.
    """
    now_iso = _utc_now_iso()
    final_triage_level = triage_decision["final_triage_level"]
    final_requires_review = triage_decision["final_requires_review"]
    final_max_sev = triage_decision["final_max_sev"]
    review_status = triage_decision["review_status"]
    triage_dict = triage_decision["triage_dict"]

    sanitized_trace = _sanitize_trace_for_persistence(trace)

    create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=state.intakes,
        reconciliation=recon_result.to_dict(),
        verification=verif_result.to_dict(),
        requires_review=final_requires_review,
        max_severity=final_max_sev,
        review_status=review_status,
        triage_level=final_triage_level,
        triage=triage_dict,
        risk=risk,
        explanation=explanation,
        trace=sanitized_trace,
    )
    update_checkin_state(
        checkin_id=checkin_id,
        state_dict=state.to_dict(),
        status="complete",
        completed_at=now_iso,
        med_state_dict=med_state.to_dict() if med_state else None,
        protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
    )

    answered_by_val = None
    for it in (state.intakes or []):
        if it.get("answered_by"):
            answered_by_val = it["answered_by"]
            break

    safety_note_val = None
    from agents.danger_wordgroups import is_danger_wordgroups_enabled, get_safety_note
    if is_danger_wordgroups_enabled() and triage_dict and triage_dict.get("wordgroups"):
        lang = getattr(state, "language", None) or "en"
        safety_note_val = get_safety_note(lang)

    return CheckinCompleteResponse(
        emergency=False,
        intakes=state.intakes,
        reconciliation=recon_result.to_dict(),
        verification=verif_result.to_dict(),
        requires_review=final_requires_review,
        max_severity=final_max_sev,
        triage=triage_dict,
        record_source_label=record_label,
        answered_by=answered_by_val,
        risk=_build_patient_risk_view(risk),
        explanation=_build_patient_explain_view(explanation),
        safety_note=safety_note_val,
    )
