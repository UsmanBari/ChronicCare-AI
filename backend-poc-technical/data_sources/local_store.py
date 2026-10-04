"""
Local Store for Isolated Mode (Dual Backend: SQLite & MySQL).

Provides schema creation, synthetic data seeding, and deterministic retrieval functions.
Performs NO clinical interpretation, risk calculation, reconciliation, or LLM processing.
All local records are clearly labeled as synthetic test data.

Backend selection:
- If DB_BACKEND is 'mysql' (or backend='mysql' is explicitly passed), uses PyMySQL.
- Otherwise defaults to SQLite (local_store.db).
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional
from data_sources.db_config import get_db_backend, get_mysql_connection_params

DEFAULT_DB_PATH = "local_store.db"
SOURCE_TAG = "local_synthetic_store"

# =============================================================================
# SYNTHETIC DATA FIXTURES
# =============================================================================

SYNTHETIC_PATIENTS = [
    ("LOCAL-PATIENT-001", "Synthetic Patient Alpha (John Doe)", "1965-04-12"),
    ("LOCAL-PATIENT-002", "Synthetic Patient Beta (Jane Smith)", "1978-09-23"),
    ("LOCAL-PATIENT-003", "Synthetic Patient Gamma (Robert Johnson)", "1952-11-05"),
]

SYNTHETIC_OBSERVATIONS = [
    # Patient 001
    ("OBS-001-1", "LOCAL-PATIENT-001", "Glucose", 145.0, "mg/dL", "2026-08-01T08:30:00Z", SOURCE_TAG),
    ("OBS-001-2", "LOCAL-PATIENT-001", "Blood Pressure (Systolic)", 138.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG),
    ("OBS-001-3", "LOCAL-PATIENT-001", "Blood Pressure (Diastolic)", 88.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG),
    ("OBS-001-4", "LOCAL-PATIENT-001", "Weight", 84.5, "kg", "2026-08-01T08:30:00Z", SOURCE_TAG),
    ("OBS-001-5", "LOCAL-PATIENT-001", "HbA1c", 7.2, "%", "2026-07-15T10:00:00Z", SOURCE_TAG),
    # Patient 002
    ("OBS-002-1", "LOCAL-PATIENT-002", "Glucose", 110.0, "mg/dL", "2026-08-05T09:00:00Z", SOURCE_TAG),
    ("OBS-002-2", "LOCAL-PATIENT-002", "Blood Pressure (Systolic)", 122.0, "mmHg", "2026-08-05T09:00:00Z", SOURCE_TAG),
    ("OBS-002-3", "LOCAL-PATIENT-002", "Weight", 68.0, "kg", "2026-08-05T09:00:00Z", SOURCE_TAG),
    # Patient 003
    ("OBS-003-1", "LOCAL-PATIENT-003", "Glucose", 160.0, "mg/dL", "2026-08-10T07:45:00Z", SOURCE_TAG),
    ("OBS-003-2", "LOCAL-PATIENT-003", "HbA1c", 8.1, "%", "2026-08-10T07:45:00Z", SOURCE_TAG),
]

SYNTHETIC_MEDICATIONS = [
    ("MED-001-1", "LOCAL-PATIENT-001", "Metformin 500mg Oral Tablet", "active", "1 tablet twice daily", "2026-01-10T00:00:00Z", SOURCE_TAG),
    ("MED-001-2", "LOCAL-PATIENT-001", "Lisinopril 10mg Oral Tablet", "active", "1 tablet once daily in the morning", "2026-02-15T00:00:00Z", SOURCE_TAG),
    ("MED-002-1", "LOCAL-PATIENT-002", "Atorvastatin 20mg Tablet", "active", "1 tablet once daily at bedtime", "2026-03-01T00:00:00Z", SOURCE_TAG),
    ("MED-003-1", "LOCAL-PATIENT-003", "Insulin Glargine 100 units/mL", "active", "20 units subcutaneously once daily at bedtime", "2026-04-12T00:00:00Z", SOURCE_TAG),
]


def _get_db_path(db_path: Optional[str] = None) -> str:
    if db_path:
        return db_path
    return os.environ.get("LOCAL_DB_PATH", DEFAULT_DB_PATH)


def _resolve_backend(backend: Optional[str] = None) -> str:
    if backend:
        return backend.strip().lower()
    return get_db_backend()


# =============================================================================
# SQLITE IMPLEMENTATION
# =============================================================================

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _init_sqlite_db(db_path: Optional[str] = None) -> None:
    path = _get_db_path(db_path)
    db_dir = os.path.dirname(path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL
            )
        """)
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


def _seed_sqlite_db(db_path: Optional[str] = None) -> None:
    path = _get_db_path(db_path)
    _init_sqlite_db(path)
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medications")
        cursor.execute("DELETE FROM observations")
        cursor.execute("DELETE FROM patients")
        
        cursor.executemany("INSERT INTO patients (id, name, date_of_birth) VALUES (?, ?, ?)", SYNTHETIC_PATIENTS)
        cursor.executemany("INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source) VALUES (?, ?, ?, ?, ?, ?, ?)", SYNTHETIC_OBSERVATIONS)
        cursor.executemany("INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source) VALUES (?, ?, ?, ?, ?, ?, ?)", SYNTHETIC_MEDICATIONS)
        conn.commit()


