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


THIRD_PARTY_SUBJECTS = {
    "sister", "wife", "daughter", "friend", "mother", "mom", "cousin",
    "partner", "relative", "neighbor", "colleague", "coworker", "aunt", "niece"
}

PAST_TENSE_PHRASES = [
    "was pregnant", "were pregnant", "previously pregnant", "pregnant in the past",
    "pregnant last year", "years ago", "months ago", "prior pregnancy", "past pregnancy"
]


def detect_pregnancy_statement(text: str) -> bool:
    """
    Detects if free-text contains an affirmative first-person statement indicating current pregnancy.
    Uses negation-aware matching imported from adaptive_interview_agent.
    Filters out third-person references, past pregnancies, and negative test results.
    Returns True if an unnegated, current first-person pregnancy statement is found, False otherwise.
    """
    if not text or not text.strip():
        return False
    
    normalized_full = _normalize(text)
    
    # Check for negative pregnancy test phrasing in clause or full text
    if "negative" in normalized_full:
        for term in ("pregnancy test negative", "test is negative", "test was negative", "negative pregnancy", "negative test"):
            if term in normalized_full:
                return False

    for clause in _CLAUSE_BREAK.split(normalized_full):
        clause_clean = clause.strip()
        if not clause_clean:
            continue
        
        # Filter out past tense / historical mentions
        if any(past in clause_clean for past in PAST_TENSE_PHRASES):
            continue
        
        # Filter out third-person references
        words = clause_clean.split()
        if any(tp in words for tp in THIRD_PARTY_SUBJECTS):
            continue
            
        for pattern in PREGNANCY_PATTERNS:
            for match in re.finditer(re.escape(pattern), clause_clean):
                if not _is_negated(clause_clean, match.start()):
                    # Check if post-match has 'negative'
                    post_text = clause_clean[match.end(): match.end() + 25].strip()
                    if post_text.startswith("negative") or post_text.startswith("test negative") or post_text.startswith("is negative"):
                        continue
                    return True
    return False
