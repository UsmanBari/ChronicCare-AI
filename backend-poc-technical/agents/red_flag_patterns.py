"""
backend-poc-technical/agents/red_flag_patterns.py

Tolerant, negation-aware, multi-lingual red flag pattern matcher for
clinical Stage-1 triage emergencies across English, Urdu script, and Roman Urdu.

Covers five canonical emergency categories:
1. chest_pain
2. breathing
3. confusion_and_stroke
4. loss_of_consciousness
5. dka_vomiting_high_glucose

Key architectural rules:
- Negation-aware: Negation tokens ("no", "not", "nahi", "نہیں", "without", "never") negate
  ONLY symptom words ("no chest pain", "dard nahi hai"), NEVER inability phrases
  ("saans nahi aa rahi", "pani nahi ruk raha").
- Remote past suppression: "5 years ago", "bachpan mein" do not hit unless a
  current-tense marker ("now", "aaj", "abhi") is also present.
- Exertion / rest suppression: Exertion coupled with rest relief ("breathless when walking fast,
  better after resting") indicates chronic exertional symptoms, not an acute emergency.
- Chronic qualifier suppression: "for years", "saalon se" suppresses chronic neuropathy / ache hits.
- Emotional "dil": "dil mein dard" without physical cardiac cues (or with emotional words like "yaad")
  does not hit.
- Fainting rule: Fainting that recovered ("gir gaya phir theek ho gaya", "fainted but I'm fine now")
  stays on the wordgroup/review path. Only fainting with no recovery or not waking is Red.
- No-throw guarantee: All matching is wrapped in a safe handler returning (False, None) on any error.
"""

import re
import unicodedata
from typing import Optional, Tuple, List


# Module configuration for window tolerance (architectural invariant verified by mutation M-RF-1)
MAX_WINDOW_WORDS: int = 6


# =============================================================================
# Normalization Helpers
# =============================================================================

_APOSTROPHE_REGEX = re.compile(r"['’`]")
_PUNCT_REGEX = re.compile(r"[\.,!?;:،۔\"()\[\]\{\}\-–—/\\_~*#@$^&+=|<>]")
_MULTI_SPACE_REGEX = re.compile(r"\s+")

# Common Urdu script character normalization mapping
_URDU_CHAR_MAP = {
    "\u064a": "\u06cc",  # Arabic Yeh -> Urdu Yeh (ی)
    "\u0649": "\u06cc",  # Alef Maksura -> Urdu Yeh (ی)
    "\u0643": "\u06a9",  # Arabic Kaf -> Urdu Keheh (ک)
    "\u06c1": "\u06c1",  # Goal Heh
    "\u0629": "\u06c1",  # Teh Marbuta -> Heh
    "\u200c": " ",       # Zero-width non-joiner -> space
    "\u200d": "",        # Zero-width joiner
    "\u200e": "",        # Left-to-right mark
    "\u200f": "",        # Right-to-left mark
    "\ufeff": "",        # Byte order mark
}

# Roman Urdu phonetic/spelling variation normalization
_ROMAN_URDU_SPELLINGS = [
    (r"\bmein\b", "me"),
    (r"\bmain\b", "me"),
    (r"\bmen\b", "me"),
    (r"\bbohat\b", "bohot"),
    (r"\bbahut\b", "bohot"),
    (r"\bbht\b", "bohot"),
    (r"\bseene\b", "seena"),
    (r"\bseenay\b", "seena"),
    (r"\bsene\b", "seena"),
    (r"\bsenay\b", "seena"),
    (r"\bsaans\b", "sans"),
    (r"\bbaazu\b", "bazu"),
    (r"\bbazoo\b", "bazu"),
    (r"\bnahin\b", "nahi"),
    (r"\bnahe\b", "nahi"),
    (r"\bnhi\b", "nahi"),
    (r"\bnhn\b", "nahi"),
    (r"\bpaani\b", "pani"),
    (r"\bshadeed\b", "shadeed"),
    (r"\bshaded\b", "shadeed"),
    (r"\bshdeed\b", "shadeed"),
    (r"\bdabao\b", "dabao"),
    (r"\bdabaw\b", "dabao"),
    (r"\bdbao\b", "dabao"),
    (r"\bjabray\b", "jabra"),
    (r"\bjabde\b", "jabra"),
    (r"\bjabrey\b", "jabra"),
    (r"\bzabaan\b", "zaban"),
    (r"\bzuban\b", "zaban"),
]


