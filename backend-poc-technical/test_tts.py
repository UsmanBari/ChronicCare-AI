"""
Hermetic Tests for Meta MMS-TTS Speech Synthesis Service (PR I4-I).
Verifies:
1. Feature flag gating: TTS_ENABLED=false (default) returns 404 on all speech endpoints.
2. Ownership and authorization: Only the check-in owner can request speech (cross-patient rejected with 403/404).
3. Safety invariant: Speaks ONLY already-shown explanation sentences (no client free-text input).
4. Language handling:
   - 'en': speaks English sentences.
   - 'ur': speaks Urdu script sentences.
   - 'roman_ur': resolves to Urdu script version of same template key.
   - 'roman_ur' with no script mapping returns 409 Conflict.
5. Disk caching: Audio cached per (checkin_id, language) under cache dir; cache hit skips re-synthesis.
6. Emergency 1122 speech: Pre-cached, instant playback for Urdu and English.
7. Fake synthesizer: Pure Python standard library WAV generator runs hermetically in CI without model download.
"""

import io
import os
import tempfile
import wave

import main
import pytest
from data_sources import app_store
from fastapi.testclient import TestClient
from voice.tts_service import (
    RomanUrduVoiceUnavailableError,
    TtsDisabledError,
    generate_fake_wav,
    get_checkin_speech,
    get_emergency_speech,
    is_tts_enabled,
    resolve_explanation_text_to_speak,
    set_force_fake_synthesizer,
)


@pytest.fixture(autouse=True)
def force_fake_tts(monkeypatch):
    """Ensures all tests use the in-memory fake synthesizer with zero model downloads or network calls."""
    set_force_fake_synthesizer(True)
    yield
    set_force_fake_synthesizer(False)


@pytest.fixture
def temp_db(monkeypatch):
    """Hermetic SQLite database fixture migrated to latest schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name

    monkeypatch.setenv("LOCAL_DB_PATH", path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    app_store.migrate(backend="sqlite", db_path=path)

    yield path

    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def api_client(temp_db):
    """TestClient wired to hermetic SQLite database with dependency overrides cleared after."""
    client = TestClient(main.app)
    yield client
    main.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Feature Flag & Pure WAV Generation Tests
# ---------------------------------------------------------------------------

def test_tts_flag_off_by_default(monkeypatch):
    """TTS_ENABLED defaults to False when unset."""
    monkeypatch.delenv("TTS_ENABLED", raising=False)
    assert is_tts_enabled() is False


def test_fake_wav_generator_produces_valid_riff_pcm():
    """Validates that generate_fake_wav outputs valid 16kHz mono 16-bit PCM WAV."""
    wav_bytes = generate_fake_wav("Test speech output", sample_rate=16000, duration_seconds=0.25)
    assert len(wav_bytes) > 44
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"

    # Verify with standard wave module
    bio = io.BytesIO(wav_bytes)
    with wave.open(bio, "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 16000
        assert w.getnframes() > 0


def test_tts_disabled_raises_error_when_flag_off(monkeypatch):
    """Direct service functions raise TtsDisabledError when TTS_ENABLED is False."""
    monkeypatch.delenv("TTS_ENABLED", raising=False)
    with pytest.raises(TtsDisabledError):
        get_emergency_speech("ur")


# ---------------------------------------------------------------------------
# 2. Safety Invariant: Speaks ONLY Stored Finalized Sentences
# ---------------------------------------------------------------------------

def test_resolve_explanation_text_enforces_stored_sentences_only(temp_db):
    """Verifies text to speak is strictly retrieved from finalized checkin explanation."""
    # Seed check-in and explanation
    checkin_id = "chk-tts-auth-1"
    patient_id = "pat-tts-1"

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        state_dict={"language": "en"},
        status="complete",
        db_path=temp_db,
    )

    # Store explanation with explicit sentences
    expl = {
        "status": "ready",
        "language": "en",
        "sentences": [
            {"text": "Your fasting glucose is slightly elevated.", "cites": ["S1"]},
            {"text": "Maintain your recommended dietary routine.", "cites": ["S2"]},
        ],
        "sources": [{"chunk_id": "c1", "title": "ADA 2026"}],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    # Resolve text
    spoken_text, resolved_lang = resolve_explanation_text_to_speak(
        checkin_id=checkin_id,
        current_user_id=patient_id,
        db_path=temp_db,
    )
    assert spoken_text == "Your fasting glucose is slightly elevated. Maintain your recommended dietary routine."
    assert resolved_lang == "en"


def test_resolve_explanation_rejects_cross_patient_access(temp_db):
    """A user cannot access or speak another patient's check-in explanation."""
    checkin_id = "chk-tts-cross"
    patient_id = "pat-tts-real-owner"
    attacker_id = "pat-tts-attacker"

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        state_dict={"language": "en"},
        status="complete",
        db_path=temp_db,
    )

    with pytest.raises(PermissionError):
        resolve_explanation_text_to_speak(
            checkin_id=checkin_id,
            current_user_id=attacker_id,
            db_path=temp_db,
        )


