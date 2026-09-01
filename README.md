# ChronicCare AI — Frontend UI Prototype (Milestones 1 & 2)

This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones.

## Overview
A high-fidelity, interactive, mobile-responsive frontend prototype for **ChronicCare AI**, built with Next.js (React) and Tailwind CSS.

### Implemented Capabilities:

#### Milestone 1 (M1) — Daily Symptom Check-In Flow
- **Login / Sign-up Flow**: Clean credentials entry navigating into onboarding.
- **Dual Connection Modes**:
  - **Hospital EHR (FHIR)**: Simulated HL7® FHIR® connectivity handshake with City General Hospital directly leading into the Home Dashboard.
  - **Isolated Offline Mode**: Local device profile configuration capturing baseline conditions, medications, and age.
- **Home / Dashboard**: Prominent daily symptom check-in reminder card and clinical overview.
- **Bilingual Support (English / اردو)**: Full static UI translation toggle persisting across all screen transitions.
- **Check-In Entry**: Free-form text input and simulated 2-second voice listening animation with hardcoded transcription auto-fill.
- **Adaptive Clinical Interview**:
  - Question 1 (Thirst) with conditional branch to Question 2 (Urination frequency).
  - Question 3 (Medication adherence) with "Prefer not to answer" option setting `lowConfidence` state.
- **Confirmation Screen**: Official completion acknowledgment with options to Return to Home or View Results.

#### Milestone 2 (M2) — Processing, Risk Assessment & Trend Visualization
- **Processing Screen**: 2.2-second animated loading indicator ("Analyzing your recent health information…").
- **Verification Flash**: Automatic 1-second "✓ Result verified" validation beat before displaying results.
- **Risk Result Screen & Purely Presentational `RiskBadge`**:
  - `RiskBadge` component rendering `riskLevel="low"` (🟢 Low Risk) without computing or inferring scores.
  - Supporting clinical context ("Your recent check-ins look stable").
- **"Why" / Contributing Factors Panel**:
  - 4 bullet points highlighting key stable indicators (glucose in target range, zero missed doses, stable blood pressure).
  - Mandatory safeguard label: *"Example contributing factors — representative visualization of future SHAP-based explanation."*
- **Trend Screen**:
  - 3 responsive multi-day observation charts using Recharts:
    1. **Blood Glucose (mg/dL)**: 8-day trajectory with target range indicator.
    2. **Blood Pressure (mmHg)**: 8-day Systolic and Diastolic trend.
    3. **Medication Adherence (%)**: 8-day adherence tracking.
  - Return to Home navigation ending the M2 milestone flow.

---

## Running Locally

### Prerequisites
- Node.js (v18+ recommended)
- npm

### 1. Install Dependencies
```bash
npm install
```

### 2. Start the Development Server
```bash
npm run dev
```

### 3. Open in Browser
Visit [http://localhost:3000](http://localhost:3000) to interact with the prototype.
