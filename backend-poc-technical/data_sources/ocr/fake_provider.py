"""
Hermetic Fake OCR Provider for Unit Tests and Offline CI.
Never touches real ML models, external OCR binaries, or native libraries.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from data_sources.ocr.provider import OcrProvider
from data_sources.ocr.extract_fields import extract_fields


class FakeOcrProvider(OcrProvider):
    """
    Fake OCR engine that converts image bytes or pre-configured mock text
    into structured clinical fields using extract_fields.
    """

    def __init__(self, canned_text: Optional[str] = None):
        self.canned_text = canned_text

    def extract_text(self, image_bytes: bytes) -> str:
        if self.canned_text is not None:
            return self.canned_text

        # Try to decode ascii/utf-8 text embedded in test mock image bytes
        try:
            decoded = image_bytes.decode("utf-8", errors="ignore")
            # If readable clinical tokens exist in the byte payload, use them
            if any(kw in decoded.lower() for kw in ["glucose", "bp", "hba1c", "tab", "metformin", "amlodipine", "blood sugar"]):
                return decoded
        except Exception:
            pass

        # Standard canned synthetic clinical document
        return (
            "Lab Report\n"
            "Patient: Test Patient\n"
            "Fasting Blood Glucose: 118 mg/dL\n"
            "HbA1c: 6.8%\n"
            "Blood Pressure: 130/84 mmHg\n"
            "Rx: Tab Metformin 500mg 1 tab BD\n"
            "Rx: Tab Amlodipine 5mg 1 tab OD\n"
            "Allergies: Penicillin (Rash)\n"
        )

    def extract(self, image_bytes: bytes) -> Dict[str, Any]:
        raw_text = self.extract_text(image_bytes)

        # Check for Urdu script characters (Unicode Arabic/Urdu block: 0600-06FF)
        has_urdu = bool(re.search(r"[\u0600-\u06FF]", raw_text))

        parsed = extract_fields(raw_text)

        # Group fields into medications, observations, and allergies
        medications = []
        observations = []
        allergies = []

        for f in parsed.get("fields", []):
            kind = f.get("kind")
            if kind == "medication":
                medications.append({
                    "name": f.get("name", ""),
                    "dosage": f.get("dose") or f.get("frequency") or "",
                    "frequency": f.get("frequency"),
                    "status": "active",
                    "evidence": f.get("evidence", ""),
                    "confidence": f.get("confidence", "Medium"),
                })
            elif kind == "glucose":
                observations.append({
                    "observation_type": "glucose",
                    "value": f.get("value"),
                    "unit": f.get("unit") or "mg/dL",
                    "context": f.get("context"),
                    "evidence": f.get("evidence", ""),
                    "confidence": f.get("confidence", "High"),
                })
            elif kind == "hba1c":
                observations.append({
                    "observation_type": "hba1c",
                    "value": f.get("value"),
                    "unit": "%",
                    "evidence": f.get("evidence", ""),
                    "confidence": f.get("confidence", "High"),
                })
            elif kind == "bp":
                vals = f.get("value", [])
                if len(vals) == 2:
                    observations.append({
                        "observation_type": "blood_pressure_systolic",
                        "value": vals[0],
                        "unit": "mmHg",
                        "evidence": f.get("evidence", ""),
                        "confidence": f.get("confidence", "High"),
                    })
                    observations.append({
                        "observation_type": "blood_pressure_diastolic",
                        "value": vals[1],
                        "unit": "mmHg",
                        "evidence": f.get("evidence", ""),
                        "confidence": f.get("confidence", "High"),
                    })

        # Check for allergy lines in raw text
        for line in raw_text.splitlines():
            line_clean = line.strip()
            line_lower = line_clean.lower()
            if "allerg" in line_lower:
                m = re.search(r"allerg(?:y|ies)?\s*:\s*([A-Za-z]+)(?:\s*\(([^)]+)\))?", line_clean, re.IGNORECASE)
                if m:
                    substance = m.group(1).strip()
                    reaction = m.group(2).strip() if m.group(2) else None
                    allergies.append({
                        "substance": substance,
                        "reaction": reaction,
                        "confirmed": True,
                        "evidence": line_clean,
                        "confidence": "High",
                    })

        notice = None
        if has_urdu:
            notice = "We can only read English reports for now. Please add these values yourself."

        return {
            "raw_text": raw_text,
            "has_urdu": has_urdu,
            "notice": notice,
            "medications": medications,
            "observations": observations,
            "allergies": allergies,
            "warnings": parsed.get("warnings", []),
            "unmatched_lines": parsed.get("unmatched_lines", []),
        }
