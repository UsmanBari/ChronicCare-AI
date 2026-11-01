from __future__ import annotations
from typing import TypedDict, Optional, List, Dict, Any


class CheckinState(TypedDict, total=False):
    """
    Typed state schema for check-in completion orchestrator (LangGraph & direct).
    
    Invariant:
    `trace` step entries must NOT log patient names, dates, or reading values.
    Only step names, counts, and levels (e.g. "reconcile: 2 obs, 1 med", "triage: urgent").
    """
    checkin_id: str
    user_id: str
    record_patient_id: str
    mode: str
    status: str
    interview_engine: str  # "v2" or "v3"
    intakes: list
    interview_state: dict
    protocol_state: Optional[dict]
    med_state: Optional[dict]
    is_emergency: bool
    emergency_reason: Optional[str]
    prior_bundle: Optional[dict]
    checkin_bundle: Optional[dict]
    reconciliation: Optional[dict]
    verification: Optional[dict]
    triage_result: Optional[dict]
    triage_level: Optional[str]
    requires_review: bool
    max_severity: str
    error: Optional[str]
    trace: List[str]  # names of steps visited, in order

