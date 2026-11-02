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
    r"\b(?:cholesterol|triglyceride[s]?|creatinine|urea|hdl|ldl|bilirubin|uric\s+acid|sgpt|alt|ast|platelet[s]?|wbc)\b",
    re.IGNORECASE,
)


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

    # Build evaluation windows: individual lines and adjacent merged pairs
    windows = []
    for line in clean_lines:
        windows.append(line)
    for i in range(len(clean_lines) - 1):
        windows.append(f"{clean_lines[i]} {clean_lines[i+1]}")

    seen_fields = set()

    # 1. HbA1c Extraction
    # Pattern: a number + % within 35 characters after HbA1c / A1c / glycated / glycosylated
    hba1c_keyword_pattern = re.compile(
        r"(?:hba[1li|]\.?c|a1c|glycated\s+haemoglobin|glycated|glycosylated|۲۸۹)",
        re.IGNORECASE,
    )
    for win in windows:
        for km in hba1c_keyword_pattern.finditer(win):
            kw_end = km.end()
            window_slice = win[kw_end : kw_end + 35]
            pct_match = re.search(r"[:=\s]*([0-9]+(?:\.[0-9]+)?)\s*%", window_slice, re.IGNORECASE)
            if pct_match:
                val = float(pct_match.group(1))
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
    # Look for glucose values with unit (mg/dL or mmol/L) or without unit
    glucose_line_pattern = re.compile(
        r"(?:glucose|blood\s+sugar|fbs|rbs|fasting|random|post-prandial|postprandial|pp)",
        re.IGNORECASE,
    )
    for win in windows:
        win_lower = win.lower()

        # Exclude non-glucose analytes (e.g. cholesterol, creatinine)
        if NON_GLUCOSE_ANALYTE_PATTERN.search(win):
            continue

        # Check context
        context = None
        if "fasting" in win_lower or "fbs" in win_lower:
            context = "fasting"
        elif "random" in win_lower or "rbs" in win_lower:
            context = "random"
        elif "post-prandial" in win_lower or "postprandial" in win_lower or " pp" in win_lower:
            context = "post-prandial"

        # Explicit unit: mmol/L or mmol/l
        mmol_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mmol/l|mmol/L)\b", win, re.IGNORECASE)
        if mmol_match:
            val = float(mmol_match.group(1))
            field_key = ("glucose", val, "mmol/L")
            if field_key not in seen_fields:
                seen_fields.add(field_key)
                fields.append({
                    "kind": "glucose",
                    "value": val,
                    "unit": "mmol/L",
                    "mg_dl": round(val * 18.0, 1),
                    "context": context,
                    "evidence": win.strip(),
                    "confidence": "High",
                })
            continue

        # Explicit unit: mg/dL, mg/dl, mgdl
        mg_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl|mg/dL|mgdl)\b", win, re.IGNORECASE)
        if mg_match:
            val = float(mg_match.group(1))
            field_key = ("glucose", val, "mg/dL")
            if field_key not in seen_fields:
                seen_fields.add(field_key)
                fields.append({
                    "kind": "glucose",
                    "value": val,
                    "unit": "mg/dL",
                    "context": context,
                    "evidence": win.strip(),
                    "confidence": "High",
                })
            continue

        # If line mentions glucose keyword but no unit found
        if glucose_line_pattern.search(win) and not re.search(r"%", win):
            num_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\b", win)
            # Ensure it's not a reference range or BP
            if num_match and "/" not in win:
                val = float(num_match.group(1))
                field_key = ("glucose", val, None)
                if field_key not in seen_fields:
                    seen_fields.add(field_key)
                    warnings.append(f"Glucose value {val} unit missing; kept as low confidence")
                    fields.append({
                        "kind": "glucose",
                        "value": val,
                        "unit": None,
                        "context": context,
                        "evidence": win.strip(),
                        "confidence": "Low",
                    })

    # 3. Blood Pressure Extraction
    # Pattern: \d{2,3}\s*/\s*\d{2,3} near "BP" or "blood pressure"
    bp_pair_pattern = re.compile(r"\b([0-9]{2,3})\s*/\s*([0-9]{2,3})\b")
    for win in windows:
        for bpm in bp_pair_pattern.finditer(win):
            start, end = bpm.start(), bpm.end()
            window_slice = win[max(0, start - 25) : min(len(win), end + 25)]
            if re.search(r"(?:bp|blood\s+pressure|mmhg)", window_slice, re.IGNORECASE):
                sys_val = int(bpm.group(1))
                dia_val = int(bpm.group(2))
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
