# Trend Agent Specification (Iteration 2 — Day 4)

## 1. Purpose & Clinical Safety Invariant

The Trend Agent is a deterministic medical decision-support module that computes the directional trajectory (`rising`, `stable`, `falling`, or `not_enough_history`) of key physiological readings over a recent observation window.

> **CRITICAL CLINICAL SAFETY INVARIANT (Advisory Only):**
> 1. **Zero Triage Impact:** The trend agent is strictly **ADVISORY**. It **never** sets, modifies, escalates, or lowers any clinical triage level (`emergency`, `urgent`, or `routine`).
> 2. **Not a Diagnosis:** Trend outputs are **never** presented to the patient or clinician as a medical diagnosis, clinical prognosis, or treatment directive.
> 3. **The Rules Decide:** "The model proposes, the rules decide." All triage and emergency escalations continue to be governed exclusively by `agents.triage_protocol`.

---

## 2. Data Sources & Inputs

The trend agent ingests the same underlying data sources as `get_user_baseline_history`, but operates over a configurable observation window (default **30 days**):
1. **Completed Check-In Intakes:** Vetted readings recorded in `checkin_results.intakes_json` from completed, non-emergency check-in sessions.
2. **Local Store Baseline Observations:** In isolated mode, patient-entered readings from the encrypted Local Store (excluding synthetic check-in mirrors prefixed with `CHECKIN-`).
3. **Connected EHR Observations:** In EHR-connected mode, standardized external observation resources.

*Note:* The existing 14-day triage baseline used by `agents.triage_protocol.compute_baseline` remains completely untouched.

---

## 3. Supported Reading Types & Glucose Context

### Monitored Observation Types:
- `blood_pressure_systolic` (mmHg)
- `blood_pressure_diastolic` (mmHg)
- `glucose` (mg/dL)

### Glucose by Context & Documented Limitation:
- In clinical practice, blood glucose trajectory varies significantly by meal context (`fasting`, `before_meal`, `after_meal`, `bedtime`).
- **Limitation:** In the current data model, while `adaptive_interview_agent.py` can capture glucose context within qualitative answer slots, quantitative readings in `intakes_json` and Local Store observations do not yet store a standardized context tag across all historical entries.
- **Protocol:** If a context tag is present on an entry, it is preserved in the reading history (`glucose_context`). However, for the Day 4 trend computation, all glucose readings are aggregated as a unified series. This constraint is documented as an exploratory limitation scheduled for context-stratified splitting in Iteration 3.

---

## 4. Mathematical Method

To ensure maximum robustness against measurement noise, white-coat spikes, and irregular intervals without external heavy dependencies like `scipy`, the trend agent uses a dual-agreement algorithm combining median delta and Theil–Sen robust slope estimation.

```text
Raw Readings (last 30 days)
    │
    ▼
1. Validation & Range Filtering (Exclude None, strings, out-of-bounds)
    │
    ▼
2. Timestamp Sort & Deduplication (Ascending order; latest reading kept)
    │
    ▼
3. Sample Size Check: n < BASELINE_MIN_READINGS (3) ──► "not_enough_history"
    │ (n >= 3)
    ▼
4. Half-Split: Earlier Half vs. Recent Half (Middle reading goes to recent half on odd n)
    │
    ▼
5. Median Delta: change = median(recent) - median(earlier)
    │
    ▼
6. Pure-Python Theil–Sen Slope per Week: median of all pairwise slopes
    │
    ▼
7. Dual-Agreement Direction Rule:
    ├── Rising:   change >= +Threshold  AND  slope_per_week > 0
    ├── Falling:  change <= -Threshold  AND  slope_per_week < 0
    └── Stable:   All other cases (sub-threshold or delta/slope sign conflict)
```

### Detailed Steps:

1. **Filtering & Plausibility Boundaries:**
   Readings outside physiological plausibility limits are excluded from trend calculations and tallied in `excluded_count`:
   - Systolic BP: `50.0 <= value <= 300.0 mmHg`
   - Diastolic BP: `30.0 <= value <= 200.0 mmHg`
   - Glucose: `20.0 <= value <= 1000.0 mg/dL`
   - `None`, booleans, NaN, and unparseable types are discarded.

2. **Temporal Sorting & Deduplication:**
   Readings are sorted in ascending chronological order (`oldest -> newest`). If two readings of the same type share identical timestamps, the latest observed value is retained.

3. **Window Boundary:**
   Only readings where `now - window_days <= timestamp <= now` are evaluated. Readings older than `window_days` or timestamped in the future are excluded.

4. **Minimum History Requirement ($n < 3$):**
   If fewer than `BASELINE_MIN_READINGS` (imported directly from `agents.triage_protocol`, default 3) remain, the trajectory direction is strictly `"not_enough_history"`.

5. **Odd/Even Half-Split:**
   The series of $n$ readings is divided into an earlier half and a recent half:
   - For even $n$: `earlier = values[:n // 2]`, `recent = values[n // 2:]`
   - For odd $n$: `earlier = values[:n // 2]`, `recent = values[n // 2:]` (the middle reading at index `n // 2` is assigned to the recent half).
   $$\Delta_{\text{median}} = \text{median}(\text{recent}) - \text{median}(\text{earlier})$$

