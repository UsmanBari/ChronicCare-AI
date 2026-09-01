"""
Synthetic Test Fixtures for Milestone 3 & Milestone 4 (Reconciliation & Verification Agents)

Contains hand-authored synthetic paired bundles representing SAME-PATIENT, SAME-MODE
reconciliation scenarios:
- Connected Mode (FHIR + FHIR): Prior FHIR state vs. new FHIR check-in for Patient A
- Isolated Mode (Local + Local): Prior Local Store state vs. new Local check-in for Patient B

ALL pairs strictly satisfy:
1. Identity invariant: patient_id_A == patient_id_B
2. Store invariant: source_A == source_B (both "fhir" or both "local")
3. Mode invariant: Each scenario is 100% Connected Mode or 100% Isolated Mode.
4. Semantic invariant: Bundle A = prior/existing state, Bundle B = new incoming check-in/report.
"""

from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication

# 1. CLEAN AGREE PAIR (Connected Mode: FHIR Patient A prior state vs. new check-in)
CLEAN_AGREE_PAIR = {
    "name": "Clean Agree Pair (Connected Mode)",
    "mode": "connected",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-001", name="Alice Miller", date_of_birth="1970-01-01"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="glucose", value=140.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-01"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="hba1c", value=7.0, unit="%", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-02"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="blood_pressure_systolic", value=130.0, unit="mmHg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-03"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="weight", value=75.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-04"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-001", medication_name="Metformin 500mg", status="active", dosage="1 tablet twice daily", timestamp="2026-01-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-01")
        ]
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-001", name="Alice Miller", date_of_birth="1970-01-01"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="glucose", value=145.0, unit="mg/dL", timestamp="2026-08-15T12:00:00Z", source="fhir", source_record_id="FHIR-OBS-01-CHECKIN"), # delta 5 <= 15
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="hba1c", value=7.1, unit="%", timestamp="2026-08-15T12:00:00Z", source="fhir", source_record_id="FHIR-OBS-02-CHECKIN"), # delta 0.1 <= 0.5
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="blood_pressure_systolic", value=132.0, unit="mmHg", timestamp="2026-08-15T12:00:00Z", source="fhir", source_record_id="FHIR-OBS-03-CHECKIN"), # delta 2 <= 10
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="weight", value=75.5, unit="kg", timestamp="2026-08-15T12:00:00Z", source="fhir", source_record_id="FHIR-OBS-04-CHECKIN"), # delta 0.5 <= 2.0
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-001", medication_name="Metformin 500mg", status="active", dosage="1 tablet twice daily", timestamp="2026-01-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-01-CHECKIN")
        ]
    }
}

# 2. CONFLICT PAIR (Isolated Mode: Local Patient B prior state vs. new check-in)
CONFLICT_PAIR = {
    "name": "Conflict Pair (Isolated Mode)",
    "mode": "isolated",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-002", name="Bob Smith", date_of_birth="1965-05-12"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-21"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="hba1c", value=6.5, unit="%", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-22"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-002", medication_name="Lisinopril 10mg", status="active", dosage="1 tablet daily", timestamp="2026-02-01T00:00:00Z", source="local", source_record_id="LOC-MED-21")
        ]
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-002", name="Bob Smith", date_of_birth="1965-05-12"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="glucose", value=165.0, unit="mg/dL", timestamp="2026-08-15T14:00:00Z", source="local", source_record_id="LOC-OBS-21-CHECKIN"), # delta 55 > 15 threshold
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="hba1c", value=8.2, unit="%", timestamp="2026-08-15T14:00:00Z", source="local", source_record_id="LOC-OBS-22-CHECKIN"), # delta 1.7 > 0.5 threshold
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-002", medication_name="Lisinopril 10mg", status="stopped", dosage="1 tablet daily", timestamp="2026-03-01T00:00:00Z", source="local", source_record_id="LOC-MED-21-CHECKIN") # status mismatch
        ]
    }
}

# 3. MISSING DATA PAIR (Connected Mode: FHIR Patient C prior state vs. new check-in)
MISSING_DATA_PAIR = {
    "name": "Missing Data Pair (Connected Mode)",
    "mode": "connected",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-003", name="Charlie Brown", date_of_birth="1980-11-20"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="glucose", value=130.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-31"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="weight", value=82.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-32"), # missing in B
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-003", medication_name="Atorvastatin 20mg", status="active", dosage="1 tablet daily", timestamp="2026-04-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-31") # missing in B
        ]
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-003", name="Charlie Brown", date_of_birth="1980-11-20"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="glucose", value=132.0, unit="mg/dL", timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="FHIR-OBS-31-CHECKIN"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="hba1c", value=7.4, unit="%", timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="FHIR-OBS-32-CHECKIN"), # missing in A, tagged OCR/upload -> medium trust
        ],
        "medications": []
    }
}

