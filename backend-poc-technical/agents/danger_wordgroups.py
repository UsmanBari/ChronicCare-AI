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
from dataclasses import dataclass, field
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
# NEGATION, PAST-TENSE & RESOLVED GUARDS
# =============================================================================

# Preceding negation cues (checked up to 4 tokens before match)
_PRECEDING_NEGATION_WORDS: set[str] = {
    "no", "not", "none", "denies", "denied", "never", "without", "hardly", "barely",
    "nahi", "nahin", "na", "mat", "baghair", "bina", "koi nahi", "kuch nahi",
    "نہیں", "نہ", "مت", "بغیر", "کوئی نہیں", "کچھ نہیں",
}

# Trailing / After negation patterns (e.g. Urdu "seene mein dard nahi hai", "اب نہیں ہے")
_TRAILING_NEGATION_PATTERNS: list[str] = [
    r"\b(?:nahi|nahin|na|mat)\s*(?:hai|tha|thi|the|hona|hua|raha|aayi|aaya)?\b",
    r"\b(?:koi\s+nahi|kuch\s+nahi)\b",
    r"(?:نہیں|نہ|مت)\s*(?:ہے|تھا|تھی|تھے|ہوا|رہا|آئی|آیا)?",
    r"(?:کوئی\s+نہیں|کچھ\s+نہیں)",
]

# Explicitly resolved cues ("ab theek", "theek ho gaya", "اب ٹھیک")
_RESOLVED_CUES: list[str] = [
    r"\b(?:ab|abb)\b.*?\b(?:theek|thik|behtar|achha|acha|nahi|nahin)\b",
    r"\b(?:theek|thik|behtar)\s+ho\s+(?:gaya|gaye|gayi|gya)\b",
    r"\b(?:now|currently)\s+(?:fine|better|resolved|okay|ok|gone)\b",
    r"(?:اب|ابھی).*?(?:ٹھیک|بہتر|اچھا|نہیں)",
    r"(?:ٹھیک|بہتر)\s*ہو\s*(?:گیا|گئی|گئے)",
]

# Historical / Past temporal cues (must be strictly historical, NOT ambiguous bare "kal")
_PAST_PATTERNS: list[str] = [
    r"\b(?:yesterday|last\s+year|last\s+month|last\s+week|months\s+ago|weeks\s+ago|days\s+ago|years\s+ago)\b",
    r"\b(?:in\s+the\s+past|history\s+of|previously|used\s+to|had\s+in\s+past)\b",
    r"\b(?:pichle\s+saal|pichlay\s+saal|saal\s+pehle|mahine\s+pehle|haftay\s+pehle|pehle\s+tha|pehle\s+thi)\b",
    r"\b(?:kal\s+tha|kal\s+thi|kal\s+raat\s+tha|kal\s+raat\s+thi)\b",  # "kal tha" is past; bare "kal" is NOT past
    r"(?:پچھلے\s+سال|سال\s+پہلے|مہینے\s+پہلے|ہفتے\s+پہلے|پہلے\s+تھا|پہلے\s+تھی)",
    r"(?:کل\s+تھا|کل\s+تھی|کل\s+رات\s+تھا|کل\s+رات\s+تھی)",
]


# =============================================================================
# ACUTE DANGER WORD GROUPS
# =============================================================================

# Group 1: Acute Coronary / Cardiac Crisis
_CHEST_BODY_RE = re.compile(
    r"\b(?:chest|breastbone|sternum|ribs|heart|left\s+arm)\b|"
    r"\b(?:seena|seenay|seene|chhati|chaati|dil)\b|"
    r"(?:سینہ|سینے|چھاتی|دل)",
    re.IGNORECASE,
)

_CHEST_SEVERITY_RE = re.compile(
    r"\b(?:crushing|pressure|tightness|squeezing|heavy|heaviness|burning|severe\s+ache|stabbing|radiating|intense\s+pain)\b|"
    r"\b(?:shadeed\s+dard|sakht\s+dard|bojh|dabao|jalan|sakht|khichao|phat\s+raha)\b|"
    r"(?:شدید\s+درد|سخت\s+درد|دباؤ|بوجھ|جلن|کھچاؤ|پھٹ\s+رہا)",
    re.IGNORECASE,
)

_CHEST_PAIN_COOCCUR_RE = re.compile(
    r"\b(?:pain|severe|crushing|pressure|tightness|heavy|squeezing|bojh|dabao|shadeed|sakht|dard)\b|"
    r"(?:درد|شدید|بوجھ|دباؤ|سخت)",
    re.IGNORECASE,
)

