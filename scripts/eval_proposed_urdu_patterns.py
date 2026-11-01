#!/usr/bin/env python3
"""
scripts/eval_proposed_urdu_patterns.py

Standalone evaluation harness for proposed Urdu danger patterns (PR #89 / Correction 3).
Evaluates:
  1. Legacy v2 Engine (run_stage1_red_flag_screen)
  2. Current v3 Engine (classify_input)
  3. Proposed v3+ Engine (clinically broadened patterns, 1 tuning round)

Against:
  - Primary Independent Set (Hassaan): 20 Danger Phrases + 10 Safe Look-alikes
  - Held-out Set (Saad): 20 New Danger Phrases + 20 New Safe Sentences
  - Benign Conversational Set (Hassaan): 40 Everyday Urdu Patient Sentences

DOES NOT MODIFY input_triage.py or any protected engine files.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents.adaptive_interview_agent import (
    _EASTERN_DIGITS_TABLE,
    run_stage1_red_flag_screen,
)
from agents.input_triage import classify_input

PRIMARY_PHRASES_PATH = REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_hassaan_ur.json"
TUNING_SET_PATH = REPO_ROOT / "tests" / "sim" / "tuning_set_urdu.json"
BLIND_SAAD_PATH = REPO_ROOT / "tests" / "sim" / "blind_urdu_saad.json"
BENIGN_SENTENCES_PATH = REPO_ROOT / "tests" / "sim" / "benign_urdu_sentences_hassaan.json"


# =============================================================================
# Proposed Clinical Patterns (Round 1: Broader but Safe)
# =============================================================================

PROPOSED_REGEX_PATTERNS = [
    # 1. Chest pain radiating to arm / neck / shoulder or severe constriction
    (
        re.compile(r"(?:چھاتی|سینے).*(?:دباؤ|بوجھ|درد|چبھن|سخت گھٹن).*(?:بائیں|بازو|گردن|کندھ)"),
        "chest_pain",
        "emergency",
    ),
    (re.compile(r"(?:سینے|چھاتی).*(?:شدید گھٹن|سخت گھٹن|دم گھٹ)"), "chest_pain", "emergency"),
    # 2. Severe respiratory compromise / orthopnea / pulmonary foam
    (
        re.compile(
            r"سانس.*(?:پھول|تکلیف|رکنے لگا|رک رہا).*(?:بیٹھا بھی نہیں جا رہا|چلنا محال|لیٹنے پر دم گھٹ|جھاگ)"
        ),
        "breathing",
        "emergency",
    ),
    # 3. Syncope: recurrent blackouts / fainting / collapsing (tightened from bare 'اندھیرا')
    (
        re.compile(
            r"غشی(?: کے دورے)?|(?:آنکھوں کے آگے اندھیرا.*(?:دورے|غشی|بے ہوش|گر پڑ|چھا گیا))|(?:بے سدھ ہو کر گر)"
        ),
        "syncope",
        "emergency",
    ),
    # 4. Stroke / Focal weakness / Facial droop / Dysphasia
    (
        re.compile(r"(?:آدھا جسم|ایک طرف|بائیں ہاتھ|دائیں ہاتھ).*(?:سن|کمزور|جان نہیں|ہلایا نہیں جا رہا)"),
        "focal_weakness_stroke",
        "emergency",
    ),
    (
        re.compile(r"(?:ایک طرف کا (?:ہاتھ|بازو|پاؤں|ٹانگ).*(?:کمزور|سن|جان نہیں))|(?:ہاتھ اور پاؤں.*جان نہیں رہی)"),
        "focal_weakness_stroke",
        "emergency",
    ),
    (
        re.compile(
            r"(?:منہ.*(?:ٹیڑھا|ڈھلک|لٹک))|(?:چہرہ|چہرے).*(?:ٹیڑھا|ڈھلک|لٹک)|(?:بولنے میں مشکل.*ایک طرف)|(?:منہ.*ٹیڑھا.*بولا نہیں جا رہا)|(?:پانی پیتے ہوئے منہ سے نکل)"
        ),
        "focal_weakness_stroke",
        "emergency",
    ),
    # 5. Acute confusion / encephalopathy / disorientation
    (
        re.compile(r"حواس کام نہیں کر رہے|باتیں بہکی|نہیں پتہ.*کہاں"),
        "confusion",
        "emergency",
    ),
    # 6. Severe headache (thunderclap / worst of life / uncontrollable pain)
    (
        re.compile(
            r"سر.*(?:بجلی کا جھٹکا|شدید ترین درد|بدترین|پہلے کبھی نہیں ہوا|چبھن.*شدید ترین|(?:درد.*(?:اتنا شدید.*(?:الٹی|برداشت سے باہر))))"
        ),
        "severe_headache",
        "emergency",
    ),
    # 7. Sudden monocular or severe acute vision loss
    (
        re.compile(r"(?:اچانک.*(?:ایک آنکھ|دائیں آنکھ|بائیں آنکھ|دونوں آنکھوں)?.*(?:نظر آنا بند|کالی پٹی))"),
        "vision_loss",
        "emergency",
    ),
    # 8. Active gastrointestinal hemorrhage (hematemesis / melena)
    (re.compile(r"خون کی الٹی|قے.*خون|الٹی میں.*خون|پاخانے کا رنگ کالا سیاہ"), "bleeding", "emergency"),
    # 9. Violent tachyarrhythmia / palpitations with autonomic distress
    (
        re.compile(r"(?:دھڑکن|دل).*بے قابو.*(?:پسینے|سینے)|دل بہت تیز دھڑک.*سینے سے باہر"),
        "palpitations_danger",
        "emergency",
    ),
]


def eval_numeric_hypoglycemia(text: str) -> tuple[str, str] | None:
    """
    Evaluates objective numeric hypoglycemia with autonomic/neuroglycopenic symptoms.
    Normalizes Eastern Arabic digits (۰-۹ -> 0-9).
    Requires integer extraction with whole-number word boundaries.
    Only triggers if standalone glucose value < 54 mg/dL.
    Protects against numbers like 135 matching 35.
    """
    normalized = text.translate(_EASTERN_DIGITS_TABLE)

    # Check explicit '< 40' or '< 50' or '< 54' phrasing
    if re.search(r"شوگر.*(?:40|50|54)\s*سے کم", normalized):
        return ("severe_hypoglycemia", "emergency")

    # Autonomic / neuroglycopenic symptoms: tremors, sweats, presyncope, dizziness, confusion
    has_hypo_symptom = bool(
        re.search(r"(?:ہاتھ کانپ|پسینہ|کپکپی|لرز|چکر|بے ہوش|غشی|الجھن|بے چینی|کمزوری)", normalized)
    )
    if not has_hypo_symptom:
        return None

    # Check standalone integer tokens if 'شوگر' or 'گلوکومیٹر' is present
    if "شوگر" in normalized or "گلوکومیٹر" in normalized:
        numbers = [int(n) for n in re.findall(r"\b\d{1,3}\b", normalized)]
        for n in numbers:
            if n < 54:
                return ("severe_hypoglycemia", "emergency")

    return None


def screen_proposed_v3_plus(text: str) -> tuple[bool, str | None, str | None]:
    """
    Evaluates current v3 classify_input plus the broadened proposed patterns.
    Returns (is_danger, category, triage_level).
    """
    # 1. First run current v3 triage
    v3_res = classify_input(text)
    if v3_res.category == "danger_phrase":
        level = "emergency" if v3_res.is_emergency else "urgent"
        return True, v3_res.trigger_detail, level

    # 2. Check numeric hypoglycemia rule
    hypo = eval_numeric_hypoglycemia(text)
    if hypo:
        return True, hypo[0], hypo[1]

    # 3. Check proposed regex patterns
    for pat, cat, lvl in PROPOSED_REGEX_PATTERNS:
        if pat.search(text):
            return True, cat, lvl

    return False, None, None


# =============================================================================
# Benchmark Evaluation Logic
# =============================================================================

def evaluate_dataset(dataset_path: Path) -> dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dangers = [d for d in data if d.get("expected_danger")]
    safes = [d for d in data if not d.get("expected_danger")]

    res = {
        "v2": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "misses": [], "alarms": []},
        "v3": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "misses": [], "alarms": []},
        "proposed": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "misses": [], "alarms": []},
    }

    for item in dangers:
        phrase = item["text"]
        # v2
        rf_v2, _ = run_stage1_red_flag_screen(phrase)
        if rf_v2:
            res["v2"]["tp"] += 1
        else:
            res["v2"]["fn"] += 1
            res["v2"]["misses"].append(phrase)

        # v3
        triage_v3 = classify_input(phrase)
        if triage_v3.category == "danger_phrase":
            res["v3"]["tp"] += 1
        else:
            res["v3"]["fn"] += 1
            res["v3"]["misses"].append(phrase)

        # Proposed
        prop_is, _, _ = screen_proposed_v3_plus(phrase)
        if prop_is:
            res["proposed"]["tp"] += 1
        else:
            res["proposed"]["fn"] += 1
            res["proposed"]["misses"].append(phrase)

    for item in safes:
        phrase = item["text"]
        # v2
        rf_v2, _ = run_stage1_red_flag_screen(phrase)
        if rf_v2:
            res["v2"]["fp"] += 1
            res["v2"]["alarms"].append(phrase)
        else:
            res["v2"]["tn"] += 1

        # v3
        triage_v3 = classify_input(phrase)
        if triage_v3.category == "danger_phrase":
            res["v3"]["fp"] += 1
            res["v3"]["alarms"].append(phrase)
        else:
            res["v3"]["tn"] += 1

        # Proposed
        prop_is, _, _ = screen_proposed_v3_plus(phrase)
        if prop_is:
            res["proposed"]["fp"] += 1
            res["proposed"]["alarms"].append(phrase)
        else:
            res["proposed"]["tn"] += 1

    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    primary_res = evaluate_dataset(PRIMARY_PHRASES_PATH)
    tuning_res = evaluate_dataset(TUNING_SET_PATH)
    blind_res = evaluate_dataset(BLIND_SAAD_PATH) if BLIND_SAAD_PATH.exists() else None

    with open(BENIGN_SENTENCES_PATH, "r", encoding="utf-8") as f:
        benign_sentences = json.load(f)

    benign_counts = {"v2_fp": 0, "v3_fp": 0, "prop_fp": 0}
    for b in benign_sentences:
        if run_stage1_red_flag_screen(b)[0]:
            benign_counts["v2_fp"] += 1
        if classify_input(b).category == "danger_phrase":
            benign_counts["v3_fp"] += 1
        if screen_proposed_v3_plus(b)[0]:
            benign_counts["prop_fp"] += 1

    print("=" * 80)
    print("CHRONICCARE-AI: MEASURED URDU DANGER PHRASE EVALUATION (CORRECTION 4)")
    print("=" * 80)

    print("\n### 1. Primary Set (Hassaan: 20 Danger + 10 Safe Look-alikes)")
    print("| Engine | Sensitivity (TP/20) | Safe Specificity (TN/10) | False Alarms |")
    print("|---|---|---|---|")
    for name, r in [
        ("Legacy v2 (`run_stage1_red_flag_screen`)", primary_res["v2"]),
        ("Current v3 (`classify_input`)", primary_res["v3"]),
        ("Proposed v3+ (Broadened Round 1)", primary_res["proposed"]),
    ]:
        sens = (r["tp"] / 20) * 100
        spec = (r["tn"] / 10) * 100
        print(f"| {name} | {sens:.1f}% ({r['tp']}/20) | {spec:.1f}% ({r['tn']}/10) | {r['fp']} |")

    print("\n### 2. Tuning Set (patterns adjusted once on it: 20 Danger + 20 Safe)")
    print("| Engine | Sensitivity (TP/20) | Safe Specificity (TN/20) | False Alarms |")
    print("|---|---|---|---|")
    for name, r in [
        ("Legacy v2 (`run_stage1_red_flag_screen`)", tuning_res["v2"]),
        ("Current v3 (`classify_input`)", tuning_res["v3"]),
        ("Proposed v3+ (Broadened Round 1)", tuning_res["proposed"]),
    ]:
        sens = (r["tp"] / 20) * 100
        spec = (r["tn"] / 20) * 100
        print(f"| {name} | {sens:.1f}% ({r['tp']}/20) | {spec:.1f}% ({r['tn']}/20) | {r['fp']} |")

    total_safe = 10 + 20 + 40  # 70 total safe sentences
    print("\n### 3. Combined Safe Specificity across All 70 Safe Sentences (10 Hassaan + 20 Saad + 40 Benign)")
    for name, r_prim, r_held, b_fp in [
        ("Legacy v2", primary_res["v2"], tuning_res["v2"], benign_counts["v2_fp"]),
        ("Current v3", primary_res["v3"], tuning_res["v3"], benign_counts["v3_fp"]),
        ("Proposed v3+", primary_res["proposed"], tuning_res["proposed"], benign_counts["prop_fp"]),
    ]:
        total_tn = r_prim["tn"] + r_held["tn"] + (40 - b_fp)
        total_fp = r_prim["fp"] + r_held["fp"] + b_fp
        spec = (total_tn / total_safe) * 100
        print(f"  {name:15}: Specificity = {spec:.1f}% ({total_tn}/{total_safe}) [Total False Positives: {total_fp}]")

    
    if blind_res:
        print("\n### 4. Blind Saad Set (Round 0 Un-tuned: 20 Danger + 20 Safe Look-alikes)")
        print("| Engine | Sensitivity (TP/20) | Safe Specificity (TN/20) | False Alarms |")
        print("|---|---|---|---|")
        for name, r in [
            ("Legacy v2 (`run_stage1_red_flag_screen`)", blind_res["v2"]),
            ("Current v3 (`classify_input`)", blind_res["v3"]),
            ("Proposed v3+ (Round 0 Un-tuned)", blind_res["proposed"]),
        ]:
            sens = (r["tp"] / 20) * 100
            spec = (r["tn"] / 20) * 100
            print(f"| {name} | {sens:.1f}% ({r['tp']}/20) | {spec:.1f}% ({r['tn']}/20) | {r['fp']} |")
    else:
        print("\n### 4. Blind Saad Set (Table 6E): AWAITING tests/sim/blind_urdu_saad.json from Saad")

    print("\n" + "=" * 80)
    print("CRITICAL USMAN VALIDATION CHECKS:")
    test_cases = [
        ("اچانک بولنے میں مشکل ہو رہی ہے اور ایک طرف کا ہاتھ کمزور ہے", True, "Stroke / hemiparesis"),
        ("شوگر ۴۵ ہے اور چکر آ رہے ہیں", True, "Severe hypoglycemia with Eastern Arabic digits"),
        ("شوگر 135 ہے اور ہاتھ کانپ رہے ہیں", False, "Safe benign normal reading with cold shiver"),
    ]
    for phrase, exp_danger, desc in test_cases:
        trig, _cat, _lvl = screen_proposed_v3_plus(phrase)
        status = "PASS" if trig == exp_danger else "FAIL"
        print(f"  [{status}] '{phrase}' -> Triggered: {trig} (Expected: {exp_danger}) — {desc}")
        assert trig == exp_danger, f"Assertion failed for phrase: {phrase}"

    print("=" * 80)


if __name__ == "__main__":
    main()
