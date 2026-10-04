"""
Initialization and seeding script for Isolated Mode local database store.
Supports both SQLite and MySQL backends with identical schema and synthetic data fixtures.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure local imports work regardless of working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Load environment variables
env_file = os.path.join(script_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

from data_sources.db_config import get_db_backend
from data_sources.local_store import (
    init_db,
    seed_db,
    get_local_patient,
    get_local_observations,
    get_local_medications,
)

def seed_and_verify(backend: str, reset: bool = False, db_path: str = None):
    print(f"\n==================================================")
    print(f"Initializing & Seeding Local Store (Backend: {backend.upper()})")
    print(f"==================================================")
    
    seed_db(db_path=db_path, backend=backend, reset=reset)
    print(f"[SUCCESS] {backend.upper()} database initialized and seeded.")

    print(f"\n--- {backend.upper()} Seeding Verification ---")
    patient = get_local_patient("LOCAL-PATIENT-001", db_path=db_path, backend=backend)
    if patient:
        print(f"Patient retrieved: {patient['name']} (ID: {patient['id']}, DOB: {patient['date_of_birth']})")
        obs = get_local_observations("LOCAL-PATIENT-001", db_path=db_path, backend=backend)
        print(f"Observations count for {patient['id']}: {len(obs)}")
        for o in obs:
            print(f"  - {o['type']}: {o['value']} {o['unit']} ({o['source']})")

        meds = get_local_medications("LOCAL-PATIENT-001", db_path=db_path, backend=backend)
        print(f"Medications count for {patient['id']}: {len(meds)}")
        for m in meds:
            print(f"  - {m['medication_name']} [{m['status']}] dosage: {m['dosage']} ({m['source']})")
    else:
        print(f"ERROR: Patient LOCAL-PATIENT-001 not found in {backend.upper()} store.")
        raise RuntimeError(f"Verification failed for backend {backend}")

def main():
    parser = argparse.ArgumentParser(description="Initialize and seed ChronicCare local database store.")
    parser.add_argument(
        "--backend",
        choices=["sqlite", "mysql", "both"],
        default=None,
        help="Database backend to initialize. Defaults to DB_BACKEND env var (or sqlite)."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate tables before seeding (MySQL: only allowed on databases ending in '_dev')."
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Custom SQLite db file path (ignored for MySQL)."
    )
    args = parser.parse_args()

    default_sqlite_path = os.path.join(script_dir, "local_store.db")
    target_path = args.db_path or default_sqlite_path

    selected_backend = args.backend or get_db_backend()

    if selected_backend == "both":
        seed_and_verify("sqlite", reset=args.reset, db_path=target_path)
        seed_and_verify("mysql", reset=args.reset)
    else:
        seed_and_verify(selected_backend, reset=args.reset, db_path=target_path)

if __name__ == "__main__":
    main()
