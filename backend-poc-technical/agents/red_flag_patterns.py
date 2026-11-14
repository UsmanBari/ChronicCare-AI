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
  ("saans nahi aa rahi", "pani nahi ruk raha"). Negation attaches locally to the adjacent word/clause.
- Remote past suppression: "5 years ago", "bachpan mein" do not hit unless a
  current-tense marker ("now", "aaj", "abhi") is also present.
- Exertion / rest suppression: Exertion coupled with rest relief ("breathless when walking fast,
  better after resting") indicates chronic exertional symptoms, not an acute emergency.
- Chronic qualifier suppression: "for years", "saalon se" suppresses chronic neuropathy / ache hits.
- Emotional "dil": "dil mein dard" without physical cardiac cues (or with emotional words like "yaad")
  does not hit.
- Fainting rule: Fainting that recovered ("gir gaya phir theek ho gaya", "fainted but I'm fine now")
  stays on the wordgroup/review path. Only fainting with active unresponsiveness or failure to wake is Red.
  Crucially, recovery from fainting is strictly scoped to loss_of_consciousness and NEVER cancels
  unrelated emergency symptoms (e.g., chest pain, breathing difficulty, stroke, fluid intolerance).
- No-throw guarantee: All matching is wrapped in a safe handler returning (False, None) on any error.
"""

import re
import unicodedata
from typing import Optional, Tuple, List


# Module configuration for window tolerance (architectural invariant verified by mutation M-RF-1)
MAX_WINDOW_WORDS: int = 8


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
    (r"\bkaafi\b", "kafi"),
    (r"\bziada\b", "zyada"),
    (r"\bseene\b", "seena"),
    (r"\bseenay\b", "seena"),
    (r"\bsene\b", "seena"),
    (r"\bsenay\b", "seena"),
    (r"\bchhati\b", "chhati"),
    (r"\bchati\b", "chhati"),
    (r"\bchaati\b", "chhati"),
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
    (r"\bawaaz\b", "awaz"),
    (r"\btedha\b", "terha"),
    (r"\btedhi\b", "terha"),
    (r"\bterhi\b", "terha"),
    (r"\bchehray\b", "chehra"),
    (r"\bchehre\b", "chehra"),
    (r"\bpasina\b", "paseena"),
    (r"\bpaseene\b", "paseena"),
    (r"\bpaseeney\b", "paseena"),
    (r"\bghunt\b", "ghoont"),
    (r"\bwapis\b", "wapas"),
    (r"\bkaam\b", "kam"),
    (r"\bbe\s*sudh\b", "be sudh"),
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


def _has_proximity(words: List[str], set_a: set, set_b: set, window: int = MAX_WINDOW_WORDS) -> bool:
    """
    Returns True if any token from set_a and set_b appear within `window` words
    of each other in the given token sequence (concept-based proximity matching).
    """
    n = len(words)
    for i in range(n):
        if words[i] in set_a:
            start = max(0, i - window)
            end = min(n, i + window + 1)
            for j in range(start, end):
                if i != j and words[j] in set_b:
                    return True
    return False


# =============================================================================
# Context Suppressions: Past, Exertion+Rest, Chronic, Emotional
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
    r"\bپھر\s*سے\b",
]

_EXERTION_PATTERNS = [
    r"\b(?:walking\s+fast|running|jogging|exercise|exercising|climbing\s+stairs|walking\s+upstairs|walk\s+up\s+(?:the\s+)?stairs|walking\s+up\s+(?:the\s+)?stairs|on\s+exertion)\b",
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
    """Returns True if the entire text should be suppressed due to remote past or exertion context."""
    # 1. Remote past without acute current marker
    has_past = _has_any(norm, _PAST_PATTERNS)
    has_current = _has_any(norm, _CURRENT_PATTERNS)
    if has_past and not has_current:
        return True

    # 2. Exertion with relief by rest
    has_exertion = _has_any(norm, _EXERTION_PATTERNS)
    has_rest = _has_any(norm, _REST_RELIEF_PATTERNS)
    if has_exertion and has_rest:
        return True

    return False


# =============================================================================
# Category 1: Chest Pain
# =============================================================================

_CHEST_BODY_TOKENS = {
    "chest", "breastbone", "sternum",
    "seena", "seenay", "seene", "sene", "senay", "chhati", "chati", "chaati",
    "سینہ", "سینے", "چھاتی"
}
_CHEST_SYMPTOM_TOKENS = {
    "pain", "pains", "painful", "hurt", "hurts", "hurting", "ache", "aching", "aches", "discomfort",
    "pressure", "tight", "tightness", "heavy", "heaviness", "crushing", "squeezing", "squeezed", "crushed",
    "vice", "vise", "elephant",
    "dard", "dardi", "dukhta", "dukh", "dabao", "dbao", "dabaw", "bojh", "jakran", "bhari", "bhaari",
    "sakht", "shadeed", "tez", "khichao", "nichor", "masal", "bandhna", "phat",
    "درد", "دکھتا", "دباؤ", "بوجھ", "جکڑن", "بھاری", "سخت", "شدید", "تیز", "کھچاؤ", "نچوڑ", "پھٹ"
}

_CHEST_METAPHORS = [
    r"\belephant\s+(?:is\s+)?(?:sitting|standing)\s+on\s+(?:my\s+)?chest\b",
    r"\b(?:like\s+)?(?:an\s+elephant|something\s+heavy|a\s+heavy\s+(?:rock|stone|weight|brick))\s+(?:is\s+)?(?:sitting|placed)\s+on\s+(?:my\s+)?chest\b",
    r"\bfeels?\s+like\s+(?:an\s+elephant|something\s+heavy|a\s+heavy\s+weight)\s+on\s+(?:my\s+)?chest\b",
    r"\b(?:heavy\s+weight|ton\s+of\s+bricks)\s+(?:(?:is\s+)?(?:sitting|lying|placed)\s+)?on\s+(?:my\s+)?chest\b",
    r"\b(?:someone|something)\s+is\s+(?:squeezing|crushing|pressing\s+down\s+on)\s+(?:my\s+)?chest\b",
    r"\b(?:tight\s+)?band\s+tightening\s+around\s+(?:my\s+)?chest\b",
    r"\b(?:vise|vice)\s+(?:around|gripping|crushing)\s+(?:my\s+)?chest\b",
    r"\bcrushing\s+(?:weight|pressure)\s+on\s+(?:my\s+)?chest\b",
    r"\bcrushing\s+pressure\b",
    r"\b(?:j[ae]ise|jese)\s+(?:koi\s+)?bhari\s+cheez\s+(?:rakh[iy]\s+ho|rakh\s+di\s+ho)\b",
    r"\b(?:j[ae]ise|jese)\s+(?:koi\s+)?(?:seena|chhati)?(?:\s+ko)?(?:\s+\w+){0,3}\s+daba\s+raha\s+(?:hai|ho)\b",
    r"\b(?:aisa\s+lagta\s+hai\s+|aisa\s+mehsoos\s+hota\s+hai\s+)?(?:j[ae]ise|jese)\s+(?:koi\s+)?(?:\w+\s+){0,4}daba\s+raha\s+(?:hai|ho)\b",
    r"\b(?:seena|chhati)\s+(?:\w+\s+){0,4}(?:daba|nichor|masal)\s+raha\s+(?:hai|ho)\b",
    r"\b(?:seena|chhati)\s+(?:par|pe)\s+(?:j[ae]ise|jese)\s+(?:koi\s+)?(?:bhari\s+cheez|wazan|bojh|hathi)\b",
    r"\b(?:seena|chhati)\s+(?:par|pe)\s+hathi\s+baitha\s+(?:hai|ho)\b",
    r"\b(?:aisa\s+lagta\s+hai\s+)?(?:koi\s+)?(?:seena|chhati)\s+(?:ko\s+)?(?:daba|nichor|masal)\s+raha\s+hai\b",
    r"چھاتی\s*پر\s*ہاتھی\s*بیٹھا",
    r"سینے\s*پر\s*ہاتھی\s*بیٹھا",
    r"جیسے\s*(?:کوئی\s*)?بھاری\s*چیز\s*(?:رکھی\s*ہو|رکھ\s*دی\s*ہو)",
    r"جیسے\s*(?:کوئی\s*)?(?:سینہ\s*)?دبا\s*رہا\s*ہو",
    r"سینے\s*پر\s*(?:جیسے\s*)?(?:کوئی\s*)?(?:بھاری\s*چیز|وزن|بوجھ|ہاتھی)",
    r"(?:چھاتی|سینے)\s*کو\s*کوئی\s*(?:نچوڑ|دبا)\s*رہا\s*ہو",
    # Someone standing / sitting on chest (any verb)
    r"\b(?:someone|somebody|anyone)\s+(?:is\s+)?(?:standing|sitting|stepped|pressing|crushing|lying)\s+on\s+(?:my\s+)?chest\b",
    r"\bfeels?\s+like\s+(?:someone|somebody)\s+(?:is\s+)?(?:standing|sitting|stepped|pressing|crushing|lying)\s+on\s+(?:my\s+)?chest\b",
    r"\b(?:seena|seenay|seene|chhati)\s+(?:par|pe)\s+(?:koi\s+)?(?:baitha|betha|khara|khada|sawar|dabaye)\b",
    r"(?:سینے|چھاتی)\s*پر\s*(?:کوئی\s*)?(?:بیٹھا|کھڑا|سوار|دبائے)",
    # Mid-chest pressure + nausea / vomit sensation (ACS presentation)
    r"\b(?:seena|seenay|seene|chhati)\s+(?:ke\s+)?(?:beech|darmiyan|me)\s+(?:\w+\s+){0,4}(?:dabao|dabav|dbao|bojh|pressure|tightness|heaviness)\b.*?\b(?:ulti\s+jaisa|matli|nausea|vomit\w*|sick)\b",
    r"\b(?:ulti\s+jaisa|matli|nausea|vomit\w*|sick)\b.*?\b(?:seena|seenay|seene|chhati)\s+(?:ke\s+)?(?:beech|darmiyan|me)\s+(?:\w+\s+){0,4}(?:dabao|dabav|dbao|bojh|pressure|tightness|heaviness)\b",
    r"(?:سینے\s*کے\s*(?:بیچ|درمیان)|چھاتی\s*میں)\s*(?:\S+\s*){0,4}(?:دباؤ|بوجھ).*?(?:الٹی\s*جیسا|متلی|قے)",
    r"(?:الٹی\s*جیسا|متلی|قے).*?(?:سینے\s*کے\s*(?:بیچ|درمیان)|چھاتی\s*میں)\s*(?:\S+\s*){0,4}(?:دباؤ|بوجھ)",
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

_CHEST_SPAN_PATTERNS = [
    r"\b(?:seena|seenay|seene|chhati|chati|chaati|chest)\b.{0,65}\b(?:dard|dabao|bojh|jakran|bhaari|bhari|sakht|shadeed|tez|pain|pressure|tightness|heaviness|crushing|squeezing)\b",
    r"\b(?:dard|dabao|bojh|jakran|bhaari|bhari|sakht|shadeed|tez|pain|pressure|tightness|heaviness|crushing|squeezing)\b.{0,65}\b(?:seena|seenay|seene|chhati|chati|chaati|chest)\b",
    r"(?:سینہ|سینے|چھاتی).{0,65}(?:درد|دباؤ|بوجھ|جکڑن|بھاری|شدید|سخت|تیز)",
    r"(?:درد|دباؤ|بوجھ|جکڑن|بھاری|شدید|سخت|تیز).{0,65}(?:سینہ|سینے|چھاتی)",
]

_SWEATING_CARDIAC_PATTERNS = [
    r"\b(?:paseena|sweat|sweating|perspiration)\b.*?\b(?:seena|seenay|seene|chhati|chest|dil|bazu|jabra)\b",
    r"\b(?:seena|seenay|seene|chhati|chest|dil|bazu|jabra)\b.*?\b(?:paseena|sweat|sweating|perspiration)\b",
    r"پسینہ.*?(?:سینہ|سینے|چھاتی|دل|بازو|جبڑا)",
    r"(?:سینہ|سینے|چھاتی|دل|بازو|جبڑا).*?پسینہ",
]


def _is_chest_symptom_negated(norm: str) -> bool:
    """
    Detects negated chest pain expressions.
    Negation attaches locally to the adjacent word/clause.
    If the patient affirms an acute chest symptom (e.g. 'jalan nahi, asal mein tez dard hai',
    'dard nahi dabao hai'), it is NOT negated.
    """
    # 1. Check if un-negated acute chest symptoms are explicitly present
    # e.g. "jalan nahi ... tez dard", "not heartburn ... crushing pain", "dard nahi ... dabao"
    has_contrastive_acute = bool(re.search(
        r"\b(?:jalan\s+nahi|not\s+(?:heartburn|acid(?:ity)?|gas|mild)|dard\s+nahi|no\s+pain)\b.*?\b(?:tez\s+dard|shadeed\s+dard|severe\s+pain|sharp\s+pain|crushing|dabao|bojh|jakran|pressure|tightness|heaviness)\b",
        norm
    ) or re.search(
        r"(?:جلن\s*نہیں|گیس\s*نہیں|درد\s*نہیں).*?(?:تیز\s*درد|شدید\s*درد|دباؤ|بوجھ|جکڑن|کھچاؤ)",
        norm
    ))
    if has_contrastive_acute:
        return False

    # 2. General negation patterns
    if re.search(
        r"\b(?:no|not|without|denies|denied|never|free\s+of|zero|"
        r"i\s+do\s*n\s*['’]?\s*t\s+have|i\s+did\s*n\s*['’]?\s*t\s+have|"
        r"i\s+have\s+no|there\s+is\s+no|not\s+feeling\s+any|no\s+sign\s+of|"
        r"i\s*['’]?\s*m\s+not\s+having)\s+(?:\w+\s+){0,3}"
        r"(?:chest\s+pain|chest\s+trouble|chest\s+problem|chest\s+issue|chest\s+discomfort|pain|pressure|tightness|heaviness|discomfort|hurts|ache|trouble|problem|masla|takleef)\b",
        norm
    ):
        return True
    if re.search(r"\b(?:chest|seena|seenay|seene|chhati)\s+(?:is\s+)?(?:completely\s+)?(?:fine|normal|ok|okay|good|unremarkable|theek|sahi)\b", norm):
        return True
    if re.search(r"\b(?:seena|seenay|seene|chhati)\s+(?:me\s+)?(?:koi\s+)?(?:dard|dabao|bojh|takleef|masla)\s+(?:bhi\s+)?nahi\b", norm):
        return True
    if re.search(r"\b(?:dard|dabao|bojh|takleef|masla)\s+(?:to\s+|bhi\s+|bilkul\s+|hai\s+|ho\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\b(?:mujhe\s+koi|koi\s+bhi)\s+(?:\w+\s+){0,3}(?:dard|dabao|bojh|takleef|masla|seene\s+me\s+dard)\s+(?:bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\bkoi\s+(?:bhi\s+)?(?:\w+\s+){0,2}(?:dard|dabao|bojh|takleef|masla)\s+(?:bhi\s+)?nahi\b", norm):
        return True
    if re.search(r"(?:مجھے\s+کوئی|کوئی\s+بھی)\s*(?:\S+\s*){0,3}(?:درد|دباؤ|بوجھ|تکلیف|مسئلہ)\s*(?:بھی\s*)?(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"(?:سینہ|سینے|چھاتی)\s*(?:میں\s*)?(?:کوئی\s*)?(?:درد|دباؤ|بوجھ|تکلیف|مسئلہ)\s*(?:بھی\s*)?نہیں", norm):
        return True
    if re.search(r"(?:درد|دباؤ|بوجھ|تکلیف|مسئلہ)\s*(?:تو|بھی|بالکل|ہے)?\s*نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"کوئی\s*(?:بھی\s*)?(?:درد|دباؤ|بوجھ|تکلیف|مسئلہ)\s*(?:بھی\s*)?نہیں", norm):
        return True
    if re.search(r"بغیر\s*(?:کسی\s*)?(?:درد|تکلیف|مسئلے)", norm):
        return True
    return False


def _is_benign_food_jalan(norm: str) -> bool:
    """
    Detects benign gastrointestinal heartburn / jalan triggered by spicy food/meals
    without acute cardiac red flags (pressure, radiation, sweating, breathlessness, severe pain).
    """
    has_jalan = bool(re.search(r"\b(?:jalan|burning|heartburn|acid(?:ity)?|tezabiyat)\b|جلن|تیزابیت", norm))
    if not has_jalan:
        return False

    # Check for food / meal / spicy trigger
    has_food_trigger = bool(re.search(
        r"\b(?:khana|khanay|khana\s+kha\s+kar|khane\s+ke\s+baad|khane\s+par|tez\s+mirch|mirch\w*|masalay?|spicy|food|meal|after\s+eating|eating|fried|chilli)\b|"
        r"کھانا|کھانے|مرچ|تیز\s*مرچ|کھانے\s*کے\s*بعد|کھا\s*کر",
        norm
    ))
    if not has_food_trigger:
        return False

    # Cardiac red flags that override benign food trigger
    has_pressure = bool(re.search(
        r"\b(?:dabao|dbao|dabaw|pressure|bojh|jakran|crushing|squeezing|vice|elephant|bhaari|bhari)\b|دباؤ|بوجھ|جکڑن",
        norm
    ))
    has_radiation = bool(re.search(
        r"\b(?:left\s+arm|bayein\s+bazu|bayan\s+bazu|left\s+jaw|bayein\s+jabra|bayan\s+jabra|radiat)\b|بائیں\s*بازو|بائیں\s*جبڑا",
        norm
    ))
    has_sweating = bool(re.search(
        r"\b(?:paseena|sweat|sweating|perspiration)\b|پسینہ",
        norm
    ))
    has_breathless = bool(re.search(
        r"\b(?:breathless|shortness\s+of\s+breath|cant\s+breathe|sans\s+phool|sans\s+nahi|dam\s+ghut)\b|سانس|دم\s*گھٹ",
        norm
    ))
    has_explicit_pain = bool(re.search(
        r"\b(?:tez\s+dard|shadeed\s+dard|severe\s+pain|sharp\s+pain|crushing\s+pain)\b|تیز\s*درد|شدید\s*درد",
        norm
    ))

    # If NO acute cardiac features, it is benign gastrointestinal heartburn
    if not (has_pressure or has_radiation or has_sweating or has_breathless or has_explicit_pain):
        return True
    return False


def is_symptom_negated(norm: str) -> bool:
    """
    Public negation check function (architectural invariant verified by mutation M-RF-2).
    Returns True if an acute symptom is explicitly negated.
    """
    return _is_chest_symptom_negated(norm)


def _match_chest_pain(norm: str) -> bool:
    # 1. Contrastive un-negated pain presentation ("jalan nahi, asal mein tez dard hai")
    if re.search(r"\b(?:jalan\s+nahi|not\s+(?:heartburn|acid(?:ity)?|gas))\b.*?\b(?:tez\s+dard|shadeed\s+dard|severe\s+pain|sharp\s+pain|crushing|dabao|bojh)\b", norm) or \
       re.search(r"(?:جلن\s*نہیں|گیس\s*نہیں).*?(?:تیز\s*درد|شدید\s*درد|دباؤ|بوجھ)", norm):
        return True

    # If symptom is explicitly negated, reject (architectural invariant for M-RF-2)
    if is_symptom_negated(norm):
        return False

    # Benign food-triggered heartburn / jalan without cardiac red flags
    if _is_benign_food_jalan(norm):
        return False

    # 2. Metaphors & heaviness comparisons
    if _has_any(norm, _CHEST_METAPHORS):
        return True

    # Chronic qualifiers (old injury, years)
    if _has_any(norm, _CHRONIC_PATTERNS):
        return False

    # Palpation tenderness / bruise (non-cardiac chest wall)
    if re.search(r"\b(?:when\s+i\s+press|press\s+on|touching|bruise|chot)\b", norm):
        return False

    # 3. Sweating (paseena) with cardiac / chest involvement
    if _has_any(norm, _SWEATING_CARDIAC_PATTERNS):
        if re.search(r"\b(?:dard|dabao|bojh|jakran|khichao|pain|pressure|tightness|heaviness|درد|دباؤ|بوجھ|جکڑن)\b", norm):
            return True

    # 4. Regex span patterns for body + intermediate words + symptom (G1 coverage)
    if _has_any(norm, _CHEST_SPAN_PATTERNS):
        return True

    # 5. Token distance window (MAX_WINDOW_WORDS)
    words = norm.split()
    n = len(words)
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

    # 6. Cardiac radiation (left arm / left jaw pain)
    if re.search(r"(?:left\s+arm|bayein\s+bazu|bayan\s+bazu|بائیں\s*بازو)", norm):
        if re.search(r"(?:pain|dard|numb|sunn|kamzor|heaviness|bojh|khichao|درد|سن|کھچاؤ)", norm):
            return True

    if re.search(r"(?:left\s+jaw|bayein\s+jabra|bayan\s+jabra|بائیں\s*جبڑا)", norm):
        if re.search(r"(?:pain|dard|pressure|dabao|khichao|درد|دباؤ|کھچاؤ)", norm):
            return True

    # 7. "dil" (heart) only with physical cue and no emotional cue
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
    # Inability & gasping (English)
    r"\b(?:cant|cannot|unable\s+to)\s+breathe\b",
    r"\b(?:cant|cannot|unable\s+to)\s+catch\s+(?:my\s+)?breath\b",
    r"\b(?:cant|cannot|unable\s+to)\s+get\s+(?:any\s+)?air\b",
    r"\b(?:can\s+)?barely\s+(?:able\s+to\s+)?breathe\b",
    r"\bhardly\s+(?:able\s+to\s+)?breathe\b",
    r"\bcan\s+hardly\s+(?:catch\s+(?:my\s+)?breath|breathe|get\s+(?:any\s+)?air)\b",
    r"\bhardly\s+(?:any\s+air|getting\s+air)\b",
    r"\bhard\s+to\s+breathe\b",
    r"\bdifficult\s+to\s+breathe\b",
    r"\bdifficulty\s+breathing\b",
    r"\btrouble\s+breathing\b",
    r"\bstruggling\s+(?:to\s+breathe|for\s+air|for\s+every\s+breath)\b",
    r"\bgasping(?:\s+for\s+air)?\b",
    r"\bsuffocating\b",
    r"\bchoking\b",
    r"\bsevere\s+(?:breathlessness|shortness\s+of\s+breath)\b",
    # Rest dyspnea (English)
    r"\b(?:short(?:ness)?\s+of\s+breath|breathless(?:ness)?|difficult(?:y)?\s+breathing|cant\s+breathe|hard\s+to\s+breathe)\s+(?:even\s+)?(?:at\s+rest|while\s+sitting(?:\s+still)?|while\s+lying(?:\s+down|\s+flat)?|when\s+lying|when\s+sitting)\b",
    r"\b(?:even\s+)?(?:at\s+rest|while\s+sitting(?:\s+still)?|while\s+lying(?:\s+down|\s+flat)?|when\s+lying|when\s+sitting)\b.*?\b(?:cant\s+breathe|short(?:ness)?\s+of\s+breath|breathless|struggling\s+for\s+air)\b",
    # Roman Urdu inability & rest dyspnea
    r"\bsans\s+(?:\w+\s+){0,3}nahi\s+aa\s+rah[iyea]\b",
    r"\bsans\s+nahi\s+aa\s+rah[iyea]\b",
    r"\b(?:dam|dum)\s+ghut\s+raha\b",
    r"\bsans\s+(?:\w+\s+){0,2}ruk\s+rah[iyea]\b",
    r"\bsans\s+ukhad\s+rah[iyea]\b",
    r"\bsans\s+lena\s+(?:\w+\s+){0,3}(?:mushkil|dushwar|muhaal)\b",
    r"\bsans\s+lene\s+me\s+(?:\w+\s+){0,3}(?:dushwari|mushkil)\b",
    r"\b(?:baithe|bethay|bethi|lete|letay)\s+(?:hue\s+)?(?:bhi\s+)?(?:sans\s+phool|sans\s+ruk|sans\s+nahi|dam\s+ghut)\b",
    r"\bbina\s+(?:chale|hille|harakat)\s+(?:bhi\s+)?(?:sans\s+nahi|sans\s+phool|dam\s+ghut)\b",
    r"\baaram\s+(?:se\s+baithe|karte)\s+(?:hue\s+)?(?:bhi\s+)?(?:sans\s+nahi|sans\s+lena\s+mushkil)\b",
    r"\bsans\s+lena\s+(?:bohot\s+|shadeed\s+|sakht\s+)?mushkil\s+ho\s+gaya\s+hai\b",
    # Urdu script inability & rest dyspnea
    r"سانس\s*(?:\S+\s*){0,3}نہیں\s*آ\s*رہی",
    r"دم\s*گھٹ\s*رہا",
    r"سانس\s*(?:\S+\s*){0,2}رک\s*رہی",
    r"سانس\s*(?:لینا)?\s*(?:\S+\s*){0,4}(?:مشکل|دشوار|محال)",
    r"سانس\s*لینا\s*(?:ممکن\s*نہیں|محال)",
    r"سانس\s*اکھڑ\s*(?:رہی|چکی)",
    r"ہوا\s*نہیں\s*مل\s*رہی",
    r"(?:بیٹھے|لیٹے)\s*(?:ہوئے\s*)?(?:بھی\s*)?(?:سانس\s*پھول|سانس\s*رک|سانس\s*نہیں|دم\s*گھٹ)",
    r"بغیر\s*چلے\s*(?:بھی\s*)?سانس\s*(?:نہیں\s*آ\s*رہی|پھول)",
    r"آرام\s*کی\s*حالت\s*میں\s*(?:بھی\s*)?سانس\s*(?:لینا\s*محال|نہیں\s*آ\s*رہی)",
    r"سانس\s*لینا\s*بہت\s*مشکل\s*ہو\s*گیا\s*ہے",
    # Air not going in (Roman Urdu, Urdu script, English)
    r"\bhawa\s+(?:\w+\s+){0,2}(?:andar\s+)?nahi\s+(?:jaa?ti|jaa?te|jaa?ta|jaa?\s*rahi|jaa?\s*raha|aati|aata|mil\s*rahi|mil\s*raha)\b",
    r"\b(?:air\s+(?:is\s+)?(?:not\s+going\s+in|wont\s+go\s+in|not\s+getting\s+in|cant\s+get\s+in)|no\s+air\s+(?:is\s+)?(?:going\s+in|getting\s+in))\b",
    r"ہوا\s*(?:\S+\s*){0,2}(?:اندر\s*)?نہیں\s*(?:جاتی|جا\s*رہی|آتی|مل\s*رہی)",
    # Bilkul ukhri hui
    r"\b(?:sans|saans|dam)\s+(?:\w+\s+){0,3}(?:bilkul\s+)?(?:ukhad|ukhri)\s+(?:gayi|gaya|rahi|raha|hui)\b",
    r"\b(?:bilkul\s+)?ukhri\s+hui\s+(?:sans|saans)\b",
    r"\b(?:sans|saans)\s+(?:bilkul\s+)?ukhri\s+hui\b",
    r"سانس\s*(?:\S+\s*){0,3}(?:بالکل\s*)?اکھڑ\s*(?:گئی|گیا|رہی)",
    r"(?:بالکل\s*)?اکھڑی\s*ہوئی\s*سانس",
    r"سانس\s*(?:بالکل\s*)?اکھڑی\s*ہوئی",
    # Wheezing + Blue lips
    r"\b(?:wheez\w*|seeti\s+(?:jaisi|ki\s+awaz))\b.*?\b(?:(?:blue|bluish|neela?y?)\s+(?:lips?|hon?th?)|(?:lips?|hon?th?)\s+(?:\w+\s+){0,2}(?:blue|bluish|neela?y?))\b",
    r"\b(?:(?:blue|bluish|neela?y?)\s+(?:lips?|hon?th?)|(?:lips?|hon?th?)\s+(?:\w+\s+){0,2}(?:blue|bluish|neela?y?))\b.*?\b(?:wheez\w*|seeti\s+(?:jaisi|ki\s+awaz))\b",
    r"(?:سیٹی|wheez).*?(?:نیلے\s*ہونٹ|blue\s*lips?)",
    r"(?:نیلے\s*ہونٹ|blue\s*lips?).*?(?:سیٹی|wheez)",
    # Orthopnea / Inability to lie down
    r"\b(?:lai?t|let)\s+(?:bhi\s+)?nahi\s+(?:sakta|sakti|saktay|sakte|pa\s+raha|pa\s+rahi|pa\s+rahe)\b",
    r"\bcant\s+(?:even\s+)?lie\s+(?:down|flat)\b",
    r"\bcannot\s+(?:even\s+)?lie\s+(?:down|flat)\b",
    r"\bunable\s+to\s+lie\s+(?:down|flat)\b",
    r"\bwont\s+lie\s+(?:down|flat)\b",
    r"لیٹ\s*(?:بھی\s*)?نہیں\s*(?:سکتا|سکتی|سکتے|پا\s*رہ)",
    r"سیدھا\s*لیٹنا\s*(?:ممکن\s*نہیں|محال)",
]

_BREATHING_NEGATIONS = [
    r"\b(?:no|not|without|never\s+had|never|denies|denied|zero)\s+(?:\w+\s+){0,3}(?:shortness\s+of\s+breath|difficulty\s+breathing|trouble\s+breathing|breathing\s+trouble|breathing\s+difficulty|breathing\s+problem|breathing\s+issue|breath\s+trouble|breath\s+problem|breath\s+difficulty|breath\s+issue|breathlessness|breath\s+shortness)\b",
    r"\b(?:i\s+do\s*n\s*['’]?\s*t\s+have|i\s+did\s*n\s*['’]?\s*t\s+have|i\s+have\s+no|there\s+is\s+no|not\s+feeling\s+any|no\s+sign\s+of|i\s*['’]?\s*m\s+not\s+having|free\s+of)\s+(?:\w+\s+){0,3}(?:shortness\s+of\s+breath|difficulty\s+breathing|trouble\s+breathing|breathing\s+trouble|breathing\s+difficulty|breathing\s+problem|breathing\s+issue|breath\s+trouble|breath\s+problem|breath\s+difficulty|breath\s+issue|breathlessness|breath\s+shortness|breathing|breath)\b",
    r"\b(?:no|not|without|never)\s+(?:trouble|difficulty|problem|issue)\s+(?:in\s+|with\s+)?(?:breathing|breath)\b",
    r"\b(?:no|not|without|never)\s+(?:breathing|breath)\s+(?:trouble|difficulty|problem|issue|complaint)\b",
    r"\bnever\s+(?:\w+\s+){0,3}(?:difficulty\s+breathing|trouble\s+breathing|breathing\s+trouble|shortness\s+of\s+breath)\b",
    r"\bnot\s+breathless\b",
    r"\bwithout\s+(?:shortness\s+of\s+breath|breathlessness)\b",
    r"\bbreathing\s+(?:is\s+)?(?:completely\s+)?(?:fine|normal|ok|okay|good|unremarkable)\b",
    r"\bwithout\s+(?:any\s+)?(?:trouble|difficulty|shortness|problem|breathlessness)\b",
    r"\bsans\s+(?:\w+\s+){0,3}(?:bilkul\s+theek|theek|sahi|behtar)\b",
    r"\b(?:mujhe\s+koi|koi\s+bhi)\s+(?:\w+\s+){0,3}(?:sans|saans|dam)\s+(?:\w+\s+){0,2}(?:masla|takleef|dushwari|mushkil|tangi|kharabi)\s+(?:bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b",
    r"\b(?:sans|saans|dam)\s+(?:ki\s+)?(?:takleef|masla|tangi|dushwari)\s+(?:to\s+|bhi\s+)?bilkul\s+nahi(?:\s+hai)?\b",
    r"\b(?:sans|saans|dam)\s+(?:ki\s+)?(?:takleef|masla|tangi|dushwari)\s+nahi\s+hai\b",
    r"\bkoi\s+(?:\w+\s+){0,3}(?:sans|saans)\s+(?:\w+\s+){0,2}(?:masla|takleef|dushwari|mushkil|tangi|kharabi)\s+(?:\w+\s+){0,2}nahi\b",
    r"\bkoi\s+(?:\w+\s+){0,3}(?:masla|takleef|dushwari|mushkil|tangi)\s+(?:\w+\s+){0,2}nahi\b",
    r"\bsans\s+(?:me\s+|lene\s+me\s+)?(?:koi\s+)?(?:masla|takleef|dushwari|mushkil|tangi)\s+nahi\b",
    r"(?:مجھے\s+کوئی|کوئی\s+بھی)\s*(?:\S+\s*){0,3}(?:سانس\s*)?(?:\S+\s*){0,2}(?:مسئلہ|تکلیف|دشواری|مشکل|تنگی)\s*(?:بھی\s*)?(?:بالکل\s*)?نہیں(?:\s*ہے)?",
    r"سانس\s*(?:کی\s*|میں\s*)?(?:تکلیف|تنگی|مسئلہ|دشواری)\s*(?:تو|بھی)?\s*بالکل\s*نہیں(?:\s*ہے)?",
    r"سانس\s*(?:کی\s*|میں\s*)?(?:تکلیف|تنگی|مسئلہ|دشواری)\s*نہیں\s*ہے",
    r"سانس\s*(?:\S+\s*){0,3}(?:بالکل\s*ٹھیک|ٹھیک|بہتر|صحیح)",
    r"کوئی\s*(?:\S+\s*){0,3}(?:سانس\s*)?(?:\S+\s*){0,2}(?:مسئلہ|تکلیف|دشواری|مشکل|تنگی)\s*(?:\S+\s*){0,2}نہیں",
    r"کوئی\s*(?:\S+\s*){0,3}(?:مسئلہ|تکلیف|دشواری|مشکل|تنگی)\s*(?:\S+\s*){0,2}نہیں",
    r"سانس\s*(?:کی\s*)?(?:تنگی|دشواری|مشکل)\s*(?:\S+\s*){0,2}نہیں",
    r"بغیر\s*(?:کسی\s*)?(?:سانس\s*)?(?:\S+\s*){0,2}(?:تکلیف|دشواری|تنگی|مسئلے)",
    r"بغیر\s*سانس\s*(?:کی\s*)?تکلیف",
]


_BREATH_ORGAN_TOKENS = {
    "breath", "breathe", "breathing", "breathless", "breathlessness", "air", "lungs", "lung",
    "choke", "choking", "choked", "suffocate", "suffocating", "suffocation", "gasp", "gasping",
    "drown", "drowning", "sans", "saans", "saas", "dam", "dum", "ghutan",
    "سانس", "دم", "گھٹن"
}

_BREATH_DISTRESS_TOKENS = {
    "cant", "cannot", "unable", "hard", "difficult", "difficulty", "trouble", "struggle", "struggling",
    "short", "shortness", "barely", "hardly", "fail", "failing", "stop", "stopped",
    "ruk", "ukhad", "ghut", "phool", "band", "dushwar", "dushwari", "mushkil", "muhaal", "tang", "kam",
    "رک", "اکھڑ", "گھٹ", "پھول", "بند", "دشوار", "دشواری", "مشکل", "محال", "تنگ", "کم"
}

_REST_POSITION_TOKENS = {
    "rest", "resting", "sitting", "lying", "flat", "bed",
    "baithe", "bethay", "bethi", "lete", "letay", "aaram",
    "بیٹھے", "لیٹے", "آرام"
}


def _has_cyanosis(norm: str) -> bool:
    """
    Detects acute central or peripheral cyanosis (blue lips / hont neelay)
    which represents severe respiratory distress / hypoxemia and triggers breathing-Red alone.
    """
    if re.search(r"\b(?:no|not|without|never|denies|denied)\s+(?:\w+\s+){0,2}(?:blue|bluish|neelay|neela|neeli)\b", norm):
        return False
    if re.search(r"\b(?:lips?\s+(?:are\s+)?(?:turning\s+|turned\s+)?(?:blue|bluish)|(?:blue|bluish)\s+lips?)\b", norm):
        return True
    if re.search(r"\b(?:hon?th?|hont)\s+(?:\w+\s+){0,2}(?:neelay|neela|neeli)\b|\b(?:neelay|neela|neeli)\s+(?:hon?th?|hont)\b", norm):
        return True
    if re.search(r"نیلے\s*ہونٹ|ہونٹ\s*(?:\S+\s*){0,2}نیلے", norm):
        return True
    return False


def _match_breathing(norm: str) -> bool:
    if re.search(r"sans\s+ke\s+siwa|سانس\s*کے\s*سوا", norm):
        return False

    if _has_cyanosis(norm):
        return True

    if _has_any(norm, _BREATHING_METAPHORS):
        return True

    # 1. Check negated breathing first
    if _has_any(norm, _BREATHING_NEGATIONS):
        # Exclude acute respiratory failure phrases from negation ONLY when failure verb itself is present
        # e.g., "sans nahi aa rahi" (air isn't coming) vs "koi sans ki takleef nahi" (no breathing trouble)
        has_failure_verb = bool(re.search(
            r"\bhawa\s+(?:andar\s+)?nahi\s+(?:jaa?ti|jaa?te|jaa?ta|jaa?\s*rahi|jaa?\s*raha|aati|aata|mil\s*rahi|mil\s*raha)\b|"
            r"\bair\s+(?:is\s+)?(?:not\s+going\s+in|wont\s+go\s+in|not\s+getting\s+in|cant\s+get\s+in)\b|"
            r"\b(?:sans|saans)\s+(?:bilkul\s+)?ukhri\s+hui\b|"
            r"\bsans\s+(?:\w+\s+){0,2}nahi\s+aa\s+rah[iyea]\b|"
            r"ہوا\s*(?:اندر\s*)?نہیں\s*(?:جاتی|جا\s*رہی|آتی|مل\s*رہی)|"
            r"سانس\s*(?:\S+\s*){0,2}نہیں\s*آ\s*رہی",
            norm
        ))
        has_preceding_negator = bool(re.search(
            r"\b(?:no|not|without|never|denies|zero)\s+(?:\w+\s+){0,3}(?:breathing|breath|shortness)\b|"
            r"\bkoi\s+(?:\w+\s+){0,3}(?:sans|saans|masla|takleef)\b|"
            r"کوئی\s*(?:\S+\s*){0,3}(?:سانس|تکلیف|مسئلہ)|"
            r"بغیر\s*(?:\S+\s*){0,2}(?:سانس|تکلیف)",
            norm
        ))
        if has_failure_verb and not has_preceding_negator:
            pass  # It's an acute failure verb!
        else:
            return False  # Suppressed by negation!

    # 2. Chronic conditions (asthma for years) or stable exertional dyspnea without rest/acute failure
    if _has_any(norm, _CHRONIC_PATTERNS) and not re.search(r"\b(?:cannot|cant|gasping|suffocating)\b", norm):
        return False

    has_exertion = _has_any(norm, _EXERTION_PATTERNS)
    has_acute_inability = bool(re.search(
        r"\b(?:cant|cannot|unable\s+to|gasp\w*|suffocat\w*|at\s+rest|sitting|lying|dam\s+ghut|ruk\s+rah|ukhri)\b|دم\s*گھٹ|اکھڑ",
        norm
    ))
    if has_exertion and not has_acute_inability:
        return False

    # 3. Acute inability & failure phrases
    if _has_any(norm, _BREATHING_INABILITY_PATTERNS):
        return True

    # 4. Concept-based proximity matching
    words = norm.split()
    if _has_proximity(words, _BREATH_ORGAN_TOKENS, _BREATH_DISTRESS_TOKENS, MAX_WINDOW_WORDS):
        return True

    if _has_proximity(words, _BREATH_ORGAN_TOKENS, _REST_POSITION_TOKENS, MAX_WINDOW_WORDS):
        if any(w in words for w in ("short", "difficult", "trouble", "hard", "cant", "cannot", "phool", "ghut", "mushkil", "نہیں", "مشکل")):
            return True

    return False


# =============================================================================
# Category 3: Confusion and Stroke
# =============================================================================

_STROKE_FAST_PATTERNS = [
    # Slurred speech / speech inability (FAST: Speech)
    r"\bslurred\s+speech\b",
    r"\bspeech\s+is\s+slurred\b",
    r"\bslurring\s+(?:my\s+)?words\b",
    r"\bwords\s+(?:\w+\s+){0,3}jumbled\b",
    r"\bjumbled\s+words\b",
    r"\b(?:lost\s+speech|lost\s+my\s+speech|unable\s+to\s+speak|cannot\s+speak|cant\s+speak)\b",
    r"\b(?:ajeeb\s+awaz|awaz\s+ajeeb|strange\s+voice)\b",
    r"\bzaban\s+ladkhada\b",
    r"\bawaz\s+ladkhada\b",
    r"\bbol\s+nahi\s+(?:pa|sak)\s+rah(?:a|i|in|e|y|ay|ey)\b",
    r"\bbol\s+nahi\s+(?:pa|sak)\s+rahe\s+hain\b",
    r"\bbolti\s+band\b",
    r"زبان\s*لڑکھڑا",
    r"آواز\s*لڑکھڑا",
    r"بول\s*نہیں\s*(?:پا|سک)\s*رہ(?:ا|ی|یں|ے)",
    r"بول\s*نہیں\s*(?:پا|سک)\s*رہے\s*ہیں",
    r"بولنا\s*(?:ممکن\s*نہیں|بند)",
    r"الفاظ\s*(?:گڈ\s*مڈ|سمجھ\s*نہیں\s*آ)",
    r"عجیب\s*آواز",
    r"آواز\s*عجیب",

    # Facial droop / asymmetry (FAST: Face)
    r"\b(?:face|mouth|eye)\s+(?:is\s+)?drooping\b",
    r"\bdrooping\s+(?:face|mouth|eye)\b",
    r"\bcrooked\s+(?:mouth|face|smile)\b",
    r"\bmouth\s+(?:\w+\s+){0,3}crooked\b",
    r"\bface\s+(?:is\s+)?drooping\s+(?:to\s+one\s+side)?\b",
    r"\bchehra\s+(?:\w+\s+){0,3}(?:jhuk|latak|tedha|terha)\b",
    r"\bmunh\s+(?:\w+\s+){0,3}(?:jhuk|latak|tedha|terha)\b",
    r"\bchehra\s+(?:achanak\s+)?(?:aik\s+taraf\s+)?(?:jhuk|latak|tedha|terha)\b",
    r"\bmunh\s+(?:achanak\s+)?(?:aik\s+taraf\s+)?(?:jhuk|latak|tedha|terha)\b",
    r"چہرہ\s*(?:\S+\s*){0,3}(?:لٹک|ٹیڑھا|جھک)",
    r"منہ\s*(?:\S+\s*){0,3}(?:ٹیڑھا|لٹک|جھک)",
    r"چہرہ\s*ٹیڑھا",

    # Unilateral weakness / numbness / limb inability (FAST: Arm / Body)
    r"\bone\s+side(?:d)?\s+(?:of\s+(?:my\s+)?(?:body|face|arm)\s+)?(?:(?:went|became|feels?|got|is)\s+)?(?:weak|numb|paralyzed)\b",
    r"\b(?:got\s+)?paralyzed\b",
    r"\bsudden\s+(?:weakness|numbness)\b",
    r"\bsuddenly\s+(?:feel\s+)?(?:weak|numb)\b",
    r"\b(?:arm|leg)\s+wont\s+move\b",
    r"\b(?:cant|cannot|unable\s+to)\s+move\s+my\s+(?:left|right)?\s*(?:arm|leg)\b",
    r"\b(?:left|right|one)\s+(?:arm|hand|leg|side)\s+(?:wont\s+lift|cant\s+lift|unable\s+to\s+lift)\b",
    r"\baik\s+taraf\s+ka\s+(?:jism|bazu|haath|hath|chehra|tang)\s+(?:\w+\s+){0,3}(?:ka?am\s+nahi\s+kar|uth\s+nahi\s+rah|hil\s+nahi\s+rah|sunn|kamzor|latak|tedha|terha)\b",
    r"\badha\s+jism\s+(?:\w+\s+){0,3}(?:sunn|kamzor)\b",
    r"\b(?:face|arm|chehra|bazu)\s+(?:\w+\s+){0,3}(?:sunn|kamzor|numb|weak)\b",
    r"\b(?:haath|hath|bazu)\s+(?:uth|hil)\s+nahi\s+rah(?:a|i|in|e|y|ay)\b",
    r"ایک\s*طرف\s*کمزوری",
    r"ایک\s*طرف\s*کا\s*(?:جسم|بازو|ہاتھ|چہرہ|ٹانگ)\s*(?:\S+\s*){0,3}(?:کام\s*نہیں\s*کر|اٹھ\s*نہیں\s*رہ|ہل\s*نہیں\s*رہ|سن|کمزور|لٹک|ٹیڑھا)",
    r"(?:ہاتھ|بازو)\s*(?:اٹھ|ہل)\s*نہیں\s*رہ(?:ا|ی|یں|ے)",
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
    # Speech / Comprehension inability & failure verbs
    r"\b(?:baat|alfaaz|words?)\s+(?:\w+\s+){0,2}samajh\s+nahi\s+(?:aa\s+rah[iyea]*|pa\s+rah[iyea]*|sak\w*)\b",
    r"\bbaat\s+nahi\s+samajh\s+aa\s+rah[iyea]*\b",
    r"\bkuch\s+samajh\s+nahi\s+aa\s+raha\s+kya\s+bol\b",
    r"\b(?:cant|cannot|unable\s+to)\s+understand\s+(?:what\s+(?:they|he|she)\s+is\s+saying|words|speech)\b",
    r"\bwords\s+(?:make\s+no\s+sense|not\s+making\s+sense|dont\s+make\s+sense)\b",
    r"بات\s*(?:\S+\s*){0,2}سمجھ\s*نہیں\s*(?:آ\s*رہ|پا\s*رہ|سک)",
    r"الفاظ\s*سمجھ\s*نہیں\s*آ\s*رہ",
    r"کچھ\s*سمجھ\s*نہیں\s*آ\s*رہا\s*کیا\s*بول",
    # Motor / Limb failure verbs (hand, arm, leg, foot)
    r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,3}(?:hila\s+)?nahi\s+(?:pa\s+rah[iyea]*|sak\w*|rah[iyea]*)\b",
    r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,2}(?:uth|hil)\s+nahi\s+rah[iyea]*\b",
    r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,2}(?:ka?am\s+)?nahi\s+kar\s+rah[iyea]*\b",
    r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:bilkul\s+)?ka?am\s+nahi\s+kar\b",
    r"\b(?:haath|hath|bazu|pair|tang|taang)\s+nahi\s+(?:uth|hil)\s+rah[iyea]*\b",
    r"\b(?:cant|cannot|unable\s+to|wont)\s+(?:move|lift)\s+(?:\w+\s+){0,2}(?:arm|leg|hand|foot|side|limb)\b",
    r"\b(?:arm|leg|hand|foot|side|limb)\s+(?:is\s+)?(?:wont|cant|cannot|not)\s+(?:move|lift|working)\b",
    r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,3}(?:نہیں\s*ہلا\s*پا|ہلا\s*نہیں\s*پا|نہیں\s*ہل|نہیں\s*اٹھ|کام\s*نہیں\s*کر|ہل\s*نہیں\s*رہ|اٹھ\s*نہیں\s*رہ)",
    r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,2}(?:اٹھ|ہل)\s*نہیں\s*رہ",
    r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,2}(?:کام\s*)?نہیں\s*کر\s*رہ",
    # "Ajeeb baatein" (confused speech) + limb that won't move
    r"\b(?:ajeeb\s+baat\w*|strange\s+words?|talking\s+strange\w*|confused\s+speech|nonsense\s+words?)\b.*?\b(?:haath|hath|bazu|pair|tang|taang|arm|leg|hand|limb)\b.*?\b(?:hil|uth|ka?am|move|lift)\b",
    r"\b(?:haath|hath|bazu|pair|tang|taang|arm|leg|hand|limb)\b.*?\b(?:hil|uth|ka?am|move|lift)\b.*?\b(?:ajeeb\s+baat\w*|strange\s+words?|talking\s+strange\w*|confused\s+speech|nonsense\s+words?)\b",
    r"عجیب\s*بات.*?(?:ہاتھ|بازو|ٹانگ|پاؤں).*?(?:ہل|اٹھ|کام)",
    r"(?:ہاتھ|بازو|ٹانگ|پاؤں).*?(?:ہل|اٹھ|کام).*?عجیب\s*بات",
    # "Aadha chehra latka" + speech/comprehension
    r"\b(?:chehra|munh|face|mouth)\s+(?:\w+\s+){0,3}(?:latk\w*|latak\w*|jhuk\w*|tedh\w*|terh\w*|droop\w*|crooked)\b.*?\b(?:bol\w*|awaz|baat|samajh|speech|words?|speak\w*|understand\w*)\b",
    r"\b(?:bol\w*|awaz|baat|samajh|speech|words?|speak\w*|understand\w*)\b.*?\b(?:chehra|munh|face|mouth)\s+(?:\w+\s+){0,3}(?:latk\w*|latak\w*|jhuk\w*|tedh\w*|terh\w*|droop\w*|crooked)\b",
    r"(?:چہرہ|منہ)\s*(?:\S+\s*){0,3}(?:لٹک|جھک|ٹیڑھا).*?(?:بول|آواز|بات|سمجھ|الفاظ)",
    r"(?:بول|آواز|بات|سمجھ|الفاظ).*?(?:چہرہ|منہ)\s*(?:\S+\s*){0,3}(?:لٹک|جھک|ٹیڑھا)",
    # Unilateral side numb (daayan/baayan hissa sunn)
    r"\b(?:daaya?n|baaya?n|daye?n|baye?n|seedha|ulta)\s+(?:hissa|jism|tarf|side)\s+(?:\w+\s+){0,2}(?:sunn?|sun)\b",
    r"(?:دایاں|بایاں|دائیں|بائیں|سیدھا|الٹا)\s*(?:حصہ|جسم|طرف)\s*(?:\S+\s*){0,2}(?:سن)",
    # Sudden drooling / munh se raal
    r"\b(?:munh|muh|mouth)\s+(?:se\s+)?raal\b.*?\b(?:achanak|sudden\w*|foran|yakdam)\b",
    r"\b(?:achanak|sudden\w*|foran|yakdam)\b.*?\b(?:munh|muh|mouth)\s+(?:se\s+)?raal\b",
    r"\b(?:drool\w*)\b.*?\b(?:sudden\w*|abrupt\w*)\b",
    r"\b(?:sudden\w*|abrupt\w*)\b.*?\b(?:drool\w*)\b",
    r"(?:منہ\s*سے\s*رال|رال).*?(?:اچانک|فورا|یکدم)",
    r"(?:اچانک|فورا|یکدم).*?(?:منہ\s*سے\s*رال|رال)",
    # Hand/arm is useless
    r"\b(?:hand|arm|leg|foot|limb|bazu|hath|haath|tang|taang)\s+(?:is\s+)?(?:completely\s+|bilkul\s+)?(?:useless|dead|limp|paralyzed|paralysed|be\s*jaan|bekaar)\b",
    r"(?:ہاتھ|بازو|ٹانگ|پاؤں)\s*(?:بالکل\s*)?(?:بے\s*جان|بیکار|شل)",
    # Speech went weird/strange suddenly
    r"\b(?:speech|voice|talking)\s+(?:\w+\s+){0,3}(?:went|became|turned|got)\s+(?:\w+\s+){0,2}(?:weird|strange|slurred|garbled|unclear|incoherent)\s+(?:suddenly|all\s+of\s+a\s+sudden)\b",
    r"\b(?:suddenly|all\s+of\s+a\s+sudden)\s+(?:\w+\s+){0,2}(?:speech|voice|talking)\s+(?:\w+\s+){0,3}(?:went|became|turned|got)\s+(?:\w+\s+){0,2}(?:weird|strange|slurred|garbled|unclear|incoherent)\b",
    r"\b(?:awaaz|bolna|baat)\s+(?:\w+\s+){0,3}(?:achanak|achanak\s+se)\s+(?:\w+\s+){0,2}(?:ajeeb|ladkhada\w*|tut\w*|garbar)\b",
]


def _is_stroke_negated(norm: str) -> bool:
    # Exclude acute stroke failure phrases from negation ONLY when failure verb itself is present
    has_failure = bool(re.search(
        r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,3}(?:hila\s+)?nahi\s+(?:pa\s+rah|sak|rah)|"
        r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,2}(?:uth|hil)\s+nahi\s+rah|"
        r"\b(?:haath|hath|bazu|pair|tang|taang)\s+(?:\w+\s+){0,2}(?:ka?am\s+)?nahi\s+kar|"
        r"\b(?:cant|cannot|unable\s+to|wont)\s+(?:move|lift)\s+(?:\w+\s+){0,2}(?:arm|leg|hand|foot|side|limb)|"
        r"\b(?:arm|leg|hand|foot|side|limb)\s+(?:wont|cant|cannot|not)\s+(?:move|lift|working)|"
        r"\b(?:baat|alfaaz|words?)\s+(?:\w+\s+){0,2}samajh\s+nahi|"
        r"\bbaat\s+nahi\s+samajh\s+aa\s+rah|"
        r"\bwords\s+(?:make\s+no\s+sense|not\s+making\s+sense|dont\s+make\s+sense)|"
        r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,3}(?:ہلا\s*)?نہیں\s*(?:پا\s*رہ|سک|رہ)|"
        r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,2}(?:اٹھ|ہل)\s*نہیں\s*رہ|"
        r"(?:ہاتھ|بازو|پاؤں|ٹانگ)\s*(?:\S+\s*){0,2}(?:کام\s*)?نہیں\s*کر\s*رہ|"
        r"بات\s*(?:\S+\s*){0,2}سمجھ\s*نہیں\s*(?:آ\s*رہ|پا\s*رہ|سک)",
        norm
    ))
    has_preceding_negator = bool(re.search(
        r"\b(?:no|not|without|never|denies|denied|zero)\s+(?:\w+\s+){0,3}(?:weakness|numbness|slurr\w*|droop\w*|stroke|paralysis|speech|difficulty|trouble|problem|masla|takleef)\b|"
        r"\bkoi\s+(?:\w+\s+){0,2}(?:kamzori|sunn|ladkhada\w*|falij|masla|takleef)\b|"
        r"کوئی\s*(?:\S+\s*){0,2}(?:کمزوری|سن|لڑکھڑاہٹ|فالج|مسئلہ|تکلیف)|"
        r"بغیر\s*(?:\S+\s*){0,2}(?:کمزوری|فالج)",
        norm
    ))
    if has_failure and not has_preceding_negator:
        return False

    if re.search(
        r"\b(?:no|not|denies|denied|without|never|"
        r"i\s+do\s*n\s*['’]?\s*t\s+have|i\s+did\s*n\s*['’]?\s*t\s+have|"
        r"i\s+have\s+no|there\s+is\s+no|not\s+feeling\s+any|no\s+sign\s+of|"
        r"i\s*['’]?\s*m\s+not\s+having|free\s+of)\s+(?:\w+\s+){0,3}"
        r"(?:slurr\w*|speech|droop\w*|weakness|numbness|facial|stroke|paralysis|trouble|problem|masla|takleef)\b",
        norm
    ):
        return True
    if re.search(r"\b(?:speech|face|arm|hand|leg|side|haath|bazu|pair|tang|chehra)\s+(?:is\s+)?(?:completely\s+)?(?:normal|fine|ok|okay|theek|thik|sahi)\b", norm):
        return True
    if re.search(r"\b(?:chehra|zaban|awaz|bazu|hath|haath|tang|pair)\s+(?:theek|thik|sahi)\s+hai\b", norm):
        return True
    if re.search(r"\b(?:mujhe\s+koi|koi\s+bhi)\s+(?:\w+\s+){0,3}(?:kamzori|sunn|ladkhada\w*|falij|masla|takleef)\s+(?:to\s+|bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\b(?:kamzori|sunn|ladkhada\w*|falij)\s+(?:\w+\s+){0,2}(?:to\s+|bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\bkoi\s+(?:\w+\s+){0,2}(?:ladkhada\w*|falij|kamzori|sunn|masla|takleef)\s+nahi\b", norm):
        return True
    if re.search(r"(?:مجھے\s+کوئی|کوئی\s+بھی)\s*(?:\S+\s*){0,3}(?:کمزوری|سن|لڑکھڑاہٹ|فالج|مسئلہ|تکلیف)\s*(?:بھی\s*)?(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"(?:کمزوری|سن|لڑکھڑا|فالج)\s*(?:\S+\s*){0,2}(?:تو|بھی)?\s*(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"کوئی\s*(?:\S+\s*){0,2}(?:کمزوری|سن|لڑکھڑاہٹ|فالج|مسئلہ|تکلیف)\s*(?:\S+\s*){0,2}نہیں", norm):
        return True
    return False


def _is_benign_postural_or_chronic_numbness(norm: str, words: List[str]) -> bool:
    """
    Detects benign postural, ergonomic, or chronic intermittent limb numbness/tingling
    (e.g., sleeping on arm, sitting long, typing/using mobile, comes and goes for months)
    with NO sudden onset and NO second focal neurological deficit (speech/facial droop/paralysis).
    """
    # 1. Must have a limb numbness / tingling cue
    has_numbness = bool(re.search(
        r"\b(?:numb\w*|tingl\w*|pins\s+and\s+needles|sunn|soya|soi|soye|jhanjhanahat)\b|سن|سویا|سوئی|جھنجھناہٹ",
        norm
    ))
    if not has_numbness:
        return False

    # 2. Must have a clear benign trigger or chronic intermittent pattern
    has_benign_trigger = bool(re.search(
        r"\b(?:jab|when|after)\s+(?:\w+\s+){0,5}(?:mobile|phone|typing|type|computer|screen|chalata|chalatay|chalati|baithta|baithtay|baithti|sota|sotay|soti|sleep\w*|sitting)\b|"
        r"\b(?:when\s+i\s+sleep\s+on\s+it|slept\s+on\s+(?:my\s+)?(?:arm|hand)|sleeping\s+on\s+it|after\s+typing|using\s+(?:the\s+)?phone|using\s+mobile|holding\s+(?:the\s+)?phone)\b|"
        r"\b(?:der\s+tak\s+(?:mobile|phone|baith|computer)|zyada\s+der\s+(?:baith|mobile)|cross\s+legged)\b|"
        r"\b(?:comes\s+and\s+goes(?:\s+for\s+(?:months|years|weeks))?|off\s+and\s+on\s+for\s+(?:months|years|weeks)|for\s+(?:months|years))\b|"
        r"\b(?:mahino\s+se|kai\s+mahine|hafto\s+se|ata\s+jata\s+hai|aata\s+jaata\s+hai|kabhi\s+kabhi\s+hota\s+hai)\b|"
        r"جب\s*(?:\S+\s*){0,4}(?:موبائل|فون|بیٹھ|سو|کمپیوٹر)|مہینوں\s*سے|کبھی\s*کبھی",
        norm
    ))
    if not has_benign_trigger:
        return False

    # 3. Check for sudden onset (precludes benign posture)
    has_sudden_onset = bool(re.search(
        r"\b(?:sudden|suddenly|all\s+of\s+a\s+sudden|abrupt|abruptly|achanak|yakdam|aik\s*dam|achanak\s+se)\b|اچانک|ایک\s*دم",
        norm
    ))
    if has_sudden_onset:
        return False

    # 4. Check for second focal neurological deficit (FAST)
    has_face = _has_proximity(words, _STROKE_FACE_TOKENS, _STROKE_DROOP_TOKENS, MAX_WINDOW_WORDS)
    has_speech = _has_proximity(words, _STROKE_SPEECH_TOKENS, _STROKE_SPEECH_DEFICIT_TOKENS, MAX_WINDOW_WORDS)
    has_paralysis = bool(re.search(
        r"\b(?:cant\s+move|unable\s+to\s+move|wont\s+move|cannot\s+move|paraly\w*|falij|hila\s+nahi|uth\s+nahi|kaam\s+nahi\s+kar)\b|کام\s*نہیں\s*کر|ہلا\s*نہیں|فالج",
        norm
    ))
    if has_face or has_speech or has_paralysis:
        return False

    return True


_STROKE_FACE_TOKENS = {
    "face", "facial", "mouth", "smile", "chehra", "chehre", "munh", "mooh", "چہرہ", "منہ"
}
_STROKE_DROOP_TOKENS = {
    "droop", "drooping", "drooped", "crooked", "asymmetric", "twisted", "lopsided", "slack", "slanted",
    "tedha", "terha", "jhuk", "latak", "latka", "latki", "latkay", "jhuka", "jhuki", "jhukay", "tedhi", "terhi",
    "ٹیڑھا", "جھک", "لٹک"
}

_STROKE_SPEECH_TOKENS = {
    "speech", "words", "voice", "speak", "talking",
    "zaban", "zuban", "awaz", "awaaz", "bol", "bolna", "bolti",
    "زبان", "آواز", "بول", "بولنا", "الفاظ"
}
_STROKE_SPEECH_DEFICIT_TOKENS = {
    "slur", "slurred", "slurring", "jumble", "jumbled", "garbled", "confused", "incoherent", "strange",
    "lost", "cant", "cannot", "unable", "ladkhada", "ladkhadata", "ajeeb", "band", "ruk", "samajh",
    "لڑکھڑا", "عجیب", "بند", "گڈ مڈ", "سمجھ"
}

_STROKE_LIMB_TOKENS = {
    "side", "arm", "hand", "leg", "body", "limb", "half",
    "bazu", "haath", "hath", "tang", "pair", "jism", "adha",
    "بازو", "ہاتھ", "ٹانگ", "جسم", "آدھا"
}
_STROKE_LIMB_DEFICIT_TOKENS = {
    "paralyze", "paralyzed", "paralysis", "weak", "weakness", "numb", "numbness", "dead", "limp",
    "immobile", "frozen", "kamzor", "kamzori", "sunn", "bejan", "falij", "hil", "uth", "hila",
    "فالج", "سن", "کمزور", "بے جان", "ہل", "اٹھ"
}


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

    words = norm.split()

    # Suppress benign postural or chronic intermittent limb numbness
    if _is_benign_postural_or_chronic_numbness(norm, words):
        return False

    # Concept-based FAST proximity matching
    if _has_proximity(words, _STROKE_FACE_TOKENS, _STROKE_DROOP_TOKENS, MAX_WINDOW_WORDS):
        return True
    if _has_proximity(words, _STROKE_SPEECH_TOKENS, _STROKE_SPEECH_DEFICIT_TOKENS, MAX_WINDOW_WORDS):
        return True
    if _has_proximity(words, _STROKE_LIMB_TOKENS, _STROKE_LIMB_DEFICIT_TOKENS, MAX_WINDOW_WORDS):
        return True

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
    r"\b(?<!haath\s)(?<!hath\s)(?<!bazu\s)(?<!chehra\s)(?<!tang\s)(?<!pair\s)uth\s+nahi\s+rah",
    r"\bpa[rd][ai]\s+hai\s+aur\s+uth\s+nahi\b",
    r"ہوش\s*میں\s*نہیں\s*آ\s*رہ",
    r"ہوش\s*نہیں\s*آ\s*رہ",
    r"جواب\s*نہیں\s*دے\s*رہ",
    r"بے\s*ہوش\s*پڑا\s*ہے",
    r"(?<!ہاتھ\s)(?<!بازو\s)(?<!چہرہ\s)(?<!ٹانگ\s)(?<!پاؤں\s)اٹھ\s*نہیں\s*رہ",
    # Eye opening failure / Unable to open eyes
    r"\baankh(?:ein)?\s+(?:\w+\s+){0,2}nahi\s+(?:khol|khul)\s*rah",
    r"\baankh(?:ein)?\s+(?:\w+\s+){0,2}(?:khol|khul)\s*nahi\s*rah",
    r"\beyes?\s+(?:wont|cant|cannot|unable\s+to|not)\s+(?:open|opening)\b",
    r"\b(?:cant|cannot|unable\s+to|wont)\s+open\s+(?:eyes?|his\s+eyes?|her\s+eyes?)\b",
    r"آنکھ(?:یں)?\s*(?:\S+\s*){0,2}نہیں\s*(?:کھول|کھل)\s*رہ",
    r"آنکھ(?:یں)?\s*(?:\S+\s*){0,2}(?:کھول|کھل)\s*نہیں\s*رہ",
    # Be-sudh (deep stupor / unresponsive)
    r"\bbe\s+sudh\b",
    r"بے\s*سدھ",
    # Found on the floor
    r"\bfound\s+(?:\w+\s+){0,2}on\s+(?:the\s+)?floor\b",
    r"\b(?:zameen|farsh)\s+par\s+(?:par[aiey]|par[eay]|gir[aiey]|gir[eay])\s+mil",
    r"فرش\s*پر\s*پڑا\s*ملا",
    r"زمین\s*پر\s*پڑا\s*ملا",
    # Out for unknown duration + drowsy
    r"\b(?:dont|do\s+not)\s+know\s+how\s+long\s+(?:i\s+was\s+)?out\b.*?\b(?:drowsy|drowsiness|sleepy|confused|unsteady)\b",
    r"\b(?:drowsy|drowsiness|sleepy|confused|unsteady)\b.*?\b(?:dont|do\s+not)\s+know\s+how\s+long\s+(?:i\s+was\s+)?out\b",
    r"\bkitni\s+der\s+(?:be\s*hosh|be\s*sudh)\s+raha\s+nahi\s+pata\b.*?\b(?:ghunoodgi|nasha|chakkar)\b",
]

_SYNCOPE_RECOVERY_PATTERNS = [
    r"\b(?:theek|thik)\s+(?:ho\s+gaya|hai|hoon|hun)\b",
    r"\b(?:fine|better|okay|ok|normal)\s+now\b",
    r"\bcompletely\s+fine\b",
    r"\bfully\s+recovered\b",
    r"\bab\s+(?:bilkul\s+)?(?:theek|behtar|achha)\b",
    r"\bhosh\s+aa\s+gaya\b",
    r"\bwoke\s+up\b",
    r"\bnow\s+awake\b",
    r"\brecovered\b",
    r"\bاب\s*(?:بالکل\s*)?(?:ٹھیک|بہتر)\b",
    r"\bٹھیک\s*(?:ہو\s*گیا|ہوں|ہے)\b",
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
    if re.search(
        r"\b(?:did\s+not|didn\s*t|not|never|no|denies|"
        r"i\s+do\s*n\s*['’]?\s*t\s+have|i\s+did\s*n\s*['’]?\s*t\s+have|"
        r"i\s+have\s+no|there\s+is\s+no|not\s+feeling\s+any|no\s+sign\s+of|"
        r"i\s*['’]?\s*m\s+not\s+having|free\s+of)\s+(?:\w+\s+){0,3}"
        r"(?:faint\w*|pass\w*\s+out|black\w*\s+out|collaps\w*|unconscious\w*|chakkar|dizziness)\b",
        norm
    ):
        return True
    if re.search(r"\b(?:mujhe\s+koi|koi\s+bhi)\s+(?:\w+\s+){0,3}(?:be\s*hosh|ghashi|chakkar)\s+(?:to\s+|bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\b(?:be\s*hosh|ghashi|chakkar)\s+(?:\w+\s+){0,2}(?:to\s+|bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\bnahi\s+(?:\w+\s+){0,2}(?:be\s*hosh|chakkar)\b", norm):
        return True
    if re.search(r"(?:مجھے\s+کوئی|کوئی\s+بھی)\s*(?:\S+\s*){0,3}(?:بے\s*ہوش|غشی|چکر)\s*(?:بھی\s*)?(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"(?:بے\s*ہوش|غشی|چکر)\s*(?:\S+\s*){0,2}(?:تو|بھی)?\s*(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
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
    Crucially, this function assesses syncope recovery ONLY and must not be used
    to suppress non-syncope emergencies.
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
    # 1. Active unresponsiveness / inability to wake / eye opening failure is ALWAYS emergency
    if _has_any(norm, _UNRESPONSIVE_PATTERNS):
        return True

    if _is_syncope_negated(norm):
        return False

    # 2. If recovered or transient syncopal episode, suppress from emergency (stays on review path)
    if is_fainting_recovered_or_benign(norm):
        return False

    # 3. Loss of consciousness / syncope keywords
    if _has_any(norm, _SYNCOPE_KEYWORDS):
        return True

    return False


# =============================================================================
# Category 5: DKA / Fluids / Persistent Vomiting
# =============================================================================

_FLUIDS_DKA_PATTERNS = [
    # Fluid inability (English)
    r"\b(?:cant|cannot|unable\s+to|wont)\s+(?:keep|hold)\s+(?:\w+\s+){0,4}down\b",
    r"\bnothing\s+(?:is\s+)?stay(?:s|ing)?\s+down\b",
    r"\b(?:even\s+)?(?:a\s+sip\s+of\s+)?(?:water|fluid|fluids|liquid|liquids|food)\s+(?:comes?\s+(?:right\s+)?back\s+up|wont\s+stay\s+down)\b",
    r"\b(?:water|fluid|fluids|liquid|liquids|food|everything)\s+(?:comes?|keeps?\s+coming)\s+(?:right\s+)?back\s+up\b",
    r"\bthrowing\s+up\s+(?:everything|non-?stop|all\s+day)\b",
    r"\bkeep\s+nothing\s+down\b",
    r"\bvomiting\s+(?:non-?stop|continuously|all\s+day)\b",
    r"\b(?:vomiting|throwing\s+up|fluids?\s+come\s+back\s+up|liquids\s+come\s+(?:right\s+)?back\s+up)\s+(?:with\s+)?(?:very\s+)?high\s+(?:sugar|glucose)\b",
    r"\b(?:liquids|fluids)\s+down\s+with\s+(?:very\s+)?high\s+(?:sugar|glucose)\b",
    # Roman Urdu fluid inability & intractable vomiting
    r"\bpani\s+(?:bhi\s+)?(?:andar\s+)?nahi\s+(?:ruk|tik|rehta|rahta)\s+rah[iyea]\b",
    r"\bpani\s+(?:bhi\s+)?(?:andar\s+)?(?:rukta|tikta|rehta|rahta)\s+nahi\b",
    r"\bpani\s+(?:bhi\s+)?(?:andar\s+)?nahi\s+(?:rukta|tikta|rehta|rahta|ruk|tik|rehta|rahta)\b",
    r"\b(?:kuch\s+bhi\s+)?andar\s+nahi\s+(?:rehta|rahta|rukta|tikta)\b",
    r"\b(?:ek\s+)?ghoont\s+(?:bhi\s+)?(?:wapis|wapas|nikal|ulti)\b",
    r"\b(?:ek\s+)?ghoont\s+(?:bhi\s+)?(?:andar\s+)?nahi\s+(?:ruk|tik|rehta|rahta|rukta|tikta)\b",
    r"\bjo\s+(?:bhi\s+)?(?:peeta|peeti|khata|khati)\s+(?:hoon|hun)\s+(?:\w+\s+){0,2}(?:nikal|wapas|wapis|ulti)\b",
    r"\bpani\s+(?:\w+\s+){0,3}(?:wapas|wapis)\b",
    r"\b(?:kuch\s+)?(?:bhi\s+)?hazam\s+nahi\s+ho\s+raha\b",
    r"\bhar\s+cheez\s+ulti\b",
    r"\bulti\s+ruk\s+nahi\s+rahi\b",
    r"\bmusalsal\s+ultiyan\b",
    r"\bultiyan\s+ruk\s+nahi\s+rah\b",
    r"\bkuch\s+bhi\s+pet\s+me\s+nahi\s+ruk\s+raha\b",
    # Urdu script fluid inability & intractable vomiting
    r"الٹی\s*رک\s*نہیں\s*رہی",
    r"الٹیاں\s*بند\s*نہیں\s*ہو\s*رہ",
    r"پانی\s*(?:بھی\s*)?(?:اندر\s*)?نہیں\s*(?:رکتا|ٹکتا|رہتا|رک\s*رہا|ٹک\s*رہا)",
    r"ایک\s*گھونٹ\s*(?:بھی\s*)?(?:واپس|نہیں\s*(?:رکتا|ٹکتا|رہتا))",
    r"جو\s*(?:بھی\s*)?(?:پیتا|کھاتا)\s*ہوں\s*(?:\S+\s*){0,2}(?:نکل|واپس|الٹی)",
    r"پانی\s*بھی\s*واپس",
    r"مسلسل\s*الٹیاں",
    r"شدید\s*قے",
    r"کچھ\s*بھی\s*(?:پیٹ\s*میں\s*)?نہیں\s*(?:ٹھہر|رک|ٹک|رہ)",
    r"ہر\s*چیز\s*(?:کی\s*)?الٹی",
    r"شوگر\s*(?:\S+\s*){0,3}الٹیاں",
]


def _is_vomiting_negated(norm: str) -> bool:
    # English negations
    if re.search(
        r"\b(?:no|not|without|denies|never|"
        r"i\s+do\s*n\s*['’]?\s*t\s+have|i\s+did\s*n\s*['’]?\s*t\s+have|"
        r"i\s+have\s+no|there\s+is\s+no|not\s+feeling\s+any|no\s+sign\s+of|"
        r"i\s*['’]?\s*m\s+not\s+having|free\s+of)\s+(?:\w+\s+){0,3}"
        r"(?:vomit\w*|throwing\s+up|puk\w*|nausea)\b",
        norm
    ):
        return True
    if re.search(r"\b(?:able\s+to\s+keep|keeping)\s+(?:\w+\s+){0,3}(?:food|fluids?|water|liquids?)\s+down\s+(?:fine|well|normally)\b", norm):
        return True
    if re.search(r"\bable\s+to\s+drink\s+(?:water|fluids?|soup)\b", norm):
        return True
    if re.search(r"\bdrinking\s+water\s+(?:normally|fine|well|aaram\s+se)\b", norm):
        return True
    if re.search(r"\bno\s+vomiting\s+or\s+inability\b", norm):
        return True
    # Roman Urdu negations
    if re.search(r"\b(?:mujhe\s+koi|koi\s+bhi)\s+(?:\w+\s+){0,3}(?:ulti|ultiyan|qay|matli)\s+(?:to\s+|bhi\s+)?(?:bilkul\s+)?nahi(?:\s+hai)?\b", norm):
        return True
    if re.search(r"\b(?:koi\s+)?(?:ulti|ultiyan|qay|matli)\s+(?:bilkul\s+)?nahi\s+(?:hai|aayi|hui)?\b", norm):
        return True
    if re.search(r"\bulti\s+bilkul\s+nahi\b", norm):
        return True
    if re.search(r"\bkoi\s+(?:\w+\s+){0,4}(?:ulti|qay|matli)\b.*?\bnahi\b", norm):
        return True
    if re.search(r"\bkhana\s+(?:peena\s+)?theek\s+(?:ruk|hazam)\b", norm):
        return True
    if re.search(r"\bkhana\s+hazam\s+ho\s+raha\b", norm):
        return True
    # Urdu script negations
    if re.search(r"(?:مجھے\s+کوئی|کوئی\s+بھی)\s*(?:\S+\s*){0,3}(?:الٹی|الٹیاں|قے|متلی)\s*(?:بھی\s*)?(?:بالکل\s*)?نہیں(?:\s*ہے)?", norm):
        return True
    if re.search(r"(?:الٹی|الٹیاں|قے|متلی)\s*(?:بالکل\s*)?نہیں\s*(?:ہے|آئی|ہوئی)?", norm):
        return True
    if re.search(r"الٹی\s*بالکل\s*نہیں", norm):
        return True
    if re.search(r"کوئی\s*(?:بھی\s*)?(?:الٹی|الٹیاں|قے|متلی)\s*نہیں", norm):
        return True
    if re.search(r"کھانا\s*(?:پینا\s*)?ٹھیک\s*(?:ہو\s*رہا|ہضم|رک)", norm):
        return True
    if re.search(r"کھانا\s*ہضم\s*ہو\s*رہا", norm):
        return True
    return False


_FLUID_TOKENS = {
    "water", "fluid", "fluids", "liquids", "drink", "sip", "food",
    "pani", "paani", "ghoont", "ghunt", "peeta", "peeti", "khata", "khati",
    "پانی", "گھونٹ", "پیتا", "کھاتا"
}
_VOMIT_DEFICIT_TOKENS = {
    "vomit", "vomiting", "vomited", "vomits", "puke", "puking",
    "ulti", "ultiyan", "qay",
    "الٹی", "الٹیاں", "قے"
}


def _match_dka_vomiting_fluids(norm: str) -> bool:
    if _is_vomiting_negated(norm):
        return False

    # 1. Recovery cancellation: "ab paani pee raha hoon / keeping water down now" cancels fluids hit
    is_fluids_recovered = bool(re.search(
        r"\b(?:ab\s+(?:to\s+)?(?:pani|paani)\s+(?:pee|pi)\s*rah[iyea]|"
        r"(?:pani|paani)\s+(?:pee|pi)\s*rah[iyea]\s*(?:hoon|hun|hai|hain)?|"
        r"can\s+drink|able\s+to\s+drink|drinking\s+(?:water|fluids?|liquids?)\s+(?:now|fine|normally|well)|"
        r"keeping\s+(?:water|fluids?|liquids?|down)\s+(?:now|fine|well|normally)|"
        r"tolerat(?:ing|es?)\s+(?:fluids?|water|liquids?)|"
        r"اب\s*(?:تو\s*)?پانی\s*پی\s*رہ|"
        r"پانی\s*پی\s*رہ[ا|ی]|"
        r"پانی\s*(?:ہضم|ٹھہر)\s*رہا)\b",
        norm
    ))
    if is_fluids_recovered:
        return False

    # 2. Single vomit suppression: "ek baar ulti hui" without intractable / repeated vomiting is NOT Red
    is_single_vomit = bool(re.search(
        r"\b(?:once|single|just\s+one|only\s+one|1\s+time|one\s+time|"
        r"ek\s+ba+r|aik\s+ba+r|ek\s+dafa|aik\s+dafa|sirf\s+ek|sirf\s+aik|"
        r"ایک\s*بار|ایک\s*دفعہ|صرف\s*ایک)\b",
        norm
    ))
    has_repeated_vomiting = bool(re.search(
        r"\b(?:ba+r\s+ba+r|non-?stop|continuously|continuous|har\s+cheez|everything|"
        r"ulti\s+pe\s+ulti|ultiyan\s+pe\s+ultiyan|musalsal|\d+\s+ghant(?:ay|e|on)\s+se|"
        r"(?:for|since)\s+\d+\s+hours?|بار\s*بار|مسلسل|ہر\s*چیز|الٹی\s*پہ\s*الٹی)\b",
        norm
    ))
    has_fluid_inability = bool(re.search(
        r"\b(?:cant|cannot|unable\s+to|wont)\s+(?:keep|hold)\s+(?:\w+\s+){0,4}down|"
        r"nothing\s+(?:is\s+)?staying?\s+down|"
        r"keeps?\s+coming\s+(?:right\s+)?back\s+up|"
        r"pani\s+(?:bhi\s+)?(?:andar\s+)?nahi\s+(?:ruk|tik|rehta|rahta)|"
        r"pani\s+(?:bhi\s+)?(?:andar\s+)?(?:rukta|tikta|rehta|rahta)\s+nahi|"
        r"andar\s+nahi\s+(?:rehta|rahta|rukta|tikta)|"
        r"ghoont\s+(?:bhi\s+)?(?:wapas|nikal|ulti)|"
        r"پانی\s*(?:بھی\s*)?(?:اندر\s*)?نہیں\s*(?:رک|ٹک|رہ)|"
        r"ایک\s*گھونٹ\s*(?:بھی\s*)?واپس\b",
        norm
    ))

    if is_single_vomit and not (has_repeated_vomiting or has_fluid_inability):
        return False

    # 3. Explicit fluids DKA / intractable patterns
    if _has_any(norm, _FLUIDS_DKA_PATTERNS):
        return True

    # 4. Repeated vomiting proximity
    if has_repeated_vomiting and bool(re.search(r"\b(?:vomit\w*|throwing\s+up|ulti|ultiyan|qay|الٹی|الٹیاں|قے)\b", norm)):
        return True

    return False


# =============================================================================
# Primary Public API
# =============================================================================

def match_categories(raw_text: str) -> List[str]:
    """
    Returns all matching Stage-1 red flag categories for an utterance.
    Guaranteed no-throw.
    """
    matched = []
    try:
        if not raw_text or not isinstance(raw_text, str):
            return matched
        norm = normalize_text(raw_text)
        if not norm:
            return matched

        # Global suppressions (remote past without current acute, exertion with rest relief)
        if _is_suppressed(norm):
            return matched

        # 1. Chest pain (including metaphors, radiation, diaphoresis)
        if _match_chest_pain(norm):
            matched.append("chest_pain")

        # 2. Breathing inability & severe distress
        if _match_breathing(norm):
            matched.append("breathing")

        # 3. FAST stroke / confusion / neurological deficit
        if _match_confusion_and_stroke(norm):
            matched.append("confusion_and_stroke")

        # 4. Syncope / Loss of consciousness (recovery check strictly scoped to fainting)
        if _match_loss_of_consciousness(norm):
            matched.append("loss_of_consciousness")

        # 5. DKA / Fluid intolerance / Persistent vomiting
        if _match_dka_vomiting_fluids(norm):
            matched.append("dka_vomiting_high_glucose")

        return matched
    except Exception:
        return []


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
        cats = match_categories(raw_text)
        if cats:
            return True, cats[0]
        return False, None
    except Exception:
        return False, None
