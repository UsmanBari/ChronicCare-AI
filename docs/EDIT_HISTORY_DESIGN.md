# ChronicCare-AI — Record Edit History Technical Design Document

**Document ID**: `docs/EDIT_HISTORY_DESIGN.md`  
**Iteration**: I2-5 (Day 5 Design & Spike)  
**Author**: Hassaan (AI Assistant Antigravity)  
**Target Milestone**: Day 6 (Schema v13, API, UI, JSON/FHIR Export/Import)  

---

## 1. Call Chain Audit for Record Routes

The patient record subsystem spans two separate data layers: `local_store.py` (clinical observations, medications) and `app_store.py` (allergies, patient profile and conditions-basis). Below is the complete trace from FastAPI route handler down to database execution:

| Route | HTTP Method | Handler Function (`backend-poc-technical/main.py`) | Downstream Data Function | Target DB Connection |
|---|---|---|---|---|
| `/api/me/record` | `GET` | `get_patient_record_endpoint` | `local_store.get_local_medications`<br>`local_store.get_local_observations`<br>`app_store.get_allergies`<br>`app_store.get_patient_profile` | `local_store.db` + `app.db` (or shared MySQL) |
| `/api/me/record/conditions-basis` | `PUT` | `update_conditions_basis_endpoint` | `app_store.get_patient_profile`<br>`app_store.update_patient_conditions_basis` | `app_store.get_db_cursor()` (`app.db`) |
| `/api/me/record/medications` | `POST` | `create_record_medication_endpoint` | `local_store.get_local_medications`<br>`local_store.add_local_medication` | `local_store.get_connection()` (`local_store.db`) |
| `/api/me/record/medications/{id}` | `PATCH` | `update_record_medication_endpoint` | `local_store.get_local_medication_by_id`<br>`local_store.update_local_medication` | `local_store.get_connection()` (`local_store.db`) |
| `/api/me/record/medications/{id}` | `DELETE` | `delete_record_medication_endpoint` | `local_store.get_local_medication_by_id`<br>`local_store.delete_local_medication` | `local_store.get_connection()` (`local_store.db`) |
| `/api/me/record/allergies` | `POST` | `create_record_allergy_endpoint` | `app_store.get_allergies`<br>`app_store.create_allergy` | `app_store.get_db_cursor()` (`app.db`) |
| `/api/me/record/allergies/{id}` | `DELETE` | `delete_record_allergy_endpoint` | `app_store.get_allergy_by_id`<br>`app_store.delete_allergy` | `app_store.get_db_cursor()` (`app.db`) |
| `/api/me/record/observations` | `POST` | `create_record_observation_endpoint` | `local_store.get_local_observations`<br>`local_store.add_local_observation` | `local_store.get_connection()` (`local_store.db`) |
| `/api/me/record/observations/{id}`| `DELETE` | `delete_record_observation_endpoint` | `local_store.get_local_observation_by_id`<br>`local_store.delete_local_observation` | `local_store.get_connection()` (`local_store.db`) |

---

## 2. Table Schema: `record_edits`

The `record_edits` table captures an immutable, append-only provenance log of all discrete field-level additions, modifications, and deletions.

### 2.1 Columns & Types

| Column | SQLite Type | MySQL Type | Constraints | Description |
|---|---|---|---|---|
| `edit_id` | `TEXT` | `VARCHAR(64)` | `PRIMARY KEY` | UUIDv4 identifier for the edit event. |
| `user_id` | `TEXT` | `VARCHAR(64)` | `NOT NULL` | Owning patient ID (`auth_user_id` / `patient_id`). |
| `record_type` | `TEXT` | `VARCHAR(32)` | `NOT NULL` | Enum: `'medication'`, `'observation'`, `'allergy'`, `'condition'`. |
| `record_id` | `TEXT` | `VARCHAR(64)` | `NOT NULL` | ID of the entity (e.g. `local-med-...`, `local-obs-...`, allergy UUID, or condition slug). |
| `field` | `TEXT` | `VARCHAR(64)` | `NOT NULL` | Specific attribute changed (e.g. `'dosage'`, `'status'`, `'value'`, `'reaction'`, `'basis'`). |
| `old_value` | `TEXT` | `TEXT` | `NULL` | JSON-encoded prior value (`null` on entity creation). |
| `new_value` | `TEXT` | `TEXT` | `NULL` | JSON-encoded subsequent value (`null` on entity deletion). |
| `origin` | `TEXT` | `VARCHAR(32)` | `NOT NULL` | Source of truth: `'self_reported'`, `'ocr'`, `'clinician'`. |
| `changed_by_user_id` | `TEXT` | `VARCHAR(64)` | `NOT NULL` | Actor user ID who executed the mutation. |
| `changed_at` | `TEXT` | `VARCHAR(64)` | `NOT NULL` | UTC ISO-8601 timestamp ending in `'Z'`. |
| `reason` | `TEXT` | `TEXT` | `NULL` | Optional clinical or operational reason (e.g. `"patient corrected OCR value"`). |

