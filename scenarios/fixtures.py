"""
Synthetic Test Fixtures for Milestone 3 (Reconciliation Agent)

Contains hand-authored synthetic paired bundles (Connected Mode + Isolated Mode)
conforming to the exact M2 Normalized Data Models.
All records are explicitly labeled as synthetic test data.

Pairs included:
1. CLEAN_AGREE_PAIR: Consistent values within thresholds (Positive test / Negative control).
2. CONFLICT_PAIR: Values beyond threshold within 48h window & medication status/dosage mismatch.
3. MISSING_DATA_PAIR: Observations and medications present in one source but absent in the other.
4. INSUFFICIENT_DATA_PAIR: Matched observation within 48h window with unusable/missing value.
5. NEGATIVE_CONTROL_PAIR: 100% exact value agreement across sources (zero conflicts/insufficient_data).
"""

from data_sources.models import NormalizedPatient, NormalizedObservation, NormalizedMedication

# 1. CLEAN AGREE PAIR (Observations and Medications agree within thresholds)
CLEAN_AGREE_PAIR = {
    "name": "Clean Agree Pair",
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
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="glucose", value=145.0, unit="mg/dL", timestamp="2026-08-15T12:00:00Z", source="local", source_record_id="LOC-OBS-01"), # delta 5 <= 15
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="hba1c", value=7.1, unit="%", timestamp="2026-08-15T12:00:00Z", source="local", source_record_id="LOC-OBS-02"), # delta 0.1 <= 0.5
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="blood_pressure_systolic", value=132.0, unit="mmHg", timestamp="2026-08-15T12:00:00Z", source="local", source_record_id="LOC-OBS-03"), # delta 2 <= 10
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-001", observation_type="weight", value=75.5, unit="kg", timestamp="2026-08-15T12:00:00Z", source="local", source_record_id="LOC-OBS-04"), # delta 0.5 <= 2.0
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-001", medication_name="Metformin 500mg", status="active", dosage="1 tablet twice daily", timestamp="2026-01-01T00:00:00Z", source="local", source_record_id="LOC-MED-01")
        ]
    }
}

# 2. CONFLICT PAIR (Values exceed thresholds within 48h & medication status mismatch)
CONFLICT_PAIR = {
    "name": "Conflict Pair",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-002", name="Bob Smith", date_of_birth="1965-05-12"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-21"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="hba1c", value=6.5, unit="%", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-22"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-002", medication_name="Lisinopril 10mg", status="active", dosage="1 tablet daily", timestamp="2026-02-01T00:00:00Z", source="fhir", source_record_id="FHIR-MED-21")
        ]
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-002", name="Bob Smith", date_of_birth="1965-05-12"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="glucose", value=165.0, unit="mg/dL", timestamp="2026-08-15T14:00:00Z", source="local", source_record_id="LOC-OBS-21"), # delta 55 > 15 threshold
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-002", observation_type="hba1c", value=8.2, unit="%", timestamp="2026-08-15T14:00:00Z", source="local", source_record_id="LOC-OBS-22"), # delta 1.7 > 0.5 threshold
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-002", medication_name="Lisinopril 10mg", status="stopped", dosage="1 tablet daily", timestamp="2026-03-01T00:00:00Z", source="local", source_record_id="LOC-MED-21") # status mismatch
        ]
    }
}

# 3. MISSING DATA PAIR (Observations and Medications present in one source, absent in the other)
MISSING_DATA_PAIR = {
    "name": "Missing Data Pair",
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
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="glucose", value=132.0, unit="mg/dL", timestamp="2026-08-15T11:00:00Z", source="local", source_record_id="LOC-OBS-31"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-003", observation_type="hba1c", value=7.4, unit="%", timestamp="2026-08-15T11:00:00Z", source="local", source_record_id="LOC-OBS-32"), # missing in A
        ],
        "medications": []
    }
}

# 4. INSUFFICIENT DATA PAIR (Matched observation within 48h window with non-numeric value)
INSUFFICIENT_DATA_PAIR = {
    "name": "Insufficient Data Pair",
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
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-004", observation_type="glucose", value=None, unit="mg/dL", timestamp="2026-08-15T11:00:00Z", source="local", source_record_id="LOC-OBS-41") # None value
        ],
        "medications": []
    }
}

# 5. NEGATIVE CONTROL PAIR (100% exact agreement across all fields)
NEGATIVE_CONTROL_PAIR = {
    "name": "Negative Control Pair (100% Exact Agreement)",
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
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="glucose", value=120.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-51"),
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-005", observation_type="weight", value=70.0, unit="kg", timestamp="2026-08-15T10:00:00Z", source="local", source_record_id="LOC-OBS-52"),
        ],
        "medications": [
            NormalizedMedication(patient_id="SYNTHETIC-PATIENT-MATCH-005", medication_name="Aspirin 81mg", status="active", dosage="1 tablet daily", timestamp="2026-05-01T00:00:00Z", source="local", source_record_id="LOC-MED-51")
        ]
    }
}

# 6. NEAR-THRESHOLD CONFLICT PAIR (Milestone 4: Delta exceeds 1x threshold but within 2x -> moderate severity)
NEAR_THRESHOLD_CONFLICT_PAIR = {
    "name": "Near-Threshold Conflict Pair (1x-2x Threshold)",
    "bundle_a": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-006", name="Fiona Gallagher", date_of_birth="1988-09-30"),
        "observations": [
            # Glucose threshold = 15.0 mg/dL. 110 vs 128 -> delta 18.0 (15.0 < 18.0 <= 30.0 -> moderate)
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-006", observation_type="glucose", value=110.0, unit="mg/dL", timestamp="2026-08-15T10:00:00Z", source="fhir", source_record_id="FHIR-OBS-61")
        ],
        "medications": []
    },
    "bundle_b": {
        "patient": NormalizedPatient(patient_id="SYNTHETIC-PATIENT-MATCH-006", name="Fiona Gallagher", date_of_birth="1988-09-30"),
        "observations": [
            NormalizedObservation(patient_id="SYNTHETIC-PATIENT-MATCH-006", observation_type="glucose", value=128.0, unit="mg/dL", timestamp="2026-08-15T10:30:00Z", source="local", source_record_id="LOC-OBS-61")
        ],
        "medications": []
    }
}

# 7. LOW-TRUST AGREE PAIR (Milestone 4: Both sources are low trust -> agree -> severity low & requires review)
LOW_TRUST_AGREE_PAIR = {
    "name": "Low-Trust Agree Pair (Self-Reported Both Sides)",
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
