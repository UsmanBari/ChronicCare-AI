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

### 1. Patient Exposure & Policy Evolution (Change D12, Dated 8 Nov 2026)
- **Historical Policy (Iteration 2 D12)**: Zero patient visibility; provider panel only.
- **Clinician Guidance (Update 8 Nov 2026)**: A clinician approved patient-facing visibility of risk bands ("Patients should see their risk band too: YES").
- **Current Architecture (`RISK_PATIENT_VISIBLE`)**:
  - Controlled by runtime flag `RISK_PATIENT_VISIBLE` (default `false` in production code).
  - When enabled, patients see only their qualitative **band** (`Low` / `Moderate` / `High`) along with a plain-language sentence and recommended action.
  - **Strict Privacy & Anti-Alarmism Invariant**: Patients **never** see raw probabilities, decimal percentages, statistical model identifiers (`chd10_framingham`, `diabetes_full_nhanes`), logits, or mathematical SHAP driver contributions.
  - Providers continue to have full access to model name, drivers, confidence, and research banners.

---

## Stage-2 Final Triage & Escalation Agent

Proposal Sections 13.1 (Agent 10), 15, and 17 establish Stage-2 Final Triage.
Motto: *"The model proposes, the rules decide."*

### Stage-2 Escalation Rules Table

| Rule ID | Condition | Effect | Flag / Guard |
|---------|-----------|--------|--------------|
| **R-S2-0** | Level is already `emergency`, `urgent`, or `review` | Level unchanged | Invariant: Stage-2 **never lowers** any level and never touches emergency |
| **R-S2-1** | Clinical rules level is `routine`, any applicable risk model outputs band `high` | routine $\to$ `review` | `RISK_CAN_RAISE=true` (Subject to `RISK_RAISE_COOLDOWN_DAYS`) |
| **R-S2-2** | Clinical rules level is `routine`, trend agent reports direction `rising` with $\ge 5$ points (`TREND_MIN_POINTS=5`, Doctor Answer 2), and latest reading is above target threshold (>140 SBP or >180 Glucose) | routine $\to$ `review` | `TREND_CAN_RAISE=true` (Provider review detail displays longitudinal trend chart) |
| **R-S2-3** | Any Stage-2 escalation | Maximum 1 step (`routine` $\to$ `review`) | Invariant: Stage-2 can **never** escalate directly to `urgent` or `emergency` |
| **R-S2-4** | Clinical rules level is `routine`, no BP or glucose readings available, and patient reported feeling unwell (severe symptom picture) | routine $\to$ `review` | `NO_READING_SYMPTOM_RAISE=true` (**Pending clinician formal sign-off**) |

### Single Source of Truth Triage Colors

Colors are computed centrally via `level_to_colour(level)` in `backend-poc-technical/agents/final_triage.py`:
- `routine` $\to$ **Green** ("Green - Routine")
- `review` $\to$ **Yellow** ("Yellow - Review")
- `urgent` $\to$ **Red** ("Red - Urgent")
- `emergency` $\to$ **Red** ("Red - Emergency")

Accessibility Requirement: Text labels are always rendered alongside color chips; color is never the sole indicator.

---

## Confidence Level Calculation (Section 17)

Each risk assessment carries an evidence confidence rating:
- **High**: Vital reading acquired via FHIR connection, recorded on the same day (`age_days == 0`), with no reconciliation conflict.
- **Medium**: Patient self-reported vital reading, or FHIR reading older than 7 days.
- **Low**: OCR extracted reading not yet confirmed by patient.
- **First-Checkin Cap**: A patient's first completed check-in is capped at **Medium** confidence (Section 13.1.1).

---

## Multi-Model Architecture & SHAP Drivers

- **Dynamic Loading**: Loads all models from `backend-poc-technical/models/*.json`.
- **Supported Models**:
  - `diabetes_full_nhanes`: Evaluated for hypertensive patients without diabetes.
  - `chd10_framingham`: Framingham 10-year coronary heart disease model, evaluated for patients with hypertension OR diabetes.
- **Standardized SHAP Drivers**: Feature contributions in standardized log-odds space:
  $$\text{contribution}_i = \text{coef}_i \times \frac{x_i - \text{mean}_i}{\text{scale}_i}$$
  Guaranteed identity: $\text{intercept} + \sum_i \text{contribution}_i = \text{logit}$.
  Provider review UI renders top 3 drivers with direction (+ / -) and localized clinical labels.

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
