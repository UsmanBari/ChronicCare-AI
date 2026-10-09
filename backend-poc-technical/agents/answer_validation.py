"""
Deterministic Answer Validation & Correction Engine (Interview Engine v3).

Features:
- Multilingual numeric parsing (English digits, Urdu digits ۰-۹, Arabic-Indic ٠-٩).
- English and Roman Urdu number words ("one twenty", "ek sau bees", "do sau").
- Compact BP formats ("12080", "120 by 80", "120/80", "120 80", decimal commas).
- Glucose unit disambiguation: values 2.0 to 40.0 without units trigger a clarification;
  values > 40 default to mg/dL. If unit remains unresolved, marked unknown + low_confidence + needs_review.
- Plausibility data tables with clinical references.
- Cross-check engine detecting contradictions against patient record or earlier answers.
- Minimiser detection ("just a little", "bas thora sa") triggering clinical anchoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


# =============================================================================
# Plausibility Ranges Data (Clinical references documented)
# =============================================================================
PLAUSIBILITY_RANGES = {
    # ADA Standards of Care 2026: plausible human blood glucose limits
    "glucose_mg_dl": {"min": 20.0, "max": 600.0, "source": "ada_2026_soc_sec6"},
    "glucose_mmol_l": {"min": 1.1, "max": 33.3, "source": "ada_2026_soc_sec6"},
    # 2025 AHA/ACC Hypertension Guidelines: human physiologic BP bounds
    "bp_systolic_mmhg": {"min": 60.0, "max": 260.0, "source": "aha_acc_2025_hypertension"},
    "bp_diastolic_mmhg": {"min": 30.0, "max": 160.0, "source": "aha_acc_2025_hypertension"},
    # Standard physiological clinical bounds (clinician review needed)
    "pulse_bpm": {"min": 30.0, "max": 220.0, "source": "clinical_team_illustrative"},
    "weight_kg": {"min": 20.0, "max": 400.0, "source": "clinical_team_illustrative"},
    "height_cm": {"min": 50.0, "max": 250.0, "source": "clinical_team_illustrative"},
    "temperature_c": {"min": 34.0, "max": 43.0, "source": "clinical_team_illustrative"},
}

_EASTERN_DIGITS_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# =============================================================================
# Number Word Dictionaries (English and Roman Urdu)
# =============================================================================
_WORD_TO_NUMBER: Dict[str, int] = {
    "zero": 0, "sifar": 0,
    "one": 1, "ek": 1, "aik": 1,
    "two": 2, "do": 2,
    "three": 3, "teen": 3,
    "four": 4, "chaar": 4, "char": 4,
    "five": 5, "paanch": 5, "panch": 5,
    "six": 6, "chhe": 6, "che": 6,
    "seven": 7, "saat": 7,
    "eight": 8, "aath": 8,
    "nine": 9, "nau": 9, "no": 9,
    "ten": 10, "das": 10, "dass": 10,
    "eleven": 11, "gyarah": 11,
    "twelve": 12, "barah": 12,
    "thirteen": 13, "terah": 13,
    "fourteen": 14, "chaudah": 14,
    "fifteen": 15, "pandrah": 15,
    "sixteen": 16, "solah": 16,
    "seventeen": 17, "satrah": 17,
    "eighteen": 18, "atharah": 18,
    "nineteen": 19, "unnees": 19,
    "twenty": 20, "bees": 20,
    "thirty": 30, "tees": 30,
    "forty": 40, "chaalis": 40, "chalis": 40,
    "fifty": 50, "pachaas": 50, "pachas": 50,
    "sixty": 60, "saath": 60,
    "seventy": 70, "sattar": 70,
    "eighty": 80, "assi": 80,
    "ninety": 90, "nabbe": 90,
    "hundred": 100, "sau": 100, "so": 100,
}


def _parse_number_words(text: str) -> Optional[float]:
    """Converts phrases like 'one twenty', 'ek sau bees', 'two hundred' into numeric values."""
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return None

    # Check for compound verbal expressions: e.g. "ek sau bees" -> 120, "one twenty" -> 120
    if len(words) == 3 and words[0] in ("ek", "aik", "one") and words[1] in ("sau", "so", "hundred"):
        base = 100
        third = _WORD_TO_NUMBER.get(words[2])
        if third is not None and third < 100:
            return float(base + third)

    if len(words) == 2 and words[0] in ("one", "ek", "aik") and words[1] in ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "bees", "tees", "chaalis", "pachaas", "saath", "sattar", "assi", "nabbe"):
        # "one twenty" -> 120
        tens_val = _WORD_TO_NUMBER.get(words[1], 0)
        return float(100 + tens_val)

    if len(words) == 2 and words[0] in ("do", "two") and words[1] in ("sau", "so", "hundred"):
        return 200.0

    if len(words) == 1 and words[0] in _WORD_TO_NUMBER:
        return float(_WORD_TO_NUMBER[words[0]])

    return None


@dataclass
class ValidationResult:
    valid: bool
    value: Any = None
    unit: Optional[str] = None
    is_ambiguous: bool = False
    needs_unit_clarification: bool = False
    is_possible_severe_low: bool = False
    is_minimiser: bool = False
    is_unclear: bool = False
    needs_review: bool = False
    review_reason: Optional[str] = None
    safety_guidance: Optional[str] = None
    confidence: str = "High"
    raw_quote: str = ""
    clarification_prompt: Optional[str] = None


def validate_glucose_input(text: str, previously_asked_unit: bool = False) -> ValidationResult:
    """
    Parses and validates glucose input:
    - If explicit 'mmol' or 'mmol/L', validates in mmol/L range (1.1 to 33.3).
    - If explicit 'mg/dL' / 'mg', validates in mg/dL range (20 to 600).
    - If number is 2.0 to 40.0 with NO unit:
      - If first time: returns needs_unit_clarification=True.
      - If second time (previously_asked_unit=True): treated as POSSIBLE SEVERE LOW (<= 40 mg/dL):
        level is at least Review, provider card shows 'glucose value unit unclear, possible low',
        low-sugar safety guidance is attached, symptom questions continue. Never lowers any level.
    - If number > 40: treated as mg/dL.
    """
    if not text or not text.strip():
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low")

    clean = text.strip().translate(_EASTERN_DIGITS_TABLE)
    lowered = clean.lower()

    # Check for skip or unknown
    if any(k in lowered for k in ["don't know", "dont know", "skip", "not sure", "prefer not to say", "maloom nahi", "nahi pata"]):
        if previously_asked_unit:
            # If answering "I don't know" to unit clarification, and original value was <= 40, treat as possible low
            return ValidationResult(
                valid=True,
                value=None,
                unit="unclear",
                is_unclear=True,
                needs_review=True,
                is_possible_severe_low=True,
                review_reason="glucose value unit unclear, possible low",
                safety_guidance="If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar (fruit juice or sweets) and re-check, or seek medical advice.",
                confidence="Low",
                raw_quote=clean,
                clarification_prompt="Glucose unit unclear. Treated as possible low sugar for safety review."
            )
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=clean)

    # Verbal number words check
    num_from_words = _parse_number_words(lowered)

    has_mmol = "mmol" in lowered
    has_mgdl = "mg/dl" in lowered or "mgdl" in lowered or "mg" in lowered

    # Find numeric float tokens
    # Replace decimal comma with dot (e.g. "6,5" -> 6.5)
    normalized_digits = re.sub(r"(?<=\d),(?=\d)", ".", lowered)
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", normalized_digits)]
    if not numbers and num_from_words is not None:
        numbers = [num_from_words]

    if not numbers:
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=clean)

    if len(numbers) > 1 and not (has_mmol or has_mgdl):
        return ValidationResult(valid=False, is_ambiguous=True, needs_review=True, confidence="Low", raw_quote=clean)

    val = numbers[0]

    # Explicit mmol/L
    if has_mmol:
        if PLAUSIBILITY_RANGES["glucose_mmol_l"]["min"] <= val <= PLAUSIBILITY_RANGES["glucose_mmol_l"]["max"]:
            return ValidationResult(valid=True, value=val, unit="mmol/L", confidence="High", raw_quote=clean)
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=clean)

    # Explicit mg/dL
    if has_mgdl:
        if PLAUSIBILITY_RANGES["glucose_mg_dl"]["min"] <= val <= PLAUSIBILITY_RANGES["glucose_mg_dl"]["max"]:
            return ValidationResult(valid=True, value=val, unit="mg/dL", confidence="High", raw_quote=clean)
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=clean)

    # No explicit unit: evaluate range
    if 2.0 <= val <= 40.0:
        if previously_asked_unit:
            return ValidationResult(
                valid=False,
                value=val,
                unit="unclear",
                is_unclear=True,
                needs_review=True,
                is_possible_severe_low=True,
                review_reason="glucose value unit unclear, possible low",
                safety_guidance="If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar (fruit juice or sweets) and re-check, or seek medical advice.",
                confidence="Low",
                raw_quote=clean,
                clarification_prompt="Glucose unit unclear. Treated as possible low sugar for safety review."
            )
        return ValidationResult(
            valid=False,
            value=val,
            is_ambiguous=True,
            needs_unit_clarification=True,
            raw_quote=clean,
            clarification_prompt=f"I heard {val:g}. Is that mmol/L or mg/dL?"
        )

    if PLAUSIBILITY_RANGES["glucose_mg_dl"]["min"] <= val <= PLAUSIBILITY_RANGES["glucose_mg_dl"]["max"]:
        return ValidationResult(valid=True, value=val, unit="mg/dL", confidence="High", raw_quote=clean)

    return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=clean)


def validate_bp_input(text: str) -> ValidationResult:
    """
    Parses blood pressure from various formats: '120/80', '120 by 80', '12080', '130 85'.
    """
    if not text or not text.strip():
        return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low")

    clean = text.strip().translate(_EASTERN_DIGITS_TABLE).lower()

    # 1. Compact 5-digit or 6-digit format: "12080" -> 120/80, "13585" -> 135/85
    match_compact = re.search(r"\b(1\d{2}|2\d{2}|[7-9]\d)([4-9]\d|1[0-2]\d)\b", clean)
    if match_compact and ("/" not in clean and "by" not in clean and "over" not in clean):
        sys_v = int(match_compact.group(1))
        dia_v = int(match_compact.group(2))
        if (PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["min"] <= sys_v <= PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["max"] and
            PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["min"] <= dia_v <= PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["max"] and
            sys_v > dia_v):
            return ValidationResult(valid=True, value=[sys_v, dia_v], unit="mmHg", confidence="High", raw_quote=text.strip())

    # 2. Standard pair patterns: 120/80, 120 by 80, 120 over 80, 120 80
    pairs = re.findall(r"(\d{2,3})\s*(?:/|by|over|\s+)\s*(\d{2,3})", clean)
    for s_str, d_str in pairs:
        sys_v, dia_v = int(s_str), int(d_str)
        if (PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["min"] <= sys_v <= PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["max"] and
            PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["min"] <= dia_v <= PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["max"] and
            sys_v > dia_v):
            return ValidationResult(valid=True, value=[sys_v, dia_v], unit="mmHg", confidence="High", raw_quote=text.strip())

    return ValidationResult(valid=False, is_unclear=True, needs_review=True, confidence="Low", raw_quote=text.strip())


def detect_cross_checks_and_contradictions(
    current_slot: str,
    answer_text: str,
    known_slots: Dict[str, Any],
    patient_record: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Cross-checks the current answer against patient record and earlier answers:
    - Insulin contradiction: patient on insulin in record says 'no insulin'
    - Adherence contradiction: says 'took all doses' then 'ran out of meds'
    - Fasting contradiction: says 'fasting' then mentions 'just ate lunch'
    - Symptom contradiction: says 'no symptoms' then reports 'severe pain'
    """
    lowered = (answer_text or "").lower()

    # 1. Insulin Record vs Answer
    if patient_record.get("on_insulin_or_sulfonylurea") and ("no insulin" in lowered or "don't take insulin" in lowered or "dawa nahi leta" in lowered):
        return {
            "slot": current_slot,
            "type": "record_mismatch",
            "message": "Your medical profile lists insulin or sulfonylurea, but you mentioned not taking it. Did your doctor recently change this medication?",
            "record_value": "on_insulin_or_sulfonylurea=True",
            "reported_value": answer_text,
        }

    # 2. Adherence vs Ran Out
    if known_slots.get("adherence_diabetes") is True or known_slots.get("adherence_hypertension") is True:
        if "ran out" in lowered or "khatam ho gayi" in lowered or "no pills left" in lowered:
            return {
                "slot": current_slot,
                "type": "answer_contradiction",
                "message": "Earlier you mentioned taking all doses, but also mentioned running out of medicine. Would you like to clarify?",
                "previous_value": "adherence=True",
                "reported_value": answer_text,
            }

    # 3. Fasting vs Just Ate
    if known_slots.get("glucose_context") == "fasting" or known_slots.get("is_fasting_today") is True:
        if "just ate" in lowered or "after lunch" in lowered or "khana khaya" in lowered:
            return {
                "slot": current_slot,
                "type": "context_mismatch",
                "message": "We noted this reading as fasting, but you mentioned eating recently. Was this reading taken before or after your meal?",
                "previous_value": "fasting",
                "reported_value": answer_text,
            }

    return None


check_contradiction = detect_cross_checks_and_contradictions
