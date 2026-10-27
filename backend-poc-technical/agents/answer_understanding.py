"""
Pure stdlib module for multilingual answer understanding and parsing.
Supports English, Roman Urdu, and Urdu script.
No I/O, no network, deterministic.

Functions:
- normalise_text(text: str) -> str
- parse_yes_no(text: str, lang: Optional[str] = None) -> dict
- parse_number(text: str) -> dict
- parse_bp(text: str) -> dict
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

# Re-use Eastern digits translation table and clinical limits from answer_validation
from agents.answer_validation import (
    _EASTERN_DIGITS_TABLE,
    PLAUSIBILITY_RANGES,
)

BP_SYSTOLIC_MIN = PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["min"]
BP_SYSTOLIC_MAX = PLAUSIBILITY_RANGES["bp_systolic_mmhg"]["max"]
BP_DIASTOLIC_MIN = PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["min"]
BP_DIASTOLIC_MAX = PLAUSIBILITY_RANGES["bp_diastolic_mmhg"]["max"]

# -----------------------------------------------------------------------------
# A1: Normalisation
# -----------------------------------------------------------------------------
_ARABIC_TO_URDU = str.maketrans({
    "ي": "ی",  # \u064A -> \u06CC
    "ك": "ک",  # \u0643 -> \u06A9
    "ه": "ہ",  # \u0647 -> \u06C1
    "ى": "ی",  # \u0649 -> \u06CC
})

_DIACRITICS_RE = re.compile(r"[\u0640\u064B-\u065F\u0670]")


def normalise_text(text: str) -> str:
    """
    Normalises input text:
    - Unicode NFKC
    - Arabic -> Urdu letter harmonization (ي->ی, ك->ک, ه->ہ, ى->ی)
    - Tatweel (ـ) and Urdu/Arabic diacritics removed
    - Eastern Arabic and Urdu digits -> ASCII (via _EASTERN_DIGITS_TABLE)
    - Lowercase Latin characters
    - Collapse multiple spaces to a single space, strip leading/trailing
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    norm = norm.translate(_EASTERN_DIGITS_TABLE)
    norm = norm.translate(_ARABIC_TO_URDU)
    norm = _DIACRITICS_RE.sub("", norm)
    norm = norm.lower()
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


# -----------------------------------------------------------------------------
# A2: parse_yes_no
# -----------------------------------------------------------------------------
# Punctuation to strip around words (apostrophe excluded so contractions like don't remain single tokens)
_PUNCT = ".,!?;:()[]{}\"«»؛؟،\t\n\r"


def _tokenize(norm_text: str) -> List[str]:
    """Splits normalised text into words preserving Urdu and Latin tokens."""
    cleaned = ""
    for ch in norm_text:
        if ch in _PUNCT:
            cleaned += " "
        else:
            cleaned += ch
    return cleaned.split()


def _contains_subsequence(tokens: List[str], phrase_tokens: List[str]) -> bool:
    """Checks if phrase_tokens appears as a contiguous subsequence in tokens."""
    n, m = len(tokens), len(phrase_tokens)
    if m == 0 or n < m:
        return False
    for i in range(n - m + 1):
        if tokens[i:i + m] == phrase_tokens:
            return True
    return False


_UNKNOWN_PHRASES = [
    # English
    ["i", "don't", "know"],
    ["i", "dont", "know"],
    ["don't", "know"],
    ["dont", "know"],
    ["not", "sure"],
    ["no", "idea"],
    ["idk"],
    ["maybe"],
    ["perhaps"],
    # Roman Urdu
    ["pata", "nahi"],
    ["pata", "nahin"],
    ["pta", "nahi"],
    ["pta", "nahin"],
    ["maloom", "nahi"],
    ["maloom", "nahin"],
    ["shayad"],
    # Urdu script
    ["معلوم", "نہیں"],
    ["پتہ", "نہیں"],
    ["شاید"],
]

