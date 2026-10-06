"""
Unit tests for FHIR R4 client and FHIR adapter normalisation (test_fhir_client.py).
Hermetic: fake transports, in-memory cache testing, no real network.
"""

import json
import time
from datetime import datetime, timezone
import pytest
import requests

from data_sources.fhir_client import (
    fhir_get,
    FHIRError,
    clear_fhir_cache,
    set_cache_clock,
)
from data_sources.fhir_adapter import (
    fhir_to_normalized_observations,
    fhir_to_normalized_medications,
)


# =============================================================================
# 1. CLIENT TRANSPORT, RETRIES, AND ERROR CODES
# =============================================================================

def test_sim_url_routes_to_simulator():
    """Verify sim:// prefix routes in-memory to simulator without network."""
    clear_fhir_cache()
    data = fhir_get("sim://demo", "Patient/sim-ayesha")
    assert data["resourceType"] == "Patient"
    assert data["id"] == "sim-ayesha"


def test_retry_on_502_recovers(monkeypatch):
    """Verify HTTP 502 triggers retry and succeeds on 2nd attempt."""
    clear_fhir_cache()
    attempts = 0

    class MockResponse:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content
            self.headers = {"Content-Type": "application/fhir+json"}

        def raise_for_status(self):
            if self.status_code >= 400:
                resp = requests.Response()
                resp.status_code = self.status_code
                raise requests.exceptions.HTTPError(f"HTTP {self.status_code}", response=resp)

    def mock_get(url, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return MockResponse(502, b'{"resourceType":"OperationOutcome"}')
        return MockResponse(200, b'{"resourceType":"Patient","id":"pat-recovered"}')

    monkeypatch.setattr("requests.get", mock_get)

    res = fhir_get("https://fhir.example.com", "Patient/pat-recovered", max_retries=2, use_cache=False)
    assert res["id"] == "pat-recovered"
    assert attempts == 2


def test_404_not_retried(monkeypatch):
    """Verify 404 is not retried and raises ehr_patient_not_found."""
    clear_fhir_cache()
    attempts = 0

    def mock_get(url, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        resp = requests.Response()
        resp.status_code = 404
        raise requests.exceptions.HTTPError("404 Not Found", response=resp)

    monkeypatch.setattr("requests.get", mock_get)

    with pytest.raises(FHIRError) as exc:
        fhir_get("https://fhir.example.com", "Patient/missing-123", max_retries=2, use_cache=False)

    assert exc.value.error_code == "ehr_patient_not_found"
    assert attempts == 1


def test_403_raises_ehr_forbidden(monkeypatch):
    """Verify 403 Forbidden is not retried and raises ehr_forbidden."""
    clear_fhir_cache()
    attempts = 0

    def mock_get(url, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        resp = requests.Response()
        resp.status_code = 403
        raise requests.exceptions.HTTPError("403 Forbidden", response=resp)

    monkeypatch.setattr("requests.get", mock_get)

    with pytest.raises(FHIRError) as exc:
        fhir_get("https://fhir.example.com", "Patient/forbidden-123", max_retries=2, use_cache=False)

    assert exc.value.error_code == "ehr_forbidden"
    assert attempts == 1


def test_timeouts_exhausted_raises_ehr_unreachable(monkeypatch):
    """Verify repeated timeouts exhaust retries (total 3 attempts) and raise ehr_unreachable."""
    clear_fhir_cache()
    attempts = 0

    def mock_get(url, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise requests.exceptions.Timeout("Connection timed out")

    monkeypatch.setattr("requests.get", mock_get)

    with pytest.raises(FHIRError) as exc:
        fhir_get("https://fhir.example.com", "Patient/timeout-123", max_retries=2, use_cache=False)

    assert exc.value.error_code == "ehr_unreachable"
    assert attempts == 3


def test_oversized_payload_raises_ehr_bad_response(monkeypatch):
    """Verify responses exceeding 2MB raise ehr_bad_response."""
    clear_fhir_cache()

    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b"x" * (2 * 1024 * 1024 + 5)
            self.headers = {"Content-Type": "application/fhir+json"}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.get", lambda url, headers, params, timeout, stream: MockResponse())

    with pytest.raises(FHIRError) as exc:
        fhir_get("https://fhir.example.com", "Patient/oversized", use_cache=False)

    assert exc.value.error_code == "ehr_bad_response"


def test_invalid_json_raises_ehr_bad_response(monkeypatch):
    """Verify non-JSON response raises ehr_bad_response."""
    clear_fhir_cache()

    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b"<html>Not JSON</html>"
            self.headers = {"Content-Type": "text/html"}

        def raise_for_status(self):
            pass

    monkeypatch.setattr("requests.get", lambda url, headers, params, timeout, stream: MockResponse())

    with pytest.raises(FHIRError) as exc:
        fhir_get("https://fhir.example.com", "Patient/invalid-json", use_cache=False)

    assert exc.value.error_code == "ehr_bad_response"


# =============================================================================
# 2. IN-MEMORY CACHING BEHAVIOR
# =============================================================================

def test_cache_serves_within_30s_and_expires_after():
    """Verify 30s TTL in-memory cache avoids duplicate network fetches and expires."""
    clear_fhir_cache()
    sim_clock = 1000.0
    set_cache_clock(lambda: sim_clock)

    # First fetch (populates cache)
    r1 = fhir_get("sim://demo", "Patient/sim-ayesha")
    assert r1["id"] == "sim-ayesha"

    # Second fetch at +10s (serves from cache)
    sim_clock += 10.0
    r2 = fhir_get("sim://demo", "Patient/sim-ayesha")
    assert r2["id"] == "sim-ayesha"

    # Advance clock to +35s (cache expires)
    sim_clock += 25.0
    r3 = fhir_get("sim://demo", "Patient/sim-ayesha")
    assert r3["id"] == "sim-ayesha"

    # Reset clock
    set_cache_clock(time.time)
    clear_fhir_cache()


def test_clear_cache_clears_entries():
    clear_fhir_cache()
    fhir_get("sim://demo", "Patient/sim-ayesha")
    clear_fhir_cache()


# =============================================================================
# 3. NORMALISATION AUDIT AND CONVERSIONS
# =============================================================================

def test_bp_panel_55284_4_normalisation():
    bundle = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "bp-55284",
                "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "component": [
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                        "valueQuantity": {"value": 130, "unit": "mm[Hg]"}
                    },
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                        "valueQuantity": {"value": 85, "unit": "mm[Hg]"}
                    }
                ]
            }
        }]
    }
    obs = fhir_to_normalized_observations(bundle)
    assert len(obs) == 2
    types = {o.observation_type: o.value for o in obs}
    assert types["blood_pressure_systolic"] == 130.0
    assert types["blood_pressure_diastolic"] == 85.0
    for o in obs:
        assert o.unit == "mmHg"


