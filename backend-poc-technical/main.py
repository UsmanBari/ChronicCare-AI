"""
FastAPI Backend Application for ChronicCare AI

Wraps the core deterministic Reconciliation and Verification agents in HTTP endpoints:
- POST /api/reconcile: Wraps reconcile_bundles() from agents/reconciliation_agent.py (provider/admin)
- POST /api/verify: Wraps verify_reconciliation() from agents/verification_agent.py (provider/admin)
- GET /api/health: Health check endpoint (public)
- GET /api/llm/health: LLM connectivity check (admin)
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
import copy
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, status, Header, Depends, Query, Request
from fastapi.responses import JSONResponse
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
from agents.adaptive_interview_agent import (
    InterviewState,
    adaptive_interview_node,
    build_checkin_bundle,
    build_checkin_origins,
    get_current_question,
    INTERVIEW_COMPLETE,
    run_stage1_red_flag_screen,
)
from agents.interview_v3_runner import (
    start_v3_session as v3_start_session,
    next_turn as v3_next_turn,
    finish_v3_session as v3_finish,
    finish_v3_session,
)
from agents.medication_confirmation import (
    start_medication_check,
    current_medication_question,
    advance_medication_check,
    restrict_to_asked,
    build_medication_bundle_items,
    build_medication_origins,
    MedicationCheckState,
    _norm,
)
from agents.triage_protocol import (
    evaluate_triggers,
    start_protocol,
    advance_protocol,
    current_protocol_question,
    current_protocol_step,
    compute_baseline,
    TriageProtocolState,
    _raise_level,
)
from data_sources.data_source import get_patient_bundle
from data_sources.local_store import (
    init_db as local_store_init_db,
    add_local_patient_if_missing,
    add_local_observation,
    get_local_observation_origins,
    get_local_medication_origins,
    get_local_medications,
    add_local_medication,
    update_local_medication,
    delete_local_medication,
    get_local_medication_by_id,
    get_local_observations,
    get_local_observation_by_id,
    delete_local_observation,
)
from llm.groq_client import is_configured, get_configured_model, chat
from auth.firebase_verify import verify_firebase_token, AuthError, get_firebase_project_id
from data_sources.medication_scope import select_chronic_care_medications
from data_sources.fhir_client import get_fhir_patient, fhir_get, check_fhir_metadata, FHIRError, clear_fhir_cache
from data_sources.fhir_sim import SAMPLE_PATIENTS
from data_sources.validation import (
    calculate_age,
    validate_date_of_birth,
    detect_pregnancy_statement,
)
from data_sources.app_store import (
    migrate,
    get_user_by_id,
    get_user_by_email,
    create_user,
    update_user_role,
    update_user_last_login,
    append_audit,
    get_audit_logs,
    get_patient_profile,
    upsert_patient_profile,
    update_patient_conditions_basis,
    set_patient_consent,
    set_patient_provider_notification_consent,
    create_allergy,
    get_allergies,
    get_allergy_by_id,
    delete_allergy,
    get_enabled_ehr_systems,
    get_ehr_system_by_id,
    get_active_ehr_connection,
    get_active_connection_by_external_id,
    record_ehr_connection,
    revoke_ehr_connection,
    create_checkin,
    get_checkin_by_id,
    update_checkin_state,
    apply_checkin_answer_atomic,
    create_checkin_result,
    get_checkin_result,
    get_user_checkins,
    get_user_baseline_history,
    get_provider_review_queue,
    append_review_action,
    get_review_actions,
    ALLOWED_CONDITIONS,
    ALLOWED_LANGUAGES,
    _utc_now_iso,
)

logger = logging.getLogger(__name__)


def get_cors_allowed_origins() -> List[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return [o for o in origins if o != "*"]


def validate_production_config():
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env == "production":
        db_backend = os.environ.get("DB_BACKEND", "").strip().lower()
        if db_backend != "mysql":
            raise RuntimeError("Production configuration error: DB_BACKEND must be set to 'mysql'")

        firebase_project = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
        if not firebase_project:
            raise RuntimeError("Production configuration error: FIREBASE_PROJECT_ID is required")

        cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
        if not cors_origins:
            raise RuntimeError("Production configuration error: CORS_ALLOWED_ORIGINS is required")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes app database schema on startup if configured and enforces production guards."""
    validate_production_config()
    try:
        migrate()
    except Exception as e:
        logger.warning("Database migration skipped on startup: %s", str(e))
    try:
        local_store_init_db()
        logger.info("local store ready")
    except Exception as e:
        logger.warning("Local store initialization skipped on startup: %s", str(e))
    yield


class DynamicCORSMiddleware(CORSMiddleware):
    def is_allowed_origin(self, origin: str) -> bool:
        if self.allow_all_origins:
            return True
        allowed = get_cors_allowed_origins()
        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(origin):
            return True
        return origin in allowed


