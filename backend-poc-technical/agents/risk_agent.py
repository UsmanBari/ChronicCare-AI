"""
Pure Standard Library Risk Agent for ChronicCare AI (Part C).
Evaluates diabetes risk advisory for hypertensive patients using exported model coefficients.

Adheres strictly to D12, D13, D14, and Week 2 Day 5 instructions:
- Pure Python standard library: NO numpy, scipy, or scikit-learn.
- Applicability: Hypertension AND NOT diabetes -> diabetes risk; otherwise None.
- Missing features -> {"status": "not_enough_information", "missing": [...]} (no basic fallback).
- Top 3 positive contributions in plain words (en, ur, roman_ur) from label map; never numbers the patient didn't give.
- Never raises on bad input: returns {"status": "error", "reason": "<code>"} and logs without values.
"""
from __future__ import annotations

from datetime import date, datetime
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default model directory
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# In-memory model cache
_LOADED_MODELS: Dict[str, Dict[str, Any]] = {}

REASON_LABELS = {
    "age": {
        "en": "your age",
        "ur": "آپ کی عمر",
        "roman_ur": "aap ki umar",
    },
    "waist_cm": {
        "en": "your waist size",
        "ur": "آپ کی کمر کا ناپ",
        "roman_ur": "aap ki kamar ka naap",
    },
    "bmi": {
        "en": "your BMI",
        "ur": "آپ کا بی ایم آئی",
        "roman_ur": "aap ka BMI",
    },
    "sbp": {
        "en": "your recent blood pressure",
        "ur": "آپ کا حالیہ بلڈ پریشر",
        "roman_ur": "aap ka haaliya blood pressure",
    },
    "dbp": {
        "en": "your recent blood pressure",
        "ur": "آپ کا حالیہ بلڈ پریشر",
        "roman_ur": "aap ka haaliya blood pressure",
    },
    "told_high_bp": {
        "en": "history of high blood pressure",
        "ur": "ہائی بلڈ پریشر کی تاریخ",
        "roman_ur": "high blood pressure ki tareekh",
    },
    "ever_smoked_100": {
        "en": "smoking history",
        "ur": "تمباکو نوشی کی تاریخ",
        "roman_ur": "smoking ki tareekh",
    },
    "sex_male": {
        "en": "biological sex",
        "ur": "پیدائشی جنس",
        "roman_ur": "paidaishi jins",
    },
}