### 2.2 Indexes
- `idx_record_edits_lookup`: `(user_id, record_type, record_id)`
- `idx_record_edits_timeline`: `(user_id, changed_at DESC)`

---

## 3. Transaction Trap Analysis & Architecture

### 3.1 The Problem
In the local development environment and hermetic CI test suite:
- `local_store.py` manages a dedicated SQLite file at `data/local_store.db`.
- `app_store.py` manages a dedicated SQLite file at `data/app.db`.
- SQLite connections cannot participate in cross-database atomic transactions without SQLite's `ATTACH DATABASE` syntax (which introduces brittle filesystem coupling and breaks MySQL compatibility).
- If `record_edits` were placed exclusively in `app_store.py`, mutating a medication in `local_store.py` would require opening a second connection to `app.db`. If the server crashes or the second transaction aborts, the medication is committed but the edit record is lost.

### 3.2 The Solution
1. **Dual Initialization**:
   - `local_store.init_db()` creates `record_edits` inside `local_store.db` (for `medication` and `observation` writes).
   - `app_store.migrate()` (Schema v13) creates `record_edits` inside `app.db` (for `allergy` and `condition` writes).
   - In production with MySQL (`CHRONICCARE_MYSQL_URL`), both stores connect to the same centralized schema, where both create statements are idempotent `CREATE TABLE IF NOT EXISTS`.
2. **Atomic Write Helper**:
   - A helper `record_edit(cursor, ph, ...)` is passed the **exact active cursor** of the calling operation before transaction commit.
   - For `add_local_medication`, `update_local_medication`, and `delete_local_medication`: `record_edit` runs on the `conn.cursor()` in `local_store.py`. If either statement fails, the entire transaction rolls back cleanly.
   - For `create_allergy`, `delete_allergy`, and `update_patient_conditions_basis`: `record_edit` runs on the active cursor in `app_store.py`.
3. **Atomicity Guarantee Table**:

| Record Type | SQLite Dev/CI Atomic? | Production MySQL Atomic? | Justification |
|---|---|---|---|
| **Medication** (`create/update/delete`) | **YES** | **YES** | Written on caller's `local_store` transaction cursor. |
| **Observation** (`create/delete`) | **YES** | **YES** | Written on caller's `local_store` transaction cursor. |
| **Allergy** (`create/delete`) | **YES** | **YES** | Written on caller's `app_store` transaction cursor. |
| **Conditions Basis** (`PUT`) | **YES** | **YES** | Written on caller's `app_store` transaction cursor. |

---

## 4. DDL & Migration Plan (Schema v13)

### 4.1 SQLite DDL (`app_store.py` and `local_store.py`)
```sql
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
);
CREATE INDEX IF NOT EXISTS idx_record_edits_lookup 
    ON record_edits (user_id, record_type, record_id);
CREATE INDEX IF NOT EXISTS idx_record_edits_timeline 
    ON record_edits (user_id, changed_at DESC);
```

### 4.2 MySQL DDL (`app_store.py` and `local_store.py`)
```sql
CREATE TABLE IF NOT EXISTS record_edits (
    edit_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    record_type VARCHAR(32) NOT NULL,
    record_id VARCHAR(64) NOT NULL,
    field VARCHAR(64) NOT NULL,
    old_value TEXT DEFAULT NULL,
    new_value TEXT DEFAULT NULL,
    origin VARCHAR(32) NOT NULL,
    changed_by_user_id VARCHAR(64) NOT NULL,
    changed_at VARCHAR(64) NOT NULL,
    reason TEXT DEFAULT NULL,
    INDEX idx_record_edits_lookup (user_id, record_type, record_id),
    INDEX idx_record_edits_timeline (user_id, changed_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.3 Idempotent Migration Step (v12 $\rightarrow$ v13)
```python
# In app_store.py migrate()
cursor.execute("SELECT version FROM schema_version WHERE version = 13")
if not cursor.fetchone():
    if backend == "sqlite":
        cursor.execute(SQLITE_RECORD_EDITS_DDL)
        cursor.execute(SQLITE_INDEX_LOOKUP)
        cursor.execute(SQLITE_INDEX_TIMELINE)
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (13, ?)", (now,))
    else:
        cursor.execute(MYSQL_RECORD_EDITS_DDL)
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (13, %s)", (now,))
```
- Bump `LATEST_SCHEMA_VERSION = 13`.
- Update `scripts/mysql_preflight.py` to assert schema version 13.
- Test in `backend-poc-technical/test_schema_v12_to_v13.py` verifying v12 $\rightarrow$ v13 migration, idempotency, data preservation, and index presence.

---

## 5. Writers Specification

### 5.1 Helper Implementation
```python
import json
import uuid
from typing import Any, Optional

