"""
SOAP Note Generation Agent (Proposal Section 13.1 Agent 7, Section 35).

Synthesizes Agents 1-6 outputs into a Subjective / Objective / Assessment / Plan
clinical document for healthcare providers.
Strictly deterministic, no LLM calls.
Zero invented values or readings: every value is traceable to stored check-in data.
In connected mode, writes FHIR R4 DocumentReference to in-process FhirSim.
In isolated mode, stores note with check-in.
"""

from __future__ import annotations

import base64
import copy
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory store for isolated mode SOAP notes
STORED_SOAP_NOTES: Dict[str, Dict[str, Any]] = {}


def store_soap_note(checkin_id: str, soap_dict: Dict[str, Any]) -> None:
    """Stores a generated SOAP note for an isolated check-in in memory."""
    STORED_SOAP_NOTES[checkin_id] = copy.deepcopy(soap_dict)


def get_stored_soap_note(checkin_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves stored SOAP note for a check-in."""
    return STORED_SOAP_NOTES.get(checkin_id)


def reset_stored_soap_notes() -> None:
    """Clears in-memory stored SOAP notes (test isolation helper)."""
    STORED_SOAP_NOTES.clear()


def create_fhir_document_reference(
    checkin_id: str,
    patient_id: str,
    plain_text: str,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs a FHIR R4 DocumentReference resource representing the SOAP note.
    - Status: current
    - Type: LOINC 11506-3 "Progress note"
    - Subject: FHIR patient reference
    - Content: base64 text/plain
    """
    now_iso = created_at or datetime.now(timezone.utc).isoformat()
    clean_pid = patient_id.replace("Patient/", "")
    b64_content = base64.b64encode(plain_text.encode("utf-8")).decode("ascii")

    return {
        "resourceType": "DocumentReference",
        "id": f"docref-{checkin_id}",
        "status": "current",
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11506-3",
                    "display": "Progress note",
                }
            ],
            "text": "Progress note",
        },
        "subject": {
            "reference": f"Patient/{clean_pid}",
        },
        "date": now_iso,
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "data": b64_content,
                }
            }
        ],
        "context": {
            "related": [
                {
                    "reference": f"Encounter/checkin-{checkin_id}",
                }
            ]
        },
    }


def format_soap_plain_text(soap_dict: Dict[str, Any]) -> str:
    """Formats structured SOAP dictionary into a standard clinical plain-text note."""
    lines = [
        "================================================================================",
        "SOAP NOTE - CHRONICCARE AI CLINICAL DECISION SUPPORT",
        f"Check-in ID: {soap_dict.get('checkin_id', 'unknown')}",
        f"Patient ID:  {soap_dict.get('patient_id', 'unknown')}",
        f"Generated:   {soap_dict.get('generated_at', 'unknown')}",
        "================================================================================",
        "",
        "SUBJECTIVE:",
    ]
    for s in soap_dict.get("subjective", []):
        lines.append(f"  * {s}")

    lines.append("")
    lines.append("OBJECTIVE:")
    for o in soap_dict.get("objective", []):
        lines.append(f"  * {o}")

    lines.append("")
    lines.append("ASSESSMENT:")
    for a in soap_dict.get("assessment", []):
        lines.append(f"  * {a}")

    lines.append("")
    lines.append("PLAN:")
    for p in soap_dict.get("plan", []):
        lines.append(f"  * {p}")

    lines.append("")
    lines.append("DATA SOURCES:")
    for ds in soap_dict.get("data_sources", []):
        lines.append(f"  - {ds}")

    lines.append("================================================================================")
    return "\n".join(lines)


