# ChronicCare AI — Clinical Safety & Emergency Handling

## What Happens When a Patient Reports an Emergency

ChronicCare AI is a clinical decision-support prototype. In accordance with safety principles, clinical decision-support systems must prioritize patient safety by failing closed and preventing any dropped emergency notifications.

---

### Step-by-Step Emergency Escalation Lifecycle

```
[Patient In-App Answer]
          │
          ▼
[Stage 1 Red-Flag & Dangerous BP Screen]
   ├── 1. Red-Flag Phrases (e.g., "chest pain", "can't breathe", "lost consciousness")
   └── 2. Hypertensive Crisis (systolic >= 180 mmHg or diastolic >= 120 mmHg)
          │
          ▼ (If Triggered)
[Atomic Server-Side Persistence]
   ├── 1. Update Check-In Status to 'emergency' (version incremented)
   ├── 2. Create 'checkin_results' (emergency=True, max_severity='high', review_status='open')
   │      - Captures trigger_category (e.g. 'chest_pain' or 'bp_crisis_range')
   │      - Captures trigger_text (truncated to 500 chars)
   │      - Captures trigger_reading (systolic/diastolic for BP crisis)
   └── 3. Append 'emergency_escalated' Audit Log Entry (ZERO PHI: contains only category)
          │
          ▼
[Immediate Parallel Response]
   ├── Patient UI: Receives { complete: true, emergency: true, escalation_recorded: true }
   │               Bypasses remaining questions; renders Urgent Medical Attention Screen.
   └── Provider Queue: Instantly populated at highest priority without requiring /complete call.
```

---

### Key Architectural Guarantees

1. **Zero Reliance on Secondary Client Calls**:
   - In earlier versions, emergency items were written only when `/complete` was called. In a real emergency, the patient's browser transitions immediately to an emergency screen and never calls `/complete`.
   - Now, the exact `POST /api/checkins/{id}/answer` request that detects the red flag persists the emergency item to the database in the same transaction as the state update.

2. **Stage 1 Hypertensive Crisis Screening**:
   - In accordance with the AHA hypertensive crisis benchmark (Proposal Section 27), systolic readings $\ge 180$ mmHg or diastolic readings $\ge 120$ mmHg trigger Stage 1 red-flag escalation with reason `bp_crisis_range`.
   - The trigger reading is attached directly to the intake and exposed to the provider in the review queue.

3. **Concurrency and State Integrity (Optimistic Locking)**:
   - Each check-in maintains a monotonic `version` counter.
   - Answers submitted with a `step` that does not match the server's state return `409 Conflict` (`stale_step`).
   - Concurrent writes attempting to update the same version return `409 Conflict` (`concurrent_update`).

4. **Zero-PHI Audit Logging**:
   - The `emergency_escalated` audit log entry records only `{ "category": "<reason>" }` (e.g. `chest_pain` or `bp_crisis_range`).
   - Free-text patient answers and symptoms are never stored in the immutable audit log.
