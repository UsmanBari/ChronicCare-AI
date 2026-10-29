**Status:** Approved by Usman 28 Oct 2026 with changes.

# Machine Learning Model Artifact Contract & Interfaces Specification

This document defines the strict contract for serialized machine learning models, model metadata cards (`model_card.json`), production lightweight exports (`export.json`), evaluation interfaces, and external validation protocols across the ChronicCare-AI ecosystem.

---

## 1. Model Artifact Folder Layout

Every trained clinical risk model artifact must be saved as a self-contained directory within `backend-poc-technical/ml/outputs/models/<model_name>/` (which is strictly git-ignored):

```text
backend-poc-technical/ml/outputs/models/<model_name>/
├── model.joblib          # Full fitted scikit-learn Pipeline (preprocessing + estimator)
├── model_card.json       # Validated schema metadata card describing provenance, target, and metrics
└── export.json           # Lightweight pure-Python scoring specification for production runtime
```

### Key Principles:
1. **Raw Feature Ingestion:** `model.joblib` is a scikit-learn `Pipeline` (e.g. `StandardScaler` + `LogisticRegression`) that operates on raw DataFrame / 2D array features matching the card's `features` order.
2. **Deterministic Versioning:** The model card links directly to the git commit hash at training time (`git rev-parse HEAD`), the installed `sklearn_version`, the dataset split version (`nhanes_temporal_v1`), and the author.
3. **Decoupled Deployment:** Downstream inference engines and external validation suites load artifacts using `load_model_artifact(dir_path)` without needing access to original training scripts or raw survey datasets.

---

## 2. Model Card (`model_card.json`) Schema Specification

The model card is validated by `ml.artifacts.validate_model_card(card)`. All 20 keys are strictly required:

| Key | Type | Description | Example |
|---|---|---|---|
| `name` | `string` | Unique identifier of the model artifact | `"baseline_temporal_lr"` |
| `owner` | `string` | Author / engineer who trained and saved the model | `"saad"` (or `"usman"`) |
| `created_at` | `string` | ISO 8601 UTC timestamp of creation | `"2026-10-28T14:30:00Z"` |
| `git_commit` | `string` | 40-character SHA from `git rev-parse HEAD` | `"<40-char SHA from git rev-parse HEAD>"` |
| `label` | `string` | Target label registered in `ml.labels.LABELS` | `"diabetes_undiagnosed"` |
| `population` | `string` | Target population definition / cohort inclusion filter | `"told_diabetes == 0"` |
| `tier` | `string` | Feature tier level (`basic` | `full`) | `"basic"` |
| `features` | `list[string]` | Ordered list of candidate input features | `["age", "sex_male", "bmi", "ever_smoked_100", "told_high_bp"]` |
| `threshold` | `float` | Operational decision threshold in range `[0.0, 1.0]` | `0.082` |
| `threshold_policy` | `dict` | Policy dict used to select the threshold on validation | `{"type": "min_sensitivity", "value": 0.80}` |
| `bands` | `dict` | Risk band thresholds for clinical triage stratification | `{"low_max": 0.082, "high_min": 0.250}` |
| `split` | `string` | Dataset partition version name | `"nhanes_temporal_v1"` |
| `model_type` | `string` | Human-readable model architecture descriptor | `"LogisticRegression (balanced)"` |
| `hyperparameters` | `dict` | Key-value mapping of tuned model hyperparameters | `{"max_iter": 1000, "class_weight": "balanced", "random_state": 42}` |
| `sklearn_version` | `string` | Installed `scikit-learn` version at training time | `"1.9.1"` |
| `train_rows` | `integer` | Count of clean training samples fitted | `33783` |
| `val_rows` | `integer` | Count of clean validation samples evaluated | `9722` |
| `val_auroc` | `float` | Validation AUROC performance | `0.7712` |
| `test_metrics` | `dict` | Held-out test set performance summary dict | `{"auroc": 0.7685, "brier": 0.1852, "sensitivity": 0.805, ...}` |
| `notes` | `string` | Clinical context, limitations, or architecture remarks | `"Stage 1 basic tier screening model on temporal split."` |

