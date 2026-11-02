"""
In-Process Simulated FHIR R4 Server for Connected Mode Demonstrations & Hermetic Testing.

Provides synthetic FHIR R4 resources with deterministic, dynamic timestamps relative to `now`.
No real patient data. Never represents itself as a real hospital.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List
import copy

SAMPLE_PRACTITIONERS: Dict[str, Dict[str, Any]] = {
    "prac-sim-tahir": {
        "resourceType": "Practitioner",
        "id": "prac-sim-tahir",
        "identifier": [{"system": "http://hospital.sim/practitioners", "value": "SIM-MD-101"}],
        "name": [{"family": "Mansoor", "given": ["Dr. Tahir"], "prefix": ["Dr."]}],
        "gender": "male",
    },
    "prac-sim-fatima": {
        "resourceType": "Practitioner",
        "id": "prac-sim-fatima",
        "identifier": [{"system": "http://hospital.sim/practitioners", "value": "SIM-MD-102"}],
        "name": [{"family": "Tariq", "given": ["Dr. Fatima"], "prefix": ["Dr."]}],
        "gender": "female",
    },
    "prac-sim-zubair": {
        "resourceType": "Practitioner",
        "id": "prac-sim-zubair",
        "identifier": [{"system": "http://hospital.sim/practitioners", "value": "SIM-MD-103"}],
        "name": [{"family": "Farooq", "given": ["Dr. Zubair"], "prefix": ["Dr."]}],
        "gender": "male",
    },
}

SAMPLE_PATIENTS: Dict[str, Dict[str, Any]] = {
    "sim-ayesha": {
        "id": "sim-ayesha",
        "name": "Ayesha K.",
        "age": 52,
        "gender": "female",
        "conditions": ["Type 2 Diabetes Mellitus", "Essential Hypertension"],
        "description": "BP about 128/82 daily for 7 days; fasting glucose 140 to 150",
    },
    "sim-bilal": {
        "id": "sim-bilal",
        "name": "Bilal A.",
        "age": 67,
        "gender": "male",
        "conditions": ["Essential Hypertension"],
        "description": "BP 110 to 116 over 70 to 74 daily for 10 days (a low, stable personal baseline)",
    },
    "sim-sana": {
        "id": "sim-sana",
        "name": "Sana M.",
        "age": 45,
        "gender": "female",
        "conditions": ["Type 2 Diabetes Mellitus"],
        "description": "fasting glucose 150 to 175 daily for 7 days",
    },
    "sim-imran": {
        "id": "sim-imran",
        "name": "Imran Q.",
        "age": 71,
        "gender": "male",
        "conditions": ["Type 2 Diabetes Mellitus", "Essential Hypertension"],
        "description": "BP 148 to 156 over 92 to 98, rising; glucose 180 to 210",
    },
    "sim-newpatient": {
        "id": "sim-newpatient",
        "name": "Nadia R.",
        "age": 38,
        "gender": "female",
        "conditions": ["Essential Hypertension"],
        "description": "no observations at all, one active medication",
    },
    "sim-child": {
        "id": "sim-child",
        "name": "Zain B.",
        "age": 12,
        "gender": "male",
        "conditions": ["Type 1 Diabetes Mellitus"],
        "description": "Paediatric patient (age 12)",
    },
}


def _get_now(now: Optional[datetime] = None) -> datetime:
    if now is not None:
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    return datetime.now(timezone.utc)


def _iso_offset(base: datetime, days_ago: float, hours_ago: float = 0.0) -> str:
    dt = base - timedelta(days=days_ago, hours=hours_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dob_for_age(base: datetime, age_years: int) -> str:
    # approximate birthDate YYYY-MM-DD
    year = base.year - age_years
    return f"{year:04d}-05-15"


def _build_synthetic_dataset(now: datetime) -> Dict[str, Dict[str, Any]]:
    # 1. sim-ayesha: 52yo, T2D + HTN, BP ~128/82 daily for 7 days (LOINC 55284-4), fasting glucose 140-150
    ayesha_dob = _dob_for_age(now, 52)
    ayesha_obs = []
    for d in range(7):
        ts = _iso_offset(now, days_ago=d, hours_ago=2.0)
        sys_val = 126.0 + (d % 3) * 2.0  # 126, 128, 130
        dia_val = 80.0 + (d % 3) * 2.0  # 80, 82, 84
        gluc_val = 142.0 + (d % 4) * 3.0  # 142, 145, 148, 151
        
        # BP Panel coded 55284-4 (Blood Pressure)
        ayesha_obs.append({
            "resourceType": "Observation",
            "id": f"obs-ayesha-bp-{d}",
            "status": "final",
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "55284-4", "display": "Blood Pressure"}
                ],
                "text": "Blood Pressure"
            },
            "subject": {"reference": "Patient/sim-ayesha"},
            "effectiveDateTime": ts,
            "component": [
                {
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]
                    },
                    "valueQuantity": {"value": sys_val, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]
                    },
                    "valueQuantity": {"value": dia_val, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
        })
        # Glucose
        ayesha_obs.append({
            "resourceType": "Observation",
            "id": f"obs-ayesha-glu-{d}",
            "status": "final",
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "2339-0", "display": "Glucose [Mass/volume] in Blood"}
                ],
                "text": "Fasting Blood Glucose"
            },
            "subject": {"reference": "Patient/sim-ayesha"},
            "effectiveDateTime": ts,
            "valueQuantity": {"value": gluc_val, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"}
        })

    ayesha_meds = [
        {
            "resourceType": "MedicationRequest",
            "id": "med-ayesha-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin hydrochloride 500 MG Oral Tablet"}],
                "text": "Metformin 500 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-ayesha"},
            "authoredOn": _iso_offset(now, days_ago=30),
            "dosageInstruction": [{"text": "500 mg twice daily"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-ayesha-2",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "314076", "display": "Lisinopril 10 MG Oral Tablet"}],
                "text": "Lisinopril 10 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-ayesha"},
            "authoredOn": _iso_offset(now, days_ago=30),
            "dosageInstruction": [{"text": "10 mg once daily in the morning"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-ayesha-3",
            "status": "stopped",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197737", "display": "Glibenclamide 5 MG Oral Tablet"}],
                "text": "Glibenclamide 5 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-ayesha"},
            "authoredOn": _iso_offset(now, days_ago=90),
            "dosageInstruction": [{"text": "5 mg once daily (Discontinued)"}]
        }
    ]

    ayesha_allergies = [
        {
            "resourceType": "AllergyIntolerance",
            "id": "alg-ayesha-1",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]},
            "criticality": "high",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "373270004", "display": "Penicillin G"}], "text": "Penicillin G"},
            "patient": {"reference": "Patient/sim-ayesha"},
            "reaction": [{"manifestation": [{"coding": [{"system": "http://snomed.info/sct", "code": "247472004", "display": "Urticaria"}], "text": "Hives and facial swelling"}]}]
        },
        {
            "resourceType": "AllergyIntolerance",
            "id": "alg-ayesha-2",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "entered-in-error"}]},
            "criticality": "low",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "387458008", "display": "Aspirin"}], "text": "Aspirin"},
            "patient": {"reference": "Patient/sim-ayesha"}
        }
    ]

    # 2. sim-bilal: 67yo, HTN, BP 110-116/70-74 daily for 10 days (LOINC 55284-4), Amlodipine 5mg
    bilal_dob = _dob_for_age(now, 67)
    bilal_obs = []
    for d in range(10):
        ts = _iso_offset(now, days_ago=d, hours_ago=3.0)
        sys_val = 110.0 + (d % 4) * 2.0  # 110, 112, 114, 116
        dia_val = 70.0 + (d % 3) * 2.0  # 70, 72, 74
        bilal_obs.append({
            "resourceType": "Observation",
            "id": f"obs-bilal-bp-{d}",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "55284-4", "display": "Blood Pressure"}],
                "text": "Blood Pressure"
            },
            "subject": {"reference": "Patient/sim-bilal"},
            "effectiveDateTime": ts,
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": sys_val, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": dia_val, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
        })

    bilal_meds = [
        {
            "resourceType": "MedicationRequest",
            "id": "med-bilal-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197361", "display": "Amlodipine 5 MG Oral Tablet"}],
                "text": "Amlodipine 5 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-bilal"},
            "authoredOn": _iso_offset(now, days_ago=45),
            "dosageInstruction": [{"text": "5 mg once daily"}]
        }
    ]

    # 3. sim-sana: 45yo, T2D on insulin, glucose 150-175 daily for 7 days, Insulin glargine + Metformin
    sana_dob = _dob_for_age(now, 45)
    sana_obs = []
    for d in range(7):
        ts = _iso_offset(now, days_ago=d, hours_ago=1.0)
        gluc_val = 152.0 + (d % 5) * 5.0  # 152, 157, 162, 167, 172
        sana_obs.append({
            "resourceType": "Observation",
            "id": f"obs-sana-glu-{d}",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Glucose [Mass/volume] in Blood"}],
                "text": "Blood Glucose"
            },
            "subject": {"reference": "Patient/sim-sana"},
            "effectiveDateTime": ts,
            "valueQuantity": {"value": gluc_val, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"}
        })

    sana_meds = [
        {
            "resourceType": "MedicationRequest",
            "id": "med-sana-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "285018", "display": "Insulin Glargine 100 UNT/ML Injectable Solution"}],
                "text": "Insulin glargine 100 units/mL"
            },
            "subject": {"reference": "Patient/sim-sana"},
            "authoredOn": _iso_offset(now, days_ago=60),
            "dosageInstruction": [{"text": "20 units subcutaneously at bedtime"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-sana-2",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin hydrochloride 500 MG Oral Tablet"}],
                "text": "Metformin 500 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-sana"},
            "authoredOn": _iso_offset(now, days_ago=60),
            "dosageInstruction": [{"text": "500 mg twice daily with meals"}]
        }
    ]

    # 4. sim-imran: 71yo, T2D + HTN, rising BP 148-156/92-98 (LOINC 85354-9), glucose 180-210
    imran_dob = _dob_for_age(now, 71)
    imran_obs = []
    for d in range(7):
        ts = _iso_offset(now, days_ago=d, hours_ago=2.5)
        # Rising BP: day 6 (oldest) = 148, day 0 (newest) = 156
        sys_val = 156.0 - (d * 1.3)
        dia_val = 98.0 - (d * 1.0)
        gluc_val = 210.0 - (d * 4.0)
        
        # BP Panel coded 85354-9
        imran_obs.append({
            "resourceType": "Observation",
            "id": f"obs-imran-bp-{d}",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel with all children optional"}],
                "text": "Blood Pressure Panel"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "effectiveDateTime": ts,
            "component": [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": round(sys_val, 1), "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": round(dia_val, 1), "unit": "mm[Hg]", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
        })
        imran_obs.append({
            "resourceType": "Observation",
            "id": f"obs-imran-glu-{d}",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Glucose [Mass/volume] in Blood"}],
                "text": "Blood Glucose"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "effectiveDateTime": ts,
            "valueQuantity": {"value": round(gluc_val, 1), "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"}
        })

    imran_meds = [
        {
            "resourceType": "MedicationRequest",
            "id": "med-imran-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin hydrochloride 500 MG Oral Tablet"}],
                "text": "Metformin 500 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "authoredOn": _iso_offset(now, days_ago=90),
            "dosageInstruction": [{"text": "500 mg twice daily"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-imran-2",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "314076", "display": "Lisinopril 10 MG Oral Tablet"}],
                "text": "Lisinopril 10 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "authoredOn": _iso_offset(now, days_ago=90),
            "dosageInstruction": [{"text": "10 mg once daily"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-imran-3",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "259255", "display": "Atorvastatin 20 MG Oral Tablet"}],
                "text": "Atorvastatin 20 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "authoredOn": _iso_offset(now, days_ago=90),
            "dosageInstruction": [{"text": "20 mg once daily at bedtime"}]
        },
        {
            "resourceType": "MedicationRequest",
            "id": "med-imran-4",
            "status": "stopped",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "243670", "display": "Aspirin 81 MG Oral Tablet"}],
                "text": "Aspirin 81 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-imran"},
            "authoredOn": _iso_offset(now, days_ago=120),
        }
    ]

    imran_allergies = [
        {
            "resourceType": "AllergyIntolerance",
            "id": "alg-imran-1",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]},
            "criticality": "high",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "91936005", "display": "Sulfonamide allergy"}], "text": "Sulfa antibiotics"},
            "patient": {"reference": "Patient/sim-imran"},
            "reaction": [{"manifestation": [{"text": "Cutaneous rash"}]}]
        }
    ]

    # 5. sim-newpatient: 38yo, HTN, NO observations, 1 active med
    newpat_dob = _dob_for_age(now, 38)
    newpat_meds = [
        {
            "resourceType": "MedicationRequest",
            "id": "med-newpat-1",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "314076", "display": "Lisinopril 10 MG Oral Tablet"}],
                "text": "Lisinopril 10 mg Oral Tablet"
            },
            "subject": {"reference": "Patient/sim-newpatient"},
            "authoredOn": _iso_offset(now, days_ago=10),
            "dosageInstruction": [{"text": "10 mg once daily"}]
        }
    ]

    # 6. sim-child: 12yo for under-18 testing
    child_dob = _dob_for_age(now, 12)

    dataset: Dict[str, Dict[str, Any]] = {
        "sim-ayesha": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-ayesha",
                "name": [{"family": "K.", "given": ["Ayesha"]}],
                "gender": "female",
                "birthDate": ayesha_dob,
                "generalPractitioner": [{"reference": "Practitioner/prac-sim-fatima", "display": "Dr. Fatima Tariq"}]
            },
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-ayesha-1",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"}], "text": "Type 2 diabetes mellitus"},
                    "subject": {"reference": "Patient/sim-ayesha"}
                },
                {
                    "resourceType": "Condition",
                    "id": "cond-ayesha-2",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}], "text": "Essential hypertension"},
                    "subject": {"reference": "Patient/sim-ayesha"}
                }
            ],
            "observations": ayesha_obs,
            "medications": ayesha_meds,
            "allergies": ayesha_allergies,
        },
        "sim-bilal": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-bilal",
                "name": [{"family": "A.", "given": ["Bilal"]}],
                "gender": "male",
                "birthDate": bilal_dob,
                "generalPractitioner": [{"reference": "Practitioner/prac-sim-tahir", "display": "Dr. Tahir Mansoor"}]
            },
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-bilal-1",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}], "text": "Essential hypertension"},
                    "subject": {"reference": "Patient/sim-bilal"}
                }
            ],
            "observations": bilal_obs,
            "medications": bilal_meds,
            "allergies": [],
        },
        "sim-sana": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-sana",
                "name": [{"family": "M.", "given": ["Sana"]}],
                "gender": "female",
                "birthDate": sana_dob,
                "generalPractitioner": [{"reference": "Practitioner/prac-sim-fatima", "display": "Dr. Fatima Tariq"}]
            },
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-sana-1",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"}], "text": "Type 2 diabetes mellitus"},
                    "subject": {"reference": "Patient/sim-sana"}
                }
            ],
            "observations": sana_obs,
            "medications": sana_meds,
            "allergies": [],
        },
        "sim-imran": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-imran",
                "name": [{"family": "Q.", "given": ["Imran"]}],
                "gender": "male",
                "birthDate": imran_dob,
                "generalPractitioner": [{"reference": "Practitioner/prac-sim-zubair", "display": "Dr. Zubair Farooq"}]
            },
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-imran-1",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11", "display": "Type 2 diabetes mellitus"}], "text": "Type 2 diabetes mellitus"},
                    "subject": {"reference": "Patient/sim-imran"}
                },
                {
                    "resourceType": "Condition",
                    "id": "cond-imran-2",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}], "text": "Essential hypertension"},
                    "subject": {"reference": "Patient/sim-imran"}
                }
            ],
            "observations": imran_obs,
            "medications": imran_meds,
            "allergies": imran_allergies,
        },
        "sim-newpatient": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-newpatient",
                "name": [{"family": "R.", "given": ["Nadia"]}],
                "gender": "female",
                "birthDate": newpat_dob
            },
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-newpat-1",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}], "text": "Essential hypertension"},
                    "subject": {"reference": "Patient/sim-newpatient"}
                }
            ],
            "observations": [],
            "medications": newpat_meds,
            "allergies": [],
        },
        "sim-child": {
            "patient": {
                "resourceType": "Patient",
                "id": "sim-child",
                "name": [{"family": "Patient", "given": ["Child"]}],
                "gender": "other",
                "birthDate": child_dob,
                "generalPractitioner": [{"reference": "Practitioner/prac-sim-fatima", "display": "Dr. Fatima Tariq"}]
            },
            "conditions": [],
            "observations": [],
            "medications": [],
            "allergies": [],
        }
    }

    fixtures = _load_fixtures_from_disk(now)
    dataset.update(fixtures)
    return dataset


def _load_fixtures_from_disk(now: datetime) -> Dict[str, Dict[str, Any]]:
    """Loads external fixtures from fhir_sim_fixtures directory."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fhir_sim_fixtures")
    if not os.path.isdir(fixtures_dir):
        return {}
    results = {}
    for fname in sorted(os.listdir(fixtures_dir)):
        if fname.startswith("sim-syn-") and fname.endswith(".json"):
            fpath = os.path.join(fixtures_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pid = data.get("patient", {}).get("id")
                if pid:
                    results[pid] = data
                    # Register practitioner if present
                    prac = data.get("practitioner")
                    if prac and isinstance(prac, dict) and prac.get("id"):
                        SAMPLE_PRACTITIONERS[prac["id"]] = prac
                    # Also register in SAMPLE_PATIENTS for backwards-compatibility
                    if pid not in SAMPLE_PATIENTS:
                        SAMPLE_PATIENTS[pid] = {
                            "id": pid,
                            "name": " ".join(data.get("patient", {}).get("name", [{}])[0].get("given", [])) + " " + data.get("patient", {}).get("name", [{}])[0].get("family", ""),
                            "age": now.year - int(data.get("patient", {}).get("birthDate", "1970")[:4]),
                            "gender": data.get("patient", {}).get("gender", "unknown"),
                            "conditions": [c.get("code", {}).get("text", "Condition") for c in data.get("conditions", [])],
                            "description": data.get("description", "Simulated (Synthea) patient"),
                        }
            except Exception:
                pass
    return results


def _make_bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"fullUrl": f"sim://demo/{r.get('resourceType')}/{r.get('id')}", "resource": r} for r in resources]
    }