6. **Theil–Sen Robust Slope per Week:**
   For all distinct index pairs $(i, j)$ with $i < j$ and $t_i < t_j$:
   $$S_{ij} = \frac{v_j - v_i}{(t_j - t_i)_{\text{days}}} \times 7.0$$
   $$\text{slope\_per\_week} = \text{median}(\{S_{ij} : i < j, t_i < t_j\})$$
   If all timestamps are identical (time delta 0), the slope defaults to `0.0`. Implemented entirely in pure Python (no `scipy` dependency).

7. **Dual-Agreement Direction Rule:**
   - `"rising"`: $\Delta_{\text{median}} \ge +\text{Threshold}$ **AND** $\text{slope\_per\_week} > 0$
   - `"falling"`: $\Delta_{\text{median}} \le -\text{Threshold}$ **AND** $\text{slope\_per\_week} < 0$
   - `"stable"`: All other conditions (e.g. magnitude of change $< \text{Threshold}$, or sign disagreement between delta and slope).

---

## 5. Proposed Thresholds

All thresholds are centralized in a single configuration block in `agents/trend_agent.py`:

```python
# PROPOSED - needs Usman + doctor review
TREND_THRESHOLDS = {
    "blood_pressure_systolic": 10.0,   # mmHg
    "blood_pressure_diastolic": 5.0,    # mmHg
    "glucose": 20.0,                   # mg/dL
}
```

---

## 6. Output Schema Specification

The top-level JSON structure returned by `compute_trends`:

```json
{
  "generated_at": "2026-10-29T14:30:00Z",
  "advisory": true,
  "window_days": 30,
  "excluded_count": 0,
  "trends": {
    "blood_pressure_systolic": {
      "direction": "rising",
      "n": 4,
      "window_days": 30,
      "first_at": "2026-10-05T08:00:00Z",
      "last_at": "2026-10-28T09:30:00Z",
      "median_earlier": 122.0,
      "median_recent": 136.0,
      "change": 14.0,
      "slope_per_week": 4.25,
      "values": [
        {"value": 120.0, "at": "2026-10-05T08:00:00Z"},
        {"value": 124.0, "at": "2026-10-12T08:15:00Z"},
        {"value": 134.0, "at": "2026-10-20T08:00:00Z"},
        {"value": 138.0, "at": "2026-10-28T09:30:00Z"}
      ]
    },
    "blood_pressure_diastolic": {
      "direction": "stable",
      "n": 4,
      "window_days": 30,
      "first_at": "2026-10-05T08:00:00Z",
      "last_at": "2026-10-28T09:30:00Z",
      "median_earlier": 78.0,
      "median_recent": 80.0,
      "change": 2.0,
      "slope_per_week": 0.6,
      "values": [
        {"value": 78.0, "at": "2026-10-05T08:00:00Z"},
        {"value": 78.0, "at": "2026-10-12T08:15:00Z"},
        {"value": 80.0, "at": "2026-10-20T08:00:00Z"},
        {"value": 80.0, "at": "2026-10-28T09:30:00Z"}
      ]
    },
    "glucose": {
      "direction": "not_enough_history",
      "n": 1,
      "window_days": 30,
      "first_at": "2026-10-28T09:30:00Z",
      "last_at": "2026-10-28T09:30:00Z",
      "median_earlier": null,
      "median_recent": null,
      "change": null,
      "slope_per_week": null,
      "values": [
        {"value": 140.0, "at": "2026-10-28T09:30:00Z"}
      ]
    }
  }
}
```

*Note on Values Capping:* `values` contains at most **14** most recent readings, formatted in chronological order (`oldest -> newest`).

---

## 7. Multilingual Labels (`TREND_LABELS`)

Multilingual presentation strings are provided in English, Urdu (Nastaliq script), and Roman Urdu. Marked `needs_native_review` for clinical terminology verification:

| Key | English (`en`) | Urdu (`ur`) | Roman Urdu (`roman_ur`) |
|---|---|---|---|
| `rising` | "Rising" | "اوپر کی طرف" | "Upar ki taraf" |
| `falling` | "Falling" | "نیچے کی طرف" | "Neechay ki taraf" |
| `stable` | "Stable" | "مستحکم" | "Mustahkam" |
| `not_enough_history` | "Not enough history" | "ناکافی ریکارڈ" | "Na-kaafi record" |
| `summary_pattern` | "{n} readings in {days} days" | "{days} دنوں میں {n} ریکارڈنگز" | "{days} dino mein {n} readings" |

---

## 8. Edge Case Defenses & Clinical Justifications

1. **Single Measurement Spike (White-Coat Effect / Acute Transient):**
   - *Scenario:* A patient with normal baseline BP (120, 122, 121) has an acute stress spike to 160 on reading 4, followed by 122 on reading 5: `[120, 122, 121, 160, 122]`.
   - *Defense:* The earlier half `[120, 122]` has median 121. The recent half `[121, 160, 122]` has median 122. Change is $+1$ mmHg ($< 10$ mmHg threshold). Furthermore, the pairwise slopes from the spike back down to 122 pull the Theil-Sen slope toward zero. The model labels this **stable**, preventing spurious alerts.
2. **Median / Slope Conflict:**
   - If an anomalous distribution yields a median delta $\ge 10$ but pairwise slopes are negative or zero (e.g. stepped drop followed by flat line), the direction defaults to **stable**.
3. **Missing or Corrupted Data:**
   - Any reading with `value=None`, boolean, non-numeric strings, or timestamps failing ISO parsing is dropped and recorded under `excluded_count`.
4. **Timezone Normalization:**
   - All string timestamps are parsed and converted to UTC timezone-aware datetimes before chronological sorting and window difference computations. Outputs are serialized with trailing `Z`.

