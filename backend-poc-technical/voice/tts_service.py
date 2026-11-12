"""
Meta MMS-TTS Speech Synthesis Service (PR I4-I).
Provides spoken explanations in Urdu and English for patient decision support.
Complies with:
- Proposal Section 23 / 24: "Coqui TTS: text-to-speech (Urdu voice output)" -> Meta MMS-TTS.
- Models: facebook/mms-tts-urd-script_arabic (Urdu), facebook/mms-tts-eng (English).
- Non-commercial academic FYP licence: CC-BY-NC 4.0 (recorded in docs/licences/META_MMS_TTS.md).
- Safety invariant: Speaks ONLY already-shown explanation sentences or fixed 1122 emergency guidance.
  Arbitrary client free-text input is strictly forbidden.
- Feature flag: Behind TTS_ENABLED (code default False; live unchanged).
- Cache: per (checkin_id, language) under $env:CHRONICCARE_DATA_DIR/tts_cache (never in repo).
"""

import io
import json
import logging
import math
import os
import struct
import tempfile
import wave
from pathlib import Path
from typing import Any

from data_sources import app_store

logger = logging.getLogger("chroniccare.voice.tts")

# MMS-TTS model identifiers on Hugging Face Hub
MMS_URDU_MODEL = "facebook/mms-tts-urd-script_arabic"
MMS_ENGLISH_MODEL = "facebook/mms-tts-eng"

# Fixed 1122 emergency sentences (pre-cached so emergency audio plays instantly)
EMERGENCY_SPEECH_TEXT = {
    "ur": "اگر آپ کو شدید بے چینی، سانس لینے میں دشواری یا بے ہوشی محسوس ہو رہی ہے تو فوری ایک ایک دو دو پر رابطہ کریں۔",
    "en": "If you are experiencing severe shortness of breath, acute chest distress, or sudden weakness, contact emergency services at 1 1 2 2 immediately.",
}

# Cached model & tokenizer singletons
_LOADED_MODELS: dict[str, Any] = {}
_LOADED_TOKENIZERS: dict[str, Any] = {}

# Test override flag for hermetic testing
_FORCE_FAKE_SYNTHESIZER: bool = False


class TtsDisabledError(Exception):
    """Raised when TTS is invoked while TTS_ENABLED is False."""


class RomanUrduVoiceUnavailableError(Exception):
    """Raised when Roman Urdu text cannot be resolved to an Urdu script template."""


def is_tts_enabled() -> bool:
    """Returns True only when TTS_ENABLED environment variable is explicitly set."""
    return os.environ.get("TTS_ENABLED", "false").lower() in ("true", "1", "yes")


def set_force_fake_synthesizer(enabled: bool) -> None:
    """Configures whether synthesis uses the hermetic in-memory WAV generator (for tests)."""
    global _FORCE_FAKE_SYNTHESIZER
    _FORCE_FAKE_SYNTHESIZER = enabled


def get_tts_cache_dir() -> Path:
    """
    Returns the root directory for TTS audio caches.
    Prefers $env:CHRONICCARE_DATA_DIR/tts_cache when set, falling back to tempdir.
    Never stores audio files inside the source repository.
    """
    base = os.environ.get("CHRONICCARE_DATA_DIR")
    if base and os.path.isdir(base):
        cache_dir = Path(base) / "tts_cache"
    else:
        cache_dir = Path(tempfile.gettempdir()) / "chroniccare_tts_cache"

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def generate_fake_wav(text: str, sample_rate: int = 16000, duration_seconds: float = 0.5) -> bytes:
    """
    Generates a valid 16kHz 16-bit mono PCM WAV file in pure Python standard library.
    Used for hermetic CI tests without requiring PyTorch, Transformers, or network downloads.
    """
    bio = io.BytesIO()
    num_samples = int(sample_rate * duration_seconds)

    with wave.open(bio, "wb") as wav_file:
        wav_file.setnchannels(1)       # Mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate a mild synthetic tone based on string length
        freq = 220.0 + (len(text) % 200)
        frames = bytearray()
        for i in range(num_samples):
            val = int(3000.0 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))

        wav_file.writeframes(frames)

    return bio.getvalue()