def normalize_text(text: str) -> str:
    """Normalizes Unicode, Urdu script variants, punctuation, and whitespace."""
    if not text:
        return ""
    # Unicode NFKC normalization
    s = unicodedata.normalize("NFKC", text)

    # Normalize Urdu script letter variants
    for ch, repl in _URDU_CHAR_MAP.items():
        s = s.replace(ch, repl)

    s = s.lower()

    # Strip apostrophes before general punctuation so can't -> cant, don't -> dont
    s = _APOSTROPHE_REGEX.sub("", s)

    # Replace punctuation with space
    s = _PUNCT_REGEX.sub(" ", s)

    # Normalize Roman Urdu common spellings
    for pattern, repl in _ROMAN_URDU_SPELLINGS:
        s = re.sub(pattern, repl, s)

    # Collapse multiple spaces
    s = _MULTI_SPACE_REGEX.sub(" ", s).strip()
    return s


# =============================================================================
# Context Suppressions: Past, Exertion+Rest, Chronic, Emotional, Resolved
# =============================================================================

_PAST_PATTERNS = [
    r"\b\d+\s*(?:years?|yrs?|months?|weeks?)\s+ago\b",
    r"\b(?:years?|months?)\s+ago\b",
    r"\blast\s+(?:year|month|week)\b",
    r"\b(?:in\s+my\s+)?childhood\b",
    r"\bwhen\s+i\s+was\s+(?:young|a\s+child)\b",
    r"\bhistory\s+of\b",
    r"\b\d+\s*(?:saal|baras|mahine|hafte)\s+pehle\b",
    r"\b(?:saal|mahine|hafte|baras)\s+pehle\b",
    r"\bpichle\s+(?:saal|mahine|hafte)\b",
    r"\bbachpan\s+me\b",
    r"\bpehle\s+kabhi\b",
    r"\bpehle\s+(?:\w+\s+){0,3}(?:tha|thi|the)\b",
    r"\b\d+\s*(?:سال|مہینے|ہفتے)\s*پہلے\b",
    r"\b(?:سال|مہینے|ہفتے)\s*پہلے\b",
    r"\bپچھلے\s*(?:سال|مہینے|ہفتے)\b",
    r"\bبچپن\s*میں\b",
    r"\bپہلے\s*(?:\S+\s*){0,3}(?:تھا|تھی|تھے)\b",
]

_CURRENT_PATTERNS = [
    r"\b(?:right\s+)?now\b",
    r"\btoday\b",
    r"\bcurrently\b",
    r"\bat\s+(?:this|the)\s+moment\b",
    r"\babhi\b",
    r"\baaj\b",
    r"\bis\s+waqt\b",
    r"\bdobara\b",
    r"\bphir\s+se\b",
    r"\bابھی\b",
    r"\bآج\b",
    r"\bاس\s*وقت\b",
    r"\bدوبارہ\b",
    r"\پھر\s*سے\b",
]

_RESOLVED_PATTERNS = [
    r"\b(?:fine|better|okay|ok|normal)\s+now\b",
    r"\bcompletely\s+fine\b",
    r"\bfully\s+recovered\b",
    r"\bab\s+(?:bilkul\s+)?(?:theek|behtar|achha)\b",
    r"\btheek\s+(?:ho\s+gaya|hai|hoon|hun)\b",
    r"\bاب\s*(?:بالکل\s*)?(?:ٹھیک|بہتر)\b",
    r"\bٹھیک\s*(?:ہو\s*گیا|ہوں|ہے)\b",
]

_EXERTION_PATTERNS = [
    r"\b(?:walking\s+fast|running|jogging|exercise|exercising|climbing\s+stairs|walking\s+upstairs|on\s+exertion)\b",
    r"\b(?:tez\s+chalne|bhagne|kasrat|warjish|seedhiyan\s+chadhne)\b",
    r"\b(?:تیز\s*چلنے|بھاگنے|ورزش|سیڑھیاں\s*چڑھنے)\b",
]

_REST_RELIEF_PATTERNS = [
    r"\b(?:better\s+(?:after|with)\s+rest(?:ing)?|relieved\s+by\s+rest|goes\s+away\s+(?:with|after)\s+rest(?:ing)?)\b",
    r"\b(?:aaram\s+karne\s+se\s+(?:behtar|theek)|aaram\s+se\s+(?:behtar|theek)|aaram\s+ke\s+baad\s+(?:behtar|theek))\b",
    r"\b(?:آرام\s*کرنے\s*سے\s*(?:بہتر|ٹھیک)|آرام\s*سے\s*(?:بہتر|ٹھیک)|آرام\s*کے\s*بعد\s*(?:بہتر|ٹھیک))\b",
]

