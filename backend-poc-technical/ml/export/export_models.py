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

LABEL_TEXT = {
    "en": "Experimental: trained on US NHANES data, not validated for Pakistani patients",
    "ur": "تجرباتی: امریکی NHANES ڈیٹا پر تربیت یافتہ، پاکستانی مریضوں کے لیے غیر تصدیق شدہ",
    "roman_ur": "Tajurbati: US NHANES data par train kiya gaya, Pakistani mareezon ke liye tasdeeq shuda nahi",
    "needs_native_review": True,
}

FEATURE_UNITS = {
    "age": "years",
    "sex_male": "binary (1=male, 0=female)",
    "bmi": "kg/m2",
    "ever_smoked_100": "binary (1=yes, 0=no)",
    "told_high_bp": "binary (1=yes, 0=no)",
    "sbp": "mmHg",
    "dbp": "mmHg",
    "waist_cm": "cm",
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
    payload["audience"] = "provider_only"
    payload["label_text"] = LABEL_TEXT
    payload["feature_units"] = FEATURE_UNITS
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
    Generate n_rows of pure synthetic data (never real NHANES data) and record
    scikit-learn predict_proba output for hermetic floating point parity tests.
    """
    model_dir = MODELS_INPUT_DIR / config_name
    pipeline, card = load_model_artifact(model_dir)
    features = list(card["features"])

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
    print("Exporting diabetes_full_nhanes to production JSON...")
    target_json = export_model_to_production("diabetes_full_nhanes")
    print(f"Exported model: {target_json}")

    print("Generating 1,000 synthetic rows golden file...")
    golden_json = MODELS_OUTPUT_DIR / "diabetes_full_nhanes.golden.json"
    generate_golden_dataset("diabetes_full_nhanes", golden_json, n_rows=1000, seed=42)
    print(f"Generated golden file: {golden_json}")


if __name__ == "__main__":
    main()
