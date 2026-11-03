"""
Multilingual Composable Symptom Word-Groups Danger Phrase Detector (v1).

Clinical decision-support safety module for acute emergency symptom detection.
Gated behind DANGER_WORDGROUPS_ENABLED="true" (OFF by default).
Raise-only invariant: can ONLY raise check-in triage level to "review".
NEVER lowers a triage level. NEVER sets "urgent" or "emergency".

Author: Usman Bari (Lead Backend & Safety Architecture)
Review Status: Pending Clinician Review (D1)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

# =============================================================================
# CLINICAL SAFETY LINES (D1 Specification)
# =============================================================================

SAFETY_NOTE_TEXTS: dict[str, str] = {
    "en": "If this is an emergency, call 1122 now.",
    "ur": "اگر یہ ایمرجنسی ہے تو ابھی 1122 پر کال کریں۔",
    "roman_ur": "Agar yeh emergency hai to abhi 1122 par call karein.",
}


def get_safety_note(language: str = "en") -> str:
    lang = (language or "en").lower().strip()
    if lang in ("ur", "urdu"):
        return SAFETY_NOTE_TEXTS["ur"]
    if lang in ("roman_ur", "roman_urdu", "roman"):
        return SAFETY_NOTE_TEXTS["roman_ur"]
    return SAFETY_NOTE_TEXTS["en"]


def is_danger_wordgroups_enabled() -> bool:
    """Flag guard: DANGER_WORDGROUPS_ENABLED='true' (case-insensitive). OFF by default."""
    return os.getenv("DANGER_WORDGROUPS_ENABLED", "").strip().lower() == "true"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WordGroupResult:
    """
    Result of danger wordgroup detection.
    Fields:
      is_danger: bool
      group: str | None (cardiac_chest_pain, stroke_fast_cue, breathing_distress,
                         unresponsive_faint, vomiting_blood)
      suppressed_by: str | None (None | 'negation' | 'past' | 'resolved')
    """
    is_danger: bool
    group: str | None = None
    suppressed_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_danger": self.is_danger,
            "group": self.group,
            "suppressed_by": self.suppressed_by,
        }


# =============================================================================
# APOSTROPHE NORMALIZATION & CONTRACTION EXPANSION
# =============================================================================

_CONTRACTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:can't|cant)\b", re.IGNORECASE), "cannot"),
    (re.compile(r"\b(?:couldn't|couldnt)\b", re.IGNORECASE), "could not"),
    (re.compile(r"\b(?:don't|dont)\b", re.IGNORECASE), "do not"),
    (re.compile(r"\b(?:doesn't|doesnt)\b", re.IGNORECASE), "does not"),
    (re.compile(r"\b(?:didn't|didnt)\b", re.IGNORECASE), "did not"),
    (re.compile(r"\b(?:haven't|havent)\b", re.IGNORECASE), "have not"),
    (re.compile(r"\b(?:hasn't|hasnt)\b", re.IGNORECASE), "has not"),
    (re.compile(r"\b(?:isn't|isnt)\b", re.IGNORECASE), "is not"),
    (re.compile(r"\b(?:wasn't|wasnt)\b", re.IGNORECASE), "was not"),
    (re.compile(r"\b(?:won't|wont)\b", re.IGNORECASE), "will not"),
]


def _normalize_text(text: str) -> str:
    """Normalizes curly apostrophes, backticks, and expands English contractions."""
    t = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    for pattern, replacement in _CONTRACTIONS:
        t = pattern.sub(replacement, t)
    return t


# =============================================================================
# URDU SCRIPT WORD BOUNDARIES & GUARDS
# =============================================================================
# Python \b is ASCII-only. In Urdu script, (?<![\u0600-\u06FF]) and (?![\u0600-\u06FF])
# ensure no adjacent Arabic/Urdu Unicode character precedes or follows the token,
# preventing false substring matches (e.g. 'سن' in 'سنبھل' or 'دل' in 'بدل').
U_PRE = r"(?<![\u0600-\u06FF])"
U_POST = r"(?![\u0600-\u06FF])"

# Preceding negation cues (checked within 4 tokens before match)
_PRECEDING_NEGATION_WORDS: set[str] = {
    "no", "not", "none", "denies", "denied", "never", "without", "hardly", "barely",
    "nahi", "nahin", "na", "mat", "baghair", "bina", "koi nahi", "kuch nahi",
    "نہیں", "نہ", "مت", "بغیر", "کوئی نہیں", "کچھ نہیں",
}

# Inability constructions in Roman Urdu, English & Urdu script.
# Idioms expressing functional deficits (paralysis, aphasia, dyspnea) confirming danger,
# NOT symptom negations: 'uthaya nahi ja raha', 'bol nahi pa raha', 'saans nahi aa rahi',
# 'could not move his arm', 'jaan nahi rahi', 'جان نہیں رہی'.
_INABILITY_PATTERNS: list[str] = [
    r"\b(?:nahi|nahin)\s+(?:ja\s+rah[aiye]|pa\s+rah[aiye]|aa\s+rah[aiye]|hua\s+ja\s+raha)\b",
    r"\b(?:cant|cannot|could\s+not|unable\s+to)\s+(?:lift|move|speak|talk|walk|stand|breathe|feel)\b",
    r"\bjaan\s*(?:nahi|nahin)\b",
    U_PRE + r"(?:نہیں|نہ)\s+(?:جا\s+رہ[ایہے]|پا\s+رہ[ایہے]|آ\s+رہ[ایہے]|ہو\s+پا\s+رہ)" + U_POST,
    U_PRE + r"جان\s*(?:نہیں\s*رہی|نہیں\s*ہے|نکل\s*گئی)" + U_POST,
]
_INABILITY_RE = re.compile("|".join(_INABILITY_PATTERNS), re.IGNORECASE)

# Trailing / After negation patterns (e.g. 'seene mein dard nahi hai', 'سن نہیں ہوا')
_TRAILING_NEGATION_PATTERNS: list[str] = [
    r"\b(?:nahi|nahin|na|mat)\s*(?:hai|tha|thi|the|hona|hua|raha|aayi|aaya)?\b",
    r"\b(?:koi\s+nahi|kuch\s+nahi)\b",
    U_PRE + r"(?:نہیں|نہ|مت)(?![\u0600-\u06FF])\s*(?:ہے|تھا|تھی|تھے|ہوا|رہا|آئی|آیا)?",
    U_PRE + r"(?:کوئی\s+نہیں|کچھ\s+نہیں)" + U_POST,
]
_TRAILING_NEGATION_RE = re.compile("|".join(_TRAILING_NEGATION_PATTERNS), re.IGNORECASE)

# Explicitly resolved cues:
# 'ab / اب' only resolves if followed by 'theek / behtar / achha / ٹھیک / بہتر / اچھا' (within 3 words)
# or 'theek ho gaya / ٹھیک ہو گیا'.
# 'nahi / nahin / نہیں' and 'ابھی' are strictly excluded from resolved patterns.
_RESOLVED_CUES: list[str] = [
    r"\b(?:ab|abb)\b(?:\s+\w+){0,3}\s+(?:theek|thik|behtar|achha|acha)\b",
    r"\b(?:theek|thik|behtar)\s+ho\s+(?:gaya|gaye|gayi|gya)\b",
    r"\b(?:now|currently)\s+(?:\w+\s+){0,3}(?:fine|better|resolved|okay|ok|gone)\b",
    U_PRE + r"اب(?:\s+[\u0600-\u06FF]+){0,3}\s+(?:ٹھیک|بہتر|اچھا)" + U_POST,
    U_PRE + r"(?:ٹھیک|بہتر)\s*ہو\s*(?:گیا|گئی|گئے)" + U_POST,
]
_RESOLVED_RE = re.compile("|".join(_RESOLVED_CUES), re.IGNORECASE)

# Ongoing time indicators: 'since', 'kal se', 'subah se', 'do din se', 'کل سے', 'صبح سے'
# describe active ongoing symptoms and must NEVER be treated as historical past.
_ONGOING_TIME_PATTERNS: list[str] = [
    r"\b(?:since|from)\b",
    r"\b(?:kal|subah|shaam|raat|do\s+din|teen\s+din|\w+)\s+se\b",
    U_PRE + r"(?:کل|صبح|شام|رات|دو\s*دن|تین\s*دن|ایک\s*ہفتے|ایک\s*مہینے|کئی\s*دن)\s*سے" + U_POST,
]
_ONGOING_TIME_RE = re.compile("|".join(_ONGOING_TIME_PATTERNS), re.IGNORECASE)

# Historical / Past temporal cues (must be strictly historical with explicit past verbs)
_PAST_PATTERNS: list[str] = [
    r"\b(?:history\s+of|used\s+to|previously|in\s+the\s+past)\b",
    r"\bhad\b.*?\b(?:ago|last\s+year|last\s+month|yesterday)\b",
    r"\byesterday\b",
    r"\b(?:last\s+(?:year|month|week)|(?:months|weeks|days|years|\d+\s+days?|\d+\s+weeks?|\d+\s+months?|\d+\s+years?)\s+ago)\b",
    r"\b(?:pehle\s+(?:tha|thi|the)|(?:tha|thi|the)\s+pehle)\b",
    r"\b(?:kal|pichle\s+(?:saal|mahine|hafte|haftay|din)|pichlay\s+(?:saal|mahine|hafte|haftay|din)|saal\s+pehle|mahine\s+pehle|haftay\s+pehle)\b.*?\b(?:tha|thi|the)\b",
    r"\b(?:hua\s+tha|hui\s+thi|hue\s+the|aaya\s+tha|aayi\s+thi|dard\s+tha|dard\s+thi)\b",
    r"\b(?:hota\s+tha|hoti\s+thi|hote\s+the|hotay\s+the)\b",
    U_PRE + r"(?:پہلے\s+(?:تھا|تھی|تھے)|(?:تھا|تھی|تھے)\s+پہلے)" + U_POST,
    U_PRE + r"(?:کل|پچھلے\s+(?:سال|مہینے|ہفتے|دن)|سال\s+پہلے|مہینے\s+پہلے|ہفتے\s+پہلے).*?(?:تھا|تھی|تھے)" + U_POST,
    U_PRE + r"(?:ہوا\s+تھا|ہوئی\s+تھی|ہوئے\s+تھے|آیا\s+تھا|آئی\s+تھی|درد\s+تھا|درد\s+تھی)" + U_POST,
    U_PRE + r"(?:ہوتا\s+تھا|ہوتی\s+تھی|ہوتے\s+تھے)" + U_POST,
]
_PAST_RE = re.compile("|".join(_PAST_PATTERNS), re.IGNORECASE)


# =============================================================================
# ACUTE DANGER WORD GROUPS
# =============================================================================

# Group 1: Acute Coronary / Cardiac Crisis
_CHEST_BODY_RE = re.compile(
    r"\b(?:chest|breastbone|sternum|ribs|heart|left\s+arm)\b|"
    r"\b(?:seena|seenay|seene|chhati|chaati|dil)\b|"
    + U_PRE + r"(?:سینہ|سینے|چھاتی|دل)" + U_POST,
    re.IGNORECASE,
)

_CHEST_SEVERITY_RE = re.compile(
    r"\b(?:crushing|pressure|tightness|squeezing|heavy|heaviness|burning|severe\s+ache|stabbing|radiating|intense\s+pain)\b|"
    r"\b(?:shadeed\s+dard|sakht\s+dard|bojh|dabao|bhaari|bhari|bhaary|jalan|sakht|khichao|phat\s+raha)\b|"
    + U_PRE + r"(?:شدید\s+درد|سخت\s+درد|دباؤ|دباو|بوجھ|بھاری|جلن|کھچاؤ|پھٹ\s+رہا)" + U_POST,
    re.IGNORECASE,
)

_CHEST_PAIN_COOCCUR_RE = re.compile(
    r"\b(?:pain|severe|crushing|pressure|tightness|heavy|squeezing|bojh|dabao|bhaari|bhari|bhaary|shadeed|sakht|dard)\b|"
    + U_PRE + r"(?:درد|شدید|بوجھ|بھاری|دباؤ|دباو|سخت)" + U_POST,
    re.IGNORECASE,
)

# Qualifiers for non-cardiac / non-respiratory mild sensations (e.g. heartburn, walk fatigue)
_MILD_QUALIFIER_RE = re.compile(
    r"\b(?:mild|slight|halka|halki|halkay|thora|thori|thoda|thodi)\b|"
    + U_PRE + r"(?:ہلکا|ہلکی|ہلکے|تھوڑا|تھوڑی|معمولی)" + U_POST,
    re.IGNORECASE,
)
_SEVERE_QUALIFIER_RE = re.compile(
    r"\b(?:crushing|severe|shadeed|pressure|tightness|heavy|squeezing|sakht|dabao|bojh|bhaari|bhari|bhaary|cant\s+breathe|cannot\s+breathe|gasping)\b|"
    + U_PRE + r"(?:شدید|سخت|دباؤ|دباو|بوجھ|بھاری|پھٹ|دم\s+گھٹ)" + U_POST,
    re.IGNORECASE,
)

# Dental benign oral numbness
_DENTAL_PROCEDURE_RE = re.compile(
    r"\b(?:dental|dentist|tooth|teeth|daant|dant)\b|"
    + U_PRE + r"(?:دانت|مسوڑھ\w*|ڈینٹسٹ)" + U_POST,
    re.IGNORECASE,
)

# Group 2: Acute Cerebrovascular Event (Stroke / FAST)
_STROKE_FAST_PATTERNS: list[re.Pattern] = [
    # Face droop / crooked / numbness
    re.compile(
        r"\b(?:face|mouth|chehra|chehray|munh)\b.*?\b(?:droop(?:ing)?|crooked|numb(?:ness)?|paralyz(?:ed|is)?|terha|tedha|sunn|dhalak\w*)\b|"
        r"\b(?:droop(?:ing)?|crooked|numb(?:ness)?|paralyz(?:ed|is)?|terha|tedha|sunn|dhalak\w*)\b.*?\b(?:face|mouth|chehra|chehray|munh)\b|"
        + U_PRE + r"(?:منہ|چہرہ|چہرے)" + U_POST + r".*?" + U_PRE + r"(?:ٹیڑھا|سن|فالج|ڈھلک\w*)" + U_POST + r"|"
        + U_PRE + r"(?:ٹیڑھا|سن|فالج|ڈھلک\w*)" + U_POST + r".*?" + U_PRE + r"(?:منہ|چہرہ|چہرے)" + U_POST,
        re.IGNORECASE,
    ),
    # Arm / Leg / Unilateral weakness, numbness or motor inability
    re.compile(
        r"\b(?:arm|hand|leg|foot|feet|bazu|baazu|haath|hath|taang|tang|paon|pair)\b.*?\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|sunn|kamzor|kamzori|jaan\s*(?:nahi|nahin)|(?:could\s+not|cannot|cant|unable\s+to)\s+(?:move|lift|feel))\b|"
        r"\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|sunn|kamzor|kamzori|jaan\s*(?:nahi|nahin)|(?:could\s+not|cannot|cant|unable\s+to)\s+(?:move|lift|feel))\b.*?\b(?:arm|hand|leg|foot|feet|bazu|baazu|haath|hath|taang|tang|paon|pair)\b|"
        r"\b(?:one\s+side|aik\s+taraf|ek\s+taraf|aadha\s+jism|adha\s+jism)\b.*?\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|falij|faalij|kamzor|kamzori|sunn|jaan\s*(?:nahi|nahin))\b|"
        r"\b(?:falij|faalij|hemiparesis|facial\s+droop)\b|"
        + U_PRE + r"(?:بازو|ہاتھ|ٹانگ|پاؤں|پاوں|ایک\s+طرف|آدھا\s+جسم)" + U_POST + r".*?" + U_PRE + r"(?:کمزور|کمزوری|سن|فالج|جان\s*(?:نہیں\s*رہی|نہیں\s*ہے|نکل\s*گئی))" + U_POST + r"|"
        + U_PRE + r"(?:کمزور|کمزوری|سن|فالج|جان\s*(?:نہیں\s*رہی|نہیں\s*ہے|نکل\s*گئی))" + U_POST + r".*?" + U_PRE + r"(?:بازو|ہاتھ|ٹانگ|پاؤں|پاوں|ایک\s+طرف|آدھا\s+جسم)" + U_POST,
        re.IGNORECASE,
    ),
    # Speech impairment / dysarthria
    re.compile(
        r"\b(?:slurr(?:ed)?\s+speech|lost\s+speech)\b|"
        r"\b(?:cant|cannot|could\s+not|unable\s+to)\s+(?:speak|talk)(?!\s+(?:to|with)\s+(?:the\s+)?(?:doctor|dr|nurse|physician|clinic|hospital|someone|anybody|anyone|him|her|them)\b)\b|"
        r"\b(?:bol\s+nahi\s+pa\s+rah(?:a|i|e|y)?|awaz\s+ladkhada|zuban\s+ladkhada|awaz\s+band)\b|"
        + U_PRE + r"(?:بول\s+نہیں\s+پا\s+رہ(?:ا|ی|ے)?|آواز\s+لڑکھڑا\w*|زبان\s+لڑکھڑا\w*|آواز\s+بند)" + U_POST,
        re.IGNORECASE,
    ),
]

# Group 3: Acute Respiratory Distress
_BREATHING_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:cant\s+breathe|cannot\s+breathe|unable\s+to\s+breathe|struggling\s+to\s+breathe|gasping\s+for\s+air|suffocat(?:ing|ion))\b|"
        r"\b(?:severe\s+shortness\s+of\s+breath|shortness\s+of\s+breath\s+at\s+rest)\b|"
        r"\b(?:saans\s+nahi\s+aa\s+rah(?:a|i|e|y)?|dum\s+ghut|sans\s+ruk|saans\s+ruk\w*|saans\s+phool\w*|sans\s+phool\w*|saans\s+ukhad)\b|"
        + U_PRE + r"(?:سانس\s+نہیں\s+آ\s+رہ(?:ا|ی|ے)?|دم\s+گھٹ|سانس\s*(?:بالکل\s*)?رک\w*|سانس\s*(?:بہت\s*)?پھول\w*|سانس.*?اکھڑ\w*)" + U_POST,
        re.IGNORECASE,
    ),
]

# Group 4: Syncope / Unresponsiveness / Collapse
_SYNCOPE_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:unconscious|passed\s+out|fainted|blackout|blacked\s+out|collapsed|unresponsive)\b|"
        r"\b(?:behosh|be\s+hosh|be\s*sudh|gash\w*|chakkar\s+kha\s+kar\s+gir)\b|"
        + U_PRE + r"(?:بے\s*ہوش|بے\s*سدھ|غش\w*|چکر\s+کھا\s+کر\s+گر\w*)" + U_POST,
        re.IGNORECASE,
    ),
]

# Group 5: Acute GI Hemorrhage (Hematemesis / Melena)
_GI_BLEED_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:vomit(?:ing)?\s+blood|blood\s+in\s+vomit|coffee\s+ground\s+emesis)\b|"
        r"\b(?:throw(?:ing)?\s+up|vomit(?:ing)?|threw\s+up)\b.*?\bblood\b|"
        r"\b(?:khoon\s+ki\s+ulti|ulti\s+mein\s+khoon|khoon\s+ke\s+dast)\b|"
        r"\b(?:black\s+tarry\s+stool|melena)\b|"
        r"\b(?:pakhana\w*.*?(?:kala|siyah)|(?:kala|siyah).*?pakhana\w*)\b|"
        + U_PRE + r"(?:خون\s+کی\s+الٹی|الٹی\s+میں\s+خون)" + U_POST + r"|"
        + U_PRE + r"(?:پاخان\w*.*?(?:کالا|سیاہ)|(?:کالا|سیاہ).*?پاخان\w*)" + U_POST,
        re.IGNORECASE,
    ),
]


# =============================================================================
# CLAUSE-LEVEL PROCESSING LOGIC
# =============================================================================

def _split_into_clauses(text: str) -> list[str]:
    """Splits text into clinical clauses at punctuation and conjunction boundaries."""
    parts = re.split(
        r"[,;:\.!\?\n\r،؛؟]+|\b(?:and|aur|lekin|magar|but)\b|" + U_PRE + r"(?:اور|لیکن|مگر)" + U_POST,
        text,
        flags=re.IGNORECASE,
    )
    clauses: list[str] = []
    for p in parts:
        c = p.strip()
        if c:
            clauses.append(c)
    return clauses if clauses else [text.strip()]


def _is_negated_clause(clause: str, match_start: int, match_end: int) -> bool:
    """
    Checks bidirectional and internal negation strictly within the clause:
    1. Preceding window (up to 4 tokens before match_start).
    2. Trailing window after match_end. Inability constructions ('uthaya nahi ja raha',
       'نہیں جا رہا', 'could not move', 'jaan nahi rahi') confirm deficits and do NOT count as symptom negation.
    3. Internal tokens within the matched span itself, unless the span is an inability symptom.
    """
    matched_span = clause[match_start:match_end].strip().lower()
    is_inability = bool(_INABILITY_RE.search(matched_span))
    if not is_inability:
        int_tokens = re.findall(r"[\w']+|[\u0600-\u06FF]+", matched_span)
        if any(t in _PRECEDING_NEGATION_WORDS for t in int_tokens):
            return True

    preceding_text = clause[:match_start].strip().lower()
    preceding_tokens = re.findall(r"[\w']+|[\u0600-\u06FF]+", preceding_text)
    if any(tok in _PRECEDING_NEGATION_WORDS for tok in preceding_tokens[-4:]):
        return True

    trailing_text = clause[match_end:].strip().lower()
    cleaned_trailing = _INABILITY_RE.sub("", trailing_text)
    if _TRAILING_NEGATION_RE.search(cleaned_trailing):
        return True

    return False


def _is_past_clause(clause: str) -> bool:
    """
    Evaluates whether the clause describes historical events.
    Ongoing time indicators ('since', 'kal se', 'صبح سے') immediately disqualify past.
    """
    if _ONGOING_TIME_RE.search(clause):
        return False
    return bool(_PAST_RE.search(clause))


def _is_resolved_clause(clause: str) -> bool:
    """Evaluates whether the clause explicitly describes a resolved state."""
    return bool(_RESOLVED_RE.search(clause))


def detect(text: str | None) -> WordGroupResult:
    """
    Pure deterministic clinical detector for acute danger word groups.
    Runs without network, LLM, or database dependencies.

    Returns:
        WordGroupResult indicating danger status, matched group, and suppression reason.
    """
    if not text or not isinstance(text, str):
        return WordGroupResult(is_danger=False)

    clean_text = _normalize_text(text.strip())
    if not clean_text:
        return WordGroupResult(is_danger=False)

    clauses = _split_into_clauses(clean_text)
    suppressed_info: tuple[str, str] | None = None

    for clause in clauses:
        # Check Stroke FAST patterns
        for pat in _STROKE_FAST_PATTERNS:
            m = pat.search(clause)
            if m:
                # Benign dental oral numbness guard (local anesthesia without focal deficits)
                is_dental = bool(_DENTAL_PROCEDURE_RE.search(clause))
                if is_dental and ("منہ" in m.group(0) or "mouth" in m.group(0).lower() or "munh" in m.group(0).lower()):
                    if not any(k in clause.lower() for k in ["bazu", "haath", "taang", "arm", "leg", "speech", "bol", "آواز", "بازو", "ٹانگ", "ہاتھ"]):
                        continue
                if _is_negated_clause(clause, m.start(), m.end()):
                    suppressed_info = ("negation", "stroke_fast_cue")
                    continue
                if _is_past_clause(clause):
                    suppressed_info = ("past", "stroke_fast_cue")
                    continue
                if _is_resolved_clause(clause):
                    suppressed_info = ("resolved", "stroke_fast_cue")
                    continue
                return WordGroupResult(is_danger=True, group="stroke_fast_cue")

        # Check Acute Respiratory Compromise
        for pat in _BREATHING_PATTERNS:
            m = pat.search(clause)
            if m:
                # Benign mild exertion / walk guard
                is_mild = bool(_MILD_QUALIFIER_RE.search(clause))
                has_sev = bool(_SEVERE_QUALIFIER_RE.search(clause))
                if is_mild and not has_sev:
                    continue
                if _is_negated_clause(clause, m.start(), m.end()):
                    suppressed_info = ("negation", "breathing_distress")
                    continue
                if _is_past_clause(clause):
                    suppressed_info = ("past", "breathing_distress")
                    continue
                if _is_resolved_clause(clause):
                    suppressed_info = ("resolved", "breathing_distress")
                    continue
                return WordGroupResult(is_danger=True, group="breathing_distress")

        # Check Syncope / Unresponsiveness
        for pat in _SYNCOPE_PATTERNS:
            m = pat.search(clause)
            if m:
                if _is_negated_clause(clause, m.start(), m.end()):
                    suppressed_info = ("negation", "unresponsive_faint")
                    continue
                if _is_past_clause(clause):
                    suppressed_info = ("past", "unresponsive_faint")
                    continue
                if _is_resolved_clause(clause):
                    suppressed_info = ("resolved", "unresponsive_faint")
                    continue
                return WordGroupResult(is_danger=True, group="unresponsive_faint")

        # Check Acute GI Hemorrhage
        for pat in _GI_BLEED_PATTERNS:
            m = pat.search(clause)
            if m:
                if _is_negated_clause(clause, m.start(), m.end()):
                    suppressed_info = ("negation", "vomiting_blood")
                    continue
                if _is_past_clause(clause):
                    suppressed_info = ("past", "vomiting_blood")
                    continue
                if _is_resolved_clause(clause):
                    suppressed_info = ("resolved", "vomiting_blood")
                    continue
                return WordGroupResult(is_danger=True, group="vomiting_blood")

        # Check Cardiac / Chest Pain Word Group (Composable: Body + Severity/Pain)
        m_body = _CHEST_BODY_RE.search(clause)
        if m_body:
            m_sev = _CHEST_SEVERITY_RE.search(clause) or _CHEST_PAIN_COOCCUR_RE.search(clause)
            if m_sev:
                start_pos = min(m_body.start(), m_sev.start())
                end_pos = max(m_body.end(), m_sev.end())
                # Benign mild heartburn / indigestion guard
                is_mild = bool(_MILD_QUALIFIER_RE.search(clause))
                has_sev = bool(_SEVERE_QUALIFIER_RE.search(clause))
                if is_mild and not has_sev:
                    pass
                elif _is_negated_clause(clause, start_pos, end_pos):
                    suppressed_info = ("negation", "cardiac_chest_pain")
                elif _is_past_clause(clause):
                    suppressed_info = ("past", "cardiac_chest_pain")
                elif _is_resolved_clause(clause):
                    suppressed_info = ("resolved", "cardiac_chest_pain")
                else:
                    return WordGroupResult(is_danger=True, group="cardiac_chest_pain")

    if suppressed_info:
        return WordGroupResult(is_danger=False, group=suppressed_info[1], suppressed_by=suppressed_info[0])
    return WordGroupResult(is_danger=False)
