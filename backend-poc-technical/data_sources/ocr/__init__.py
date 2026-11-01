"""
OCR package for ChronicCare AI.
Extracts structured clinical observations, medications, and allergies from OCR text.
"""

from data_sources.ocr.extract_fields import (
    extract_fields,
    levenshtein_distance,
    match_medication_name,
    ALL_KNOWN_MEDICATIONS,
)

__all__ = [
    "extract_fields",
    "levenshtein_distance",
    "match_medication_name",
    "ALL_KNOWN_MEDICATIONS",
]
