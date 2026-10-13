import os
import pytest
from data_sources.local_store import (
    init_db,
    add_local_patient_if_missing,
    add_local_observation,
    add_local_medication,
    get_local_observation_by_id,
    get_local_medication_by_id,
    update_local_medication,
    delete_local_observation,
    delete_local_medication,
)


@pytest.fixture
def temp_db(tmp_path):
    """A fresh, empty SQLite store for each test."""
    path = str(tmp_path / "local_store_test.db")
    init_db(db_path=path, backend="sqlite")
    return path


def test_cross_patient_access_isolation(temp_db):
    """
    Shows that Patient A adds an observation and a medication,
    and Patient B cannot retrieve, update, or delete them by ID.
    """
    # Setup patients
    add_local_patient_if_missing("PATIENT_A", "Patient A", db_path=temp_db)
    add_local_patient_if_missing("PATIENT_B", "Patient B", db_path=temp_db)

    # Patient A adds records
    add_local_observation(
        id="OBS-A-01",
        patient_id="PATIENT_A",
        observation_type="glucose",
        value=130.0,
        unit="mg/dL",
        timestamp="2026-08-15T10:00:00Z",
        db_path=temp_db
    )
    add_local_medication(
        id="MED-A-01",
        patient_id="PATIENT_A",
        medication_name="Metformin 500mg",
        status="active",
        dosage="1 daily",
        timestamp="2026-08-15T10:00:00Z",
        db_path=temp_db
    )

    # 1. Patient B tries to get Patient A's observation by ID
    obs_b_get = get_local_observation_by_id("OBS-A-01", patient_id="PATIENT_B", db_path=temp_db)
    assert obs_b_get is None, "Security violation: Patient B retrieved Patient A's observation!"

    # 2. Patient B tries to get Patient A's medication by ID
    med_b_get = get_local_medication_by_id("MED-A-01", patient_id="PATIENT_B", db_path=temp_db)
    assert med_b_get is None, "Security violation: Patient B retrieved Patient A's medication!"

    # 3. Patient B tries to update Patient A's medication dosage
    updated = update_local_medication(
        medication_id="MED-A-01",
        patient_id="PATIENT_B",
        dosage="5 daily (malicious update)",
        db_path=temp_db
    )
    assert updated is False, "Security violation: Patient B updated Patient A's medication!"

    # 4. Patient B tries to delete Patient A's observation
    deleted_obs = delete_local_observation("OBS-A-01", patient_id="PATIENT_B", db_path=temp_db)
    assert deleted_obs is False, "Security violation: Patient B deleted Patient A's observation!"

    # 5. Patient B tries to delete Patient A's medication
    deleted_med = delete_local_medication("MED-A-01", patient_id="PATIENT_B", db_path=temp_db)
    assert deleted_med is False, "Security violation: Patient B deleted Patient A's medication!"

    # Verify Patient A's records remain intact
    assert get_local_observation_by_id("OBS-A-01", patient_id="PATIENT_A", db_path=temp_db) is not None
    assert get_local_medication_by_id("MED-A-01", patient_id="PATIENT_A", db_path=temp_db) is not None
