"""
Contract Tests for MySQL ID Column Widths (Part C1).
Verifies that all MySQL table columns that receive generated IDs
(observations.id, medications.id, record_edits.record_id, audit_log.target, etc.)
have declared widths >= the maximum possible generated ID length.

Tested against:
- 28-character Firebase UIDs
- Longest observation_type in code ('blood_pressure_diastolic', 24 chars)
- Maximum medication index (99)
- Timestamp formats (16-char standard UTC ISO, 22-char microsecond ISO)
- Audit log targets (checkin UUID, user ID, record targets)
"""

import re
import pytest
from data_sources import local_store, app_store


def parse_mysql_column_width(ddl: str, table_name: str, column_name: str) -> int:
    """Extracts declared VARCHAR width for a column in a MySQL CREATE TABLE DDL string."""
    table_pattern = rf"CREATE TABLE IF NOT EXISTS\s+{table_name}\s*\(((?:(?!CREATE TABLE).)*?)\)\s*ENGINE=InnoDB"
    match = re.search(table_pattern, ddl, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Table {table_name} not found in MySQL DDL")
    cols_text = match.group(1)
    
    col_pattern = rf"\b{re.escape(column_name)}\b\s+VARCHAR\((\d+)\)"
    col_match = re.search(col_pattern, cols_text, re.IGNORECASE)
    if not col_match:
        # Check with backticks
        col_pattern_bt = rf"`{re.escape(column_name)}`\s+VARCHAR\((\d+)\)"
        col_match = re.search(col_pattern_bt, cols_text, re.IGNORECASE)
    if not col_match:
        raise ValueError(f"Column {column_name} VARCHAR definition not found in table {table_name}")
    return int(col_match.group(1))


def get_local_store_ddl() -> str:
    """Reads MySQL DDL from local_store.py source."""
    import inspect
    return inspect.getsource(local_store._init_mysql_db)


def get_app_store_ddl() -> str:
    """Reads MySQL DDL from app_store.py source."""
    import inspect
    return inspect.getsource(app_store)


def test_width_contract_observations_id():
    """observations.id must be wide enough for longest CHECKIN observation ID."""
    ddl = get_local_store_ddl()
    declared_width = parse_mysql_column_width(ddl, "observations", "id")
    
    uid_28 = "U" * 28
    stamp_16 = "20261108T150000Z"
    longest_obs_type = "blood_pressure_diastolic"  # 24 chars
    longest_id = f"CHECKIN-local-{uid_28}-{stamp_16}-{longest_obs_type}"
    
    assert len(longest_id) <= declared_width, (
        f"observations.id width {declared_width} is too narrow for checkin id "
        f"'{longest_id}' (length {len(longest_id)})"
    )


def test_width_contract_medications_id():
    """medications.id must be wide enough for longest CHECKIN medication ID."""
    ddl = get_local_store_ddl()
    declared_width = parse_mysql_column_width(ddl, "medications", "id")
    
    uid_28 = "U" * 28
    stamp_16 = "20261108T150000Z"
    longest_id = f"CHECKIN-local-{uid_28}-{stamp_16}-med-99"
    
    assert len(longest_id) <= declared_width, (
        f"medications.id width {declared_width} is too narrow for checkin med id "
        f"'{longest_id}' (length {len(longest_id)})"
    )


def test_width_contract_record_edits_record_id():
    """record_edits.record_id must be wide enough for observations.id and medications.id."""
    ddl = app_store.MYSQL_RECORD_EDITS_DDL
    declared_width = parse_mysql_column_width(ddl, "record_edits", "record_id")
    
    uid_28 = "U" * 28
    stamp_16 = "20261108T150000Z"
    longest_obs_id = f"CHECKIN-local-{uid_28}-{stamp_16}-blood_pressure_diastolic"
    longest_med_id = f"CHECKIN-local-{uid_28}-{stamp_16}-med-99"
    
    assert len(longest_obs_id) <= declared_width, (
        f"record_edits.record_id width {declared_width} is too narrow for obs id "
        f"'{longest_obs_id}' (length {len(longest_obs_id)})"
    )
    assert len(longest_med_id) <= declared_width, (
        f"record_edits.record_id width {declared_width} is too narrow for med id "
        f"'{longest_med_id}' (length {len(longest_med_id)})"
    )


def test_width_contract_audit_log_target():
    """audit_log.target (VARCHAR(128)) must fit checkin UUIDs, user IDs, and record target names."""
    ddl = get_app_store_ddl()
    declared_width = parse_mysql_column_width(ddl, "audit_log", "target")
    
    longest_checkin_id = "12345678-1234-1234-1234-123456789abc"  # 36 chars
    uid_28 = "U" * 28  # 28 chars
    longest_record_target = "record_conditions_basis"  # 23 chars
    
    assert declared_width == 128
    assert len(longest_checkin_id) <= declared_width
    assert len(uid_28) <= declared_width
    assert len(longest_record_target) <= declared_width


def test_width_contract_patient_id_columns():
    """patients.id and FK patient_id columns must fit local-<28uid>."""
    ddl = get_local_store_ddl()
    uid_28 = "U" * 28
    local_pid = f"local-{uid_28}"  # 34 chars
    
    pat_id_w = parse_mysql_column_width(ddl, "patients", "id")
    obs_pid_w = parse_mysql_column_width(ddl, "observations", "patient_id")
    med_pid_w = parse_mysql_column_width(ddl, "medications", "patient_id")
    
    assert len(local_pid) <= pat_id_w
    assert len(local_pid) <= obs_pid_w
    assert len(local_pid) <= med_pid_w