# 4. INSUFFICIENT DATA PAIR (Connected Mode: FHIR Patient D prior state vs. unparseable check-in)
INSUFFICIENT_DATA_PAIR = {
    "name": "Insufficient Data Pair (Connected Mode)",
    "mode": "connected",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-004", name="Diana Prince", date_of_birth="1985-03-15"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-004", observation_type="glucose", value=140.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-41")
        ],
        "medications": []
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-004", name="Diana Prince", date_of_birth="1985-03-15"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-004", observation_type="glucose", value=None, unit="mg/dL", timestamp="2026-08-15T11:00:00Z", source="fhir", source_record_id="FHIR-OBS-41-CHECKIN") # None value
        ],
        "medications": []
    }
}

# 5. NEGATIVE CONTROL PAIR (Connected Mode: 100% exact agreement)
NEGATIVE_CONTROL_PAIR = {
    "name": "Negative Control Pair (100% Exact Agreement - Connected Mode)",
    "mode": "connected",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-005", name="Evan Wright", date_of_birth="1992-07-04"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-51"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="weight", value=70.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-52"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-005", medication_name="Aspirin 81mg", status="active", dosage="1 tablet daily", timestamp="2026-05-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-51")
        ]
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-005", name="Evan Wright", date_of_birth="1992-07-04"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-51-CHECKIN"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="weight", value=70.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-52-CHECKIN"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-005", medication_name="Aspirin 81mg", status="active", dosage="1 tablet daily", timestamp="2026-05-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-51-CHECKIN")
        ]
    }
}

# 6. NEAR-THRESHOLD CONFLICT PAIR (Isolated Mode: 1x-2x Threshold -> moderate severity)
NEAR_THRESHOLD_CONFLICT_PAIR = {
    "name": "Near-Threshold Conflict Pair (Isolated Mode)",
    "mode": "isolated",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-006", name="Fiona Gallagher", date_of_birth="1988-09-30"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-006", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-61")
        ],
        "medications": []
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-006", name="Fiona Gallagher", date_of_birth="1988-09-30"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-006", observation_type="glucose", value=128.0, unit="mg/dL", timestamp="2026-08-15T10:30:00Z", source="local", source_record_id="LOC-OBS-61-CHECKIN")
        ],
        "medications": []
    }
}

# 7. LOW-TRUST AGREE PAIR (Isolated Mode: Self-Reported Both Sides -> low severity, requires review)
LOW_TRUST_AGREE_PAIR = {
    "name": "Low-Trust Agree Pair (Isolated Mode)",
    "mode": "isolated",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-007", name="George Harris", date_of_birth="1975-02-14"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-007", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-71")
        ],
        "medications": []
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-007", name="George Harris", date_of_birth="1975-02-14"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-007", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:15:00Z", source="local", source_record_id="LOC-OBS-72")
        ],
        "medications": []
    }
}

# Optional fixture-level origins mapping (does NOT alter M2 models)
FIXTURE_ORIGINS = {
    "LOC-OBS-71": "local_self_reported",
    "LOC-OBS-72": "local_self_reported",
    "FHIR-OBS-32-CHECKIN": "local_ocr_or_upload",  # maps to medium trust for missing_in_a test
}

ALL_FIXTURE_PAIRS = [
    CLEAN_AGREE_PAIR,
    CONFLICT_PAIR,
    MISSING_DATA_PAIR,
    INSUFFICIENT_DATA_PAIR,
    NEGATIVE_CONTROL_PAIR,
    NEAR_THRESHOLD_CONFLICT_PAIR,
    LOW_TRUST_AGREE_PAIR
]


def validate_fixture_invariants(fixture: dict) -> bool:
    """
    Automated invariant validator for test fixtures.
    Enforces:
    1. patient_id_A == patient_id_B
    2. source_A == source_B (both "fhir" or both "local")
    3. source_A in {"fhir", "local"}
    """
    b_a = fixture["bundle_a"]
    b_b = fixture["bundle_b"]

    pid_a = b_a["patient"].patient_id
    pid_b = b_b["patient"].patient_id
    if pid_a != pid_b:
        raise ValueError(f"Identity Invariant Violation in '{fixture.get('name')}': patient_id_A '{pid_a}' != patient_id_B '{pid_b}'")

    sources_a = {o.source for o in b_a.get("observations", [])} | {m.source for m in b_a.get("medications", [])}
    sources_b = {o.source for o in b_b.get("observations", [])} | {m.source for m in b_b.get("medications", [])}
    all_sources = sources_a | sources_b

    if len(all_sources) > 1:
        raise ValueError(f"Store Invariant Violation in '{fixture.get('name')}': mixed sources detected {all_sources}. Must be pure FHIR or pure Local!")

    if all_sources and not all_sources.issubset({"fhir", "local"}):
        raise ValueError(f"Invalid Source Error in '{fixture.get('name')}': source must be 'fhir' or 'local', got {all_sources}")

    return True


# Run invariant check on load to guarantee repo integrity
for _fix in ALL_FIXTURE_PAIRS:
    validate_fixture_invariants(_fix)

