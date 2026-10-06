"""
Medication Scope Filter for Connected Mode.

Filters large clinical EHR medication lists down to relevant active chronic-disease
medications (Type 2 Diabetes & Hypertension) to prevent overwhelming the patient
with excessive check-in questions while preserving clinical safety.
"""

from typing import List, Set, Any
from data_sources.models import NormalizedMedication

DIABETES_MEDICATION_KEYWORDS = (
    "metformin",
    "glimepiride",
    "gliclazide",
    "glibenclamide",
    "glipizide",
    "insulin",
    "sitagliptin",
    "vildagliptin",
    "linagliptin",
    "empagliflozin",
    "dapagliflozin",
    "canagliflozin",
    "pioglitazone",
    "liraglutide",
    "semaglutide",
    "dulaglutide",
    "acarbose",
)

HYPERTENSION_MEDICATION_KEYWORDS = (
    "amlodipine",
    "nifedipine",
    "lisinopril",
    "enalapril",
    "ramipril",
    "perindopril",
    "losartan",
    "valsartan",
    "telmisartan",
    "candesartan",
    "irbesartan",
    "atenolol",
    "bisoprolol",
    "metoprolol",
    "carvedilol",
    "propranolol",
    "hydrochlorothiazide",
    "chlorthalidone",
    "indapamide",
    "furosemide",
    "spironolactone",
    "hydralazine",
    "methyldopa",
    "doxazosin",
)

DIABETES_MEDICATIONS = DIABETES_MEDICATION_KEYWORDS
HYPERTENSION_MEDICATIONS = HYPERTENSION_MEDICATION_KEYWORDS
CHRONIC_CARE_MEDICATION_KEYWORDS = DIABETES_MEDICATIONS + HYPERTENSION_MEDICATIONS
DEFAULT_MEDICATION_LIMIT = 8


def _norm(text: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]', '', (text or "").lower())


def _get_med_name(m: Any) -> str:
    if hasattr(m, "medication_name") and m.medication_name:
        return m.medication_name
    if hasattr(m, "name") and m.name:
        return m.name
    if isinstance(m, dict):
        return m.get("medication_name") or m.get("name") or ""
    return ""


def _get_med_status(m: Any) -> str:
    if hasattr(m, "status") and m.status:
        return m.status
    if isinstance(m, dict):
        return m.get("status") or ""
    return ""


def _get_med_timestamp(m: Any) -> str:
    if hasattr(m, "timestamp") and m.timestamp:
        return m.timestamp
    if isinstance(m, dict):
        return m.get("timestamp") or ""
    return ""


def select_chronic_care_medications(
    medications: List[Any],
    limit: int = DEFAULT_MEDICATION_LIMIT
) -> List[Any]:
    """
    Filters and prioritizes active medications for chronic care review in Connected Mode.
    
    1. Keeps only ACTIVE medications.
    2. Matches against diabetes and hypertension medication keywords.
    3. De-duplicates by normalized medication name.
    4. Orders by most recently authored first (preserving timestamp order).
    5. Capped at `limit` (default 8).
    """
    if not medications:
        return []

    # Filter active only
    active_meds = [m for m in medications if _get_med_status(m).lower() == "active"]

    # Filter by keyword relevance
    relevant: List[Any] = []
    for med in active_meds:
        med_norm = _norm(_get_med_name(med))
        if any(kw in med_norm for kw in CHRONIC_CARE_MEDICATION_KEYWORDS):
            relevant.append(med)

    # Sort most recent first if timestamps present
    sorted_meds = sorted(relevant, key=lambda m: _get_med_timestamp(m), reverse=True)

    # Deduplicate by normalised medication name (keeping first/most recent)
    seen_names: Set[str] = set()
    deduped: List[Any] = []
    for med in sorted_meds:
        med_norm = _norm(_get_med_name(med))
        if med_norm not in seen_names:
            seen_names.add(med_norm)
            deduped.append(med)

    return deduped[:limit]

