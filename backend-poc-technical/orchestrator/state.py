from __future__ import annotations
from typing import TypedDict, Optional, List, Dict, Any


class CheckinState(TypedDict, total=False):
    """
    Typed state schema for check-in completion orchestrator (LangGraph & direct).

    Invariant (U6-04):
    `trace` step entries must contain counts and levels only.
    NEVER patient names, dates of birth, or reading values.
    """
    checkin: Dict[str, Any]
    user: Dict[str, Any]
    mode: str
    bundles: Dict[str, Any]
    recon_result: Optional[Any]
    verif_result: Optional[Any]
    triage: Optional[Dict[str, Any]]
    result: Optional[Any]
    emergency: bool
    trace: List[Dict[str, Any]]
    errors: List[str]

    # Additional internal pipeline context
    record_label: Optional[str]
    parsed_context: Optional[Dict[str, Any]]
    triage_decision: Optional[Dict[str, Any]]
    risk: Optional[Dict[str, Any]]
    explanation: Optional[Dict[str, Any]]