_PARTIAL_PHRASES = [
    ["thora", "sa"],
    ["thoda", "sa"],
    ["thora"],
    ["thoda"],
    ["kabhi", "kabhi"],
    ["sometimes"],
    ["a", "little"],
    ["a", "bit"],
    # Urdu script
    ["تھوڑا", "سا"],
    ["تھوڑا"],
    ["کبھی", "کبھی"],
]

_YES_PHRASES = [
    ["of", "course"],
    ["i", "am"],
    ["i", "do"],
    ["i", "did"],
    ["i", "have"],
    ["haan", "ji"],
    ["han", "ji"],
    ["ji", "haan"],
    ["jee", "haan"],
    ["ji", "han"],
    ["jee", "han"],
    ["جی", "ہاں"],
]

_YES_WORDS = {
    "yes", "yeah", "yep", "yup", "sure", "correct", "right",
    "haan", "han", "haanji", "hanji", "bilkul", "zaroor",
    "ہاں", "بالکل", "ضرور",
}

_NO_PHRASES = [
    ["not", "really"],
    ["i", "am", "not"],
    ["i", "don't"],
    ["i", "dont"],
    ["i", "didn't"],
    ["i", "didnt"],
    ["i", "haven't"],
    ["i", "havent"],
    ["na", "nahi"],
    ["na", "nahin"],
    ["ji", "nahi"],
    ["jee", "nahi"],
    ["ji", "nahin"],
    ["jee", "nahin"],
    ["bilkul", "nahi"],
    ["bilkul", "nahin"],
    ["kabhi", "nahi"],
    ["kabhi", "nahin"],
    ["جی", "نہیں"],
    ["بالکل", "نہیں"],
    ["کبھی", "نہیں"],
]

_NO_WORDS = {
    "no", "nope", "nah", "never",
    "nahi", "nahin", "nai",
    "don't", "dont", "didn't", "didnt", "haven't", "havent",
    "نہیں",
}


