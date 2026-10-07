"""
Shared Validation and Clinical Safety Helpers for ChronicCare AI.
Provides exact age calculations, DOB boundary checks, and negation-aware safety phrase detection.
Pure python with zero network or external service dependencies.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional, Tuple, Union

from agents.adaptive_interview_agent import _CLAUSE_BREAK, _normalize, _is_negated

PREGNANCY_PATTERNS = [
    "pregnant",
    "pregnancy",
    "positive pregnancy test",
    "expecting a baby",
    "i am expecting",
    "i'm expecting",
    "having a baby",
    "حامل",
]


def parse_date(d: Union[str, date, datetime]) -> date:
    """Parses a date string in YYYY-MM-DD format or returns a date object."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if not isinstance(d, str):
        raise ValueError("invalid_date_of_birth")
    
    clean = d.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        raise ValueError("invalid_date_of_birth")
    
    try:
        return datetime.strptime(clean, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("invalid_date_of_birth")


def calculate_age(
    dob: Union[str, date, datetime],
    as_of_date: Optional[Union[str, date, datetime]] = None
) -> int:
    """
    Computes exact chronological age in completed years.
    Handles leap-day births (Feb 29), month/day boundaries, and future dates safely.
    Raises ValueError('invalid_date_of_birth') for future dates, dates > 120 years ago, or invalid formats.
    """
    dob_date = parse_date(dob)
    
    if as_of_date is not None:
        ref_date = parse_date(as_of_date)
    else:
        ref_date = datetime.now(timezone.utc).date()
    
    if dob_date > ref_date:
        raise ValueError("invalid_date_of_birth")
    
    # Calculate age in completed years:
    # Subtract 1 if current month/day is before birth month/day
    age = ref_date.year - dob_date.year - (
        (ref_date.month, ref_date.day) < (dob_date.month, dob_date.day)
    )
    
    if age < 0:
        raise ValueError("invalid_date_of_birth")
    if age > 120:
        raise ValueError("invalid_date_of_birth")
        
    return age


def validate_date_of_birth(
    dob: Union[str, date, datetime],
    as_of_date: Optional[Union[str, date, datetime]] = None
) -> Tuple[str, int]:
    """
    Validates DOB format and adult age requirement (18+).
    Returns (cleaned_iso_date_str, age).
    Raises ValueError('adults_only') if age < 18.
    Raises ValueError('invalid_date_of_birth') for malformed/future/unrealistic dates.
    """
    dob_date = parse_date(dob)
    age = calculate_age(dob_date, as_of_date=as_of_date)
    
    if age < 18:
        raise ValueError("adults_only")
        
    return dob_date.isoformat(), age


def detect_pregnancy_statement(text: str) -> bool:
    """
    Detects if free-text contains an affirmative statement indicating pregnancy.
    Uses negation-aware matching imported from adaptive_interview_agent.
    Returns True if an unnegated pregnancy statement is found, False otherwise.
    """
    if not text or not text.strip():
        return False
        
    for clause in _CLAUSE_BREAK.split(_normalize(text)):
        if not clause.strip():
            continue
        for pattern in PREGNANCY_PATTERNS:
            for match in re.finditer(re.escape(pattern), clause):
                if not _is_negated(clause, match.start()):
                    return True
    return False
