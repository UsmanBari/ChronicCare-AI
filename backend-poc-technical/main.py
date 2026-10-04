"""
FastAPI Backend Application for ChronicCare AI

Wraps the core deterministic Reconciliation and Verification agents in HTTP endpoints:
- POST /api/reconcile: Wraps reconcile_bundles() from agents/reconciliation_agent.py
- POST /api/verify: Wraps verify_reconciliation() from agents/verification_agent.py
- GET /api/health: Health check endpoint
- GET /api/llm/health: LLM connectivity check
- POST /api/auth/session: Authenticate and session init for Firebase users
- GET /api/me: Retrieve current authenticated user profile
- POST /api/admin/users/{user_id}/role: Update user role (admin only)
- GET /api/admin/audit: Retrieve immutable audit logs (admin only)

Note: The underlying algorithmic reconciliation and verification agents remain unchanged
from the validated technical proof-of-concept.
"""

import os
import re
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, status, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from data_sources.models import (
    NormalizedPatient,
    NormalizedObservation,
    NormalizedMedication,
)
from agents.reconciliation_agent import (
    reconcile_bundles,
    ReconciliationResult,
    ObservationComparison,
    MedicationComparison,
)
from agents.verification_agent import (
    verify_reconciliation,
    VerificationResult,
)
from llm.groq_client import is_configured, get_configured_model, chat
from auth.firebase_verify import verify_firebase_token, AuthError, get_firebase_project_id
from data_sources.fhir_client import get_fhir_patient
from data_sources.app_store import (
    migrate,
    get_user_by_id,
    create_user,
    update_user_role,
    update_user_last_login,
    append_audit,
    get_audit_logs,
    get_patient_profile,
    upsert_patient_profile,
    set_patient_consent,
    get_enabled_ehr_systems,
    get_ehr_system_by_id,
    get_active_ehr_connection,
    get_active_connection_by_external_id,
    record_ehr_connection,
    revoke_ehr_connection,
    ALLOWED_CONDITIONS,
    ALLOWED_LANGUAGES,
    _utc_now_iso,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes app database schema on startup if configured."""
    try:
        migrate()
    except Exception as e:
        logger.warning("Database migration skipped on startup: %s", str(e))
    yield


app = FastAPI(
    title="ChronicCare AI - Clinical Reconciliation & Verification API",
    version="0.1.0",
    description="FastAPI service wrapping deterministic multi-source reconciliation and clinical consistency verification.",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PYDANTIC REQUEST / RESPONSE SCHEMAS
# =============================================================================

class PatientModel(BaseModel):
    patient_id: str
    name: str
    date_of_birth: Optional[str] = None


class ObservationModel(BaseModel):
    patient_id: str
    observation_type: str
    value: Optional[float] = None
    unit: str
    timestamp: str
    source: str
    source_record_id: str


class MedicationModel(BaseModel):
    patient_id: str
    medication_name: str
    status: str
    dosage: str
    timestamp: str
    source: str
    source_record_id: str


class PatientBundleModel(BaseModel):
    patient: PatientModel
    observations: List[ObservationModel] = Field(default_factory=list)
    medications: List[MedicationModel] = Field(default_factory=list)


class ReconcileRequest(BaseModel):
    bundle_a: PatientBundleModel
    bundle_b: PatientBundleModel


class ObservationComparisonModel(BaseModel):
    observation_type: str
    value_a: Optional[float] = None
    value_b: Optional[float] = None
    unit_a: Optional[str] = None
    unit_b: Optional[str] = None
    source_a: Optional[str] = None
    source_b: Optional[str] = None
    source_record_id_a: Optional[str] = None
    source_record_id_b: Optional[str] = None
    timestamp_a: Optional[str] = None
    timestamp_b: Optional[str] = None
    status: str
    delta: Optional[float] = None


class MedicationComparisonModel(BaseModel):
    medication_name: str
    status_a: Optional[str] = None
    status_b: Optional[str] = None
    dosage_a: Optional[str] = None
    dosage_b: Optional[str] = None
    source_a: Optional[str] = None
    source_b: Optional[str] = None
    source_record_id_a: Optional[str] = None
    source_record_id_b: Optional[str] = None
    comparison_status: str


class ReconciliationResultModel(BaseModel):
    patient_id: str
    observation_comparisons: List[ObservationComparisonModel]
    medication_comparisons: List[MedicationComparisonModel]
    summary: Dict[str, int]


class VerifyRequest(BaseModel):
    reconciliation_result: Optional[ReconciliationResultModel] = None
    bundle_a: Optional[PatientBundleModel] = None
    bundle_b: Optional[PatientBundleModel] = None
    origins: Optional[Dict[str, str]] = None


# --- Auth & Profile Schemas ---

class RoleUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    role: str


class SessionResponse(BaseModel):
    user_id: str
    email: str
    role: str
    display_name: Optional[str] = None
    status: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    display_name: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
    mode: Optional[str] = None


class AuditLogRow(BaseModel):
    id: int
    ts: str
    actor_user_id: Optional[str] = None
    action: str
    target: Optional[str] = None
    outcome: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class ProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    conditions: List[str]
    on_insulin_or_sulfonylurea: bool
    language: str = "en"

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("conditions must contain at least one condition.")
        cleaned = []
        for c in v:
            c_str = str(c).strip().lower()
            if c_str not in ALLOWED_CONDITIONS:
                raise ValueError(f"Invalid condition '{c}'. Allowed conditions: {sorted(list(ALLOWED_CONDITIONS))}")
            if c_str not in cleaned:
                cleaned.append(c_str)
        return cleaned

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        clean = str(v).strip().lower()
        if clean not in ALLOWED_LANGUAGES:
            raise ValueError(f"Invalid language '{v}'. Allowed languages: {sorted(list(ALLOWED_LANGUAGES))}")
        return clean


class ProfileResponse(BaseModel):
    user_id: str
    conditions: List[str]
    on_insulin_or_sulfonylurea: bool
    language: str
    consent_granted_at: Optional[str] = None
    consent_revoked_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    granted: bool


class EHRSystemResponse(BaseModel):
    ehr_system_id: str
    display_name: str


PATIENT_ID_REGEX = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")


class EHRConnectRequest(BaseModel):
    model_config = {"extra": "forbid"}
    ehr_system_id: str
    external_patient_id: str

    @field_validator("external_patient_id")
    @classmethod
    def validate_external_patient_id(cls, v: str) -> str:
        clean = str(v).strip()
        if not PATIENT_ID_REGEX.match(clean):
            raise ValueError("external_patient_id must match pattern ^[A-Za-z0-9\\-.]{1,64}$")
        return clean


class EHRConnectionInfo(BaseModel):
    ehr_system_id: str
    display_name: str
    masked_patient_id: str
    linked_at: str
    last_verified_at: Optional[str] = None


class EHRConnectionResponse(BaseModel):
    mode: str
    connection: Optional[EHRConnectionInfo] = None
    message: Optional[str] = None


# =============================================================================
# HELPER PARSING & AUTH FUNCTIONS
# =============================================================================

def get_demo_role_map() -> Dict[str, str]:
    """
    Parses DEMO_ROLE_MAP environment variable (format: email:role,email:role).
    Ignores malformed entries and logs a safe warning without revealing emails or values.
    """
    raw = os.environ.get("DEMO_ROLE_MAP", "").strip()
    if not raw:
        return {}

    role_map: Dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 2:
            logger.warning("Malformed entry encountered in DEMO_ROLE_MAP configuration (ignored).")
            continue
        email = parts[0].strip().lower()
        role = parts[1].strip().lower()
        if role in ("patient", "provider", "admin") and email:
            role_map[email] = role
        else:
            logger.warning("Invalid role or email format in DEMO_ROLE_MAP configuration (ignored).")
    return role_map


def extract_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Extracts and validates Bearer token from Authorization header (rejects > 4 KB)."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if len(authorization) > 4096:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return token


def get_current_user(token: str = Depends(extract_bearer_token)) -> Dict[str, Any]:
    """
    Dependency that verifies Firebase token and retrieves active user profile from DB.
    Raises:
    - 503 if FIREBASE_PROJECT_ID is not configured or cert service is down.
    - 401 if token is missing/invalid/expired.
    - 403 if user is not found or is disabled.
    """
    try:
        claims = verify_firebase_token(token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    user_id = claims["uid"]
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account not found or not registered",
        )
    if user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return user


def require_role(*allowed_roles: str):
    """Dependency factory ensuring user has one of the required roles."""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            append_audit(
                actor_user_id=current_user.get("user_id"),
                action="role_denied",
                target=None,
                outcome="denied",
                detail={"user_role": user_role, "required_roles": list(allowed_roles)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Insufficient privileges",
            )
        return current_user
    return role_checker


def _bundle_model_to_domain(bundle: PatientBundleModel) -> Dict[str, Any]:
    """Converts Pydantic PatientBundleModel into dataclass models expected by reconcile_bundles."""
    patient = NormalizedPatient(
        patient_id=bundle.patient.patient_id,
        name=bundle.patient.name,
        date_of_birth=bundle.patient.date_of_birth,
    )
    observations = [
        NormalizedObservation(
            patient_id=obs.patient_id,
            observation_type=obs.observation_type,
            value=obs.value,
            unit=obs.unit,
            timestamp=obs.timestamp,
            source=obs.source,
            source_record_id=obs.source_record_id,
        )
        for obs in bundle.observations
    ]
    medications = [
        NormalizedMedication(
            patient_id=med.patient_id,
            medication_name=med.medication_name,
            status=med.status,
            dosage=med.dosage,
            timestamp=med.timestamp,
            source=med.source,
            source_record_id=med.source_record_id,
        )
        for med in bundle.medications
    ]
    return {
        "patient": patient,
        "observations": observations,
        "medications": medications,
    }


def _recon_model_to_domain(recon_model: ReconciliationResultModel) -> ReconciliationResult:
    """Converts Pydantic ReconciliationResultModel to domain dataclass ReconciliationResult."""
    obs_comps = [
        ObservationComparison(
            observation_type=o.observation_type,
            value_a=o.value_a,
            value_b=o.value_b,
            unit_a=o.unit_a,
            unit_b=o.unit_b,
            source_a=o.source_a,
            source_b=o.source_b,
            source_record_id_a=o.source_record_id_a,
            source_record_id_b=o.source_record_id_b,
            timestamp_a=o.timestamp_a,
            timestamp_b=o.timestamp_b,
            status=o.status,
            delta=o.delta,
        )
        for o in recon_model.observation_comparisons
    ]
    med_comps = [
        MedicationComparison(
            medication_name=m.medication_name,
            status_a=m.status_a,
            status_b=m.status_b,
            dosage_a=m.dosage_a,
            dosage_b=m.dosage_b,
            source_a=m.source_a,
            source_b=m.source_b,
            source_record_id_a=m.source_record_id_a,
            source_record_id_b=m.source_record_id_b,
            comparison_status=m.comparison_status,
        )
        for m in recon_model.medication_comparisons
    ]
    return ReconciliationResult(
        patient_id=recon_model.patient_id,
        observation_comparisons=obs_comps,
        medication_comparisons=med_comps,
        summary=recon_model.summary,
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "chroniccare-backend",
        "version": "0.1.0",
    }


@app.get("/api/llm/health", tags=["LLM"])
def llm_health_check(ping: bool = False):
    """
    Checks LLM integration health.
    - Default (ping=False): Returns {configured: bool, model: str|null} without calling Groq.
    - With ping=True: Makes a minimal completion and returns {ok: bool, latency_ms: int}.
    Never reveals API keys.
    """
    configured = is_configured()
    model = get_configured_model()

    if not ping:
        return {
            "configured": configured,
            "model": model,
        }

    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not configured (missing GROQ_API_KEY or GROQ_MODEL).",
        )

    start_time = time.perf_counter()
    try:
        chat(
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            timeout=10.0,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "ok": True,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq ping failed: {str(e)}",
        )


@app.post("/api/auth/session", response_model=SessionResponse, tags=["Auth"])
def auth_session_endpoint(token: str = Depends(extract_bearer_token)):
    """
    Verifies Firebase token and initializes user session.
    - If user does not exist: creates a new user row (role seeded from DEMO_ROLE_MAP, otherwise 'patient').
    - If user exists: updates last_login_at and records login audit.
    - Idempotent.
    """
    try:
        claims = verify_firebase_token(token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    user_id = claims["uid"]
    raw_email = claims.get("email", "")
    email = str(raw_email).strip().lower() if raw_email else f"{user_id}@anonymous.local"
    display_name = claims.get("name")

    user = get_user_by_id(user_id)
    if not user:
        role_map = get_demo_role_map()
        assigned_role = role_map.get(email, "patient")
        user = create_user(
            user_id=user_id,
            email=email,
            role=assigned_role,
            display_name=display_name,
            status="active",
        )
        append_audit(
            actor_user_id=user_id,
            action="user_registered",
            target=user_id,
            outcome="ok",
            detail={"role": assigned_role},
        )
    else:
        if user.get("status") != "active":
            append_audit(
                actor_user_id=user_id,
                action="login_blocked",
                target=user_id,
                outcome="denied",
                detail={"reason": "disabled_account"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        user = update_user_last_login(user_id)
        append_audit(
            actor_user_id=user_id,
            action="login",
            target=user_id,
            outcome="ok",
            detail={},
        )

    return SessionResponse(
        user_id=user["user_id"],
        email=user["email"],
        role=user["role"],
        display_name=user.get("display_name"),
        status=user.get("status", "active"),
    )


@app.get("/api/me", response_model=UserResponse, tags=["Auth"])
def get_me_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated user profile with derived mode for patients."""
    mode = None
    if current_user.get("role") == "patient":
        active_conn = get_active_ehr_connection(current_user["user_id"])
        mode = "connected" if active_conn else "isolated"

    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        role=current_user["role"],
        display_name=current_user.get("display_name"),
        status=current_user.get("status", "active"),
        created_at=current_user.get("created_at"),
        last_login_at=current_user.get("last_login_at"),
        mode=mode,
    )


