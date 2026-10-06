"""
Robust FHIR R4 Client for Connected Mode.

Supports both live external FHIR R4 endpoints and the built-in in-process simulator (sim://).
Provides deterministic error handling, response size protection, in-memory caching with 30s TTL,
and bounded retries for transient server faults.
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Tuple, Callable
from data_sources import fhir_sim

DEFAULT_FHIR_BASE_URL = "https://r4.smarthealthit.org"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB cap
DEFAULT_CACHE_TTL = 30.0  # 30 seconds

# In-memory cache: (base_url, path, tuple_of_sorted_params) -> (timestamp, data)
_CACHE: Dict[Tuple[str, str, Tuple], Tuple[float, Any]] = {}
_CLOCK_OVERRIDE: Optional[Callable[[], float]] = None


def _get_time() -> float:
    if _CLOCK_OVERRIDE is not None:
        return _CLOCK_OVERRIDE()
    return time.monotonic()


def set_cache_clock(clock_fn: Optional[Callable[[], float]]):
    """Allows tests to inject a mock clock for testing cache expiration."""
    global _CLOCK_OVERRIDE
    _CLOCK_OVERRIDE = clock_fn


def clear_fhir_cache():
    """Clears the in-memory FHIR cache."""
    global _CACHE
    _CACHE.clear()


class FHIRError(Exception):
    """Custom exception for structured FHIR client error codes."""
    def __init__(self, error_code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def _get_base_url(base_url: Optional[str] = None) -> str:
    if base_url:
        return base_url.rstrip("/")
    env_url = os.environ.get("FHIR_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    return DEFAULT_FHIR_BASE_URL.rstrip("/")


def fhir_get(
    base: Optional[str],
    path: str,
    params: Optional[Dict[str, Any]] = None,
    timeout_connect: float = 5.0,
    timeout_read: float = 10.0,
    max_retries: int = 2,
    use_cache: bool = True,
) -> Any:
    """
    Unified FHIR GET retriever.
    - Routes `sim://` to in-process fhir_sim.
    - Uses in-memory cache with 30s TTL.
    - Retries only for timeouts, connection errors, and HTTP 502/503/504 (up to max_retries).
    - Caps response body to 2MB.
    - Validates JSON format.
    """
    resolved_base = _get_base_url(base)
    clean_path = path.lstrip("/")
    
    # 1. Check in-memory cache
    cache_key = None
    if use_cache:
        param_items = tuple(sorted((str(k), str(v)) for k, v in (params or {}).items()))
        cache_key = (resolved_base, clean_path, param_items)
        if cache_key in _CACHE:
            cached_time, cached_val = _CACHE[cache_key]
            if _get_time() - cached_time < DEFAULT_CACHE_TTL:
                return cached_val
            else:
                _CACHE.pop(cache_key, None)

    # 2. Simulator route
    if resolved_base.startswith("sim://"):
        status_code, body = fhir_sim.handle(clean_path, params=params)
        if status_code == 404:
            raise FHIRError("ehr_patient_not_found", "Patient not found in this EHR", status_code=404)
        if status_code == 403:
            raise FHIRError("ehr_forbidden", "Access forbidden by EHR", status_code=403)
        if status_code >= 400:
            raise FHIRError("ehr_bad_response", f"Simulator returned HTTP {status_code}", status_code=502)
        
        if use_cache and cache_key:
            _CACHE[cache_key] = (_get_time(), body)
        return body

    # 3. HTTP route with bounded retries and timeouts
    url = f"{resolved_base}/{clean_path}"
    headers = {"Accept": "application/fhir+json, application/json", "User-Agent": "ChronicCare-AI/1.0"}
    timeout_tuple = (timeout_connect, timeout_read)

    attempts = 0
    backoffs = [0.5, 1.0]

    while True:
        attempts += 1
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout_tuple, stream=True)
            
            # 4xx client errors: never retried
            if resp.status_code == 404:
                raise FHIRError("ehr_patient_not_found", "Patient not found in this EHR", status_code=404)
            if resp.status_code in (401, 403):
                raise FHIRError("ehr_forbidden", "Access forbidden by EHR server", status_code=403)
            if 400 <= resp.status_code < 500:
                raise FHIRError("ehr_bad_response", f"EHR returned client error HTTP {resp.status_code}", status_code=502)

            # 5xx server errors: retryable
            if resp.status_code in (502, 503, 504):
                if attempts <= max_retries:
                    time.sleep(backoffs[attempts - 1])
                    continue
                raise FHIRError("ehr_unreachable", f"EHR unavailable (HTTP {resp.status_code})", status_code=502)
            
            if resp.status_code >= 500:
                if attempts <= max_retries:
                    time.sleep(backoffs[attempts - 1])
                    continue
                raise FHIRError("ehr_unreachable", f"EHR server error HTTP {resp.status_code}", status_code=502)

            # Enforce 2MB size cap and parse JSON
            data = None
            if hasattr(resp, "content") and isinstance(resp.content, (bytes, bytearray)):
                if len(resp.content) > MAX_RESPONSE_BYTES:
                    raise FHIRError("ehr_bad_response", "EHR response exceeded maximum allowable size (2MB)", status_code=502)
                try:
                    data = json.loads(resp.content.decode("utf-8"))
                except Exception as e:
                    raise FHIRError("ehr_bad_response", f"EHR returned non-JSON content: {e}", status_code=502)
            elif hasattr(resp, "iter_content") and callable(resp.iter_content):
                try:
                    content = bytearray()
                    for chunk in resp.iter_content(chunk_size=65536):
                        if isinstance(chunk, (bytes, bytearray)):
                            content.extend(chunk)
                        elif isinstance(chunk, str):
                            content.extend(chunk.encode("utf-8"))
                        if len(content) > MAX_RESPONSE_BYTES:
                            raise FHIRError("ehr_bad_response", "EHR response exceeded maximum allowable size (2MB)", status_code=502)
                    if content:
                        data = json.loads(content.decode("utf-8"))
                except FHIRError:
                    raise
                except Exception:
                    data = None

            if data is None and hasattr(resp, "json") and callable(resp.json):
                try:
                    data = resp.json()
                except Exception as e:
                    raise FHIRError("ehr_bad_response", f"EHR returned non-JSON content: {e}", status_code=502)

            if not isinstance(data, dict):
                raise FHIRError("ehr_bad_response", "EHR returned invalid resource structure", status_code=502)

            if use_cache and cache_key:
                _CACHE[cache_key] = (_get_time(), data)
            return data

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempts <= max_retries:
                time.sleep(backoffs[attempts - 1])
                continue
            raise FHIRError("ehr_unreachable", "The test server is not responding.", status_code=502)
        except requests.exceptions.HTTPError as e:
            resp = getattr(e, "response", None)
            if resp is not None:
                if resp.status_code == 404:
                    raise FHIRError("ehr_patient_not_found", "Patient not found in this EHR", status_code=404)
                if resp.status_code in (401, 403):
                    raise FHIRError("ehr_forbidden", "Access forbidden by EHR server", status_code=403)
                if 400 <= resp.status_code < 500:
                    raise FHIRError("ehr_bad_response", f"EHR returned client error HTTP {resp.status_code}", status_code=502)
                if resp.status_code in (502, 503, 504) or resp.status_code >= 500:
                    if attempts <= max_retries:
                        time.sleep(backoffs[attempts - 1])
                        continue
                    raise FHIRError("ehr_unreachable", f"EHR server error HTTP {resp.status_code}", status_code=502)
            raise FHIRError("ehr_unreachable", f"EHR HTTP error: {e}", status_code=502)
        except FHIRError:
            raise
        except Exception as e:
            raise FHIRError("ehr_unreachable", f"EHR connection failed: {e}", status_code=502)


def check_fhir_metadata(base_url: Optional[str] = None, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Checks the FHIR server metadata (CapabilityStatement) endpoint with no retries.
    """
    return fhir_get(base_url, "metadata", timeout_connect=timeout, timeout_read=timeout, max_retries=0, use_cache=False)