app = FastAPI(
    title="ChronicCare AI - Clinical Reconciliation & Verification API",
    version="0.1.0",
    description="FastAPI service wrapping deterministic multi-source reconciliation and clinical consistency verification.",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    DynamicCORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
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


ALLOWED_SEX_AT_BIRTH = {"female", "male", "prefer_not_to_say"}
ALLOWED_PREGNANCY_STATUS = {"no", "yes", "not_sure", "not_applicable"}
ALLOWED_SMOKING_STATUS = {"never", "former", "current", "prefer_not_to_say"}
ALLOWED_COMORBIDITIES = {
    "kidney_disease",
    "heart_disease",
    "stroke_or_tia",
    "eye_problems",
    "nerve_or_foot_problems",
}


class ProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    conditions: Optional[List[str]] = None
    on_insulin_or_sulfonylurea: Optional[bool] = None
    language: Optional[str] = None
    date_of_birth: Optional[str] = None
    inclusion_confirmed: Optional[bool] = None
    sex_at_birth: Optional[str] = None
    pregnancy_status: Optional[str] = None
    voice_enabled: Optional[bool] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    diagnosis_year_diabetes: Optional[int] = None
    diagnosis_year_hypertension: Optional[int] = None
    smoking_status: Optional[str] = None
    comorbidities: Optional[Dict[str, bool]] = None

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if not v:
            raise ValueError("conditions list cannot be empty")
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
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip().lower()
        if clean not in ALLOWED_LANGUAGES:
            raise ValueError(f"Invalid language '{v}'. Allowed languages: {sorted(list(ALLOWED_LANGUAGES))}")
        return clean

    @field_validator("sex_at_birth")
    @classmethod
    def validate_sex_at_birth(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip().lower()
        if clean not in ALLOWED_SEX_AT_BIRTH:
            raise ValueError(f"Invalid sex_at_birth '{v}'. Allowed values: {sorted(list(ALLOWED_SEX_AT_BIRTH))}")
        return clean

    @field_validator("pregnancy_status")
    @classmethod
    def validate_pregnancy_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip().lower()
        if clean not in ALLOWED_PREGNANCY_STATUS:
            raise ValueError(f"Invalid pregnancy_status '{v}'. Allowed values: {sorted(list(ALLOWED_PREGNANCY_STATUS))}")
        return clean

    @field_validator("height_cm")
    @classmethod
    def validate_height_cm(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Height must be a valid number")
        if val < 50.0 or val > 250.0:
            raise ValueError("Height must be between 50 and 250 cm")
        return round(val, 1)

    @field_validator("weight_kg")
    @classmethod
    def validate_weight_kg(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Weight must be a valid number")
        if val < 20.0 or val > 400.0:
            raise ValueError("Weight must be between 20 and 400 kg")
        return round(val, 1)

    @field_validator("diagnosis_year_diabetes")
    @classmethod
    def validate_diag_year_dm(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        current_year = datetime.now(timezone.utc).year
        if v < 1900 or v > current_year:
            raise ValueError(f"Diagnosis year for diabetes must be between 1900 and {current_year}")
        return v

    @field_validator("diagnosis_year_hypertension")
    @classmethod
    def validate_diag_year_htn(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        current_year = datetime.now(timezone.utc).year
        if v < 1900 or v > current_year:
            raise ValueError(f"Diagnosis year for hypertension must be between 1900 and {current_year}")
        return v

    @field_validator("smoking_status")
    @classmethod
    def validate_smoking_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip().lower()
        if clean not in ALLOWED_SMOKING_STATUS:
            raise ValueError(f"Invalid smoking_status '{v}'. Allowed values: {sorted(list(ALLOWED_SMOKING_STATUS))}")
        return clean

    @field_validator("comorbidities", mode="before")
    @classmethod
    def validate_comorbidities(cls, v: Any) -> Optional[Dict[str, bool]]:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("comorbidities must be a dictionary")
        cleaned: Dict[str, bool] = {}
        for k, val in v.items():
            k_clean = str(k).strip().lower()
            if k_clean not in ALLOWED_COMORBIDITIES:
                raise ValueError(f"Invalid comorbidity key '{k}'. Allowed: {sorted(list(ALLOWED_COMORBIDITIES))}")
            if not isinstance(val, bool):
                raise ValueError(f"Comorbidity value for '{k}' must be a boolean (True/False)")
            cleaned[k_clean] = val
        return cleaned


class ProfileResponse(BaseModel):
    user_id: str
    conditions: List[str]
    on_insulin_or_sulfonylurea: bool
    language: str
    date_of_birth: Optional[str] = None
    inclusion_confirmed_at: Optional[str] = None
    sex_at_birth: Optional[str] = None
    pregnancy_status: Optional[str] = None
    voice_enabled: bool = False
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    diagnosis_year_diabetes: Optional[int] = None
    diagnosis_year_hypertension: Optional[int] = None
    smoking_status: Optional[str] = None
    comorbidities: Optional[Dict[str, bool]] = None
    consent_granted_at: Optional[str] = None
    consent_revoked_at: Optional[str] = None
    provider_notification_consent_at: Optional[str] = None
    provider_notification_revoked_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    granted: bool
    provider_notification: Optional[bool] = None


class ProviderNotificationConsentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    granted: bool


# --- Patient Record Schemas (Isolated Mode) ---

def _reject_control_chars(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    raw = str(v)
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise ValueError("Control characters are not allowed")
    return raw.strip()


class RecordConditionItem(BaseModel):
    name: str
    basis: Optional[str] = None


class RecordMedicationItem(BaseModel):
    id: str
    name: str
    dosage: str
    status: str


class RecordAllergyItem(BaseModel):
    id: str
    substance: str
    reaction: Optional[str] = None
    confirmed: bool


class RecordObservationItem(BaseModel):
    id: str
    observation_type: str
    value: float
    unit: str
    measured_at: str


class PatientRecordResponse(BaseModel):
    mode: str
    conditions: List[RecordConditionItem]
    medications: List[RecordMedicationItem]
    allergies: List[RecordAllergyItem]
    baseline_observations: List[RecordObservationItem]


class CreateMedicationRequest(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(..., max_length=80)
    dosage: str = Field(..., max_length=100)
    status: str

    @field_validator("name")
    @classmethod
    def val_name(cls, v: str) -> str:
        clean = _reject_control_chars(v)
        if not clean:
            raise ValueError("name cannot be empty")
        return clean

    @field_validator("dosage")
    @classmethod
    def val_dosage(cls, v: str) -> str:
        clean = _reject_control_chars(v)
        if not clean:
            raise ValueError("dosage cannot be empty")
        return clean

    @field_validator("status")
    @classmethod
    def val_status(cls, v: str) -> str:
        clean = str(v).strip().lower()
        if clean not in ("active", "stopped"):
            raise ValueError("status must be 'active' or 'stopped'")
        return clean


class UpdateMedicationRequest(BaseModel):
    model_config = {"extra": "forbid"}
    dosage: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None

    @field_validator("dosage")
    @classmethod
    def val_dosage(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = _reject_control_chars(v)
        if not clean:
            raise ValueError("dosage cannot be empty")
        return clean

    @field_validator("status")
    @classmethod
    def val_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = str(v).strip().lower()
        if clean not in ("active", "stopped"):
            raise ValueError("status must be 'active' or 'stopped'")
        return clean


class CreateAllergyRequest(BaseModel):
    model_config = {"extra": "forbid"}
    substance: str = Field(..., max_length=80)
    reaction: Optional[str] = Field(None, max_length=120)
    confirmed: bool

    @field_validator("substance")
    @classmethod
    def val_substance(cls, v: str) -> str:
        clean = _reject_control_chars(v)
        if not clean:
            raise ValueError("substance cannot be empty")
        return clean

    @field_validator("reaction")
    @classmethod
    def val_reaction(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = _reject_control_chars(v)
        return clean if clean else None


class CreateObservationRequest(BaseModel):
    model_config = {"extra": "forbid"}
    observation_type: str
    value: float
    measured_at: Optional[str] = None

    @field_validator("observation_type")
    @classmethod
    def val_obs_type(cls, v: str) -> str:
        clean = str(v).strip().lower()
        if clean not in ("glucose", "blood_pressure_systolic", "blood_pressure_diastolic", "weight", "hba1c"):
            raise ValueError("Unsupported observation_type")
        return clean


class SamplePatient(BaseModel):
    id: str
    label: str
    description: str


class EHRSystemResponse(BaseModel):
    ehr_system_id: str
    display_name: str
    kind: str = "public_sandbox"
    description: str = ""
    sample_patients: Optional[List[SamplePatient]] = None
    suggested_patient_ids: Optional[List[str]] = None


class EHRTestRequest(BaseModel):
    ehr_system_id: Optional[str] = None
    system_id: Optional[str] = None


class EHRTestResponse(BaseModel):
    ok: bool
    latency_ms: int
    kind: str
    error_code: Optional[str] = None


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


class EHRConnectionSummary(BaseModel):
    recent_observations: int = 0
    active_medications: int = 0


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
    system_id: Optional[str] = None
    kind: Optional[str] = None
    record_source_label: Optional[str] = None
    summary: Optional[EHRConnectionSummary] = None
    warning: Optional[str] = None


class ConfigItem(BaseModel):
    name: str
    set: bool


class ConfigStatusResponse(BaseModel):
    settings: List[ConfigItem]


# --- Check-in & Review Schemas ---

class CheckinStartResponse(BaseModel):
    checkin_id: str
    question: Optional[str] = None
    mode: str
    is_cold_start: bool
    step: Optional[str] = None
    version: int = 0
    why_text: Optional[str] = None
    options: Optional[List[str]] = None
    system_note: Optional[str] = None
    progress_hint: Optional[str] = None
    language: Optional[str] = None
    can_skip: Optional[bool] = None
    can_say_unknown: Optional[bool] = None


class CheckinAnswerRequest(BaseModel):
    model_config = {"extra": "forbid"}
    answer: str = Field(..., max_length=1000)
    step: Optional[str] = None


class CheckinAnswerResponse(BaseModel):
    question: Optional[str] = None
    complete: bool
    emergency: bool
    emergency_reason: Optional[str] = None
    step: Optional[str] = None
    version: int = 0
    escalation_recorded: Optional[bool] = None
    phase: Optional[str] = None
    triage: Optional[Dict[str, Any]] = None
    why_text: Optional[str] = None
    options: Optional[List[str]] = None
    system_note: Optional[str] = None
    progress_hint: Optional[str] = None
    language: Optional[str] = None
    can_skip: Optional[bool] = None
    can_say_unknown: Optional[bool] = None


class CheckinCompleteResponse(BaseModel):
    emergency: bool
    intakes: List[Dict[str, Any]]
    reconciliation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    requires_review: bool
    max_severity: Optional[str] = None
    triage: Optional[Dict[str, Any]] = None
    record_source_label: Optional[str] = None


class UserCheckinSummaryResponse(BaseModel):
    checkin_id: str
    mode: str
    record_patient_id: str
    status: str
    version: int = 0
    started_at: str
    completed_at: Optional[str] = None
    emergency: bool
    requires_review: bool
    max_severity: Optional[str] = None
    review_status: Optional[str] = None


class UserCheckinDetailResponse(BaseModel):
    checkin_id: str
    user_id: str
    mode: str
    record_patient_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    state: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    record_source_label: Optional[str] = None


class ReviewQueueItemResponse(BaseModel):
    checkin_id: str
    patient_display: str
    mode: str
    created_at: str
    max_severity: Optional[str] = None
    emergency: bool
    overdue: bool
    counts: Dict[str, int]
    trigger_category: Optional[str] = None
    trigger_text: Optional[str] = None
    trigger_reading: Optional[Dict[str, Any]] = None
    escalated_at: Optional[str] = None
    triage_level: Optional[str] = None


class ReviewActionResponse(BaseModel):
    id: int
    checkin_id: str
    provider_user_id: str
    action: str
    note: Optional[str] = None
    ts: str


class ReviewDetailResponse(BaseModel):
    checkin_id: str
    patient_id: str
    patient_display: str
    mode: str
    emergency: bool
    intakes: List[Dict[str, Any]]
    reconciliation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    requires_review: bool
    max_severity: Optional[str] = None
    review_status: str
    created_at: str
    trigger_category: Optional[str] = None
    trigger_text: Optional[str] = None
    trigger_reading: Optional[Dict[str, Any]] = None
    escalated_at: Optional[str] = None
    triage: Optional[Dict[str, Any]] = None
    actions: List[ReviewActionResponse]
    record_source_label: Optional[str] = None
    patient_background: Optional[Dict[str, Any]] = None


class VoiceTranscribeResponse(BaseModel):
    text: str


class ReviewActionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    action: str
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        clean = str(v).strip().lower()
        if clean not in ("acknowledge", "resolve", "escalate"):
            raise ValueError("action must be one of 'acknowledge', 'resolve', or 'escalate'")
        return clean


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
def llm_health_check(
    ping: bool = False,
    current_user: Dict[str, Any] = Depends(require_role("admin")),
):
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
        if user.get("_is_new", False):
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
            voice_enabled=False,
            consent_granted_at=None,
            consent_revoked_at=None,
            provider_notification_consent_at=None,
            provider_notification_revoked_at=None,
            updated_at=None,
        )
    return ProfileResponse(
        user_id=profile["user_id"],
        conditions=profile["conditions"],
        on_insulin_or_sulfonylurea=profile["on_insulin_or_sulfonylurea"],
        language=profile["language"],
        date_of_birth=profile.get("date_of_birth"),
        inclusion_confirmed_at=profile.get("inclusion_confirmed_at"),
        sex_at_birth=profile.get("sex_at_birth"),
        pregnancy_status=profile.get("pregnancy_status"),
        voice_enabled=profile.get("voice_enabled", False),
        height_cm=profile.get("height_cm"),
        weight_kg=profile.get("weight_kg"),
        diagnosis_year_diabetes=profile.get("diagnosis_year_diabetes"),
        diagnosis_year_hypertension=profile.get("diagnosis_year_hypertension"),
        smoking_status=profile.get("smoking_status"),
        comorbidities=profile.get("comorbidities"),
        consent_granted_at=profile.get("consent_granted_at"),
        consent_revoked_at=profile.get("consent_revoked_at"),
        provider_notification_consent_at=profile.get("provider_notification_consent_at"),
        provider_notification_revoked_at=profile.get("provider_notification_revoked_at"),
        updated_at=profile.get("updated_at"),
    )


@app.put("/api/me/profile", response_model=ProfileResponse, tags=["Patient Profile"])
def update_profile_endpoint(
    body: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Updates patient profile conditions, insulin/sulfonylurea flag, language, date of birth, sex, pregnancy status, and richer background fields (patient only)."""
    user_id = current_user["user_id"]

    dob_clean = None
    if body.date_of_birth is not None:
        try:
            dob_clean, _ = validate_date_of_birth(str(body.date_of_birth).strip())
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(ve),
            )

    # Cross-field validation with birth year
    existing_prof = get_patient_profile(user_id) or {}
    effective_dob = dob_clean or existing_prof.get("date_of_birth")
    if effective_dob:
        try:
            birth_year = int(effective_dob.split("-")[0])
            if body.diagnosis_year_diabetes is not None and body.diagnosis_year_diabetes < birth_year:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Diagnosis year for diabetes cannot be before birth year",
                )
            if body.diagnosis_year_hypertension is not None and body.diagnosis_year_hypertension < birth_year:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Diagnosis year for hypertension cannot be before birth year",
                )
        except (ValueError, IndexError):
            pass

    final_sex = body.sex_at_birth
    final_preg = body.pregnancy_status
    if final_sex == "male" and final_preg is None:
        final_preg = "not_applicable"

    updated = upsert_patient_profile(
        user_id=user_id,
        conditions=body.conditions,
        on_insulin_or_sulfonylurea=body.on_insulin_or_sulfonylurea,
        language=body.language,
        date_of_birth=dob_clean,
        inclusion_confirmed=body.inclusion_confirmed,
        sex_at_birth=final_sex,
        pregnancy_status=final_preg,
        voice_enabled=body.voice_enabled,
        height_cm=body.height_cm,
        weight_kg=body.weight_kg,
        diagnosis_year_diabetes=body.diagnosis_year_diabetes,
        diagnosis_year_hypertension=body.diagnosis_year_hypertension,
        smoking_status=body.smoking_status,
        comorbidities=body.comorbidities,
    )

    updated_fields = ["conditions", "on_insulin_or_sulfonylurea", "language"]
    if body.date_of_birth is not None:
        updated_fields.append("date_of_birth")
    if body.inclusion_confirmed is not None:
        updated_fields.append("inclusion_confirmed")
    if body.sex_at_birth is not None:
        updated_fields.append("sex_at_birth")
    if body.pregnancy_status is not None:
        updated_fields.append("pregnancy_status")
    if body.voice_enabled is not None:
        updated_fields.append("voice_enabled")
    if body.height_cm is not None:
        updated_fields.append("height_cm")
    if body.weight_kg is not None:
        updated_fields.append("weight_kg")
    if body.diagnosis_year_diabetes is not None:
        updated_fields.append("diagnosis_year_diabetes")
    if body.diagnosis_year_hypertension is not None:
        updated_fields.append("diagnosis_year_hypertension")
    if body.smoking_status is not None:
        updated_fields.append("smoking_status")
    if body.comorbidities is not None:
        updated_fields.append("comorbidities")

    append_audit(
        actor_user_id=user_id,
        action="profile_updated",
        target=user_id,
        outcome="ok",
        detail={"fields": updated_fields},
    )
    return ProfileResponse(
        user_id=updated["user_id"],
        conditions=updated["conditions"],
        on_insulin_or_sulfonylurea=updated["on_insulin_or_sulfonylurea"],
        language=updated["language"],
        date_of_birth=updated.get("date_of_birth"),
        inclusion_confirmed_at=updated.get("inclusion_confirmed_at"),
        sex_at_birth=updated.get("sex_at_birth"),
        pregnancy_status=updated.get("pregnancy_status"),
        voice_enabled=updated.get("voice_enabled", False),
        height_cm=updated.get("height_cm"),
        weight_kg=updated.get("weight_kg"),
        diagnosis_year_diabetes=updated.get("diagnosis_year_diabetes"),
        diagnosis_year_hypertension=updated.get("diagnosis_year_hypertension"),
        smoking_status=updated.get("smoking_status"),
        comorbidities=updated.get("comorbidities"),
        consent_granted_at=updated.get("consent_granted_at"),
        consent_revoked_at=updated.get("consent_revoked_at"),
        provider_notification_consent_at=updated.get("provider_notification_consent_at"),
        provider_notification_revoked_at=updated.get("provider_notification_revoked_at"),
        updated_at=updated.get("updated_at"),
    )


@app.post("/api/me/consent", response_model=ProfileResponse, tags=["Patient Profile"])
def set_consent_endpoint(
    body: ConsentRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Explicitly grants or revokes patient consent and optional provider notification consent (patient only)."""
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

    p_notif = body.provider_notification if body.provider_notification is not None else body.granted
    updated = set_patient_provider_notification_consent(user_id=user_id, granted=p_notif)
    p_action = "consent_provider_notification_granted" if p_notif else "consent_provider_notification_revoked"
    append_audit(
        actor_user_id=user_id,
        action=p_action,
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
        provider_notification_consent_at=updated.get("provider_notification_consent_at"),
        provider_notification_revoked_at=updated.get("provider_notification_revoked_at"),
        updated_at=updated.get("updated_at"),
    )


@app.post("/api/me/consent/provider-notification", response_model=ProfileResponse, tags=["Patient Profile"])
def set_provider_notification_consent_endpoint(
    body: ProviderNotificationConsentRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Explicitly grants or revokes provider notification consent line (patient only)."""
    user_id = current_user["user_id"]
    updated = set_patient_provider_notification_consent(user_id=user_id, granted=body.granted)
    p_action = "consent_provider_notification_granted" if body.granted else "consent_provider_notification_revoked"
    append_audit(
        actor_user_id=user_id,
        action=p_action,
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
        provider_notification_consent_at=updated.get("provider_notification_consent_at"),
        provider_notification_revoked_at=updated.get("provider_notification_revoked_at"),
        updated_at=updated.get("updated_at"),
    )


# =============================================================================
# PATIENT'S OWN RECORD ENDPOINTS (ISOLATED MODE)
# =============================================================================

ALLOWED_CONDITIONS_BASIS = {"clinician_diagnosed", "self_reported", "unsure"}


def _require_isolated_mode_patient(current_user: Dict[str, Any]) -> str:
    """Verifies that patient has active consent and is in isolated mode (no active EHR link)."""
    user_id = current_user["user_id"]
    profile = get_patient_profile(user_id)
    if not profile or not profile.get("consent_granted_at") or profile.get("consent_revoked_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="consent_required",
        )
    active_conn = get_active_ehr_connection(user_id)
    if active_conn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="record_managed_by_ehr",
        )
    return f"local-{user_id}"


def _validate_observation_value_and_unit(obs_type: str, value: float) -> str:
    clean_type = str(obs_type).strip().lower()
    val = float(value)
    if clean_type == "glucose":
        if not (20.0 <= val <= 600.0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Glucose reading outside plausible range (20-600 mg/dL)")
        return "mg/dL"
    elif clean_type == "blood_pressure_systolic":
        if not (60 <= val <= 260):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Systolic BP outside plausible range (60-260 mmHg)")
        return "mmHg"
    elif clean_type == "blood_pressure_diastolic":
        if not (30 <= val <= 160):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Diastolic BP outside plausible range (30-160 mmHg)")
        return "mmHg"
    elif clean_type == "weight":
        if not (20.0 <= val <= 300.0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weight outside plausible range (20-300 kg)")
        return "kg"
    elif clean_type == "hba1c":
        if not (3.0 <= val <= 20.0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HbA1c outside plausible range (3-20 %)")
        return "%"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported observation type '{obs_type}'")


def _parse_and_validate_measured_at(measured_at: Optional[str]) -> str:
    if not measured_at:
        return _utc_now_iso()
    clean = str(measured_at).strip()
    try:
        dt_str = clean.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ISO timestamp format for measured_at")

    now = datetime.now(timezone.utc)
    if dt > now + timedelta(seconds=60):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="measured_at cannot be in the future")
    if dt < now - timedelta(days=365):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="measured_at cannot be more than 365 days old")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/api/me/record", response_model=PatientRecordResponse, tags=["Patient Record"])
def get_patient_record_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """Retrieves patient's own isolated-mode clinical record (patient only)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    profile = get_patient_profile(user_id) or {}
    conds = profile.get("conditions", [])
    cond_basis = profile.get("conditions_basis", {})
    conditions_list = [
        RecordConditionItem(name=c, basis=cond_basis.get(c))
        for c in conds
    ]

    local_meds = get_local_medications(patient_id)
    medications_list = [
        RecordMedicationItem(
            id=m["id"],
            name=m["medication_name"],
            dosage=m["dosage"],
            status=m["status"],
        )
        for m in local_meds
    ]

    user_allergies = get_allergies(user_id)
    allergies_list = [
        RecordAllergyItem(
            id=a["allergy_id"],
            substance=a["substance"],
            reaction=a.get("reaction"),
            confirmed=bool(a["confirmed"]),
        )
        for a in user_allergies
    ]

    local_obs = get_local_observations(patient_id)
    observations_list = [
        RecordObservationItem(
            id=o["id"],
            observation_type=o["type"],
            value=float(o["value"]),
            unit=o["unit"],
            measured_at=o["timestamp"],
        )
        for o in local_obs
    ]

    return PatientRecordResponse(
        mode="isolated",
        conditions=conditions_list,
        medications=medications_list,
        allergies=allergies_list,
        baseline_observations=observations_list,
    )


@app.put("/api/me/record/conditions-basis", tags=["Patient Record"])
def update_conditions_basis_endpoint(
    body: Dict[str, Optional[str]],
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Updates diagnostic basis for conditions in patient's profile (patient only)."""
    _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    profile = get_patient_profile(user_id) or {}
    profile_conds = set(profile.get("conditions", []))

    for cond_name, basis_val in body.items():
        if cond_name not in profile_conds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Condition '{cond_name}' is not in user profile conditions",
            )
        if basis_val is not None and basis_val not in ALLOWED_CONDITIONS_BASIS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid basis '{basis_val}'. Allowed: {sorted(list(ALLOWED_CONDITIONS_BASIS))}",
            )

    updated_basis = dict(profile.get("conditions_basis", {}))
    for k, v in body.items():
        if v is None:
            updated_basis.pop(k, None)
        else:
            updated_basis[k] = v

    update_patient_conditions_basis(user_id, updated_basis)
    append_audit(
        actor_user_id=user_id,
        action="record_conditions_basis_updated",
        target="record_conditions_basis",
        outcome="ok",
        detail={"type": "conditions_basis", "count": len(body)},
    )
    return {"status": "ok", "conditions_basis": updated_basis}


@app.post("/api/me/record/medications", response_model=RecordMedicationItem, tags=["Patient Record"])
def create_record_medication_endpoint(
    body: CreateMedicationRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Adds a medication to the patient's isolated record (patient only, max 30)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    current_meds = get_local_medications(patient_id)
    if len(current_meds) >= 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maximum_medications_exceeded",
        )

    norm_new = _norm(body.name)
    if any(_norm(m["medication_name"]) == norm_new for m in current_meds):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate_medication",
        )

    med_id = f"local-med-{uuid.uuid4()}"
    now_ts = _utc_now_iso()
    add_local_patient_if_missing(patient_id, name=current_user.get("display_name") or "Patient")
    add_local_medication(
        id=med_id,
        patient_id=patient_id,
        medication_name=body.name,
        status=body.status,
        dosage=body.dosage,
        timestamp=now_ts,
        source="local",
        origin="self_reported",
    )
    append_audit(
        actor_user_id=user_id,
        action="record_medication_created",
        target="record_medication",
        outcome="ok",
        detail={"type": "medication", "count": 1},
    )
    return RecordMedicationItem(
        id=med_id,
        name=body.name,
        dosage=body.dosage,
        status=body.status,
    )


@app.patch("/api/me/record/medications/{med_id}", response_model=RecordMedicationItem, tags=["Patient Record"])
def update_record_medication_endpoint(
    med_id: str,
    body: UpdateMedicationRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Updates dosage or status of a medication in patient's isolated record (patient only)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    if body.dosage is None and body.status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of dosage or status must be provided",
        )

    existing = get_local_medication_by_id(med_id, patient_id=patient_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    new_dosage = body.dosage if body.dosage is not None else existing["dosage"]
    new_status = body.status if body.status is not None else existing["status"]
    update_local_medication(
        medication_id=med_id,
        patient_id=patient_id,
        dosage=new_dosage,
        status=new_status,
    )
    append_audit(
        actor_user_id=user_id,
        action="record_medication_updated",
        target="record_medication",
        outcome="ok",
        detail={"type": "medication", "count": 1},
    )
    return RecordMedicationItem(
        id=med_id,
        name=existing["medication_name"],
        dosage=new_dosage,
        status=new_status,
    )


@app.delete("/api/me/record/medications/{med_id}", tags=["Patient Record"])
def delete_record_medication_endpoint(
    med_id: str,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Deletes a medication from patient's isolated record (patient only)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    existing = get_local_medication_by_id(med_id, patient_id=patient_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    delete_local_medication(med_id, patient_id=patient_id)
    append_audit(
        actor_user_id=user_id,
        action="record_medication_deleted",
        target="record_medication",
        outcome="ok",
        detail={"type": "medication", "count": 1},
    )
    return {"status": "ok"}


@app.post("/api/me/record/allergies", response_model=RecordAllergyItem, tags=["Patient Record"])
def create_record_allergy_endpoint(
    body: CreateAllergyRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Adds an allergy to the patient's isolated record (patient only, max 30)."""
    _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    current_allergies = get_allergies(user_id)
    if len(current_allergies) >= 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maximum_allergies_exceeded",
        )

    allergy_id = str(uuid.uuid4())
    create_allergy(
        allergy_id=allergy_id,
        user_id=user_id,
        substance=body.substance,
        reaction=body.reaction,
        confirmed=body.confirmed,
    )
    append_audit(
        actor_user_id=user_id,
        action="record_allergy_created",
        target="record_allergy",
        outcome="ok",
        detail={"type": "allergy", "count": 1},
    )
    return RecordAllergyItem(
        id=allergy_id,
        substance=body.substance,
        reaction=body.reaction,
        confirmed=body.confirmed,
    )


@app.delete("/api/me/record/allergies/{allergy_id}", tags=["Patient Record"])
def delete_record_allergy_endpoint(
    allergy_id: str,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Deletes an allergy from patient's isolated record (patient only)."""
    _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    existing = get_allergy_by_id(allergy_id, user_id=user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allergy not found",
        )

    delete_allergy(allergy_id, user_id=user_id)
    append_audit(
        actor_user_id=user_id,
        action="record_allergy_deleted",
        target="record_allergy",
        outcome="ok",
        detail={"type": "allergy", "count": 1},
    )
    return {"status": "ok"}


@app.post("/api/me/record/observations", response_model=RecordObservationItem, tags=["Patient Record"])
def create_record_observation_endpoint(
    body: CreateObservationRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Adds a baseline observation to patient's isolated record (patient only, max 20)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    unit = _validate_observation_value_and_unit(body.observation_type, body.value)
    ts = _parse_and_validate_measured_at(body.measured_at)

    current_obs = get_local_observations(patient_id)
    if len(current_obs) >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="maximum_observations_exceeded",
        )

    obs_id = f"local-obs-{uuid.uuid4()}"
    add_local_patient_if_missing(patient_id, name=current_user.get("display_name") or "Patient")
    add_local_observation(
        id=obs_id,
        patient_id=patient_id,
        observation_type=body.observation_type,
        value=float(body.value),
        unit=unit,
        timestamp=ts,
        source="local",
        origin="self_reported",
    )
    append_audit(
        actor_user_id=user_id,
        action="record_observation_created",
        target="record_observation",
        outcome="ok",
        detail={"type": "observation", "count": 1},
    )
    return RecordObservationItem(
        id=obs_id,
        observation_type=body.observation_type,
        value=float(body.value),
        unit=unit,
        measured_at=ts,
    )


@app.delete("/api/me/record/observations/{obs_id}", tags=["Patient Record"])
def delete_record_observation_endpoint(
    obs_id: str,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Deletes a baseline observation from patient's isolated record (patient only)."""
    patient_id = _require_isolated_mode_patient(current_user)
    user_id = current_user["user_id"]
    existing = get_local_observation_by_id(obs_id, patient_id=patient_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found",
        )

    delete_local_observation(obs_id, patient_id=patient_id)
    append_audit(
        actor_user_id=user_id,
        action="record_observation_deleted",
        target="record_observation",
        outcome="ok",
        detail={"type": "observation", "count": 1},
    )
    return {"status": "ok"}


def _compute_record_source_label(mode: str, ehr_system_id: Optional[str] = None) -> str:
    if mode == "isolated":
        return "Your saved record"
    if ehr_system_id:
        sys = get_ehr_system_by_id(ehr_system_id)
        if sys and sys.get("kind") == "simulated":
            return "Simulated hospital record (synthetic data)"
    return "Hospital EHR (FHIR test server)"


SAMPLE_PATIENTS_LIST = [
    SamplePatient(id="sim-ayesha", label="Ayesha K. (age 52)", description="Type 2 diabetes & hypertension (BP ~128/82, glucose 140-150, active Metformin & Lisinopril)"),
    SamplePatient(id="sim-bilal", label="Bilal A. (age 67)", description="Hypertension personal baseline (BP 110-116/70-74, active Amlodipine)"),
    SamplePatient(id="sim-sana", label="Sana M. (age 45)", description="Type 2 diabetes on insulin (glucose 150-175, active Insulin glargine & Metformin)"),
    SamplePatient(id="sim-imran", label="Imran Q. (age 71)", description="Type 2 diabetes & hypertension, rising readings (BP 148-156/92-98, glucose 180-210)"),
    SamplePatient(id="sim-newpatient", label="Nadia R. (age 38)", description="Hypertension, no recent observations (empty record test)"),
]

SUGGESTED_PATIENT_IDS = [
    "d48ac962-78c6-46cf-ba33-a24771bfa0e4",
    "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3",
    "4551370c-c3eb-4164-a2ff-b528f73a4e0f",
]


# =============================================================================
# EHR REGISTRY & CONNECTION ENDPOINTS
# =============================================================================

@app.get("/api/ehr/systems", response_model=List[EHRSystemResponse], tags=["EHR Connection"])
def get_ehr_systems_endpoint():
    """Returns enabled EHR systems (id, display name, kind, description and suggested/sample patients, never URLs)."""
    systems = get_enabled_ehr_systems()
    res = []
    for s in systems:
        kind = s.get("kind", "public_sandbox")
        sample_patients = SAMPLE_PATIENTS_LIST if kind == "simulated" else None
        suggested_ids = SUGGESTED_PATIENT_IDS if kind == "public_sandbox" else None
        res.append(
            EHRSystemResponse(
                ehr_system_id=s["ehr_system_id"],
                display_name=s["display_name"],
                kind=kind,
                description=s.get("description", ""),
                sample_patients=sample_patients,
                suggested_patient_ids=suggested_ids,
            )
        )
    return res


@app.post("/api/ehr/test", response_model=EHRTestResponse, tags=["EHR Connection"])
def test_ehr_endpoint(
    body: EHRTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Tests connectivity to an EHR system with a 5s timeout and no retries.
    Requires signed-in user, no consent required, uses no patient data.
    """
    sys_id = body.ehr_system_id or body.system_id
    if not sys_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ehr_system_id")
    sys = get_ehr_system_by_id(sys_id)
    if not sys or not sys.get("enabled"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EHR system not found or disabled")

    base_url = sys["fhir_base_url"]
    kind = sys.get("kind", "public_sandbox")
    t0 = time.monotonic()
    try:
        check_fhir_metadata(base_url=base_url, timeout=5.0)
        lat = round((time.monotonic() - t0) * 1000)
        return EHRTestResponse(ok=True, latency_ms=lat, kind=kind)
    except FHIRError as fe:
        lat = round((time.monotonic() - t0) * 1000)
        return EHRTestResponse(ok=False, latency_ms=lat, kind=kind, error_code=fe.error_code)
    except Exception:
        lat = round((time.monotonic() - t0) * 1000)
        return EHRTestResponse(ok=False, latency_ms=lat, kind=kind, error_code="ehr_unreachable")


@app.post("/api/ehr/connect", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def connect_ehr_endpoint(
    body: EHRConnectRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """
    Connects patient account to an external patient record in a registered EHR system.
    Requires active consent. Checks live FHIR patient record deterministically and enforces adult scope.
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
        patient_res = get_fhir_patient(patient_id=body.external_patient_id, base_url=base_url, timeout=10)
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
                detail="Patient not found in this EHR (ehr_patient_not_found)",
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
                detail="EHR unavailable (ehr_unreachable)",
            )
    except FHIRError as fe:
        err_code = fe.error_code
        if fe.status_code == 404 or err_code == "ehr_patient_not_found":
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
                detail="Patient not found in this EHR (ehr_patient_not_found)",
            )
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
            detail=f"EHR unavailable ({err_code})",
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
            detail="EHR unavailable (ehr_unreachable)",
        )

    # 4c. Adults only check: read Patient birthDate
    dob_str = patient_res.get("birthDate") if isinstance(patient_res, dict) else None
    warning = None
    if not dob_str:
        warning = "ehr_birthdate_missing"
    else:
        age = _compute_age_years(dob_str)
        if age is not None and age < 18:
            record_ehr_connection(
                connection_id=str(uuid.uuid4()),
                user_id=user_id,
                ehr_system_id=body.ehr_system_id,
                external_patient_id=body.external_patient_id,
                status="failed",
                last_error_code="not_adult",
            )
            append_audit(
                actor_user_id=user_id,
                action="ehr_connect_failed",
                target=body.ehr_system_id,
                outcome="error",
                detail={"ehr_system_id": body.ehr_system_id, "error_code": "ehr_patient_not_adult", "masked_patient_id": masked_id},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This record belongs to a patient under 18. ChronicCare AI is for adults (18 and over) in this release. (ehr_patient_not_adult)",
            )

    # Fetch bundle for summary counts
    try:
        bundle = get_patient_bundle(body.external_patient_id, mode="connected", base_url=base_url)
        obs_count = len(bundle.get("observations", []))
        meds = bundle.get("medications", [])
        med_count = sum(1 for m in meds if getattr(m, "status", None) == "active" or (isinstance(m, dict) and m.get("status") == "active"))
    except Exception:
        obs_count = 0
        med_count = 0

    if obs_count == 0:
        warning = "ehr_empty_record"

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

    record_label = _compute_record_source_label(mode="connected", ehr_system_id=body.ehr_system_id)

    return EHRConnectionResponse(
        mode="connected",
        connection=EHRConnectionInfo(
            ehr_system_id=body.ehr_system_id,
            display_name=ehr_system["display_name"],
            masked_patient_id=masked_id,
            linked_at=record["linked_at"],
            last_verified_at=now_iso,
        ),
        system_id=body.ehr_system_id,
        kind=ehr_system.get("kind", "public_sandbox"),
        record_source_label=record_label,
        summary=EHRConnectionSummary(
            recent_observations=obs_count,
            active_medications=med_count,
        ),
        warning=warning,
    )


@app.get("/api/ehr/connection", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def get_ehr_connection_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves current patient EHR connection status and masked identifiers."""
    active = get_active_ehr_connection(current_user["user_id"])
    if not active:
        return EHRConnectionResponse(mode="isolated", connection=None)

    masked_id = "..." + active["external_patient_id"][-4:]
    sys = get_ehr_system_by_id(active["ehr_system_id"])
    kind = sys.get("kind", "public_sandbox") if sys else "public_sandbox"
    record_label = _compute_record_source_label(mode="connected", ehr_system_id=active["ehr_system_id"])

    return EHRConnectionResponse(
        mode="connected",
        connection=EHRConnectionInfo(
            ehr_system_id=active["ehr_system_id"],
            display_name=active.get("display_name") or "",
            masked_patient_id=masked_id,
            linked_at=active["linked_at"],
            last_verified_at=active.get("last_verified_at"),
        ),
        system_id=active["ehr_system_id"],
        kind=kind,
        record_source_label=record_label,
    )


@app.delete("/api/ehr/connection", response_model=EHRConnectionResponse, tags=["EHR Connection"])
def delete_ehr_connection_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """Revokes active EHR connection and switches patient mode to isolated (patient only). Clears transient FHIR cache."""
    user_id = current_user["user_id"]
    clear_fhir_cache()
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


@app.get("/api/admin/config-status", response_model=ConfigStatusResponse, tags=["Admin"])
def get_config_status_endpoint(current_user: Dict[str, Any] = Depends(require_role("admin"))):
    """
    Returns configured status (name and set boolean only, never values) for critical server settings.
    Restricted to admin role only.
    """
    db_backend = os.environ.get("DB_BACKEND", "").strip().lower()
    is_mysql = db_backend == "mysql"

    keys = [
        "FIREBASE_PROJECT_ID",
        "DB_BACKEND",
        "FHIR_BASE_URL",
        "DEMO_ROLE_MAP",
    ]
    if is_mysql:
        keys.extend([
            "MYSQL_HOST",
            "MYSQL_PORT",
            "MYSQL_USER",
            "MYSQL_PASSWORD",
            "MYSQL_DATABASE",
        ])

    settings = [
        ConfigItem(name=k, set=bool(os.environ.get(k, "").strip()))
        for k in keys
    ]
    return ConfigStatusResponse(settings=settings)


def _compute_age_years(dob_str: Optional[str]) -> Optional[float]:
    if not dob_str:
        return None
    try:
        dob_dt = datetime.strptime(dob_str.strip(), "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        age = today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))
        return float(age)
    except Exception:
        return None


# =============================================================================
# PATIENT CHECK-IN PIPELINE ENDPOINTS
# =============================================================================

@app.post("/api/checkins/start", response_model=CheckinStartResponse, tags=["Check-in"])
def start_checkin_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """
    Initializes a new server-side check-in session for the authenticated patient.
    Requires active consent and an existing clinical profile.
    Idempotent: Reuses existing un-answered in-progress check-in if started within last 15 minutes.
    """
    user_id = current_user["user_id"]

    # 1. Consent verification
    profile = get_patient_profile(user_id)
    if not profile or not profile.get("consent_granted_at") or profile.get("consent_revoked_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active consent is required to start a check-in (consent_required)",
        )
    if not profile.get("provider_notification_consent_at") or profile.get("provider_notification_revoked_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider notification consent is required to start a check-in (provider_notification_consent_required)",
        )

    # 2. Pregnancy eligibility & inclusion verification
    preg_status = (profile.get("pregnancy_status") or "").lower()
    if preg_status == "yes":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "not_eligible", "reason": "pregnant"},
        )
    if preg_status == "not_sure":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "not_eligible", "reason": "pregnancy_unconfirmed"},
        )

    require_inclusion = os.environ.get("REQUIRE_INCLUSION", "1")
    if require_inclusion != "0":
        missing_items = []
        if not profile.get("date_of_birth"):
            missing_items.append("date_of_birth")
        if not profile.get("inclusion_confirmed_at"):
            missing_items.append("inclusion_confirmed")
        if not profile.get("conditions"):
            missing_items.append("conditions")
        if missing_items:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "profile_incomplete", "missing": missing_items},
            )

    # 3. Profile verification
    conditions = profile.get("conditions", [])
    if not conditions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete your profile first",
        )

    # 3. Start Idempotency Check (re-use recent in-progress checkin if no answers provided yet)
    now_dt = datetime.now(timezone.utc)
    recent_checkins = get_user_checkins(user_id, limit=5)
    for c_summary in recent_checkins:
        if c_summary.get("status") == "in_progress":
            c_detail = get_checkin_by_id(c_summary["checkin_id"])
            if c_detail and c_detail.get("status") == "in_progress":
                c_state = c_detail.get("state", {})
                answers = c_state.get("answers", {})
                if len(answers) == 0:
                    started_str = c_detail.get("started_at", "")
                    try:
                        started_dt = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
                        if (now_dt - started_dt).total_seconds() <= 900:
                            st = InterviewState.from_dict(c_state)
                            med_st_dict = c_detail.get("med_state")
                            med_st = MedicationCheckState.from_dict(med_st_dict) if med_st_dict else None
                            if st.step == INTERVIEW_COMPLETE and med_st and not med_st.complete:
                                res_step = f"medication_check:{med_st.index}:{med_st.attempts}"
                                res_question = current_medication_question(med_st)
                            else:
                                res_step = st.step
                                res_question = get_current_question(st)
                            return CheckinStartResponse(
                                checkin_id=c_detail["checkin_id"],
                                question=res_question,
                                mode=c_detail["mode"],
                                is_cold_start=st.is_cold_start,
                                step=res_step,
                                version=c_detail.get("version", 0),
                            )
                    except Exception:
                        pass

    # 4. Derive mode and record patient id
    active_conn = get_active_ehr_connection(user_id)
    if active_conn:
        mode = "connected"
        record_patient_id = active_conn["external_patient_id"]
        ehr_sys = get_ehr_system_by_id(active_conn["ehr_system_id"])
        base_url = ehr_sys["fhir_base_url"] if ehr_sys else None
    else:
        mode = "isolated"
        record_patient_id = f"local-{user_id}"
        base_url = None

    # 5. In isolated mode, ensure local store patient row exists
    if mode == "isolated":
        patient_name = current_user.get("display_name") or "Local Patient"
        add_local_patient_if_missing(record_patient_id, name=patient_name)

    # 6. Fetch prior bundle to determine cold start and initialize medication confirmation
    try:
        prior_bundle = get_patient_bundle(record_patient_id, mode=mode, base_url=base_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Record source unavailable",
        )

    # 4d. MEDICATION SCOPE in Connected Mode
    meds_for_check = prior_bundle.get("medications", [])
    if mode == "connected":
        meds_for_check = select_chronic_care_medications(meds_for_check)

    is_cold_start = (len(prior_bundle.get("observations", [])) == 0 and len(prior_bundle.get("medications", [])) == 0)
    med_state = start_medication_check(meds_for_check)
    med_state_dict = med_state.to_dict()

    checkin_id = str(uuid.uuid4())
    engine_ver = os.environ.get("INTERVIEW_ENGINE", "v2").lower()

    if engine_ver == "v3":
        history = get_user_baseline_history(user_id=user_id)
        baseline = compute_baseline(history)
        v3_state = v3_start_session(
            checkin_id=checkin_id,
            patient_id=user_id,
            conditions=conditions,
            on_insulin_or_sulfonylurea=profile.get("on_insulin_or_sulfonylurea", False),
            is_cold_start=is_cold_start,
            baseline=baseline,
            language=profile.get("preferred_language") or profile.get("language") or "en",
        )
        create_checkin(
            checkin_id=checkin_id,
            user_id=user_id,
            mode=mode,
            record_patient_id=record_patient_id,
            state_dict=v3_state,
            status="in_progress",
            med_state_dict=med_state_dict,
            ehr_system_id=active_conn["ehr_system_id"] if active_conn else None,
        )
        return CheckinStartResponse(
            checkin_id=checkin_id,
            question=v3_state.get("current_question"),
            mode=mode,
            is_cold_start=is_cold_start,
            step=v3_state.get("step"),
            version=0,
            why_text=v3_state.get("why_text"),
            options=v3_state.get("options"),
            system_note=v3_state.get("system_note"),
            progress_hint=v3_state.get("progress_hint"),
            language=v3_state.get("language"),
            can_skip=v3_state.get("can_skip"),
            can_say_unknown=v3_state.get("can_say_unknown"),
        )

    # 7. Initialize InterviewState and run first node (v2 default)
    state = InterviewState(
        patient_id=record_patient_id,
        conditions_on_file=conditions,
        on_insulin_or_sulfonylurea=profile.get("on_insulin_or_sulfonylurea", False),
        is_cold_start=is_cold_start,
    )
    initial_state = adaptive_interview_node(state, patient_response=None)

    # 8. Persist session
    create_checkin(
        checkin_id=checkin_id,
        user_id=user_id,
        mode=mode,
        record_patient_id=record_patient_id,
        state_dict=initial_state.to_dict(),
        status="in_progress",
        med_state_dict=med_state_dict,
        ehr_system_id=active_conn["ehr_system_id"] if active_conn else None,
    )
    question = get_current_question(initial_state)

    return CheckinStartResponse(
        checkin_id=checkin_id,
        question=question,
        mode=mode,
        is_cold_start=is_cold_start,
        step=initial_state.step,
        version=0,
    )


def _compute_age_years(dob_str: Optional[str]) -> Optional[int]:
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return None


@app.post("/api/checkins/{checkin_id}/answer", response_model=CheckinAnswerResponse, tags=["Check-in"])
def answer_checkin_endpoint(
    checkin_id: str,
    body: CheckinAnswerRequest,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Advances the checkin state (interview, triage protocol, or medication check) with optimistic concurrency and atomic emergency persistence."""
    checkin = get_checkin_by_id(checkin_id)
    if not checkin or checkin["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in session not found",
        )

    if checkin["status"] != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in session is not in progress",
        )

    raw_state = checkin["state"]
    is_v3_session = isinstance(raw_state, dict) and (raw_state.get("engine") == "v3" or raw_state.get("is_v3") is True or "known_slots" in raw_state)
    current_state = raw_state if is_v3_session else InterviewState.from_dict(raw_state)
    current_version = checkin.get("version", 0)
    protocol_state_dict = checkin.get("protocol_state")
    protocol_state = TriageProtocolState.from_dict(protocol_state_dict) if protocol_state_dict else None
    med_state_dict = checkin.get("med_state")
    med_state = MedicationCheckState.from_dict(med_state_dict) if med_state_dict else None

    # Clinical Safety Rule: Typed pregnancy statement stops check-in immediately
    answer_raw = (body.answer or "").strip()
    if answer_raw and detect_pregnancy_statement(answer_raw):
        completed_at = _utc_now_iso()
        apply_checkin_answer_atomic(
            checkin_id=checkin_id,
            expected_version=current_version,
            state_dict=current_state if is_v3_session else current_state.to_dict(),
            status="abandoned",
            completed_at=completed_at,
            emergency=False,
            actor_user_id=current_user["user_id"],
            protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
            med_state_dict=med_state.to_dict() if med_state else None,
        )
        upsert_patient_profile(
            user_id=current_user["user_id"],
            pregnancy_status="yes",
        )
        append_audit(
            actor_user_id=current_user["user_id"],
            action="checkin_stopped_pregnancy",
            target=checkin_id,
            outcome="ok",
            detail={"reason": "patient_reported_pregnancy"},
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "not_eligible",
                "reason": "pregnant",
                "message": "Check-in stopped. ChronicCare AI is designed for non-pregnant adults. Please consult your clinician.",
            },
        )

    # 1. TRIAGE PROTOCOL PHASE
    if protocol_state is not None and not protocol_state.complete:
        expected_step = current_protocol_step(protocol_state)
        if body.step is not None and body.step != expected_step:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "stale_step",
                    "step": expected_step,
                    "question": current_protocol_question(protocol_state),
                },
            )

        answer_text = (body.answer or "").strip()
        if not answer_text:
            return CheckinAnswerResponse(
                question=current_protocol_question(protocol_state),
                complete=False,
                emergency=False,
                emergency_reason=None,
                step=expected_step,
                version=current_version,
                phase="triage",
            )

        next_protocol_state = advance_protocol(protocol_state, body.answer)
        if next_protocol_state.complete:
            res = next_protocol_state.result
            level = res.get("level")
            if level == "emergency":
                completed_at = _utc_now_iso()
                try:
                    success = apply_checkin_answer_atomic(
                        checkin_id=checkin_id,
                        expected_version=current_version,
                        state_dict=current_state.to_dict(),
                        status="emergency",
                        completed_at=completed_at,
                        emergency=True,
                        trigger_category=f"triage:{next_protocol_state.protocol}",
                        trigger_text=res.get("summary"),
                        actor_user_id=current_user["user_id"],
                        med_state_dict=med_state.to_dict() if med_state else None,
                        protocol_state_dict=next_protocol_state.to_dict(),
                        triage_level="emergency",
                        triage_dict=res,
                    )
                except Exception as e:
                    logger.error(f"Persistence error during answer: {type(e).__name__}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to save check-in answer. Please try again.",
                    )

                if not success:
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={"detail": "concurrent_update"},
                    )

                return CheckinAnswerResponse(
                    question=None,
                    complete=True,
                    emergency=True,
                    emergency_reason=res.get("summary"),
                    step=expected_step,
                    version=current_version + 1,
                    escalation_recorded=True,
                    phase="triage",
                    triage=res,
                )
            else:
                # Non-emergency protocol completion (urgent, review, routine)
                has_med_items = bool(med_state and len(med_state.items) > 0 and not med_state.complete)
                if has_med_items:
                    new_status = "in_progress"
                    completed_at = None
                    is_complete = False
                    next_step_str = f"medication_check:{med_state.index}:{med_state.attempts}"
                    next_question_str = current_medication_question(med_state)
                    next_phase = "medication"
                else:
                    new_status = "complete"
                    completed_at = _utc_now_iso()
                    is_complete = True
                    next_step_str = expected_step
                    next_question_str = None
                    next_phase = "triage"

                try:
                    success = apply_checkin_answer_atomic(
                        checkin_id=checkin_id,
                        expected_version=current_version,
                        state_dict=current_state.to_dict(),
                        status=new_status,
                        completed_at=completed_at,
                        emergency=False,
                        actor_user_id=current_user["user_id"],
                        med_state_dict=med_state.to_dict() if med_state else None,
                        protocol_state_dict=next_protocol_state.to_dict(),
                    )
                except Exception as e:
                    logger.error(f"Persistence error during answer: {type(e).__name__}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to save check-in answer. Please try again.",
                    )

                if not success:
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={"detail": "concurrent_update"},
                    )

                return CheckinAnswerResponse(
                    question=next_question_str,
                    complete=is_complete,
                    emergency=False,
                    emergency_reason=None,
                    step=next_step_str,
                    version=current_version + 1,
                    phase=next_phase,
                    triage=res,
                )
        else:
            # Protocol in progress
            next_step_str = current_protocol_step(next_protocol_state)
            next_question_str = current_protocol_question(next_protocol_state)
            try:
                success = apply_checkin_answer_atomic(
                    checkin_id=checkin_id,
                    expected_version=current_version,
                    state_dict=current_state.to_dict(),
                    status="in_progress",
                    completed_at=None,
                    emergency=False,
                    actor_user_id=current_user["user_id"],
                    med_state_dict=med_state.to_dict() if med_state else None,
                    protocol_state_dict=next_protocol_state.to_dict(),
                )
            except Exception as e:
                logger.error(f"Persistence error during answer: {type(e).__name__}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save check-in answer. Please try again.",
                )

            if not success:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"detail": "concurrent_update"},
                )

            return CheckinAnswerResponse(
                question=next_question_str,
                complete=False,
                emergency=False,
                emergency_reason=None,
                step=next_step_str,
                version=current_version + 1,
                phase="triage",
            )

    # 2. MEDICATION CHECK PHASE
    in_med_phase = (not is_v3_session and current_state.step == INTERVIEW_COMPLETE and (protocol_state is None or protocol_state.complete) and med_state is not None and not med_state.complete)

    if in_med_phase:
        expected_step = f"medication_check:{med_state.index}:{med_state.attempts}"
        if body.step is not None and body.step != expected_step:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "stale_step",
                    "step": expected_step,
                    "question": current_medication_question(med_state),
                },
            )

        answer_text = (body.answer or "").strip()
        if not answer_text:
            return CheckinAnswerResponse(
                question=current_medication_question(med_state),
                complete=False,
                emergency=False,
                emergency_reason=None,
                step=expected_step,
                version=current_version,
                phase="medication",
                triage=protocol_state.result if protocol_state else None,
            )

        # Stage-1 red-flag screen on medication answer
        triggered, reason = run_stage1_red_flag_screen(body.answer)
        if triggered:
            last_cond = current_state.active_condition or "general"
            intakes = current_state.intakes if current_state.intakes else [{"condition": last_cond, "emergency": True, "reason": reason}]
            completed_at = _utc_now_iso()
            try:
                success = apply_checkin_answer_atomic(
                    checkin_id=checkin_id,
                    expected_version=current_version,
                    state_dict=current_state.to_dict(),
                    status="emergency",
                    completed_at=completed_at,
                    emergency=True,
                    trigger_category=reason,
                    trigger_text=body.answer,
                    actor_user_id=current_user["user_id"],
                    med_state_dict=med_state.to_dict(),
                    protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
                )
            except Exception as e:
                logger.error(f"Persistence error during answer: {type(e).__name__}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save check-in answer. Please try again.",
                )

            if not success:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"detail": "concurrent_update"},
                )

            return CheckinAnswerResponse(
                question=None,
                complete=True,
                emergency=True,
                emergency_reason=reason,
                step=expected_step,
                version=current_version + 1,
                escalation_recorded=True,
                phase="medication",
                triage=protocol_state.result if protocol_state else None,
            )

        next_med_state = advance_medication_check(med_state, body.answer)
        is_med_complete = next_med_state.complete
        new_status = "complete" if is_med_complete else "in_progress"
        completed_at = _utc_now_iso() if is_med_complete else None

        try:
            success = apply_checkin_answer_atomic(
                checkin_id=checkin_id,
                expected_version=current_version,
                state_dict=current_state.to_dict(),
                status=new_status,
                completed_at=completed_at,
                emergency=False,
                actor_user_id=current_user["user_id"],
                med_state_dict=next_med_state.to_dict(),
                protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
            )
        except Exception as e:
            logger.error(f"Persistence error during answer: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save check-in answer. Please try again.",
            )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "concurrent_update"},
            )

        next_version = current_version + 1
        if is_med_complete:
            return CheckinAnswerResponse(
                question=None,
                complete=True,
                emergency=False,
                emergency_reason=None,
                step=f"medication_check:{next_med_state.index}:{next_med_state.attempts}",
                version=next_version,
                phase="medication",
                triage=protocol_state.result if protocol_state else None,
            )
        else:
            return CheckinAnswerResponse(
                question=current_medication_question(next_med_state),
                complete=False,
                emergency=False,
                emergency_reason=None,
                step=f"medication_check:{next_med_state.index}:{next_med_state.attempts}",
                version=next_version,
                phase="medication",
                triage=protocol_state.result if protocol_state else None,
            )

    # 3. INTERVIEW PHASE
    if is_v3_session:
        current_step_id = current_state.get("step")
        if body.step is not None and body.step != current_step_id:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "stale_step",
                    "step": current_step_id,
                    "question": current_state.get("current_question"),
                },
            )

        next_state = v3_next_turn(copy.deepcopy(current_state), body.answer)
        is_emergency = bool(next_state.get("emergency"))
        emergency_reason = next_state.get("emergency_reason")

        if is_emergency:
            new_status = "emergency"
            completed_at = _utc_now_iso()
            is_complete = True
            next_step_str = next_state.get("step", "COMPLETE")
            next_question_str = None
            next_phase = None
            new_protocol_state_dict = None
        elif next_state.get("completed"):
            readings = {}
            for k, v in next_state.get("readings", {}).items():
                if k in ("glucose", "blood_pressure_systolic", "blood_pressure_diastolic") and v is not None:
                    readings[k] = float(v)

            history = get_user_baseline_history(user_id=current_user["user_id"], exclude_checkin_id=checkin_id)
            baseline = compute_baseline(history)
            triggers = evaluate_triggers(readings, baseline)

            if triggers:
                trigger = triggers[0]
                profile = get_patient_profile(current_user["user_id"]) or {}
                dob = profile.get("date_of_birth")
                try:
                    age_years = calculate_age(dob) if dob else 40
                except Exception:
                    age_years = 40

                new_proto = start_protocol(trigger, readings, age_years, baseline)
                new_protocol_state_dict = new_proto.to_dict()
                new_status = "in_progress"
                completed_at = None
                is_complete = False
                next_step_str = current_protocol_step(new_proto)
                next_question_str = current_protocol_question(new_proto)
                next_phase = "triage"
            else:
                new_protocol_state_dict = None
                has_med_items = bool(med_state and len(med_state.items) > 0 and not med_state.complete)
                if has_med_items:
                    new_status = "in_progress"
                    completed_at = None
                    is_complete = False
                    next_step_str = f"medication_check:{med_state.index}:{med_state.attempts}"
                    next_question_str = current_medication_question(med_state)
                    next_phase = "medication"
                else:
                    new_status = "complete"
                    completed_at = _utc_now_iso()
                    is_complete = True
                    next_step_str = next_state.get("step", "COMPLETE")
                    next_question_str = None
                    next_phase = None
        else:
            new_protocol_state_dict = None
            new_status = "in_progress"
            completed_at = None
            is_complete = False
            next_step_str = next_state.get("step")
            next_question_str = next_state.get("current_question")
            next_phase = None

        try:
            success = apply_checkin_answer_atomic(
                checkin_id=checkin_id,
                expected_version=current_version,
                state_dict=next_state,
                status=new_status,
                completed_at=completed_at,
                emergency=is_emergency,
                trigger_category=emergency_reason,
                trigger_text=body.answer,
                actor_user_id=current_user["user_id"],
                med_state_dict=med_state.to_dict() if med_state else None,
                protocol_state_dict=new_protocol_state_dict,
            )
        except Exception as e:
            logger.error(f"Persistence error during answer: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save check-in answer. Please try again.",
            )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "concurrent_update"},
            )

        next_version = current_version + 1

        return CheckinAnswerResponse(
            question=next_question_str,
            complete=is_complete,
            emergency=is_emergency,
            emergency_reason=emergency_reason,
            step=next_step_str,
            version=next_version,
            escalation_recorded=True if is_emergency else None,
            phase=next_phase,
            why_text=next_state.get("why_text"),
            options=next_state.get("options"),
            system_note=next_state.get("system_note"),
            progress_hint=next_state.get("progress_hint"),
            language=next_state.get("language"),
            can_skip=next_state.get("can_skip"),
            can_say_unknown=next_state.get("can_say_unknown"),
        )

    # v2 Interview node path
    if body.step is not None:
        if body.step != current_state.step:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "stale_step",
                    "step": current_state.step,
                    "question": get_current_question(current_state),
                },
            )

    try:
        next_state = adaptive_interview_node(current_state, patient_response=body.answer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    is_emergency = bool(next_state.stage1_red_flag or (next_state.intake and next_state.intake.get("emergency")))

    if is_emergency:
        new_status = "emergency"
        completed_at = _utc_now_iso()
        is_complete = True
        next_step_str = next_state.step
        next_question_str = None
        next_phase = None
        new_protocol_state_dict = None
    elif next_state.step == INTERVIEW_COMPLETE:
        # Build readings and evaluate triage triggers
        readings = {}
        for intake in next_state.intakes:
            for r in intake.get("readings", []):
                obs_type = r.get("observation_type")
                val = r.get("value")
                if obs_type in ("glucose", "blood_pressure_systolic", "blood_pressure_diastolic") and val is not None:
                    readings[obs_type] = float(val)

        history = get_user_baseline_history(user_id=current_user["user_id"], exclude_checkin_id=checkin_id)
        baseline = compute_baseline(history)
        triggers = evaluate_triggers(readings, baseline)

        if triggers:
            trigger = triggers[0]
            profile = get_patient_profile(current_user["user_id"]) or {}
            dob = profile.get("date_of_birth")
            try:
                age_years = calculate_age(dob) if dob else 40
            except Exception:
                age_years = 40

            new_proto = start_protocol(trigger, readings, age_years, baseline)
            new_protocol_state_dict = new_proto.to_dict()
            new_status = "in_progress"
            completed_at = None
            is_complete = False
            next_step_str = current_protocol_step(new_proto)
            next_question_str = current_protocol_question(new_proto)
            next_phase = "triage"
        else:
            new_protocol_state_dict = None
            has_med_items = bool(med_state and len(med_state.items) > 0 and not med_state.complete)
            if has_med_items:
                new_status = "in_progress"
                completed_at = None
                is_complete = False
                next_step_str = f"medication_check:{med_state.index}:{med_state.attempts}"
                next_question_str = current_medication_question(med_state)
                next_phase = "medication"
            else:
                new_status = "complete"
                completed_at = _utc_now_iso()
                is_complete = True
                next_step_str = next_state.step
                next_question_str = None
                next_phase = None
    else:
        new_protocol_state_dict = None
        new_status = "in_progress"
        completed_at = None
        is_complete = False
        next_step_str = next_state.step
        next_question_str = get_current_question(next_state)
        next_phase = None

    try:
        success = apply_checkin_answer_atomic(
            checkin_id=checkin_id,
            expected_version=current_version,
            state_dict=next_state.to_dict(),
            status=new_status,
            completed_at=completed_at,
            emergency=is_emergency,
            trigger_category=next_state.stage1_reason,
            trigger_text=body.answer,
            actor_user_id=current_user["user_id"],
            med_state_dict=med_state.to_dict() if med_state else None,
            protocol_state_dict=new_protocol_state_dict,
        )
    except Exception as e:
        logger.error(f"Persistence error during answer: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save check-in answer. Please try again.",
        )

    if not success:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "concurrent_update"},
        )

    next_version = current_version + 1

    return CheckinAnswerResponse(
        question=next_question_str,
        complete=is_complete,
        emergency=is_emergency,
        emergency_reason=next_state.stage1_reason if is_emergency else None,
        step=next_step_str,
        version=next_version,
        escalation_recorded=True if is_emergency else None,
        phase=next_phase,
    )


