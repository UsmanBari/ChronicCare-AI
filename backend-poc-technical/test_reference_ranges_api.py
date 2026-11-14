"""
Test Reference Ranges API (F2 / Doctor Decision D5).
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from agents.reference_ranges import REFERENCE_RANGES, is_reading_in_normal_range
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
    assert data["disclaimer"] == "Normal range used by this app"
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
    assert keys["glucose_fasting"]["low"] == 70.0
    assert keys["glucose_fasting"]["high"] == 130.0
    assert "ADA Standards of Care" in keys["glucose_fasting"]["source_label"]

    assert "glucose_post_meal" in keys
    assert keys["glucose_post_meal"]["low"] == 70.0
    assert keys["glucose_post_meal"]["high"] == 180.0


def test_reference_ranges_authenticated_provider(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-ref-prov", email="refprov@demo.com")
    bootstrap_provider(client, tok)
    headers = {"Authorization": f"Bearer {tok}"}

    resp = client.get("/api/reference-ranges", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["disclaimer"] == "Normal range used by this app"
    assert len(data["ranges"]) == 4


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
    assert glu_fast["low"] == 3.9
    assert glu_fast["high"] == 7.2
    assert glu_fast["low_mg_dl"] == 70.0
    assert glu_fast["high_mg_dl"] == 130.0
