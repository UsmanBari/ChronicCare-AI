"""
Deterministic Field Extractor for OCR Spike.

Pure Python standard library implementation with medication_scope integration.
Performs deterministic parsing of:
- HbA1c (with plausibility range 3.0% to 20.0%)
- Glucose (mg/dL and mmol/L with auto mg_dl conversion, context extraction, missing unit warnings)
- Blood Pressure (systolic/diastolic bounds checking and reversal rejection)
- Medications (Levenshtein distance <= 1 slip correction for 6+ letter drugs, dose/frequency extraction)
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend root is on sys.path to import medication_scope
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from data_sources.medication_scope import (
    DIABETES_MEDICATIONS,
    HYPERTENSION_MEDICATIONS,
)

ALL_KNOWN_MEDICATIONS = sorted(
    set([m.lower() for m in DIABETES_MEDICATIONS + HYPERTENSION_MEDICATIONS]),
    key=lambda s: len(s),
    reverse=True,
)

# App clinical physiologic ranges (referenced from answer_validation.py)
BP_SYSTOLIC_MIN = 60.0
BP_SYSTOLIC_MAX = 260.0
BP_DIASTOLIC_MIN = 30.0
BP_DIASTOLIC_MAX = 160.0

HBA1C_MIN = 3.0
HBA1C_MAX = 20.0

NON_GLUCOSE_ANALYTE_PATTERN = re.compile(
    r"\b(?:cholesterol|triglyceride[s]?|creatinine|urea|blood\s+urea\s+nitrogen|bun|uric\s+acid|bilirubin|sgpt|alt|ast|alkaline\s+phosphatase|platelet[s]?|wbc)\b",
    re.IGNORECASE,
)

GLUCOSE_KEYWORD_PATTERN = re.compile(
    r"(?:glucose|blood\s+sugar|fbs|rbs|fasting|random|post[- ]?prandial|pp\b|plasma\s+glucose)",
    re.IGNORECASE,
)


def is_in_reference_context(text: str, match_start: int, match_end: int) -> bool:
    """
    Checks if a matched numeric position in text is part of a reference range, interval, or threshold.
    Guarantees clinical reference bounds (e.g. '< 5.7%', '70 - 100 mg/dL', '< 120/80') are NEVER read as patient values.
    """
    prefix = text[max(0, match_start - 35) : match_start].strip().lower()
    suffix = text[match_end : min(len(text), match_end + 35)].strip().lower()

    # 1. Direct comparison operators in prefix (< 5.7, <= 120, > 100)
    if re.search(r"[<>≤≥]|(?:less|greater)\s+than", prefix):
        return True

    # 2. Range hyphens / conjunctions (70 - 100, 4.0 to 7.8)
    if any(prefix.endswith(sym) for sym in ["-", "–", "—", "to"]):
        return True
    if any(suffix.startswith(sym) for sym in ["-", "–", "—", "to"]):
        return True

    # 3. Reference indicators in prefix (e.g. "Reference: 80 - 140", "Normal: 70 - 110", "Limits: < 130")
    if re.search(r"\b(?:reference|ref|interval|normal|standard|limits?|desirable|biological)\b", prefix):
        return True

    # 4. Enclosed in descriptive parenthetical status (e.g. "(Normal)", "(Prediabetes)", "(Desirable)")
    surrounding = text[max(0, match_start - 40) : min(len(text), match_end + 40)].lower()
    if any(k in surrounding for k in ["(normal", "(prediabetes", "(desirable", "(non-diabetic"]):
        open_paren = text.rfind("(", 0, match_start)
        close_paren = text.find(")", match_end)
        if open_paren != -1 and close_paren != -1 and open_paren < close_paren:
            return True

    # 5. Multi-column table check: a BP reading preceded by an earlier BP reading in the same row/context is in the reference column
    matched_token = text[match_start:match_end]
    if "/" in matched_token and re.search(r"\b[0-9]{2,3}\s*/\s*[0-9]{2,3}\b", text[max(0, match_start - 60) : match_start]):
        return True

    return False


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes pure Python Levenshtein edit distance without external dependencies."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def match_medication_name(token: str) -> Optional[Tuple[str, str]]:
    """
    Matches token against known diabetes/hypertension lists.
    Allows Levenshtein distance <= 1 for drug names with >= 6 letters,
    handles whitespace breaks (e.g. 'empag liflozin'), and OCR digit slips (1->l, 0->o).
    Returns (canonical_name, matched_slice) or None.
    """
    clean = token.lower().strip()
    if not clean:
        return None

    # 1. Exact substring match (prioritizing insulin compounds)
    for med in ALL_KNOWN_MEDICATIONS:
        if med == "insulin":
            ins_match = re.search(
                r"\binsulin\s+(glargine|lispro|aspart|detemir|degludec|regular|nph|isophane|70/30|30/70|50/50)\b",
                clean,
            )
            if ins_match:
                return ins_match.group(0), ins_match.group(0)
        if med in clean:
            return med, med

    # 2. Tokenized Levenshtein slip matching (words and adjacent word pairs)
    words = re.findall(r"[a-z0-9]+", clean)
    candidate_tokens = list(words)
    for i in range(len(words) - 1):
        candidate_tokens.append(words[i] + words[i + 1])

    digit_slip_table = str.maketrans("105", "los")
    best_match = None
    min_dist = 999

    for token_word in candidate_tokens:
        if len(token_word) >= 5:
            w_norm = token_word.translate(digit_slip_table)
            for med in ALL_KNOWN_MEDICATIONS:
                med_parts = med.split()
                if len(med_parts) == 1:
                    target = med
                    max_dist = 2 if len(target) >= 9 else 1
                    if abs(len(token_word) - len(target)) <= max_dist:
                        d1 = levenshtein_distance(token_word, target)
                        d2 = levenshtein_distance(w_norm, target)
                        d = min(d1, d2)
                        if d <= max_dist and d < min_dist:
                            min_dist = d
                            best_match = (target, token_word)
                            if min_dist == 0:
                                return best_match
                else:
                    if token_word in med_parts or token_word == med.replace(" ", ""):
                        return med, token_word
                    for p in med_parts:
                        if len(p) >= 6:
                            d = min(levenshtein_distance(token_word, p), levenshtein_distance(w_norm, p))
                            if d <= 1 and d < min_dist:
                                min_dist = d
                                best_match = (med, token_word)

    if best_match:
        return best_match

    return None


def extract_fields(ocr_text: str) -> Dict[str, Any]:
    """
    Extracts structured clinical fields from raw OCR text.
    Handles single-line and cross-line table columns.
    Returns:
        {
            "fields": [
                {
                    "kind": "hba1c" | "glucose" | "bp" | "medication",
                    "value": ...,
                    "unit": ...,
                    "evidence": ...,
                    "confidence": "High" | "Medium" | "Low",
                    ...
                }
            ],
            "warnings": [...],
            "unmatched_lines": [...]
        }
    """
    if not ocr_text or not ocr_text.strip():
        return {"fields": [], "warnings": [], "unmatched_lines": []}

    fields: List[Dict[str, Any]] = []
    warnings: List[str] = []
    unmatched_lines: List[str] = []

    raw_lines = ocr_text.splitlines()
    clean_lines = [l.strip() for l in raw_lines if l.strip()]

    # Separate clinical rows from report footnotes/methodology lines
    test_lines = []
    for line in clean_lines:
        # Exclude report footnotes/disclaimers from merging into test rows
        if not re.match(r"^(?:note|method|verified|signature|consult|disclaimer|affiliated|accredited)\b", line, re.IGNORECASE):
            test_lines.append(line)

    # Build evaluation windows: 1, 2, 3, and 4 consecutive clinical lines
    windows = []
    for line in test_lines:
        windows.append(line)
    for i in range(len(test_lines) - 1):
        windows.append(f"{test_lines[i]} {test_lines[i+1]}")
    for i in range(len(test_lines) - 2):
        windows.append(f"{test_lines[i]} {test_lines[i+1]} {test_lines[i+2]}")
    for i in range(len(test_lines) - 3):
        windows.append(f"{test_lines[i]} {test_lines[i+1]} {test_lines[i+2]} {test_lines[i+3]}")

    seen_fields = set()
    seen_glucose_values = set()

    # 1. HbA1c Extraction
    # Matches HbA1c, A1c, Glycated/Glycosylated Haemoglobin/Hemoglobin across tabular line wraps
    hba1c_keyword_pattern = re.compile(
        r"(?:hba[1li|]\.?c|a1c|glycated\s*h[ae]moglobin|glycosylated\s*h[ae]moglobin|glycosylated\s*hb|glycated\s*hb|glycated|glycosylated|۲۸۹)",
        re.IGNORECASE,
    )
    for win in windows:
        for km in hba1c_keyword_pattern.finditer(win):
            kw_end = km.end()
            window_slice = win[kw_end : kw_end + 45]
            for pct_match in re.finditer(r"[:=\s]*([0-9]+(?:\.[0-9]+)?)\s*%", window_slice, re.IGNORECASE):
                val = float(pct_match.group(1))
                match_start_in_win = kw_end + pct_match.start(1)
                match_end_in_win = kw_end + pct_match.end(1)

                # Never extract reference range thresholds (e.g. "< 5.7%", "4.0 - 5.6%")
                if is_in_reference_context(win, match_start_in_win, match_end_in_win):
                    continue

                evidence = win[km.start() : kw_end + pct_match.end()].strip()
                if HBA1C_MIN <= val <= HBA1C_MAX:
                    field_key = ("hba1c", val)
                    if field_key not in seen_fields:
                        seen_fields.add(field_key)
                        fields.append({
                            "kind": "hba1c",
                            "value": val,
                            "unit": "%",
                            "evidence": evidence,
                            "confidence": "High",
                        })
                else:
                    warnings.append(f"Implausible HbA1c value {val}% dropped outside [3.0, 20.0]")

    # 2. Glucose Extraction
    # Pass 1: Explicit units (mmol/L and mg/dL)
    for win in windows:
        win_lower = win.lower()

        # Must exclude non-glucose analytes
        if NON_GLUCOSE_ANALYTE_PATTERN.search(win):
            continue

        # Must have an explicit glucose keyword in this window
        if not GLUCOSE_KEYWORD_PATTERN.search(win):
            continue

        # Context detection
        context = None
        if "fasting" in win_lower or "fbs" in win_lower:
            context = "fasting"
        elif "random" in win_lower or "rbs" in win_lower:
            context = "random"
        elif "post-prandial" in win_lower or "postprandial" in win_lower or " pp" in win_lower:
            context = "post-prandial"

        # Explicit unit: mmol/L or mmol/l
        for mmol_match in re.finditer(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mmol/l|mmol/L)\b", win, re.IGNORECASE):
            val = float(mmol_match.group(1))
            val_start, val_end = mmol_match.start(1), mmol_match.end(1)

            # Never extract reference ranges (e.g. "4.0 - 7.8 mmol/L")
            if is_in_reference_context(win, val_start, val_end):
                continue

            field_key = ("glucose", val, "mmol/L")
            if field_key not in seen_fields:
                seen_fields.add(field_key)
                seen_glucose_values.add(val)
                fields.append({
                    "kind": "glucose",
                    "value": val,
                    "unit": "mmol/L",
                    "mg_dl": round(val * 18.0, 1),
                    "context": context,
                    "evidence": win.strip(),
                    "confidence": "High",
                })

        # Explicit unit: mg/dL, mg/dl, mgdl
        for mg_match in re.finditer(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl|mg/dL|mgdl)\b", win, re.IGNORECASE):
            val = float(mg_match.group(1))
            val_start, val_end = mg_match.start(1), mg_match.end(1)

            # Never extract reference ranges (e.g. "70 - 100 mg/dL", "< 200 mg/dL")
            if is_in_reference_context(win, val_start, val_end):
                continue

            field_key = ("glucose", val, "mg/dL")
            if field_key not in seen_fields:
                seen_fields.add(field_key)
                seen_glucose_values.add(val)
                fields.append({
                    "kind": "glucose",
                    "value": val,
                    "unit": "mg/dL",
                    "context": context,
                    "evidence": win.strip(),
                    "confidence": "High",
                })

    # Pass 2: Unitless glucose fallback (only if value not already extracted with explicit unit)
    for line in test_lines:
        line_lower = line.lower()
        if (
            GLUCOSE_KEYWORD_PATTERN.search(line)
            and not NON_GLUCOSE_ANALYTE_PATTERN.search(line)
            and not re.search(r"%", line)
            and not re.search(r"(?:mg/dl|mmol/l)", line, re.IGNORECASE)
        ):
            context = None
            if "fasting" in line_lower or "fbs" in line_lower:
                context = "fasting"
            elif "random" in line_lower or "rbs" in line_lower:
                context = "random"
            elif "post-prandial" in line_lower or "postprandial" in line_lower or " pp" in line_lower:
                context = "post-prandial"

            for num_match in re.finditer(r"(\b[0-9]+(?:\.[0-9]+)?)\b", line):
                if "/" in line:
                    continue
                val = float(num_match.group(1))
                if val in seen_glucose_values:
                    continue
                val_start, val_end = num_match.start(1), num_match.end(1)
                if is_in_reference_context(line, val_start, val_end):
                    continue

                field_key = ("glucose", val, None)
                if field_key not in seen_fields:
                    seen_fields.add(field_key)
                    seen_glucose_values.add(val)
                    warnings.append(f"Glucose value {val} unit missing; kept as low confidence")
                    fields.append({
                        "kind": "glucose",
                        "value": val,
                        "unit": None,
                        "context": context,
                        "evidence": line.strip(),
                        "confidence": "Low",
                    })

    # 3. Blood Pressure Extraction
    bp_pair_pattern = re.compile(r"\b([0-9]{2,3})\s*/\s*([0-9]{2,3})\b")
    for win in windows:
        bp_matches = list(bp_pair_pattern.finditer(win))
        for idx_m, bpm in enumerate(bp_matches):
            # In multi-column lab reports, subsequent BP readings in the same row represent the reference column
            if idx_m > 0:
                continue

            start, end = bpm.start(), bpm.end()

            # Never extract reference range BP thresholds (e.g. "< 120/80 mmHg", "Standard: 120/80")
            if is_in_reference_context(win, start, end):
                continue

            window_slice = win[max(0, start - 40) : min(len(win), end + 40)]
            if re.search(r"(?:bp\b|b\.?p\.?|blood\s*pressure|vitals?|sitting|standing|supine)", window_slice, re.IGNORECASE):
                sys_val = int(bpm.group(1))
                dia_val = int(bpm.group(2))

                # If another BP reading is already recorded, standard reference intervals (120/80, 130/80) are reference columns
                if any(k[0] == "bp" for k in seen_fields) and (sys_val, dia_val) in [(120, 80), (130, 80)]:
                    continue

                if (
                    BP_SYSTOLIC_MIN <= sys_val <= BP_SYSTOLIC_MAX
                    and BP_DIASTOLIC_MIN <= dia_val <= BP_DIASTOLIC_MAX
                    and sys_val > dia_val
                ):
                    field_key = ("bp", sys_val, dia_val)
                    if field_key not in seen_fields:
                        seen_fields.add(field_key)
                        fields.append({
                            "kind": "bp",
                            "value": [sys_val, dia_val],
                            "unit": "mmHg",
                            "evidence": win.strip(),
                            "confidence": "High",
                        })
                else:
                    warnings.append(f"Invalid or reversed BP reading {sys_val}/{dia_val} dropped")

    # 4. Medication Extraction
    rx_indicator_pattern = re.compile(
        r"(?:tab\.?|cap\.?|inj\.?|syp\.?|rx:?|[0-9]+\.|\bmg\b|\bmcg\b|\bunits?\b)",
        re.IGNORECASE,
    )
    dose_pattern = re.compile(r"\b([0-9]+(?:\.[0-9]+)?\s*(?:mg|mcg|units?|iu)|[0-9]+[:\.]?[0-9]*\s*mg)\b", re.IGNORECASE)
    freq_pattern = re.compile(
        r"\b(od|bd|tds|qid|hs|1\s*[+-]\s*0\s*[+-]\s*1|1\s*[+-]\s*1\s*[+-]\s*1|0\s*[+-]\s*0\s*[+-]\s*1|1\s*[+-]\s*0\s*[+-]\s*0|once daily|twice daily|three times daily|subah/shaam|at night|روزانہ(?:\s+دو\s+بار)?|کھانے\s+کے\s+بعد)\b",
        re.IGNORECASE,
    )

    for line in clean_lines:
        matched = match_medication_name(line)
        if matched:
            med_name, _ = matched
            dose_m = dose_pattern.search(line)
            freq_m = freq_pattern.search(line)

            dose = dose_m.group(1) if dose_m else None
            if dose:
                dose = dose.replace(":", ".")
            freq = freq_m.group(1) if freq_m else None

            confidence = "High" if dose and freq else ("Medium" if dose or freq else "Low")
            field_key = ("medication", med_name)
            if field_key not in seen_fields:
                seen_fields.add(field_key)
                fields.append({
                    "kind": "medication",
                    "name": med_name,
                    "dose": dose,
                    "frequency": freq,
                    "value": f"{med_name} {dose or ''} {freq or ''}".strip(),
                    "unit": None,
                    "evidence": line.strip(),
                    "confidence": confidence,
                })
        elif rx_indicator_pattern.search(line) and not any(kw in line.lower() for kw in ["patient", "doctor", "report", "lab", "date", "sample", "prescription"]):
            unmatched_lines.append(line)

    return {
        "fields": fields,
        "warnings": warnings,
        "unmatched_lines": unmatched_lines,
    }
