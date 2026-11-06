"""
Production RapidOCR Provider using ONNX Runtime.
Performs server-side text recognition on English prescriptions and lab reports.
Lazy-loads rapidocr_onnxruntime so imports never fail when rapidocr is not used.
"""

from __future__ import annotations

import io
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from data_sources.ocr.provider import OcrProvider
from data_sources.ocr.extract_fields import extract_fields


class RapidOcrProvider(OcrProvider):
    """
    RapidOCR implementation.
    Processes images via RapidOCR on ONNX runtime (CPU hermetic execution).
    """

    def __init__(self, use_subprocess: Optional[bool] = None):
        self._engine = None
        if use_subprocess is None:
            flag = os.environ.get("OCR_USE_SUBPROCESS", "true").lower()
            self.use_subprocess = flag in ("true", "1", "yes")
        else:
            self.use_subprocess = use_subprocess

    def _get_engine(self):
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                # Pass single-thread session options to restrict CPU memory allocations on low-memory containers (Render 512MB)
                self._engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
            except ImportError as e:
                raise RuntimeError(
                    "RapidOCR engine is not installed. Please install requirements from requirements-ocr.txt."
                ) from e
        return self._engine

    def extract_text(self, image_bytes: bytes) -> str:
        engine = self._get_engine()
        # rapidocr accepts numpy ndarray, raw bytes or file path
        result, _ = engine(image_bytes)
        if not result:
            return ""

        # RapidOCR returns list of [box, text, score]
        lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
        return "\n".join(lines)

    def extract(self, image_bytes: bytes) -> Dict[str, Any]:
        if self.use_subprocess:
            return run_ocr_in_subprocess(image_bytes)

        engine = self._get_engine()
        result, _ = engine(image_bytes)
        if not result:
            return {
                "raw_text": "",
                "has_urdu": False,
                "notice": None,
                "medications": [],
                "observations": [],
                "allergies": [],
                "warnings": ["No text detected in uploaded image."],
                "unmatched_lines": [],
            }

        lines = [item[1] for item in result if item and len(item) > 1 and item[1]]
        raw_text = "\n".join(lines)

        # Check for Urdu script characters (Unicode Arabic/Urdu block: 0600-06FF)
        has_urdu = bool(re.search(r"[\u0600-\u06FF]", raw_text))

        parsed = extract_fields(raw_text)

        medications = []
        observations = []
        allergies = []

        for f in parsed.get("fields", []):
            kind = f.get("kind")
            if kind == "medication":
                medications.append({
                    "id": f"ocr-med-{uuid.uuid4().hex[:8]}",
                    "name": f.get("name", ""),
                    "dosage": f.get("dose") or f.get("frequency") or "",
                    "frequency": f.get("frequency"),
                    "status": "active",
                    "evidence": f.get("evidence", ""),
                    "confidence": f.get("confidence", "Medium"),
                })
            elif kind == "glucose":
                observations.append({
                    "id": f"ocr-obs-{uuid.uuid4().hex[:8]}",
                    "observation_type": "glucose",
                    "value": f.get("value"),
                    "unit": f.get("unit") or "mg/dL",
                    "context": f.get("context"),
                    "evidence": f.get("evidence", ""),
                    "confidence": f.get("confidence", "High"),
                })
            elif kind == "hba1c":
                observations.append({
                    "id": f"ocr-obs-{uuid.uuid4().hex[:8]}",
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
                        "id": f"ocr-obs-{uuid.uuid4().hex[:8]}",
                        "observation_type": "blood_pressure_systolic",
                        "value": vals[0],
                        "unit": "mmHg",
                        "evidence": f.get("evidence", ""),
                        "confidence": f.get("confidence", "High"),
                    })
                    observations.append({
                        "id": f"ocr-obs-{uuid.uuid4().hex[:8]}",
                        "observation_type": "blood_pressure_diastolic",
                        "value": vals[1],
                        "unit": "mmHg",
                        "evidence": f.get("evidence", ""),
                        "confidence": f.get("confidence", "High"),
                    })

        for line in lines:
            line_clean = line.strip()
            line_lower = line_clean.lower()
            if "allerg" in line_lower:
                m = re.search(r"allerg(?:y|ies)?\s*:\s*([A-Za-z]+)(?:\s*\(([^)]+)\))?", line_clean, re.IGNORECASE)
                if m:
                    substance = m.group(1).strip()
                    reaction = m.group(2).strip() if m.group(2) else None
                    allergies.append({
                        "id": f"ocr-all-{uuid.uuid4().hex[:8]}",
                        "substance": substance,
                        "reaction": reaction,
                        "confirmed": True,
                        "evidence": line_clean,
                        "confidence": "High",
                    })

        notice = None
        if has_urdu:
            notice = (
                "Urdu text detected in document. In v1, Urdu handwriting recognition is experimental. "
                "Please review detected values carefully against the original prescription or report."
            )

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


def _ocr_subprocess_worker(result_queue, image_bytes: bytes, provider_name: Optional[str] = None):
    """
    Isolated worker process function for running OCR.
    Executes in a separate process, puts extracted dictionary or error into result_queue, and exits.
    """
    import os
    import time

    # Injected test hooks for verifying worker lifecycle robustness
    if os.environ.get("TEST_OCR_WORKER_CRASH") == "1":
        os._exit(139)
    if os.environ.get("TEST_OCR_WORKER_HANG") == "1":
        time.sleep(10)

    # Ensure worker executes inference in-process without recursing subprocesses
    os.environ["OCR_USE_SUBPROCESS"] = "false"

    try:
        from data_sources.ocr.provider import get_ocr_provider
        provider = get_ocr_provider(provider_name)
        extracted = provider.extract(image_bytes)
        result_queue.put({"status": "ok", "data": extracted})
    except (ImportError, ModuleNotFoundError) as e:
        result_queue.put({"status": "unavailable", "error": type(e).__name__})
    except Exception as e:
        result_queue.put({"status": "error", "error": type(e).__name__})


def run_ocr_in_subprocess(
    image_bytes: bytes,
    provider_name: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes OCR in a short-lived spawn subprocess to guarantee immediate memory reclamation
    by the operating system upon process termination (preventing ONNX runtime resident accumulation on Render free tier).
    """
    import multiprocessing as mp
    import os

    if timeout_seconds is None:
        timeout_seconds = float(os.environ.get("OCR_SUBPROCESS_TIMEOUT", "30.0"))

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(
        target=_ocr_subprocess_worker,
        args=(q, image_bytes, provider_name or os.environ.get("OCR_PROVIDER")),
    )
    p.start()
    p.join(timeout=timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join(timeout=1.0)
        if p.is_alive():
            p.kill()
        raise TimeoutError(f"OCR worker timed out after {timeout_seconds}s")

    if p.exitcode != 0:
        raise RuntimeError(f"OCR worker crashed with exitcode {p.exitcode}")

    if q.empty():
        raise RuntimeError("OCR worker exited without returning result")

    msg = q.get_nowait()
    if msg.get("status") == "unavailable":
        raise ModuleNotFoundError(f"OCR provider unavailable: {msg.get('error')}")
    if msg.get("status") == "error":
        raise RuntimeError(f"OCR extraction failed: {msg.get('error')}")

    return msg.get("data")