def search_fhir_patients(count: int = 10, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Searches for Patient resources on the FHIR server up to `count`.
    """
    bundle = fhir_get(base_url, "Patient", params={"_count": count})
    entries = bundle.get("entry", []) if isinstance(bundle, dict) else []
    return [entry["resource"] for entry in entries if "resource" in entry]


def get_fhir_patient(patient_id: str, base_url: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    """
    Retrieves a Patient resource by patient ID.
    """
    return fhir_get(base_url, f"Patient/{patient_id}", timeout_read=float(timeout))


def get_fhir_observations(patient_id: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves Observation resources for a given patient ID.
    """
    bundle = fhir_get(base_url, "Observation", params={"patient": patient_id, "_count": 100, "_sort": "-date"})
    entries = bundle.get("entry", []) if isinstance(bundle, dict) else []
    return [entry["resource"] for entry in entries if "resource" in entry]


def get_fhir_medications(patient_id: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves MedicationRequest resources for a given patient ID.
    """
    bundle = fhir_get(base_url, "MedicationRequest", params={"patient": patient_id, "_count": 100})
    entries = bundle.get("entry", []) if isinstance(bundle, dict) else []
    return [entry["resource"] for entry in entries if "resource" in entry]


def get_fhir_conditions(patient_id: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves Condition resources for a given patient ID.
    """
    bundle = fhir_get(base_url, "Condition", params={"patient": patient_id, "_count": 100})
    entries = bundle.get("entry", []) if isinstance(bundle, dict) else []
    return [entry["resource"] for entry in entries if "resource" in entry]
