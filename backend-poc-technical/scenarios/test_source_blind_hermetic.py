"""
Hermetic Source-Blind Acceptance Test (Milestone 2)

Proves structural and type equivalence between Connected Mode (FHIR) and Isolated Mode (Local Store)
using pre-recorded sanitized responses in scenarios/fixtures_recorded/fhir_patient_bundle.json.
Guarantees 100% hermetic, zero-network execution for CI.
"""

import os
import sys
import json
from typing import Dict, Any
from unittest.mock import MagicMock

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources.data_source import get_patient_bundle
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication


def test_source_blind_hermetic(monkeypatch):
    """
    Executes source-blind bundle retrieval and equivalence assertions
    without contacting external live endpoints.
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixture_path = os.path.join(script_dir, "scenarios", "fixtures_recorded", "fhir_patient_bundle.json")
    
    with open(fixture_path, "r") as f:
        fixtures = json.load(f)

    # Monkeypatch requests.get to return recorded fixtures
    def mock_requests_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        if "/Patient/" in url or url.endswith("/Patient"):
            mock_resp.json.return_value = fixtures["patient"]
        elif "/Observation" in url:
            mock_resp.json.return_value = {
                "resourceType": "Bundle",
                "entry": [{"resource": obs} for obs in fixtures["observations"]],
            }
        elif "/MedicationRequest" in url:
            mock_resp.json.return_value = {
                "resourceType": "Bundle",
                "entry": [{"resource": med} for med in fixtures["medication_requests"]],
            }
        else:
            mock_resp.json.return_value = {}
        return mock_resp

    import requests
    monkeypatch.setattr(requests, "get", mock_requests_get)

    fhir_patient_id = "768be7ac-743f-4c24-aa0f-fed5a3a38b6a"
    local_patient_id = "LOCAL-PATIENT-001"
    db_path = os.path.join(script_dir, "local_store.db")

    connected_bundle = get_patient_bundle(fhir_patient_id, mode="connected")
    isolated_bundle = get_patient_bundle(local_patient_id, mode="isolated", db_path=db_path)

    EXPECTED_PATIENT_FIELDS = {"patient_id", "name", "date_of_birth"}
    EXPECTED_OBSERVATION_FIELDS = {"patient_id", "observation_type", "value", "unit", "timestamp", "source", "source_record_id"}
    EXPECTED_MEDICATION_FIELDS = {"patient_id", "medication_name", "status", "dosage", "timestamp", "source", "source_record_id"}

    # Assert model types for Connected Bundle
    assert isinstance(connected_bundle["patient"], NormalizedPatient)
    assert all(isinstance(o, NormalizedObservation) for o in connected_bundle["observations"])
    assert all(isinstance(m, NormalizedMedication) for m in connected_bundle["medications"])

    # Assert model types for Isolated Bundle
    assert isinstance(isolated_bundle["patient"], NormalizedPatient)
    assert all(isinstance(o, NormalizedObservation) for o in isolated_bundle["observations"])
    assert all(isinstance(m, NormalizedMedication) for m in isolated_bundle["medications"])

    # Assert schema fields
    assert set(connected_bundle["patient"].to_dict().keys()) == EXPECTED_PATIENT_FIELDS
    assert set(isolated_bundle["patient"].to_dict().keys()) == EXPECTED_PATIENT_FIELDS

    for obs in connected_bundle["observations"] + isolated_bundle["observations"]:
        assert set(obs.to_dict().keys()) == EXPECTED_OBSERVATION_FIELDS

    for med in connected_bundle["medications"] + isolated_bundle["medications"]:
        assert set(med.to_dict().keys()) == EXPECTED_MEDICATION_FIELDS
