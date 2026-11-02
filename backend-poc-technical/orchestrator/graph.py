from __future__ import annotations

import os
import time
from typing import Dict, Any, Optional, Tuple, Literal
from langgraph.graph import StateGraph, START, END

from data_sources.app_store import _utc_now_iso
from orchestrator.state import CheckinState
from orchestrator.steps import (
    CheckinCompleteResponse,
    step_parse_and_validate_intake,
    step_fetch_prior_bundle,
    step_build_bundles,
    step_reconcile,
    step_verify,
    step_persist_local_observations,
    step_decide_triage,
    step_risk,
    step_explain,
    step_persist_and_respond,
)


def _make_trace_step(node: str, start_iso: str, start_time: float, summary: str) -> Dict[str, Any]:
    """
    Appends a structured trace step adhering to invariant U6-04:
    Contains ONLY node name, timestamps, elapsed ms, and aggregate counts/levels.
    Never patient names, dates of birth, or clinical reading values.
    """
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "node": node,
        "started_at": start_iso,
        "ms": elapsed_ms,
        "summary": summary,
    }


def node_intake(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    user = state["user"]
    record_label = state.get("record_label") or ""

    parsed_context, early_resp = step_parse_and_validate_intake(checkin, user, record_label)
    trace = list(state.get("trace") or [])

    if early_resp is not None:
        intake_count = len(early_resp.intakes or [])
        trace.append(_make_trace_step(
            node="node_intake",
            start_iso=start_iso,
            start_time=t0,
            summary=f"intake validated; {intake_count} intakes, emergency=True",
        ))
        return {
            "emergency": True,
            "result": early_resp,
            "triage": early_resp.triage,
            "trace": trace,
        }

    st = parsed_context["state"]
    intake_count = len(st.intakes or [])
    trace.append(_make_trace_step(
        node="node_intake",
        start_iso=start_iso,
        start_time=t0,
        summary=f"intake validated; {intake_count} intakes, emergency=False",
    ))
    return {
        "emergency": False,
        "parsed_context": parsed_context,
        "trace": trace,
    }


def route_after_intake(state: CheckinState) -> Literal["persist", "fetch_prior"]:
    if state.get("emergency"):
        return "persist"
    return "fetch_prior"


def node_fetch_prior(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    user = state["user"]
    mode = state.get("mode") or checkin.get("mode", "isolated")

    prior_bundle = step_fetch_prior_bundle(
        record_patient_id=checkin["record_patient_id"],
        mode=mode,
        user_id=user["user_id"],
    )

    obs_count = len(prior_bundle.get("observations") or [])
    med_count = len(prior_bundle.get("medications") or [])
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_fetch_prior",
        start_iso=start_iso,
        start_time=t0,
        summary=f"prior bundle fetched; {obs_count} obs, {med_count} meds",
    ))

    bundles = dict(state.get("bundles") or {})
    bundles["prior_bundle"] = prior_bundle
    return {
        "bundles": bundles,
        "trace": trace,
    }


def node_build_bundles(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    user = state["user"]
    mode = state.get("mode") or checkin.get("mode", "isolated")
    parsed_context = state["parsed_context"]
    interview_st = parsed_context["state"]
    med_st = parsed_context.get("med_state")
    prior_bundle = state["bundles"]["prior_bundle"]

    patient_name = user.get("display_name") or (prior_bundle["patient"].name if prior_bundle.get("patient") else "Patient")

    prior_bundle, checkin_bundle = step_build_bundles(
        state=interview_st,
        prior_bundle=prior_bundle,
        mode=mode,
        patient_name=patient_name,
        med_state=med_st,
        record_patient_id=checkin["record_patient_id"],
    )

    obs_count = len(checkin_bundle.get("observations") or [])
    med_count = len(checkin_bundle.get("medications") or [])
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_build_bundles",
        start_iso=start_iso,
        start_time=t0,
        summary=f"bundles built; {obs_count} obs, {med_count} meds",
    ))

    bundles = dict(state.get("bundles") or {})
    bundles["prior_bundle"] = prior_bundle
    bundles["checkin_bundle"] = checkin_bundle
    return {
        "bundles": bundles,
        "trace": trace,
    }


