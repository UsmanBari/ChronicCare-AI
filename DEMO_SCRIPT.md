# ChronicCare AI — Presenter Live Demo Cue Sheet

> **Presenter Guide**: Follow these exact click-by-click sequences for demonstrating the three clinical scenarios across the Patient, Provider, and Admin portals.
>
> *Disclaimer: "This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones."*

---

## Pre-Demo Setup
1. Launch app at `http://localhost:3000`.
2. Select **"Patient Portal"** on the landing screen.
3. Sign in with sample credentials (`patient@demo.care`).
4. Select **"Connect to your hospital's EHR"** (FHIR path) $\rightarrow$ Observe 1.5s simulated handshake $\rightarrow$ Lands on **Home Dashboard**.

---

## Scenario A: Normal Daily Check-in (Stable Risk & Trends)

### Patient Portal Flow
1. On **Home Dashboard**, ensure **[Scenario A: Normal]** is active in the dashed *Presenter Controls* box.
2. Click **"Start Daily Check-In"**.
3. In **Check-In Entry**:
   - Click the **Microphone icon** $\rightarrow$ *Say: "The patient uses speech-to-text to dictate symptoms."* $\rightarrow$ Observe 2s pulsing animation auto-filling *"I've been feeling a bit tired and thirsty lately"*.
   - Click **"Continue"**.
4. In **Adaptive Interview**:
   - **Question 1** (*Thirst*): Click **"No"** $\rightarrow$ *Say: "The system skips Question 2 because no thirst escalation was reported."*
   - **Question 3** (*Missed Meds*): Click **"No"**.
   - Click **"Submit Check-In"**.
5. In **Confirmation Screen**:
   - Click **"View My Results"**.
6. In **Processing & Risk Assessment**:
   - Observe 2.2s analysis progress $\rightarrow$ 1.0s **"✓ Clinical Assessment Verified"** validation flash.
   - Observe **🟢 Low Risk** badge and *"Your recent check-ins look stable"*.
   - Click **"See Why"** $\rightarrow$ *Say: "Here are the contributing factors, highlighting our future SHAP-based explanation safeguard."*
   - Click **"View Trends"** $\rightarrow$ Observe 8-day multi-day observation charts (Blood Glucose, Blood Pressure, Medication Adherence).
   - Click **"Return to Home"**.

### Provider Portal Verification
1. Click **Portal Switcher** in header $\rightarrow$ Select **"Provider Portal"** (or sign in as `dr.sanamalik@citygeneral.org`).
2. Point to **Live Counters**:
   - *Active Cases: 2 Tracked* (Baseline: Ahmed + Sara Ahmed).
   - *Urgent Cases: 0*.
3. Point to **Patient Cohort**: Ali Khan is 🟢 Green (Stable check-in logged). Review Queue has no pending item for Ali Khan.

---

## Scenario B: Data Reconciliation Conflict (Discrepancy Triage)

### Patient Portal Flow
1. Switch to **Patient Portal** via header dropdown.
2. In *Presenter Controls*, click **"Scenario B: Conflict"**.
3. Click **"Start Daily Check-In"** $\rightarrow$ Click **"Continue"**.
4. In **Adaptive Interview**:
   - **Question 1** (*Thirst*): Click **"Yes"** $\rightarrow$ Follow-up **Question 2** appears.
   - **Question 2** (*Urination*): Click **"No"**.
   - **Question 3** (*Missed Meds*): Click **"Prefer not to answer"** *(tracks low confidence)*.
   - Click **"Submit Check-In"** $\rightarrow$ Click **"View My Results"**.
5. In **Processing & Conflict Screen**:
   - Observe 2.2s processing $\rightarrow$ Direct transition to **"⚠ Conflict Detected"** screen.
   - *Say: "The reconciliation layer detected a conflict between self-reported glucose (180 mg/dL) and the clinic's FHIR record (140 mg/dL), noting an unanswered question."*
   - Point to exact defensive caption.
   - Click **"Continue"** $\rightarrow$ Lands on **"⚠ Low Confidence — Routed to Human Review"**.
   - Click **"Return to Home"**.

### Provider Portal Triage & Scheduling
1. Switch to **Provider Portal** via header.
2. Point to **Live Counters**:
   - *Active Cases: 3 — New: Ali Khan* (glowing highlight flash).
   - *Notifications*: 🟡 *"Review required — Ali Khan, conflicting glucose readings"*.
3. Click **"Open Review Queue"** $\rightarrow$ Click **Ali Khan's row**.
4. In **Reconciliation Alert Detail**:
   - Point to Patient Check-in (180 mg/dL) vs. FHIR EHR (140 mg/dL).
   - Click **"Schedule Appointment"**.
5. In **Schedule Patient Follow-up**:
   - Select **"Mon, Sep 7 • 9:00 AM"** $\rightarrow$ Click **"Confirm Appointment"**.
   - Observe confirmation: *"Appointment booked. Ali Khan has been notified."*

### Cross-Portal Confirmation (Patient Side)
1. Switch to **Patient Portal** via header.
2. Click **"My Appointments"** button.
3. *Say: "Ali Khan immediately sees the appointment scheduled by Dr. Sana Malik for Mon, Sep 7 at 9:00 AM."*

---

## Scenario C: Critical Emergency Escalation

### Patient Portal Flow
1. In **Patient Portal**, click **"Scenario C: Emergency"** in *Presenter Controls*.
2. Click **"Start Daily Check-In"** $\rightarrow$ Click **"Continue"**.
3. In **Adaptive Interview**:
   - **Question 1**: Click **"Yes"**.
   - **Question 2**: Click **"Yes"**.
   - **Question 3**: Click **"Yes"**.
   - Click **"Submit Check-In"** $\rightarrow$ Click **"View My Results"**.
4. In **Processing & Emergency Screen**:
   - Observe fast 1.0s processing $\rightarrow$ Direct transition to **"🚨 Emergency Pattern Detected"** red alert screen.
   - *Say: "The system bypasses standard risk badges and issues immediate medical guidance with automated provider dispatch."*
   - Click **"Return to Home"**.

### Provider & Admin Portal Verification
1. Switch to **Provider Portal**:
   - Point to **Urgent Cases Counter**: Flashing **🔴 1 New Urgent Case**.
   - Point to **Notification**: 🔴 *"New urgent case — Ali Khan, high-risk pattern detected"*.
   - Review Queue flags Ali Khan with *Urgent Action Required*.
2. Switch to **Admin Portal**:
   - Point to **Active System Alerts**: **🔴 1 Urgent**.
   - Point to **Audit Log**: *"Dr. Sana Malik reviewed Ali Khan's case"* timestamped record.

---

## Resetting Between Live Runs
- Return to **Patient Portal** $\rightarrow$ In *Presenter Controls*, click **"Reset Demo"**.
- *Say: "With one click, all transient check-in states, appointments, and alerts across all three portals are wiped clean back to baseline."*
