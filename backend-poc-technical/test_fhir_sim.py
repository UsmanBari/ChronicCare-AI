"""
Unit tests for FHIR R4 in-process simulator (data_sources/fhir_sim.py).
Hermetic: no network, no database, injected clock.
"""

from datetime import datetime, timezone, timedelta
import pytest
from data_sources.fhir_sim import (
    handle,
    SAMPLE_PATIENTS,
)


def test_sample_patients_definitions():
    """Verify synthetic patients are defined and distinct."""
    assert len(SAMPLE_PATIENTS) >= 5
    for pid in ("sim-ayesha", "sim-bilal", "sim-sana", "sim-imran", "sim-newpatient", "sim-child"):
        assert pid in SAMPLE_PATIENTS
        p = SAMPLE_PATIENTS[pid]
        assert p["age"] > 0
        assert p["name"]


def test_metadata_endpoint():
    status, body = handle("metadata", {"_summary": "true"})
    assert status == 200
    assert body["resourceType"] == "CapabilityStatement"
    assert body["fhirVersion"] == "4.0.0"


def test_patient_search_endpoint():
    status, body = handle("Patient", {"_count": "5"})
    assert status == 200
    assert body["resourceType"] == "Bundle"
    assert len(body["entry"]) >= 5


def test_patient_read_fidelity():
    for pid, expected in SAMPLE_PATIENTS.items():
        status, body = handle(f"Patient/{pid}", {})
        assert status == 200
        assert body["resourceType"] == "Patient"
        assert body["id"] == pid
        assert "birthDate" in body
        # Check birthDate year reflects age
        now_year = datetime.now(timezone.utc).year
        expected_birth_year = now_year - expected["age"]
        assert body["birthDate"].startswith(str(expected_birth_year))


def test_unknown_patient_returns_404_operation_outcome():
    status, body = handle("Patient/nonexistent-9999", {})
    assert status == 404
    assert body["resourceType"] == "OperationOutcome"
    assert body["issue"][0]["code"] == "not-found"


def test_sim_newpatient_has_no_observations():
    status, body = handle("Observation", {"patient": "sim-newpatient"})
    assert status == 200
    assert body["resourceType"] == "Bundle"
    assert body["total"] == 0
    assert len(body["entry"]) == 0

    # But has 1 active medication
    med_status, med_body = handle("MedicationRequest", {"patient": "sim-newpatient"})
    assert med_status == 200
    assert med_body["total"] == 1


def test_observation_loinc_codes_and_bp_panels():
    # sim-ayesha uses LOINC 55284-4 for BP panel
    status_a, obs_a = handle("Observation", {"patient": "sim-ayesha"})
    assert status_a == 200
    entries_a = [e["resource"] for e in obs_a["entry"]]
    bp_a = [o for o in entries_a if any(c.get("code") == "55284-4" for c in o.get("code", {}).get("coding", []))]
    assert len(bp_a) > 0
    for o in bp_a:
        components = o.get("component", [])
        assert len(components) == 2
        comp_codes = {c["code"]["coding"][0]["code"] for c in components}
        assert comp_codes == {"8480-6", "8462-4"}
        for comp in components:
            assert comp["valueQuantity"]["unit"] == "mm[Hg]"

    # sim-sana uses LOINC 85354-9 for BP panel
    status_s, obs_s = handle("Observation", {"patient": "sim-imran"})
    assert status_s == 200
    entries_s = [e["resource"] for e in obs_s["entry"]]
    bp_s = [o for o in entries_s if any(c.get("code") == "85354-9" for c in o.get("code", {}).get("coding", []))]
    assert len(bp_s) > 0


def test_relative_timestamps_shift_with_injected_now():
    t1 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)

    _, obs_t1 = handle("Observation", {"patient": "sim-ayesha"}, now=t1)
    _, obs_t2 = handle("Observation", {"patient": "sim-ayesha"}, now=t2)

    date_t1 = obs_t1["entry"][0]["resource"]["effectiveDateTime"]
    date_t2 = obs_t2["entry"][0]["resource"]["effectiveDateTime"]

    dt1 = datetime.fromisoformat(date_t1)
    dt2 = datetime.fromisoformat(date_t2)

    # The difference between the observations must equal the 14 days difference in injected now
    assert dt2 - dt1 == timedelta(days=14)


def test_condition_bundle_fidelity():
    status, body = handle("Condition", {"patient": "sim-ayesha"})
    assert status == 200
    assert body["resourceType"] == "Bundle"
    assert body["total"] >= 1
    for entry in body["entry"]:
        res = entry["resource"]
        assert res["resourceType"] == "Condition"
        assert res["clinicalStatus"]["coding"][0]["code"] == "active"
