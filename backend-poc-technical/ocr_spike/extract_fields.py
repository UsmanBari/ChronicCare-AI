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
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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
    Allows Levenshtein distance <= 1 for drug names with >= 6 letters.
    Returns (canonical_name, matched_slice) or None.
    """
    clean = token.lower().strip()
    if not clean:
        return None

    # 1. Exact match (prioritizing insulin compounds if insulin is matched)
    for med in ALL_KNOWN_MEDICATIONS:
        if med == "insulin":
            ins_match = re.search(r"\binsulin\s+(glargine|lispro|aspart|detemir|degludec|regular|nph|isophane|70/30|30/70|50/50)\b", clean)
            if ins_match:
                return ins_match.group(0), ins_match.group(0)
        if med in clean:
            return med, med

    # 2. Tokenized Levenshtein slip matching (words of 6+ chars)
    words = re.findall(r"[a-z0-9]+", clean)
    for word in words:
        if len(word) >= 5:
            for med in ALL_KNOWN_MEDICATIONS:
                # Handle multi-word drugs like 'insulin glargine'
                med_parts = med.split()
                if len(med_parts) == 1:
                    target = med
                    if len(target) >= 6 and abs(len(word) - len(target)) <= 1:
                        if levenshtein_distance(word, target) <= 1:
                            return target, word
                else:
                    if word in med_parts:
                        # Check full phrase in clean
                        if med in clean or any(levenshtein_distance(word, p) <= 1 for p in med_parts if len(p) >= 6):
                            return med, word

    return None


def extract_fields(ocr_text: str) -> Dict[str, Any]:
    """
    Extracts structured clinical fields from raw OCR text.
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

    lines = ocr_text.splitlines()

    # 1. HbA1c Extraction
    # Pattern: a number + % within 30 characters after HbA1c / A1c / glycated / glycosylated
    hba1c_keyword_pattern = re.compile(
        r"(?:hba1c|a1c|glycated|glycosylated|glycated\s+haemoglobin)",
        re.IGNORECASE,
    )
    for line in lines:
        for km in hba1c_keyword_pattern.finditer(line):
            kw_end = km.end()
            window = line[kw_end : kw_end + 35]
            pct_match = re.search(r"[:=\s]*([0-9]+(?:\.[0-9]+)?)\s*%", window, re.IGNORECASE)
            if pct_match:
                val = float(pct_match.group(1))
                evidence = line[km.start() : kw_end + pct_match.end()].strip()
                if HBA1C_MIN <= val <= HBA1C_MAX:
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
    for line in lines:
        # Check context
        context = None
        line_lower = line.lower()
        if "fasting" in line_lower or "fbs" in line_lower:
            context = "fasting"
        elif "random" in line_lower or "rbs" in line_lower:
            context = "random"
        elif "post-prandial" in line_lower or "postprandial" in line_lower or " pp" in line_lower:
            context = "post-prandial"

        # Explicit unit: mmol/L or mmol/l
        mmol_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mmol/l|mmol/L)\b", line, re.IGNORECASE)
        if mmol_match:
            val = float(mmol_match.group(1))
            ev = mmol_match.group(0)
            fields.append({
                "kind": "glucose",
                "value": val,
                "unit": "mmol/L",
                "mg_dl": round(val * 18.0, 1),
                "context": context,
                "evidence": line.strip(),
                "confidence": "High",
            })
            continue

        # Explicit unit: mg/dL, mg/dl, mgdl
        mg_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\s*(?:mg/dl|mg/dL|mgdl)\b", line, re.IGNORECASE)
        if mg_match:
            val = float(mg_match.group(1))
            fields.append({
                "kind": "glucose",
                "value": val,
                "unit": "mg/dL",
                "context": context,
                "evidence": line.strip(),
                "confidence": "High",
            })
            continue

        # If line mentions glucose keyword but no unit found
        if glucose_line_pattern.search(line) and not re.search(r"%", line):
            num_match = re.search(r"(\b[0-9]+(?:\.[0-9]+)?)\b", line)
            # Ensure it's not a reference range or BP
            if num_match and "/" not in line:
                val = float(num_match.group(1))
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
    # Pattern: \d{2,3}\s*/\s*\d{2,3} near "BP" or "blood pressure" (within 20 characters)
    bp_pair_pattern = re.compile(r"\b([0-9]{2,3})\s*/\s*([0-9]{2,3})\b")
    for line in lines:
        for bpm in bp_pair_pattern.finditer(line):
            start, end = bpm.start(), bpm.end()
            # Context window within 20 chars before or after
            window = line[max(0, start - 25) : min(len(line), end + 25)]
            if re.search(r"(?:bp|blood\s+pressure|mmhg)", window, re.IGNORECASE):
                sys_val = int(bpm.group(1))
                dia_val = int(bpm.group(2))
                # Validate systolic > diastolic and within physiologic bounds
                if (
                    BP_SYSTOLIC_MIN <= sys_val <= BP_SYSTOLIC_MAX
                    and BP_DIASTOLIC_MIN <= dia_val <= BP_DIASTOLIC_MAX
                    and sys_val > dia_val
                ):
                    fields.append({
                        "kind": "bp",
                        "value": [sys_val, dia_val],
                        "unit": "mmHg",
                        "evidence": line.strip(),
                        "confidence": "High",
                    })
                else:
                    warnings.append(f"Invalid or reversed BP reading {sys_val}/{dia_val} dropped")

    # 4. Medication Extraction
    rx_indicator_pattern = re.compile(r"(?:tab\.?|cap\.?|inj\.?|syp\.?|rx:?|[0-9]+\.|\bmg\b|\bmcg\b|\bunits?\b)", re.IGNORECASE)
    dose_pattern = re.compile(r"\b([0-9]+(?:\.[0-9]+)?\s*(?:mg|mcg|units?|iu))\b", re.IGNORECASE)
    freq_pattern = re.compile(
        r"\b(od|bd|tds|qid|hs|1\s*[+-]\s*0\s*[+-]\s*1|1\s*[+-]\s*1\s*[+-]\s*1|0\s*[+-]\s*0\s*[+-]\s*1|once daily|twice daily|three times daily|subah/shaam|at night|روزانہ(?:\s+دو\s+بار)?|کھانے\s+کے\s+بعد)\b",
        re.IGNORECASE,
    )

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        matched = match_medication_name(trimmed)
        if matched:
            med_name, _ = matched
            dose_m = dose_pattern.search(trimmed)
            freq_m = freq_pattern.search(trimmed)

            dose = dose_m.group(1) if dose_m else None
            freq = freq_m.group(1) if freq_m else None

            confidence = "High" if dose and freq else ("Medium" if dose or freq else "Low")
            fields.append({
                "kind": "medication",
                "name": med_name,
                "dose": dose,
                "frequency": freq,
                "value": f"{med_name} {dose or ''} {freq or ''}".strip(),
                "unit": None,
                "evidence": trimmed,
                "confidence": confidence,
            })
        elif rx_indicator_pattern.search(trimmed) and not any(kw in trimmed.lower() for kw in ["patient", "doctor", "report", "lab", "date", "sample"]):
            # Line looks like prescription line but contains no known medication
            unmatched_lines.append(trimmed)

    return {
        "fields": fields,
        "warnings": warnings,
        "unmatched_lines": unmatched_lines,
    }
