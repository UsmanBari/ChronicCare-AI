"""
Firebase ID Token Verification Module.

Implements server-side verification of Google Firebase ID tokens using PyJWT
and Google's public x509 certificates.
Follows official Firebase third-party verification specification:
- RS256 algorithm only (strict rejection of 'none', HS256, etc.)
- Verification of 'kid' against Google's public key endpoint
- Verification of 'aud' against FIREBASE_PROJECT_ID
- Verification of 'iss' against https://securetoken.google.com/<FIREBASE_PROJECT_ID>
- Non-empty 'sub' (Firebase UID)
- Expiration and issued-at checks with max 60s leeway
- Response Cache-Control respect with clamp (5 min to 24 hours)
- Zero credential/token logging
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional
import requests
import jwt
from cryptography import x509

logger = logging.getLogger(__name__)

GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

# In-memory certificate cache
_KEY_CACHE: Dict[str, Any] = {
    "keys": {},
    "expires_at": 0.0,
}


class AuthError(Exception):
    """Exception raised for authentication errors with a safe public message."""
    def __init__(self, message: str = "Invalid or expired token", status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_firebase_project_id() -> Optional[str]:
    """Retrieves FIREBASE_PROJECT_ID from environment."""
    pid = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    return pid if pid else None


def _parse_max_age(cache_control: Optional[str]) -> int:
    """Extracts and clamps max-age from Cache-Control header (5 min .. 24 h)."""
    default_age = 3600  # 1 hour default
    if not cache_control:
        return default_age
    match = re.search(r"max-age=(\d+)", cache_control)
    if match:
        try:
            val = int(match.group(1))
            return max(300, min(val, 86400))
        except ValueError:
            pass
    return default_age


def fetch_google_public_keys(force_refresh: bool = False) -> Dict[str, str]:
    """
    Fetches and caches Google's public x509 certificates.
    If network fetch fails and cache is non-empty, falls back to cache.
    If network fetch fails and cache is empty, raises AuthError(503).
    """
    now = time.time()
    if not force_refresh and _KEY_CACHE["keys"] and now < _KEY_CACHE["expires_at"]:
        return _KEY_CACHE["keys"]

    try:
        response = requests.get(GOOGLE_CERTS_URL, timeout=10.0)
        if response.status_code == 200:
            keys = response.json()
            max_age = _parse_max_age(response.headers.get("Cache-Control"))
            _KEY_CACHE["keys"] = keys
            _KEY_CACHE["expires_at"] = now + max_age
            return keys
        else:
            logger.warning("Failed to fetch Google certs: HTTP %s", response.status_code)
    except Exception as e:
        logger.warning("Error connecting to Google certs service: %s", str(e))

    # Check fallback cache
    if _KEY_CACHE["keys"]:
        return _KEY_CACHE["keys"]

    raise AuthError("Authentication service unavailable", status_code=503)


def verify_firebase_token(token: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifies a Firebase ID token.
    
    Args:
        token: Raw JWT string.
        project_id: Optional project id override; defaults to FIREBASE_PROJECT_ID env var.
        
    Returns:
        Verified claims dictionary (e.g. {'uid': ..., 'email': ..., 'name': ...}).
        
    Raises:
        AuthError: On invalid token, missing configuration, or service unavailability.
    """
    pid = project_id or get_firebase_project_id()
    if not pid:
        raise AuthError("Authentication not configured", status_code=503)

    if not token or not isinstance(token, str):
        raise AuthError("Invalid or expired token", status_code=401)

    # 1. Read unverified header safely
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        raise AuthError("Invalid or expired token", status_code=401)

    # 2. Enforce RS256 algorithm only
    alg = header.get("alg")
    if alg != "RS256":
        raise AuthError("Invalid or expired token", status_code=401)

    kid = header.get("kid")
    if not kid or not isinstance(kid, str):
        raise AuthError("Invalid or expired token", status_code=401)

    # 3. Retrieve Google public certs (refresh once if kid is unknown)
    keys = fetch_google_public_keys(force_refresh=False)
    if kid not in keys:
        keys = fetch_google_public_keys(force_refresh=True)
        if kid not in keys:
            raise AuthError("Invalid or expired token", status_code=401)

    cert_str = keys[kid]
    try:
        cert_bytes = cert_str.encode("utf-8") if isinstance(cert_str, str) else cert_str
        cert_obj = x509.load_pem_x509_certificate(cert_bytes)
        public_key = cert_obj.public_key()
    except Exception:
        raise AuthError("Invalid or expired token", status_code=401)

    # 4. Verify signature and claims with PyJWT
    expected_issuer = f"https://securetoken.google.com/{pid}"
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=pid,
            issuer=expected_issuer,
            leeway=60,
            options={
                "require": ["exp", "iat", "aud", "iss", "sub"],
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
    except Exception:
        raise AuthError("Invalid or expired token", status_code=401)

    # 5. Check sub claim (Firebase UID)
    sub = claims.get("sub")
    if not sub or not str(sub).strip():
        raise AuthError("Invalid or expired token", status_code=401)
    claims["uid"] = str(sub).strip()

    # 6. Check auth_time if present
    auth_time = claims.get("auth_time")
    if auth_time is not None:
        try:
            if float(auth_time) > time.time() + 60:
                raise AuthError("Invalid or expired token", status_code=401)
        except (ValueError, TypeError):
            raise AuthError("Invalid or expired token", status_code=401)

    return claims