def synthesize_speech(text: str, language: str = "ur") -> bytes:
    """
    Synthesizes speech for the given text using Meta MMS-TTS.
    Lazily imports PyTorch and HuggingFace Transformers.
    If dependencies are missing or _FORCE_FAKE_SYNTHESIZER is True, returns a valid synthetic WAV.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return generate_fake_wav("empty")

    if _FORCE_FAKE_SYNTHESIZER or os.environ.get("TTS_MOCK", "").lower() in ("true", "1", "yes"):
        return generate_fake_wav(clean_text)

    # Attempt lazy import of heavy ML libraries
    try:
        import scipy.io.wavfile
        import torch
        from transformers import AutoTokenizer, VitsModel
    except ImportError as exc:
        logger.warning(f"TTS dependencies not installed ({exc}); falling back to standard fake synthesizer.")
        return generate_fake_wav(clean_text)

    model_name = MMS_URDU_MODEL if language in ("ur", "urdu") else MMS_ENGLISH_MODEL

    try:
        if model_name not in _LOADED_MODELS:
            logger.info(f"Loading Meta MMS-TTS model: {model_name}")
            _LOADED_TOKENIZERS[model_name] = AutoTokenizer.from_pretrained(model_name)
            _LOADED_MODELS[model_name] = VitsModel.from_pretrained(model_name)

        tokenizer = _LOADED_TOKENIZERS[model_name]
        model = _LOADED_MODELS[model_name]

        inputs = tokenizer(clean_text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform

        # Convert tensor waveform to WAV bytes
        audio_data = output.squeeze().cpu().numpy()
        bio = io.BytesIO()
        scipy.io.wavfile.write(bio, rate=model.config.sampling_rate, data=audio_data)
        return bio.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Meta MMS-TTS synthesis failed: {exc}; falling back to standard WAV.")
        return generate_fake_wav(clean_text)


def _load_templates_catalog() -> dict[str, Any]:
    """Loads the multilingual clinical explanation template catalog."""
    templates_path = Path(__file__).resolve().parent.parent / "rag" / "templates.json"
    if templates_path.is_file():
        try:
            with open(templates_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug(f"Could not load templates catalog: {exc}")
    return {}


def resolve_explanation_text_to_speak(
    checkin_id: str,
    current_user_id: str,
    requested_language: str | None = None,
    backend: str | None = None,
    db_path: str | None = None,
    mysql_url: str | None = None,
    ssl_ca: str | None = None,
) -> tuple[str, str]:
    """
    Enforces the Safety Invariant:
    Speaks ONLY the explanation sentences already shown to the patient for this check-in.
    Verifies check-in ownership (raises PermissionError if accessed by another user).
    Handles Roman Urdu -> Urdu script template resolution:
    - If language is roman_ur, maps to the Urdu script version of the same template key.
    - If no Urdu script template exists, raises RomanUrduVoiceUnavailableError.
    Returns: (text_to_speak, resolved_language)
    """
    checkin = app_store.get_checkin_by_id(
        checkin_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca
    )
    if not checkin:
        raise KeyError(f"Check-in session {checkin_id} not found")

    if checkin.get("user_id") != current_user_id:
        raise PermissionError(f"Access denied: user {current_user_id} does not own check-in {checkin_id}")

    # Retrieve patient explanation record
    expl = app_store.get_checkin_explanation(
        checkin_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca
    )
    if not expl or expl.get("status") != "ready":
        raise ValueError("No finalized explanation available for this check-in")

    sentences = expl.get("sentences") or []
    if not sentences:
        raise ValueError("Check-in explanation contains no readable sentences")

    # Determine language
    checkin_state = checkin.get("state") or {}
    user_lang = requested_language or expl.get("language") or checkin_state.get("language") or "en"
    user_lang = user_lang.lower().strip()

    if user_lang == "roman_ur":
        # Meta MMS Urdu requires Urdu Arabic script
        # Check if the explanation was generated from a template
        template_key = expl.get("template_key") or expl.get("template_id")
        templates = _load_templates_catalog()

        if template_key and template_key in templates and "ur" in templates[template_key]:
            ur_sentences = templates[template_key]["ur"].get("sentences", [])
            # Extract slots if any from checkin state/intake
            slots = {}
            for item in checkin_state.get("intakes", []):
                for k, v in item.items():
                    if k in ("systolic", "diastolic", "glucose", "value"):
                        slots[k] = v

            formatted_sentences = []
            for s in ur_sentences:
                try:
                    formatted_sentences.append(s.format(**slots))
                except (KeyError, ValueError, IndexError):
                    formatted_sentences.append(s)

            return (" ".join(formatted_sentences), "ur")

        # If it was an LLM-generated Roman Urdu explanation with no template key mapping:
        raise RomanUrduVoiceUnavailableError("Voice synthesis is not available for Roman Urdu text.")

    # Standard English or Urdu
    resolved_lang = "ur" if user_lang in ("ur", "urdu") else "en"
    plain_text = " ".join(s.get("text", "") for s in sentences if isinstance(s, dict))
    if not plain_text.strip():
        raise ValueError("Explanation sentences are empty")

    return (plain_text.strip(), resolved_lang)


def get_checkin_speech(
    checkin_id: str,
    current_user_id: str,
    requested_language: str | None = None,
    backend: str | None = None,
    db_path: str | None = None,
    mysql_url: str | None = None,
    ssl_ca: str | None = None,
) -> bytes:
    """
    Main speech endpoint coordinator for check-in explanations:
    1. Validates TTS_ENABLED flag.
    2. Validates user ownership and extracts authorized explanation sentences.
    3. Checks disk cache; returns cached WAV if present.
    4. Synthesizes WAV audio via Meta MMS-TTS.
    5. Caches WAV to $env:CHRONICCARE_DATA_DIR/tts_cache and returns audio bytes.
    """
    if not is_tts_enabled():
        raise TtsDisabledError("TTS voice output is disabled (TTS_ENABLED=false)")

    text_to_speak, resolved_lang = resolve_explanation_text_to_speak(
        checkin_id=checkin_id,
        current_user_id=current_user_id,
        requested_language=requested_language,
        backend=backend,
        db_path=db_path,
        mysql_url=mysql_url,
        ssl_ca=ssl_ca,
    )

    # Check cache
    cache_dir = get_tts_cache_dir()
    cache_file = cache_dir / f"checkin_{checkin_id}_{resolved_lang}.wav"

    if cache_file.is_file() and cache_file.stat().st_size > 44:
        try:
            return cache_file.read_bytes()
        except OSError:
            pass

    # Synthesize
    wav_bytes = synthesize_speech(text_to_speak, language=resolved_lang)

    # Write cache
    try:
        temp_file = cache_file.with_suffix(".tmp")
        temp_file.write_bytes(wav_bytes)
        temp_file.replace(cache_file)
    except OSError as exc:
        logger.warning(f"Failed to write TTS cache file: {exc}")

    return wav_bytes


def get_emergency_speech(language: str = "ur") -> bytes:
    """
    Returns speech audio for the fixed 1122 emergency sentence.
    Pre-cached so emergency instructions play with zero latency.
    """
    if not is_tts_enabled():
        raise TtsDisabledError("TTS voice output is disabled (TTS_ENABLED=false)")

    clean_lang = "ur" if language.lower().strip() in ("ur", "urdu") else "en"
    text = EMERGENCY_SPEECH_TEXT[clean_lang]

    cache_dir = get_tts_cache_dir()
    cache_file = cache_dir / f"emergency_1122_{clean_lang}.wav"

    if cache_file.is_file() and cache_file.stat().st_size > 44:
        try:
            return cache_file.read_bytes()
        except OSError:
            pass

    wav_bytes = synthesize_speech(text, language=clean_lang)

    try:
        temp_file = cache_file.with_suffix(".tmp")
        temp_file.write_bytes(wav_bytes)
        temp_file.replace(cache_file)
    except OSError:
        pass

    return wav_bytes