def _sigmoid(z: float) -> float:
    """Stable sigmoid implementation in pure stdlib."""
    if z >= 40.0:
        return 1.0
    if z <= -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def load_models(models_dir: Path | str | None = None) -> Dict[str, Dict[str, Any]]:
    """Loads exported JSON model coefficients into memory once."""
    global _LOADED_MODELS
    target_dir = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    model_file = target_dir / "diabetes_full_nhanes.json"
    if model_file.is_file():
        try:
            _LOADED_MODELS["diabetes_full_nhanes"] = json.loads(model_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load model file %s: %s", model_file.name, type(e).__name__)
    return _LOADED_MODELS


def _parse_iso_date(date_str: Any) -> Optional[date]:
    """Parse date string into date object."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    clean = date_str.strip()
    # Handle YYYY-MM-DD or full ISO
    try:
        return datetime.fromisoformat(clean.replace("Z", "+00:00")).date()
    except Exception:
        pass
    try:
        return datetime.strptime(clean[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _calculate_age(dob: Optional[date], ref_date: date) -> Optional[float]:
    """Calculates age in years."""
    if not dob:
        return None
    age = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
    return float(age) if 0 <= age <= 130 else None


def _extract_blood_pressure(latest_readings: Any, ref_date: date) -> Tuple[Optional[float], Optional[float]]:
    """
    Extracts sbp and dbp from latest readings if within 30 days.
    Supports either a single dict {'systolic': x, 'diastolic': y, 'at': ...}
    or a history list of dicts.
    """
    if not latest_readings:
        return None, None

    readings_list: List[Dict[str, Any]] = []
    if isinstance(latest_readings, dict):
        if "systolic" in latest_readings or "diastolic" in latest_readings:
            readings_list = [latest_readings]
        elif "readings" in latest_readings and isinstance(latest_readings["readings"], list):
            readings_list = latest_readings["readings"]
    elif isinstance(latest_readings, list):
        readings_list = latest_readings

    # Find the most recent reading with systolic and diastolic
    best_sbp = None
    best_dbp = None
    best_dt = None

    for r in readings_list:
        if not isinstance(r, dict):
            continue
        s_val = r.get("systolic") or r.get("sbp")
        d_val = r.get("diastolic") or r.get("dbp")
        if s_val is None or d_val is None:
            continue

        try:
            s_float = float(s_val)
            d_float = float(d_val)
        except (ValueError, TypeError):
            continue

        # Check recency if date is present
        ts_raw = r.get("at") or r.get("created_at") or r.get("recorded_at") or r.get("timestamp")
        r_date = _parse_iso_date(ts_raw) if ts_raw else None

        if r_date is not None:
            age_days = (ref_date - r_date).days
            if age_days < 0 or age_days > 30:
                continue  # Stale reading (> 30 days) or future timestamp
            if best_dt is None or r_date > best_dt:
                best_dt = r_date
                best_sbp = s_float
                best_dbp = d_float
        else:
            # If no date tag provided in reading object, accept if no dated reading found
            if best_sbp is None:
                best_sbp = s_float
                best_dbp = d_float

    return best_sbp, best_dbp


def assess(
    profile: Optional[Dict[str, Any]],
    latest_readings: Optional[Any],
    conditions: Optional[List[Any]],
    now: Optional[str] = None,
    models_dir: Path | str | None = None,
) -> Optional[Dict[str, Any]]:
    """
    Assess diabetes risk for a hypertensive patient without diagnosed diabetes.

    Parameters
    ----------
    profile : dict
        Patient profile with demographic and physical measurements.
    latest_readings : dict or list
        Recent vital readings (must have BP reading within past 30 days).
    conditions : list
        List of tracked patient conditions.
    now : str, optional
        Reference evaluation timestamp (ISO format). Defaults to current UTC date.
    models_dir : Path or str, optional
        Directory where exported model JSON files reside.

    Returns
    -------
    dict or None
        Risk assessment dictionary, or None if not applicable.
    """
    try:
        # Reference date
        ref_date = _parse_iso_date(now) if now else date.today()
        if not ref_date:
            ref_date = date.today()

        # 1. Applicability Check (D12, D13)
        # Hypertension AND NOT diabetes -> diabetes risk; diabetes only, both, or neither -> None
        if conditions is None:
            return None
        cond_set = {str(c).strip().lower() for c in conditions}
        has_htn = any("hyper" in c for c in cond_set)
        has_t2d = any("diabet" in c for c in cond_set)

        if not has_htn or has_t2d:
            return None

        # 2. Model retrieval
        models = load_models(models_dir)
        model = models.get("diabetes_full_nhanes")
        if not model:
            logger.warning("Risk assessment model 'diabetes_full_nhanes' not found in models directory")
            return {"status": "error", "reason": "model_not_found"}

        if not isinstance(profile, dict):
            profile = {}

        # 3. Feature Extraction
        missing: List[str] = []
        raw_features: Dict[str, float] = {}

        # Feature: age
        dob_val = _parse_iso_date(profile.get("date_of_birth"))
        age_val = _calculate_age(dob_val, ref_date)
        if age_val is not None and age_val >= 18.0:
            raw_features["age"] = age_val
        else:
            missing.append("age")

        # Feature: sex_male
        sex_raw = str(profile.get("sex_at_birth", "")).strip().lower()
        if sex_raw == "male":
            raw_features["sex_male"] = 1.0
        elif sex_raw == "female":
            raw_features["sex_male"] = 0.0
        else:
            missing.append("sex_male")

        # Feature: bmi (from height_cm and weight_kg)
        h_cm = profile.get("height_cm")
        w_kg = profile.get("weight_kg")
        if h_cm is not None and w_kg is not None:
            try:
                h_f = float(h_cm)
                w_f = float(w_kg)
                if h_f > 0 and w_f > 0:
                    raw_features["bmi"] = w_f / ((h_f / 100.0) ** 2)
                else:
                    missing.append("bmi")
            except (ValueError, TypeError):
                missing.append("bmi")
        else:
            missing.append("bmi")

        # Feature: ever_smoked_100
        # Mapped from smoking_status: 'never' -> 0, 'former' -> 1, 'current' -> 1
        smoke_raw = str(profile.get("smoking_status", "")).strip().lower()
        if smoke_raw in ("current", "former"):
            raw_features["ever_smoked_100"] = 1.0
        elif smoke_raw == "never":
            raw_features["ever_smoked_100"] = 0.0
        else:
            missing.append("smoking_status")

        # Feature: told_high_bp (1.0 by applicability check)
        raw_features["told_high_bp"] = 1.0

        # Features: sbp, dbp (from most recent reading within 30 days)
        sbp_val, dbp_val = _extract_blood_pressure(latest_readings, ref_date)
        if sbp_val is not None:
            raw_features["sbp"] = sbp_val
        else:
            missing.append("sbp")
        if dbp_val is not None:
            raw_features["dbp"] = dbp_val
        else:
            missing.append("dbp")

        # Feature: waist_cm (Part H)
        waist_val = profile.get("waist_cm")
        if waist_val is not None:
            try:
                w_cm = float(waist_val)
                if w_cm > 0:
                    raw_features["waist_cm"] = w_cm
                else:
                    missing.append("waist_cm")
            except (ValueError, TypeError):
                missing.append("waist_cm")
        else:
            missing.append("waist_cm")

        # 4. Check Missing Features (No Basic Fallback per D8/D12)
        if missing:
            return {
                "status": "not_enough_information",
                "missing": sorted(list(set(missing))),
                "audience": "provider_only",
            }

        # 5. Model Inference (StandardScaler + Logistic Regression Sigmoid)
        feature_order: List[str] = model["feature_order"]
        scaler_mean: List[float] = model["scaler_mean"]
        scaler_scale: List[float] = model["scaler_scale"]
        coef: List[float] = model["coef"]
        intercept: float = float(model["intercept"])

        linear_predictor = intercept
        contributions: List[Tuple[str, float]] = []

        for i, feat in enumerate(feature_order):
            x_i = raw_features[feat]
            mean_i = scaler_mean[i]
            scale_i = scaler_scale[i]
            coef_i = coef[i]

            z_i = (x_i - mean_i) / scale_i
            contrib_i = coef_i * z_i
            linear_predictor += contrib_i

            # Only positive contributions are candidate reasons for risk
            if contrib_i > 0:
                contributions.append((feat, contrib_i))

        probability = _sigmoid(linear_predictor)

        # 6. Risk Band Determination (D8)
        bands = model["bands"]
        low_max = float(bands["low_max"])
        high_min = float(bands["high_min"])

        if probability < low_max:
            band = "low"
        elif probability >= high_min:
            band = "high"
        else:
            band = "moderate"

        # 7. Top 3 Positive Contributors
        contributions.sort(key=lambda item: item[1], reverse=True)
        top_3 = contributions[:3]

        reasons = [
            {
                "feature": feat,
                "contribution": round(contrib, 4),
                "label": REASON_LABELS.get(feat, {"en": feat, "ur": feat, "roman_ur": feat}),
            }
            for feat, contrib in top_3
        ]

        return {
            "status": "ok",
            "disease": "diabetes",
            "model_name": model.get("model_name", "diabetes_full_nhanes"),
            "model_version": model.get("model_version", "1.0.0"),
            "probability": probability,
            "band": band,
            "reasons": reasons,
            "advisory": True,
            "audience": "provider_only",
            "label_text": model.get("label_text", {}),
            "caveats": ["home_bp_not_exam_bp", "not_validated_pakistan"],
        }

    except Exception as e:
        logger.warning("Risk assessment execution failed: %s", type(e).__name__)
        return {"status": "error", "reason": type(e).__name__}
