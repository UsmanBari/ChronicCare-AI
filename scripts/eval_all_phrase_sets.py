"""
Evaluation Harness for Multilingual Clinical Danger Phrase Detection.
Compares v2, v3, WG_V1 (Danger Word Groups v1), and hybrid engines across
gold, independent, and blind sets.
Includes PROTOTYPE function labeled PROTOTYPE (never imported by the app).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend-poc-technical"
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.adaptive_interview_agent import run_stage1_red_flag_screen
from agents.danger_wordgroups import detect as detect_danger_wordgroups
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


def PROTOTYPE_screen_danger_phrase(text: str) -> tuple[bool, str | None]:
    """
    PROTOTYPE danger phrase classifier based on composable symptom word-groups,
    negation windows, and clinical red flag rules.
    """
    if not text or not isinstance(text, str):
        return False, None

    clean = text.strip()
    lowered = clean.lower()

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
        m_body = re.search(r"\b(?:" + "|".join(_PROTO_CHEST_BODY) + r")\b", lowered)
        m_sev = re.search(r"\b(?:" + "|".join(_PROTO_CHEST_SEVERITY) + r")\b", lowered)
        pos = min(m_body.start() if m_body else 999, m_sev.start() if m_sev else 999)
        if pos < 999 and not is_negated_window(pos):
            return True, "cardiac_chest_pain"

    return False, None


# ===========================================================================
# Dataset Configuration & Data Discipline
# ===========================================================================

PHRASE_FILES = [
    # Dev Sets (can be run during development)
    {
        "name": "Gold Standard Danger",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_gold.json",
        "format": "gold_list",
        "heldout": False,
    },
    {
        "name": "Tuning Set Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "tuning_set_urdu.json",
        "format": "blind_list",
        "heldout": False,
    },
    {
        "name": "Hassaan Urdu Independent",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_hassaan_ur.json",
        "format": "gold_list",
        "heldout": False,
    },
    {
        "name": "Wordgroups Dev (144 balanced)",
        "path": REPO_ROOT / "tests" / "sim" / "wordgroups_dev.json",
        "format": "gold_list",
        "heldout": False,
    },
    # Held-Out Sets (MUST NOT BE ACCESSED without --heldout-counts-only)
    {
        "name": "Saad Independent",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_saad.json",
        "format": "gold_list",
        "heldout": True,
    },
    {
        "name": "Hassaan Benign Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "benign_urdu_sentences_hassaan.json",
        "format": "benign_list",
        "heldout": True,
    },
    {
        "name": "Saad Blind Urdu",
        "path": REPO_ROOT / "tests" / "sim" / "blind_urdu_saad.json",
        "format": "blind_list",
        "heldout": True,
    },
    {
        "name": "Saad Independent R2",
        "path": REPO_ROOT / "tests" / "sim" / "danger_phrases_independent_saad_r2.json",
        "format": "gold_list",
        "heldout": True,
    },
    {
        "name": "Saad Blind Set 3",
        "path": REPO_ROOT / "tests" / "sim" / "blind_set_3_saad.json",
        "format": "gold_list",
        "heldout": True,
    },
]


def load_dataset(file_info: dict[str, Any]) -> list[tuple[str, bool]] | None:
    path: Path = file_info["path"]
    if not path.is_file():
        return None

    with open(path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    samples: list[tuple[str, bool]] = []
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


def eval_engine(engine_name: str, samples: list[tuple[str, bool]]) -> tuple[int, int, int, int, list[str], list[str]]:
    """
    Evaluates engine across samples.
    Returns: (danger_caught, danger_total, false_alarms, safe_total, missed_list, false_alarm_list)
    """
    danger_caught = 0
    danger_total = 0
    false_alarms = 0
    safe_total = 0
    missed_list: list[str] = []
    fa_list: list[str] = []

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
        elif engine_name == "WG_V1":
            wg = detect_danger_wordgroups(text)
            caught = bool(wg.is_danger)
        elif engine_name == "V2_PLUS_WG":
            is_d, _ = run_stage1_red_flag_screen(text)
            wg = detect_danger_wordgroups(text)
            caught = bool(is_d or wg.is_danger)
        elif engine_name == "V3_PLUS_WG":
            res = classify_input(text)
            is_v3 = bool(res.category == "danger_phrase" or res.is_emergency or res.is_urgent_safety)
            wg = detect_danger_wordgroups(text)
            caught = bool(is_v3 or wg.is_danger)
        elif engine_name == "PROTOTYPE":
            is_d, _ = PROTOTYPE_screen_danger_phrase(text)
            caught = bool(is_d)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

        if expected and caught:
            danger_caught += 1
        elif expected and not caught:
            missed_list.append(text)
        elif not expected and caught:
            false_alarms += 1
            fa_list.append(text)

    return danger_caught, danger_total, false_alarms, safe_total, missed_list, fa_list


def main():
    parser = argparse.ArgumentParser(description="Multilingual Clinical Danger Phrase Benchmark")
    parser.add_argument(
        "--heldout-counts-only",
        action="store_true",
        help="Run evaluation on held-out test sets in counts-only mode (no individual samples printed).",
    )
    parser.add_argument(
        "--verbose-misses",
        action="store_true",
        help="Print missed danger phrases and false alarms for evaluation.",
    )
    parser.add_argument(
        "--markdown",
        type=str,
        default=None,
        help="Path to write the markdown results table.",
    )
    args = parser.parse_args()

    engines = ["v2", "v3", "WG_V1", "V2_PLUS_WG", "V3_PLUS_WG", "PROTOTYPE"]

    print("=" * 105)
    print("MULTILINGUAL DANGER PHRASE BENCHMARK & WORD GROUPS V1 EVALUATION")
    print(f"Mode: {'HELD-OUT COUNTS ONLY + DEV SETS' if args.heldout_counts_only else 'DEV SETS ONLY (Held-out Protected)'}")
    print("=" * 105)
    print(f"{'Dataset':<32} | {'Engine':<12} | {'Danger Caught / Total':<24} | {'False Alarms / Safe':<22}")
    print("-" * 105)

    results_for_report = []

    for file_info in PHRASE_FILES:
        name = file_info["name"]
        is_heldout = file_info.get("heldout", False)

        if is_heldout and not args.heldout_counts_only:
            print(f"{name:<32} | {'ALL':<12} | {'HELD-OUT (PROTECTED)':<24} | {'HELD-OUT (PROTECTED)':<22}")
            results_for_report.append({
                "name": name,
                "engine": "ALL",
                "status": "HELD-OUT (PROTECTED)",
                "heldout": True,
            })
            print("-" * 105)
            continue

        samples = load_dataset(file_info)
        if samples is None:
            print(f"{name:<32} | {'ALL':<12} | {'NOT PRESENT':<24} | {'NOT PRESENT':<22}")
            results_for_report.append({
                "name": name,
                "engine": "ALL",
                "status": "NOT PRESENT",
                "heldout": is_heldout,
            })
            print("-" * 105)
            continue

        for eng in engines:
            caught, d_tot, fa, s_tot, missed, fa_items = eval_engine(eng, samples)
            d_str = f"{caught} / {d_tot} ({caught/d_tot*100:.1f}%)" if d_tot > 0 else "0 / 0 (N/A)"
            fa_str = f"{fa} / {s_tot} ({fa/s_tot*100:.1f}%)" if s_tot > 0 else f"{fa} / 0 (N/A)"
            print(f"{name:<32} | {eng:<12} | {d_str:<24} | {fa_str:<22}")
            if args.verbose_misses and (missed or fa_items):
                if missed:
                    print(f"    [{eng} Missed Positives ({len(missed)})]:")
                    for m in missed:
                        print(f"      - {m}")
                if fa_items:
                    print(f"    [{eng} False Alarms ({len(fa_items)})]:")
                    for f_item in fa_items:
                        print(f"      - {f_item}")
            results_for_report.append({
                "name": name,
                "engine": eng,
                "caught": caught,
                "d_tot": d_tot,
                "fa": fa,
                "s_tot": s_tot,
                "missed": missed,
                "fa_items": fa_items,
                "heldout": is_heldout,
            })
        print("-" * 105)

    print("=" * 105)

    if args.markdown:
        out_path = Path(args.markdown)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# Multilingual Danger Phrase Benchmark & Word Groups v1 Results",
            "",
            f"**Mode**: `{'Held-out Counts Only + Dev Sets' if args.heldout_counts_only else 'Dev Sets Only'}`",
            "",
            "| Dataset | Engine | Sensitivity (Danger Caught) | Specificity / False Alarms |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for r in results_for_report:
            if "status" in r:
                md_lines.append(f"| {r['name']} | {r['engine']} | {r['status']} | {r['status']} |")
            else:
                d_str = f"{r['caught']} / {r['d_tot']} ({r['caught']/r['d_tot']*100:.1f}%)" if r['d_tot'] > 0 else "N/A"
                fa_str = f"{r['fa']} / {r['s_tot']} ({r['fa']/r['s_tot']*100:.1f}%)" if r['s_tot'] > 0 else f"{r['fa']} / 0 (N/A)"
                md_lines.append(f"| {r['name']} | {r['engine']} | {d_str} | {fa_str} |")
        out_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print(f"Markdown results written to: {out_path}")

    return results_for_report


if __name__ == "__main__":
    main()
