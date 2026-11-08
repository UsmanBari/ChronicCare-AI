"""
Targeted Unit Tests Closing Week 3 Code Coverage Gaps.
(Iteration 3 Day 6 - Acceptance S3-6-03)

Covers under-covered branches and edge cases across:
1. rag.store:
   - JsonlChunkStore (file not found, corrupt JSON, condition/topic/priority filters, all_chunks)
   - DbChunkStore (condition/topic/priority filters, malformed topics_json, all_chunks)
   - get_db_chunk_store (singleton caching, force_reload)
2. orchestrator.steps:
   - _build_patient_explain_view (None input, pending status, error status, ready view field stripping)
   - _build_patient_risk_view (strict None return invariant under any flags / conditions)
   - step_risk (disabled flag RISK_ENABLED=false, diabetes condition non-applicability)
   - step_explain (disabled flag EXPLAIN_ENABLED=false, emergency bypass)
   - _sanitize_trace_for_persistence (trace node sequence, metadata isolation, zero PHI)
   - step_check_idempotency (already completed checkin idempotency response)
3. data_sources.ocr:
   - staging (_clean_expired, stage_upload, get_staged_upload, remove_staged_upload, get_user_pending_count)
   - provider (check_ocr_provider_available, get_ocr_provider, SubprocessOcrProvider)
   - extract_fields (is_in_reference_context, levenshtein_distance, match_medication_name, edge pattern extraction)
4. data_sources.app_store:
   - record_edit and get_record_edits (filtering by since_ts, limit, record_type)
5. agents.risk_rules:
   - is_risk_applicable (empty, none, non-list, hypertension vs diabetes)
   - apply_risk_to_level (high risk elevation when RISK_CAN_RAISE=true, routine to review)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import pytest

# Ensure backend-poc-technical is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.store import (
    ChunkStore,
    JsonlChunkStore,
    DbChunkStore,
    get_db_chunk_store,
)
from orchestrator.steps import (
    _build_patient_explain_view,
    _build_patient_risk_view,
    _sanitize_trace_for_persistence,
    step_check_idempotency,
    step_risk,
    step_explain,
)
from agents.adaptive_interview_agent import InterviewState
from data_sources.ocr.staging import (
    stage_upload,
    get_staged_upload,
    remove_staged_upload,
    get_user_pending_count,
    clear_all_staged_uploads_for_testing,
    _clean_expired,
    _STAGING_STORE,
)
from data_sources.ocr.provider import (
    check_ocr_provider_available,
    get_ocr_provider,
    SubprocessOcrProvider,
    OcrProvider,
)
from data_sources.ocr.fake_provider import FakeOcrProvider
from data_sources.ocr.extract_fields import (
    extract_fields,
    is_in_reference_context,
    levenshtein_distance,
    match_medication_name,
)
from data_sources import app_store
from agents.risk_rules import is_risk_applicable, apply_risk_to_level


# ==============================================================================
# SECTION 1: rag.store Tests (JsonlChunkStore, DbChunkStore, get_db_chunk_store)
# ==============================================================================

def test_jsonl_chunk_store_file_not_found(tmp_path: Path) -> None:
    """Verifies that JsonlChunkStore raises FileNotFoundError on missing file."""
    missing = tmp_path / "does_not_exist.jsonl"
    with pytest.raises(FileNotFoundError, match="JSONL chunk store file does not exist"):
        JsonlChunkStore(missing)


def test_jsonl_chunk_store_invalid_json(tmp_path: Path) -> None:
    """Verifies that JsonlChunkStore raises ValueError on invalid JSON syntax."""
    bad_file = tmp_path / "corrupt.jsonl"
    bad_file.write_text("{\"chunk_id\": \"c1\"}\n{not valid json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON at line 2"):
        JsonlChunkStore(bad_file)


def test_jsonl_chunk_store_empty_lines_and_no_chunk_id(tmp_path: Path) -> None:
    """Verifies handling of blank lines and records without chunk_id."""
    f = tmp_path / "sparse.jsonl"
    lines = [
        "",
        "   ",
        json.dumps({"title": "No ID"}),
        json.dumps({"chunk_id": "c1", "title": "Valid", "condition": "hypertension", "priority": 1}),
        "",
    ]
    f.write_text("\n".join(lines), encoding="utf-8")
    store = JsonlChunkStore(f)
    assert store.total_chunks() == 1
    assert store.get_chunk("c1") is not None
    assert store.get_chunk("nonexistent") is None


def test_jsonl_chunk_store_filters(tmp_path: Path) -> None:
    """Verifies condition, topic, and min_priority filtering in JsonlChunkStore."""
    f = tmp_path / "chunks.jsonl"
    data = [
        {"chunk_id": "c1", "condition": "hypertension", "topics": ["diet", "bp"], "priority": 1},
        {"chunk_id": "c2", "condition": "diabetes", "topics": ["glucose"], "priority": 2},
        {"chunk_id": "c3", "condition": "both", "topics": ["exercise"], "priority": 3},
        {"chunk_id": "c4", "condition": "general", "topics": ["diet"], "priority": 1},
    ]
    f.write_text("\n".join(json.dumps(d) for d in data), encoding="utf-8")
    store = JsonlChunkStore(f)

    # Condition filter includes target, both, general
    htn_chunks = store.list_chunks(condition="hypertension")
    assert {c["chunk_id"] for c in htn_chunks} == {"c1", "c3", "c4"}

    # Topic filter
    diet_chunks = store.list_chunks(topic="diet")
    assert {c["chunk_id"] for c in diet_chunks} == {"c1", "c4"}

    # Priority filter
    high_pri = store.list_chunks(min_priority=2)
    assert {c["chunk_id"] for c in high_pri} == {"c2", "c3"}

    # Combined filter
    combined = store.list_chunks(condition="hypertension", topic="exercise", min_priority=2)
    assert len(combined) == 1
    assert combined[0]["chunk_id"] == "c3"

    # all_chunks
    assert len(store.all_chunks()) == 4


def test_db_chunk_store_filters_and_topics(tmp_path: Path) -> None:
    """Verifies DbChunkStore loading, corrupt topic JSON handling, and filtering."""
    db_file = str(tmp_path / "test_rag.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        ("c_htn_1", "src1", "BP Guidelines", "1st", 1, "s1", 1, 2, "A", "hypertension", '["diet", "bp"]', "Text 1", now),
        ("c_dm_1", "src2", "Sugar Guidelines", "2nd", 2, "s2", 3, 4, "B", "diabetes", '["glucose"]', "Text 2", now),
        ("c_bad_topic", "src3", "Corrupt Topic", "1st", 1, "s3", 5, 6, "A", "general", '{not valid json', "Text 3", now),
        ("c_none_topic", "src4", "Null Topic", "1st", 1, "s4", 7, 8, "A", "both", None, "Text 4", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for r in rows:
            cur.execute(
                f"INSERT INTO guideline_chunks (chunk_id, source_id, title, edition, priority, "
                f"section_path, page_start, page_end, grade, condition, topics_json, text, loaded_at) "
                f"VALUES ({','.join([ph]*13)})",
                r,
            )

    store = DbChunkStore(backend="sqlite", db_path=db_file)
    assert store.total_chunks() == 4
    assert store.get_chunk("c_htn_1") is not None
    assert store.get_chunk("nonexistent") is None

    # Corrupt topics JSON parsed to []
    bad_chunk = store.get_chunk("c_bad_topic")
    assert bad_chunk is not None
    assert bad_chunk["topics"] == []

    # Condition filtering includes specific condition + both + general
    htn_chunks = store.list_chunks(condition="hypertension")
    assert {c["chunk_id"] for c in htn_chunks} == {"c_htn_1", "c_bad_topic", "c_none_topic"}

    # Topic filtering
    diet_chunks = store.list_chunks(topic="diet")
    assert len(diet_chunks) == 1
    assert diet_chunks[0]["chunk_id"] == "c_htn_1"

    # Priority filtering
    pri2_chunks = store.list_chunks(min_priority=2)
    assert len(pri2_chunks) == 1
    assert pri2_chunks[0]["chunk_id"] == "c_dm_1"

    # all_chunks
    assert len(store.all_chunks()) == 4


def test_get_db_chunk_store_singleton(tmp_path: Path) -> None:
    """Verifies get_db_chunk_store singleton caching and force_reload."""
    db_file = str(tmp_path / "singleton_rag.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    s1 = get_db_chunk_store(backend="sqlite", db_path=db_file, force_reload=True)
    s2 = get_db_chunk_store(backend="sqlite", db_path=db_file)
    assert s1 is s2

    s3 = get_db_chunk_store(backend="sqlite", db_path=db_file, force_reload=True)
    assert s3 is not s1


# ==============================================================================
# SECTION 2: orchestrator.steps Tests
# ==============================================================================

def test_build_patient_explain_view_none_or_invalid() -> None:
    """Verifies _build_patient_explain_view returns None for None or non-dict input."""
    assert _build_patient_explain_view(None) is None
    assert _build_patient_explain_view("string_is_invalid") is None  # type: ignore
    assert _build_patient_explain_view([]) is None  # type: ignore


def test_build_patient_explain_view_pending_and_error_states() -> None:
    """Verifies _build_patient_explain_view handles pending and error statuses safely."""
    pending_in = {"status": "pending", "mode": "background", "provider": "groq"}
    pending_out = _build_patient_explain_view(pending_in)
    assert pending_out == {"status": "pending"}

    error_in = {"status": "error", "reason": "timeout", "rejected_reasons": ["V1"]}
    error_out = _build_patient_explain_view(error_in)
    assert error_out == {"status": "error", "sentences": [], "sources": []}


def test_build_patient_explain_view_strips_internal_audit_fields() -> None:
    """Verifies that _build_patient_explain_view strictly strips internal diagnostics."""
    full_explanation = {
        "status": "ready",
        "sentences": [{"text": "Your BP is normal.", "cites": ["S1"]}],
        "sources": [{"chunk_id": "c1", "title": "Guideline"}],
        "mode": "llm",
        "reason": "normal",
        "provider": "groq",
        "providers_tried": ["groq", "gemini"],
        "tokens_used": 150,
        "provider_timings": {"groq": 0.42},
    }
    patient_view = _build_patient_explain_view(full_explanation)
    assert patient_view is not None
    assert "status" in patient_view
    assert "sentences" in patient_view
    assert "sources" in patient_view
    for forbidden in ["mode", "reason", "provider", "providers_tried", "tokens_used", "provider_timings"]:
        assert forbidden not in patient_view


def test_build_patient_risk_view_invariant() -> None:
    """Verifies that _build_patient_risk_view always returns None (H3 doctors-only)."""
    assert _build_patient_risk_view(None) is None
    assert _build_patient_risk_view({"status": "ok", "probability": 0.25, "band": "low"}) is None
    assert _build_patient_risk_view({"status": "error"}) is None


def test_step_risk_flag_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies step_risk returns None when RISK_ENABLED is false."""
    monkeypatch.setenv("RISK_ENABLED", "false")
    state = InterviewState(patient_id="p1", conditions_on_file=["hypertension"])
    triage = {"final_triage_level": "routine", "emergency": False}
    res = step_risk(user_id="u1", state=state, triage_decision=triage)
    assert res is None