# =============================================================================
# MYSQL IMPLEMENTATION
# =============================================================================

def get_mysql_connection(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None):
    import pymysql
    from pymysql.cursors import DictCursor
    params = get_mysql_connection_params(mysql_url=mysql_url, ssl_ca=ssl_ca)
    params["cursorclass"] = DictCursor
    return pymysql.connect(**params)


def _init_mysql_db(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> None:
    conn = get_mysql_connection(mysql_url=mysql_url, ssl_ca=ssl_ca)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    date_of_birth VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id VARCHAR(64) PRIMARY KEY,
                    patient_id VARCHAR(64) NOT NULL,
                    type VARCHAR(128) NOT NULL,
                    value DOUBLE NOT NULL,
                    unit VARCHAR(64) NOT NULL,
                    timestamp VARCHAR(64) NOT NULL,
                    source VARCHAR(64) NOT NULL,
                    INDEX idx_obs_patient (patient_id),
                    CONSTRAINT fk_obs_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id VARCHAR(64) PRIMARY KEY,
                    patient_id VARCHAR(64) NOT NULL,
                    medication_name VARCHAR(255) NOT NULL,
                    status VARCHAR(64) NOT NULL,
                    dosage VARCHAR(255) NOT NULL,
                    timestamp VARCHAR(64) NOT NULL,
                    source VARCHAR(64) NOT NULL,
                    INDEX idx_med_patient (patient_id),
                    CONSTRAINT fk_med_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
        conn.commit()
    finally:
        conn.close()


def _seed_mysql_db(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None, reset: bool = False) -> None:
    params = get_mysql_connection_params(mysql_url=mysql_url, ssl_ca=ssl_ca)
    db_name = params["database"]

    if reset:
        if not db_name.endswith("_dev"):
            raise ValueError(f"Refusing to reset MySQL database '{db_name}'. Reset is only permitted on databases ending in '_dev'.")
        conn = get_mysql_connection(mysql_url=mysql_url, ssl_ca=ssl_ca)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                cursor.execute("DROP TABLE IF EXISTS medications;")
                cursor.execute("DROP TABLE IF EXISTS observations;")
                cursor.execute("DROP TABLE IF EXISTS patients;")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conn.commit()
        finally:
            conn.close()

    _init_mysql_db(mysql_url=mysql_url, ssl_ca=ssl_ca)

    conn = get_mysql_connection(mysql_url=mysql_url, ssl_ca=ssl_ca)
    try:
        with conn.cursor() as cursor:
            # Idempotent delete before insert
            cursor.execute("DELETE FROM medications;")
            cursor.execute("DELETE FROM observations;")
            cursor.execute("DELETE FROM patients;")

            cursor.executemany(
                "INSERT INTO patients (id, name, date_of_birth) VALUES (%s, %s, %s);",
                SYNTHETIC_PATIENTS
            )
            cursor.executemany(
                "INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                SYNTHETIC_OBSERVATIONS
            )
            cursor.executemany(
                "INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                SYNTHETIC_MEDICATIONS
            )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# PUBLIC UNIFIED STORE INTERFACE (Preserves exact backwards-compatible signatures)
# =============================================================================

def init_db(db_path: Optional[str] = None, backend: Optional[str] = None) -> None:
    """Initializes schema on the configured backend (SQLite or MySQL)."""
    b = _resolve_backend(backend)
    if b == "mysql":
        _init_mysql_db()
    else:
        _init_sqlite_db(db_path)


def seed_db(db_path: Optional[str] = None, backend: Optional[str] = None, reset: bool = False) -> None:
    """Seeds synthetic test patients and observations into the configured backend."""
    b = _resolve_backend(backend)
    if b == "mysql":
        _seed_mysql_db(reset=reset)
    else:
        _seed_sqlite_db(db_path)


def get_local_patient(patient_id: str, db_path: Optional[str] = None, backend: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single patient record by patient_id from the active store."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, date_of_birth FROM patients WHERE id = %s", (patient_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, date_of_birth FROM patients WHERE id = ?", (patient_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_local_observations(patient_id: str, db_path: Optional[str] = None, backend: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all observation records for a given patient_id from the active store."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, patient_id, type, value, unit, timestamp, source FROM observations WHERE patient_id = %s",
                    (patient_id,)
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, patient_id, type, value, unit, timestamp, source FROM observations WHERE patient_id = ?",
                (patient_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_local_medications(patient_id: str, db_path: Optional[str] = None, backend: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all medication records for a given patient_id from the active store."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, patient_id, medication_name, status, dosage, timestamp, source FROM medications WHERE patient_id = %s",
                    (patient_id,)
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, patient_id, medication_name, status, dosage, timestamp, source FROM medications WHERE patient_id = ?",
                (patient_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
