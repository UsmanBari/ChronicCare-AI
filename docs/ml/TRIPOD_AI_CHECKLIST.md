# TRIPOD+AI Item Mapping Guide — ChronicCare AI Risk Models

> **Document Purpose:** Structural map of TRIPOD+AI reporting items against ChronicCare AI documentation and code artifacts.  
> **Status:** Transparent documentation map (not a claim of official TRIPOD regulatory certification or compliance).  
> **Evaluation Date:** 29 October 2026  
> **Author:** Usman (ML Lead)

---

| Item # | TRIPOD+AI Checklist Item | Addressed in Project? | File & Section / Implementation Reference | Notes / Scope |
|---|---|---|---|---|
| **1** | **Title / Abstract:** Identification as developing/validating a clinical AI model | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L1-L8) | Summary title and clinical governance status |
| **2** | **Source of Data:** Data source description and collection period | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L30-L55) | CDC NHANES 1999–2023 (10 cycles); external validation on BRFSS scheduled for Day 6 |
| **3** | **Participants:** Eligibility criteria, inclusion/exclusion, cohort derivation | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L110-L165) & [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L10-L22) | Adults $\ge 18$, condition-free baseline for training, reciprocal display card population |
| **4** | **Outcome:** Definition of outcome, blind assessment, timing | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L75-L105) (D2 T2D & HTN) | Laboratory-confirmed undiagnosed diabetes (HbA1c $\ge 6.5\%$ or fasting glucose $\ge 126$); measured BP $\ge 130/80$ mmHg |
| **5** | **Predictors:** Definition of all candidate predictor variables | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L170-L195) (D4) & [docs/ML_INTERFACES.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_INTERFACES.md) | BASIC (demographics/history) and FULL (BASIC + vitals/labs + waist circumference) |
| **6** | **Sample Size:** Total observations, event counts, split sizes | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L190-L205) (D5 table) & [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L14-L21) | Temporal splits: train_core (1999–2012), validation (2013–2016), test (2017–2023) |
| **7** | **Missing Data:** Handling of missing values, drop counts | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L190-L208) (D5) & `docs/ml/experiments/*.md` Section 1 | Complete-case policy; exact dropped/retained counts audited across splits; no inference imputation |
| **8** | **Analysis & Modeling:** Model types, hyperparameter search, feature scaling | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L210-L225) (D6), [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L265-L275) (D10), `backend-poc-technical/ml/experiments/run.py` | Scikit-learn (LR, LR balanced, RF, HGB); StandardScaler fit on train_core only; D10 parsimony rule |
| **9** | **Threshold Selection:** Decision threshold selection and rationale | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L225-L235) (D7) & `docs/ml/experiments/*.md` Section 3 | Locked on temporal validation set at sensitivity $\ge 0.80$; never altered on test |
| **10** | **Risk Stratification:** Risk groups/bands definition | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L235-L250) (D8) | LOW (< locked threshold), MODERATE (threshold to 90th percentile), HIGH (top 10% validation) |
| **11** | **Performance (Discrimination):** AUROC, AUPRC with confidence intervals | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L14-L21) & `docs/ml/experiments/*.md` Section 4 | Bootstrap 95% CIs reported for test AUROC and AUPRC |
| **12** | **Performance (Calibration):** Calibration slope, intercept, Brier score | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L14-L21) & `docs/ml/experiments/*.md` Section 4 | Calibration slope and intercept reported; secondary recalibration avoided (D10) |
| **13** | **Clinical Utility:** Net benefit, decision curve analysis | YES | [docs/ml/DECISION_CURVE.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/DECISION_CURVE.md) | Net benefit evaluated across $p_t \in [0.01, 0.20]$ vs screen all/none and guideline rules |
| **14** | **Subgroup & Fairness:** Disaggregated performance across demographic strata | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L45-L55) & `docs/ml/experiments/*.md` Section 5 | Sex, age band (18–39, 40–59, 60+), race/ethnicity, card audience; Gate 4 enforces sens $\ge 0.60$ for $n_{\text{pos}} \ge 50$ |
| **15** | **Transportability & Demographics:** Population transferability and geographic limits | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L60-L75) | Documented US NHANES origin; Asian lower BMI action points noted; NOT validated for Pakistani patients |
| **16** | **Model Deployment & Integration:** Runtime export format, interface guardrails | YES | [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L250-L260) (D9), [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L300-L315) (D12–D15), [docs/ML_INTERFACES.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_INTERFACES.md) | Pure-Python scorer parity tested; `RISK_ENABLED=off` production guard; shown only on provider review page |
| **17** | **Limitations:** Dataset and operational limits | YES | [docs/ml/EXPERIMENTS_SUMMARY.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/EXPERIMENTS_SUMMARY.md#L60-L85) & [docs/ML_PLAN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ML_PLAN.md#L300-L325) | BRFSS lack of laboratory data; age bias in logistic regression coefficients |
| **18** | **Open Science / Reproducibility:** Code, configs, seeds, data download scripts | YES | `backend-poc-technical/ml/experiments/run.py`, `backend-poc-technical/ml/experiments/configs/*.json`, `scripts/get_nhanes.py` | Hermetic test harness (`test_harness.py`), declarative JSON configs, deterministic seeds |
| **19** | **Prospective Clinical Trial Evaluation:** Real-world randomized impact trial | **NOT DONE** | N/A | Prototype FYP-1 phase; clinical efficacy trial not conducted prior to deployment |

---

## 2. TRIPOD+AI Item Coverage for `chd10_framingham` (Framingham Heart Study)

| TRIPOD+AI Item | Coverage in `chd10_framingham` | Document / Code Reference |
| :--- | :--- | :--- |
| **Pre-Registration** | Fully pre-registered protocol before test evaluation | [`docs/ml/CHD10_PREREGISTRATION.md`](file:///c:/Users/Saad/Documents/ChronicCare-AI/docs/ml/CHD10_PREREGISTRATION.md) |
| **Source of Data** | Framingham Heart Study (FHS, NHLBI) cohort | [`docs/DATASETS.md`](file:///c:/Users/Saad/Documents/ChronicCare-AI/docs/DATASETS.md#L125-L160) |
| **Participants & Eligibility** | Adults aged 30–74 with hypertension or diabetes | `backend-poc-technical/ml/datasets/framingham.py` |
| **Outcome** | Ten-year coronary heart disease (`TenYearCHD`) | `backend-poc-technical/ml/labels.py` |
| **Predictors** | 9 non-lab features (`age`, `sex_male`, `current_smoker`, `bmi`, `sbp`, `dbp`, `bp_meds`, `diabetes`, `prevalent_hyp`) | `backend-poc-technical/ml/experiments/configs/chd10_framingham.json` |
| **Sample Size & Splits** | Complete-case $N=4,166$ (train 2,499 / val 833 / test 834) | `docs/ml/experiments/chd10_framingham.md` Section 1 |
| **Missing Data** | Complete cases (74 dropped due to missing feature or label) | `docs/ml/experiments/chd10_framingham.md` Section 1 |
| **Model Development** | LR, LR balanced, RF, HGB evaluated; 5-fold CV on train | `docs/ml/experiments/chd10_framingham.md` Section 2 |
| **Thresholds & Bands** | Pre-registered NCEP ATP III bands: <10% (Low), 10–20% (Mod), $\ge 20\%$ (High) | `docs/ml/CHD10_PREREGISTRATION.md` |
| **Discrimination & Calibration** | Test AUROC: 0.7241 [95% CI: 0.6732–0.7659]; Calibration Slope: 1.142 | `docs/ml/experiments/chd10_framingham.md` Section 3 & 4 |
| **Clinical Utility / DCA** | Net benefit evaluated across thresholds $p_t \in [0.05, 0.30]$ | `docs/ml/experiments/chd10_framingham.md` Section 5 |
| **Explainability (SHAP)** | Global mean \|SHAP\| and local explanations for 3 synthetic patients | `docs/ml/experiments/chd10_framingham.md` Section 5 |
| **Transportability Limitations** | US Framingham 1948 cohort; ethnic gap for South Asian/Pakistani adults | [`docs/LIMITATIONS.md`](file:///c:/Users/Saad/Documents/ChronicCare-AI/docs/LIMITATIONS.md) |
| **Implementation Guardrails** | Pure-Python scorer parity tested to $10^{-9}$; patient note disclaimer | `backend-poc-technical/ml/tests/test_chd10_model.py` |

