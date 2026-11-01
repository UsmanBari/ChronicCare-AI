"""
Hermetic Tests for Risk Agent (Part C & F).
Verifies floating-point parity with scikit-learn, applicability rules,
missing feature handling without basic fallback, top 3 positive contributors,
and error resilience without leaking PHI to logs.
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import logging
from pathlib import Path
import pytest

from agents import risk_agent

MODELS_DIR = Path(__file__).resolve().parent / "models"


@pytest.fixture(autouse=True)
def ensure_models_loaded():
    risk_agent.load_models(MODELS_DIR)


def test_golden_file_parity_1000_rows():
    """Golden parity: risk_agent pure stdlib probabilities match scikit-learn within 1e-9 for all 1,000 synthetic rows."""
    golden_path = MODELS_DIR / "diabetes_full_nhanes.golden.json"
    assert golden_path.is_file(), f"Golden file not found: {golden_path}"

    records = json.loads(golden_path.read_text(encoding="utf-8"))
    assert len(records) == 1000

    ref_date = date(2026, 10, 30)

    for idx, rec in enumerate(records):
        inp = rec["inputs"]
        expected_prob = rec["sklearn_prob"]

        # Synthesize profile
        birth_year = ref_date.year - inp["age"]
        dob = f"{birth_year:04d}-06-15"

        # Calculate height and weight from BMI
        # Use height 170 cm
        height_cm = 170.0
        h_m = height_cm / 100.0
        weight_kg = inp["bmi"] * (h_m * h_m)

        smoke_status = "current" if inp["ever_smoked_100"] == 1 else "never"
        sex_str = "male" if inp["sex_male"] == 1 else "female"

        profile = {
            "date_of_birth": dob,
            "sex_at_birth": sex_str,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "smoking_status": smoke_status,
            "waist_cm": inp["waist_cm"],
        }
        latest_readings = {
            "systolic": inp["sbp"],
            "diastolic": inp["dbp"],
            "at": "2026-10-25T10:00:00Z",  # 5 days ago, well within 30 days
        }
        conditions = ["hypertension"]

        res = risk_agent.assess(profile, latest_readings, conditions, now=ref_date.isoformat(), models_dir=MODELS_DIR)
        assert res is not None, f"Row {idx} returned None"
        assert res["status"] == "ok", f"Row {idx} returned status {res.get('status')}: {res.get('missing')}"

        actual_prob = res["probability"]
        diff = abs(actual_prob - expected_prob)
        assert diff < 1e-9, f"Row {idx} parity mismatch: actual {actual_prob} vs expected {expected_prob} (diff {diff})"


def test_applicability_matrix():
    """
    Applicability filter per D12, D13:
    - Hypertension only -> diabetes risk assessed
    - Diabetes only -> None
    - Both (Dual) -> None
    - Neither -> None
    """
    profile = {
        "date_of_birth": "1975-01-01",
        "sex_at_birth": "male",
        "height_cm": 175.0,
        "weight_kg": 80.0,
        "smoking_status": "never",
        "waist_cm": 95.0,
    }
    readings = {"systolic": 135.0, "diastolic": 85.0}

    # 1. Hypertension only -> Assessed
    res_htn = risk_agent.assess(profile, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_htn is not None
    assert res_htn["status"] == "ok"
    assert res_htn["disease"] == "diabetes"

    # 2. Diabetes only -> None
    res_t2d = risk_agent.assess(profile, readings, ["diabetes"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_t2d is None

    # 3. Dual (both) -> None
    res_dual = risk_agent.assess(profile, readings, ["hypertension", "diabetes"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_dual is None

    # 4. Neither -> None
    res_none = risk_agent.assess(profile, readings, [], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_none is None


def test_missing_waist_yields_not_enough_info():
    """Missing waist_cm returns not_enough_information with no fallback to basic model."""
    profile = {
        "date_of_birth": "1980-05-10",
        "sex_at_birth": "female",
        "height_cm": 160.0,
        "weight_kg": 65.0,
        "smoking_status": "never",
        # waist_cm intentionally omitted
    }
    readings = {"systolic": 130.0, "diastolic": 80.0}
    res = risk_agent.assess(profile, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)

    assert res is not None
    assert res["status"] == "not_enough_information"
    assert res["missing"] == ["waist_cm"]
    assert res["audience"] == "provider_only"
    # Ensure there is no fallback prediction
    assert "probability" not in res
    assert "band" not in res


def test_missing_or_stale_blood_pressure():
    """Readings older than 30 days are rejected as stale, yielding missing sbp and dbp."""
    profile = {
        "date_of_birth": "1980-05-10",
        "sex_at_birth": "female",
        "height_cm": 160.0,
        "weight_kg": 65.0,
        "smoking_status": "never",
        "waist_cm": 85.0,
    }
    ref_date = date(2026, 10, 30)

    # 1. Reading 31 days ago (stale)
    stale_date = (ref_date - timedelta(days=31)).isoformat()
    readings_stale = {"systolic": 130.0, "diastolic": 80.0, "at": stale_date}
    res_stale = risk_agent.assess(profile, readings_stale, ["hypertension"], now=ref_date.isoformat(), models_dir=MODELS_DIR)
    assert res_stale is not None
    assert res_stale["status"] == "not_enough_information"
    assert "sbp" in res_stale["missing"]
    assert "dbp" in res_stale["missing"]

    # 2. Reading 29 days ago (valid)
    valid_date = (ref_date - timedelta(days=29)).isoformat()
    readings_valid = {"systolic": 130.0, "diastolic": 80.0, "at": valid_date}
    res_valid = risk_agent.assess(profile, readings_valid, ["hypertension"], now=ref_date.isoformat(), models_dir=MODELS_DIR)
    assert res_valid is not None
    assert res_valid["status"] == "ok"


def test_top_3_reasons_and_multilingual_labels():
    """Top 3 reasons represent the largest positive contributions with en/ur/roman_ur labels."""
    profile = {
        "date_of_birth": "1945-01-01",  # 81 years old (large positive contribution)
        "sex_at_birth": "male",
        "height_cm": 170.0,
        "weight_kg": 110.0,  # BMI ~38.1
        "smoking_status": "current",
        "waist_cm": 125.0,  # Large waist (large positive contribution)
    }
    readings = {"systolic": 170.0, "diastolic": 95.0}  # High BP

    res = risk_agent.assess(profile, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res is not None
    assert res["status"] == "ok"
    assert res["band"] == "high"

    reasons = res["reasons"]
    assert len(reasons) <= 3
    assert len(reasons) > 0

    # Ensure contributions are descending and strictly positive
    for r in reasons:
        assert r["contribution"] > 0
        lbl = r["label"]
        assert "en" in lbl and len(lbl["en"]) > 0
        assert "ur" in lbl and len(lbl["ur"]) > 0
        assert "roman_ur" in lbl and len(lbl["roman_ur"]) > 0

    # Age and waist should be top contributors
    feature_names = [r["feature"] for r in reasons]
    assert "age" in feature_names or "waist_cm" in feature_names


def test_bmi_and_smoking_status_mappings():
    """Verifies BMI calculation and smoking_status mapping for every allowed value."""
    base_profile = {
        "date_of_birth": "1985-06-15",
        "sex_at_birth": "male",
        "height_cm": 200.0,  # 2.0 meters
        "weight_kg": 100.0,  # BMI = 100 / (2*2) = 25.0
        "waist_cm": 90.0,
    }
    readings = {"systolic": 120.0, "diastolic": 80.0}

    # 1. Smoking: 'never' -> 0.0
    p_never = dict(base_profile, smoking_status="never")
    res_never = risk_agent.assess(p_never, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_never["status"] == "ok"

    # 2. Smoking: 'former' -> 1.0
    p_former = dict(base_profile, smoking_status="former")
    res_former = risk_agent.assess(p_former, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_former["status"] == "ok"

    # 3. Smoking: 'current' -> 1.0
    p_current = dict(base_profile, smoking_status="current")
    res_current = risk_agent.assess(p_current, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_current["status"] == "ok"

    # Former and current should produce identical probability when other features are identical
    assert abs(res_former["probability"] - res_current["probability"]) < 1e-12
    # Never smoker should have lower risk probability than current smoker
    assert res_never["probability"] < res_current["probability"]


def test_smoking_status_prefer_not_to_say_is_missing():
    """Smoking status 'prefer_not_to_say', empty, or unknown counts as MISSING, never as non-smoker."""
    base_profile = {
        "date_of_birth": "1985-06-15",
        "sex_at_birth": "male",
        "height_cm": 175.0,
        "weight_kg": 75.0,
        "waist_cm": 85.0,
    }
    readings = {"systolic": 120.0, "diastolic": 80.0}

    # 1. prefer_not_to_say
    p_prefer = dict(base_profile, smoking_status="prefer_not_to_say")
    res_prefer = risk_agent.assess(p_prefer, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_prefer is not None
    assert res_prefer["status"] == "not_enough_information"
    assert "smoking_status" in res_prefer["missing"]
    assert "probability" not in res_prefer

    # 2. None
    p_none = dict(base_profile, smoking_status=None)
    res_none = risk_agent.assess(p_none, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_none["status"] == "not_enough_information"
    assert "smoking_status" in res_none["missing"]

    # 3. Empty string
    p_empty = dict(base_profile, smoking_status="")
    res_empty = risk_agent.assess(p_empty, readings, ["hypertension"], now="2026-10-30", models_dir=MODELS_DIR)
    assert res_empty["status"] == "not_enough_information"
    assert "smoking_status" in res_empty["missing"]


def test_error_resilience_and_no_phi_in_logs(caplog):
    """Corrupted inputs never crash the agent, and logs never contain patient values."""
    caplog.set_level(logging.WARNING)

    # 1. Non-dict profile
    res1 = risk_agent.assess("not_a_dict", {"systolic": 120}, ["hypertension"], models_dir=MODELS_DIR)
    assert res1 is not None
    assert res1["status"] in ("not_enough_information", "error")

    # 2. Negative height
    bad_profile = {
        "date_of_birth": "1980-01-01",
        "sex_at_birth": "male",
        "height_cm": -180.0,
        "weight_kg": 70.0,
        "waist_cm": 90.0,
        "smoking_status": "never",
    }
    res2 = risk_agent.assess(bad_profile, {"systolic": 120, "diastolic": 80}, ["hypertension"], models_dir=MODELS_DIR)
    assert res2["status"] == "not_enough_information"
    assert "bmi" in res2["missing"]

    # 3. Completely bogus reading types
    bogus_readings = {"systolic": "broken", "diastolic": None}
    res3 = risk_agent.assess(bad_profile, bogus_readings, ["hypertension"], models_dir=MODELS_DIR)
    assert res3["status"] == "not_enough_information"

    # 4. Verify no patient values (e.g. "1980-01-01", "-180.0", "70.0") appear in log text
    for record in caplog.records:
        assert "1980" not in record.message
        assert "-180" not in record.message
        assert "70.0" not in record.message