def test_roman_urdu_resolves_to_urdu_script_template(temp_db):
    """Roman Urdu check-in with template_key resolves to Urdu script version for Meta MMS."""
    checkin_id = "chk-tts-roman"
    patient_id = "pat-tts-roman"

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        state_dict={"language": "roman_ur", "intakes": [{"systolic": "165", "diastolic": "98"}]},
        status="complete",
        db_path=temp_db,
    )

    expl = {
        "status": "ready",
        "language": "roman_ur",
        "template_key": "bp_urgent",
        "sentences": [
            {"text": "Aap ka blood pressure 165/98 mmHg Stage 2 barhao zahir karta hai.", "cites": []}
        ],
        "sources": [],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    spoken_text, resolved_lang = resolve_explanation_text_to_speak(
        checkin_id=checkin_id,
        current_user_id=patient_id,
        requested_language="roman_ur",
        db_path=temp_db,
    )
    # Must resolve to Urdu script for MMS Urdu model
    assert resolved_lang == "ur"
    assert "اسٹیج 2" in spoken_text or "بلڈ پریشر" in spoken_text


def test_roman_urdu_without_script_template_raises_conflict(temp_db):
    """Roman Urdu text with no template key mapping raises RomanUrduVoiceUnavailableError."""
    checkin_id = "chk-tts-roman-no-key"
    patient_id = "pat-tts-roman-no-key"

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        state_dict={"language": "roman_ur"},
        status="complete",
        db_path=temp_db,
    )

    expl = {
        "status": "ready",
        "language": "roman_ur",
        "template_key": None,  # No template key
        "sentences": [{"text": "Yeh Roman Urdu text hai.", "cites": []}],
        "sources": [],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    with pytest.raises(RomanUrduVoiceUnavailableError):
        resolve_explanation_text_to_speak(
            checkin_id=checkin_id,
            current_user_id=patient_id,
            requested_language="roman_ur",
            db_path=temp_db,
        )


# ---------------------------------------------------------------------------
# 3. Audio Caching Tests
# ---------------------------------------------------------------------------

def test_checkin_speech_caching(temp_db, monkeypatch, tmp_path):
    """Verifies WAV output is cached on disk and reused on repeat calls."""
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))

    checkin_id = "chk-tts-cache"
    patient_id = "pat-tts-cache"

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=patient_id,
        mode="isolated",
        record_patient_id=patient_id,
        state_dict={"language": "en"},
        status="complete",
        db_path=temp_db,
    )

    expl = {
        "status": "ready",
        "language": "en",
        "sentences": [{"text": "Your readings are within target.", "cites": []}],
        "sources": [],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    # First call: synthesizes and writes cache
    wav_1 = get_checkin_speech(checkin_id, patient_id, db_path=temp_db)
    assert len(wav_1) > 44

    expected_cache_file = tmp_path / "tts_cache" / f"checkin_{checkin_id}_en.wav"
    assert expected_cache_file.is_file()

    # Second call: reads directly from cache file
    wav_2 = get_checkin_speech(checkin_id, patient_id, db_path=temp_db)
    assert wav_1 == wav_2


def test_emergency_speech_pre_cached(monkeypatch, tmp_path):
    """Verifies fixed 1122 emergency speech can be synthesized and cached."""
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))

    wav_ur = get_emergency_speech("ur")
    assert len(wav_ur) > 44
    assert (tmp_path / "tts_cache" / "emergency_1122_ur.wav").is_file()

    wav_en = get_emergency_speech("en")
    assert len(wav_en) > 44
    assert (tmp_path / "tts_cache" / "emergency_1122_en.wav").is_file()