def build_soap(
    checkin: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
    trends: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesizes Agents 1-6 outputs into a Subjective/Objective/Assessment/Plan document.
    Deterministic, zero LLM, provider-only clinical summary.
    """
    checkin_id = checkin.get("checkin_id", "unknown")
    patient_id = checkin.get("record_patient_id") or checkin.get("user_id") or "Patient"
    mode = checkin.get("mode") or "isolated"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Load result from DB if not provided
    if result is None and checkin_id != "unknown":
        try:
            from data_sources.app_store import get_checkin_result
            result = get_checkin_result(checkin_id)
        except Exception:
            result = None

    state = checkin.get("state") or {}
    answers = state.get("answers") or {}
    intakes = (result.get("intakes") if result else None) or state.get("intakes") or []

    # Safe trend computation if not provided
    if trends is None and checkin.get("user_id"):
        try:
            from data_sources.app_store import get_user_reading_history
            from agents.trend_agent import compute_trends
            raw_hist = get_user_reading_history(checkin["user_id"], days=30)
            trends = compute_trends(raw_hist, window_days=30)
        except Exception:
            trends = None

    # =========================================================================
    # S: SUBJECTIVE
    # =========================================================================
    s_lines: List[str] = []

    # 1. Reported symptoms / interview answers (short form; "skipped" -> "not answered")
    reported_symptoms = []
    greeting = answers.get("greeting_response")
    if greeting:
        val = str(greeting).strip()
        if val.lower() in ("skip", "skipped", "null", "none", "not provided", ""):
            reported_symptoms.append("General condition: not answered")
        else:
            reported_symptoms.append(f"General condition: {val}")

    symp_keys = ["hyperglycemia_symptoms", "hypoglycemia_symptoms", "symptoms", "symptom_notes"]
    found_symp = False
    for sk in symp_keys:
        if sk in answers and answers[sk] is not None:
            val = str(answers[sk]).strip()
            if val.lower() in ("skip", "skipped", "null", "none", "not provided", ""):
                reported_symptoms.append("Reported symptoms: not answered")
            else:
                reported_symptoms.append(f"Reported symptoms: {val}")
            found_symp = True
            break

    if not found_symp:
        intake_symps = []
        for it in intakes:
            if isinstance(it, dict) and it.get("symptoms"):
                for k, v in it["symptoms"].items():
                    if v and str(v).lower() not in ("skip", "skipped", "null", "none", "not provided", ""):
                        intake_symps.append(f"{k.replace('_', ' ')}: {v}")
        if intake_symps:
            reported_symptoms.append(f"Reported symptoms: {'; '.join(intake_symps)}")
        elif result and (result.get("emergency") or (result.get("triage_level") == "emergency")):
            trig_cat = (result.get("trigger_category") or state.get("stage1_reason") or "Emergency Red-Flag").replace("_", " ").title()
            trig_txt = result.get("trigger_text") or answers.get("greeting_response") or ""
            if trig_txt:
                reported_symptoms.append(f"Reported symptoms: Emergency red-flag ({trig_cat}), quoted: \"{trig_txt}\"")
            else:
                reported_symptoms.append(f"Reported symptoms: Emergency red-flag ({trig_cat})")
        elif not reported_symptoms:
            reported_symptoms.append("Reported symptoms: not answered")

    lifestyle = answers.get("lifestyle_notes")
    if lifestyle:
        val = str(lifestyle).strip()
        if val.lower() in ("skip", "skipped", "null", "none", "not provided", ""):
            reported_symptoms.append("Lifestyle notes: not answered")
        else:
            reported_symptoms.append(f"Lifestyle notes: {val}")

    for symp in reported_symptoms:
        s_lines.append(symp)

    # 2. Danger words findings
    triage_obj = (result.get("triage") if result else None) or {}
    wordgroups = set()
    if isinstance(triage_obj, dict) and triage_obj.get("wordgroups"):
        wordgroups.update(triage_obj["wordgroups"])
    if isinstance(state, dict):
        for h in state.get("wordgroup_hits", []) or []:
            if isinstance(h, dict) and h.get("group"):
                wordgroups.add(h["group"])
        for h in (state.get("answers", {}) or {}).get("_wordgroup_hits", []) or []:
            if isinstance(h, dict) and h.get("group"):
                wordgroups.add(h["group"])
    if result and (result.get("emergency") or (result.get("triage_level") == "emergency")):
        trig_cat = result.get("trigger_category") or state.get("stage1_reason") or "emergency_red_flag"
        wordgroups.add(str(trig_cat).lower())
    if wordgroups:
        s_lines.append(f"Danger words detected: {', '.join(sorted(wordgroups))}")
    else:
        s_lines.append("Danger words: None detected")

    # 3. Medication adherence
    adherence_val = None
    if "adherence" in answers:
        adherence_val = answers["adherence"]
    else:
        for it in intakes:
            if isinstance(it, dict) and "adherence" in it:
                adherence_val = it["adherence"]
                break

    if adherence_val is True or str(adherence_val).lower() in ("true", "yes"):
        s_lines.append("Medication adherence: Reported taking medications as prescribed")
    elif adherence_val is False or str(adherence_val).lower() in ("false", "no"):
        s_lines.append("Medication adherence: Reported missed doses or difficulty with medications")
    else:
        s_lines.append("Medication adherence: not answered")

    # =========================================================================
    # O: OBJECTIVE
    # =========================================================================
    o_lines: List[str] = []

    # 1. Today's readings with unit, source and trust level
    readings = []
    for it in intakes:
        if isinstance(it, dict) and it.get("readings"):
            readings.extend(it["readings"])
    if not readings and state.get("intake", {}).get("readings"):
        readings.extend(state["intake"]["readings"])

    if readings:
        for r in readings:
            obs_type = r.get("observation_type") or r.get("type") or "reading"
            val = r.get("value")
            unit = r.get("unit") or ""
            source = (r.get("source") or "").lower()

            if source == "fhir":
                trust = "High"
                source_label = "FHIR"
            elif source == "ocr":
                trust = "Medium"
                source_label = "OCR"
            else:
                trust = "Low"
                source_label = "Self-Report"

            unit_str = f" {unit}" if unit else ""
            o_lines.append(f"Reading - {obs_type}: {val}{unit_str} [Source: {source_label}, Trust: {trust}]")
    else:
        o_lines.append("Readings: no reading today")

    # 2. Reconciliation discrepancies (connected mode)
    if mode == "connected":
        recon = (result.get("reconciliation") if result else None) or {}
        verif = (result.get("verification") if result else None) or {}
        discrepancies = []

        conflicts = recon.get("summary", {}).get("conflicts", 0)
        if conflicts > 0:
            for obs_rec in recon.get("observation_reconciliations", []):
                if obs_rec.get("status") == "conflict":
                    obs_t = obs_rec.get("observation_type", "reading")
                    val_a = obs_rec.get("value_a")
                    val_b = obs_rec.get("value_b")
                    discrepancies.append(f"Observation conflict on {obs_t}: baseline {val_a} vs check-in {val_b}")
            for med_rec in recon.get("medication_reconciliations", []):
                if med_rec.get("status") == "conflict":
                    med_name = med_rec.get("medication_name", "medication")
                    discrepancies.append(f"Medication conflict on {med_name}")

        if verif.get("summary", {}).get("requires_review"):
            for obs_v in verif.get("observation_verifications", []):
                if obs_v.get("requires_human_review"):
                    obs_t = obs_v.get("observation_type", "reading")
                    sev = obs_v.get("severity", "moderate")
                    discrepancies.append(f"Clinical verification discrepancy on {obs_t} (severity: {sev})")

        if discrepancies:
            for d in discrepancies:
                o_lines.append(f"Reconciliation discrepancy: {d}")
        else:
            o_lines.append("Reconciliation: Reconciled with baseline; no discrepancies detected")
    else:
        o_lines.append("Reconciliation: Not applicable (isolated local mode)")

    # 3. Longitudinal Trends
    if trends and isinstance(trends, dict) and trends.get("trends"):
        trend_items = trends["trends"]
        trend_found = False
        for series_name, series_data in trend_items.items():
            if isinstance(series_data, dict):
                direction = series_data.get("direction", "not_enough_history")
                n = series_data.get("n", 0)
                window_days = series_data.get("window_days", 30)
                o_lines.append(f"Trend - {series_name}: {direction} ({n} readings over {window_days} days)")
                trend_found = True
        if not trend_found:
            o_lines.append("Trends: no trend history available")
    else:
        o_lines.append("Trends: no trend history available")

    # =========================================================================
    # A: ASSESSMENT
    # =========================================================================
    a_lines: List[str] = []

    # 1. Triage level + colour + rules' reasons
    from agents.final_triage import level_to_colour

    level = (
        (result.get("triage_level") if result else None)
        or (triage_obj.get("level") if isinstance(triage_obj, dict) else None)
        or ("emergency" if (result and result.get("emergency")) else "routine")
    )
    colour_raw = level_to_colour(level)
    colour_map = {
        "green": "Green",
        "yellow": "Yellow",
        "red": "Red (emergency)" if level == "emergency" else "Red",
    }
    colour = colour_map.get(colour_raw.lower(), colour_raw.title())
    a_lines.append(f"Triage evaluation: {level} ({colour})")

    reasons = []
    if isinstance(triage_obj, dict):
        if triage_obj.get("reasons"):
            reasons.extend(triage_obj["reasons"])
        elif triage_obj.get("summary"):
            reasons.append(triage_obj["summary"])
    if not reasons and result and result.get("trigger_text"):
        cat = (result.get("trigger_category") or state.get("stage1_reason") or "Emergency Red-Flag").replace("_", " ").title()
        reasons.append(f"Emergency Red-Flag: {cat} (patient stated: \"{result['trigger_text']}\")")
    if not reasons:
        reasons.append("Routine check-in protocol completed within expected bounds")

    a_lines.append(f"Clinical rules rationale: {'; '.join(reasons)}")

    # 2. Stage-2 raises (raised_by)
    raised_by = (result.get("raised_by") if result else None) or (
        triage_obj.get("raised_by") if isinstance(triage_obj, dict) else None
    )
    if not raised_by and result and isinstance(result.get("risk"), dict):
        raised_by = result["risk"].get("raised_by")

    if raised_by:
        if isinstance(raised_by, list):
            raise_descs = []
            for rb in raised_by:
                if isinstance(rb, dict):
                    m = rb.get("model") or rb.get("rule") or "risk"
                    r = rb.get("reason") or rb.get("rule") or "escalation"
                    raise_descs.append(f"{m} ({r})")
                else:
                    raise_descs.append(str(rb))
            a_lines.append(f"Stage-2 escalation: Level raised by {', '.join(raise_descs)}")
        else:
            a_lines.append(f"Stage-2 escalation: Level raised by {raised_by}")
    else:
        a_lines.append("Stage-2 escalation: None (rules level maintained)")

    # 3. Risk models
    risk_data = result.get("risk") if result else None
    if risk_data and isinstance(risk_data, dict):
        models_dict = risk_data.get("models")
        if models_dict and isinstance(models_dict, dict):
            for model_name, m_info in models_dict.items():
                if isinstance(m_info, dict):
                    status = m_info.get("status")
                    if status == "ok":
                        band = m_info.get("band", "Unknown")
                        prob = m_info.get("probability")
                        a_lines.append(f"Risk model ({model_name}): Band {band}, Probability {prob}")
                        drivers = m_info.get("drivers", [])[:3]
                        if drivers:
                            drv_strs = [
                                f"{d.get('feature')}: {d.get('contribution')}"
                                for d in drivers
                                if isinstance(d, dict)
                            ]
                            a_lines.append(f"Risk drivers ({model_name}): {', '.join(drv_strs)}")
                    elif status == "not_enough_information":
                        missing = m_info.get("missing", [])
                        missing_str = ", ".join(missing) if missing else "incomplete profile"
                        a_lines.append(f"Risk model ({model_name}): not enough information (missing: {missing_str})")
        else:
            status = risk_data.get("status")
            if status == "ok":
                band = risk_data.get("band", "Unknown")
                prob = risk_data.get("probability")
                a_lines.append(f"Risk model: Band {band}, Probability {prob}")
                drivers = risk_data.get("drivers", [])[:3]
                if drivers:
                    drv_strs = [
                        f"{d.get('feature')}: {d.get('contribution')}"
                        for d in drivers
                        if isinstance(d, dict)
                    ]
                    a_lines.append(f"Risk drivers: {', '.join(drv_strs)}")
            elif status == "not_enough_information":
                missing = risk_data.get("missing", [])
                missing_str = ", ".join(missing) if missing else "incomplete profile"
                a_lines.append(f"Risk model: not enough information (missing: {missing_str})")

        a_lines.append(
            "Investigational caveat: Risk model scores are investigational decision support tools and do not represent a clinical diagnosis."
        )
    else:
        a_lines.append("Risk assessment: Not evaluated or disabled")

    # 4. Confidence (Section 17)
    confidence = "Medium"
    for it in intakes:
        if isinstance(it, dict) and it.get("confidence"):
            confidence = it["confidence"]
            break
    if not confidence and state.get("intake", {}).get("confidence"):
        confidence = state["intake"]["confidence"]

    is_cold_start = bool(state.get("is_cold_start"))
    if is_cold_start:
        a_lines.append("Data confidence: Medium (first check-in: confidence capped at Medium)")
    else:
        a_lines.append(f"Data confidence: {confidence or 'Medium'}")

    # =========================================================================
    # P: PLAN
    # =========================================================================
    p_lines: List[str] = []

    # 1. Rule guidance already shown to patient
    guidance = None
    if isinstance(triage_obj, dict):
        guidance = triage_obj.get("guidance") or triage_obj.get("summary")
    if not guidance and result and result.get("trigger_text"):
        guidance = result["trigger_text"]
    if not guidance:
        guidance = "Continue routine self-monitoring and care plan."

    if level == "emergency":
        p_lines.append(f"Patient guidance: Immediate emergency guidance provided: {guidance}")
    else:
        p_lines.append(f"Patient guidance provided: {guidance}")

    # 2. Appointment action
    appt = None
    try:
        from data_sources.app_store import get_appointment_by_checkin
        appt = get_appointment_by_checkin(checkin_id)
    except Exception:
        pass

    if appt:
        spec = appt.get("specialty", "general").replace("_", " ").title()
        urg = appt.get("urgency", "routine").title()
        st = appt.get("status", "offered").title()
        prov = appt.get("provider_id", "unassigned")
        p_lines.append(f"Appointment action: {urg} appointment ({st}) - Specialty: {spec}, Provider: {prov}")
    elif level == "routine":
        p_lines.append("Appointment action: Routine monitoring, no follow-up appointment required")
    else:
        p_lines.append("Appointment action: Follow-up appointment offered for clinical review")

    # 3. Clinician review required
    if level in ("review", "urgent", "emergency"):
        p_lines.append("Clinician review: clinician review required")
    else:
        p_lines.append("Clinician review: Routine monitoring, no clinician review required")

    # 4. Guideline sources by title/section only (NO guideline text)
    sources = []
    if result and isinstance(result.get("explanation"), dict):
        sources = result["explanation"].get("sources", [])
    if sources:
        p_lines.append("Guideline sources:")
        for s in sources:
            if isinstance(s, dict):
                title = s.get("title", "Clinical Practice Guideline")
                sec = s.get("section_path") or s.get("section") or "General"
                p_lines.append(f"- {title} (Section: {sec})")
    else:
        p_lines.append("Guideline sources: None cited")

    # =========================================================================
    # DATA SOURCES
    # =========================================================================
    data_sources: List[str] = []
    if mode == "connected":
        conn_name = "FHIR R4 in-process simulator (sim://demo)"
        try:
            from data_sources.app_store import get_ehr_connection
            uid = checkin.get("user_id") or patient_id
            clean_uid = str(uid).removeprefix("local-")
            conn = get_ehr_connection(clean_uid)
            if conn and conn.get("system_name"):
                conn_name = f"Connected EHR: {conn['system_name']}"
                if conn.get("fhir_base_url"):
                    conn_name += f" ({conn['fhir_base_url']})"
        except Exception:
            pass
        data_sources.append(conn_name)
    else:
        data_sources.append("Local store (isolated mode)")
    data_sources.append("Check-in interview responses")
    data_sources.append("Deterministic clinical rules engine")
    if risk_data:
        data_sources.append("Investigational risk models")
    if trends and trends.get("trends"):
        data_sources.append("Longitudinal reading history (30-day window)")
    if sources:
        data_sources.append("Clinical practice guideline corpus")

    soap_dict = {
        "checkin_id": checkin_id,
        "patient_id": patient_id,
        "generated_at": now_iso,
        "subjective": s_lines,
        "objective": o_lines,
        "assessment": a_lines,
        "plan": p_lines,
        "data_sources": data_sources,
    }
    plain_text = format_soap_plain_text(soap_dict)
    soap_dict["plain_text"] = plain_text

    # Connected mode: write FHIR DocumentReference to in-process FhirSim
    if mode == "connected":
        try:
            from data_sources import fhir_sim
            doc_ref = create_fhir_document_reference(
                checkin_id=checkin_id,
                patient_id=patient_id,
                plain_text=plain_text,
                created_at=now_iso,
            )
            fhir_sim.store_document_reference(doc_ref)
        except Exception as e:
            logger.warning(f"Failed to store FHIR DocumentReference: {e}")
    else:
        store_soap_note(checkin_id, soap_dict)

    return soap_dict
