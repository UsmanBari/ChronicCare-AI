"""
OCR Provider Abstraction and Factory for ChronicCare AI.
Provides clean interface for OCR extraction and strict production guard.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class OcrProvider(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """Extracts raw text strings from image bytes."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, image_bytes: bytes) -> Dict[str, Any]:
        """Performs full OCR and returns structured clinical fields with evidence snippets."""
        raise NotImplementedError


class SubprocessOcrProvider(OcrProvider):
    """
    Decorator that executes OCR extraction inside an isolated spawn subprocess
    to guarantee 100% operating system memory reclamation upon process termination.
    """

    def __init__(self, inner: OcrProvider, provider_name: str):
        self.inner = inner
        self.provider_name = provider_name

    def extract_text(self, image_bytes: bytes) -> str:
        return self.inner.extract_text(image_bytes)

    def extract(self, image_bytes: bytes) -> Dict[str, Any]:
        from data_sources.ocr.rapidocr_provider import run_ocr_in_subprocess
        return run_ocr_in_subprocess(image_bytes, provider_name=self.provider_name)


def check_ocr_provider_available(provider_type: Optional[str] = None) -> bool:
    """
    Checks whether the configured OCR provider can be imported and executed.
    Returns False in production if provider is fake, or if rapidocr is not installed.
    """
    selected_provider = (
        provider_type
        or os.environ.get("OCR_PROVIDER")
        or "rapidocr"
    ).strip().lower()

    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env == "production" and selected_provider == "fake":
        return False

    if selected_provider == "fake":
        return True

    if selected_provider == "rapidocr":
        try:
            import rapidocr_onnxruntime  # noqa: F401
            return True
        except Exception:
            return False

    return False


def get_ocr_provider(provider_type: Optional[str] = None) -> OcrProvider:
    """
    Factory function returning the configured OCR provider.
    Enforces strict production safety guard: refuses fake provider in production.
    """
    selected_provider = (
        provider_type
        or os.environ.get("OCR_PROVIDER")
        or "rapidocr"
    ).strip().lower()

    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env == "production" and selected_provider == "fake":
        raise RuntimeError("Fake OCR provider refused in production environment (APP_ENV=production)")

    if selected_provider == "fake":
        from data_sources.ocr.fake_provider import FakeOcrProvider
        raw = FakeOcrProvider()
    elif selected_provider == "rapidocr":
        from data_sources.ocr.rapidocr_provider import RapidOcrProvider
        raw = RapidOcrProvider(use_subprocess=False)
    else:
        raise ValueError(f"Unknown OCR provider: '{selected_provider}'. Allowed: 'rapidocr', 'fake'.")

    use_subprocess = os.environ.get("OCR_USE_SUBPROCESS")
    if use_subprocess is None:
        use_subprocess = (selected_provider == "rapidocr")
    else:
        use_subprocess = (use_subprocess.lower() in ("true", "1", "yes"))

    if use_subprocess:
        return SubprocessOcrProvider(raw, selected_provider)
    return raw
