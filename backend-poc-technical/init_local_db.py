"""
Initialization script for local SQLite database store.
Creates tables and seeds synthetic test patient data.
"""

import os
import sys

# Ensure local imports work regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_sources.local_store import init_db, seed_db, get_local_patient, get_local_observations, get_local_medications
from data_sources.app_store import migrate

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "local_store.db")
    
    print(f"Initializing and seeding SQLite database at: {db_path}")
    migrate(db_path=db_path)
    seed_db(db_path)
    print("Database seeded successfully.")
    
    print("\n--- Seeding Verification ---")
    patient = get_local_patient("LOCAL-PATIENT-001", db_path)
    if patient:
        print(f"Patient retrieved: {patient['name']} (ID: {patient['id']}, DOB: {patient['date_of_birth']})")
        obs = get_local_observations("LOCAL-PATIENT-001", db_path)
        print(f"Observations count for {patient['id']}: {len(obs)}")
        for o in obs:
            print(f"  - {o['type']}: {o['value']} {o['unit']} ({o['source']})")
        
        meds = get_local_medications("LOCAL-PATIENT-001", db_path)
        print(f"Medications count for {patient['id']}: {len(meds)}")
        for m in meds:
            print(f"  - {m['medication_name']} [{m['status']}] dosage: {m['dosage']} ({m['source']})")
    else:
        print("ERROR: Patient LOCAL-PATIENT-001 not found.")

if __name__ == "__main__":
    main()