# =============================================================================
# PATIENT PROFILE & CONSENT ENDPOINTS
# =============================================================================

@app.get("/api/me/profile", response_model=ProfileResponse, tags=["Patient Profile"])
def get_profile_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """Retrieves patient clinical profile and consent status (patient only)."""
    user_id = current_user["user_id"]
    profile = get_patient_profile(user_id)
    if not profile:
        return ProfileResponse(
            user_id=user_id,
            conditions=[],
            on_insulin_or_sulfonylurea=False,
            language="en",
            consent_granted_at=None,
            consent_revoked_at=None,
            updated_at=None,
        )
    return ProfileResponse(
        user_id=profile["user_id"],
        conditions=profile["conditions"],
        on_insulin_or_sulfonylurea=profile["on_insulin_or_sulfonylurea"],
        language=profile["language"],
        consent_granted_at=profile.get("consent_granted_at"),
        consent_revoked_at=profile.get("consent_revoked_at"),
        updated_at=profile.get("updated_at"),
    )


@app.put("/api/me/profile", response_model=ProfileResponse, tags=["Patient Profile"])
def update_profile_endpoint(
    body: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Updates patient profile conditions, insulin/sulfonylurea flag, and language (patient only)."""
    user_id = current_user["user_id"]
    updated = upsert_patient_profile(
        user_id=user_id,
        conditions=body.conditions,
        on_insulin_or_sulfonylurea=body.on_insulin_or_sulfonylurea,
        language=body.language,
    )
    append_audit(
        actor_user_id=user_id,
        action="profile_updated",
        target=user_id,
        outcome="ok",
        detail={
            "conditions": updated["conditions"],
            "language": updated["language"],
            "on_insulin_or_sulfonylurea": updated["on_insulin_or_sulfonylurea"],
        },
    )
    return ProfileResponse(
        user_id=updated["user_id"],
        conditions=updated["conditions"],
        on_insulin_or_sulfonylurea=updated["on_insulin_or_sulfonylurea"],
        language=updated["language"],
        consent_granted_at=updated.get("consent_granted_at"),
        consent_revoked_at=updated.get("consent_revoked_at"),
        updated_at=updated.get("updated_at"),
    )


@app.post("/api/me/consent", response_model=ProfileResponse, tags=["Patient Profile"])
def set_consent_endpoint(
    body: ConsentRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Explicitly grants or revokes patient consent (patient only)."""
    user_id = current_user["user_id"]
    updated = set_patient_consent(user_id=user_id, granted=body.granted)
    action = "consent_granted" if body.granted else "consent_revoked"
    append_audit(
        actor_user_id=user_id,
        action=action,
        target=user_id,
        outcome="ok",
        detail={},
    )
    return ProfileResponse(
        user_id=updated["user_id"],
        conditions=updated["conditions"],
        on_insulin_or_sulfonylurea=updated["on_insulin_or_sulfonylurea"],
        language=updated["language"],
        consent_granted_at=updated.get("consent_granted_at"),
        consent_revoked_at=updated.get("consent_revoked_at"),
        updated_at=updated.get("updated_at"),
    )


# =============================================================================
# EHR REGISTRY & CONNECTION ENDPOINTS
# =============================================================================

@app.get("/api/ehr/systems", response_model=List[EHRSystemResponse], tags=["EHR Connection"])
def get_ehr_systems_endpoint():
    """Returns enabled EHR systems (id and display name only, never URLs)."""
    systems = get_enabled_ehr_systems()
    return [
        EHRSystemResponse(
            ehr_system_id=s["ehr_system_id"],
            display_name=s["display_name"],
        )
        for s in systems
    ]


@app.post("/api/ehr/connect", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def connect_ehr_endpoint(
    body: EHRConnectRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """
    Connects patient account to an external patient record in a registered EHR system.
    Requires active consent. Checks live FHIR patient record deterministically.
    """
    user_id = current_user["user_id"]
    masked_id = "..." + body.external_patient_id[-4:]

    # 1. Consent check: patient must have granted consent and not revoked it
    profile = get_patient_profile(user_id)
    if not profile or not profile.get("consent_granted_at") or profile.get("consent_revoked_at"):
        append_audit(
            actor_user_id=user_id,
            action="ehr_connect_denied",
            target=body.ehr_system_id,
            outcome="denied",
            detail={"reason": "consent_required", "masked_patient_id": masked_id},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent is required before connecting an EHR system",
        )

    # 2. EHR System verification from database (SSRF prevention: URL is never client-supplied)
    ehr_system = get_ehr_system_by_id(body.ehr_system_id)
    if not ehr_system or not ehr_system.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EHR system not found or disabled",
        )

    # 3. Invariant: external_patient_id may be active for at most one user
    conflict = get_active_connection_by_external_id(body.ehr_system_id, body.external_patient_id)
    if conflict and conflict.get("user_id") != user_id:
        append_audit(
            actor_user_id=user_id,
            action="ehr_connect_conflict",
            target=body.ehr_system_id,
            outcome="denied",
            detail={"ehr_system_id": body.ehr_system_id, "masked_patient_id": masked_id},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This EHR patient is already linked to another account",
        )

    # 4. Live FHIR verification with timeout <= 10s
    base_url = ehr_system["fhir_base_url"]
    try:
        get_fhir_patient(patient_id=body.external_patient_id, base_url=base_url, timeout=10)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            record_ehr_connection(
                connection_id=str(uuid.uuid4()),
                user_id=user_id,
                ehr_system_id=body.ehr_system_id,
                external_patient_id=body.external_patient_id,
                status="failed",
                last_error_code="not_found",
            )
            append_audit(
                actor_user_id=user_id,
                action="ehr_connect_failed",
                target=body.ehr_system_id,
                outcome="error",
                detail={"ehr_system_id": body.ehr_system_id, "error_code": "not_found", "masked_patient_id": masked_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found in this EHR",
            )
        else:
            record_ehr_connection(
                connection_id=str(uuid.uuid4()),
                user_id=user_id,
                ehr_system_id=body.ehr_system_id,
                external_patient_id=body.external_patient_id,
                status="failed",
                last_error_code="unavailable",
            )
            append_audit(
                actor_user_id=user_id,
                action="ehr_connect_failed",
                target=body.ehr_system_id,
                outcome="error",
                detail={"ehr_system_id": body.ehr_system_id, "error_code": "unavailable", "masked_patient_id": masked_id},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="EHR unavailable",
            )
    except requests.exceptions.RequestException:
        record_ehr_connection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            ehr_system_id=body.ehr_system_id,
            external_patient_id=body.external_patient_id,
            status="failed",
            last_error_code="unavailable",
        )
        append_audit(
            actor_user_id=user_id,
            action="ehr_connect_failed",
            target=body.ehr_system_id,
            outcome="error",
            detail={"ehr_system_id": body.ehr_system_id, "error_code": "unavailable", "masked_patient_id": masked_id},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="EHR unavailable",
        )

    # 5. Connect Success: store active connection (replaces previous active connection)
    now_iso = _utc_now_iso()
    conn_id = str(uuid.uuid4())
    record = record_ehr_connection(
        connection_id=conn_id,
        user_id=user_id,
        ehr_system_id=body.ehr_system_id,
        external_patient_id=body.external_patient_id,
        status="active",
        last_verified_at=now_iso,
    )
    append_audit(
        actor_user_id=user_id,
        action="ehr_connected",
        target=body.ehr_system_id,
        outcome="ok",
        detail={"ehr_system_id": body.ehr_system_id, "masked_patient_id": masked_id},
    )

    return EHRConnectionResponse(
        mode="connected",
        connection=EHRConnectionInfo(
            ehr_system_id=body.ehr_system_id,
            display_name=ehr_system["display_name"],
            masked_patient_id=masked_id,
            linked_at=record["linked_at"],
            last_verified_at=now_iso,
        ),
    )


@app.get("/api/ehr/connection", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def get_ehr_connection_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves current patient EHR connection status and masked identifiers."""
    active = get_active_ehr_connection(current_user["user_id"])
    if not active:
        return EHRConnectionResponse(mode="isolated", connection=None)

    masked_id = "..." + active["external_patient_id"][-4:]
    return EHRConnectionResponse(
        mode="connected",
        connection=EHRConnectionInfo(
            ehr_system_id=active["ehr_system_id"],
            display_name=active.get("display_name") or "",
            masked_patient_id=masked_id,
            linked_at=active["linked_at"],
            last_verified_at=active.get("last_verified_at"),
        ),
    )


@app.delete("/api/ehr/connection", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def delete_ehr_connection_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """Revokes active EHR connection and switches patient mode to isolated (patient only)."""
    user_id = current_user["user_id"]
    revoke_ehr_connection(user_id)
    append_audit(
        actor_user_id=user_id,
        action="ehr_disconnected",
        target=user_id,
        outcome="ok",
        detail={},
    )
    return EHRConnectionResponse(
        mode="isolated",
        connection=None,
        message="EHR connection revoked",
    )


@app.post("/api/admin/users/{user_id}/role", response_model=UserResponse, tags=["Admin"])
def update_user_role_endpoint(
    user_id: str,
    body: RoleUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role("admin")),
):
    """
    Updates the role of a target user (Admin only).
    Admin cannot change their own role.
    """
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot change their own role",
        )

    clean_role = body.role.strip().lower()
    if clean_role not in ("patient", "provider", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'patient', 'provider', or 'admin'.",
        )

    target_user = get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = update_user_role(user_id, clean_role)
    append_audit(
        actor_user_id=current_user["user_id"],
        action="role_updated",
        target=user_id,
        outcome="ok",
        detail={"new_role": clean_role},
    )
    return UserResponse(
        user_id=updated_user["user_id"],
        email=updated_user["email"],
        role=updated_user["role"],
        display_name=updated_user.get("display_name"),
        status=updated_user.get("status", "active"),
        created_at=updated_user.get("created_at"),
        last_login_at=updated_user.get("last_login_at"),
    )


@app.get("/api/admin/audit", response_model=List[AuditLogRow], tags=["Admin"])
def get_audit_endpoint(
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_role("admin")),
):
    """Retrieves newest audit log records (Admin only)."""
    logs = get_audit_logs(limit=limit)
    return logs


@app.post("/api/reconcile", tags=["Reconciliation"])
def reconcile_endpoint(request: ReconcileRequest):
    """
    Reconciles two patient bundles (prior history vs incoming check-in).
    Wraps deterministic reconcile_bundles() agent.
    """
    try:
        domain_bundle_a = _bundle_model_to_domain(request.bundle_a)
        domain_bundle_b = _bundle_model_to_domain(request.bundle_b)
        result = reconcile_bundles(domain_bundle_a, domain_bundle_b)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation error: {str(e)}",
        )


@app.post("/api/verify", tags=["Verification"])
def verify_endpoint(request: VerifyRequest):
    """
    Evaluates trust levels, severity, and review necessity on reconciled clinical data.
    Wraps deterministic verify_reconciliation() agent.
    """
    try:
        if request.reconciliation_result is not None:
            recon_result = _recon_model_to_domain(request.reconciliation_result)
        elif request.bundle_a is not None and request.bundle_b is not None:
            domain_bundle_a = _bundle_model_to_domain(request.bundle_a)
            domain_bundle_b = _bundle_model_to_domain(request.bundle_b)
            recon_result = reconcile_bundles(domain_bundle_a, domain_bundle_b)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'reconciliation_result' or both 'bundle_a' and 'bundle_b' must be provided.",
            )

        verif_result = verify_reconciliation(recon_result, origins=request.origins)
        return verif_result.to_dict()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}",
        )