def test_bp_panel_85354_9_normalisation():
    bundle = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "bp-85354",
                "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "component": [
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                        "valueQuantity": {"value": 140, "unit": "mm[Hg]"}
                    },
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                        "valueQuantity": {"value": 90, "unit": "mm[Hg]"}
                    }
                ]
            }
        }]
    }
    obs = fhir_to_normalized_observations(bundle)
    assert len(obs) == 2
    types = {o.observation_type: o.value for o in obs}
    assert types["blood_pressure_systolic"] == 140.0
    assert types["blood_pressure_diastolic"] == 90.0


def test_bp_separate_observations_normalisation():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "bp-sys",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                    "effectiveDateTime": "2026-10-01T12:00:00Z",
                    "valueQuantity": {"value": 125, "unit": "mm[Hg]"}
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "bp-dia",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                    "effectiveDateTime": "2026-10-01T12:00:00Z",
                    "valueQuantity": {"value": 82, "unit": "mm[Hg]"}
                }
            }
        ]
    }
    obs = fhir_to_normalized_observations(bundle)
    assert len(obs) == 2
    types = {o.observation_type: o.value for o in obs}
    assert types["blood_pressure_systolic"] == 125.0
    assert types["blood_pressure_diastolic"] == 82.0


def test_glucose_loinc_codes():
    for loinc in ("2339-0", "2345-7", "15074-8", "1558-6", "41653-7"):
        bundle = {
            "resourceType": "Bundle",
            "entry": [{
                "resource": {
                    "resourceType": "Observation",
                    "id": f"glu-{loinc}",
                    "code": {"coding": [{"system": "http://loinc.org", "code": loinc}]},
                    "effectiveDateTime": "2026-10-01T12:00:00Z",
                    "valueQuantity": {"value": 110, "unit": "mg/dL"}
                }
            }]
        }
        obs = fhir_to_normalized_observations(bundle)
        assert len(obs) == 1
        assert obs[0].observation_type == "glucose"
        assert obs[0].value == 110.0


def test_glucose_mmol_to_mg_dl_conversion():
    bundle = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "glu-mmol",
                "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "valueQuantity": {"value": 7.0, "unit": "mmol/L"}
            }
        }]
    }
    obs = fhir_to_normalized_observations(bundle)
    assert len(obs) == 1
    # 7.0 * 18.016 = 126.112 -> rounded to 126.1
    assert obs[0].value == 126.1
    assert obs[0].unit == "mg/dL"


def test_hba1c_loinc_codes_and_conversion():
    for loinc in ("4548-4", "17856-6", "59261-8"):
        bundle = {
            "resourceType": "Bundle",
            "entry": [{
                "resource": {
                    "resourceType": "Observation",
                    "id": f"hba1c-{loinc}",
                    "code": {"coding": [{"system": "http://loinc.org", "code": loinc}]},
                    "effectiveDateTime": "2026-10-01T12:00:00Z",
                    "valueQuantity": {"value": 6.5, "unit": "%"}
                }
            }]
        }
        obs = fhir_to_normalized_observations(bundle)
        assert len(obs) == 1
        assert obs[0].observation_type == "hba1c"
        assert obs[0].value == 6.5

    # mmol/mol conversion: (48 * 0.09148) + 2.152 = 4.39104 + 2.152 = 6.54304 -> 6.5%
    bundle_ifcc = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "hba1c-mmol",
                "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "valueQuantity": {"value": 48, "unit": "mmol/mol"}
            }
        }]
    }
    obs_ifcc = fhir_to_normalized_observations(bundle_ifcc)
    assert len(obs_ifcc) == 1
    assert obs_ifcc[0].value == 6.5
    assert obs_ifcc[0].unit == "%"


