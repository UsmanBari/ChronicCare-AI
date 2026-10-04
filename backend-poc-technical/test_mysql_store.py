"""
Opt-in Integration Tests for MySQL Local Store Backend.

Runs ONLY when:
1. Environment variable RUN_MYSQL_TESTS=1
2. MYSQL_URL is configured
3. Database name ends in '_dev' (safety guardrail)

Otherwise skips all tests cleanly so default CI (which has no MySQL) remains green.
"""

import os
import sys
import pytest
from dotenv import load_dotenv

# Ensure backend root is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

env_file = os.path.join(script_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

from data_sources.db_config import get_mysql_connection_params
from data_sources.local_store import (
    get_local_patient,
    get_local_observations,
    get_local_medications,
    seed_db,
)
from data_sources.local_adapter import (
    get_normalized_patient,
    get_normalized_observations,
    get_normalized_medications,
)
from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication


def _should_run_mysql_tests() -> bool:
    if os.environ.get("RUN_MYSQL_TESTS") != "1":
        return False
    mysql_url = os.environ.get("MYSQL_URL")
    if not mysql_url:
        return False
    try:
        params = get_mysql_connection_params(mysql_url)
        return params["database"].endswith("_dev")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _should_run_mysql_tests(),
    reason="MySQL tests skipped: RUN_MYSQL_TESTS=1 not set or database does not end in '_dev'"
)


def test_mysql_seeding_and_retrieval():
    """Verifies MySQL seeding and basic CRUD retrieval."""
    seed_db(backend="mysql", reset=False)
    
    patient = get_local_patient("LOCAL-PATIENT-001", backend="mysql")
    assert patient is not None
    assert patient["id"] == "LOCAL-PATIENT-001"
    assert "John Doe" in patient["name"]
    
    obs = get_local_observations("LOCAL-PATIENT-001", backend="mysql")
    assert len(obs) == 5
    types = {o["type"] for o in obs}
    assert "Glucose" in types
    assert "HbA1c" in types
    
    meds = get_local_medications("LOCAL-PATIENT-001", backend="mysql")
    assert len(meds) == 2


def test_dual_backend_source_blind_equivalence():
    """
    Source-Blind Equivalence Test across SQLite and MySQL backends.
    Proves that normalizing data from SQLite vs MySQL produces identical domain models.
    """
    db_path = os.path.join(script_dir, "local_store.db")
    patient_id = "LOCAL-PATIENT-001"
    
    # Ensure both are seeded
    seed_db(db_path=db_path, backend="sqlite")
    seed_db(backend="mysql")
    
    # 1. Patient equivalence
    sqlite_patient = get_normalized_patient(patient_id, db_path=db_path)
    # Temporarily set DB_BACKEND=mysql for adapter call
    orig_backend = os.environ.get("DB_BACKEND")
    try:
        os.environ["DB_BACKEND"] = "mysql"
        mysql_patient = get_normalized_patient(patient_id)
    finally:
        if orig_backend:
            os.environ["DB_BACKEND"] = orig_backend
        else:
            os.environ.pop("DB_BACKEND", None)
            
    assert sqlite_patient.to_dict() == mysql_patient.to_dict()
    assert isinstance(mysql_patient, NormalizedPatient)
    
    # 2. Observations equivalence
    sqlite_obs = get_normalized_observations(patient_id, db_path=db_path)
    try:
        os.environ["DB_BACKEND"] = "mysql"
        mysql_obs = get_normalized_observations(patient_id)
    finally:
        if orig_backend:
            os.environ["DB_BACKEND"] = orig_backend
        else:
            os.environ.pop("DB_BACKEND", None)
            
    assert len(sqlite_obs) == len(mysql_obs)
    sqlite_obs_dicts = [o.to_dict() for o in sqlite_obs]
    mysql_obs_dicts = [o.to_dict() for o in mysql_obs]
    assert sqlite_obs_dicts == mysql_obs_dicts
    
    # 3. Medications equivalence
    sqlite_meds = get_normalized_medications(patient_id, db_path=db_path)
    try:
        os.environ["DB_BACKEND"] = "mysql"
        mysql_meds = get_normalized_medications(patient_id)
    finally:
        if orig_backend:
            os.environ["DB_BACKEND"] = orig_backend
        else:
            os.environ.pop("DB_BACKEND", None)
            
    assert len(sqlite_meds) == len(mysql_meds)
    sqlite_meds_dicts = [m.to_dict() for m in sqlite_meds]
    mysql_meds_dicts = [m.to_dict() for m in mysql_meds]
    assert sqlite_meds_dicts == mysql_meds_dicts
