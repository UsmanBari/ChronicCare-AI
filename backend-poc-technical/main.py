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
import time
import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
from data_sources.app_store import (
    migrate,
    get_user_by_id,
    create_user,
    update_user_role,
    update_user_last_login,
    append_audit,
    get_audit_logs,
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


# --- Auth Schemas ---

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


class AuditLogRow(BaseModel):
    id: int
    ts: str
    actor_user_id: Optional[str] = None
    action: str
    target: Optional[str] = None
    outcome: str
    detail: Dict[str, Any] = Field(default_factory=dict)


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
    """Returns the authenticated user profile."""
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        role=current_user["role"],
        display_name=current_user.get("display_name"),
        status=current_user.get("status", "active"),
        created_at=current_user.get("created_at"),
        last_login_at=current_user.get("last_login_at"),
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
