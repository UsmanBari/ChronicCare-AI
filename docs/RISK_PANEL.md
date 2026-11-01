# Provider Diabetes Risk Panel (Experimental)

## Overview & Background
The **Diabetes Risk Panel** is an experimental clinical decision-support feature introduced in Iteration 2 (Decisions D12–D15, `docs/ML_PLAN.md`). It provides attending clinicians with an evidence-based assessment of 10-year type 2 diabetes risk for adult hypertensive patients who have not yet been diagnosed with diabetes.

The feature is displayed exclusively within the Provider Reconciliation & Review interface (`/api/provider/review/{checkin_id}`) behind the `RISK_ENABLED` feature flag.

---

## Configuration & Demo Switch

The feature is controlled at runtime via the environment variable:

```bash
# Enable provider risk panel for demos and clinical review
RISK_ENABLED=true

# Default production state (disabled)
RISK_ENABLED=false
```

When `RISK_ENABLED` is absent or set to any value other than `"true"`, the backend returns `risk: null` on all review detail endpoints. The frontend completely omits the risk card from the DOM.

---

## Why Disabled by Default in Production

1. **Geographic & Demographic Validation**: The underlying statistical model (`diabetes_full_nhanes`) was developed and calibrated using US National Health and Nutrition Examination Survey (NHANES) cohorts. It has not undergone formal clinical validation on a Pakistani demographic or local South Asian cohorts.
2. **Clinical Governance First**: In accordance with medical safety principles, unvalidated algorithmic predictions must not enter general production workflows until approved by institutional clinical governance and regulatory oversight.
3. **Card Audience Restriction**: The model is intended strictly as decision support for hypertensive screening reminders (ADA Table 2.5 / USPSTF 2021), not as an autonomous diagnostic instrument.

---

## Safety Constraints & Guardrails

### 1. Zero Patient Exposure (Strict Leak Defense)
- **Zero UI Visibility**: Patients never see a risk score, risk band, percentage, or advisory hint anywhere in the patient portal.
- **Endpoint Protection**: Patient-facing endpoints (`/api/me`, `/api/me/profile`, `/api/checkins/{id}`, `/api/me/trends`) are structurally prevented from evaluating or returning `risk` data. This invariant is continuously verified by `backend-poc-technical/test_risk_panel_api.py`.

### 2. Clinical Applicability Criteria
Risk assessment is only computed when **both** conditions are met:
- The patient has documented **hypertension**.
- The patient has **not** been diagnosed with **diabetes**.
If the patient already has diabetes, lacks hypertension, or has no profile, `risk` evaluates to `null`.

### 3. Qualitative Bands Over Raw Probabilities
Per Decision D12, the UI displays qualitative calibrated risk bands:
- **Low**: Emerald badge with `<ShieldCheck>` icon and translated text.
- **Moderate**: Amber badge with `<AlertTriangle>` icon and translated text.
- **High**: Rose badge with `<AlertOctagon>` icon and translated text.

**Accessible Design**: Badges always combine color, icons, and text — never color alone.
**No Raw Percentages**: Numerical percentages (e.g. `14.2%`) are strictly withheld from the provider UI because raw decimals invite false precision and over-interpretation.

### 4. Transparent Missing Data Handling
If any required input feature is missing (waist circumference, 30-day blood pressure reading, smoking status, or BMI), the system returns `status: "not_enough_information"`. The provider interface clearly displays what measurements are missing rather than imputing or guessing.

### 5. Mandatory Clinical Caveats
Every positive risk panel prominently renders mandatory caveats:
- *Home blood pressure readings are self-reported and have not been validated against clinic measurements.*
- *This model was developed on US NHANES data and has not been validated on a Pakistani population.*

### 6. Fail-Safe Error Handling
Any unhandled exception during risk evaluation is trapped cleanly and logged by exception type only (without logging Protected Health Information). The review detail endpoint succeeds with HTTP 200 and `risk: null`.