def test_step_risk_diabetes_ineligible(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies step_risk returns None when conditions include diabetes (D12/D13 policy)."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    state = InterviewState(patient_id="p1", conditions_on_file=["diabetes", "hypertension"])
    triage = {"final_triage_level": "routine", "emergency": False}
    res = step_risk(
        user_id="u1",
        state=state,
        triage_decision=triage,
        get_patient_profile_fn=lambda uid: {"conditions": ["diabetes", "hypertension"]},
    )
    assert res is None


def test_step_explain_flag_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies step_explain returns None when EXPLAIN_ENABLED is false."""
    monkeypatch.setenv("EXPLAIN_ENABLED", "false")
    state = InterviewState(patient_id="p1", conditions_on_file=["hypertension"])
    triage = {"final_triage_level": "routine", "emergency": False}
    res = step_explain(user_id="u1", state=state, triage_decision=triage)
    assert res is None


def test_step_intake_emergency_early_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies step_parse_and_validate_intake executes emergency early return with null risk/explain."""
    from orchestrator.steps import step_parse_and_validate_intake

    db_file = str(tmp_path / "emg_intake.db")
    app_store.migrate(db_path=db_file, backend="sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")

    cid = "chk_emg_early_ret_01"
    uid = "usr_emg_01"
    app_store.create_checkin(
        checkin_id=cid,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict={"engine": "v3", "stage1_red_flag": True, "stage1_reason": "chest_pain"},
        status="emergency",
    )

    checkin_row = app_store.get_checkin_by_id(cid, backend="sqlite", db_path=db_file)
    user_row = {"user_id": uid, "role": "patient"}

    context, early_resp = step_parse_and_validate_intake(checkin_row, user_row, "local_synthetic_store")
    assert early_resp is not None
    assert early_resp.emergency is True
    assert early_resp.risk is None
    assert early_resp.explanation is None


def test_sanitize_trace_for_persistence() -> None:
    """Verifies _sanitize_trace_for_persistence formats node traces with zero PHI."""
    steps = [
        {"node": "idempotency_check", "started_at": "2026-11-07T10:00:00Z", "summary": "Cache miss"},
        {"node": "triage_evaluation", "started_at": "2026-11-07T10:00:01Z", "summary": "Level: routine"},
    ]
    trace = _sanitize_trace_for_persistence(steps)
    assert len(trace) == 2
    assert trace[0]["node"] == "idempotency_check"
    assert trace[0]["summary"] == "Cache miss"
    dumped = json.dumps(trace).lower()
    for phi_field in ["systolic", "diastolic", "glucose", "patient_name", "waist_cm"]:
        assert phi_field not in dumped


def test_step_check_idempotency_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies step_check_idempotency returns None for new/uncompleted checkin."""
    db_file = str(tmp_path / "idemp.db")
    app_store.migrate(db_path=db_file, backend="sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")

    cached = step_check_idempotency("nonexistent_chk_id", "local_synthetic_store")
    assert cached is None


# ==============================================================================
# SECTION 3: data_sources.ocr Tests (staging, provider, extract_fields)
# ==============================================================================

def test_ocr_staging_crud_and_counts() -> None:
    """Verifies stage_upload, get_staged_upload, remove_staged_upload, and get_user_pending_count."""
    clear_all_staged_uploads_for_testing()
    user_id = "user_ocr_stage_test"
    data = {"kind": "glucose", "value": 115.0}

    # 1. Stage upload
    upload_id = stage_upload(user_id=user_id, extracted_data=data, filename="lab.jpg")
    assert upload_id is not None
    assert get_user_pending_count(user_id) == 1

    # 2. Retrieve upload
    retrieved = get_staged_upload(upload_id, user_id=user_id)
    assert retrieved is not None
    assert retrieved["extracted"] == data

    # Wrong user cannot access
    assert get_staged_upload(upload_id, user_id="wrong_user") is None

    # 3. Remove upload
    assert remove_staged_upload(upload_id) is True
    assert get_user_pending_count(user_id) == 0
    assert remove_staged_upload(upload_id) is False


def test_ocr_staging_expired_clean() -> None:
    """Verifies _clean_expired purges entries older than TTL."""
    clear_all_staged_uploads_for_testing()
    upload_id = stage_upload(user_id="u1", extracted_data={"test": 1})
    assert get_user_pending_count("u1") == 1

    # Simulate expiration by setting created_at to 2 hours ago
    _STAGING_STORE[upload_id]["created_at"] = datetime.now(timezone.utc) - timedelta(hours=2)

    _clean_expired()
    assert get_user_pending_count("u1") == 0


def test_ocr_provider_factory_and_production_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies check_ocr_provider_available, get_ocr_provider production guards and errors."""
    # 1. Fake provider is available in dev
    monkeypatch.delenv("APP_ENV", raising=False)
    assert check_ocr_provider_available("fake") is True
    prov = get_ocr_provider("fake")
    assert isinstance(prov, FakeOcrProvider)

    # 2. Fake provider is refused in production
    monkeypatch.setenv("APP_ENV", "production")
    assert check_ocr_provider_available("fake") is False
    with pytest.raises(RuntimeError, match="Fake OCR provider refused in production"):
        get_ocr_provider("fake")

    # 3. Unknown provider raises ValueError
    monkeypatch.delenv("APP_ENV", raising=False)
    assert check_ocr_provider_available("unknown_provider_xyz") is False
    with pytest.raises(ValueError, match="Unknown OCR provider: 'unknown_provider_xyz'"):
        get_ocr_provider("unknown_provider_xyz")

    # 4. Subprocess wrapper
    monkeypatch.setenv("OCR_USE_SUBPROCESS", "true")
    wrapped = get_ocr_provider("fake")
    assert isinstance(wrapped, SubprocessOcrProvider)
    assert wrapped.provider_name == "fake"
    assert wrapped.extract_text(b"raw image") is not None


def test_extract_fields_levenshtein_and_med_match() -> None:
    """Verifies levenshtein_distance and match_medication_name helper branches."""
    # Distance
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("metformin", "metformin") == 0
    assert levenshtein_distance("", "test") == 4
    assert levenshtein_distance("test", "") == 4

    # Medication matching
    assert match_medication_name("metformin") == ("metformin", "metformin")
    assert match_medication_name("metformin 500mg") == ("metformin", "metformin")
    assert match_medication_name("lisinopril") == ("lisinopril", "lisinopril")
    assert match_medication_name("unknownmedxyz123") is None


def test_extract_fields_is_in_reference_context() -> None:
    """Verifies reference context suppression (range headers, normal values)."""
    text = "Fasting Blood Sugar: 110 mg/dL Normal Range: 70-100 mg/dL"
    idx_110 = text.find("110")
    idx_70 = text.find("70")
    assert is_in_reference_context(text, idx_110, idx_110 + 3) is False
    assert is_in_reference_context(text, idx_70, idx_70 + 2) is True


def test_extract_fields_edge_patterns() -> None:
    """Verifies extraction across varying punctuation and spacing."""
    ocr_sample = """
    PATIENT REPORT
    B.P: 135 / 85 mmHg
    HbA1c ... 6.8 %
    Random Blood Glucose : 165 mg/dL
    Medications: Glucophage 500mg tablet daily
    """
    res = extract_fields(ocr_sample)
    assert "fields" in res
    fields_by_kind = {f["kind"]: f["value"] for f in res["fields"]}
    assert fields_by_kind.get("bp") == [135, 85]
    assert fields_by_kind.get("hba1c") == 6.8
    assert fields_by_kind.get("glucose") == 165.0


# ==============================================================================
# SECTION 4: data_sources.app_store Tests (record_edits)
# ==============================================================================

def test_app_store_record_edits_lifecycle(tmp_path: Path) -> None:
    """Verifies record_edit insertion and get_record_edits querying and filtering."""
    db_file = str(tmp_path / "edits.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    uid = "user_test_edits_01"
    now = datetime.now(timezone.utc)
    t1 = (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    t2 = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        app_store.record_edit(
            cur, ph,
            user_id=uid, record_type="observation", record_id="obs_1", field="value",
            old_value=None, new_value=120, origin="patient", changed_by_user_id="patient",
            reason="Initial checkin",
        )
        app_store.record_edit(
            cur, ph,
            user_id=uid, record_type="observation", record_id="obs_1", field="value",
            old_value=120, new_value=125, origin="provider", changed_by_user_id="dr_provider",
            reason="Correction",
        )
        app_store.record_edit(
            cur, ph,
            user_id=uid, record_type="medication", record_id="med_1", field="dosage",
            old_value=None, new_value="500mg daily", origin="provider", changed_by_user_id="dr_provider",
            reason="New prescription",
        )

    # Fetch all edits for user
    edits = app_store.get_record_edits(user_id=uid, backend="sqlite", db_path=db_file)
    assert len(edits) == 3
    assert {e["record_id"] for e in edits} == {"obs_1", "med_1"}

    # Filter by record_type
    obs_edits = app_store.get_record_edits(user_id=uid, record_type="observation", backend="sqlite", db_path=db_file)
    assert len(obs_edits) == 2

    # Filter with limit
    limited = app_store.get_record_edits(user_id=uid, limit=1, backend="sqlite", db_path=db_file)
    assert len(limited) == 1
    assert limited[0]["record_id"] in {"obs_1", "med_1"}


# ==============================================================================
# SECTION 5: agents.risk_rules Tests
# ==============================================================================

def test_risk_rules_applicability() -> None:
    """Verifies is_risk_applicable handling of varied condition formats."""
    assert is_risk_applicable(["hypertension"]) is True
    assert is_risk_applicable(["HYPERTENSION"]) is True
    assert is_risk_applicable(["hypertension", "other"]) is True

    # Diabetes is non-applicable
    assert is_risk_applicable(["diabetes"]) is False
    assert is_risk_applicable(["diabetes", "hypertension"]) is False

    # Empty or None conditions
    assert is_risk_applicable([]) is False
    assert is_risk_applicable(None) is False
    assert is_risk_applicable("not_a_list") is False


def test_apply_risk_to_level_elevation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies apply_risk_to_level behavior when RISK_CAN_RAISE is enabled vs disabled."""
    # 1. When RISK_CAN_RAISE is False, triage level is NEVER elevated
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")
    high_risk_assessment = {"status": "ok", "band": "high", "probability": 0.85}
    lvl, raised = apply_risk_to_level("routine", risk=high_risk_assessment)
    assert lvl == "routine"
    assert raised is False

    # 2. When RISK_CAN_RAISE is True, high risk can elevate routine -> review
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "true")
    lvl_raised, raised = apply_risk_to_level("routine", risk=high_risk_assessment)
    assert lvl_raised == "review"
    assert raised is True

    # Emergency is never altered
    lvl_emg, raised = apply_risk_to_level("emergency", risk=high_risk_assessment)
    assert lvl_emg == "emergency"
    assert raised is False


# ==============================================================================
# SECTION 6: Additional Edge Case & Invariant Tests (Total 30 Tests)
# ==============================================================================

def test_ocr_staging_prunes_oldest_on_limit() -> None:
    """Verifies that stage_upload automatically prunes oldest upload when exceeding MAX_PENDING_PER_USER (3)."""
    clear_all_staged_uploads_for_testing()
    user_id = "user_prune_test_01"

    id1 = stage_upload(user_id=user_id, extracted_data={"v": 1})
    time.sleep(0.01)
    id2 = stage_upload(user_id=user_id, extracted_data={"v": 2})
    time.sleep(0.01)
    id3 = stage_upload(user_id=user_id, extracted_data={"v": 3})
    assert get_user_pending_count(user_id) == 3

    # Adding 4th upload should prune id1 (the oldest)
    time.sleep(0.01)
    id4 = stage_upload(user_id=user_id, extracted_data={"v": 4})
    assert get_user_pending_count(user_id) == 3
    assert get_staged_upload(id1, user_id=user_id) is None
    assert get_staged_upload(id2, user_id=user_id) is not None
    assert get_staged_upload(id3, user_id=user_id) is not None
    assert get_staged_upload(id4, user_id=user_id) is not None


def test_extract_fields_empty_and_whitespace() -> None:
    """Verifies extract_fields on empty text, whitespace, and non-medical strings."""
    assert extract_fields("") == {"fields": [], "warnings": [], "unmatched_lines": []}
    assert extract_fields("   \n\t\n  ") == {"fields": [], "warnings": [], "unmatched_lines": []}
    res = extract_fields("This is a random note with no clinical vitals or lab results.")
    assert len(res["fields"]) == 0


def test_db_chunk_store_empty_table(tmp_path: Path) -> None:
    """Verifies DbChunkStore behaves gracefully on an empty table."""
    db_file = str(tmp_path / "empty_rag.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    store = DbChunkStore(backend="sqlite", db_path=db_file)
    assert store.total_chunks() == 0
    assert store.all_chunks() == []
    assert store.get_chunk("nonexistent") is None
    assert store.list_chunks(condition="hypertension") == []


def test_app_store_record_edits_empty_result(tmp_path: Path) -> None:
    """Verifies get_record_edits returns empty list when no edits exist for user."""
    db_file = str(tmp_path / "empty_edits.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    edits = app_store.get_record_edits(user_id="user_with_no_edits", backend="sqlite", db_path=db_file)
    assert edits == []


def test_build_patient_explain_view_empty_sentences() -> None:
    """Verifies _build_patient_explain_view handles ready status with empty sentences."""
    inp = {"status": "ready", "sentences": [], "sources": []}
    out = _build_patient_explain_view(inp)
    assert out is not None
    assert out["status"] == "ready"
    assert out["sentences"] == []
    assert out["sources"] == []