# Qualifiers for non-cardiac / non-respiratory mild sensations (e.g. heartburn, walk fatigue)
_MILD_QUALIFIER_RE = re.compile(
    r"\b(?:mild|slight|halka|halki|halkay|thora|thori|thoda|thodi)\b|"
    r"(?:ہلکا|ہلکی|ہلکے|تھوڑا|تھوڑی|معمولی)",
    re.IGNORECASE,
)
_SEVERE_QUALIFIER_RE = re.compile(
    r"\b(?:crushing|severe|shadeed|pressure|tightness|heavy|squeezing|sakht|dabao|bojh|cant\s+breathe|gasping)\b|"
    r"(?:شدید|سخت|دباؤ|بوجھ|پھٹ|دم\s+گھٹ)",
    re.IGNORECASE,
)

# Dental benign oral numbness
_DENTAL_PROCEDURE_RE = re.compile(
    r"\b(?:dental|dentist|tooth|teeth|daant|dant)\b|"
    r"(?:دانت|مسوڑھ|ڈینٹسٹ)",
    re.IGNORECASE,
)

# Group 2: Acute Cerebrovascular Event (Stroke / FAST)
_STROKE_FAST_PATTERNS: list[re.Pattern] = [
    # Face droop / crooked / numbness
    re.compile(
        r"\b(?:face|mouth|chehra|chehray|munh)\b.*?\b(?:droop(?:ing)?|crooked|numb(?:ness)?|paralyz(?:ed|is)?|terha|tedha|sunn|dhalak\w*)\b|"
        r"\b(?:droop(?:ing)?|crooked|numb(?:ness)?|paralyz(?:ed|is)?|terha|tedha|sunn|dhalak\w*)\b.*?\b(?:face|mouth|chehra|chehray|munh)\b|"
        r"(?:منہ|چہرہ|چہرے).*?(?:ٹیڑھا|سن|فالج|ڈھلک\w*)|(?:ٹیڑھا|سن|فالج|ڈھلک\w*).*?(?:منہ|چہرہ|چہرے)",
        re.IGNORECASE,
    ),
    # Arm / Leg / Unilateral weakness or numbness
    re.compile(
        r"\b(?:arm|hand|leg|foot|feet|bazu|baazu|haath|hath|taang|tang|paon|pair)\b.*?\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|sunn|kamzor|kamzori|jaan\s*(?:nahi|nahin))\b|"
        r"\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|sunn|kamzor|kamzori|jaan\s*(?:nahi|nahin))\b.*?\b(?:arm|hand|leg|foot|feet|bazu|baazu|haath|hath|taang|tang|paon|pair)\b|"
        r"\b(?:one\s+side|aik\s+taraf|ek\s+taraf|aadha\s+jism|adha\s+jism)\b.*?\b(?:weak(?:ness)?|numb(?:ness)?|paralyz(?:ed|is)?|falij|faalij|kamzor|kamzori|sunn|jaan\s*(?:nahi|nahin))\b|"
        r"\b(?:falij|faalij|hemiparesis|facial\s+droop)\b|"
        r"(?:بازو|ہاتھ|ٹانگ|پاؤں|پاوں|ایک\s+طرف|آدھا\s+جسم).*?(?:کمزور|کمزوری|سن|فالج|جان\s*(?:نہیں\s*رہی|نہیں\s*ہے|نکل\s*گئی))|"
        r"(?:کمزور|کمزوری|سن|فالج|جان\s*(?:نہیں\s*رہی|نہیں\s*ہے|نکل\s*گئی)).*?(?:بازو|ہاتھ|ٹانگ|پاؤں|پاوں|ایک\s+طرف|آدھا\s+جسم)",
        re.IGNORECASE,
    ),
    # Speech impairment / dysarthria
    re.compile(
        r"\b(?:slurr(?:ed)?\s+speech|cant\s+speak|cannot\s+speak|unable\s+to\s+speak|lost\s+speech)\b|"
        r"\b(?:bol\s+nahi\s+pa\s+rah(?:a|i|e|y)?|awaz\s+ladkhada|zuban\s+ladkhada|awaz\s+band)\b|"
        r"(?:بول\s+نہیں\s+پا\s+رہ(?:ا|ی|ے)?|آواز\s+لڑکھڑا|زبان\s+لڑکھڑا|آواز\s+بند)",
        re.IGNORECASE,
    ),
]