def node_reconcile(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    bundles = state["bundles"]
    prior_bundle = bundles["prior_bundle"]
    checkin_bundle = bundles["checkin_bundle"]

    recon_res = step_reconcile(prior_bundle, checkin_bundle)

    obs_compared = len(recon_res.observation_comparisons)
    meds_compared = len(recon_res.medication_comparisons)
    conflicts_count = recon_res.summary.get("conflict", 0)
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_reconcile",
        start_iso=start_iso,
        start_time=t0,
        summary=f"reconciled; {obs_compared} obs compared, {meds_compared} meds compared, {conflicts_count} conflicts",
    ))

    return {
        "recon_result": recon_res,
        "trace": trace,
    }


def node_verify(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    mode = state.get("mode") or checkin.get("mode", "isolated")
    recon_res = state["recon_result"]
    checkin_bundle = state["bundles"]["checkin_bundle"]
    med_st = state["parsed_context"].get("med_state")

    verif_res = step_verify(
        recon_result=recon_res,
        checkin_bundle=checkin_bundle,
        med_state=med_st,
        mode=mode,
        record_patient_id=checkin["record_patient_id"],
    )

    req_review_count = verif_res.summary.get("requires_review", 0)
    conflict_count = verif_res.summary.get("conflict", 0)
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_verify",
        start_iso=start_iso,
        start_time=t0,
        summary=f"verified; requires_review={req_review_count}, conflicts={conflict_count}",
    ))

    return {
        "verif_result": verif_res,
        "trace": trace,
    }


def route_after_verify(state: CheckinState) -> Literal["persist_local", "decide_triage"]:
    mode = state.get("mode") or state["checkin"].get("mode", "isolated")
    if mode == "isolated":
        return "persist_local"
    return "decide_triage"


def node_persist_local(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    mode = state.get("mode") or checkin.get("mode", "isolated")
    checkin_bundle = state["bundles"]["checkin_bundle"]

    step_persist_local_observations(
        checkin_bundle=checkin_bundle,
        record_patient_id=checkin["record_patient_id"],
        mode=mode,
    )

    obs_count = len(checkin_bundle.get("observations") or [])
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_persist_local",
        start_iso=start_iso,
        start_time=t0,
        summary=f"local observations persisted; {obs_count} obs",
    ))

    return {
        "trace": trace,
    }


