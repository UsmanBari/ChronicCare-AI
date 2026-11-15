"""
Test Reference Ranges API & In-Target Logic (G3 / Doctor Decisions D5 & D6).
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from agents.reference_ranges import (
    REFERENCE_RANGES,
    is_reading_in_normal_range,
    is_reading_in_target_range,
)
from test_checkin_api import (
    rsa_key_pair,
    x509_cert_pem,
    setup_test_environment,
    create_test_token,
    bootstrap_patient,
)


def bootstrap_provider(client: TestClient, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/role", headers=headers, json={"role": "provider"})


def test_reference_ranges_unauthenticated():
    client = TestClient(app)
    resp = client.get("/api/reference-ranges")
    assert resp.status_code in (401, 403)


def test_reference_ranges_authenticated_patient(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-ref-pat", email="refpat@demo.com")
    bootstrap_patient(client, tok, conditions=["diabetes", "hypertension"])
    headers = {"Authorization": f"Bearer {tok}"}

    resp = client.get("/api/reference-ranges", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["disclaimer"] == "Target range used by this app"
    assert "ranges" in data
    keys = {r["key"]: r for r in data["ranges"]}
    assert "blood_pressure_systolic" in keys
    assert keys["blood_pressure_systolic"]["low"] == 90.0
    assert keys["blood_pressure_systolic"]["high"] == 140.0
    assert "2025 AHA/ACC" in keys["blood_pressure_systolic"]["source_label"]

    assert "blood_pressure_diastolic" in keys
    assert keys["blood_pressure_diastolic"]["low"] == 60.0
    assert keys["blood_pressure_diastolic"]["high"] == 90.0

    assert "glucose_fasting" in keys
    assert keys["glucose_fasting"]["low"] == 90.0
    assert keys["glucose_fasting"]["high"] == 125.0
    assert "doctor on record" in keys["glucose_fasting"]["source_label"]

    assert "glucose_post_meal" in keys
    assert keys["glucose_post_meal"]["low"] == 125.0
    assert keys["glucose_post_meal"]["high"] == 200.0

    assert "glucose_random" in keys
    assert keys["glucose_random"]["low"] == 90.0
    assert keys["glucose_random"]["high"] == 200.0


def test_reference_ranges_authenticated_provider(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-ref-prov", email="refprov@demo.com")
    bootstrap_provider(client, tok)
    headers = {"Authorization": f"Bearer {tok}"}

    resp = client.get("/api/reference-ranges", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["disclaimer"] == "Target range used by this app"
    assert len(data["ranges"]) == 5


def test_reference_ranges_mmol_conversion(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-ref-mmol", email="refmmol@demo.com")
    bootstrap_patient(client, tok, conditions=["diabetes"])
    headers = {"Authorization": f"Bearer {tok}"}

    resp = client.get("/api/reference-ranges?unit=mmol/L", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    keys = {r["key"]: r for r in data["ranges"]}
    glu_fast = keys["glucose_fasting"]
    assert glu_fast["unit"] == "mmol/L"
    assert glu_fast["low"] == 5.0
    assert glu_fast["high"] == 6.9
    assert glu_fast["low_mg_dl"] == 90.0
    assert glu_fast["high_mg_dl"] == 125.0

    glu_pm = keys["glucose_post_meal"]
    assert glu_pm["unit"] == "mmol/L"
    assert glu_pm["low"] == 6.9
    assert glu_pm["high"] == 11.1
    assert glu_pm["low_mg_dl"] == 125.0
    assert glu_pm["high_mg_dl"] == 200.0


def test_is_reading_in_target_range_doctor_decision_d6():
    # 1. Below 90 mg/dL in any context must be False (below target, dizziness risk, goes to review)
    assert not is_reading_in_normal_range("glucose", 89.0, context="fasting")
    assert not is_reading_in_normal_range("glucose", 85.0, context="after_meal")
    assert not is_reading_in_normal_range("glucose", 75.0, context="random")
    assert not is_reading_in_normal_range("glucose", 50.0)

    # 2. Fasting: target 90–125 mg/dL
    assert is_reading_in_normal_range("glucose", 90.0, context="fasting")
    assert is_reading_in_normal_range("glucose", 110.0, context="fasting")
    assert is_reading_in_normal_range("glucose", 125.0, context="fasting")
    assert not is_reading_in_normal_range("glucose", 126.0, context="fasting")

    # 3. Post-meal: doctor target 125–200 mg/dL, with 90–124 accepted as in-target under D5
    assert is_reading_in_normal_range("glucose", 90.0, context="after_meal")
    assert is_reading_in_normal_range("glucose", 100.0, context="after_meal")
    assert is_reading_in_normal_range("glucose", 124.0, context="after_meal")
    assert is_reading_in_normal_range("glucose", 150.0, context="after_meal")
    assert is_reading_in_normal_range("glucose", 200.0, context="after_meal")
    assert not is_reading_in_normal_range("glucose", 201.0, context="after_meal")

    # 4. Random / unspecified: 90–200 mg/dL
    assert is_reading_in_normal_range("glucose", 90.0)
    assert is_reading_in_normal_range("glucose", 150.0)
    assert is_reading_in_normal_range("glucose", 200.0)
    assert not is_reading_in_normal_range("glucose", 205.0)

    # 5. BP ranges (unchanged routine targets)
    assert is_reading_in_normal_range("blood_pressure_systolic", 120.0)
    assert not is_reading_in_normal_range("blood_pressure_systolic", 85.0)
    assert not is_reading_in_normal_range("blood_pressure_systolic", 140.0)

    assert is_reading_in_normal_range("blood_pressure_diastolic", 80.0)
    assert not is_reading_in_normal_range("blood_pressure_diastolic", 55.0)
    assert not is_reading_in_normal_range("blood_pressure_diastolic", 90.0)

    # Alias check
    assert is_reading_in_target_range("glucose", 110.0)