### Concrete `model_card.json` Example:

```json
{
  "name": "stage1_screening_lr",
  "owner": "saad",
  "created_at": "2026-10-28T14:30:00Z",
  "git_commit": "<40-char SHA from git rev-parse HEAD>",
  "label": "diabetes_undiagnosed",
  "population": "told_diabetes == 0",
  "tier": "basic",
  "features": [
    "age",
    "sex_male",
    "bmi",
    "ever_smoked_100",
    "told_high_bp"
  ],
  "threshold": 0.082,
  "threshold_policy": {
    "type": "min_sensitivity",
    "value": 0.80
  },
  "bands": {
    "low_max": 0.082,
    "high_min": 0.250
  },
  "split": "nhanes_temporal_v1",
  "model_type": "LogisticRegression (balanced)",
  "hyperparameters": {
    "C": 1.0,
    "class_weight": "balanced",
    "max_iter": 1000,
    "random_state": 42
  },
  "sklearn_version": "1.9.1",
  "train_rows": 33783,
  "val_rows": 9722,
  "val_auroc": 0.7712,
  "test_metrics": {
    "auroc": 0.7685,
    "brier": 0.1852,
    "sensitivity": 0.805,
    "specificity": 0.612,
    "ppv": 0.124
  },
  "notes": "Stage 1 basic tier screening model on temporal split with undiagnosed diabetes target."
}
```

---

## 3. Training & Evaluation Pipeline Workflow (Usman's Harness Integration)

Usman's experiment harness (`backend-poc-technical/ml/experiments/`) executes the following sequential steps using the Day 3 toolkit:

```text
 1. Check Target Leakage
    └── ml.evaluation.check_leakage(label_name, feature_list)
        (Raises LeakageError if features leak the target label; halts before data is loaded)

 2. Partition Temporal Dataset
    └── ml.common.load_split("nhanes_temporal_v1")
        (Splits into train_core 1999-2012, validation 2013-2016, test 2017-2023)

 3. Model Training & Pipeline Fitting
    └── pipeline.fit(X_train, y_train)
        (Fitted exclusively on train_core)

 4. Validation Threshold Selection
    └── ml.evaluation.choose_threshold(y_val, p_val, policy)
        (CRITICAL: Run strictly on validation predictions; test data is NEVER passed here)

 5. Held-Out Test Evaluation
    ├── ml.evaluation.auroc(y_test, p_test)
    ├── ml.evaluation.auprc(y_test, p_test)
    ├── ml.evaluation.bootstrap_ci(y_test, p_test, metric_fn)
    ├── ml.evaluation.metrics_at_threshold(y_test, p_test, chosen_threshold)
    ├── ml.evaluation.calibration(y_test, p_test, n_bins=10)
    └── ml.evaluation.subgroup_report(df_test, y_col, p_col, chosen_threshold)

 6. Save Validated Model Artifact & Export
    ├── ml.artifacts.save_model_artifact(pipeline, model_card, out_dir)
    └── ml.artifacts.export_production_lr(pipeline, model_card, out_dir / "export.json")
        (Writes model.joblib, model_card.json, and production-ready export.json)

 7. Generate Standardized Report
    └── ml.evaluation.write_eval_report(report_path, sections_dict)
```

---

## 4. External Validation Protocol (Day 6 Interface)

On Day 6, the external validation suite independently assesses generalization on non-NHANES datasets (BRFSS, Kaggle cohorts, Framingham, Cardio70k, DHS):

1. **Artifact Ingestion:**
   ```python
   from ml.artifacts import load_model_artifact

   pipeline, card = load_model_artifact("backend-poc-technical/ml/outputs/models/baseline_temporal_lr")
   ```
