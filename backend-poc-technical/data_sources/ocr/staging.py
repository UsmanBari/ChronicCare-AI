"""
In-Memory Ephemeral Staging Store for OCR Uploads.
Ensures zero disk persistence, 30-minute TTL, and max 3 pending uploads per user.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# Max pending uploads allowed per user before oldest is dropped
MAX_PENDING_PER_USER = 3

# TTL for pending uploads before expiry
STAGING_TTL_MINUTES = 30

_STAGING_STORE: Dict[str, Dict[str, Any]] = {}


def _clean_expired() -> None:
    """Removes uploads that exceed STAGING_TTL_MINUTES."""
    now = datetime.now(timezone.utc)
    expired_ids = [
        uid for uid, item in _STAGING_STORE.items()
        if now - item["created_at"] > timedelta(minutes=STAGING_TTL_MINUTES)
    ]
    for uid in expired_ids:
        _STAGING_STORE.pop(uid, None)


def stage_upload(user_id: str, extracted_data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Stages an OCR upload in memory.
    Enforces TTL cleanup and per-user max 3 pending uploads limit.
    Returns generated upload_id.
    """
    _clean_expired()

    clean_uid = str(user_id).strip()
    now = datetime.now(timezone.utc)

    # Find existing pending uploads for this user
    user_uploads = [
        (item_id, item)
        for item_id, item in _STAGING_STORE.items()
        if item.get("user_id") == clean_uid
    ]

    # If at or exceeding limit, prune oldest
    if len(user_uploads) >= MAX_PENDING_PER_USER:
        user_uploads.sort(key=lambda x: x[1]["created_at"])
        excess = len(user_uploads) - MAX_PENDING_PER_USER + 1
        for i in range(excess):
            oldest_id = user_uploads[i][0]
            _STAGING_STORE.pop(oldest_id, None)

    upload_id = str(uuid.uuid4())
    _STAGING_STORE[upload_id] = {
        "upload_id": upload_id,
        "user_id": clean_uid,
        "filename": filename or "document.jpg",
        "created_at": now,
        "extracted": extracted_data,
        "status": "pending",
    }
    return upload_id


def get_staged_upload(upload_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a staged upload if it exists, is not expired, and belongs to user_id.
    """
    _clean_expired()
    item = _STAGING_STORE.get(str(upload_id).strip())
    if not item:
        return None
    if item.get("user_id") != str(user_id).strip():
        return None
    return item


def remove_staged_upload(upload_id: str) -> bool:
    """
    Removes a staged upload after confirmation or cancellation.
    """
    return _STAGING_STORE.pop(str(upload_id).strip(), None) is not None


def get_user_pending_count(user_id: str) -> int:
    """Returns number of active pending uploads for a user."""
    _clean_expired()
    clean_uid = str(user_id).strip()
    return sum(1 for item in _STAGING_STORE.values() if item.get("user_id") == clean_uid)


def clear_all_staged_uploads_for_testing() -> None:
    """Hermetic reset helper for tests."""
    _STAGING_STORE.clear()