# Group 3: Acute Respiratory Distress
_BREATHING_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:cant\s+breathe|cannot\s+breathe|unable\s+to\s+breathe|struggling\s+to\s+breathe|gasping\s+for\s+air|suffocat(?:ing|ion))\b|"
        r"\b(?:severe\s+shortness\s+of\s+breath|shortness\s+of\s+breath\s+at\s+rest)\b|"
        r"\b(?:saans\s+nahi\s+aa\s+rah(?:a|i|e|y)?|dum\s+ghut|sans\s+ruk|saans\s+ruk\w*|saans\s+phool\w*|sans\s+phool\w*|saans\s+ukhad)\b|"
        r"(?:سانس\s+نہیں\s+آ\s+رہ(?:ا|ی|ے)?|دم\s+گھٹ|سانس\s*(?:بالکل\s*)?رک\w*|سانس\s*(?:بہت\s*)?پھول\w*|سانس.*?اکھڑ)",
        re.IGNORECASE,
    ),
]

# Group 4: Syncope / Unresponsiveness / Collapse
_SYNCOPE_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(?:unconscious|passed\s+out|fainted|blackout|blacked\s+out|collapsed|unresponsive)\b|"
        r"\b(?:behosh|be\s+hosh|be\s*sudh|gash\w*|chakkar\s+kha\s+kar\s+gir)\b|"
        r"(?:بے\s*ہوش|بے\s*سدھ|غش\w*|چکر\s+کھا\s+کر\s+گر)",
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
        r"(?:خون\s+کی\s+الٹی|الٹی\s+میں\s+خون)|"
        r"(?:پاخان[ہے۔\w]*.*?(?:کالا|سیاہ)|(?:کالا|سیاہ).*?پاخان[ہے۔\w]*)",
        re.IGNORECASE,
    ),
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WordGroupResult:
    is_danger: bool
    group: str | None = None
    matched_phrase: str | None = None
    cues: list[str] = field(default_factory=list)
    safety_note: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_danger": self.is_danger,
            "group": self.group,
            "matched_phrase": self.matched_phrase,
            "cues": self.cues,
            "safety_note": self.safety_note,
        }


# =============================================================================
# CORE DETECTION LOGIC
# =============================================================================