_CHRONIC_PATTERNS = [
    r"\b(?:for\s+years|for\s+months|for\s+a\s+long\s+time|for\s+many\s+years|chronic(?:ally)?|since\s+\d+\s+years?|neuropathy)\b",
    r"\b(?:saalon\s+se|mahino\s+se|kafi\s+ars[ay]?\s+se|barson\s+se|purana|neuropathy)\b",
    r"\b(?:سالوں\s*سے|مہینوں\s*سے|کافی\s*عرصے\s*سے|برسوں\s*سے|پرانا)\b",
]

_EMOTIONAL_CUES = [
    r"\byaad\s+(?:aati|aye|ati|aata)\b",
    r"\byaad\b",
    r"\bro\s+raha\b",
    r"\budas\b",
    r"\bg[uh]am\b",
    r"\btoot\b",
    r"\bmiss(?:ing)?\b",
    r"\bsad\b",
    r"\bemotional\b",
    r"\bheartbroken\b",
    r"\bیاد\b",
    r"\bاداس\b",
    r"\bغم\b",
]


def _has_any(text: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _is_suppressed(norm: str) -> bool:
    """Returns True if the entire text should be suppressed due to past/exertion context."""
    # 1. Resolved / recovered expressions
    if _has_any(norm, _RESOLVED_PATTERNS):
        has_acute_current = _has_any(norm, [r"\blekin\s+abhi\b", r"\bbut\s+now\b", r"\babhi\s+dobara\b", r"\bلیکن\s*ابھی\b"])
        if not has_acute_current:
            return True

    # 2. Remote past without acute current marker
    has_past = _has_any(norm, _PAST_PATTERNS)
    has_current = _has_any(norm, _CURRENT_PATTERNS)
    if has_past and not has_current:
        return True

    # 3. Exertion with relief by rest
    has_exertion = _has_any(norm, _EXERTION_PATTERNS)
    has_rest = _has_any(norm, _REST_RELIEF_PATTERNS)
    if has_exertion and has_rest:
        return True

    return False


# =============================================================================
# Category 1: Chest Pain
# =============================================================================

_CHEST_BODY_TOKENS = {"chest", "seena", "chhati", "سینہ", "سینے", "چھاتی"}
_CHEST_SYMPTOM_TOKENS = {
    "pain", "pressure", "tightness", "heaviness", "crushing", "squeezing",
    "ache", "aching", "discomfort", "hurts", "heavy",
    "dard", "dabao", "bojh", "jakran", "bhaari", "bhari", "sakht", "shadeed", "tez", "khichao",
    "درد", "دباؤ", "بوجھ", "جکڑن", "بھاری", "کھچاؤ", "شدید", "سخت"
}

_CHEST_METAPHORS = [
    r"\belephant\s+(?:sitting\s+)?on\s+(?:my\s+)?chest\b",
    r"\b(?:tight\s+)?band\s+tightening\s+around\s+(?:my\s+)?chest\b",
    r"\bvise\s+around\s+(?:my\s+)?chest\b",
    r"\bcrushing\s+(?:weight|pressure)\s+on\s+(?:my\s+)?chest\b",
    r"\bcrushing\s+pressure\b",
    r"چھاتی\s*پر\s*ہاتھی\s*بیٹھا",
]

_PHYSICAL_CARDIAC_CUES = [
    r"\b(?:bayein|bayan|left)\s+(?:bazu|arm|shoulder|jabra|jaw)\b",
    r"\b(?:radiat(?:ing|es)|going\s+down)\s+to\s+(?:my\s+)?(?:left\s+arm|jaw)\b",
    r"\b(?:paseena|sweat|sweating|perspiration)\b",
    r"\b(?:seena|chest|chhati)\b",
    r"\b(?:dabao|pressure|bojh|jakran|crushing|squeezing)\b",
    r"\b(?:jalan|burning)\b",
    r"\b(?:khichao)\b",
    r"(?:بائیں\s*بازو|بائیں\s*جبڑا|پسینہ|دباؤ|بوجھ|جکڑن|جلن|کھچاؤ)",
]


def _is_chest_symptom_negated(norm: str) -> bool:
    """Detects negated chest pain expressions."""
    if re.search(r"\b(?:no|not|without|denies|denied|free\s+of)\s+(?:\w+\s+){0,3}(?:chest\s+pain|pain|pressure|tightness|heaviness|discomfort|hurts|ache)\b", norm):
        return True
    if re.search(r"\b(?:dard|dabao|bojh|takleef)\s+(?:to\s+|bhi\s+|bilkul\s+|hai\s+)?nahi\b", norm):
        return True
    if re.search(r"\bkoi\s+(?:bhi\s+)?(?:dard|dabao|bojh|takleef)\s+(?:bhi\s+)?nahi\b", norm):
        return True
    if re.search(r"(?:درد|دباؤ|بوجھ|تکلیف)\s*(?:تو|بھی|بالکل|ہے)?\s*نہیں", norm):
        return True
    if re.search(r"کوئی\s*(?:بھی\s*)?(?:درد|دباؤ|بوجھ|تکلیف)\s*(?:بھی\s*)?نہیں", norm):
        return True
    return False


def is_symptom_negated(norm: str) -> bool:
    """
    Public negation check function (architectural invariant verified by mutation M-RF-2).
    Returns True if an acute symptom is explicitly negated.
    """
    return _is_chest_symptom_negated(norm)


def _match_chest_pain(norm: str) -> bool:
    # 1. Metaphors
    if _has_any(norm, _CHEST_METAPHORS):
        return True

    # If symptom is explicitly negated, reject
    if is_symptom_negated(norm):
        return False

    # Chronic qualifiers (old injury, years)
    if _has_any(norm, _CHRONIC_PATTERNS):
        return False

    # Palpation tenderness / bruise (non-cardiac chest wall)
    if re.search(r"\b(?:when\s+i\s+press|press\s+on|touching|bruise|chot)\b", norm):
        return False

    words = norm.split()
    n = len(words)

    # Check for body + symptom within MAX_WINDOW_WORDS
    for i in range(n):
        w = words[i]
        if w in _CHEST_BODY_TOKENS:
            start = max(0, i - MAX_WINDOW_WORDS)
            end = min(n, i + MAX_WINDOW_WORDS + 1)
            for j in range(start, end):
                if i == j:
                    continue
                sj = words[j]
                if sj in _CHEST_SYMPTOM_TOKENS:
                    return True

    # 2. Cardiac radiation (left arm / left jaw pain)
    if re.search(r"(?:left\s+arm|bayein\s+bazu|bayan\s+bazu|بائیں\s*بازو)", norm):
        if re.search(r"(?:pain|dard|numb|sunn|kamzor|heaviness|bojh|khichao|درد|سن|کھچاؤ)", norm):
            return True

    if re.search(r"(?:left\s+jaw|bayein\s+jabra|bayan\s+jabra|بائیں\s*جبڑا)", norm):
        if re.search(r"(?:pain|dard|pressure|dabao|khichao|درد|دباؤ|کھچاؤ)", norm):
            return True

    # 3. "dil" (heart) only with physical cue and no emotional cue
    if re.search(r"(?:dil|دل)", norm):
        has_emotional = _has_any(norm, _EMOTIONAL_CUES)
        if not has_emotional:
            has_physical = _has_any(norm, _PHYSICAL_CARDIAC_CUES)
            has_symptom = bool(re.search(r"(?:dard|pain|heaviness|bojh|dabao|pressure|jalan|burning|khichao|درد|جلن|کھچاؤ)", norm))
            if has_physical and has_symptom:
                return True

    return False


# =============================================================================
# Category 2: Breathing
# =============================================================================

_BREATHING_METAPHORS = [
    r"\bdrowning\s+in\s+air\b",
    r"\bgasping\s+for\s+every\s+breath\b",
]

_BREATHING_INABILITY_PATTERNS = [
    r"\b(?:cant|cannot|unable\s+to)\s+breathe\b",
    r"\b(?:cant|cannot|unable\s+to)\s+catch\s+(?:my\s+)?breath\b",
    r"\bhard\s+to\s+breathe\b",
    r"\bdifficult\s+to\s+breathe\b",
    r"\bdifficulty\s+breathing\b",
    r"\btrouble\s+breathing\b",
    r"\bstruggling\s+(?:to\s+breathe|for\s+air|for\s+every\s+breath)\b",
    r"\bgasping(?:\s+for\s+air)?\b",
    r"\bsuffocating\b",
    r"\bchoking\b",
    r"\bsevere\s+(?:breathlessness|shortness\s+of\s+breath)\b",
    # Roman Urdu inability (tolerant of inserted tokens like bilkul, bhi, etc.)
    r"\bsans\s+(?:\w+\s+){0,3}nahi\s+aa\s+rah[iyea]\b",
    r"\bsans\s+nahi\s+aa\s+rah[iyea]\b",
    r"\b(?:dam|dum)\s+ghut\s+raha\b",
    r"\bsans\s+(?:\w+\s+){0,2}ruk\s+rah[iyea]\b",
    r"\bsans\s+ukhad\s+rah[iyea]\b",
    r"\bsans\s+lena\s+(?:\w+\s+){0,3}(?:mushkil|dushwar|muhaal)\b",
    r"\bsans\s+lene\s+me\s+(?:\w+\s+){0,3}(?:dushwari|mushkil)\b",
    # Urdu script inability
    r"سانس\s*(?:\S+\s*){0,3}نہیں\s*آ\s*رہی",
    r"دم\s*گھٹ\s*رہا",
    r"سانس\s*(?:\S+\s*){0,2}رک\s*رہی",
    r"سانس\s*(?:لینا)?\s*(?:\S+\s*){0,4}(?:مشکل|دشوار|محال)",
    r"سانس\s*لینا\s*(?:ممکن\s*نہیں|محال)",
    r"سانس\s*اکھڑ\s*(?:رہی|چکی)",
    r"ہوا\s*نہیں\s*مل\s*رہی",
]

_BREATHING_NEGATIONS = [
    r"\b(?:no|without|never\s+had)\s+(?:shortness\s+of\s+breath|difficulty\s+breathing|trouble\s+breathing|breathlessness)\b",
    r"\bnever\s+(?:\w+\s+){0,3}(?:difficulty\s+breathing|trouble\s+breathing|shortness\s+of\s+breath)\b",
    r"\bnot\s+breathless\b",
    r"\bwithout\s+(?:shortness\s+of\s+breath|breathlessness)\b",
    r"\bsans\s+(?:\w+\s+){0,3}(?:bilkul\s+theek|theek)\b",
    r"\bkoi\s+(?:\w+\s+){0,3}(?:masla|takleef|dushwari|mushkil)\s+(?:\w+\s+){0,2}nahi\b",
    r"سانس\s*(?:\S+\s*){0,3}(?:بالکل\s*ٹھیک|ٹھیک)",
    r"کوئی\s*(?:\S+\s*){0,3}(?:مسئلہ|تکلیف|دشواری|مشکل)\s*(?:\S+\s*){0,2}نہیں",
]


def _match_breathing(norm: str) -> bool:
    if _has_any(norm, _BREATHING_METAPHORS):
        return True

    # Check negated breathing first
    if _has_any(norm, _BREATHING_NEGATIONS):
        return False

    # Chronic conditions (asthma for years)
    if _has_any(norm, _CHRONIC_PATTERNS) and not re.search(r"\b(?:cannot|cant|gasping|suffocating)\b", norm):
        return False

    if _has_any(norm, _BREATHING_INABILITY_PATTERNS):
        return True

    return False


# =============================================================================
# Category 3: Confusion and Stroke
# =============================================================================

_STROKE_FAST_PATTERNS = [
    # Slurred speech / speech inability
    r"\bslurred\s+speech\b",
    r"\bspeech\s+is\s+slurred\b",
    r"\bslurring\s+(?:my\s+)?words\b",
    r"\b(?:lost\s+speech|lost\s+my\s+speech|unable\s+to\s+speak|cannot\s+speak|cant\s+speak)\b",
    r"\bzaban\s+ladkhada\b",
    r"\bawaz\s+ladkhada\b",
    r"\bbol\s+nahi\s+pa\s+rah[iy]\b",
    r"\bbol\s+nahi\s+sak\s+rah[iy]\b",
    r"\bbolti\s+band\b",
    r"زبان\s*لڑکھڑا",
    r"آواز\s*لڑکھڑا",
    r"بول\s*نہیں\s*پا\s*رہ[یا]",
    r"بولنا\s*(?:ممکن\s*نہیں|بند)",

    # Facial droop / asymmetry
    r"\b(?:face|mouth|eye)\s+(?:is\s+)?drooping\b",
    r"\bdrooping\s+(?:face|mouth|eye)\b",
    r"\bchehra\s+(?:aik\s+taraf\s+)?(?:latak|tedha|terha)\b",
    r"\bmunh\s+(?:aik\s+taraf\s+)?(?:tedha|terha)\b",
    r"چہرہ\s*(?:ایک\s*طرف\s*(?:کو\s*)?)?لٹک",
    r"منہ\s*(?:ایک\s*طرف\s*(?:کو\s*)?)?ٹیڑھا",
    r"چہرہ\s*ٹیڑھا",

    # Unilateral weakness / numbness (acute)
    r"\bone\s+side(?:d)?\s+(?:of\s+(?:my\s+)?(?:body|face|arm)\s+)?(?:(?:went|became|feels?|got|is)\s+)?(?:weak|numb|paralyzed)\b",
    r"\b(?:got\s+)?paralyzed\b",
    r"\bsudden\s+(?:weakness|numbness)\b",
    r"\bsuddenly\s+(?:feel\s+)?(?:weak|numb)\b",
    r"\b(?:arm|leg)\s+wont\s+move\b",
    r"\b(?:cant|cannot)\s+move\s+my\s+(?:left|right)?\s*(?:arm|leg)\b",
    r"\baik\s+taraf\s+ka\s+(?:\w+\s+){1,4}(?:sunn|kamzor|latak)\b",
    r"\badha\s+jism\s+(?:\w+\s+){0,3}(?:sunn|kamzor)\b",
    r"\b(?:face|arm|chehra|bazu)\s+(?:\w+\s+){0,3}(?:sunn|kamzor|numb|weak)\b",
    r"\bbazu\s+hil\s+nahi\s+raha\b",
    r"\bhath\s+hil\s+nahi\s+raha\b",
    r"ایک\s*طرف\s*کمزوری",
    r"ایک\s*طرف\s*کا\s*(?:\S+\s*){1,4}(?:سن|کمزور|لٹک)",
    r"(?:چہرہ|بازو)\s*(?:\S+\s*){0,3}(?:سن|کمزور)",
    r"آدھا\s*جسم\s*(?:سن|کمزور|بے\s*جان)",
    r"فالج\s*(?:کا\s*اثر|ہو\s*گیا)?",

    # Confusion / disorientation
    r"\bdisoriented\b",
    r"\bdont\s+know\s+where\s+i\s+am\b",
    r"\bdo\s+not\s+know\s+where\s+i\s+am\b",
    r"\bsevere\s+confusion\b",
    r"\bconfused\s+and\s+disoriented\b",
    r"\bkuch\s+samajh\s+nahi\s+aa\s+raha\s+kahan\b",
    r"کچھ\s*سمجھ\s*نہیں\s*آ\s*رہا\s*کہاں",
    r"شدید\s*الجھن",
]


def _is_stroke_negated(norm: str) -> bool:
    if re.search(r"\b(?:no|not|denies|denied|without)\s+(?:\w+\s+){0,3}(?:slurred|speech|droop|weakness|numbness)\b", norm):
        return True
    if re.search(r"\b(?:kamzori|sunn|ladkhada)\s+(?:\w+\s+){0,2}nahi\b", norm):
        return True
    if re.search(r"(?:کمزوری|سن|لڑکھڑا)\s*(?:\S+\s*){0,2}نہیں", norm):
        return True
    return False


def _match_confusion_and_stroke(norm: str) -> bool:
    # Chronic qualifier suppresses neuropathy / bilateral numbness
    if _has_any(norm, _CHRONIC_PATTERNS):
        return False

    if _is_stroke_negated(norm):
        return False

    # Suppress non-stroke bilateral feet/legs unless acute FAST unilateral
    if "feet numb" in norm or "both feet" in norm or "pair sunn" in norm:
        if not re.search(r"\b(?:face|chehra|speech|zaban|bol|one\s+side|aik\s+taraf)\b", norm):
            return False

    return _has_any(norm, _STROKE_FAST_PATTERNS)


# =============================================================================
# Category 4: Loss of Consciousness & Unresponsiveness
# =============================================================================

# Active unresponsiveness cues indicating current acute failure to wake / recover (Red)
_UNRESPONSIVE_PATTERNS = [
    r"\b(?:not|wont|unable\s+to|cant|cannot)\s+wake\b",
    r"\bnot\s+waking\s+up\b",
    r"\bstill\s+unconscious\b",
    r"\bremains\s+unconscious\b",
    r"\bcompletely\s+unresponsive\b",
    r"\bunresponsive\b",
    r"\bno\s+recovery\b",
    r"\bhosh\s+me(?:in)?\s+nahi\s+aa\s+rah",
    r"\bhosh\s+nahi\s+aa\s+rah",
    r"\bjawab\s+nahi\s+de\s+rah",
    r"\buth\s+nahi\s+rah",
    r"\bpa[rd][ai]\s+hai\s+aur\s+uth\s+nahi\b",
    r"ہوش\s*میں\s*نہیں\s*آ\s*رہ",
    r"ہوش\s*نہیں\s*آ\s*رہ",
    r"جواب\s*نہیں\s*دے\s*رہ",
    r"بے\s*ہوش\s*پڑا\s*ہے",
    r"اٹھ\s*نہیں\s*رہ",
]

_SYNCOPE_RECOVERY_PATTERNS = [
    r"\b(?:theek|thik)\s+(?:ho\s+gaya|hai|hoon|hun)\b",
    r"\b(?:fine|better|okay|ok)\s+now\b",
    r"\bab\s+(?:theek|behtar)\b",
    r"\bhosh\s+aa\s+gaya\b",
    r"\bwoke\s+up\b",
    r"\bnow\s+awake\b",
    r"\brecovered\b",
    r"اب\s*ٹھیک",
    r"ٹھیک\s*ہو\s*گیا",
    r"ہوش\s*آ\s*گیا",
]

_SYNCOPE_KEYWORDS = [
    r"\bpassed\s+out\b",
    r"\bblacked\s+out\b",
    r"\bfainted\b",
    r"\bcollapsed\b",
    r"\bunconscious\b",
    r"\blost\s+consciousness\b",
    r"\bhosh\s+kho\b",
    r"\bbe\s*hosh\b",
    r"\bghashi\s+(?:par\s+gayi|tari)\b",
    r"بے\s*ہوش",
    r"بے\s*ہوشی",
    r"غشی",
    r"غش\s*کھا",
]


def _is_syncope_negated(norm: str) -> bool:
    if re.search(r"\b(?:did\s+not|didn\s*t|not|never|no|denies)\s+(?:\w+\s+){0,3}(?:faint|pass\s+out|black\s+out|collapse|collapsed|unconscious)\b", norm):
        return True
    if re.search(r"\b(?:be\s*hosh|ghashi|chakkar)\s+(?:\w+\s+){0,2}nahi\b", norm):
        return True
    if re.search(r"\bnahi\s+(?:\w+\s+){0,2}(?:be\s*hosh|chakkar)\b", norm):
        return True
    if re.search(r"(?:بے\s*ہوش|غشی|چکر)\s*(?:\S+\s*){0,2}نہیں", norm):
        return True
    if re.search(r"نہیں\s*(?:\S+\s*){0,2}(?:بے\s*ہوش|غشی|چکر)", norm):
        return True
    return False


def is_fainting_recovered_or_benign(raw_text: str) -> bool:
    """
    Implements the clinical rule:
    Fainting that recovered ('gir gaya phir theek ho gaya', 'fainted but I'm fine now')
    or transient fainting episodes without persistent unresponsiveness (e.g.
    'chakkar kha kar gir gaya aur behosh ho gaya') stay on the danger wordgroup /
    review path.
    Only fainting with active unresponsiveness or no recovery ('not waking',
    'cannot wake', 'hosh mein nahi aa rahe', 'unresponsive', 'still unconscious')
    is an immediate Red emergency.
    """
    if not raw_text or not isinstance(raw_text, str):
        return False
    norm = normalize_text(raw_text)

    # Check if text contains syncope/fainting concepts
    has_syncope = _has_any(norm, [
        r"\bfaint", r"\bpass(?:ed)?\s+out\b", r"\bblack(?:ed)?\s+out\b",
        r"\bcollapse", r"\bchakkar\b", r"\bgir\s+(?:gaya|gayi|para|pari|pae)\b",
        r"\bbe\s*hosh\b", r"\bghashi\b", r"بے\s*ہوش", r"غشی", r"چکر", r"گر\s*پڑ"
    ])
    if not has_syncope:
        return False

    # If active unresponsiveness / no recovery cues are present, it is NOT recovered (it is Red!)
    has_unresponsive = _has_any(norm, _UNRESPONSIVE_PATTERNS)
    if has_unresponsive:
        return False

    # Explicit recovery cues
    has_recovery = _has_any(norm, _SYNCOPE_RECOVERY_PATTERNS)
    if has_recovery:
        return True

    # Check for transient fainting (like test_c3's chakkar kha kar gir gaya aur behosh ho gaya)
    if _has_any(norm, [r"\bchakkar\s+kha\s+kar\s+gir\b", r"\bchakkar\s+(?:\w+\s+){0,3}gir\b", r"چکر\s*(?:\S+\s*){0,3}گر"]):
        return True

    return False


def _match_loss_of_consciousness(norm: str) -> bool:
    if _is_syncope_negated(norm):
        return False

    # Active unresponsiveness / inability to wake is always emergency
    if _has_any(norm, _UNRESPONSIVE_PATTERNS):
        return True

    # If recovered or transient syncopal episode, suppress from emergency (stays on review path)
    if is_fainting_recovered_or_benign(norm):
        return False

    # Loss of consciousness / syncope keywords
    if _has_any(norm, _SYNCOPE_KEYWORDS):
        return True

    return False


# =============================================================================
# Category 5: DKA / Fluids / Persistent Vomiting
# =============================================================================

_FLUIDS_DKA_PATTERNS = [
    # Fluid inability
    r"\b(?:cant|cannot|unable\s+to)\s+keep\s+(?:\w+\s+){1,4}down\b",
    r"\beven\s+(?:\w+\s+){0,3}water\s+comes?\s+(?:back\s+)?up\b",
    r"\bwater\s+comes\s+(?:right\s+)?back\s+up\b",
    r"\bthrowing\s+up\s+everything\b",
    r"\bkeep\s+nothing\s+down\b",
    r"\bvomiting\s+(?:non-?stop|continuously|all\s+day)\b",
    r"\bvomiting\s+with\s+(?:very\s+)?high\s+(?:sugar|glucose)\b",
    r"\bliquids\s+down\s+with\s+(?:very\s+)?high\s+(?:sugar|glucose)\b",
    # Roman Urdu
    r"\bpani\s+(?:bhi\s+)?nahi\s+ruk\s+raha\b",
    r"\bpani\s+bhi\s+rukta\s+nahi\b",
    r"\bpani\s+(?:\w+\s+){0,3}wapis\b",
    r"\b(?:kuch\s+)?(?:bhi\s+)?hazam\s+nahi\s+ho\s+raha\b",
    r"\bhar\s+cheez\s+ulti\b",
    r"\bulti\s+ruk\s+nahi\s+rahi\b",
    r"\bmusalsal\s+ultiyan\b",
    r"\bkuch\s+bhi\s+pet\s+me\s+nahi\s+ruk\s+raha\b",
    # Urdu script
    r"الٹی\s*رک\s*نہیں\s*رہی",
    r"الٹیاں\s*بند\s*نہیں\s*ہو\s*رہ",
    r"پانی\s*بھی\s*واپس",
    r"پانی\s*بھی\s*نہیں\s*رک\s*رہا",
    r"پانی\s*بھی\s*نہیں\s*رکتا",
    r"مسلسل\s*الٹیاں",
    r"کچھ\s*بھی\s*ہضم\s*نہیں\s*ہو\s*رہا",
    r"ہر\s*چیز\s*الٹی",
    r"شوگر\s*(?:\S+\s*){0,3}الٹیاں",
]


def _match_dka_vomiting_fluids(norm: str) -> bool:
    return _has_any(norm, _FLUIDS_DKA_PATTERNS)


# =============================================================================
# Primary Public API
# =============================================================================

def match(raw_text: str) -> Tuple[bool, Optional[str]]:
    """
    Screens an utterance against Stage-1 clinical red flag patterns.

    Returns:
        (hit: bool, category: Optional[str])
        where category is strictly one of:
            "chest_pain", "breathing", "confusion_and_stroke",
            "loss_of_consciousness", "dka_vomiting_high_glucose"
        or (False, None) if no acute emergency is detected or if suppressed.

    No-throw guarantee: Wraps all processing in try/except and returns (False, None)
    on any internal exception.
    """
    try:
        if not raw_text or not isinstance(raw_text, str):
            return False, None

        norm = normalize_text(raw_text)
        if not norm:
            return False, None

        # Check global suppressions (remote past without current acute, exertion with rest relief, resolved)
        if _is_suppressed(norm):
            return False, None

        # 1. Chest pain (including metaphors & radiating pain)
        if _match_chest_pain(norm):
            return True, "chest_pain"

        # 2. Breathing inability & severe distress
        if _match_breathing(norm):
            return True, "breathing"

        # 3. FAST stroke / confusion / neurological deficit
        if _match_confusion_and_stroke(norm):
            return True, "confusion_and_stroke"

        # 4. Syncope / Loss of consciousness & unresponsiveness
        if _match_loss_of_consciousness(norm):
            return True, "loss_of_consciousness"

        # 5. DKA / Fluid intolerance / Persistent vomiting
        if _match_dka_vomiting_fluids(norm):
            return True, "dka_vomiting_high_glucose"

        return False, None

    except Exception:
        # Failsafe: never crash the server
        return False, None
