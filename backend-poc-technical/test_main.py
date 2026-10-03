"""
API Endpoint Tests for ChronicCare AI FastAPI backend
"""

import os
import sys
from fastapi.testclient import TestClient

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from scenarios.fixtures import CLEAN_AGREE_PAIR, CONFLICT_PAIR

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chroniccare-backend"


def test_reconcile_endpoint_clean_pair():
    bundle_a = {
        "patient": CLEAN_AGREE_PAIR["bundle_a"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CLEAN_AGREE_PAIR["bundle_a"]["observations"]],
        "medications": [m.to_dict() for m in CLEAN_AGREE_PAIR["bundle_a"]["medications"]],
    }
    bundle_b = {
        "patient": CLEAN_AGREE_PAIR["bundle_b"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CLEAN_AGREE_PAIR["bundle_b"]["observations"]],
        "medications": [m.to_dict() for m in CLEAN_AGREE_PAIR["bundle_b"]["medications"]],
    }
    
    payload = {
        "bundle_a": bundle_a,
        "bundle_b": bundle_b,
    }
    
    response = client.post("/api/reconcile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "SYNTHETIC-PATIENT-MATCH-001"
    assert data["summary"]["conflicts"] == 0
    assert data["summary"]["agreements"] == 5


def test_verify_endpoint_conflict_pair():
    bundle_a = {
        "patient": CONFLICT_PAIR["bundle_a"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CONFLICT_PAIR["bundle_a"]["observations"]],
        "medications": [m.to_dict() for m in CONFLICT_PAIR["bundle_a"]["medications"]],
    }
    bundle_b = {
        "patient": CONFLICT_PAIR["bundle_b"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CONFLICT_PAIR["bundle_b"]["observations"]],
        "medications": [m.to_dict() for m in CONFLICT_PAIR["bundle_b"]["medications"]],
    }
    
    # 1. Reconcile
    recon_response = client.post("/api/reconcile", json={"bundle_a": bundle_a, "bundle_b": bundle_b})
    assert recon_response.status_code == 200
    recon_data = recon_response.json()

    # 2. Verify with reconciliation_result
    verify_response = client.post("/api/verify", json={"reconciliation_result": recon_data})
    assert verify_response.status_code == 200
    v_data = verify_response.json()
    assert v_data["patient_id"] == "SYNTHETIC-PATIENT-MATCH-002"
    assert v_data["summary"]["requires_review"] > 0
    assert v_data["summary"]["severity_high"] > 0


def test_reconcile_identity_mismatch_error():
    bundle_a = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    bundle_b = {
        "patient": {"patient_id": "PATIENT-B", "name": "Bob"},
        "observations": [],
        "medications": [],
    }
    
    response = client.post("/api/reconcile", json={"bundle_a": bundle_a, "bundle_b": bundle_b})
    assert response.status_code == 400
    assert "Patient Identity Contract Violation" in response.json()["detail"]
