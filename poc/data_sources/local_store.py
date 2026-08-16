"""
Local Store for Isolated Mode (SQLite Database)

Provides schema creation, synthetic data seeding, and deterministic retrieval functions.
Performs NO clinical interpretation, risk calculation, reconciliation, or LLM processing.
All local records are clearly labeled as synthetic test data.
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional

DEFAULT_DB_PATH = "local_store.db"

def _get_db_path(db_path: Optional[str] = None) -> str:
    if db_path:
        return db_path
    return os.environ.get("LOCAL_DB_PATH", DEFAULT_DB_PATH)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """
    Creates tables for Patients, Observations, and Medications in SQLite database.
    """
    path = _get_db_path(db_path)
    # Ensure directory exists if path contains a directory
    db_dir = os.path.dirname(path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        
        # Patients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL
            )
        """)
        
        # Observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # Medications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                status TEXT NOT NULL,
                dosage TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        conn.commit()

def seed_db(db_path: Optional[str] = None) -> None:
    """
    Seeds 3 synthetic patients with observations and medications into local SQLite store.
    All records explicitly tagged with source='local_synthetic_store'.
    """
    path = _get_db_path(db_path)
    init_db(path)
    
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        
        # Clear existing data to ensure idempotent seeding
        cursor.execute("DELETE FROM medications")
        cursor.execute("DELETE FROM observations")
        cursor.execute("DELETE FROM patients")
        
        SOURCE_TAG = "local_synthetic_store"
        
        # Patient 1: Chronic Condition Synthetic Patient (Diabetes & Hypertension)
        patients_data = [
            ("LOCAL-PATIENT-001", "Synthetic Patient Alpha (John Doe)", "1965-04-12"),
            ("LOCAL-PATIENT-002", "Synthetic Patient Beta (Jane Smith)", "1978-09-23"),
            ("LOCAL-PATIENT-003", "Synthetic Patient Gamma (Robert Johnson)", "1952-11-05"),
        ]
        cursor.executemany("INSERT INTO patients (id, name, date_of_birth) VALUES (?, ?, ?)", patients_data)
        
        # Observations for Patient 001 (glucose, blood pressure, weight, HbA1c)
        obs_data_001 = [
            ("OBS-001-1", "LOCAL-PATIENT-001", "Glucose", 145.0, "mg/dL", "2026-08-01T08:30:00Z", SOURCE_TAG),
            ("OBS-001-2", "LOCAL-PATIENT-001", "Blood Pressure (Systolic)", 138.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG),
            ("OBS-001-3", "LOCAL-PATIENT-001", "Blood Pressure (Diastolic)", 88.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG),
            ("OBS-001-4", "LOCAL-PATIENT-001", "Weight", 84.5, "kg", "2026-08-01T08:30:00Z", SOURCE_TAG),
            ("OBS-001-5", "LOCAL-PATIENT-001", "HbA1c", 7.2, "%", "2026-07-15T10:00:00Z", SOURCE_TAG),
        ]
        
        # Observations for Patient 002
        obs_data_002 = [
            ("OBS-002-1", "LOCAL-PATIENT-002", "Glucose", 110.0, "mg/dL", "2026-08-05T09:00:00Z", SOURCE_TAG),
            ("OBS-002-2", "LOCAL-PATIENT-002", "Blood Pressure (Systolic)", 122.0, "mmHg", "2026-08-05T09:00:00Z", SOURCE_TAG),
            ("OBS-002-3", "LOCAL-PATIENT-002", "Weight", 68.0, "kg", "2026-08-05T09:00:00Z", SOURCE_TAG),
        ]
        
        # Observations for Patient 003
        obs_data_003 = [
            ("OBS-003-1", "LOCAL-PATIENT-003", "Glucose", 160.0, "mg/dL", "2026-08-10T07:45:00Z", SOURCE_TAG),
            ("OBS-003-2", "LOCAL-PATIENT-003", "HbA1c", 8.1, "%", "2026-08-10T07:45:00Z", SOURCE_TAG),
        ]
        
        cursor.executemany(
            "INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            obs_data_001 + obs_data_002 + obs_data_003
        )
        
        # Medications for Patients
        meds_data = [
            ("MED-001-1", "LOCAL-PATIENT-001", "Metformin 500mg Oral Tablet", "active", "1 tablet twice daily", "2026-01-10T00:00:00Z", SOURCE_TAG),
            ("MED-001-2", "LOCAL-PATIENT-001", "Lisinopril 10mg Oral Tablet", "active", "1 tablet once daily in the morning", "2026-02-15T00:00:00Z", SOURCE_TAG),
            ("MED-002-1", "LOCAL-PATIENT-002", "Atorvastatin 20mg Tablet", "active", "1 tablet once daily at bedtime", "2026-03-01T00:00:00Z", SOURCE_TAG),
            ("MED-003-1", "LOCAL-PATIENT-003", "Insulin Glargine 100 units/mL", "active", "20 units subcutaneously once daily at bedtime", "2026-04-12T00:00:00Z", SOURCE_TAG),
        ]
        
        cursor.executemany(
            "INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            meds_data
        )
        
        conn.commit()

def get_local_patient(patient_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single patient record from local SQLite store by patient_id.
    Returns dictionary of patient record or None if not found.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, date_of_birth FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def get_local_observations(patient_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all observation records for a given patient_id from local SQLite store.
    Returns list of dictionaries.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, patient_id, type, value, unit, timestamp, source FROM observations WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_local_medications(patient_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all medication records for a given patient_id from local SQLite store.
    Returns list of dictionaries.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, patient_id, medication_name, status, dosage, timestamp, source FROM medications WHERE patient_id = ?", (patient_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
