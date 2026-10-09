"""
Clinical Findings and Symptom Drill-Down Engine (Interview Engine v3).

Converts patient free-text or structured answers into normalized, closed-vocabulary
findings with clinical attributes (onset, duration, severity, pattern, trigger, relief, associated).
Extracts attributes via deterministic regex/keyword rule tables (in English, Urdu script, and Roman Urdu),
maintains exact patient quotes, and manages follow-up probes (capped at max 2 follow-ups per finding).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Closed Vocabulary Finding Kinds
# =============================================================================
FINDING_KINDS: Set[str] = {
    "dizziness",
    "headache",
    "breathlessness",
    "chest_discomfort",
    "vision_change",
    "thirst_or_urination",
    "foot_problem",
    "low_sugar_episode",
    "missed_dose",
    "swelling",
    "tiredness",
    "nausea_or_vomiting",
    "pain_elsewhere",
    "sleep_disturbance",
    "low_mood",
    "other_symptom",
}


@dataclass
class FindingAttribute:
    name: str  # e.g., 'onset', 'duration', 'severity', 'pattern', 'trigger'
    value: Any  # e.g., 'since_yesterday', 8, 'standing', 'worse_than_usual'
    raw_quote: Optional[str] = None


@dataclass
class Finding:
    id: str
    kind: str  # Must be one of FINDING_KINDS
    label: str  # Human readable label
    raw_quote: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    probe_count: int = 0
    probed_slots: List[str] = field(default_factory=list)
    confidence: str = "High"
    source_step: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Multilingual Keyword Mappings to Finding Kinds
# =============================================================================
SYMPTOM_KEYWORD_RULES: List[Tuple[str, List[str]]] = [
    ("dizziness", [
        "dizzy", "dizziness", "lightheaded", "light-headed", "spinning", "room spinning",
        "chakkar", "sir ghoom", "sar ghoom", "sar ghum", "چکر", "سر گھوم"
    ]),
    ("headache", [
        "headache", "head ache", "head hurts", "throbbing head", "head pressure",
        "sar dard", "sar me dard", "sir dard", "sar mein dard", "سر درد", "سر میں درد"
    ]),
    ("breathlessness", [
        "shortness of breath", "short of breath", "breathless", "hard to breathe", "winded",
        "saans phool", "saans phoolna", "saans fool", "saans lene", "saans nahi aa rahi", "سانس پھول", "سانس میں دشواری"
    ]),
    ("chest_discomfort", [
        "chest discomfort", "chest aching", "chest soreness", "chest pain", "chest tightness",
        "seene me dard", "seene mein dard", "chhati me dard", "سینے میں درد", "سینے میں بوجھ"
    ]),
    ("vision_change", [
        "blurry vision", "blurred vision", "can't see clearly", "vision spots", "floaters",
        "dhundla", "dhundhli", "nazar kamzor", "aankhon ke aage andhera", "دھندلا", "نظر کی کمزوری"
    ]),
    ("thirst_or_urination", [
        "thirsty", "more thirsty", "dry mouth", "frequent urination", "peeing a lot", "passing urine often",
        "pyas ziada", "bar bar peshab", "peshab ziada", "پیاس زیادہ", "بار بار پیشاب"
    ]),
    ("foot_problem", [
        "foot pain", "sore on foot", "cut on foot", "blister on foot", "numb feet", "tingling feet",
        "paon me dard", "paon mein dard", "paon sunn", "paon par zakham", "پاؤں میں درد", "پاؤں سن", "پاؤں پر زخم"
    ]),
    ("low_sugar_episode", [
        "shaky", "shakiness", "cold sweat", "low sugar", "hypo", "sugar drop",
        "sugar low", "kapkapahat", "thanday paseenay", "شوگر لو", "کپکپاہٹ", "ٹھنڈے پسینے"
    ]),
    ("missed_dose", [
        "missed medicine", "forgot dose", "skipped pill", "ran out of medicine", "didn't take medicine",
        "dawa bhool", "dawa chhoot", "dawai nahi li", "دوا بھول", "دوا نہیں لی"
    ]),
    ("swelling", [
        "swelling", "swollen ankles", "swollen feet", "puffy legs", "fluid in legs",
        "sojan", "paon soojh", "takhno par sojan", "سوجن", "پاؤں پر سوجن"
    ]),
    ("tiredness", [
        "tired", "tiredness", "exhausted", "fatigue", "no energy", "weakness",
        "thakawat", "kamzori", "bejaan", "تھکاوٹ", "کمزوری"
    ]),
    ("nausea_or_vomiting", [
        "nausea", "nauseous", "vomiting", "throwing up", "threw up", "upset stomach",
        "ulti", "matli", "الٹی", "متلی"
    ]),
    ("sleep_disturbance", [
        "poor sleep", "can't sleep", "insomnia", "waking up at night", "sleep trouble",
        "neend nahi aati", "neend kharab", "نیند نہ آنا", "نیند خراب"
    ]),
    ("low_mood", [
        "feeling down", "depressed", "hopeless", "sad", "no motivation", "unhappy",
        "udas", "mayoos", "dil nahi lagta", "اداس", "مایوس", "دل اداس"
    ]),
]


# =============================================================================
# Attribute Extraction Rules (Data Tables)
# =============================================================================
SEVERITY_SCALE_REGEX = re.compile(r"\b([1-9]|10)\s*(?:out of\s*10|/10|/ 10|dass me se)\b", re.IGNORECASE)

SEVERITY_LEVEL_PATTERNS: List[Tuple[str, List[str]]] = [
    ("mild", [
        "mild", "slight", "a little", "just a bit", "just a little", "bas thora", "thora sa", "thora", "halka", "halka sa", "ہلکا", "تھوڑا"
    ]),
    ("moderate", [
        "moderate", "medium", "noticeable", "darmiyana", "theek thaak", "درمیانہ"
    ]),
    ("severe", [
        "severe", "terrible", "very bad", "extreme", "unbearable", "shadeed", "bohat ziada", "intehai", "شدید", "بہت زیادہ"
    ]),
]

ONSET_PATTERNS: List[Tuple[str, List[str]]] = [
    ("today", ["today", "aaj", "aaj se", "since morning", "subah se", "آج", "صبح سے"]),
    ("since_yesterday", ["since yesterday", "yesterday", "kal se", "kal raat se", "last night", "کل سے", "کل رات سے"]),
    ("few_days", ["few days", "for a few days", "2-3 days", "3 days", "chand dino se", "kuch dino se", "چند دنوں سے", "کچھ دنوں سے"]),
    ("over_a_week", ["for a week", "over a week", "weeks", "haftay se", "aik haftay se", "کئی ہفتوں سے", "ایک ہفتے سے"]),
    ("sudden", ["suddenly", "sudden", "all of a sudden", "achanak", "ek dam", "اچانک", "ایک دم"]),
    ("gradual", ["gradually", "slowly", "aahista aahista", "rafta rafta", "آہستہ آہستہ"]),
]

PATTERN_PATTERNS: List[Tuple[str, List[str]]] = [
    ("constant", ["constant", "all the time", "continuous", "har waqt", "muntazim", "ہر وقت", "مسلسل"]),
    ("intermittent", ["comes and goes", "intermittent", "sometimes", "aata jaata", "kabhi kabhi", "کبھی کبھی", "آتا جاتا"]),
    ("worse_than_usual", ["worse than usual", "getting worse", "ziada ho raha hai", "pehle se kharab", "زیادہ ہو رہا ہے", "پہلے سے خراب"]),
]

TRIGGER_PATTERNS: List[Tuple[str, List[str]]] = [
    ("standing_up", ["when standing", "standing up", "on standing", "stand up", "standing", "khare hone par", "uthne par", "کھڑے ہونے پر", "اٹھنے پر"]),
    ("after_eating", ["after eating", "after meal", "khanay ke baad", "کھانے کے بعد"]),
    ("exertion", ["walking", "stairs", "exertion", "running", "chaltay hue", "chalnay par", "chalne par", "seedhiyan", "چلتے ہوئے", "سیڑھیاں"]),
]


def _extract_attributes_from_text(text: str) -> Dict[str, Any]:
    """Extracts clinical attributes (severity, onset, pattern, trigger) deterministically."""
    attrs: Dict[str, Any] = {}
    lowered = text.lower()

    # 1. Numeric Severity 1-10
    match_num = SEVERITY_SCALE_REGEX.search(lowered)
    if match_num:
        attrs["severity_score"] = int(match_num.group(1))
        attrs["severity"] = "severe" if attrs["severity_score"] >= 8 else ("moderate" if attrs["severity_score"] >= 4 else "mild")
    else:
        for level, words in SEVERITY_LEVEL_PATTERNS:
            if any(w in lowered for w in words):
                attrs["severity"] = level
                if level == "mild":
                    attrs["is_minimiser"] = True
                break

    # 2. Onset
    for onset_val, words in ONSET_PATTERNS:
        if any(w in lowered for w in words):
            attrs["onset"] = onset_val
            break

    # 3. Pattern
    for pattern_val, words in PATTERN_PATTERNS:
        if any(w in lowered for w in words):
            attrs["pattern"] = pattern_val
            break

    # 4. Trigger
    for trig_val, words in TRIGGER_PATTERNS:
        if any(w in lowered for w in words):
            attrs["trigger"] = trig_val
            break

    return attrs


def extract_findings_from_answer(answer_text: str, step_id: str = "") -> List[Finding]:
    """
    Parses a patient's answer into zero or more normalized Finding objects with quotes and attributes.
    """
    if not answer_text or not answer_text.strip():
        return []

    clean_text = answer_text.strip()
    lowered = clean_text.lower()
    findings: List[Finding] = []
    extracted_kinds: Set[str] = set()

    for kind, patterns in SYMPTOM_KEYWORD_RULES:
        for pat in patterns:
            if pat in lowered and kind not in extracted_kinds:
                extracted_kinds.add(kind)
                attrs = _extract_attributes_from_text(clean_text)
                finding_id = f"fnd_{kind}_{len(findings) + 1}"
                findings.append(
                    Finding(
                        id=finding_id,
                        kind=kind,
                        label=kind.replace("_", " ").title(),
                        raw_quote=clean_text,
                        attributes=attrs,
                        probe_count=0,
                        probed_slots=[],
                        confidence="High",
                        source_step=step_id,
                    )
                )
                break

    return findings


def get_next_probe_for_finding(
    finding: Finding,
    probes_bank: Dict[str, List[Dict[str, Any]]],
    max_probes: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Returns the next follow-up question for a finding if under probe limit and unasked probes remain.
    """
    if finding.probe_count >= max_probes:
        return None

    kind_probes = probes_bank.get(finding.kind, probes_bank.get("other_symptom", []))
    for probe in kind_probes:
        slot = probe.get("slot")
        if slot and slot not in finding.probed_slots:
            return probe

    return None