# ---------------------------------------------------------------------------
# 4. REST API Endpoints Tests
# ---------------------------------------------------------------------------

def test_speech_endpoints_return_404_when_flag_off(api_client, monkeypatch):
    """When TTS_ENABLED is False (code default), speech endpoints return 404."""
    monkeypatch.delenv("TTS_ENABLED", raising=False)
    patient_user = {"user_id": "p-tts-1", "role": "patient", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: patient_user

    # Checkin speech endpoint -> 404
    resp_chk = api_client.post("/api/checkins/any-id/speech")
    assert resp_chk.status_code == 404

    # Emergency speech endpoint -> 404
    resp_emg = api_client.post("/api/emergency/speech")
    assert resp_emg.status_code == 404


def test_api_checkin_speech_workflow(api_client, temp_db, monkeypatch, tmp_path):
    """Verifies end-to-end HTTP request for check-in explanation speech."""
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))

    patient_user = {"user_id": "p-tts-api", "role": "patient", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: patient_user

    checkin_id = "chk-tts-api-1"
    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id="p-tts-api",
        mode="isolated",
        record_patient_id="p-tts-api",
        state_dict={"language": "ur"},
        status="complete",
        db_path=temp_db,
    )

    expl = {
        "status": "ready",
        "language": "ur",
        "sentences": [{"text": "آپ کا بلڈ پریشر معمول کے مطابق ہے۔", "cites": []}],
        "sources": [],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    resp = api_client.post(f"/api/checkins/{checkin_id}/speech")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert len(resp.content) > 44
    assert resp.content[:4] == b"RIFF"


def test_api_checkin_speech_roman_urdu_conflict(api_client, temp_db, monkeypatch):
    """When a Roman Urdu checkin cannot be mapped to an Urdu script template, returns 409."""
    monkeypatch.setenv("TTS_ENABLED", "true")

    patient_user = {"user_id": "p-tts-api-roman", "role": "patient", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: patient_user

    checkin_id = "chk-tts-roman-fail"
    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id="p-tts-api-roman",
        mode="isolated",
        record_patient_id="p-tts-api-roman",
        state_dict={"language": "roman_ur"},
        status="complete",
        db_path=temp_db,
    )

    expl = {
        "status": "ready",
        "language": "roman_ur",
        "template_key": None,
        "sentences": [{"text": "Roman text without script version", "cites": []}],
        "sources": [],
    }
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        explanation=expl,
        db_path=temp_db,
    )

    resp = api_client.post(f"/api/checkins/{checkin_id}/speech?lang=roman_ur")
    assert resp.status_code == 409
    assert "voice not available for Roman Urdu text" in resp.json()["detail"]


def test_api_emergency_speech_endpoint(api_client, monkeypatch, tmp_path):
    """Verifies emergency speech endpoint returns audio/wav."""
    monkeypatch.setenv("TTS_ENABLED", "true")
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))

    patient_user = {"user_id": "p-emg-tts", "role": "patient", "status": "active"}
    main.app.dependency_overrides[main.get_current_user] = lambda: patient_user

    resp_ur = api_client.post("/api/emergency/speech?lang=ur")
    assert resp_ur.status_code == 200
    assert resp_ur.headers["content-type"] == "audio/wav"
    assert resp_ur.content[:4] == b"RIFF"

    resp_en = api_client.post("/api/emergency/speech?lang=en")
    assert resp_en.status_code == 200
    assert resp_en.headers["content-type"] == "audio/wav"
