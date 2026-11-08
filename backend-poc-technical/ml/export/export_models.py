"""
Export production model coefficients and generate hermetic golden file.
Reuses ml.artifacts.export_production_lr and enforces SHIP CANDIDATE gate.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ml.artifacts import export_production_lr, load_model_artifact

REPORTS_DIR = BACKEND_DIR / "ml" / "outputs" / "reports"
MODELS_INPUT_DIR = BACKEND_DIR / "ml" / "outputs" / "models"
MODELS_OUTPUT_DIR = BACKEND_DIR / "models"

LABEL_TEXT_DIABETES = {
    "en": "Experimental: trained on US NHANES data, not validated for Pakistani patients",
    "ur": "تجرباتی: امریکی NHANES ڈیٹا پر تربیت یافتہ، پاکستانی مریضوں کے لیے غیر تصدیق شدہ",
    "roman_ur": "Tajurbati: US NHANES data par train kiya gaya, Pakistani mareezon ke liye tasdeeq shuda nahi",
    "needs_native_review": True,
}

LABEL_TEXT_CHD10 = {
    "en": "Experimental: trained on US Framingham data, not validated for Pakistani patients",
    "ur": "تجرباتی: امریکی Framingham ڈیٹا پر تربیت یافتہ، پاکستانی مریضوں کے لیے غیر تصدیق شدہ",
    "roman_ur": "Tajurbati: US Framingham data par train kiya gaya, Pakistani mareezon ke liye tasdeeq shuda nahi",
    "needs_native_review": True,
}

PATIENT_NOTE_CHD10 = {
    "en": "This is an estimate from a research model, not a diagnosis.",
    "ur": "یہ ایک تحقیقی ماڈل سے لگایا گیا تخمینہ ہے، کوئی تشخیص نہیں۔",
    "roman_ur": "Yeh ek tehqeeqi model se lagaya gaya takhmeena hai, koi tashkhees nahi.",
    "needs_native_review": True,
}

FEATURE_UNITS_DIABETES = {
    "age": "years",
    "sex_male": "binary (1=male, 0=female)",
    "bmi": "kg/m2",
    "ever_smoked_100": "binary (1=yes, 0=no)",
    "told_high_bp": "binary (1=yes, 0=no)",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "waist_cm": "cm",
}

FEATURE_UNITS_CHD10 = {
    "age": "years",
    "sex_male": "binary (1=male, 0=female)",
    "current_smoker": "binary (1=yes, 0=no)",
    "bmi": "kg/m2",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "bp_meds": "binary (1=yes, 0=no)",
    "diabetes": "binary (1=yes, 0=no)",
    "prevalent_hyp": "binary (1=yes, 0=no)",
}


def export_model_to_production(config_name: str, out_dir: Path | str = MODELS_OUTPUT_DIR) -> Path:
    """
    Exports a trained model to production JSON.
    Refuses to export if the model's metrics.json status is not 'SHIP CANDIDATE'.
    """
    metrics_path = REPORTS_DIR / config_name / "metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"Missing metrics.json for {config_name} at {metrics_path}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    ship_status = metrics.get("ship_status", "")
    if not str(ship_status).startswith("SHIP CANDIDATE"):
        raise ValueError(
            f"Refusing to export {config_name}: ship_status is '{ship_status}', which is not a SHIP CANDIDATE."
        )

    model_dir = MODELS_INPUT_DIR / config_name
    pipeline, card = load_model_artifact(model_dir)

    payload = export_production_lr(pipeline, card)
    payload["model_version"] = "1.0.0"

    if config_name == "chd10_framingham":
        payload["audience"] = "provider_and_patient_band"
        payload["label_text"] = LABEL_TEXT_CHD10
        payload["patient_note"] = PATIENT_NOTE_CHD10
        payload["feature_units"] = FEATURE_UNITS_CHD10
        payload["population"] = "hypertension_or_diabetes"
        payload["threshold"] = 0.10
        payload["bands"] = {"low_max": 0.10, "high_min": 0.20}
    else:
        payload["audience"] = "provider_only"
        payload["label_text"] = LABEL_TEXT_DIABETES
        payload["feature_units"] = FEATURE_UNITS_DIABETES

    payload["training_commit"] = card.get("git_commit", "")
    payload["sklearn_version"] = card.get("sklearn_version", "")
    payload["created_at"] = card.get("created_at", "")

    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    target_file = out_p / f"{config_name}.json"
    target_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target_file


def generate_golden_dataset(
    config_name: str,
    out_file: Path | str,
    n_rows: int = 1000,
    seed: int = 42,
) -> Path:
    """
    Generate synthetic data and record scikit-learn predict_proba output for hermetic floating point parity tests.
    For chd10_framingham: generates 10 fake inputs spanning low, moderate, and high bands with expected bands.
    """
    model_dir = MODELS_INPUT_DIR / config_name
    pipeline, card = load_model_artifact(model_dir)
    features = list(card["features"])

    if config_name == "chd10_framingham":
        fake_inputs = [
            # Low Risk (< 10%)
            {"age": 36, "sex_male": 0, "current_smoker": 0, "bmi": 21.0, "sbp": 110.0, "dbp": 70.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
            {"age": 42, "sex_male": 0, "current_smoker": 0, "bmi": 23.5, "sbp": 118.0, "dbp": 76.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
            {"age": 48, "sex_male": 0, "current_smoker": 0, "bmi": 24.0, "sbp": 122.0, "dbp": 78.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
            {"age": 38, "sex_male": 1, "current_smoker": 0, "bmi": 25.0, "sbp": 120.0, "dbp": 80.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
            # Moderate Risk (10% to < 20%)
            {"age": 52, "sex_male": 1, "current_smoker": 0, "bmi": 26.5, "sbp": 135.0, "dbp": 85.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 1},
            {"age": 56, "sex_male": 0, "current_smoker": 1, "bmi": 28.0, "sbp": 140.0, "dbp": 88.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 1},
            {"age": 50, "sex_male": 1, "current_smoker": 1, "bmi": 27.0, "sbp": 138.0, "dbp": 86.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
            # High Risk (>= 20%)
            {"age": 65, "sex_male": 1, "current_smoker": 1, "bmi": 29.5, "sbp": 160.0, "dbp": 95.0, "bp_meds": 1, "diabetes": 0, "prevalent_hyp": 1},
            {"age": 68, "sex_male": 1, "current_smoker": 1, "bmi": 32.0, "sbp": 170.0, "dbp": 100.0, "bp_meds": 1, "diabetes": 1, "prevalent_hyp": 1},
            {"age": 70, "sex_male": 0, "current_smoker": 1, "bmi": 34.0, "sbp": 175.0, "dbp": 102.0, "bp_meds": 1, "diabetes": 1, "prevalent_hyp": 1},
        ]
        df_synth = pd.DataFrame(fake_inputs)[features]
        probs = pipeline.predict_proba(df_synth)[:, 1]

        golden_records = []
        for i in range(len(fake_inputs)):
            prob_val = float(probs[i])
            band_str = "low" if prob_val < 0.10 else "moderate" if prob_val < 0.20 else "high"
            golden_records.append({
                "inputs": fake_inputs[i],
                "expected_prob": prob_val,
                "expected_band": band_str,
            })
    else:
        rng = np.random.RandomState(seed)
        rows = []
        data_dict: dict[str, list[Any]] = {f: [] for f in features}

        for _ in range(n_rows):
            sample = {
                "age": int(rng.randint(18, 86)),
                "sex_male": int(rng.choice([0, 1])),
                "bmi": round(float(rng.uniform(15.0, 55.0)), 2),
                "ever_smoked_100": int(rng.choice([0, 1])),
                "told_high_bp": 1,  # card population is hypertensive
                "sbp": round(float(rng.uniform(85.0, 210.0)), 1),
                "dbp": round(float(rng.uniform(45.0, 125.0)), 1),
                "waist_cm": round(float(rng.uniform(50.0, 160.0)), 1),
            }
            for f in features:
                data_dict[f].append(sample[f])
            rows.append(sample)

        df_synth = pd.DataFrame(data_dict)[features]
        probs = pipeline.predict_proba(df_synth)[:, 1]

        golden_records = []
        for i in range(n_rows):
            golden_records.append({
                "inputs": rows[i],
                "sklearn_prob": float(probs[i]),
            })

    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(golden_records, indent=2), encoding="utf-8")
    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Export trained model to production")
    parser.add_argument("--config", default="diabetes_full_nhanes", help="Model name to export")
    args = parser.parse_args()

    cfg_name = args.config
    print(f"Exporting {cfg_name} to production JSON...")
    target_json = export_model_to_production(cfg_name)
    print(f"Exported model: {target_json}")

    n_rows = 10 if cfg_name == "chd10_framingham" else 1000
    print(f"Generating {n_rows} synthetic rows golden file...")
    golden_json = MODELS_OUTPUT_DIR / f"{cfg_name}.golden.json"
    generate_golden_dataset(cfg_name, golden_json, n_rows=n_rows, seed=42)
    print(f"Generated golden file: {golden_json}")



if __name__ == "__main__":
    main()