def parse_yes_no(text: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses a patient's free text response into yes / no / unknown.
    Returns:
    {
        "value": "yes" | "no" | "unknown",
        "partial": bool,
        "evidence": <exact substring of original text>,
        "confidence": "High" | "Medium" | "Low",
        "matched_rule": <str>,
    }
    """
    orig_text = text if text is not None else ""
    trimmed = orig_text.strip()
    evidence = trimmed

    if not trimmed:
        return {
            "value": "unknown",
            "partial": False,
            "evidence": "",
            "confidence": "High",
            "matched_rule": "empty_input",
        }

    # Emoji checks
    if "👍" in trimmed or "✔️" in trimmed or "✅" in trimmed:
        return {
            "value": "yes",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Low",
            "matched_rule": "emoji_thumbs_up",
        }
    if "👎" in trimmed or "❌" in trimmed:
        return {
            "value": "no",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Low",
            "matched_rule": "emoji_thumbs_down",
        }
    if all(ord(c) > 0x1F000 for c in trimmed.replace(" ", "")):
        return {
            "value": "unknown",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Low",
            "matched_rule": "emoji_unknown",
        }

    norm = normalise_text(trimmed)
    tokens = _tokenize(norm)
    if not tokens:
        return {
            "value": "unknown",
            "partial": False,
            "evidence": trimmed,
            "confidence": "High",
            "matched_rule": "no_tokens",
        }

    # Trap: "not bad" -> unknown Medium
    if _contains_subsequence(tokens, ["not", "bad"]):
        return {
            "value": "unknown",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Medium",
            "matched_rule": "trap_not_bad",
        }

    # Trap: "no problem", "no worries" -> not no -> unknown Medium
    if _contains_subsequence(tokens, ["no", "problem"]) or _contains_subsequence(tokens, ["no", "worries"]):
        return {
            "value": "unknown",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Medium",
            "matched_rule": "trap_no_problem",
        }

    # Double negatives: e.g. "nahi aisa nahi hai", "no that is not true"
    if _contains_subsequence(tokens, ["nahi", "aisa", "nahi"]) or _contains_subsequence(tokens, ["no", "that", "is", "not"]):
        return {
            "value": "unknown",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Low",
            "matched_rule": "double_negative",
        }

    # Trap: "I don't know", "pata nahi", "maloom nahi" BEFORE no-words
    for unk_phrase in _UNKNOWN_PHRASES:
        if _contains_subsequence(tokens, unk_phrase):
            return {
                "value": "unknown",
                "partial": False,
                "evidence": trimmed,
                "confidence": "High",
                "matched_rule": "unknown_phrase",
            }

    # Multi-word NO phrases (High confidence: e.g. "bilkul nahi", "i am not", "ji nahi")
    for np in _NO_PHRASES:
        if _contains_subsequence(tokens, np):
            return {
                "value": "no",
                "partial": False,
                "evidence": trimmed,
                "confidence": "High",
                "matched_rule": "no_phrase",
            }

    # Multi-word YES phrases (High confidence: e.g. "ji haan", "of course")
    for yp in _YES_PHRASES:
        if _contains_subsequence(tokens, yp):
            return {
                "value": "yes",
                "partial": False,
                "evidence": trimmed,
                "confidence": "High",
                "matched_rule": "yes_phrase",
            }

    # Mixed statements: "the LAST clear statement wins, Medium, with both pieces in the evidence."
    last_yes_idx = -1
    last_no_idx = -1
    for i, t in enumerate(tokens):
        if t in _YES_WORDS:
            last_yes_idx = max(last_yes_idx, i)
        if t in _NO_WORDS or (t == "na" and i == 0):
            last_no_idx = max(last_no_idx, i)

    if last_yes_idx != -1 and last_no_idx != -1:
        if last_no_idx > last_yes_idx:
            return {
                "value": "no",
                "partial": False,
                "evidence": trimmed,
                "confidence": "Medium",
                "matched_rule": "mixed_last_wins_no",
            }
        else:
            return {
                "value": "yes",
                "partial": False,
                "evidence": trimmed,
                "confidence": "Medium",
                "matched_rule": "mixed_last_wins_yes",
            }

    # Partial: "thora sa", "thoda", "kabhi kabhi", "sometimes", "a little", "a bit"
    for part_p in _PARTIAL_PHRASES:
        if _contains_subsequence(tokens, part_p):
            return {
                "value": "yes",
                "partial": True,
                "evidence": trimmed,
                "confidence": "Medium",
                "matched_rule": "partial_yes",
            }

    # "ji" / "jee" / "جی" ALONE (or with polite doctor address) -> yes, Medium
    if tokens == ["ji"] or tokens == ["jee"] or tokens == ["جی"] or tokens in (["ji", "doc"], ["ji", "doctor"]):
        return {
            "value": "yes",
            "partial": False,
            "evidence": trimmed,
            "confidence": "Medium",
            "matched_rule": "polite_ji_alone",
        }

    # Single-word YES check
    for t in tokens:
        if t in _YES_WORDS:
            return {
                "value": "yes",
                "partial": False,
                "evidence": trimmed,
                "confidence": "High",
                "matched_rule": "yes_word",
            }

    # Single-word NO check & tag-question na handling
    for i, t in enumerate(tokens):
        if t in _NO_WORDS:
            return {
                "value": "no",
                "partial": False,
                "evidence": trimmed,
                "confidence": "High",
                "matched_rule": "no_word",
            }
        if t == "na":
            if len(tokens) == 1 or i == 0:
                return {
                    "value": "no",
                    "partial": False,
                    "evidence": trimmed,
                    "confidence": "High",
                    "matched_rule": "no_na_start_or_whole",
                }

    return {
        "value": "unknown",
        "partial": False,
        "evidence": trimmed,
        "confidence": "Low",
        "matched_rule": "unmatched_fallback",
    }


# -----------------------------------------------------------------------------
# A3: parse_number
# -----------------------------------------------------------------------------
_ENGLISH_NUMBERS: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_ROMAN_URDU_NUMBERS: Dict[str, int] = {
    # 0-20
    "sifar": 0, "zero": 0,
    "ek": 1, "aik": 1,
    "do": 2,
    "teen": 3,
    "chaar": 4, "char": 4,
    "paanch": 5, "panch": 5,
    "chheh": 6, "che": 6, "chhe": 6, "chey": 6,
    "saat": 7,
    "aath": 8,
    "nau": 9, "no": 9,
    "das": 10,
    "gyaarah": 11, "gyara": 11,
    "baarah": 12, "bara": 12,
    "teerah": 13, "tera": 13,
    "chaudah": 14, "choda": 14,
    "pandrah": 15, "pandra": 15,
    "solah": 16, "sola": 16,
    "satrah": 17, "satra": 17,
    "athaarah": 18, "athara": 18,
    "unnees": 19, "unis": 19,
    "bees": 20, "bis": 20,
    # 21-30
    "ikkees": 21, "ikkis": 21,
    "baais": 22, "bais": 22,
    "teis": 23,
    "chaubees": 24, "chaubis": 24,
    "pachchees": 25, "pachees": 25, "pachis": 25,
    "chhabbees": 26, "chhabis": 26,
    "sattais": 27,
    "atthais": 28,
    "untees": 29, "untis": 29,
    "tees": 30,
    # 31-40
    "ikattis": 31, "iktis": 31,
    "battees": 32, "battis": 32,
    "taintees": 33, "taintis": 33,
    "chautees": 34, "chautis": 34,
    "paintees": 35, "paintis": 35,
    "chhattees": 36, "chhattis": 36,
    "saintees": 37, "saintis": 37,
    "adtees": 38, "adtis": 38,
    "untaalees": 39, "untalis": 39,
    "chaalees": 40, "chalis": 40,
    # 41-50
    "iktaalees": 41, "iktalis": 41,
    "bayaalees": 42, "bayalis": 42,
    "taintaalees": 43, "taintalis": 43,
    "chawalees": 44, "chawalis": 44,
    "pentaalees": 45, "pentalees": 45, "pantalis": 45, "paintalis": 45,
    "chhiyaalees": 46, "chhiyalis": 46,
    "saintaalees": 47, "saintalis": 47,
    "adtaalees": 48, "adtalis": 48,
    "unchaas": 49, "unchas": 49,
    "pachaas": 50, "pachas": 50,
    # 51-60
    "ikyaavan": 51, "ikyawan": 51,
    "baavan": 52, "bawan": 52,
    "tirpan": 53,
    "chauvan": 54, "chawan": 54,
    "pachpan": 55,
    "chhappan": 56,
    "sattaavan": 57, "sattawan": 57,
    "atthaavan": 58, "atthawan": 58,
    "unsath": 59,
    "saath": 60, "sath": 60,
    # 61-70
    "iksath": 61,
    "baasath": 62, "basath": 62,
    "tirsath": 63,
    "chausath": 64,
    "painsath": 65,
    "chhiyaasath": 66, "chhiyasath": 66,
    "sarsath": 67,
    "adsath": 68,
    "unhattar": 69,
    "sattar": 70,
    # 71-80
    "ikhattar": 71,
    "bahattar": 72,
    "tihattar": 73,
    "chauhattar": 74,
    "pachhattar": 75,
    "chhihattar": 76,
    "sathattar": 77,
    "athattar": 78,
    "unaasi": 79, "unasi": 79,
    "assi": 80,
    # 81-90
    "ikyaasi": 81, "ikyasi": 81,
    "bayaasi": 82, "bayasi": 82,
    "tiraasi": 83, "tirasi": 83,
    "chauraasi": 84, "chaurasi": 84,
    "pachaasi": 85, "pachasi": 85,
    "chhiyaasi": 86, "chhiyasi": 86,
    "sattaasi": 87, "sattasi": 87,
    "athaasi": 88, "athasi": 88,
    "navaasi": 89, "navasi": 89,
    "nabbe": 90, "nave": 90,
    # 91-100
    "ikyaanve": 91, "ikyanve": 91,
    "baanve": 92, "banve": 92,
    "tiraanve": 93, "tiranve": 93,
    "chauraanve": 94, "chauranve": 94,
    "pachaanve": 95, "pachanve": 95,
    "chhiyaanve": 96, "chhiyanve": 96,
    "sattaanve": 97, "sattanve": 97,
    "atthaanve": 98, "atthanve": 98,
    "ninyaanve": 99, "ninyanve": 99,
    "sau": 100,
}

_URDU_SCRIPT_NUMBERS: Dict[str, int] = {
    "صفر": 0,
    "ایک": 1, "دو": 2, "تین": 3, "چار": 4, "پانچ": 5,
    "چھ": 6, "سات": 7, "آٹھ": 8, "نو": 9, "دس": 10,
    "گیارہ": 11, "بارہ": 12, "تیرہ": 13, "چودہ": 14, "پندرہ": 15,
    "سولہ": 16, "سترہ": 17, "اٹھارہ": 18, "انیس": 19, "بیس": 20,
    "اکیس": 21, "بائیس": 22, "تئیس": 23, "چوبیس": 24, "پچیس": 25,
    "چھبیس": 26, "ستائیس": 27, "اٹھائیس": 28, "انتیس": 29, "تیس": 30,
    "اکتیس": 31, "بتیس": 32, "تینتیس": 33, "چونتیس": 34, "پینتیس": 35,
    "چھتیس": 36, "سینتیس": 37, "اڑتیس": 38, "انتالیس": 39, "چالیس": 40,
    "اکتالیس": 41, "بیالیس": 42, "تینتالیس": 43, "چوالیس": 44, "پینتالیس": 45,
    "چھیاالیس": 46, "سینتالیس": 47, "اڑتالیس": 48, "انچاس": 49, "پچاس": 50,
    "اکیاون": 51, "باون": 52, "ترپن": 53, "چون": 54, "پچپن": 55,
    "چھپن": 56, "ستاون": 57, "اٹھاون": 58, "انسٹھ": 59, "ساٹھ": 60,
    "اکسٹھ": 61, "باسٹھ": 62, "ترسٹھ": 63, "چوسٹھ": 64, "پینسٹھ": 65,
    "چھیاسٹھ": 66, "سڑسٹھ": 67, "اڑسٹھ": 68, "انہتر": 69, "ستر": 70,
    "اکہتر": 71, "بہتر": 72, "تہتر": 73, "چوہتر": 74, "پچہتر": 75,
    "چھہتر": 76, "ستتر": 77, "اٹھہتر": 78, "اناسی": 79, "اسی": 80,
    "اکیاسی": 81, "بیاسی": 82, "تراسی": 83, "چوراسی": 84, "پچاسی": 85,
    "چھیاسی": 86, "ستاسی": 87, "اٹ्ठाسی": 88, "نواسی": 89, "نوے": 90,
    "اکیانوے": 91, "بانوے": 92, "ترانوے": 93, "چورانوے": 94, "پچانوے": 95,
    "چھیانوے": 96, "ستانوے": 97, "اٹّھانوے": 98, "ننانوے": 99, "سو": 100,
}

_DATE_TIME_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b"),  # 12/10, 12-10-2026
    re.compile(r"\b\d{1,2}:\d{2}\b"),  # 8:00
    re.compile(r"\b\d{1,2}\s*(am|pm|baje)\b", re.IGNORECASE),  # 8am, 8 baje
    re.compile(r"\b(subah|shaam|dopahar|raat)\s+\d{1,2}\b", re.IGNORECASE),  # subah 8
]


def _is_date_or_time(text: str) -> bool:
    for pat in _DATE_TIME_PATTERNS:
        if pat.search(text):
            return True
    return False


def parse_number(text: str) -> Dict[str, Any]:
    """
    Parses a single number from free text.
    Returns:
    {
        "value": float | None,
        "evidence": str,
        "kind": "digits" | "words" | "meter_out_of_range" | None,
        "direction": "low" | "high" | None,
    }
    """
    orig_text = text if text is not None else ""
    trimmed = orig_text.strip()
    evidence = trimmed

    if not trimmed:
        return {"value": None, "evidence": "", "kind": None, "direction": None}

    # 1. Date and Time rejection
    if _is_date_or_time(trimmed):
        return {"value": None, "evidence": evidence, "kind": None, "direction": None}

    norm = normalise_text(trimmed)
    tokens = _tokenize(norm)

    # 2. Addendum E4: Meter LO and HI recognition
    lo_cues = {"lo", "low", "bohat kam", "bohot kam"}
    hi_cues = {"hi", "high", "bohat zyada", "bohot zyada"}

    norm_no_punct = " ".join(tokens)
    if norm_no_punct in ("lo", "low", "hi", "high") or trimmed.upper() in ("LO", "HI"):
        direction = "low" if norm_no_punct in ("lo", "low") or trimmed.upper() == "LO" else "high"
        return {"value": None, "evidence": evidence, "kind": "meter_out_of_range", "direction": direction}

    if any(norm_no_punct == c or f"meter {c}" in norm_no_punct or f"reading {c}" in norm_no_punct for c in lo_cues) or "meter pe lo" in norm_no_punct:
        return {"value": None, "evidence": evidence, "kind": "meter_out_of_range", "direction": "low"}
    if any(norm_no_punct == c or f"meter {c}" in norm_no_punct or f"reading {c}" in norm_no_punct for c in hi_cues) or "meter pe hi" in norm_no_punct:
        return {"value": None, "evidence": evidence, "kind": "meter_out_of_range", "direction": "high"}

    # 3. Ambiguity check: "120 ya 130", "120 or 130", "120 to 130", "ek do sau"
    if any(sep in tokens for sep in ["ya", "or", "to"]) and len(tokens) >= 3:
        return {"value": None, "evidence": evidence, "kind": None, "direction": None}
    if _contains_subsequence(tokens, ["ek", "do", "sau"]) or _contains_subsequence(tokens, ["aik", "do", "sau"]):
        return {"value": None, "evidence": evidence, "kind": None, "direction": None}

    # 4. Pure digits parsing (including decimals with . or ,)
    digit_match = re.findall(r"\b\d+(?:[.,]\d+)?\b", norm)
    if digit_match:
        if len(digit_match) > 1:
            return {"value": None, "evidence": evidence, "kind": None, "direction": None}
        val_str = digit_match[0].replace(",", ".")
        try:
            val = float(val_str)
            return {"value": val, "evidence": evidence, "kind": "digits", "direction": None}
        except ValueError:
            pass

    # 5. Words parsing: English, Roman Urdu, Urdu script
    val = _parse_word_compounds(tokens)
    if val is not None:
        return {"value": float(val), "evidence": evidence, "kind": "words", "direction": None}

    return {"value": None, "evidence": evidence, "kind": None, "direction": None}


def _parse_word_compounds(tokens: List[str]) -> Optional[int]:
    """Parses English, Roman Urdu, or Urdu script number phrases into an integer."""
    if not tokens:
        return None

    filtered = [t for t in tokens if t not in ("a", "and")]
    if not filtered:
        return None

    # Single word lookup (0-100)
    if len(filtered) == 1:
        w = filtered[0]
        if w in _ROMAN_URDU_NUMBERS:
            return _ROMAN_URDU_NUMBERS[w]
        if w in _ENGLISH_NUMBERS:
            return _ENGLISH_NUMBERS[w]
        if w in _URDU_SCRIPT_NUMBERS:
            return _URDU_SCRIPT_NUMBERS[w]
        if w in ("hundred", "sau"):
            return 100
        return None

    # Compound handling: hundreds + tens/units
    hundred_words = {"sau", "hundred", "سو"}
    hundred_val = 0
    rem_tokens = []

    if filtered[0] in hundred_words:
        hundred_val = 100
        rem_tokens = filtered[1:]
    elif len(filtered) >= 2 and (filtered[1] in hundred_words or (filtered[1] == "so" and filtered[0] in ("ek", "aik", "do", "teen", "char", "panch"))):
        mult = _get_single_num(filtered[0])
        if mult is not None:
            hundred_val = mult * 100
            rem_tokens = filtered[2:]
        else:
            return None
    elif len(filtered) == 2:
        # Check "one twenty" -> 120, "two thirty" -> 230
        first_num = _get_single_num(filtered[0])
        second_num = _get_single_num(filtered[1])
        if first_num == 1 and second_num is not None and second_num in (20, 30, 40, 50, 60, 70, 80, 90):
            return 100 + second_num
        if first_num == 2 and second_num is not None and second_num in (20, 30, 40, 50, 60, 70, 80, 90):
            return 200 + second_num
        return None
    else:
        return None

    if not rem_tokens:
        return hundred_val

    if len(rem_tokens) == 1:
        rem_val = _get_single_num(rem_tokens[0])
        if rem_val is not None:
            return hundred_val + rem_val
        return None

    if len(rem_tokens) == 2:
        t1 = _get_single_num(rem_tokens[0])
        t2 = _get_single_num(rem_tokens[1])
        if t1 is not None and t2 is not None and t1 in (20, 30, 40, 50, 60, 70, 80, 90) and 1 <= t2 <= 9:
            return hundred_val + t1 + t2
        return None

    return None


def _get_single_num(word: str) -> Optional[int]:
    if word in _ROMAN_URDU_NUMBERS:
        return _ROMAN_URDU_NUMBERS[word]
    if word in _ENGLISH_NUMBERS:
        return _ENGLISH_NUMBERS[word]
    if word in _URDU_SCRIPT_NUMBERS:
        return _URDU_SCRIPT_NUMBERS[word]
    return None


# -----------------------------------------------------------------------------
# A4: parse_bp
# -----------------------------------------------------------------------------
_BP_WORD_SEPARATORS = ["bata", "بٹہ", "بٹا", "by", "over"]


def parse_bp(text: str) -> Dict[str, Any]:
    """
    Parses blood pressure [systolic, diastolic] from free text.
    Accepts:
      "120/80", "120 / 80", "120 by 80", "120 over 80", "120-80", "120 80",
      "120 bata 80", "ek sau bees bata assi", "ek sau bees by assi", "١٢٠/٨٠".
    Rejects:
      systolic <= diastolic; values outside [60..260, 30..150]; 3+ numbers; single number.
    Returns:
      {"value": [sys, dia] | None, "evidence": str}
    """
    orig_text = text if text is not None else ""
    trimmed = orig_text.strip()
    evidence = trimmed

    if not trimmed:
        return {"value": None, "evidence": ""}

    norm = normalise_text(trimmed)

    # Convert word separators to slash
    norm_canonical = norm
    for sep in _BP_WORD_SEPARATORS:
        norm_canonical = re.sub(rf"\b{sep}\b", "/", norm_canonical)

    parts = None

    if "/" in norm_canonical:
        raw_parts = [p.strip() for p in norm_canonical.split("/") if p.strip()]
        if len(raw_parts) == 2:
            parts = raw_parts
        elif len(raw_parts) >= 3:
            return {"value": None, "evidence": evidence}

    if parts is None and "-" in norm_canonical:
        raw_parts = [p.strip() for p in norm_canonical.split("-") if p.strip()]
        if len(raw_parts) == 2:
            parts = raw_parts
        elif len(raw_parts) >= 3:
            return {"value": None, "evidence": evidence}

    if parts is None:
        digits = re.findall(r"\b\d+\b", norm_canonical)
        if len(digits) == 2:
            parts = [digits[0], digits[1]]
        elif len(digits) >= 3 or len(digits) == 1:
            return {"value": None, "evidence": evidence}

    if parts and len(parts) == 2:
        num1_res = parse_number(parts[0])
        num2_res = parse_number(parts[1])
        if num1_res["value"] is not None and num2_res["value"] is not None:
            sys_val = int(round(num1_res["value"]))
            dia_val = int(round(num2_res["value"]))

            # Rejections
            if sys_val <= dia_val:
                return {"value": None, "evidence": evidence}
            if not (BP_SYSTOLIC_MIN <= sys_val <= BP_SYSTOLIC_MAX):
                return {"value": None, "evidence": evidence}
            if not (BP_DIASTOLIC_MIN <= dia_val <= BP_DIASTOLIC_MAX):
                return {"value": None, "evidence": evidence}

            return {"value": [sys_val, dia_val], "evidence": evidence}

    return {"value": None, "evidence": evidence}