2. **Strict Feature Alignment (Zero Silent Dropping):**
   - External validation reads `card["features"]` to determine exact expected input columns and ordering.
   - Maps external dataset columns to match feature definitions in `docs/ML_FEATURE_MAP.md`.
   - **MANDATORY POLICY:** Every external validation dataset must explicitly map all `card["features"]` or report `"NOT EVALUABLE: missing <feature>"`. Silent dropping, subset evaluation without missing features, or zero-imputing unavailable columns is strictly prohibited.
3. **Threshold Application:**
   - Evaluates predictions using the pre-calibrated `card["threshold"]` without re-tuning or peeking at external labels.
4. **Generalization Metrics:**
   - Runs `ml.evaluation.metrics_at_threshold` and `ml.evaluation.calibration` on external cohorts to detect distribution shift, calibration drift, and demographic equity variance.

---

## 5. Production Export Contract (Backend Runtime Scoring)

The production web service / FastAPI backend **does not load `model.joblib`**. 

### Rationale:
1. **Security:** Loading pickled objects via `joblib.load()` exposes the application to arbitrary code execution vulnerabilities.
2. **Dependency Decoupling:** The production backend does not need `scikit-learn`, `scipy`, or compiler toolchains installed at runtime.
3. **Performance & Memory:** Eliminates heavy framework overhead; cold-start initialization is instantaneous and memory footprint is minimal.

### Specification (`export.json`):
For linear and logistic regression models, `ml.artifacts.export_production_lr` exports the fitted weights and scaling factors into a minimal JSON manifest:

```json
{
  "model_name": "stage1_screening_lr",
  "label": "diabetes_undiagnosed",
  "tier": "basic",
  "population": "told_diabetes == 0",
  "feature_order": [
    "age",
    "sex_male",
    "bmi",
    "ever_smoked_100",
    "told_high_bp"
  ],
  "scaler_mean": [49.2, 0.48, 28.5, 0.42, 0.35],
  "scaler_scale": [17.5, 0.50, 6.8, 0.49, 0.48],
  "coef": [0.65, 0.12, 0.54, 0.18, 0.41],
  "intercept": -1.85,
  "threshold": 0.082,
  "bands": {
    "low_max": 0.082,
    "high_min": 0.250
  }
}
```

### Pure-Python Scorer Implementation:
In production, individual records are scored in pure Python without third-party mathematical libraries:

```python
import math

def score_record(features_dict: dict, export_spec: dict) -> dict:
    z = export_spec["intercept"]
    for i, name in enumerate(export_spec["feature_order"]):
        raw_val = float(features_dict[name])
        # Standardize if scaler parameters exist
        if export_spec["scaler_mean"] and export_spec["scaler_scale"]:
            val = (raw_val - export_spec["scaler_mean"][i]) / export_spec["scaler_scale"][i]
        else:
            val = raw_val
        z += export_spec["coef"][i] * val

    # Sigmoid function
    prob = 1.0 / (1.0 + math.exp(-z))
    flagged = prob >= export_spec["threshold"]
    
    # Stratification band
    bands = export_spec.get("bands", {})
    if prob < bands.get("low_max", export_spec["threshold"]):
        risk_band = "low"
    elif prob >= bands.get("high_min", 1.0):
        risk_band = "high"
    else:
        risk_band = "moderate"

    return {"probability": prob, "flagged": flagged, "risk_band": risk_band}
```

- **Execution speed:** < 5 microseconds per record.
- **Verification Guarantee:** Unit test `ml/tests/test_artifacts.py::test_pure_python_scorer_matches_pipeline_within_1e9` validates that the pure-Python calculation matches `pipeline.predict_proba()[:, 1]` to within $10^{-9}$ on 1,000 synthetic validation rows.

---

## 6. Plotting Utilities & CI Notice

The plotting module `ml.plots` (`roc_plot`, `calibration_plot`) provides visualization functions for offline exploratory analysis by developers.

- **Non-CI Tool:** `ml.plots` is an optional developer utility and is **NOT run in automated CI test suites**.
- **Dependency Scope:** `matplotlib` is an optional developer visualizer and is not pinned as a hard dependency in continuous integration environments.
