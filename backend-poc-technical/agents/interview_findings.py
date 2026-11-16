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
        r"\bdizzy\b", r"\bdizziness\b", r"\blightheaded\b", r"\blight-headed\b", r"\bspinning\b", r"\broom\s+spinning\b",
        r"\bchakkar\b", r"\b(?:sir|sar)\s+ghoom\w*\b", r"\b(?:sir|sar)\s+ghum\w*\b", r"چکر", r"سر\s+گھوم"
    ]),
    ("headache", [
        r"\bheadache\b", r"\bhead\s*ache\b", r"\bhead\s+hurts?\b", r"\bthrobbing\s+head\b", r"\bhead\s+pressure\b",
        r"\bpain\s+in\s+(?:my\s+)?head\b",
        r"\b(?:sar|sir)\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"\b(?:sar|sir)\s+dard\b", r"\b(?:sar|sir)\s+dukh\w*\b", r"\b(?:sar|sir)\s+phat\w*\b",
        r"سر\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد", r"سر\s+درد", r"سر\s+دکھ"
    ]),
    ("breathlessness", [
        r"\bshortness\s+of\s+breath\b", r"\bshort\s+of\s+breath\b", r"\bbreathless\w*\b", r"\bhard\s+to\s+breathe\b", r"\bwinded\b",
        r"\btrouble\s+breathing\b", r"\bdifficulty\s+breathing\b",
        r"\bsaans\s+phool\w*\b", r"\bsaans\s+fool\w*\b", r"\bsaans\s+lene\s+mein\s+[^,.;!?\n]{0,30}(?:takleef|mushkil|dushwari)\b",
        r"\bsaans\s+nahi\s+aa\s+rahi\b", r"\bdum\s+ghut\w*\b",
        r"سانس\s+پھول", r"سانس\s+(?:لینے\s+)?میں\s+[^,.;!?\n]{0,30}(?:دشواری|تکلیف|مشکل)", r"دم\s+گھٹ"
    ]),
    ("chest_discomfort", [
        r"\bchest\s+discomfort\b", r"\bchest\s+aching\b", r"\bchest\s+soreness\b", r"\bchest\s+pain\b", r"\bchest\s+tightness\b",
        r"\bpressure\s+in\s+(?:my\s+)?chest\b",
        r"\bseen[ae]\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}(?:dard|bojh|dabao|jalan|takleef)\b",
        r"\bchhati\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"سینے\s+(?:میں\s+)?[^,.;!?\n]{0,30}(?:درد|بوجھ|دباؤ|جلن|تکلیف)", r"چھاتی\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد"
    ]),
    ("vision_change", [
        r"\bblurry\s+vision\b", r"\bblurred\s+vision\b", r"\bcan'?t\s+see\s+clearly\b", r"\bvision\s+spots\b", r"\bfloaters\b",
        r"\btrouble\s+seeing\b",
        r"\bdhundla\b", r"\bdhundhli\b", r"\bnazar\s+kamzor\b", r"\baankhon\s+ke\s+aage\s+andhera\b",
        r"دھندلا", r"نظر\s+کی\s+کمزوری", r"آنکھوں\s+کے\s+آگے\s+اندھیرا"
    ]),
    ("thirst_or_urination", [
        r"\bthirsty\b", r"\bmore\s+thirsty\b", r"\bdry\s+mouth\b", r"\bfrequent\s+urination\b", r"\bpeeing\s+a\s+lot\b", r"\bpassing\s+urine\s+often\b",
        r"\bpyas\s+ziada\b", r"\bziada\s+pyas\b", r"\bbar\s+bar\s+peshab\b", r"\bpeshab\s+ziada\b",
        r"پیاس\s+زیادہ", r"زیادہ\s+پیاس", r"بار\s+بار\s+پیشاب", r"پیشاب\s+زیادہ"
    ]),
    ("foot_problem", [
        r"\bfoot\s+pain\b", r"\bsore\s+on\s+foot\b", r"\bcut\s+on\s+foot\b", r"\bblister\s+on\s+foot\b", r"\bnumb\s+feet\b", r"\btingling\s+feet\b",
        r"\bfoot\s+numbness\b",
        r"\bpaon\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}(?:dard|sojan|jalan|zakham|takleef)\b", r"\bpaon\s+sunn\b", r"\bpaon\s+par\s+zakham\b",
        r"پاؤں\s+(?:میں\s+)?[^,.;!?\n]{0,30}(?:درد|سوجن|جلن|زخم|تکلیف)", r"پاؤں\s+سن", r"پاؤں\s+پر\s+زخم"
    ]),
    ("low_sugar_episode", [
        r"\bshaky\b", r"\bshakiness\b", r"\bcold\s+sweat\b", r"\blow\s+sugar\b", r"\bhypo\b", r"\bsugar\s+drop\b",
        r"\bsugar\s+low\b", r"\bkapkapahat\b", r"\bthanday\s+paseenay\b",
        r"شوگر\s+لو", r"کپکپاہٹ", r"ٹھنڈے\s+پسینے"
    ]),
    ("missed_dose", [
        r"\bmissed\s+(?:my\s+)?(?:medicine|meds|dose|pill)\b", r"\bforgot\s+(?:my\s+)?(?:dose|medicine|meds|pill)\b",
        r"\bskipped\s+(?:my\s+)?pill\b", r"\bran\s+out\s+of\s+medicine\b", r"\bdidn'?t\s+take\s+medicine\b",
        r"\bdawa\s+bhool\b", r"\bdawa\s+chhoot\b", r"\bdawai\s+nahi\s+li\b",
        r"دوا\s+بھول", r"دوا\s+نہیں\s+لی"
    ]),
    ("swelling", [
        r"\bswelling\b", r"\bswollen\s+(?:ankles|feet|legs)\b", r"\bpuffy\s+legs\b", r"\bfluid\s+in\s+legs\b",
        r"\bsojan\b", r"\bpaon\s+soojh\b", r"\btakhno\s+par\s+sojan\b",
        r"سوجن", r"پاؤں\s+پر\s+سوجن"
    ]),
    ("tiredness", [
        r"\btired\b", r"\btiredness\b", r"\bexhausted\b", r"\bfatigue\b", r"\bno\s+energy\b", r"\bweakness\b",
        r"\bthakawat\b", r"\bkamzori\b", r"\bbejaan\b",
        r"تھکاوٹ", r"کمزوری"
    ]),
    ("nausea_or_vomiting", [
        r"\bnausea\b", r"\bnauseous\b", r"\bvomiting\b", r"\bthrowing\s+up\b", r"\bthrew\s+up\b", r"\bupset\s+stomach\b",
        r"\bulti\b", r"\bmatli\b",
        r"الٹی", r"متلی"
    ]),
    ("sleep_disturbance", [
        r"\bpoor\s+sleep\b", r"\bcan'?t\s+sleep\b", r"\binsomnia\b", r"\bwaking\s+up\s+at\s+night\b", r"\bsleep\s+trouble\b",
        r"\bneend\s+nahi\s+aati\b", r"\bneend\s+kharab\b",
        r"نیند\s+نہ\s+آنا", r"نیند\s+خراب"
    ]),
    ("low_mood", [
        r"\bfeeling\s+down\b", r"\bdepressed\b", r"\bhopeless\b", r"\bsad\b", r"\bno\s+motivation\b", r"\bunhappy\b",
        r"\budas\b", r"\bmayoos\b", r"\bdil\s+nahi\s+lagta\b",
        r"اداس", r"مایوس", r"دل\s+اداس"
    ]),
    ("pain_elsewhere", [
        r"\bback\s+pain\b", r"\bbody\s+ache\b", r"\bjoint\s+pain\b", r"\bmuscle\s+ache\b", r"\bpain\s+in\s+(?:my\s+)?(?:back|joints|legs|arms|body)\b",
        r"\bkamar\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"\bjism\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"\bjoron\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"\bpait\s+(?:mein\s+|me\s+)?[^,.;!?\n]{0,30}dard\b",
        r"کمر\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد", r"جسم\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد",
        r"جوڑوں\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد", r"پیٹ\s+(?:میں\s+)?[^,.;!?\n]{0,30}درد"
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
    ("gradual", ["gradually", "gradual", "slowly", "aahista aahista", "rafta rafta", "آہستہ آہستہ"]),
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


def _is_finding_match_negated(text: str, start: int, end: int) -> bool:
    """Checks whether a matched symptom keyword is negated in the immediate clause."""
    pre = text[max(0, start - 30):start].lower()
    post = text[end:min(len(text), end + 30)].lower()

    # Isolate the clause before and after the match (stop at clause boundaries)
    pre_clause = re.split(r'[,;]|\b(?:but|magar|lekin|lekan|per|par)\b', pre)[-1]
    post_clause = re.split(r'[,;]|\b(?:but|magar|lekin|lekan|per|par)\b', post)[0]

    # Preceding negation: 'no headache', 'without headache', 'don't have headache', 'koi sar dard nahi'
    if re.search(r'\b(?:no|without|never|deny|denies|not|dont|doesn\'t|don\'t|didnt|didn\'t)\b', pre_clause):
        return True
    if re.search(r'\b(?:nahi|nahin|na)\b', pre_clause):
        return True
    if re.search(r'نہیں', pre_clause):
        return True

    # Trailing negation: 'sar dard nahi hai', 'headache was absent/none'
    if re.search(r'\b(?:nahi|nahin|na)\b', post_clause):
        return True
    if re.search(r'نہیں', post_clause):
        return True
    if re.search(r'\b(?:absent|none|not present)\b', post_clause):
        return True

    return False


def format_finding_label(finding: Finding | Dict[str, Any], lang: str = "en") -> str:
    """
    Formats a Finding into a human-readable clinical summary string,
    e.g. 'Headache (mild, gradual)' or 'سر درد (ہلکا، آہستہ آہستہ)'.
    """
    if isinstance(finding, dict):
        kind = finding.get("kind", "")
        attrs = finding.get("attributes", {}) or {}
        label = finding.get("label") or kind.replace("_", " ").title()
    else:
        kind = finding.kind
        attrs = finding.attributes or {}
        label = finding.label or kind.replace("_", " ").title()

    FINDING_LABELS: Dict[str, Dict[str, str]] = {
        "headache": {"en": "Headache", "ur": "سر درد", "roman_ur": "Sar dard"},
        "dizziness": {"en": "Dizziness", "ur": "چکر", "roman_ur": "Chakkar"},
        "breathlessness": {"en": "Shortness of breath", "ur": "سانس کی تکلیف", "roman_ur": "Saans ki takleef"},
        "chest_discomfort": {"en": "Chest discomfort", "ur": "سینے میں تکلیف", "roman_ur": "Seene mein takleef"},
        "vision_change": {"en": "Vision change", "ur": "نظر میں تبدیلی", "roman_ur": "Nazar mein tabdeeli"},
        "thirst_or_urination": {"en": "Excessive thirst/urination", "ur": "زیادہ پیاس/پیشاب", "roman_ur": "Ziada pyas ya peshab"},
        "foot_problem": {"en": "Foot problem", "ur": "پاؤں کا مسئلہ", "roman_ur": "Paon ka masla"},
        "low_sugar_episode": {"en": "Low sugar symptoms", "ur": "شوگر کم ہونے کی علامات", "roman_ur": "Low sugar ki alamaat"},
        "missed_dose": {"en": "Missed medication", "ur": "دوا چھوٹ جانا", "roman_ur": "Dawai chhootna"},
        "swelling": {"en": "Swelling", "ur": "سوجن", "roman_ur": "Sojan"},
        "tiredness": {"en": "Tiredness/Weakness", "ur": "تھکاوٹ/کمزوری", "roman_ur": "Thakawat ya kamzori"},
        "nausea_or_vomiting": {"en": "Nausea/Vomiting", "ur": "متلی/الٹی", "roman_ur": "Matli ya ulti"},
        "sleep_disturbance": {"en": "Sleep trouble", "ur": "نیند کا مسئلہ", "roman_ur": "Neend ka masla"},
        "low_mood": {"en": "Low mood", "ur": "اداس کیفیت", "roman_ur": "Udaasi"},
        "pain_elsewhere": {"en": "Body ache/Pain", "ur": "جسمانی درد", "roman_ur": "Jism mein dard"},
        "other_symptom": {"en": "Other symptom", "ur": "دیگر علامات", "roman_ur": "Deegar alamaat"},
    }

    ATTR_LABELS: Dict[str, Dict[str, str]] = {
        "mild": {"en": "mild", "ur": "ہلکا", "roman_ur": "mild"},
        "moderate": {"en": "moderate", "ur": "درمیانہ", "roman_ur": "moderate"},
        "severe": {"en": "severe", "ur": "شدید", "roman_ur": "severe"},
        "gradual": {"en": "gradual", "ur": "آہستہ آہستہ", "roman_ur": "gradual"},
        "sudden": {"en": "sudden", "ur": "اچانک", "roman_ur": "sudden"},
        "today": {"en": "since morning", "ur": "صبح سے", "roman_ur": "since morning"},
        "since_yesterday": {"en": "since yesterday", "ur": "کل سے", "roman_ur": "since yesterday"},
        "constant": {"en": "constant", "ur": "مسلسل", "roman_ur": "constant"},
        "intermittent": {"en": "intermittent", "ur": "کبھی کبھی", "roman_ur": "intermittent"},
    }

    name = FINDING_LABELS.get(kind, {}).get(lang) or FINDING_LABELS.get(kind, {}).get("en") or label

    parts = []
    sev = attrs.get("severity")
    if sev and sev in ATTR_LABELS:
        parts.append(ATTR_LABELS[sev].get(lang) or ATTR_LABELS[sev]["en"])

    onset = attrs.get("onset")
    pattern = attrs.get("pattern")
    second_attr = onset or pattern
    if second_attr and second_attr in ATTR_LABELS:
        parts.append(ATTR_LABELS[second_attr].get(lang) or ATTR_LABELS[second_attr]["en"])

    if parts:
        return f"{name} ({', '.join(parts)})"
    return name


def extract_findings_from_answer(answer_text: str, step_id: str = "") -> List[Finding]:
    """
    Parses a patient's answer into zero or more normalized Finding objects with quotes and attributes.
    """
    if not answer_text or not answer_text.strip():
        return []

    clean_text = answer_text.strip()
    findings: List[Finding] = []
    extracted_kinds: Set[str] = set()

    for kind, patterns in SYMPTOM_KEYWORD_RULES:
        for pat in patterns:
            if kind in extracted_kinds:
                break
            m = re.search(pat, clean_text, re.IGNORECASE)
            if m:
                if not _is_finding_match_negated(clean_text, m.start(), m.end()):
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
