"""
Benchmark candidate open-weight LLM models on Groq for ChronicCare AI grounded explainer.
Measures latency ONLY around each successful API request (time.perf_counter just before and after client.chat.completions.create).
Records backoff/sleep time and retry count separately.
Reports per model:
- Single-call latency (p50, p95)
- Calls per case (mean)
- Whole case latency (p50, p95) (en + translation)
- Separate backoff time and retry count
- Raw response text (first 300 chars) for any failure

Evaluates:
- llama-3.3-70b-versatile
- openai/gpt-oss-120b
- openai/gpt-oss-20b
- qwen/qwen3.8-27b
(allam-2-7b is skipped per decision)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

repo_root = Path(__file__).resolve().parent.parent.parent
env_local = repo_root / ".env.local"
if env_local.exists():
    load_dotenv(env_local)

# Add backend to path
sys.path.insert(0, str(repo_root / "backend-poc-technical"))

from llm.groq_client import get_client
from rag.explainer import explain
from rag.store import JsonlChunkStore

FAKE_SCENARIOS = [
    {
        "id": "CASE_01_BP_SEVERE",
        "triage": {
            "level": "emergency",
            "trigger_category": "bp_severe",
            "reasons": ["bp_severe: SBP >= 180 or DBP >= 120"],
            "systolic": 185,
            "diastolic": 125,
        },
        "readings": {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125},
    },
    {
        "id": "CASE_02_BP_CRISIS",
        "triage": {
            "level": "emergency",
            "trigger_category": "bp_crisis",
            "reasons": ["bp_crisis: hypertensive emergency signs"],
            "systolic": 195,
            "diastolic": 122,
        },
        "readings": {"blood_pressure_systolic": 195, "blood_pressure_diastolic": 122},
    },
    {
        "id": "CASE_03_BP_URGENT",
        "triage": {
            "level": "urgent",
            "trigger_category": "bp_urgent",
            "reasons": ["bp_stage2: SBP >= 140 or DBP >= 90"],
            "systolic": 152,
            "diastolic": 96,
        },
        "readings": {"blood_pressure_systolic": 152, "blood_pressure_diastolic": 96},
    },
    {
        "id": "CASE_04_BP_LOW",
        "triage": {
            "level": "review",
            "trigger_category": "bp_low",
            "reasons": ["bp_low: SBP < 90 or DBP < 60"],
            "systolic": 86,
            "diastolic": 54,
        },
        "readings": {"blood_pressure_systolic": 86, "blood_pressure_diastolic": 54},
    },
    {
        "id": "CASE_05_BP_CHANGE",
        "triage": {
            "level": "review",
            "trigger_category": "bp_change",
            "reasons": ["bp_change: systolic rise >= 20 mmHg over median"],
            "systolic": 146,
            "diastolic": 88,
        },
        "readings": {"blood_pressure_systolic": 146, "blood_pressure_diastolic": 88},
    },
    {
        "id": "CASE_06_GLUCOSE_LOW",
        "triage": {
            "level": "urgent",
            "trigger_category": "glucose_low",
            "reasons": ["glucose_low: glucose < 70 mg/dL"],
            "glucose": 64,
        },
        "readings": {"glucose": 64},
    },
    {
        "id": "CASE_07_GLUCOSE_VERY_LOW",
        "triage": {
            "level": "emergency",
            "trigger_category": "glucose_very_low",
            "reasons": ["glucose_very_low: glucose < 54 mg/dL"],
            "glucose": 46,
        },
        "readings": {"glucose": 46},
    },
    {
        "id": "CASE_08_GLUCOSE_HIGH",
        "triage": {
            "level": "review",
            "trigger_category": "glucose_high",
            "reasons": ["glucose_high: glucose >= 250 mg/dL"],
            "glucose": 268,
        },
        "readings": {"glucose": 268},
    },
    {
        "id": "CASE_09_GLUCOSE_URGENT_HIGH",
        "triage": {
            "level": "urgent",
            "trigger_category": "glucose_urgent_high",
            "reasons": ["glucose_urgent_high: glucose >= 300 mg/dL"],
            "glucose": 325,
        },
        "readings": {"glucose": 325},
    },
    {
        "id": "CASE_10_RAMADAN_FASTING",
        "triage": {
            "level": "urgent",
            "trigger_category": "ramadan_fasting",
            "reasons": ["ramadan_fasting: low glucose during fasting hours"],
            "glucose": 66,
        },
        "readings": {"glucose": 66},
    },
    {
        "id": "CASE_11_PREGNANCY_HTN",
        "triage": {
            "level": "urgent",
            "trigger_category": "pregnancy_hypertension",
            "reasons": ["pregnancy_hypertension: elevated blood pressure in pregnancy"],
            "systolic": 148,
            "diastolic": 94,
        },
        "readings": {"blood_pressure_systolic": 148, "blood_pressure_diastolic": 94},
    },
    {
        "id": "CASE_12_ROUTINE",
        "triage": {
            "level": "routine",
            "trigger_category": "routine",
            "reasons": ["routine: all parameters within target limits"],
        },
        "readings": {"blood_pressure_systolic": 122, "blood_pressure_diastolic": 76, "glucose": 105},
    },
]


def calc_percentile(data: list[float], pct: float) -> float:
    """Calculate percentile with standard linear interpolation."""
    if not data:
        return 0.0
    s = sorted(data)
    idx = (len(s) - 1) * (pct / 100.0)
    low = int(idx)
    high = min(low + 1, len(s) - 1)
    weight = idx - low
    return round(s[low] * (1.0 - weight) + s[high] * weight, 3)


class TimedLLMCaller:
    """
    Wraps Groq chat completions with strict, isolated per-request timing.
    Measures latency ONLY around successful API calls via time.perf_counter.
    Separately tracks backoff/sleep time, retry counts, and captures raw failure text.
    """
    def __init__(self, model_name: str, client: Any, max_token_override: int = 1200):
        self.model_name = model_name
        self.client = client
        self.max_token_override = max_token_override

        # Timing metrics
        self.all_single_call_latencies: list[float] = []
        self.total_backoff_s: float = 0.0
        self.total_retries: int = 0

        # Case-level tracking
        self.case_calls: list[int] = []
        self.case_latencies: list[float] = []
        self.current_case_call_latencies: list[float] = []

        # Raw failure storage (verbatim strings from API or model output)
        self.raw_failures: list[dict[str, str]] = []
        self.last_raw_response_text: str = ""

    def start_case(self):
        self.current_case_call_latencies = []
        self.last_raw_response_text = ""

    def end_case(self):
        calls = len(self.current_case_call_latencies)
        self.case_calls.append(calls)
        self.case_latencies.append(sum(self.current_case_call_latencies))
        self.current_case_call_latencies = []

    def __call__(self, **kwargs) -> str:
        messages = kwargs.get("messages", [])
        temperature = kwargs.get("temperature", 0.0)
        max_tokens = self.max_token_override

        max_retries = 8
        for attempt in range(1, max_retries + 1):
            try:
                # TIMING RULE: Measure latency ONLY around each successful API request
                t0 = time.perf_counter()
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                t1 = time.perf_counter()
                call_duration = t1 - t0

                # Record successful single call latency
                self.all_single_call_latencies.append(call_duration)
                self.current_case_call_latencies.append(call_duration)

                choices = getattr(response, "choices", [])
                if choices and choices[0].message and choices[0].message.content:
                    content = choices[0].message.content.strip()
                    self.last_raw_response_text = content
                    return content
                self.last_raw_response_text = ""
                return ""

            except Exception as e:
                err_str = str(e)
                # Model 404 (not found / not accessible)
                if "404" in err_str or "model_not_found" in err_str:
                    raw_text = err_str[:300]
                    self.raw_failures.append({"type": "HTTP_404", "raw": raw_text})
                    raise

                # Daily token limit (TPD) exhaustion
                if "tokens per day" in err_str.lower() or "(tpd)" in err_str.lower():
                    raw_text = err_str[:300]
                    self.raw_failures.append({"type": "TPD_LIMIT_EXCEEDED", "raw": raw_text})
                    raise RuntimeError(f"DAILY_TPD_LIMIT: {raw_text}")

                # Rate limits (429 - RPM/TPM)
                if "429" in err_str or "rate limit" in err_str.lower() or "too many requests" in err_str.lower():
                    self.total_retries += 1
                    wait_sec = min(5.0 * attempt, 30.0)
                    self.total_backoff_s += wait_sec
                    print(f"      [RATE LIMIT 429] Waiting {wait_sec}s (retry {attempt}/{max_retries})...", flush=True)
                    time.sleep(wait_sec)
                # Transient errors
                elif any(term in err_str.lower() for term in ["500", "503", "timeout", "connection"]):
                    self.total_retries += 1
                    wait_sec = 2.0 * attempt
                    self.total_backoff_s += wait_sec
                    print(f"      [TRANSIENT ERROR] Waiting {wait_sec}s (retry {attempt}/{max_retries})...", flush=True)
                    time.sleep(wait_sec)
                else:
                    raw_text = err_str[:300]
                    self.raw_failures.append({"type": "API_ERROR", "raw": raw_text})
                    raise

        raw_text = f"Persistent rate limit after {max_retries} attempts: {err_str[:200]}"
        self.raw_failures.append({"type": "MAX_RETRIES_EXCEEDED", "raw": raw_text[:300]})
        raise RuntimeError(raw_text)


def run_benchmark_for_model(
    model_name: str,
    client: Any,
    store: JsonlChunkStore,
) -> dict:
    print(f"\n{'='*75}")
    print(f"STARTING BENCHMARK: {model_name}")
    print(f"{'='*75}")

    caller = TimedLLMCaller(model_name=model_name, client=client, max_token_override=1200)

    # Initial probe to test connectivity / 404
    print(f"Probing model endpoint: {model_name}...")
    try:
        t0 = time.perf_counter()
        probe_resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": 'Respond in JSON: {"status": "ok"}'}],
            max_tokens=200,
            temperature=0.0,
        )
        probe_lat = time.perf_counter() - t0
        print(f"  --> Endpoint AVAILABLE. Initial probe successful in {probe_lat:.3f}s.")
    except Exception as e:
        err_str = str(e)
        raw_first_300 = err_str[:300]
        print(f"  --> Endpoint PROBE FAILED: {raw_first_300}")
        return {
            "model": model_name,
            "status": "UNAVAILABLE",
            "probe_raw_error": raw_first_300,
            "evaluations_attempted": 0,
            "llm_success_rate": "0.0% (0/0)",
            "single_call_p50_s": None,
            "single_call_p95_s": None,
            "calls_per_case_mean": None,
            "whole_case_p50_s": None,
            "whole_case_p95_s": None,
            "total_backoff_s": 0.0,
            "total_retries": 0,
            "raw_failures": [{"type": "PROBE_FAILURE", "raw": raw_first_300}],
        }

    total_runs = 0
    llm_modes = 0
    template_fallbacks = 0
    v_errors = {"V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0}
    urdu_successes = 0
    roman_urdu_successes = 0

    abort_due_to_limit = False

    for sc in FAKE_SCENARIOS:
        if abort_due_to_limit:
            break
        for lang in ["en", "ur", "roman_ur"]:
            total_runs += 1
            caller.start_case()

            try:
                res = explain(
                    triage_result=sc["triage"],
                    readings=sc["readings"],
                    language=lang,
                    store=store,
                    llm=caller,
                    model=model_name,
                )
                caller.end_case()

                mode = res.get("mode")
                case_api_time = caller.case_latencies[-1] if caller.case_latencies else 0.0
                case_calls_cnt = caller.case_calls[-1] if caller.case_calls else 0

                if mode == "llm":
                    llm_modes += 1
                    if lang == "ur":
                        urdu_successes += 1
                    elif lang == "roman_ur":
                        roman_urdu_successes += 1
                    print(f"  [{sc['id']}] [{lang:<8}] -> LLM ({case_calls_cnt} calls, API: {case_api_time:.3f}s)", flush=True)
                else:
                    template_fallbacks += 1
                    reasons = res.get("rejected_reasons", [])
                    raw_text_sample = caller.last_raw_response_text[:300] if caller.last_raw_response_text else "No text returned."
                    caller.raw_failures.append({
                        "case": f"{sc['id']}:{lang}",
                        "reasons": "; ".join(reasons),
                        "raw_output_first_300": raw_text_sample,
                    })
                    for err in reasons:
                        for v_key in ["V1", "V2", "V3", "V4", "V5"]:
                            if v_key in err:
                                v_errors[v_key] += 1
                    print(f"  [{sc['id']}] [{lang:<8}] -> TEMPLATE ({'; '.join(reasons[:2])}) (API: {case_api_time:.3f}s)", flush=True)

            except Exception as e:
                caller.end_case()
                err_str = str(e)
                print(f"  [{sc['id']}] [{lang:<8}] -> RUN ERROR: {err_str[:120]}", flush=True)
                if "DAILY_TPD_LIMIT" in err_str:
                    print(f"  --> Aborting remaining runs for {model_name} due to daily token limit exhaustion.")
                    abort_due_to_limit = True
                    break

            # Throttle between cases to stay safely within RPM
            time.sleep(1.2)

    # Compute percentiles
    single_p50 = calc_percentile(caller.all_single_call_latencies, 50.0) if caller.all_single_call_latencies else None
    single_p95 = calc_percentile(caller.all_single_call_latencies, 95.0) if caller.all_single_call_latencies else None

    completed_case_latencies = [lat for lat, cnt in zip(caller.case_latencies, caller.case_calls) if cnt > 0]
    case_p50 = calc_percentile(completed_case_latencies, 50.0) if completed_case_latencies else None
    case_p95 = calc_percentile(completed_case_latencies, 95.0) if completed_case_latencies else None

    completed_case_calls = [cnt for cnt in caller.case_calls if cnt > 0]
    mean_calls_per_case = round(sum(completed_case_calls) / len(completed_case_calls), 2) if completed_case_calls else 0.0

    llm_pct = (llm_modes / total_runs) * 100.0 if total_runs else 0.0
    ur_pct = (urdu_successes / len(FAKE_SCENARIOS)) * 100.0
    rur_pct = (roman_urdu_successes / len(FAKE_SCENARIOS)) * 100.0

    summary = {
        "model": model_name,
        "status": "COMPLETE" if total_runs == 36 else f"INCOMPLETE ({total_runs}/36)",
        "evaluations_attempted": total_runs,
        "llm_success_rate": f"{llm_pct:.1f}% ({llm_modes}/{total_runs})",
        "llm_success_count": llm_modes,
        "template_fallback_rate": f"{(template_fallbacks / total_runs) * 100.0:.1f}% ({template_fallbacks}/{total_runs})",
        "urdu_pass_rate": f"{ur_pct:.1f}% ({urdu_successes}/{len(FAKE_SCENARIOS)})",
        "roman_urdu_pass_rate": f"{rur_pct:.1f}% ({roman_urdu_successes}/{len(FAKE_SCENARIOS)})",
        "single_call_p50_s": single_p50,
        "single_call_p95_s": single_p95,
        "calls_per_case_mean": mean_calls_per_case,
        "whole_case_p50_s": case_p50,
        "whole_case_p95_s": case_p95,
        "total_single_calls": len(caller.all_single_call_latencies),
        "total_backoff_s": round(caller.total_backoff_s, 2),
        "total_retries": caller.total_retries,
        "latency_gate_passed": (case_p95 <= 8.0) if case_p95 is not None else False,
        "validator_failures": v_errors,
        "raw_failures": caller.raw_failures[:5],
    }
    return summary


def main():
    data_dir = Path(os.environ.get("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data"))
    chunks_file = data_dir / "rag" / "chunks.jsonl"
    store = JsonlChunkStore(chunks_file)

    client = get_client()

    candidate_models = [
        "llama-3.3-70b-versatile",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]

    all_summaries = []

    for model_name in candidate_models:
        try:
            summary = run_benchmark_for_model(model_name, client, store)
            all_summaries.append(summary)
        except Exception as e:
            print(f"FATAL ERROR on {model_name}: {e}")
            all_summaries.append({
                "model": model_name,
                "status": "FATAL_ERROR",
                "error": str(e)[:300],
            })

    # Save to JSON first
    out_path = data_dir / "rag" / "model_comparison_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2, ensure_ascii=False)
    print(f"\nSaved comparison JSON to {out_path}")

    print("\n" + "=" * 90)
    print("VERIFIED OPEN-WEIGHT MODEL BENCHMARK (ISOLATED PER-REQUEST TIMING)")
    print("=" * 90)

    for s in all_summaries:
        print(f"\nModel: {s['model']}")
        print(f"  * Status:                      {s.get('status')}")
        if s.get("status") in ("COMPLETE", "INCOMPLETE") or "INCOMPLETE" in s.get("status", ""):
            print(f"  * LLM Success Rate:            {s.get('llm_success_rate')}")
            print(f"  * Template Fallbacks:          {s.get('template_fallback_rate')}")
            print(f"  * Urdu Pass Rate:              {s.get('urdu_pass_rate')}")
            print(f"  * Roman Urdu Pass Rate:        {s.get('roman_urdu_pass_rate')}")
            print(f"  * Single-Call Latency:         p50 = {s.get('single_call_p50_s')}s, p95 = {s.get('single_call_p95_s')}s (n={s.get('total_single_calls', 0)})")
            print(f"  * Calls Per Case:              mean = {s.get('calls_per_case_mean')}")
            print(f"  * Whole Case Latency:          p50 = {s.get('whole_case_p50_s')}s, p95 = {s.get('whole_case_p95_s')}s (Gate <= 8s: {s.get('latency_gate_passed')})")
            print(f"  * Backoff Sleep Time:          {s.get('total_backoff_s', 0.0)}s across {s.get('total_retries', 0)} retries")
            print(f"  * Validator Failures:          {s.get('validator_failures')}")
        elif s.get("status") == "UNAVAILABLE":
            print(f"  * Probe Error (Raw):           {s.get('probe_raw_error')}")
        else:
            print(f"  * Error:                       {s.get('error')}")

        if s.get("raw_failures"):
            print(f"  * Sample Raw Failure Output:")
            for rf in s["raw_failures"][:2]:
                raw_val = rf.get('raw', rf.get('raw_output_first_300', ''))[:300]
                safe_val = raw_val.encode('ascii', 'replace').decode('ascii')
                print(f"    - [{rf.get('type', rf.get('case'))}]: {safe_val}")


if __name__ == "__main__":
    main()