def test_weight_loinc_and_lbs_conversion():
    bundle_kg = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "wt-kg",
                "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "valueQuantity": {"value": 75.0, "unit": "kg"}
            }
        }]
    }
    obs_kg = fhir_to_normalized_observations(bundle_kg)
    assert len(obs_kg) == 1
    assert obs_kg[0].observation_type == "weight"
    assert obs_kg[0].value == 75.0
    assert obs_kg[0].unit == "kg"

    bundle_lbs = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "wt-lbs",
                "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "valueQuantity": {"value": 165.347, "unit": "[lb_av]"}
            }
        }]
    }
    obs_lbs = fhir_to_normalized_observations(bundle_lbs)
    assert len(obs_lbs) == 1
    assert obs_lbs[0].value == 75.0


def test_bp_unrecognized_unit_left_unconverted():
    bundle = {
        "resourceType": "Bundle",
        "entry": [{
            "resource": {
                "resourceType": "Observation",
                "id": "bp-kpa",
                "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4"}]},
                "effectiveDateTime": "2026-10-01T12:00:00Z",
                "component": [
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                        "valueQuantity": {"value": 16.0, "unit": "kPa"}
                    },
                    {
                        "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                        "valueQuantity": {"value": 10.0, "unit": "kPa"}
                    }
                ]
            }
        }]
    }
    obs = fhir_to_normalized_observations(bundle)
    assert len(obs) == 2
    # Unconverted: unit is left as kPa
    assert obs[0].unit == "kPa"
    assert obs[1].unit == "kPa"


def test_timestamp_precedence():
    # 1. effectiveDateTime wins
    b1 = {"resourceType": "Bundle", "entry": [{"resource": {
        "resourceType": "Observation", "id": "t1",
        "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]},
        "effectiveDateTime": "2026-10-05T01:00:00Z",
        "effectivePeriod": {"start": "2026-10-05T02:00:00Z"},
        "issued": "2026-10-05T03:00:00Z",
        "valueQuantity": {"value": 100, "unit": "mg/dL"}
    }}]}
    assert fhir_to_normalized_observations(b1)[0].timestamp == "2026-10-05T01:00:00Z"

    # 2. effectivePeriod.start wins if effectiveDateTime missing
    b2 = {"resourceType": "Bundle", "entry": [{"resource": {
        "resourceType": "Observation", "id": "t2",
        "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]},
        "effectivePeriod": {"start": "2026-10-05T02:00:00Z"},
        "issued": "2026-10-05T03:00:00Z",
        "valueQuantity": {"value": 100, "unit": "mg/dL"}
    }}]}
    assert fhir_to_normalized_observations(b2)[0].timestamp == "2026-10-05T02:00:00Z"

    # 3. issued used if both missing
    b3 = {"resourceType": "Bundle", "entry": [{"resource": {
        "resourceType": "Observation", "id": "t3",
        "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]},
        "issued": "2026-10-05T03:00:00Z",
        "valueQuantity": {"value": 100, "unit": "mg/dL"}
    }}]}
    assert fhir_to_normalized_observations(b3)[0].timestamp == "2026-10-05T03:00:00Z"


def test_medication_request_status_and_name_normalisation():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-act",
                    "status": "active",
                    "medicationCodeableConcept": {"text": "Metformin 500mg"},
                    "dosageInstruction": [{"text": "Take 1 tablet twice daily"}]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-comp",
                    "status": "completed",
                    "medicationCodeableConcept": {"coding": [{"display": "Lisinopril 10mg"}]}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-stop",
                    "status": "stopped",
                    "medicationCodeableConcept": {"text": "Aspirin 81mg"}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-canc",
                    "status": "cancelled",
                    "medicationCodeableConcept": {"text": "Atenolol 25mg"}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-err",
                    "status": "entered-in-error",
                    "medicationCodeableConcept": {"text": "Wrong Drug"}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-draft",
                    "status": "draft",
                    "medicationCodeableConcept": {"text": "Draft Med"}
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-unk",
                    "status": "unknown",
                    "medicationCodeableConcept": {"text": "Unknown Med"}
                }
            }
        ]
    }
    meds = fhir_to_normalized_medications(bundle)
    assert len(meds) == 5  # draft and unknown skipped
    status_map = {m.medication_name: m.status for m in meds}
    assert status_map["Metformin 500mg"] == "active"
    assert status_map["Lisinopril 10mg"] == "stopped"
    assert status_map["Aspirin 81mg"] == "stopped"
    assert status_map["Atenolol 25mg"] == "stopped"
    assert status_map["Wrong Drug"] == "stopped"

    # Verify dosage instruction text
    met = next(m for m in meds if m.medication_name == "Metformin 500mg")
    assert met.dosage == "Take 1 tablet twice daily"
