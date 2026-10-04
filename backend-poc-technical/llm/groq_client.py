"""
Groq LLM Client for ChronicCare AI.

Provides resilient, server-side LLM completion support with automatic retries,
timeouts, and credential safety checks. Does NOT hardcode any model names or log API keys.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
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


def get_client(api_key: Optional[str] = None, timeout: float = 30.0) -> Any:
    """
    Instantiates and returns a Groq client instance.
    Raises ValueError if Groq is not installed or API key is missing.
    """
    if Groq is None:
        raise RuntimeError("The 'groq' package is not installed. Please install groq>=0.9.0.")
    
    key = api_key or get_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY environment variable is missing or empty.")
    
    return Groq(api_key=key, timeout=timeout)


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
    target_model = model or get_configured_model()
    if not target_model:
        raise ValueError("GROQ_MODEL environment variable is missing and no model parameter was provided.")

    client = get_client(timeout=timeout)
    
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
            choices = getattr(response, "choices", [])
            if not choices:
                return ""
            
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if message and getattr(message, "content", None):
                return message.content.strip()
            return ""
        except (APIConnectionError, RateLimitError, InternalServerError, APITimeoutError) as e:
            attempts += 1
            last_error = e
            logger.warning(
                f"Transient error calling Groq API (attempt {attempts}/{max_retries + 1}): {type(e).__name__}"
            )
            if attempts <= max_retries:
                time.sleep(0.5 * attempts)
            else:
                raise RuntimeError(f"Groq API call failed after {max_retries} retries: {e}") from e
        except Exception as e:
            # Check for generic transient error patterns
            err_str = str(e).lower()
            if any(term in err_str for term in ["rate limit", "timeout", "503", "500", "connection error"]):
                attempts += 1
                last_error = e
                logger.warning(
                    f"Transient error calling Groq API (attempt {attempts}/{max_retries + 1}): {e}"
                )
                if attempts <= max_retries:
                    time.sleep(0.5 * attempts)
                    continue
            raise e

    if last_error:
        raise last_error
    raise RuntimeError("Unexpected failure in chat completion execution.")