def record_edit(
    cursor: Any,
    ph: str,
    *,
    user_id: str,
    record_type: str,
    record_id: str,
    field: str,
    old_value: Any,
    new_value: Any,
    origin: str,
    changed_by_user_id: str,
    reason: Optional[str] = None,
    changed_at: Optional[str] = None,
) -> str:
    """Inserts a single atomic field-level audit row into record_edits."""
    if old_value == new_value:
        return ""  # No change -> no audit row generated

    edit_id = str(uuid.uuid4())
    ts = changed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    old_json = json.dumps(old_value) if old_value is not None else None
    new_json = json.dumps(new_value) if new_value is not None else None
    
    query = f"""
        INSERT INTO record_edits (
            edit_id, user_id, record_type, record_id, field,
            old_value, new_value, origin, changed_by_user_id, changed_at, reason
        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """
    cursor.execute(query, (
        edit_id, user_id, record_type, record_id, field,
        old_json, new_json, origin, changed_by_user_id, ts, reason
    ))
    return edit_id
```

### 5.2 Mutation Rules
1. **Creation**:
   - `old_value = None`, `new_value = <value>`.
   - Origin: `"self_reported"` (manual patient entry) or `"ocr"` (confirmed upload).
2. **Deletion**:
   - `old_value = <value>`, `new_value = None`.
   - Reason: Optional patient comment or null.
3. **Update**:
   - Compares previous entity fields to submitted patch.
   - Emits exactly one row per changed field.
   - If values match identically (e.g. patching status to the current status), **zero rows** are emitted.
4. **EHR Connected Mode**:
   - Endpoints continue returning `409 Conflict: {"detail": "record_managed_by_ehr"}`.
   - **Zero rows** written to `record_edits`.

---

## 6. Readers Specification

### 6.1 `GET /api/me/record/history`
- **Authorization**: `require_role("patient")`.
- **Query Parameters**:
  - `record_type`: Optional filter (`medication`, `observation`, `allergy`, `condition`).
  - `record_id`: Optional specific entity ID.
  - `limit`: Integer (default 50, maximum 200).
- **Security Boundary**: The patient can query **only their own** records (`WHERE user_id = current_user['user_id']`). Cross-user lookups are prevented at the SQL layer.
- **Pydantic Response Model**:
```python
class RecordEditItem(BaseModel):
    edit_id: str
    record_type: str
    record_id: str
    field: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    origin: str
    changed_by_user_id: str
    changed_at: str
    reason: Optional[str] = None

class RecordHistoryResponse(BaseModel):
    edits: List[RecordEditItem]
    count: int
```

### 6.2 Provider Access: Review Detail Additive Field
- Clinicians review patients solely in the context of an active check-in or clinical alert.
- **No Broad Query Endpoint**: There is **no unrestricted** `/api/provider/record/history` route. A global history endpoint would violate the principle of least privilege.
- **Additive Field**: `GET /api/provider/review/{checkin_id}` includes an optional additive field `recent_record_edits: List[RecordEditItem]` containing up to the last 20 edits for that specific check-in's patient.

---

## 7. Privacy & Zero-PHI Audit Separation

1. **Storage Separation**:
   - `audit_log` is an operational security log. It contains actions, timestamps, and actor IDs with **zero PHI**:
     - `record_medication_updated {"type": "medication", "count": 1}`.
   - `record_edits` is a clinical record table containing actual medical dosages, lab values, and reactions.
2. **Access Control**:
   - Only authenticated clinical workflows and the patient themselves can read `record_edits`.
   - No clinical values are ever copied into operational log files or stdout logs.

---

## 8. UI Sketches & Provenance Badges

### 8.1 Patient History View (Expanded Drawer)
```
+-----------------------------------------------------------+
| Health Record > Metformin 500mg > History                 |
+-----------------------------------------------------------+
| 2026-10-30 14:15 UTC                                      |
| Origin: OCR Upload [OCR Badge]                            |
| Action: Value Corrected                                   |
|   Dosage: "500 mg daily" -> "500 mg twice daily"          |
|   Reason: Patient corrected OCR value                     |
+-----------------------------------------------------------+
| 2026-10-24 09:30 UTC                                      |
| Origin: Self-Reported [Patient Badge]                     |
| Action: Created                                           |
|   Dosage: "500 mg daily"                                  |
|   Status: "active"                                        |
+-----------------------------------------------------------+
```

### 8.2 Clinician Review Diff
```
+-----------------------------------------------------------+
| Patient Changes Since Last Check-In                       |
+-----------------------------------------------------------+
| [Medication] Metformin                                    |
|   Dosage: ~~500 mg daily~~ -> 500 mg twice daily [OCR]    |
|   Changed by: Patient (Self) | 2026-10-30 14:15 UTC       |
|                                                           |
| [Observation] Blood Pressure                              |
|   Added: 135/85 mmHg [Self-Reported]                      |
|   Measured at: 2026-10-29 08:00 UTC                       |
+-----------------------------------------------------------+
```

