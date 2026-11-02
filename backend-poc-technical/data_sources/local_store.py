"""
Local Store for Isolated Mode (Dual Backend: SQLite & MySQL).

Provides schema creation, synthetic data seeding, and deterministic retrieval functions.
Performs NO clinical interpretation, risk calculation, reconciliation, or LLM processing.
All local records are clearly labeled as synthetic test data.
Supports SQLite (default) and MySQL backends seamlessly.
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional

from data_sources.db_config import (
    get_db_backend,
    get_sqlite_path,
    get_mysql_connection_params,
)

# Optional PyMySQL import for MySQL backend
try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None
    DictCursor = None

from data_sources.app_store import record_edit


DEFAULT_DB_PATH = "local_store.db"
SOURCE_TAG = "local_synthetic_store"

LOCAL_STORE_TABLES = {
    "patients",
    "observations",
    "medications",
    "record_edits",
}

# =============================================================================
# SYNTHETIC TEST FIXTURES
# =============================================================================

SYNTHETIC_PATIENTS = [
    ("LOCAL-PATIENT-001", "Synthetic Patient Alpha (John Doe)", "1965-04-12"),
    ("LOCAL-PATIENT-002", "Synthetic Patient Beta (Jane Smith)", "1978-09-23"),
    ("LOCAL-PATIENT-003", "Synthetic Patient Gamma (Robert Johnson)", "1952-11-05"),
]

SYNTHETIC_OBSERVATIONS = [
    ("OBS-001-1", "LOCAL-PATIENT-001", "Glucose", 145.0, "mg/dL", "2026-08-01T08:30:00Z", SOURCE_TAG, None),
    ("OBS-001-2", "LOCAL-PATIENT-001", "Blood Pressure (Systolic)", 138.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG, None),
    ("OBS-001-3", "LOCAL-PATIENT-001", "Blood Pressure (Diastolic)", 88.0, "mmHg", "2026-08-01T08:30:00Z", SOURCE_TAG, None),
    ("OBS-001-4", "LOCAL-PATIENT-001", "Weight", 84.5, "kg", "2026-08-01T08:30:00Z", SOURCE_TAG, None),
    ("OBS-001-5", "LOCAL-PATIENT-001", "HbA1c", 7.2, "%", "2026-07-15T10:00:00Z", SOURCE_TAG, None),
    ("OBS-002-1", "LOCAL-PATIENT-002", "Glucose", 110.0, "mg/dL", "2026-08-05T09:00:00Z", SOURCE_TAG, None),
    ("OBS-002-2", "LOCAL-PATIENT-002", "Blood Pressure (Systolic)", 122.0, "mmHg", "2026-08-05T09:00:00Z", SOURCE_TAG, None),
    ("OBS-002-3", "LOCAL-PATIENT-002", "Weight", 68.0, "kg", "2026-08-05T09:00:00Z", SOURCE_TAG, None),
    ("OBS-003-1", "LOCAL-PATIENT-003", "Glucose", 160.0, "mg/dL", "2026-08-10T07:45:00Z", SOURCE_TAG, None),
    ("OBS-003-2", "LOCAL-PATIENT-003", "HbA1c", 8.1, "%", "2026-08-10T07:45:00Z", SOURCE_TAG, None),
]

SYNTHETIC_MEDICATIONS = [
    ("MED-001-1", "LOCAL-PATIENT-001", "Metformin 500mg Oral Tablet", "active", "1 tablet twice daily", "2026-01-10T00:00:00Z", SOURCE_TAG),
    ("MED-001-2", "LOCAL-PATIENT-001", "Lisinopril 10mg Oral Tablet", "active", "1 tablet once daily in the morning", "2026-02-15T00:00:00Z", SOURCE_TAG),
    ("MED-002-1", "LOCAL-PATIENT-002", "Atorvastatin 20mg Tablet", "active", "1 tablet once daily at bedtime", "2026-03-01T00:00:00Z", SOURCE_TAG),
    ("MED-003-1", "LOCAL-PATIENT-003", "Insulin Glargine 100 units/mL", "active", "20 units subcutaneously once daily at bedtime", "2026-04-12T00:00:00Z", SOURCE_TAG),
]


def _resolve_backend(backend: Optional[str] = None) -> str:
    return (backend or get_db_backend()).lower()


def _get_db_path(db_path: Optional[str] = None) -> str:
    return get_sqlite_path(db_path)


# =============================================================================
# SQLITE BACKEND IMPLEMENTATION
# =============================================================================

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns an open SQLite connection with sqlite3.Row factory."""
    path = _get_db_path(db_path)
    _init_sqlite_db(path)
    conn = sqlite3.connect(path)
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
                origin TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # Migration: ensure origin column exists on observations table
        cursor.execute("PRAGMA table_info(observations)")
        cols = [r[1] for r in cursor.fetchall()]
        if "origin" not in cols:
            cursor.execute("ALTER TABLE observations ADD COLUMN origin TEXT")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS record_edits (
                edit_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                field TEXT NOT NULL,
                old_value TEXT DEFAULT NULL,
                new_value TEXT DEFAULT NULL,
                origin TEXT NOT NULL,
                changed_by_user_id TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                reason TEXT DEFAULT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_edits_lookup ON record_edits (user_id, record_type, record_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_edits_timeline ON record_edits (user_id, changed_at DESC)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                status TEXT NOT NULL,
                dosage TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                origin TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # Migration: ensure origin column exists on medications table
        cursor.execute("PRAGMA table_info(medications)")
        cols_m = [r[1] for r in cursor.fetchall()]
        if "origin" not in cols_m:
            cursor.execute("ALTER TABLE medications ADD COLUMN origin TEXT")
        
        conn.commit()


def _seed_sqlite_db(db_path: Optional[str] = None) -> None:
    path = _get_db_path(db_path)
    _init_sqlite_db(path)
    
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM medications")
        cursor.execute("DELETE FROM observations")
        cursor.execute("DELETE FROM patients")
        
        cursor.executemany(
            "INSERT INTO patients (id, name, date_of_birth) VALUES (?, ?, ?)",
            SYNTHETIC_PATIENTS
        )
        cursor.executemany(
            "INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            SYNTHETIC_OBSERVATIONS
        )
        cursor.executemany(
            "INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            SYNTHETIC_MEDICATIONS
        )
        conn.commit()


# =============================================================================
# MYSQL BACKEND IMPLEMENTATION
# =============================================================================

def get_mysql_connection(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None):
    """Returns an open PyMySQL connection configured with DictCursor and TLS if available."""
    if pymysql is None:
        raise RuntimeError("PyMySQL is not installed. Please install PyMySQL>=1.1.0 to use the MySQL backend.")
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
                    origin VARCHAR(64) DEFAULT NULL,
                    INDEX idx_obs_patient (patient_id),
                    CONSTRAINT fk_obs_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            # Idempotent migration: check if origin column exists on observations
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'observations' AND COLUMN_NAME = 'origin';
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE observations ADD COLUMN origin VARCHAR(64) DEFAULT NULL;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medications (
                    id VARCHAR(64) PRIMARY KEY,
                    patient_id VARCHAR(64) NOT NULL,
                    medication_name VARCHAR(255) NOT NULL,
                    status VARCHAR(64) NOT NULL,
                    dosage VARCHAR(255) NOT NULL,
                    timestamp VARCHAR(64) NOT NULL,
                    source VARCHAR(64) NOT NULL,
                    origin VARCHAR(64) DEFAULT NULL,
                    INDEX idx_med_patient (patient_id),
                    CONSTRAINT fk_med_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # Idempotent migration: check if origin column exists on medications
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'medications' AND COLUMN_NAME = 'origin';
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE medications ADD COLUMN origin VARCHAR(64) DEFAULT NULL;")
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
            cursor.execute("DELETE FROM medications;")
            cursor.execute("DELETE FROM observations;")
            cursor.execute("DELETE FROM patients;")

            cursor.executemany(
                "INSERT INTO patients (id, name, date_of_birth) VALUES (%s, %s, %s);",
                SYNTHETIC_PATIENTS
            )
            cursor.executemany(
                "INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
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
# UNIFIED PUBLIC STORE INTERFACE
# =============================================================================

def init_db(db_path: Optional[str] = None, backend: Optional[str] = None,
            mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> None:
    """Initializes schema on the configured backend (SQLite or MySQL)."""
    b = _resolve_backend(backend)
    if b == "mysql":
        _init_mysql_db(mysql_url=mysql_url, ssl_ca=ssl_ca)
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
                    "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE patient_id = %s",
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
                "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE patient_id = ?",
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
                    "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE patient_id = %s",
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
                "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE patient_id = ?",
                (patient_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def add_local_patient_if_missing(
    patient_id: str,
    name: str,
    date_of_birth: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> None:
    """Inserts a patient into local store if they do not already exist."""
    b = _resolve_backend(backend)
    dob = date_of_birth or "1970-01-01"
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT IGNORE INTO patients (id, name, date_of_birth) VALUES (%s, %s, %s);",
                    (patient_id, name, dob)
                )
            conn.commit()
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO patients (id, name, date_of_birth) VALUES (?, ?, ?)",
                (patient_id, name, dob)
            )
            conn.commit()


def add_local_observation(
    id: str,
    patient_id: str,
    observation_type: str,
    value: float,
    unit: str,
    timestamp: str,
    source: str = "local",
    origin: Optional[str] = "self_reported",
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    changed_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
    old_value: Optional[Any] = None,
    cursor: Optional[Any] = None,
) -> None:
    """Inserts or updates an observation with provenance origin in the active store."""
    b = _resolve_backend(backend)
    actor_id = changed_by_user_id or (patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id)
    clean_uid = patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id
    obs_dict = {
        "id": id,
        "patient_id": patient_id,
        "observation_type": observation_type,
        "value": value,
        "unit": unit,
        "timestamp": timestamp,
        "source": source,
        "origin": origin,
    }

    if cursor is not None:
        ph = "%s" if b == "mysql" else "?"
        if b == "mysql":
            cursor.execute(
                """
                INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    value = VALUES(value),
                    unit = VALUES(unit),
                    timestamp = VALUES(timestamp),
                    origin = VALUES(origin);
                """,
                (id, patient_id, observation_type, value, unit, timestamp, source, origin)
            )
        else:
            cursor.execute(
                """
                INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value = excluded.value,
                    unit = excluded.unit,
                    timestamp = excluded.timestamp,
                    origin = excluded.origin
                """,
                (id, patient_id, observation_type, value, unit, timestamp, source, origin)
            )
        record_edit(
            cursor,
            ph,
            user_id=clean_uid,
            record_type="observation",
            record_id=id,
            field="created",
            old_value=old_value,
            new_value=obs_dict,
            origin=origin or "self_reported",
            changed_by_user_id=actor_id,
            reason=reason,
        )
        return

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        value = VALUES(value),
                        unit = VALUES(unit),
                        timestamp = VALUES(timestamp),
                        origin = VALUES(origin);
                    """,
                    (id, patient_id, observation_type, value, unit, timestamp, source, origin)
                )
                actor_id = changed_by_user_id or (patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id)
                clean_uid = patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id
                obs_dict = {
                    "id": id,
                    "patient_id": patient_id,
                    "observation_type": observation_type,
                    "value": value,
                    "unit": unit,
                    "timestamp": timestamp,
                    "source": source,
                    "origin": origin,
                }
                record_edit(
                    cursor,
                    "%s",
                    user_id=clean_uid,
                    record_type="observation",
                    record_id=id,
                    field="created",
                    old_value=old_value,
                    new_value=obs_dict,
                    origin=origin or "self_reported",
                    changed_by_user_id=actor_id,
                    reason=reason,
                )
            conn.commit()
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO observations (id, patient_id, type, value, unit, timestamp, source, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value = excluded.value,
                    unit = excluded.unit,
                    timestamp = excluded.timestamp,
                    origin = excluded.origin
                """,
                (id, patient_id, observation_type, value, unit, timestamp, source, origin)
            )
            actor_id = changed_by_user_id or (patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id)
            clean_uid = patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id
            obs_dict = {
                "id": id,
                "patient_id": patient_id,
                "observation_type": observation_type,
                "value": value,
                "unit": unit,
                "timestamp": timestamp,
                "source": source,
                "origin": origin,
            }
            record_edit(
                cursor,
                "?",
                user_id=clean_uid,
                record_type="observation",
                record_id=id,
                field="created",
                old_value=old_value,
                new_value=obs_dict,
                origin=origin or "self_reported",
                changed_by_user_id=actor_id,
                reason=reason,
            )
            conn.commit()


def delete_local_observation(
    observation_id: str,
    patient_id: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    changed_by_user_id: Optional[str] = None,
    origin: str = "self_reported",
    reason: Optional[str] = None,
) -> bool:
    """Deletes an observation record and logs record_edits row atomically on the same cursor."""
    from data_sources.app_store import record_edit
    existing = get_local_observation_by_id(observation_id, patient_id=patient_id, db_path=db_path, backend=backend)
    if not existing:
        return False

    b = _resolve_backend(backend)
    target_pid = patient_id or existing.get("patient_id", "")
    actor_id = changed_by_user_id or target_pid
    clean_uid = target_pid.removeprefix("local-") if target_pid.startswith("local-") else target_pid

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                if patient_id:
                    cursor.execute("DELETE FROM observations WHERE id = %s AND patient_id = %s;", (observation_id, patient_id))
                else:
                    cursor.execute("DELETE FROM observations WHERE id = %s;", (observation_id,))
                deleted = cursor.rowcount > 0
                if deleted:
                    record_edit(
                        cursor,
                        "%s",
                        user_id=clean_uid,
                        record_type="observation",
                        record_id=observation_id,
                        field="deleted",
                        old_value={"value": existing.get("value"), "unit": existing.get("unit"), "measured_at": existing.get("timestamp")},
                        new_value=None,
                        origin=origin,
                        changed_by_user_id=actor_id,
                        reason=reason,
                    )
            conn.commit()
            return deleted
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            if patient_id:
                cursor.execute("DELETE FROM observations WHERE id = ? AND patient_id = ?", (observation_id, patient_id))
            else:
                cursor.execute("DELETE FROM observations WHERE id = ?", (observation_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                record_edit(
                    cursor,
                    "?",
                    user_id=clean_uid,
                    record_type="observation",
                    record_id=observation_id,
                    field="deleted",
                    old_value={"value": existing.get("value"), "unit": existing.get("unit"), "measured_at": existing.get("timestamp")},
                    new_value=None,
                    origin=origin,
                    changed_by_user_id=actor_id,
                    reason=reason,
                )
            conn.commit()
            return deleted


def add_local_medication(
    id: str,
    patient_id: str,
    medication_name: str,
    status: str,
    dosage: str,
    timestamp: str,
    source: str = "local",
    origin: Optional[str] = "self_reported",
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    changed_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
    old_value: Optional[Any] = None,
    cursor: Optional[Any] = None,
) -> None:
    """Inserts a medication and writes record_edits row atomically on the same cursor."""
    from data_sources.app_store import record_edit
    b = _resolve_backend(backend)
    actor_id = changed_by_user_id or patient_id
    effective_origin = origin or "self_reported"
    clean_uid = patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id

    if cursor is not None:
        ph = "%s" if b == "mysql" else "?"
        if b == "mysql":
            cursor.execute(
                """
                INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source, origin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    medication_name = VALUES(medication_name),
                    status = VALUES(status),
                    dosage = VALUES(dosage),
                    timestamp = VALUES(timestamp),
                    origin = VALUES(origin);
                """,
                (id, patient_id, medication_name, status, dosage, timestamp, source, effective_origin)
            )
        else:
            cursor.execute(
                """
                INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    medication_name = excluded.medication_name,
                    status = excluded.status,
                    dosage = excluded.dosage,
                    timestamp = excluded.timestamp,
                    origin = excluded.origin
                """,
                (id, patient_id, medication_name, status, dosage, timestamp, source, effective_origin)
            )
        record_edit(
            cursor,
            ph,
            user_id=clean_uid,
            record_type="medication",
            record_id=id,
            field="created",
            old_value=old_value,
            new_value={"name": medication_name, "status": status, "dosage": dosage},
            origin=effective_origin,
            changed_by_user_id=actor_id,
            reason=reason,
        )
        return

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source, origin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        medication_name = VALUES(medication_name),
                        status = VALUES(status),
                        dosage = VALUES(dosage),
                        timestamp = VALUES(timestamp),
                        origin = VALUES(origin);
                    """,
                    (id, patient_id, medication_name, status, dosage, timestamp, source, effective_origin)
                )
                record_edit(
                    cursor,
                    "%s",
                    user_id=clean_uid,
                    record_type="medication",
                    record_id=id,
                    field="created",
                    old_value=old_value,
                    new_value={"name": medication_name, "status": status, "dosage": dosage},
                    origin=effective_origin,
                    changed_by_user_id=actor_id,
                    reason=reason,
                )
            conn.commit()
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO medications (id, patient_id, medication_name, status, dosage, timestamp, source, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    medication_name = excluded.medication_name,
                    status = excluded.status,
                    dosage = excluded.dosage,
                    timestamp = excluded.timestamp,
                    origin = excluded.origin
                """,
                (id, patient_id, medication_name, status, dosage, timestamp, source, effective_origin)
            )
            record_edit(
                cursor,
                "?",
                user_id=clean_uid,
                record_type="medication",
                record_id=id,
                field="created",
                old_value=old_value,
                new_value={"name": medication_name, "status": status, "dosage": dosage},
                origin=effective_origin,
                changed_by_user_id=actor_id,
                reason=reason,
            )
            conn.commit()


def get_local_medication_by_id(
    medication_id: str,
    patient_id: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a single medication by id (and patient_id if provided)."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                if patient_id:
                    cursor.execute(
                        "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE id = %s AND patient_id = %s",
                        (medication_id, patient_id)
                    )
                else:
                    cursor.execute(
                        "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE id = %s",
                        (medication_id,)
                    )
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            if patient_id:
                cursor.execute(
                    "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE id = ? AND patient_id = ?",
                    (medication_id, patient_id)
                )
            else:
                cursor.execute(
                    "SELECT id, patient_id, medication_name, status, dosage, timestamp, source, origin FROM medications WHERE id = ?",
                    (medication_id,)
                )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_local_medication(
    medication_id: str,
    patient_id: str,
    dosage: Optional[str] = None,
    status: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    changed_by_user_id: Optional[str] = None,
    origin: str = "self_reported",
    reason: Optional[str] = None,
) -> bool:
    """Updates dosage and/or status of a medication and writes record_edits rows per changed field."""
    from data_sources.app_store import record_edit
    b = _resolve_backend(backend)
    actor_id = changed_by_user_id or patient_id
    clean_uid = patient_id.removeprefix("local-") if patient_id.startswith("local-") else patient_id

    existing = get_local_medication_by_id(medication_id, patient_id=patient_id, db_path=db_path, backend=backend)
    if not existing:
        return False

    # Check which fields actually changed
    dosage_changed = (dosage is not None and str(dosage) != str(existing.get("dosage", "")))
    status_changed = (status is not None and str(status) != str(existing.get("status", "")))

    if not dosage_changed and not status_changed:
        # No-op patch -> emit no rows
        return False

    updates = []
    params = []
    if dosage_changed:
        updates.append("dosage = %s" if b == "mysql" else "dosage = ?")
        params.append(dosage)
    if status_changed:
        updates.append("status = %s" if b == "mysql" else "status = ?")
        params.append(status)

    params.extend([medication_id, patient_id])
    query_set = ", ".join(updates)

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"UPDATE medications SET {query_set} WHERE id = %s AND patient_id = %s", tuple(params))
                updated = cursor.rowcount > 0
                if updated:
                    if dosage_changed:
                        record_edit(
                            cursor,
                            "%s",
                            user_id=clean_uid,
                            record_type="medication",
                            record_id=medication_id,
                            field="dosage",
                            old_value=existing.get("dosage"),
                            new_value=dosage,
                            origin=origin,
                            changed_by_user_id=actor_id,
                            reason=reason,
                        )
                    if status_changed:
                        record_edit(
                            cursor,
                            "%s",
                            user_id=clean_uid,
                            record_type="medication",
                            record_id=medication_id,
                            field="status",
                            old_value=existing.get("status"),
                            new_value=status,
                            origin=origin,
                            changed_by_user_id=actor_id,
                            reason=reason,
                        )
            conn.commit()
            return updated
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE medications SET {query_set} WHERE id = ? AND patient_id = ?", tuple(params))
            updated = cursor.rowcount > 0
            if updated:
                if dosage_changed:
                    record_edit(
                        cursor,
                        "?",
                        user_id=clean_uid,
                        record_type="medication",
                        record_id=medication_id,
                        field="dosage",
                        old_value=existing.get("dosage"),
                        new_value=dosage,
                        origin=origin,
                        changed_by_user_id=actor_id,
                        reason=reason,
                    )
                if status_changed:
                    record_edit(
                        cursor,
                        "?",
                        user_id=clean_uid,
                        record_type="medication",
                        record_id=medication_id,
                        field="status",
                        old_value=existing.get("status"),
                        new_value=status,
                        origin=origin,
                        changed_by_user_id=actor_id,
                        reason=reason,
                    )
            conn.commit()
            return updated


def get_local_observation_by_id(
    observation_id: str,
    patient_id: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a single observation by id (and patient_id if provided)."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                if patient_id:
                    cursor.execute(
                        "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE id = %s AND patient_id = %s",
                        (observation_id, patient_id)
                    )
                else:
                    cursor.execute(
                        "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE id = %s",
                        (observation_id,)
                    )
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            if patient_id:
                cursor.execute(
                    "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE id = ? AND patient_id = ?",
                    (observation_id, patient_id)
                )
            else:
                cursor.execute(
                    "SELECT id, patient_id, type, value, unit, timestamp, source, origin FROM observations WHERE id = ?",
                    (observation_id,)
                )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def delete_local_medication(
    medication_id: str,
    patient_id: Optional[str] = None,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    changed_by_user_id: Optional[str] = None,
    origin: str = "self_reported",
    reason: Optional[str] = None,
) -> bool:
    """Deletes a medication record and logs record_edits row atomically on the same cursor."""
    from data_sources.app_store import record_edit
    existing = get_local_medication_by_id(medication_id, patient_id=patient_id, db_path=db_path, backend=backend)
    if not existing:
        return False

    b = _resolve_backend(backend)
    target_pid = patient_id or existing.get("patient_id", "")
    actor_id = changed_by_user_id or target_pid
    clean_uid = target_pid.removeprefix("local-") if target_pid.startswith("local-") else target_pid

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                if patient_id:
                    cursor.execute("DELETE FROM medications WHERE id = %s AND patient_id = %s;", (medication_id, patient_id))
                else:
                    cursor.execute("DELETE FROM medications WHERE id = %s;", (medication_id,))
                deleted = cursor.rowcount > 0
                if deleted:
                    record_edit(
                        cursor,
                        "%s",
                        user_id=clean_uid,
                        record_type="medication",
                        record_id=medication_id,
                        field="medication",
                        old_value={"name": existing.get("medication_name"), "dosage": existing.get("dosage"), "status": existing.get("status")},
                        new_value=None,
                        origin=origin,
                        changed_by_user_id=actor_id,
                        reason=reason,
                    )
            conn.commit()
            return deleted
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            if patient_id:
                cursor.execute("DELETE FROM medications WHERE id = ? AND patient_id = ?", (medication_id, patient_id))
            else:
                cursor.execute("DELETE FROM medications WHERE id = ?", (medication_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                record_edit(
                    cursor,
                    "?",
                    user_id=clean_uid,
                    record_type="medication",
                    record_id=medication_id,
                    field="deleted",
                    old_value={"name": existing.get("medication_name"), "dosage": existing.get("dosage"), "status": existing.get("status")},
                    new_value=None,
                    origin=origin,
                    changed_by_user_id=actor_id,
                    reason=reason,
                )
            conn.commit()
            return deleted


def get_local_observation_origins(
    patient_id: str,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> Dict[str, str]:
    """Retrieves {source_record_id: origin} mapping for a patient where origin is not null."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, origin FROM observations WHERE patient_id = %s AND origin IS NOT NULL;",
                    (patient_id,)
                )
                rows = cursor.fetchall()
                return {r["id"]: r["origin"] for r in rows if r["origin"]}
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, origin FROM observations WHERE patient_id = ? AND origin IS NOT NULL",
                (patient_id,)
            )
            rows = cursor.fetchall()
            return {r["id"]: r["origin"] for r in rows if r["origin"]}
        finally:
            conn.close()


def get_local_medication_origins(
    patient_id: str,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> Dict[str, str]:
    """Retrieves {source_record_id: origin} mapping for a patient's medications where origin is not null."""
    b = _resolve_backend(backend)
    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, origin FROM medications WHERE patient_id = %s AND origin IS NOT NULL;",
                    (patient_id,)
                )
                rows = cursor.fetchall()
                return {r["id"]: r["origin"] for r in rows if r["origin"]}
        finally:
            conn.close()
    else:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, origin FROM medications WHERE patient_id = ? AND origin IS NOT NULL",
                (patient_id,)
            )
            rows = cursor.fetchall()
            return {r["id"]: r["origin"] for r in rows if r["origin"]}
        finally:
            conn.close()



def get_record_edits(
    user_id: str,
    record_type: Optional[str] = None,
    record_id: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieves record edits stored in local_store (medications/observations)."""
    import json
    b = _resolve_backend(backend)
    clean_uid = user_id.removeprefix("local-") if user_id.startswith("local-") else user_id
    safe_limit = max(1, min(int(limit), 200))
    ph = "%s" if b == "mysql" else "?"
    where_clauses = [f"(user_id = {ph} OR user_id = {ph})"]
    params: List[Any] = [clean_uid, f"local-{clean_uid}"]

    if record_type:
        where_clauses.append(f"record_type = {ph}")
        params.append(record_type)
    if record_id:
        where_clauses.append(f"record_id = {ph}")
        params.append(record_id)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT edit_id, user_id, record_type, record_id, field,
               old_value, new_value, origin, changed_by_user_id, changed_at, reason
        FROM record_edits
        WHERE {where_sql}
        ORDER BY changed_at DESC
        LIMIT {ph}
    """
    params.append(safe_limit)
    edits = []

    if b == "mysql":
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                for r in rows:
                    d = dict(r)
                    if d.get("old_value") is not None:
                        try:
                            d["old_value"] = json.loads(d["old_value"])
                        except Exception:
                            pass
                    if d.get("new_value") is not None:
                        try:
                            d["new_value"] = json.loads(d["new_value"])
                        except Exception:
                            pass
                    edits.append(d)
        finally:
            conn.close()
    else:
        path = _get_db_path(db_path)
        _init_sqlite_db(path)
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            for r in cursor.fetchall():
                d = dict(r)
                if d.get("old_value") is not None:
                    try:
                        d["old_value"] = json.loads(d["old_value"])
                    except Exception:
                        pass
                if d.get("new_value") is not None:
                    try:
                        d["new_value"] = json.loads(d["new_value"])
                    except Exception:
                        pass
                edits.append(d)

    return edits