def handle(path: str, params: Optional[Dict[str, Any]] = None, now: Optional[datetime] = None) -> Tuple[int, Dict[str, Any]]:
    """
    Handles a simulated FHIR request deterministically.
    Returns (status_code, json_dict).
    """
    current_time = _get_now(now)
    dataset = _build_synthetic_dataset(current_time)
    params = params or {}

    clean_path = path.strip("/").split("?")[0]

    # 1. Metadata endpoint
    if clean_path in ("metadata", ""):
        return 200, {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "date": _iso_offset(current_time, 0),
            "kind": "instance",
            "fhirVersion": "4.0.0",
            "format": ["json"],
            "software": {"name": "ChronicCare In-Process FHIR Simulator", "version": "1.0.0"}
        }

    # 2. Patient read or search
    if clean_path.startswith("Patient/"):
        patient_id = clean_path.split("/", 1)[1].strip()
        if patient_id in dataset:
            return 200, copy.deepcopy(dataset[patient_id]["patient"])
        return 404, {
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"Patient '{patient_id}' not found in simulator"}]
        }

    if clean_path == "Patient":
        count = int(params.get("_count", 10))
        resources = [data["patient"] for data in dataset.values()][:count]
        return 200, _make_bundle(copy.deepcopy(resources))

    # 2b. Practitioner read
    if clean_path.startswith("Practitioner/"):
        prac_id = clean_path.split("/", 1)[1].strip()
        if prac_id in SAMPLE_PRACTITIONERS:
            return 200, copy.deepcopy(SAMPLE_PRACTITIONERS[prac_id])
        return 404, {
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"Practitioner '{prac_id}' not found in simulator"}]
        }

    # 3. Observation search
    if clean_path == "Observation":
        patient_id = params.get("patient") or params.get("subject")
        if not patient_id:
            return 400, {
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "invalid", "diagnostics": "Missing patient search parameter"}]
            }
        patient_id = patient_id.replace("Patient/", "")
        if patient_id not in dataset:
            return 200, _make_bundle([])
        
        obs_list = copy.deepcopy(dataset[patient_id]["observations"])
        # _sort=-date: observations already in descending chronological order
        count = int(params.get("_count", 100))
        return 200, _make_bundle(obs_list[:count])

    # 4. MedicationRequest search
    if clean_path == "MedicationRequest":
        patient_id = params.get("patient") or params.get("subject")
        if not patient_id:
            return 400, {
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "invalid", "diagnostics": "Missing patient search parameter"}]
            }
        patient_id = patient_id.replace("Patient/", "")
        if patient_id not in dataset:
            return 200, _make_bundle([])
        
        meds_list = copy.deepcopy(dataset[patient_id]["medications"])
        count = int(params.get("_count", 100))
        return 200, _make_bundle(meds_list[:count])

    # 5. Condition search
    if clean_path == "Condition":
        patient_id = params.get("patient") or params.get("subject")
        if not patient_id:
            return 400, {
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "invalid", "diagnostics": "Missing patient search parameter"}]
            }
        patient_id = patient_id.replace("Patient/", "")
        if patient_id not in dataset:
            return 200, _make_bundle([])
        
        conds_list = copy.deepcopy(dataset[patient_id]["conditions"])
        count = int(params.get("_count", 100))
        return 200, _make_bundle(conds_list[:count])

    # 6. AllergyIntolerance search
    if clean_path == "AllergyIntolerance":
        patient_id = params.get("patient") or params.get("subject")
        if not patient_id:
            return 400, {
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "invalid", "diagnostics": "Missing patient search parameter"}]
            }
        patient_id = patient_id.replace("Patient/", "")
        if patient_id not in dataset:
            return 200, _make_bundle([])
        
        alg_list = copy.deepcopy(dataset[patient_id].get("allergies", []))
        count = int(params.get("_count", 100))
        return 200, _make_bundle(alg_list[:count])

    return 404, {
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"Resource path '{clean_path}' not supported by simulator"}]
    }