@app.post("/api/checkins/{checkin_id}/complete", response_model=CheckinCompleteResponse, tags=["Check-in"])
def complete_checkin_endpoint(
    checkin_id: str,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """
    Finalizes the check-in session, executes reconciliation and verification pipelines,
    and records results for provider review.
    """
    checkin = get_checkin_by_id(checkin_id)
    if not checkin or checkin["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in session not found",
        )

    # Idempotent check
    stored_result = get_checkin_result(checkin_id)
    record_label = _compute_record_source_label(checkin["mode"], checkin.get("ehr_system_id"))
    if stored_result:
        return CheckinCompleteResponse(
            emergency=stored_result["emergency"],
            intakes=stored_result["intakes"],
            reconciliation=stored_result.get("reconciliation"),
            verification=stored_result.get("verification"),
            requires_review=stored_result["requires_review"],
            max_severity=stored_result.get("max_severity"),
            triage=stored_result.get("triage"),
            record_source_label=record_label,
        )

    raw_state = checkin.get("state") or {}
    is_v3_session = bool(raw_state.get("engine") == "v3" or raw_state.get("completed") is not None)

    if is_v3_session:
        is_completed = bool(raw_state.get("completed"))
        is_emergency = bool(raw_state.get("stage1_red_flag") or raw_state.get("emergency") or checkin["status"] == "emergency")
        if not is_completed and not is_emergency:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interview is not complete",
            )
        if is_emergency:
            emergency_reason = raw_state.get("emergency_reason") or raw_state.get("stage1_reason")
            intakes = raw_state.get("intakes") or ([{"condition": "general", "emergency": True, "reason": emergency_reason}] if emergency_reason else [])
            now_iso = _utc_now_iso()
            create_checkin_result(
                checkin_id=checkin_id,
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                review_status="open",
                trigger_category=emergency_reason or "emergency",
                trigger_text=None,
                escalated_at=now_iso,
                triage_level="emergency",
                triage=None,
            )
            update_checkin_state(
                checkin_id=checkin_id,
                state_dict=raw_state,
                status="emergency",
                completed_at=now_iso,
                med_state_dict=None,
                protocol_state_dict=None,
            )
            return CheckinCompleteResponse(
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                triage=None,
                record_source_label=record_label,
            )

        v3_summary = finish_v3_session(raw_state)
        intakes = v3_summary.get("intakes", [])
        state = InterviewState(
            patient_id=raw_state.get("patient_id") or current_user["user_id"],
            conditions_on_file=raw_state.get("conditions_on_file") or ["diabetes"],
            step=INTERVIEW_COMPLETE,
            intakes=intakes,
        )
        protocol_state = None
        med_state = None
    else:
        state = InterviewState.from_dict(checkin["state"])
        protocol_state_dict = checkin.get("protocol_state")
        protocol_state = TriageProtocolState.from_dict(protocol_state_dict) if protocol_state_dict else None
        med_state_dict = checkin.get("med_state")
        med_state = MedicationCheckState.from_dict(med_state_dict) if med_state_dict else None

        # Check incomplete checkin
        if not state.stage1_red_flag and checkin["status"] != "emergency":
            if state.step != INTERVIEW_COMPLETE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Interview is not complete",
                )
            if protocol_state and not protocol_state.complete:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="triage_incomplete",
                )
            if med_state and not med_state.complete:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="medication_check_incomplete",
                )

        # 1. Emergency Flow
        if state.stage1_red_flag or checkin["status"] == "emergency":
            intakes = state.intakes if state.intakes else ([{"condition": state.active_condition or "general", "emergency": True, "reason": state.stage1_reason}] if state.stage1_reason else [])
            now_iso = _utc_now_iso()
            triage_dict = protocol_state.result if (protocol_state and protocol_state.complete) else None
            create_checkin_result(
                checkin_id=checkin_id,
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                review_status="open",
                trigger_category=state.stage1_reason or (f"triage:{protocol_state.protocol}" if protocol_state else None),
                trigger_text=triage_dict.get("summary") if triage_dict else None,
                escalated_at=now_iso,
                triage_level="emergency" if triage_dict else None,
                triage=triage_dict,
            )
            update_checkin_state(
                checkin_id=checkin_id,
                state_dict=state.to_dict(),
                status="emergency",
                completed_at=now_iso,
                med_state_dict=med_state.to_dict() if med_state else None,
                protocol_state_dict=protocol_state.to_dict() if protocol_state else None,
            )
            return CheckinCompleteResponse(
                emergency=True,
                intakes=intakes,
                reconciliation=None,
                verification=None,
                requires_review=True,
                max_severity="high",
                triage=triage_dict,
                record_source_label=record_label,
            )

    # 2. Non-Emergency Flow
    base_url = None
    if checkin["mode"] == "connected":
        active_conn = get_active_ehr_connection(current_user["user_id"])
        if active_conn:
            ehr_sys = get_ehr_system_by_id(active_conn["ehr_system_id"])
            base_url = ehr_sys["fhir_base_url"] if ehr_sys else None

    # Fetch prior baseline
    try:
        prior_bundle = get_patient_bundle(checkin["record_patient_id"], mode=checkin["mode"], base_url=base_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Record source unavailable",
        )

    # Build check-in bundle
    source = "fhir" if checkin["mode"] == "connected" else "local"
    patient_name = current_user.get("display_name") or (prior_bundle["patient"].name if prior_bundle.get("patient") else "Patient")
    now_iso = _utc_now_iso()
    try:
        checkin_bundle = build_checkin_bundle(state, source=source, patient_name=patient_name, checkin_timestamp=now_iso)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if med_state and med_state.items:
        checkin_bundle["medications"] = build_medication_bundle_items(
            med_state,
            patient_id=checkin["record_patient_id"],
            source=source,
            timestamp=now_iso,
        )
        prior_bundle["medications"] = restrict_to_asked(prior_bundle.get("medications", []), med_state)

    # Reconcile bundles
    try:
        recon_result = reconcile_bundles(prior_bundle, checkin_bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Verify reconciliation with origins
    checkin_origins = build_checkin_origins(checkin_bundle)
    if med_state and med_state.items:
        checkin_origins.update(build_medication_origins(checkin_bundle["medications"]))

    if checkin["mode"] == "isolated":
        local_obs_origins = get_local_observation_origins(checkin["record_patient_id"])
        local_med_origins = get_local_medication_origins(checkin["record_patient_id"])
        combined_origins = {**local_obs_origins, **local_med_origins, **checkin_origins}
    else:
        combined_origins = checkin_origins

    verif_result = verify_reconciliation(recon_result, origins=combined_origins)

    # Isolated Mode: write check-in observations to Local Store tagged self_reported
    if checkin["mode"] == "isolated":
        for obs in checkin_bundle["observations"]:
            add_local_observation(
                id=obs.source_record_id,
                patient_id=checkin["record_patient_id"],
                observation_type=obs.observation_type,
                value=obs.value,
                unit=obs.unit,
                timestamp=obs.timestamp,
                source="local",
                origin="self_reported",
            )

    # Determine severity and review necessity
    summary = verif_result.summary
    verif_requires_review = bool(summary.get("requires_review", 0) > 0)
    if summary.get("severity_high", 0) > 0:
        verif_max_severity = "high"
    elif summary.get("severity_moderate", 0) > 0:
        verif_max_severity = "moderate"
    elif summary.get("severity_low", 0) > 0:
        verif_max_severity = "low"
    else:
        verif_max_severity = "none"

    if protocol_state and protocol_state.complete:
        triage_res = dict(protocol_state.result)
        profile = get_patient_profile(current_user["user_id"]) or {}
        if not profile.get("date_of_birth"):
            triage_res["age_assumed"] = True

        proto_level = triage_res.get("level", "routine")
        if verif_requires_review:
            final_triage_level = _raise_level(proto_level, "review")
        else:
            final_triage_level = proto_level

        final_requires_review = (final_triage_level in ("review", "urgent", "emergency") or verif_requires_review)

        SEV_ORDER = {"none": 0, "low": 1, "moderate": 2, "high": 3}
        if final_triage_level == "urgent":
            final_max_sev = "high"
        elif final_triage_level == "review":
            if SEV_ORDER.get(verif_max_severity, 0) < SEV_ORDER["moderate"]:
                final_max_sev = "moderate"
            else:
                final_max_sev = verif_max_severity
        else:
            final_max_sev = verif_max_severity

        review_status = "open" if final_requires_review else "resolved"

        create_checkin_result(
            checkin_id=checkin_id,
            emergency=False,
            intakes=state.intakes,
            reconciliation=recon_result.to_dict(),
            verification=verif_result.to_dict(),
            requires_review=final_requires_review,
            max_severity=final_max_sev,
            review_status=review_status,
            triage_level=final_triage_level,
            triage=triage_res,
        )
        update_checkin_state(
            checkin_id=checkin_id,
            state_dict=state.to_dict(),
            status="complete",
            completed_at=_utc_now_iso(),
            med_state_dict=med_state.to_dict() if med_state else None,
            protocol_state_dict=protocol_state.to_dict(),
        )

        return CheckinCompleteResponse(
            emergency=False,
            intakes=state.intakes,
            reconciliation=recon_result.to_dict(),
            verification=verif_result.to_dict(),
            requires_review=final_requires_review,
            max_severity=final_max_sev,
            triage=triage_res,
            record_source_label=record_label,
        )
    else:
        review_status = "open" if verif_requires_review else "resolved"
        create_checkin_result(
            checkin_id=checkin_id,
            emergency=False,
            intakes=state.intakes,
            reconciliation=recon_result.to_dict(),
            verification=verif_result.to_dict(),
            requires_review=verif_requires_review,
            max_severity=verif_max_severity,
            review_status=review_status,
        )
        update_checkin_state(
            checkin_id=checkin_id,
            state_dict=state.to_dict(),
            status="complete",
            completed_at=_utc_now_iso(),
            med_state_dict=med_state.to_dict() if med_state else None,
            protocol_state_dict=None,
        )

        return CheckinCompleteResponse(
            emergency=False,
            intakes=state.intakes,
            reconciliation=recon_result.to_dict(),
            verification=verif_result.to_dict(),
            requires_review=verif_requires_review,
            max_severity=verif_max_severity,
            record_source_label=record_label,
        )



@app.get("/api/checkins", response_model=List[UserCheckinSummaryResponse], tags=["Check-in"])
def get_user_checkins_endpoint(current_user: Dict[str, Any] = Depends(require_role("patient"))):
    """Retrieves list of previous check-in sessions for authenticated patient."""
    checkins = get_user_checkins(current_user["user_id"], limit=20)
    return [
        UserCheckinSummaryResponse(
            checkin_id=c["checkin_id"],
            mode=c["mode"],
            record_patient_id=c["record_patient_id"],
            status=c["status"],
            version=c.get("version", 0),
            started_at=c["started_at"],
            completed_at=c.get("completed_at"),
            emergency=c["emergency"],
            requires_review=c["requires_review"],
            max_severity=c.get("max_severity"),
            review_status=c.get("review_status"),
        )
        for c in checkins
    ]


@app.get("/api/checkins/{checkin_id}", response_model=UserCheckinDetailResponse, tags=["Check-in"])
def get_user_checkin_detail_endpoint(
    checkin_id: str,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """Retrieves full details and computed results of a patient's own check-in."""
    checkin = get_checkin_by_id(checkin_id)
    if not checkin or checkin["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in session not found",
        )

    result = get_checkin_result(checkin_id)
    record_label = _compute_record_source_label(checkin["mode"], checkin.get("ehr_system_id"))
    return UserCheckinDetailResponse(
        checkin_id=checkin["checkin_id"],
        user_id=checkin["user_id"],
        mode=checkin["mode"],
        record_patient_id=checkin["record_patient_id"],
        status=checkin["status"],
        started_at=checkin["started_at"],
        completed_at=checkin.get("completed_at"),
        state=checkin["state"],
        result=result,
        record_source_label=record_label,
    )


# =============================================================================
# PROVIDER REVIEW QUEUE & ACTION ENDPOINTS
# =============================================================================

@app.get("/api/provider/review-queue", response_model=List[ReviewQueueItemResponse], tags=["Provider Review"])
def get_provider_review_queue_endpoint(
    status: str = Query("open", pattern="^(open|acknowledged|resolved|escalated)$"),
    current_user: Dict[str, Any] = Depends(require_role("provider")),
):
    """Retrieves prioritized clinical review queue (Provider only)."""
    items = get_provider_review_queue(review_status=status)
    return [ReviewQueueItemResponse(**item) for item in items]


def _build_patient_background(user_id: str) -> Optional[Dict[str, Any]]:
    profile = get_patient_profile(user_id)
    if not profile:
        return None
    height_cm = profile.get("height_cm")
    weight_kg = profile.get("weight_kg")
    bmi = None
    if height_cm and weight_kg and height_cm > 0:
        h_m = height_cm / 100.0
        bmi = round(weight_kg / (h_m * h_m), 1)
    return {
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "diagnosis_year_diabetes": profile.get("diagnosis_year_diabetes"),
        "diagnosis_year_hypertension": profile.get("diagnosis_year_hypertension"),
        "smoking_status": profile.get("smoking_status"),
        "comorbidities": profile.get("comorbidities"),
        "on_insulin_or_sulfonylurea": profile.get("on_insulin_or_sulfonylurea", False),
        "sex_at_birth": profile.get("sex_at_birth"),
        "pregnancy_status": profile.get("pregnancy_status"),
        "date_of_birth": profile.get("date_of_birth"),
    }


@app.get("/api/provider/review/{checkin_id}", response_model=ReviewDetailResponse, tags=["Provider Review"])
def get_provider_review_detail_endpoint(
    checkin_id: str,
    current_user: Dict[str, Any] = Depends(require_role("provider")),
):
    """Retrieves comprehensive clinical review details for a check-in item (Provider only)."""
    checkin = get_checkin_by_id(checkin_id)
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    result = get_checkin_result(checkin_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in result not found",
        )

    patient_user = get_user_by_id(checkin["user_id"])
    patient_display = (patient_user.get("display_name") if patient_user else None) or (patient_user.get("email") if patient_user else None) or "Patient"
    actions = get_review_actions(checkin_id)
    record_label = _compute_record_source_label(checkin["mode"], checkin.get("ehr_system_id"))

    # Extract trigger_reading if present in intakes
    trigger_reading = None
    for intake in result.get("intakes", []):
        if intake.get("trigger_reading"):
            trigger_reading = intake["trigger_reading"]
            break

    patient_bg = _build_patient_background(checkin["user_id"])

    return ReviewDetailResponse(
        checkin_id=checkin_id,
        patient_id=checkin["record_patient_id"],
        patient_display=patient_display,
        mode=checkin["mode"],
        emergency=result["emergency"],
        intakes=result["intakes"],
        reconciliation=result.get("reconciliation"),
        verification=result.get("verification"),
        requires_review=result["requires_review"],
        max_severity=result.get("max_severity"),
        review_status=result["review_status"],
        created_at=result["created_at"],
        trigger_category=result.get("trigger_category"),
        trigger_text=result.get("trigger_text"),
        trigger_reading=trigger_reading,
        escalated_at=result.get("escalated_at"),
        triage=result.get("triage"),
        actions=[ReviewActionResponse(**a) for a in actions],
        record_source_label=record_label,
        patient_background=patient_bg,
    )


@app.post("/api/provider/review/{checkin_id}/action", response_model=ReviewDetailResponse, tags=["Provider Review"])
def post_provider_review_action_endpoint(
    checkin_id: str,
    body: ReviewActionRequest,
    current_user: Dict[str, Any] = Depends(require_role("provider")),
):
    """Records an action on a clinical review item and transitions review_status (Provider only)."""
    checkin = get_checkin_by_id(checkin_id)
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    result = get_checkin_result(checkin_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in result not found",
        )

    append_review_action(
        checkin_id=checkin_id,
        provider_user_id=current_user["user_id"],
        action=body.action,
        note=body.note,
    )
    append_audit(
        actor_user_id=current_user["user_id"],
        action=f"review_{body.action}",
        target=checkin_id,
        outcome="ok",
        detail={"action": body.action, "note_length": len(body.note or "")},
    )

    updated_result = get_checkin_result(checkin_id)
    patient_user = get_user_by_id(checkin["user_id"])
    patient_display = (patient_user.get("display_name") if patient_user else None) or (patient_user.get("email") if patient_user else None) or "Patient"
    actions = get_review_actions(checkin_id)

    trigger_reading = None
    for intake in updated_result.get("intakes", []):
        if intake.get("trigger_reading"):
            trigger_reading = intake["trigger_reading"]
            break

    record_label = _compute_record_source_label(checkin["mode"], checkin.get("ehr_system_id"))
    patient_bg = _build_patient_background(checkin["user_id"])
    return ReviewDetailResponse(
        checkin_id=checkin_id,
        patient_id=checkin["record_patient_id"],
        patient_display=patient_display,
        mode=checkin["mode"],
        emergency=updated_result["emergency"],
        intakes=updated_result["intakes"],
        reconciliation=updated_result.get("reconciliation"),
        verification=updated_result.get("verification"),
        requires_review=updated_result["requires_review"],
        max_severity=updated_result.get("max_severity"),
        review_status=updated_result["review_status"],
        created_at=updated_result["created_at"],
        trigger_category=updated_result.get("trigger_category"),
        trigger_text=updated_result.get("trigger_text"),
        trigger_reading=trigger_reading,
        escalated_at=updated_result.get("escalated_at"),
        triage=updated_result.get("triage"),
        actions=[ReviewActionResponse(**a) for a in actions],
        record_source_label=record_label,
        patient_background=patient_bg,
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
def reconcile_endpoint(
    request: ReconcileRequest,
    current_user: Dict[str, Any] = Depends(require_role("provider", "admin")),
):
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
def verify_endpoint(
    request: VerifyRequest,
    current_user: Dict[str, Any] = Depends(require_role("provider", "admin")),
):
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


# =============================================================================
# VOICE INPUT / TRANSCRIPTION ENDPOINTS
# =============================================================================

_voice_rate_limit_store: Dict[str, List[float]] = {}


def _check_voice_rate_limit(user_id: str, limit: int = 10, window_seconds: float = 60.0) -> None:
    now = time.time()
    history = [t for t in _voice_rate_limit_store.get(user_id, []) if now - t < window_seconds]
    if len(history) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="voice is busy, please type",
        )
    history.append(now)
    _voice_rate_limit_store[user_id] = history


def transcribe_audio_groq(
    audio_bytes: bytes,
    content_type: str,
    language: Optional[str] = None,
) -> str:
    groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transcription service is not configured",
        )

    model = os.environ.get("GROQ_STT_MODEL", "").strip() or "whisper-large-v3-turbo"
    ext = "webm"
    if "wav" in content_type:
        ext = "wav"
    elif "mp4" in content_type or "m4a" in content_type:
        ext = "m4a"
    elif "ogg" in content_type:
        ext = "ogg"
    elif "mpeg" in content_type or "mp3" in content_type:
        ext = "mp3"

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
    }
    data: Dict[str, Any] = {
        "model": model,
        "response_format": "json",
    }
    if language in ("en", "ur"):
        data["language"] = language

    last_resp = None
    for attempt in range(2):
        try:
            files = {
                "file": (f"audio.{ext}", audio_bytes, content_type or "audio/webm"),
            }
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=20)
            if resp.status_code == 200:
                res_json = resp.json()
                return str(res_json.get("text", "")).strip()
            elif resp.status_code == 429:
                logger.warning("Groq STT returned 429 rate limit")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="voice is busy, please type",
                )
            elif resp.status_code >= 500:
                logger.warning("Groq STT server error %d (attempt %d/2)", resp.status_code, attempt + 1)
                last_resp = resp
                if attempt == 0:
                    time.sleep(0.5)
                    continue
            else:
                logger.error("Groq STT returned client error status %d", resp.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Voice transcription service error",
                )
        except requests.Timeout:
            logger.warning("Groq STT request timed out on attempt %d/2", attempt + 1)
            if attempt == 0:
                continue
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Voice transcription timed out",
            )
        except requests.RequestException as re:
            logger.error("Groq STT connection error: %s", type(re).__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Voice transcription connection error",
            )

    if last_resp is not None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice transcription service error",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Voice transcription service error",
    )


@app.post("/api/voice/transcribe", response_model=VoiceTranscribeResponse, tags=["Voice"])
async def voice_transcribe_endpoint(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role("patient")),
):
    """
    Transcribes a short audio clip (max 60s / 5MB) using Groq Whisper.
    Memory only: audio is not saved to disk or database.
    Rate limited to 10 requests/minute per patient.
    """
    user_id = current_user["user_id"]
    profile = get_patient_profile(user_id) or {}
    if not profile.get("voice_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice input is not enabled in settings",
        )

    # Per-user rate limit check
    _check_voice_rate_limit(user_id)

    raw_content_type = request.headers.get("content-type", "").lower()
    content_type = raw_content_type.split(";")[0].strip()
    if not content_type or not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio content type. Expected audio/*",
        )

    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio data received",
        )
    if len(audio_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file too large (max 5 MB)",
        )

    lang = profile.get("language", "en")
    start_t = time.time()
    text = transcribe_audio_groq(audio_bytes, content_type=content_type, language=lang)
    duration_s = round(time.time() - start_t, 2)
    logger.info("Voice transcription finished (duration=%ss, size=%d bytes)", duration_s, len(audio_bytes))

    del audio_bytes

    return VoiceTranscribeResponse(text=text)

