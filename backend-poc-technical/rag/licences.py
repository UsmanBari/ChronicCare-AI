"""
Guideline Licence Specifications & Compliance Engine.
Single machine-readable source of truth for guideline permissions, text/data mining rules,
expiry dates, provider constraints (G3), and patient attribution requirements (X4).
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_LICENCES_FILE = Path(__file__).resolve().parent / "licences.json"

_LICENCE_SPECS: Dict[str, Dict[str, Any]] = {}
_OVERRIDE_LLM_DERIVED: Dict[str, bool] = {}
_OVERRIDE_ATTRIBUTION: Dict[str, tuple[str, str]] = {}


def _load_licences() -> Dict[str, Dict[str, Any]]:
    global _LICENCE_SPECS
    if not _LICENCE_SPECS:
        if not _LICENCES_FILE.exists():
            raise FileNotFoundError(f"Licence definitions missing: {_LICENCES_FILE}")
        with open(_LICENCES_FILE, "r", encoding="utf-8") as f:
            _LICENCE_SPECS = json.load(f)
    return _LICENCE_SPECS


def get_all_licence_specs() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of all guideline licence specifications keyed by source_id."""
    return dict(_load_licences())


def get_licence_spec(source_id: str) -> Optional[Dict[str, Any]]:
    """Return licence specification for a given source_id, or None if unknown."""
    specs = _load_licences()
    return specs.get(str(source_id).strip().lower())


def get_restricted_gemini_sources() -> Set[str]:
    """
    Return set of source_ids that must NEVER be sent to Google Gemini under any circumstances (Rule G3).
    Includes all ADA 2026 sections and AHA/ACC 2025.
    """
    specs = _load_licences()
    return {
        sid for sid, s in specs.items()
        if not s.get("allowed_for_gemini", False)
    }


def is_source_allowed_for_rag(source_id: str) -> bool:
    """Return True if source is allowed for retrieval in RAG according to licence."""
    spec = get_licence_spec(source_id)
    if not spec:
        return False
    return bool(spec.get("allowed_for_rag", False))


def is_source_expired(source_id: str, as_of: Optional[date | datetime | str] = None) -> bool:
    """
    Return True if the source's licence period has expired.
    None expires_on indicates permanent/open access. Unknown sources return False.
    """
    spec = get_licence_spec(source_id)
    if not spec:
        return False
    exp_str = spec.get("expires_on")
    if not exp_str:
        return False

    if as_of is None:
        check_date = date.today()
    elif isinstance(as_of, datetime):
        check_date = as_of.date()
    elif isinstance(as_of, date):
        check_date = as_of
    elif isinstance(as_of, str):
        check_date = datetime.strptime(as_of[:10], "%Y-%m-%d").date()
    else:
        check_date = date.today()

    exp_date = datetime.strptime(exp_str[:10], "%Y-%m-%d").date()
    return check_date > exp_date


def is_llm_allowed_for_source(
    source_id: str,
    provider: str,
    as_of: Optional[date | datetime | str] = None,
) -> bool:
    """
    Check if a source's text/chunks may be used to generate LLM explanations:
    1. Source must be allowed for RAG.
    2. Source must not be expired.
    3. llm_derived_text_allowed must be True.
    4. provider must be in allowed_llm_providers (e.g. Groq only, never Gemini for ADA).
    Unknown/test sources default to True unless restricted.
    """
    sid = str(source_id).strip().lower()
    spec = get_licence_spec(sid)
    if not spec:
        return True

    if not spec.get("allowed_for_rag", False):
        return False

    if is_source_expired(sid, as_of=as_of):
        return False

    # Check override first (for hermetic test toggles), then spec
    derived_allowed = _OVERRIDE_LLM_DERIVED.get(sid, spec.get("llm_derived_text_allowed", False))
    if not derived_allowed:
        return False

    p_norm = str(provider).strip().lower()
    allowed_providers = [p.lower() for p in spec.get("allowed_llm_providers", [])]
    return p_norm in allowed_providers


def has_complete_attribution(source_id: str, chunk: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a source has complete citation and DOI attribution.
    If requires_citation_and_doi is True, full_citation and doi must be populated
    and cannot be 'TO FILL BY USMAN'.
    Attribution can be provided in overrides, chunk metadata, or licences.json.
    Unknown/mock sources default to True.
    """
    sid = str(source_id).strip().lower()
    spec = get_licence_spec(sid)
    if not spec:
        return True
    if not spec.get("requires_citation_and_doi", False):
        return True

    # 1. Check test override
    if sid in _OVERRIDE_ATTRIBUTION:
        cit, doi = _OVERRIDE_ATTRIBUTION[sid]
        if cit and cit.upper() != "TO FILL BY USMAN" and doi and doi.upper() != "TO FILL BY USMAN":
            return True

    # 2. Check chunk metadata if provided
    if chunk:
        c_cit = str(chunk.get("full_citation", "")).strip()
        c_doi = str(chunk.get("doi", "")).strip()
        if c_cit and c_cit.upper() != "TO FILL BY USMAN" and c_doi and c_doi.upper() != "TO FILL BY USMAN":
            return True

    # 3. Check licence spec
    citation = str(spec.get("full_citation", "")).strip()
    doi = str(spec.get("doi", "")).strip()

    if not citation or citation.upper() == "TO FILL BY USMAN":
        return False
    if not doi or doi.upper() == "TO FILL BY USMAN":
        return False
    return True


def get_source_attribution(source_id: str, chunk: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Return attribution metadata {'full_citation': str, 'doi': str} for a given source.
    """
    sid = str(source_id).strip().lower()
    if sid in _OVERRIDE_ATTRIBUTION:
        cit, doi = _OVERRIDE_ATTRIBUTION[sid]
        return {"full_citation": cit, "doi": doi}

    if chunk:
        c_cit = str(chunk.get("full_citation", "")).strip()
        c_doi = str(chunk.get("doi", "")).strip()
        if c_cit and c_cit.upper() != "TO FILL BY USMAN" and c_doi and c_doi.upper() != "TO FILL BY USMAN":
            return {"full_citation": c_cit, "doi": c_doi}

    spec = get_licence_spec(sid)
    if not spec:
        return {"full_citation": "", "doi": ""}
    return {
        "full_citation": str(spec.get("full_citation", "")).strip(),
        "doi": str(spec.get("doi", "")).strip(),
    }


def set_llm_derived_text_override(source_id: str, allowed: Optional[bool]) -> None:
    """Set temporary in-memory override for test assertions (None resets)."""
    sid = str(source_id).strip().lower()
    if allowed is None:
        _OVERRIDE_LLM_DERIVED.pop(sid, None)
    else:
        _OVERRIDE_LLM_DERIVED[sid] = allowed


def set_attribution_override(source_id: str, full_citation: Optional[str] = None, doi: Optional[str] = None) -> None:
    """Set temporary attribution override for testing complete attribution paths."""
    sid = str(source_id).strip().lower()
    if full_citation is None and doi is None:
        _OVERRIDE_ATTRIBUTION.pop(sid, None)
    else:
        _OVERRIDE_ATTRIBUTION[sid] = (full_citation or "", doi or "")


def reset_licence_overrides() -> None:
    """Clear all test overrides."""
    _OVERRIDE_LLM_DERIVED.clear()
    _OVERRIDE_ATTRIBUTION.clear()
