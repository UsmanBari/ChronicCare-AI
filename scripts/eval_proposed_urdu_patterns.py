#!/usr/bin/env python3
"""
scripts/eval_proposed_urdu_patterns.py

Standalone evaluation harness for proposed Urdu danger patterns (PR #89 / Day 4 Part C).
Evaluates:
  1. Legacy v2 Engine (run_stage1_red_flag_screen)
  2. Current v3 Engine (classify_input)
  3. Proposed v3+ Patterns (tightened patterns + numeric hypoglycemia evaluator)

Against:
  - 20 Independent Urdu Danger Phrases (Sensitivity)
  - 10 Safe Look-alikes (Specificity)
  - 40 Handwritten Benign Patient Sentences (Zero False Alarm Verification)

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

DANGER_PHRASES_PATH = REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_hassaan_ur.json"
BENIGN_SENTENCES_PATH = REPO_ROOT / "tests" / "sim" / "benign_urdu_sentences_hassaan.json"


# =============================================================================
# Proposed Clinical Patterns & Tightened Evaluator
# =============================================================================

PROPOSED_REGEX_PATTERNS = [
    # 1. Chest pain radiating to left arm
    (re.compile(r"(?:چھاتی|سینے).*(?:دباؤ|بوجھ|درد).*بائیں بازو"), "chest_pain", "emergency"),
    # 2. Severe chest constriction / suffocation
    (re.compile(r"(?:سینے|چھاتی).*(?:شدید گھٹن|دم گھٹ)"), "chest_pain", "emergency"),
    # 3. Severe respiratory distress / orthopnea
    (re.compile(r"سانس پھول.*(?:بیٹھا بھی نہیں جا رہا|چلنا محال)"), "breathing", "emergency"),
    # 4. Syncope: recurrent blackouts / fainting episodes (tightened from bare 'آنکھوں کے آگے اندھیرا')
    (re.compile(r"غشی(?: کے دورے)?|(?:آنکھوں کے آگے اندھیرا.*(?:دورے|غشی|بے ہوش|گر پڑا))"), "syncope", "emergency"),
    # 5. Stroke / Hemiparesis: body numbness & motor loss
    (re.compile(r"آدھا جسم.*(?:سن|ہلایا نہیں جا رہا)"), "focal_weakness_stroke", "emergency"),
    # 6. Stroke / Focal weakness: unilateral limb loss of strength
    (re.compile(r"(?:بائیں ہاتھ اور پاؤں|ایک طرف).*جان نہیں رہی"), "focal_weakness_stroke", "emergency"),
    # 7. Stroke / Facial asymmetry with dysphasia (tightened: bare 'بولا نہیں جا رہا' excluded)
    (re.compile(r"(?:منہ.*ٹیڑھا.*بولا نہیں جا رہا)|(?:منہ ایک طرف ٹیڑھا)"), "focal_weakness_stroke", "emergency"),
    # 8. Acute confusion / encephalopathy
    (re.compile(r"حواس کام نہیں کر رہے"), "confusion", "emergency"),
    # 9. Severe headache (thunderclap / worst of life)
    (re.compile(r"شدید درد.*پہلے کبھی نہیں ہوا|بدترین سر درد"), "severe_headache", "emergency"),
    # 10. Sudden monocular / acute vision loss
    (re.compile(r"اچانک.*(?:ایک آنکھ سے)?.*نظر آنا بند"), "vision_loss", "emergency"),
    # 11. Active gastrointestinal hemorrhage (hematemesis)
    (re.compile(r"خون کی الٹی|قے.*خون"), "bleeding", "emergency"),
    # 12. Uncontrolled tachycardia / violent palpitations with autonomic shock
    (re.compile(r"(?:دھڑکن|دل).*بے قابو.*(?:پسینے|سینے)"), "palpitations_danger", "emergency"),
]


def eval_numeric_hypoglycemia(text: str) -> tuple[str, str] | None:
    """
    Evaluates objective numeric hypoglycemia with autonomic symptoms.
    Normalizes Eastern Arabic digits (۰-۹ -> 0-9).
    Requires integer extraction with whole-number word boundaries.
    Only triggers if glucose value < 54 mg/dL (severe hypoglycemia threshold).
    Protects against numbers like 135 matching 35.
    """
    normalized = text.translate(_EASTERN_DIGITS_TABLE)
    
    # Check explicit '< 40' or '< 50' or '< 54' phrasing
    if re.search(r"شوگر.*(?:40|50|54)\s*سے کم", normalized):
        return ("severe_hypoglycemia", "emergency")
    
    # Check presence of autonomic symptoms
    has_autonomic = bool(re.search(r"(?:ہاتھ کانپ|پسینہ|کپکپی|لرز)", normalized))
    if not has_autonomic:
        return None
        
    # Extract standalone numeric tokens near 'شوگر'
    sugar_match = re.search(r"شوگر\s*[:=]?\s*(\d{1,3})\b", normalized)
    if sugar_match:
        val = int(sugar_match.group(1))
        if val < 54:
            return ("severe_hypoglycemia", "emergency")
            
    # Also find all standalone integers in text if 'شوگر' is present anywhere
    if "شوگر" in normalized:
        numbers = [int(n) for n in re.findall(r"\b\d{1,3}\b", normalized)]
        for n in numbers:
            if n < 54:
                return ("severe_hypoglycemia", "emergency")
                
    return None


def screen_proposed_v3_plus(text: str) -> tuple[bool, str | None, str | None]:
    """
    Evaluates current v3 classify_input plus the 14 proposed patterns.
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
# Benchmark Runner
# =============================================================================

