# ChronicCare AI — Frontend UI Prototype (Milestone 1)

This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones.

## Overview
A high-fidelity, interactive, mobile-responsive frontend prototype for **ChronicCare AI**, built with Next.js (React) and Tailwind CSS.

### Key Capabilities in Milestone 1:
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
- **Confirmation Screen**: Official completion acknowledgment for the daily check-in.

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