def _split_into_clauses(text: str) -> list[str]:
    """Splits text into clinical clauses at punctuation and conjunction boundaries."""
    parts = re.split(
        r"[,;:\.!\?\n\r،؛؟]+|\b(?:and|aur|lekin|magar|but)\b|(?:اور|لیکن|مگر)",
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
    Checks bidirectional and internal negation:
    1. Preceding window (up to 4 tokens before match_start).
    2. Trailing window (up to 6 tokens after match_end, e.g. 'seene mein dard nahi hai').
    3. Internal tokens within the matched span itself (e.g. 'face is not drooping'),
       EXCEPT when the matched phrase is an inability symptom where negation expresses the deficit
       (e.g. 'saans nahi aa rahi', 'bol nahi pa raha', 'cannot breathe', 'jaan nahi rahi').
    """
    matched_span = clause[match_start:match_end].strip().lower()
    is_inability = any(p in matched_span for p in [
        "saans nahi", "sans nahi", "saans ruk", "sans ruk",
        "سانس نہیں", "سانس رک",
        "bol nahi", "بول نہیں",
        "cant breathe", "cannot breathe", "unable to breathe",
        "cant speak", "cannot speak", "unable to speak",
        "jaan nahi", "جان نہیں",
    ])
    if not is_inability:
        int_tokens = re.findall(r"[\w']+|[\u0600-\u06FF]+", matched_span)
        if any(t in _PRECEDING_NEGATION_WORDS for t in int_tokens):
            return True

    preceding_text = clause[:match_start].strip().lower()
    preceding_tokens = re.findall(r"[\w']+|[\u0600-\u06FF]+", preceding_text)
    if any(tok in _PRECEDING_NEGATION_WORDS for tok in preceding_tokens[-4:]):
        return True

    trailing_text = clause[match_end:].strip().lower()
    trailing_tokens = re.findall(r"[\w']+|[\u0600-\u06FF]+", trailing_text)
    first_6_trailing = " ".join(trailing_tokens[:6])
    for pat in _TRAILING_NEGATION_PATTERNS:
        if re.search(pat, first_6_trailing):
            return True

    return False


def _is_past_or_resolved(clause: str, full_text: str) -> bool:
    """
    Checks if the acute symptom is strictly historical or explicitly resolved.
    Note: Bare 'kal' is NOT treated as past (e.g. 'kal se dard' is active).
    """
    low_clause = clause.lower()
    low_full = full_text.lower()

    # 1. Check resolved cues (e.g. 'ab theek ho gaya', 'ab nahi hai', 'اب ٹھیک')
    for pat in _RESOLVED_CUES:
        if re.search(pat, low_clause) or re.search(pat, low_full):
            return True

    # 2. Check explicit past patterns (e.g. 'last year', 'pichle saal', 'kal tha')
    for pat in _PAST_PATTERNS:
        if re.search(pat, low_clause) or re.search(pat, low_full):
            return True

    return False


def detect(text: str | None) -> WordGroupResult:
    """
    Pure deterministic clinical detector for acute danger word groups.
    Runs without network, LLM, or database dependencies.

    Returns:
        WordGroupResult indicating danger status, matched group, cues, and safety line.
    """
    if not text or not isinstance(text, str):
        return WordGroupResult(is_danger=False)

    clean_text = text.strip()
    if not clean_text:
        return WordGroupResult(is_danger=False)

    clauses = _split_into_clauses(clean_text)

    for clause in clauses:
        # Check Stroke FAST patterns
        for pat in _STROKE_FAST_PATTERNS:
            m = pat.search(clause)
            if m:
                # Benign dental oral numbness guard (local anesthesia without focal deficits)
                is_dental = bool(_DENTAL_PROCEDURE_RE.search(clause) or _DENTAL_PROCEDURE_RE.search(clean_text))
                if is_dental and ("منہ" in m.group(0) or "mouth" in m.group(0).lower() or "munh" in m.group(0).lower()):
                    if not any(k in clause.lower() for k in ["bazu", "haath", "taang", "arm", "leg", "speech", "bol", "آواز", "بازو", "ٹانگ", "ہاتھ"]):
                        continue
                if not _is_negated_clause(clause, m.start(), m.end()) and not _is_past_or_resolved(clause, clean_text):
                    return WordGroupResult(
                        is_danger=True,
                        group="stroke_fast_cue",
                        matched_phrase=m.group(0),
                        cues=[m.group(0)],
                        safety_note=SAFETY_NOTE_TEXTS,
                    )

        # Check Acute Respiratory Compromise
        for pat in _BREATHING_PATTERNS:
            m = pat.search(clause)
            if m:
                # Benign mild exertion / walk guard
                is_mild = bool(_MILD_QUALIFIER_RE.search(clause))
                has_sev = bool(_SEVERE_QUALIFIER_RE.search(clause))
                if is_mild and not has_sev:
                    continue
                if not _is_negated_clause(clause, m.start(), m.end()) and not _is_past_or_resolved(clause, clean_text):
                    return WordGroupResult(
                        is_danger=True,
                        group="breathing_distress",
                        matched_phrase=m.group(0),
                        cues=[m.group(0)],
                        safety_note=SAFETY_NOTE_TEXTS,
                    )

        # Check Syncope / Unresponsiveness
        for pat in _SYNCOPE_PATTERNS:
            m = pat.search(clause)
            if m:
                if not _is_negated_clause(clause, m.start(), m.end()) and not _is_past_or_resolved(clause, clean_text):
                    return WordGroupResult(
                        is_danger=True,
                        group="unresponsive_faint",
                        matched_phrase=m.group(0),
                        cues=[m.group(0)],
                        safety_note=SAFETY_NOTE_TEXTS,
                    )

        # Check Acute GI Hemorrhage
        for pat in _GI_BLEED_PATTERNS:
            m = pat.search(clause)
            if m:
                if not _is_negated_clause(clause, m.start(), m.end()) and not _is_past_or_resolved(clause, clean_text):
                    return WordGroupResult(
                        is_danger=True,
                        group="vomiting_blood",
                        matched_phrase=m.group(0),
                        cues=[m.group(0)],
                        safety_note=SAFETY_NOTE_TEXTS,
                    )

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
                elif not _is_negated_clause(clause, start_pos, end_pos) and not _is_past_or_resolved(clause, clean_text):
                    return WordGroupResult(
                        is_danger=True,
                        group="cardiac_chest_pain",
                        matched_phrase=f"{m_body.group(0)} + {m_sev.group(0)}",
                        cues=[m_body.group(0), m_sev.group(0)],
                        safety_note=SAFETY_NOTE_TEXTS,
                    )

    return WordGroupResult(is_danger=False)