def run_evaluation() -> dict[str, Any]:
    with open(DANGER_PHRASES_PATH, "r", encoding="utf-8") as f:
        danger_data = json.load(f)

    with open(BENIGN_SENTENCES_PATH, "r", encoding="utf-8") as f:
        benign_data = json.load(f)

    danger_phrases = [d for d in danger_data if d.get("expected_danger")]
    safe_lookalikes = [d for d in danger_data if not d.get("expected_danger")]

    results = {
        "v2": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "benign_fp": 0, "misses": [], "alarms": []},
        "v3": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "benign_fp": 0, "misses": [], "alarms": []},
        "proposed": {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "benign_fp": 0, "misses": [], "alarms": []},
    }

    # Evaluate 20 Danger Phrases
    for item in danger_phrases:
        phrase = item["text"]

        # v2
        is_rf_v2, _ = run_stage1_red_flag_screen(phrase)
        if is_rf_v2:
            results["v2"]["tp"] += 1
        else:
            results["v2"]["fn"] += 1
            results["v2"]["misses"].append(phrase)

        # v3
        triage_v3 = classify_input(phrase)
        if triage_v3.category == "danger_phrase":
            results["v3"]["tp"] += 1
        else:
            results["v3"]["fn"] += 1
            results["v3"]["misses"].append(phrase)

        # Proposed
        is_prop, _prop_cat, _ = screen_proposed_v3_plus(phrase)
        if is_prop:
            results["proposed"]["tp"] += 1
        else:
            results["proposed"]["fn"] += 1
            results["proposed"]["misses"].append(phrase)

    # Evaluate 10 Safe Look-alikes
    for item in safe_lookalikes:
        phrase = item["text"]

        # v2
        is_rf_v2, _ = run_stage1_red_flag_screen(phrase)
        if is_rf_v2:
            results["v2"]["fp"] += 1
            results["v2"]["alarms"].append(phrase)
        else:
            results["v2"]["tn"] += 1

        # v3
        triage_v3 = classify_input(phrase)
        if triage_v3.category == "danger_phrase":
            results["v3"]["fp"] += 1
            results["v3"]["alarms"].append(phrase)
        else:
            results["v3"]["tn"] += 1

        # Proposed
        is_prop, _, _ = screen_proposed_v3_plus(phrase)
        if is_prop:
            results["proposed"]["fp"] += 1
            results["proposed"]["alarms"].append(phrase)
        else:
            results["proposed"]["tn"] += 1

    # Evaluate 40 Benign Patient Sentences
    for phrase in benign_data:
        # v2
        is_rf_v2, _ = run_stage1_red_flag_screen(phrase)
        if is_rf_v2:
            results["v2"]["benign_fp"] += 1
            results["v2"]["alarms"].append(phrase)

        # v3
        triage_v3 = classify_input(phrase)
        if triage_v3.category == "danger_phrase":
            results["v3"]["benign_fp"] += 1
            results["v3"]["alarms"].append(phrase)

        # Proposed
        is_prop, _, _ = screen_proposed_v3_plus(phrase)
        if is_prop:
            results["proposed"]["benign_fp"] += 1
            results["proposed"]["alarms"].append(phrase)

    return results


def print_report(res: dict[str, Any]):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 80)
    print("MEASURED EVALUATION OF URDU DANGER PATTERNS (CORRECTION 2)")
    print("=" * 80)

    for eng_name, r in [
        ("Legacy v2 Engine (run_stage1_red_flag_screen)", res["v2"]),
        ("Current v3 Engine (classify_input)", res["v3"]),
        ("Proposed v3+ Engine (with 14 Proposed Patterns)", res["proposed"]),
    ]:
        tp, fn = r["tp"], r["fn"]
        tn, fp = r["tn"], r["fp"]
        benign_fp = r["benign_fp"]
        total_safe = 10 + 40
        total_fp = fp + benign_fp
        total_tn = tn + (40 - benign_fp)

        sens = (tp / (tp + fn) * 100) if (tp + fn) else 0.0
        spec = (total_tn / (total_tn + total_fp) * 100) if (total_tn + total_fp) else 0.0

        print(f"\n--- {eng_name} ---")
        print(f"  Danger Sensitivity:      {tp}/20 ({sens:.1f}%) [FN Misses: {fn}]")
        print(f"  Safe Lookalike TN:       {tn}/10 [FP Alarms: {fp}]")
        print(f"  Benign 40 Sentences TN:  {40 - benign_fp}/40 [FP Alarms: {benign_fp}]")
        print(f"  Overall Specificity:     {total_tn}/{total_safe} ({spec:.1f}%) [Total FP: {total_fp}]")

        if r["alarms"]:
            print("  False Positive Trigger Phrases:")
            for a in r["alarms"]:
                print(f"    - {a}")

    print("\n" + "=" * 80)
    print("CRITICAL SAFETY CHECK: 'شوگر 135 ہے اور ہاتھ کانپ رہے ہیں'")
    test_phrase = "شوگر 135 ہے اور ہاتھ کانپ رہے ہیں"
    is_prop, cat, lvl = screen_proposed_v3_plus(test_phrase)
    print(f"  Input:  '{test_phrase}'")
    print(f"  Result: Triggered = {is_prop} (Category: {cat}, Level: {lvl})")
    assert not is_prop, "CRITICAL ERROR: 'شوگر 135 ہے اور ہاتھ کانپ رہے ہیں' falsely triggered hypoglycemia!"
    print("  [PASS] Verified: Standalone whole-number boundary and numeric check prevented false alarm!")
    print("=" * 80)


if __name__ == "__main__":
    results = run_evaluation()
    print_report(results)
