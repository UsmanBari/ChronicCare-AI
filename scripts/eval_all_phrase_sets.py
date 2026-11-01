"""
Evaluation Harness for Multilingual Clinical Danger Phrase Detection.
Compares v2, v3, and PROTOTYPE across gold, independent, and blind sets.
Includes PROTOTYPE function labeled PROTOTYPE (never imported by the app).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend-poc-technical"
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.adaptive_interview_agent import run_stage1_red_flag_screen
from agents.input_triage import classify_input


# ===========================================================================
# PROTOTYPE: Experimental Symptom Word-Group Danger Phrase Screen
# NOTE: This function is a PROTOTYPE for doctor review (DANGER_PHRASE_PLAN.md).
# It is strictly contained within this evaluation harness and is NEVER imported
# or executed by the runtime application or API endpoints.
# ===========================================================================

_PROTO_NEGATION_WORDS = {
    "no", "not", "none", "denies", "denied", "never", "without", "hardly", "barely",
    "nahi", "nahin", "na", "mat", "baghair", "bina", "koi nahi", "kuch nahi",
    "نہیں", "نہ", "مت", "بغیر", "کوئی نہیں",
}

_PROTO_PAST_CUES = {
    "yesterday", "last year", "months ago", "weeks ago", "days ago", "years ago",
    "in the past", "history of", "previously", "used to",
    "kal", "pichle", "pehle", "guzishta", "saal pehle", "mahine pehle",
    "پہلے", "گزشتہ", "سال پہلے", "کل",
}

_PROTO_CHEST_BODY = {
    "chest", "breastbone", "sternum", "ribs", "heart", "left arm",
    "seena", "seenay", "chhati", "dil",
    "سینہ", "سینے", "چھاتی", "دل",
}

_PROTO_CHEST_SEVERITY = {
    "pain", "severe", "crushing", "heavy", "pressure", "tightness", "squeezing",
    "burning", "ache", "stabbing", "radiating", "discomfort",
    "dard", "shadeed", "dabao", "jalan", "bojh", "sakht", "teez", "khichao",
    "درد", "شدید", "دباؤ", "جلن", "سخت", "بوجھ", "تیز",
}

_PROTO_STROKE_FAST = [
    # Face
    r"\b(?:face|mouth|chehra|munh|چہرہ|منہ)\s+(?:droop|crooked|numb|paralyz|terha|sunn|ٹھیڑھا|سن)\b",
    r"\b(?:munh|chehra)\s+(?:terha|sunn)\b",
    # Arm / Weakness
    r"\b(?:arm|hand|leg|bazu|haath|taang|بازو|ہاتھ|ٹانگ)\s+(?:weak|numb|paralyz|sunn|kamzor|kamzori|کمزور|سن)\b",
    r"\b(?:one\s+side|aik\s+taraf|ایک\s+طرف)\s+(?:weak|numb|paralyz|falij|kamzor|فالج|کمزور)\b",
    # Speech
    r"\b(?:slurr|cant\s+speak|unable\s+to\s+speak|speech|awaz|bol\s+nahi|بول\s+نہیں|آواز)\s+(?:speech|lost|ladkhada|band)\b",
    r"\b(?:bol\s+nahi\s+pa\s+raha|awaz\s+ladkhada|zuban\s+ladkhada)\b",
    r"زبان لڑکھڑا|بول نہیں پا رہا|آواز بند",
]

_PROTO_BREATHING_CRISIS = [
    r"\b(?:cant|cannot|unable\s+to|struggling\s+to)\s+breathe\b",
    r"\b(?:severe|gasping|suffocating)\s+(?:shortness\s+of\s+breath|breath|dyspnea)\b",
    r"\b(?:saans\s+nahi|dum\s+ghut|saans\s+rook|sans\s+ruk)\b",
    r"سانس نہیں آرہی|دم گھٹ رہا|سانس رک",
]

_PROTO_FAINT_UNRESPONSIVE = [
    r"\b(?:unconscious|passed\s+out|fainted|blackout|collapsed|unresponsive)\b",
    r"\b(?:behosh|gash|chakkar\s+kha\s+kar\s+gir)\b",
    r"بے ہوش|غش|چکر کھا کر گر",
]

_PROTO_VOMITING_BLOOD = [
    r"\b(?:vomit|throwing\s+up|puke|emesis)\s+(?:blood|coffee\s+ground)\b",
    r"\b(?:vomiting\s+blood|blood\s+in\s+vomit)\b",
    r"\b(?:khoon\s+ki\s+ulti|ulti\s+mein\s+khoon)\b",
    r"خون کی الٹی|الٹی میں خون",
    r"\b(?:black\s+tarry\s+stool|melena|kala\s+pakhana|کالا\s+پاخانہ)\b",
]


def PROTOTYPE_screen_danger_phrase(text: str) -> Tuple[bool, Optional[str]]:
    """
    PROTOTYPE danger phrase classifier based on composable symptom word-groups,
    negation windows, and clinical red flag rules.
    """
    if not text or not isinstance(text, str):
        return False, None

    clean = text.strip()
    lowered = clean.lower()
    tokens = re.findall(r"[\w']+|[^\s\w]", lowered)

    # 1. Negation window check helper
    def is_negated_window(start_pos: int, window: int = 4) -> bool:
        preceding = lowered[:start_pos].split()
        return any(w in _PROTO_NEGATION_WORDS for w in preceding[-window:])

    # 2. Check Stroke FAST cues
    for pat in _PROTO_STROKE_FAST:
        m = re.search(pat, lowered)
        if m and not is_negated_window(m.start()):
            return True, "stroke_fast_cue"

    # 3. Check Breathing crisis
    for pat in _PROTO_BREATHING_CRISIS:
        m = re.search(pat, lowered)
        if m and not is_negated_window(m.start()):
            return True, "breathing_distress"

    # 4. Check Unresponsiveness / Fainting
    for pat in _PROTO_FAINT_UNRESPONSIVE:
        m = re.search(pat, lowered)
        if m and not is_negated_window(m.start()):
            return True, "unresponsive_faint"

    # 5. Check Vomiting Blood / GI Bleed
    for pat in _PROTO_VOMITING_BLOOD:
        m = re.search(pat, lowered)
        if m and not is_negated_window(m.start()):
            return True, "vomiting_blood"

    # 6. Composable Chest Pain Group (Body + Severity/Sensation)
    has_chest_body = any(b in lowered for b in _PROTO_CHEST_BODY)
    has_chest_sev = any(s in lowered for s in _PROTO_CHEST_SEVERITY)
    if has_chest_body and has_chest_sev:
        # Check if chest or severity word is negated
        m_body = re.search(r"\b(?:" + "|".join(_PROTO_CHEST_BODY) + r")\b", lowered)
        m_sev = re.search(r"\b(?:" + "|".join(_PROTO_CHEST_SEVERITY) + r")\b", lowered)
        pos = min(m_body.start() if m_body else 999, m_sev.start() if m_sev else 999)
        if pos < 999 and not is_negated_window(pos):
            return True, "cardiac_chest_pain"

    return False, None


# ===========================================================================
# Evaluation Harness
# ===========================================================================

PHRASE_FILES = [
    {
        "name": "Gold Standard Danger",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_gold.json",
        "format": "gold_list",
    },
    {
        "name": "Saad Independent",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_saad.json",
        "format": "gold_list",
    },
    {
        "name": "Hassaan Urdu Independent",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_hassaan_ur.json",
        "format": "gold_list",
    },
    {
        "name": "Hassaan Benign Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "benign_urdu_sentences_hassaan.json",
        "format": "benign_list",
    },
    {
        "name": "Saad Blind Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "blind_urdu_saad.json",
        "format": "blind_list",
    },
    {
        "name": "Tuning Set Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "tuning_set_urdu.json",
        "format": "blind_list",
    },
    {
        "name": "Dr Anam Clinical Review Set",
        "path": REPO_ROOT / "tests" / "sim" / "dr_anam_clinical_set.json",
        "format": "gold_list",
    },
]


def load_dataset(file_info: Dict[str, Any]) -> Optional[List[Tuple[str, bool]]]:
    path: Path = file_info["path"]
    if not path.is_file():
        return None

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    samples: List[Tuple[str, bool]] = []
    fmt = file_info["format"]

    if fmt in ("gold_list", "blind_list"):
        for item in raw:
            text = item.get("text", "")
            exp = bool(item.get("expected_danger", False))
            samples.append((text, exp))
    elif fmt == "benign_list":
        for item in raw:
            text = str(item)
            samples.append((text, False))

    return samples


def eval_engine(engine_name: str, samples: List[Tuple[str, bool]]) -> Tuple[int, int, int, int]:
    """
    Evaluates engine across samples.
    Returns: (danger_caught, danger_total, false_alarms, safe_total)
    """
    danger_caught = 0
    danger_total = 0
    false_alarms = 0
    safe_total = 0

    for text, expected in samples:
        if expected:
            danger_total += 1
        else:
            safe_total += 1

        if engine_name == "v2":
            is_d, _ = run_stage1_red_flag_screen(text)
            caught = bool(is_d)
        elif engine_name == "v3":
            res = classify_input(text)
            caught = bool(res.category == "danger_phrase" or res.is_emergency or res.is_urgent_safety)
        elif engine_name == "PROTOTYPE":
            is_d, _ = PROTOTYPE_screen_danger_phrase(text)
            caught = bool(is_d)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

        if expected and caught:
            danger_caught += 1
        elif not expected and caught:
            false_alarms += 1

    return danger_caught, danger_total, false_alarms, safe_total


def main():
    print("=" * 95)
    print("MULTILINGUAL DANGER PHRASE BENCHMARK & PROTOTYPE EVALUATION")
    print("=" * 95)
    print(f"{'Dataset':<30} | {'Engine':<10} | {'Danger Caught / Total':<23} | {'False Alarms / Safe':<20}")
    print("-" * 95)

    results_for_report = []

    for file_info in PHRASE_FILES:
        name = file_info["name"]
        samples = load_dataset(file_info)

        if samples is None:
            print(f"{name:<30} | {'ALL':<10} | {'NOT PRESENT':<23} | {'NOT PRESENT':<20}")
            results_for_report.append({"name": name, "status": "NOT PRESENT"})
            continue

        for eng in ("v2", "v3", "PROTOTYPE"):
            caught, d_tot, fa, s_tot = eval_engine(eng, samples)
            d_str = f"{caught} / {d_tot} ({caught/d_tot*100:.1f}%)" if d_tot > 0 else "0 / 0 (N/A)"
            fa_str = f"{fa} / {s_tot} ({fa/s_tot*100:.1f}%)" if s_tot > 0 else f"{fa} / 0 (N/A)"
            print(f"{name:<30} | {eng:<10} | {d_str:<23} | {fa_str:<20}")
            results_for_report.append({
                "name": name,
                "engine": eng,
                "caught": caught,
                "d_tot": d_tot,
                "fa": fa,
                "s_tot": s_tot,
            })
        print("-" * 95)

    print("=" * 95)
    return results_for_report


if __name__ == "__main__":
    main()
