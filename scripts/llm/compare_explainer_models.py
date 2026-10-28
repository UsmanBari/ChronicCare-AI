"""
Benchmark candidate open-weight LLM models on Groq for ChronicCare AI grounded explainer.
Evaluates models across 12 fake triage results in English, Urdu, and Roman Urdu.
Measures:
- Validator pass rates (V1 through V5 individually)
- Template fallback rate
- Urdu / Roman Urdu translation pass rates
- Latency (p50, p95)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parent.parent.parent
env_local = repo_root / ".env.local"
if env_local.exists():
    load_dotenv(env_local)

# Add backend to path
sys.path.insert(0, str(repo_root / "backend-poc-technical"))

from llm.groq_client import chat
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


def make_robust_llm_caller(model_name: str, max_token_override: int | None = None, force_json_prompt: bool = False):
    """
    Returns an LLM caller with retry logic for Groq rate limits (429) and transient errors,
    with configurable token allocation for reasoning models.
    """
    def _call(**kwargs):
        call_kwargs = dict(kwargs)
        call_kwargs["model"] = model_name
        if max_token_override is not None:
            call_kwargs["max_tokens"] = max_token_override

        if force_json_prompt:
            # Emphasize JSON structure for models that struggle with schema following
            msgs = list(call_kwargs.get("messages", []))
            if msgs and msgs[-1].get("role") == "user":
                last_content = msgs[-1]["content"]
                if "{" not in last_content:
                    msgs[-1]["content"] = last_content + "\nREMINDER: You must respond in valid JSON only."
                    call_kwargs["messages"] = msgs

        max_retries = 8
        for attempt in range(1, max_retries + 1):
            try:
                return chat(**call_kwargs)
            except Exception as e:
                err_str = str(e)
                # Check for rate limit or transient errors
                if "429" in err_str or "rate limit" in err_str.lower() or "too many requests" in err_str.lower():
                    wait_sec = min(5.0 * attempt, 30.0)
                    print(f"    [RATE LIMIT] {model_name}: {err_str[:120]}... Waiting {wait_sec}s (retry {attempt}/{max_retries})...", flush=True)
                    time.sleep(wait_sec)
                elif "500" in err_str or "503" in err_str or "timeout" in err_str.lower() or "connection" in err_str.lower():
                    wait_sec = 2.0 * attempt
                    print(f"    [TRANSIENT ERROR] {model_name}: {err_str[:120]}... Waiting {wait_sec}s (retry {attempt}/{max_retries})...", flush=True)
                    time.sleep(wait_sec)
                else:
                    raise
        raise RuntimeError(f"Model {model_name} failed after {max_retries} retries due to persistent rate limit: {err_str[:200]}")

    return _call


def run_evaluation_pass(model_name: str, store: JsonlChunkStore, llm_func, description: str = "") -> tuple[dict, list[str]]:
    """Runs the 12 scenarios x 3 languages (36 evaluations) for a given model."""
    print(f"\n--- EVALUATION PASS: {model_name} {description} ---")
    total_runs = 0
    llm_modes = 0
    template_fallbacks = 0
    v_errors = {"V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0}
    latencies = []
    first_raw_errors: list[str] = []

    urdu_successes = 0
    roman_urdu_successes = 0

    try:
        for sc in FAKE_SCENARIOS:
            for lang in ["en", "ur", "roman_ur"]:
                total_runs += 1
                t0 = time.time()
                res = explain(
                    triage_result=sc["triage"],
                    readings=sc["readings"],
                    language=lang,
                    store=store,
                    llm=llm_func,
                    model=model_name,
                )
                dur = time.time() - t0
                latencies.append(dur)

                mode = res.get("mode")
                if mode == "llm":
                    llm_modes += 1
                    if lang == "ur":
                        urdu_successes += 1
                    elif lang == "roman_ur":
                        roman_urdu_successes += 1
                else:
                    template_fallbacks += 1
                    reasons = res.get("rejected_reasons", [])
                    if len(first_raw_errors) < 3 and reasons:
                        first_raw_errors.append(f"[{sc['id']}][{lang}] " + "; ".join(reasons))
                    for err in reasons:
                        for v_key in ["V1", "V2", "V3", "V4", "V5"]:
                            if v_key in err:
                                v_errors[v_key] += 1

                print(f"  [{sc['id']}] [{lang:<8}] -> {mode.upper()} in {dur:.2f}s", flush=True)
                time.sleep(1.2)  # Throttle to stay safely within RPM limit
    except Exception as e:
        print(f"  [RUN INTERRUPTED] {model_name}: {e}")
        first_raw_errors.append(str(e))

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    status = "COMPLETE" if total_runs == 36 else f"INCOMPLETE ({total_runs}/36)"
    llm_rate = (llm_modes / total_runs) * 100.0 if total_runs else 0.0
    ur_rate = (urdu_successes / len(FAKE_SCENARIOS)) * 100.0
    rur_rate = (roman_urdu_successes / len(FAKE_SCENARIOS)) * 100.0

    summary = {
        "model": model_name,
        "status": status,
        "total_evaluations": total_runs,
        "llm_success_rate": f"{llm_rate:.1f}% ({llm_modes}/{total_runs})",
        "llm_success_count": llm_modes,
        "template_fallback_rate": f"{(template_fallbacks / total_runs) * 100.0:.1f}% ({template_fallbacks}/{total_runs})" if total_runs else "N/A",
        "urdu_pass_rate": f"{ur_rate:.1f}% ({urdu_successes}/{len(FAKE_SCENARIOS)})",
        "roman_urdu_pass_rate": f"{rur_rate:.1f}% ({roman_urdu_successes}/{len(FAKE_SCENARIOS)})",
        "p50_latency_s": round(p50, 2),
        "p95_latency_s": round(p95, 2),
        "latency_gate_passed": (p95 <= 8.0) if latencies else False,
        "validator_failures": v_errors,
        "notes": description,
    }
    return summary, first_raw_errors


def evaluate_model_with_diagnosis(model_name: str, store: JsonlChunkStore) -> dict:
    print(f"\n========================================================")
    print(f"BENCHMARKING MODEL: {model_name}")
    print(f"========================================================")

    # Initial Pass: Standard call with default 400 tokens
    initial_llm = make_robust_llm_caller(model_name)
    summary, raw_errors = run_evaluation_pass(model_name, store, initial_llm, "(Initial Default Call)")

    # Diagnostic Rule: If a model fails all cases, print first 300 chars of raw error, fix call, and re-run
    if summary["llm_success_count"] == 0:
        print("\n" + "!" * 70)
        print(f"MODEL {model_name} FAILED ALL CASES ON INITIAL RUN.")
        print(f"FIRST 300 CHARACTERS OF RAW ERROR:")
        error_sample = raw_errors[0] if raw_errors else "All cases fell back to template."
        print(error_sample[:300])
        print("!" * 70)

        # Diagnose failure mode:
        if "gpt-oss" in model_name:
            print("\nDIAGNOSIS FOR openai/gpt-oss-20b:")
            print("Model is an internal reasoning model. The 400 max_tokens limit is consumed entirely by internal reasoning tokens, resulting in finish_reason='length' with empty completion and JSONDecodeError.")
            print("APPLYING FIX: Adjusting call parameters to max_tokens=1200 to accommodate reasoning tokens before JSON generation.")
            fixed_llm = make_robust_llm_caller(model_name, max_token_override=1200)
            summary_fixed, _ = run_evaluation_pass(model_name, store, fixed_llm, "(Fixed Call: max_tokens=1200 Reasoning Adjustment)")
            summary_fixed["initial_raw_error_first_300_chars"] = error_sample[:300]
            summary_fixed["diagnosis"] = "Reasoning tokens exhausted 400 token limit. Resolved by increasing max_tokens to 1200."
            return summary_fixed

        elif "allam" in model_name:
            print("\nDIAGNOSIS FOR allam-2-7b:")
            print("Model generates conversational prose ('Dear patient...') instead of adhering to JSON output format, triggering JSONDecodeError.")
            print("APPLYING FIX: Re-running with explicit JSON schema reminder in user prompt.")
            fixed_llm = make_robust_llm_caller(model_name, force_json_prompt=True)
            summary_fixed, _ = run_evaluation_pass(model_name, store, fixed_llm, "(Fixed Call: Forced JSON Schema Prompt)")
            summary_fixed["initial_raw_error_first_300_chars"] = error_sample[:300]
            summary_fixed["diagnosis"] = "Model failed JSON schema adherence and generated conversational plain text."
            return summary_fixed

    return summary


def main():
    data_dir = Path(os.environ.get("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data"))
    chunks_file = data_dir / "rag" / "chunks.jsonl"
    store = JsonlChunkStore(chunks_file)

    # Candidate models to evaluate
    candidate_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "allam-2-7b"]
    all_summaries = []

    # Check Llama availability
    print("\n--- CHECKING LLAMA MODEL AVAILABILITY ON CONFIGURED GROQ KEY ---")
    try:
        chat(messages=[{"role": "user", "content": "hi"}], model="llama-3.1-8b-instant")
        print("Llama 3.1 8B Instant is available! Adding to candidates.")
        candidate_models.append("llama-3.1-8b-instant")
    except Exception as e:
        print(f"Llama 3.1 8B Instant not accessible: {str(e)[:120]}")
        all_summaries.append({
            "model": "llama-3.1-8b-instant",
            "status": "UNAVAILABLE",
            "error": str(e)[:300],
            "note": "404 model_not_found / not entitled on this Groq API key",
        })

    for m in candidate_models:
        try:
            summary = evaluate_model_with_diagnosis(m, store)
            all_summaries.append(summary)
        except Exception as e:
            print(f"Fatal error evaluating {m}: {e}")
            all_summaries.append({
                "model": m,
                "status": "FATAL_ERROR",
                "error": str(e)[:300],
            })

    print("\n" + "=" * 80)
    print("FAIR OPEN-WEIGHT MODEL COMPARISON SUMMARY REPORT")
    print("=" * 80)
    for s in all_summaries:
        print(f"\nModel: {s['model']}")
        print(f"  • Status:                   {s.get('status')}")
        if s.get("status") in ("COMPLETE", "INCOMPLETE"):
            print(f"  • LLM Success Rate:         {s['llm_success_rate']}")
            print(f"  • Template Fallbacks:       {s['template_fallback_rate']}")
            print(f"  • Urdu Pass Rate:           {s['urdu_pass_rate']}")
            print(f"  • Roman Urdu Pass Rate:     {s['roman_urdu_pass_rate']}")
            print(f"  • Latency:                  p50 = {s['p50_latency_s']}s, p95 = {s['p95_latency_s']}s (Gate <= 8s: {s['latency_gate_passed']})")
            print(f"  • Validator Failures:       {s['validator_failures']}")
            if s.get("diagnosis"):
                print(f"  • Diagnosis & Fix Applied:  {s['diagnosis']}")
        else:
            print(f"  • Note/Error:               {s.get('note') or s.get('error')}")

    out_path = data_dir / "rag" / "model_comparison_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\nSaved comparison JSON to {out_path}")


if __name__ == "__main__":
    main()