def node_decide_triage(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    user = state["user"]
    verif_res = state["verif_result"]
    parsed_context = state["parsed_context"]
    interview_st = parsed_context["state"]
    proto_st = parsed_context.get("protocol_state")

    triage_dec = step_decide_triage(
        verif_result=verif_res,
        state=interview_st,
        protocol_state=proto_st,
        user_id=user["user_id"],
    )

    final_lvl = triage_dec["final_triage_level"]
    req_rev = triage_dec["final_requires_review"]
    trace = list(state.get("trace") or [])
    trace.append(_make_trace_step(
        node="node_decide_triage",
        start_iso=start_iso,
        start_time=t0,
        summary=f"triage decided; level={final_lvl}, requires_review={req_rev}",
    ))

    return {
        "triage_decision": triage_dec,
        "triage": triage_dec.get("triage_dict"),
        "trace": trace,
    }


def node_risk(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    user = state["user"]
    parsed_context = state["parsed_context"]
    interview_st = parsed_context["state"]
    triage_dec = state["triage_decision"]
    trace = list(state.get("trace") or [])

    risk_res = step_risk(
        user_id=user["user_id"],
        state=interview_st,
        triage_decision=triage_dec,
        trace=trace,
    )

    band_str = risk_res.get("band") if risk_res else "none"
    raised_bool = risk_res.get("raised", False) if risk_res else False
    status_str = risk_res.get("status", "skipped") if risk_res else "skipped"
    trace.append(_make_trace_step(
        node="node_risk",
        start_iso=start_iso,
        start_time=t0,
        summary=f"risk assessed; status={status_str}, band={band_str}, raised={raised_bool}",
    ))

    return {
        "risk": risk_res,
        "triage_decision": triage_dec,
        "triage": triage_dec.get("triage_dict"),
        "trace": trace,
    }


def node_explain(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    user = state["user"]
    parsed_context = state["parsed_context"]
    interview_st = parsed_context["state"]
    triage_dec = state["triage_decision"]
    trace = list(state.get("trace") or [])

    explain_res = step_explain(
        user_id=user["user_id"],
        state=interview_st,
        triage_decision=triage_dec,
        trace=trace,
    )

    mode_str = explain_res.get("mode") if explain_res else "skipped"
    status_str = explain_res.get("status", "ok") if explain_res else "skipped"
    trace.append(_make_trace_step(
        node="node_explain",
        start_iso=start_iso,
        start_time=t0,
        summary=f"explanation generated; status={status_str}, mode={mode_str}",
    ))

    return {
        "explanation": explain_res,
        "trace": trace,
    }


def node_persist(state: CheckinState) -> Dict[str, Any]:
    t0 = time.perf_counter()
    start_iso = _utc_now_iso()
    checkin = state["checkin"]
    checkin_id = checkin["checkin_id"]
    record_label = state.get("record_label") or ""
    trace = list(state.get("trace") or [])

    if state.get("emergency"):
        trace.append(_make_trace_step(
            node="node_persist",
            start_iso=start_iso,
            start_time=t0,
            summary="emergency persisted; level=emergency",
        ))
        return {
            "trace": trace,
        }

    final_lvl = state["triage_decision"]["final_triage_level"]
    trace.append(_make_trace_step(
        node="node_persist",
        start_iso=start_iso,
        start_time=t0,
        summary=f"persisted checkin result; level={final_lvl}, status=complete",
    ))

    parsed_context = state["parsed_context"]
    resp = step_persist_and_respond(
        checkin_id=checkin_id,
        state=parsed_context["state"],
        recon_result=state["recon_result"],
        verif_result=state["verif_result"],
        triage_decision=state["triage_decision"],
        med_state=parsed_context.get("med_state"),
        protocol_state=parsed_context.get("protocol_state"),
        record_label=record_label,
        risk=state.get("risk"),
        explanation=state.get("explanation"),
        trace=trace,
    )

    return {
        "result": resp,
        "trace": trace,
    }


def build_checkin_completion_graph():
    """
    Constructs and compiles the StateGraph for check-in completion.
    Pure in-memory execution, zero checkpointer, zero LLM, compiled once at import.
    """
    builder = StateGraph(CheckinState)

    builder.add_node("intake", node_intake)
    builder.add_node("fetch_prior", node_fetch_prior)
    builder.add_node("build_bundles", node_build_bundles)
    builder.add_node("reconcile", node_reconcile)
    builder.add_node("verify", node_verify)
    builder.add_node("persist_local", node_persist_local)
    builder.add_node("decide_triage", node_decide_triage)
    builder.add_node("risk", node_risk)
    builder.add_node("explain", node_explain)
    builder.add_node("persist", node_persist)

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "persist": "persist",
            "fetch_prior": "fetch_prior",
        },
    )
    builder.add_edge("fetch_prior", "build_bundles")
    builder.add_edge("build_bundles", "reconcile")
    builder.add_edge("reconcile", "verify")
    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "persist_local": "persist_local",
            "decide_triage": "decide_triage",
        },
    )
    builder.add_edge("persist_local", "decide_triage")
    builder.add_edge("decide_triage", "risk")
    builder.add_edge("risk", "explain")
    builder.add_edge("explain", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


# Compiled once at import time
checkin_graph = build_checkin_completion_graph()


def run_checkin_graph(
    checkin: Dict[str, Any],
    user: Dict[str, Any],
    record_label: str,
) -> CheckinCompleteResponse:
    """
    Executes checkin completion through the compiled LangGraph orchestrator.
    """
    resp, _ = run_checkin_graph_with_state(checkin, user, record_label)
    return resp


def run_checkin_graph_with_state(
    checkin: Dict[str, Any],
    user: Dict[str, Any],
    record_label: str,
) -> Tuple[CheckinCompleteResponse, CheckinState]:
    """
    Executes checkin completion through the compiled LangGraph orchestrator
    and returns both the API response and the final CheckinState (including trace).
    """
    initial_state: CheckinState = {
        "checkin": checkin,
        "user": user,
        "mode": checkin.get("mode", "isolated"),
        "bundles": {},
        "recon_result": None,
        "verif_result": None,
        "triage": None,
        "result": None,
        "emergency": False,
        "trace": [],
        "errors": [],
        "record_label": record_label,
    }

    final_state = checkin_graph.invoke(initial_state)
    return final_state["result"], final_state
