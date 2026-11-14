"""
Medication Confirmation (Iteration 1)

After the Adaptive Interview finishes, the patient is asked about each ACTIVE medication
that the record lists ("Are you still taking X?"). The answers become the check-in's
medications, so the Reconciliation Agent can compare them with the record and the
Verification Agent can rate any difference (active against stopped is high severity).

Deterministic and rule based. No diagnosis, no scoring, no language model. One call
advances the check by one answer and returns a NEW state, so a stateless API can store it
as JSON (MedicationCheckState.to_dict() / from_dict()).

=============================================================================
RULES
=============================================================================
1. Only medications whose status is "active" are asked about, one question each, in the
   order of the record, de-duplicated by normalised name, at most MAX_MEDICATIONS.
   Historical or stopped records are kept but NOT compared (restrict_to_asked), otherwise
   every old medication would raise a review item on every check-in.
2. Answer meaning (conservative; a false flag is safer than a missed change):
     - a stop phrase ("stopped", "quit", "discontinued", "no longer", "anymore") -> stopped
     - a clear yes with no new dose                                              -> active, same dose
     - a clear yes or a dose statement that differs from the record              -> active, NEW dose
       (a dose statement needs a unit or a dose word: mg, tablet, half, twice, once, daily; a bare number such as "0" is not one)
     - a clear no                                                                -> stopped
     - "missed", "skipped", "forgot", "didn't take" alone are NOT a stop: they are unclear
     - anything else                                                             -> unclear
3. An unclear answer is asked ONE more time. If it is still unclear the medication is
   recorded as "unknown" and left out of the check-in (reported as "not reported today").
4. A blank answer never advances the check.
5. Every medication answer is self-reported: build_medication_origins() tags it so the
   Verification Agent treats it as low trust.
6. The caller must run the Stage-1 red-flag screen on every answer before this module
   (FR-5 applies to every response, including these).
=============================================================================
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Iterable, List, Optional

from agents.adaptive_interview_agent import _looks_affirmative, _normalize
from data_sources.models import NormalizedMedication

MAX_MEDICATIONS = 20
MAX_DOSAGE_CHARS = 100
SELF_REPORTED_ORIGIN = "self_reported"

_STOP_WORDS = re.compile(r"\b(?:stopped|quit|discontinued|no longer|anymore)\b")
_MISSED = re.compile(
    r"\b(?:missed|skipped|forgot|forgotten|didn'?t take|did not take|haven'?t taken|not taken)\b")
_HARD_NO = re.compile(r"\b(?:no|never|nope|nah|not taking)\b")
_DOSE_HINT = re.compile(
    r"\d\s*(?:mg|mcg|ml|units?|tablets?|pills?|capsules?|times|x)\b"
    r"|\b(?:mg|mcg|ml|tablets?|pills?|capsules?|units?|half|double|twice|thrice|once|daily|times)\b")
_LEADING_YES = re.compile(r"^(?:yes|yeah|yep|yup|haan|ji)\b[\s,.:;!-]*", re.IGNORECASE)


def _norm(text: Optional[str]) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def _get(med: Any, key: str) -> Any:
    return med.get(key) if isinstance(med, dict) else getattr(med, key, None)


@dataclass
class MedicationCheckState:
    items: List[Dict[str, str]] = field(default_factory=list)   # [{"name", "dosage"}]
    index: int = 0
    attempts: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.index >= len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MedicationCheckState":
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown MedicationCheckState fields: {sorted(unknown)}")
        return cls(**copy.deepcopy(data))


def start_medication_check(prior_medications: Optional[Iterable[Any]]) -> MedicationCheckState:
    """Builds the list of active medications to ask about (see RULES 1)."""
    seen = set()
    items: List[Dict[str, str]] = []
    for med in prior_medications or []:
        name = (_get(med, "medication_name") or "").strip()
        status = (_get(med, "status") or "").strip().lower()
        if not name or status != "active":
            continue
        key = _norm(name)
        if key in seen:
            continue
        seen.add(key)
        items.append({"name": name, "dosage": (_get(med, "dosage") or "").strip()})
        if len(items) >= MAX_MEDICATIONS:
            break
    return MedicationCheckState(items=items)


def current_medication_question(state: MedicationCheckState) -> Optional[str]:
    if state.complete:
        return None
    item = state.items[state.index]
    label = f"{item['name']} ({item['dosage']})" if item["dosage"] else item["name"]
    if state.attempts == 0:
        return (f"Your record lists {label}. Are you still taking it? "
                "Answer yes or no, or tell me the dose you take now.")
    return (f"Sorry, I didn't catch that. Are you still taking {label}? "
            "Please answer yes or no, or tell me the dose.")


def _interpret(text: str, record_dosage: str):
    """Returns (status, dosage, changed) with status in active / stopped / unclear."""
    lowered = _normalize(text)
    if _STOP_WORDS.search(lowered):
        return "stopped", record_dosage, False
    verdict = _looks_affirmative(text)
    if verdict is False:
        if _MISSED.search(lowered) and not _HARD_NO.search(lowered):
            return "unclear", record_dosage, False
        return "stopped", record_dosage, False
    stripped = _LEADING_YES.sub("", text.strip()).strip() or text.strip()
    record_norm, answer_norm = _norm(record_dosage), _norm(text)
    states_dose = bool(_DOSE_HINT.search(lowered))
    same_dose = bool(record_norm) and record_norm in answer_norm
    if verdict is True:
        if states_dose and not same_dose:
            return "active", stripped[:MAX_DOSAGE_CHARS], True
        return "active", record_dosage, False
    if states_dose:
        if same_dose:
            return "active", record_dosage, False
        return "active", stripped[:MAX_DOSAGE_CHARS], True
    return "unclear", record_dosage, False


def advance_medication_check(state: MedicationCheckState, answer: str) -> MedicationCheckState:
    """Consumes one answer and returns a NEW state (the input is untouched)."""
    state = copy.deepcopy(state)
    if state.complete:
        raise ValueError("Medication check already complete.")
    text = (answer or "").strip()
    if not text:
        return state
    item = state.items[state.index]
    status, dosage, changed = _interpret(text, item["dosage"])
    if status == "unclear" and state.attempts == 0:
        state.attempts = 1
        return state
    if status == "unclear":
        status, changed = "unknown", False
    state.results.append({
        "name": item["name"],
        "record_dosage": item["dosage"],
        "status": status,
        "dosage": dosage,
        "changed": changed,
    })
    state.index += 1
    state.attempts = 0
    return state


def restrict_to_asked(prior_medications: Optional[Iterable[Any]],
                      state: MedicationCheckState) -> List[Any]:
    """The prior medications that were actually asked about (RULES 1)."""
    asked = {_norm(item["name"]) for item in state.items}
    return [m for m in (prior_medications or []) if _norm(_get(m, "medication_name")) in asked]


def build_medication_bundle_items(state: MedicationCheckState, patient_id: str, source: str,
                                  timestamp: str) -> List[NormalizedMedication]:
    """Check-in medications for reconcile_bundles() (bundle_b["medications"]).

    `source` must be the same store as the prior record ("fhir" or "local"), otherwise
    reconcile_bundles() raises its Store Invariant error. "unknown" answers are left out."""
    if not state.complete:
        raise ValueError("Medication check is not complete.")
    clean_source = (source or "").strip().lower()
    if clean_source not in ("fhir", "local"):
        raise ValueError(f"source must be 'fhir' or 'local', got '{source}'.")
    stamp = re.sub(r"[^0-9A-Za-z]", "", timestamp)
    return [
        NormalizedMedication(
            patient_id=patient_id,
            medication_name=result["name"],
            status=result["status"],
            dosage=result["dosage"],
            timestamp=timestamp,
            source=clean_source,
            source_record_id=f"CHECKIN-{patient_id}-{stamp}-med-{index}",
        )
        for index, result in enumerate(state.results)
        if result["status"] in ("active", "stopped")
    ]


def build_medication_origins(items: Iterable[NormalizedMedication]) -> Dict[str, str]:
    """Origin tags for verify_reconciliation(): every answer is self-reported."""
    return {m.source_record_id: SELF_REPORTED_ORIGIN for m in items}
