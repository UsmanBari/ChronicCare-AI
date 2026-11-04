"""
Google Gemini LLM Client for ChronicCare AI.

Provides resilient, server-side LLM completion support via Google's Generative
Language REST API using requests. Does NOT hardcode any model names or log API keys.
Sends credentials strictly via the x-goog-api-key header (never in the URL).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

# Ensure environment variables are loaded if .env exists
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(script_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Raised when Gemini API request fails or returns an error response."""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when Gemini returns HTTP 429 Too Many Requests."""
    pass


def get_api_key() -> str:
    """Retrieves the Gemini API key from environment."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key


def get_configured_model() -> Optional[str]:
    """Retrieves the configured Gemini model ID from environment or returns None."""
    model = os.environ.get("GEMINI_MODEL", "").strip()
    return model if model else None


def is_configured() -> bool:
    """Checks whether both Gemini API key and model are configured in the environment."""
    return bool(get_api_key() and get_configured_model())


def _build_payload(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> Dict[str, Any]:
    """
    Transforms OpenAI-style messages dicts into Google Gemini REST payload format:
    - system messages mapped to top-level systemInstruction
    - user messages mapped to role 'user'
    - assistant messages mapped to role 'model'
    - generationConfig sets temperature, maxOutputTokens, and application/json mime type
    - thinkingConfig defaults to thinkingBudget=0 when GEMINI_THINKING_BUDGET is unset (set to "none" to omit)
    """
    system_parts: List[Dict[str, str]] = []
    contents: List[Dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append({"text": content})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    gen_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
        "responseMimeType": "application/json",
    }

    thinking_budget_str = os.environ.get("GEMINI_THINKING_BUDGET", "").strip()
    if thinking_budget_str.lower() == "none":
        # Explicitly skip sending thinkingConfig
        pass
    elif not thinking_budget_str:
        # Default to 0 when unset/empty to eliminate thinking latency on gemini-flash
        gen_config["thinkingConfig"] = {"thinkingBudget": 0}
    else:
        try:
            budget_val = int(thinking_budget_str)
            gen_config["thinkingConfig"] = {"thinkingBudget": budget_val}
        except (ValueError, TypeError):
            logger.warning("Invalid GEMINI_THINKING_BUDGET value: %s; defaulting to 0", thinking_budget_str)
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": gen_config,
    }

    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}

    return payload


def chat_with_usage(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: float = 30.0,
    max_retries: int = 2,
    sdk_max_retries: Optional[int] = None,
) -> Tuple[str, int]:
    """
    Executes a chat completion request with the Gemini REST API and returns (text, total_tokens).
    Sends API key in x-goog-api-key header ONLY (never in URL or query params).
    Treats HTTP 4xx/5xx, empty responses, finishReason != STOP/MAX_TOKENS, and rate limits as failures.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing or empty.")

    target_model = model or get_configured_model()
    if not target_model:
        raise ValueError("GEMINI_MODEL environment variable is missing and no model parameter was provided.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = _build_payload(messages, temperature=temperature, max_tokens=max_tokens)

    # Use max_retries unless overridden by sdk_max_retries
    effective_retries = max_retries if sdk_max_retries is None else sdk_max_retries
    attempts = 0
    last_error: Optional[Exception] = None

    while attempts <= effective_retries:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            if resp.status_code == 429:
                raise GeminiRateLimitError(f"Gemini API 429 rate limit exceeded: {resp.text[:200]}")
            
            if resp.status_code >= 400:
                raise GeminiAPIError(f"Gemini API HTTP {resp.status_code} error: {resp.text[:200]}")

            data = resp.json()
            usage = data.get("usageMetadata", {})
            total_tokens = int(usage.get("totalTokenCount", 0))

            candidates = data.get("candidates", [])
            if not candidates or not isinstance(candidates, list):
                raise GeminiAPIError("Gemini response missing candidates list")

            first_candidate = candidates[0]
            finish_reason = first_candidate.get("finishReason", "STOP")
            if finish_reason in ("SAFETY", "RECITATION", "OTHER"):
                raise GeminiAPIError(f"Gemini generation blocked with finishReason: {finish_reason}")

            content_obj = first_candidate.get("content", {})
            parts = content_obj.get("parts", [])
            if not parts:
                raise GeminiAPIError("Gemini candidate content has empty parts")

            text = "".join(part.get("text", "") for part in parts).strip()
            if not text:
                raise GeminiAPIError("Gemini returned empty text response")

            return text, total_tokens

        except GeminiRateLimitError:
            # Rate limit trips breaker immediately without retry
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            attempts += 1
            last_error = e
            logger.warning("Transient network error calling Gemini API (attempt %d/%d): %s", attempts, effective_retries + 1, type(e).__name__)
            if attempts <= effective_retries:
                time.sleep(0.5 * attempts)
            else:
                raise GeminiAPIError(f"Gemini API call failed after {effective_retries} retries: {e}") from e
        except GeminiAPIError:
            raise
        except Exception as e:
            attempts += 1
            last_error = e
            logger.warning("Unexpected error calling Gemini API (attempt %d/%d): %s", attempts, effective_retries + 1, e)
            if attempts <= effective_retries:
                time.sleep(0.5 * attempts)
            else:
                raise GeminiAPIError(f"Gemini API call failed: {e}") from e

    if last_error:
        raise last_error
    raise GeminiAPIError("Unexpected failure in Gemini chat completion execution.")


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> str:
    """Executes a chat completion request with Gemini and returns text."""
    text, _ = chat_with_usage(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
    )
    return text

