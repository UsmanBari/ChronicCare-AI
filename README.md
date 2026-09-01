# ChronicCare AI — Frontend UI Prototype (Milestones 1, 2, 3 & 4)

This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones.

## Overview
A high-fidelity, interactive, mobile-responsive frontend prototype for **ChronicCare AI**, built with Next.js (React) and Tailwind CSS.

---

### Implemented Capabilities by Milestone:

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
  - 3 responsive multi-day observation charts using Recharts (Blood Glucose, Blood Pressure, Medication Adherence).

#### Milestone 3 (M3) — Presenter Controls & Multi-Path Scenario Branching
- **Presenter Controls Panel (Home Screen)**:
  - **Scenario A: Normal**: Full M2 flow (Processing → Verification Flash → Low Risk Result → Contributing Factors → Trends).
  - **Scenario B: Conflict**: Processing → Reconciliation Conflict Screen (comparing reported 180 mg/dL vs EHR 140 mg/dL with Low Confidence and unanswered question tag if applicable) → Low Confidence / Routed to Human Review Screen.
  - **Scenario C: Emergency**: Urgency-optimized 1.0s processing → Dedicated Red Emergency Pattern Detected Screen (without RiskBadge) with clinical guidance and dispatch confirmation.
  - **Reset Demo**: Complete state clearance resetting all transient check-in responses, `lowConfidence` flags, and scenario state back to clean `'normal'`.

#### Milestone 4 (M4) — Multi-Portal Suite & Cross-Portal Synchronization
- **Portal Selection Landing Screen**:
  - Entry points for **Patient Portal** (Ali Khan), **Provider Portal** (Dr. Sana Malik), and **Admin Portal**.
  - Quick Portal Switcher dropdown in the top header.
- **Provider Dashboard & Live Counters**:
  - Live counters dynamically synchronized with `demoScenario`:
    - `Scenario A (Normal)`: Active Cases: 2, Urgent Cases: 0.
    - `Scenario B (Conflict)`: Active Cases: 3 (New: Ali Khan), Urgent Cases: 0. Notification: 🟡 *"Review required — Ali Khan, conflicting glucose readings"*.
    - `Scenario C (Emergency)`: Active Cases: 3 (New: Ali Khan), Urgent Cases: 🔴 1 New Urgent Case. Notification: 🔴 *"New urgent case — Ali Khan, high-risk pattern detected"*.
  - Fixed baseline patients: **Ahmed** (🟢 stable) and **Sara Ahmed** (🟡 incomplete check-in).
- **Clinical Review Queue & Reconciliation Alert Detail**:
  - Table with Patient, Reason, Confidence, and Status.
  - Clicking Ali Khan opens the **Reconciliation Alert Detail** with:
    - Patient check-in (180 mg/dL) vs. FHIR EHR record (140 mg/dL).
    - Exact defensive proof-of-concept caption.
    - Actions: **[Resolve Case]**, **[Schedule Appointment]**, and **[Escalate]**.
- **Provider Appointment Scheduling & Cross-Portal Sync**:
  - Provider books follow-up consultation slots (e.g. *"Mon, Sep 7 • 9:00 AM"*).
  - Instantly synchronizes to the **Patient Portal → "My Appointments"** screen.
- **Patient Appointments View**:
  - Empty state (*"No upcoming appointments"*) transitioning to scheduled appointment card with Dr. Sana Malik upon booking.
- **Admin Portal**:
  - Platform telemetry (126 Users, 18 Providers, 108 Patients, Active Alerts counter).
  - User Directory and compliance audit trail log.
- **Unified Settings Screen**:
  - Globally accessible modal consolidating Language Toggle (English / اردو) and Clinical Connection Mode status.

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
