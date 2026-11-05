"""
Groq LLM Client for ChronicCare AI.

Provides resilient, server-side LLM completion support with automatic retries,
timeouts, and credential safety checks. Does NOT hardcode any model names or log API keys.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Ensure environment variables are loaded if .env exists
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(script_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

logger = logging.getLogger(__name__)

# Groq SDK imports
try:
    from groq import Groq, APIConnectionError, RateLimitError, InternalServerError, APITimeoutError
except ImportError:
    Groq = None
    APIConnectionError = Exception
    RateLimitError = Exception
    InternalServerError = Exception
    APITimeoutError = Exception


def get_api_key() -> str:
    """Retrieves the Groq API key from environment."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key


def get_configured_model() -> Optional[str]:
    """Retrieves the configured Groq model ID from environment or returns None."""
    model = os.environ.get("GROQ_MODEL", "").strip()
    return model if model else None


def is_configured() -> bool:
    """Checks whether both Groq API key and model are configured in the environment."""
    return bool(get_api_key() and get_configured_model())


def get_client(api_key: Optional[str] = None, timeout: float = 30.0, max_retries: Optional[int] = None) -> Any:
    """
    Instantiates and returns a Groq client instance.
    Raises ValueError if Groq is not installed or API key is missing.
    """
    if Groq is None:
        raise RuntimeError("The 'groq' package is not installed. Please install groq>=0.9.0.")
    
    key = api_key or get_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY environment variable is missing or empty.")
    
    client_kwargs: Dict[str, Any] = {"api_key": key, "timeout": timeout}
    if max_retries is not None:
        client_kwargs["max_retries"] = max_retries
    return Groq(**client_kwargs)


_DEFAULT_CHAT_WITH_USAGE = None
_DEFAULT_CHAT = None


def chat_with_detailed_usage(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: float = 30.0,
    max_retries: int = 2,
    sdk_max_retries: Optional[int] = None,
) -> Tuple[str, Dict[str, int]]:
    """
    Executes a chat completion request with the Groq client and returns (text, usage_dict)
    where usage_dict has 'total_tokens' and 'completion_tokens'.
    Preserves all error handling, credential checks, and transient retry semantics.
    """
    if _DEFAULT_CHAT_WITH_USAGE is not None and chat_with_usage is not _DEFAULT_CHAT_WITH_USAGE:
        res = chat_with_usage(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            sdk_max_retries=sdk_max_retries,
        )
        if isinstance(res, tuple) and len(res) == 2:
            t, u = res
            if isinstance(u, dict):
                return t, u
            return t, {"total_tokens": int(u or 0), "completion_tokens": int(u or 0)}
        return str(res or ""), {"total_tokens": 0, "completion_tokens": 0}

    if _DEFAULT_CHAT is not None and chat is not _DEFAULT_CHAT:
        t = chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
        )
        return str(t or ""), {"total_tokens": 0, "completion_tokens": 0}
    target_model = model or get_configured_model()
    if not target_model:
        raise ValueError("GROQ_MODEL environment variable is missing and no model parameter was provided.")

    client = get_client(timeout=timeout, max_retries=sdk_max_retries)
    
    attempts = 0
    last_error: Optional[Exception] = None
    
    while attempts <= max_retries:
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if isinstance(response, dict):
                usage_obj = response.get("usage")
                choices = response.get("choices", [])
            else:
                usage_obj = getattr(response, "usage", None)
                choices = getattr(response, "choices", [])

            total_tokens = 0
            completion_tokens = 0
            if usage_obj is not None:
                if isinstance(usage_obj, dict):
                    total_tokens = int(usage_obj.get("total_tokens", 0) or 0)
                    completion_tokens = int(usage_obj.get("completion_tokens", 0) or 0)
                else:
                    total_tokens = int(getattr(usage_obj, "total_tokens", 0) or 0)
                    completion_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)

            usage_dict = {"total_tokens": total_tokens, "completion_tokens": completion_tokens}

            if not choices:
                return "", usage_dict
            
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                msg_obj = first_choice.get("message", {})
                content = msg_obj.get("content", "") if isinstance(msg_obj, dict) else getattr(msg_obj, "content", "")
            else:
                msg_obj = getattr(first_choice, "message", None)
                content = getattr(msg_obj, "content", "") if msg_obj else ""

            if content:
                return str(content).strip(), usage_dict
            return "", usage_dict
        except (APIConnectionError, RateLimitError, InternalServerError, APITimeoutError) as e:
            attempts += 1
            last_error = e
            logger.warning(
                f"Transient error calling Groq API (attempt {attempts}/{max_retries + 1}): {type(e).__name__}"
            )
            if attempts <= max_retries:
                time.sleep(0.5 * attempts)
            else:
                raise RuntimeError(f"Groq API call failed after {max_retries} retries: {type(e).__name__}") from e
        except Exception as e:
            err_str = str(e).lower()
            if any(term in err_str for term in ["rate limit", "timeout", "503", "500", "connection error"]):
                attempts += 1
                last_error = e
                logger.warning(
                    f"Transient error calling Groq API (attempt {attempts}/{max_retries + 1}): {type(e).__name__}"
                )
                if attempts <= max_retries:
                    time.sleep(0.5 * attempts)
                    continue
            raise e

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected failure in chat completion execution.")


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
    Executes a chat completion request with the Groq client and returns (text, total_tokens).
    Preserves all error handling, credential checks, and transient retry semantics.
    """
    text, usage_dict = chat_with_detailed_usage(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        sdk_max_retries=sdk_max_retries,
    )
    return text, usage_dict.get("total_tokens", 0)


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> str:
    """
    Executes a chat completion request with the Groq client.
    
    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Optional model identifier. Falls back to GROQ_MODEL environment variable.
        temperature: Sampling temperature (default: 0.2).
        max_tokens: Maximum tokens in response (default: 512).
        timeout: Request timeout in seconds (default: 30.0).
        max_retries: Maximum transient retry attempts (default: 2).
        
    Returns:
        The generated text response.
        
    Raises:
        ValueError: If API key or model is missing.
        RuntimeError: If Groq package is missing or requests fail after retries.
    """
    text, _ = chat_with_usage(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
    )
    return text

_DEFAULT_CHAT_WITH_USAGE = chat_with_usage
_DEFAULT_CHAT = chat
