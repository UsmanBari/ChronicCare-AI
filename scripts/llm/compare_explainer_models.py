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
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend-poc-technical"))

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


def evaluate_model_on_scenarios(model_name: str, store: JsonlChunkStore) -> dict:
    print(f"\n========================================================")
    print(f"BENCHMARKING MODEL: {model_name}")
    print(f"========================================================")

    total_runs = 0
    llm_modes = 0
    template_fallbacks = 0
    v_errors = {"V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0}
    latencies = []

    urdu_successes = 0
    roman_urdu_successes = 0

    for sc in FAKE_SCENARIOS:
        for lang in ["en", "ur", "roman_ur"]:
            total_runs += 1
            t0 = time.time()
            res = explain(
                triage_result=sc["triage"],
                readings=sc["readings"],
                language=lang,
                store=store,
                llm=chat,
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
                for err in res.get("rejected_reasons", []):
                    for v_key in ["V1", "V2", "V3", "V4", "V5"]:
                        if v_key in err:
                            v_errors[v_key] += 1

            print(f"  [{sc['id']}] [{lang:<8}] -> {mode.upper()} in {dur:.2f}s", flush=True)
            time.sleep(1.2)  # Throttle to stay within Groq RPM limits

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    llm_rate = (llm_modes / total_runs) * 100.0 if total_runs else 0.0
    ur_rate = (urdu_successes / len(FAKE_SCENARIOS)) * 100.0
    rur_rate = (roman_urdu_successes / len(FAKE_SCENARIOS)) * 100.0

    summary = {
        "model": model_name,
        "total_evaluations": total_runs,
        "llm_success_rate": f"{llm_rate:.1f}% ({llm_modes}/{total_runs})",
        "template_fallback_rate": f"{(template_fallbacks / total_runs) * 100.0:.1f}% ({template_fallbacks}/{total_runs})",
        "urdu_pass_rate": f"{ur_rate:.1f}% ({urdu_successes}/{len(FAKE_SCENARIOS)})",
        "roman_urdu_pass_rate": f"{rur_rate:.1f}% ({roman_urdu_successes}/{len(FAKE_SCENARIOS)})",
        "p50_latency_s": round(p50, 2),
        "p95_latency_s": round(p95, 2),
        "validator_failures": v_errors,
    }
    return summary


def main():
    data_dir = Path(os.environ.get("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data"))
    chunks_file = data_dir / "rag" / "chunks.jsonl"
    store = JsonlChunkStore(chunks_file)

    candidate_models = ["qwen/qwen3.8-27b", "allam-2-7b"]
    all_summaries = []

    for m in candidate_models:
        try:
            summary = evaluate_model_on_scenarios(m, store)
            all_summaries.append(summary)
        except Exception as e:
            print(f"Error evaluating {m}: {e}")

    print("\n" + "=" * 80)
    print("MODEL COMPARISON SUMMARY REPORT")
    print("=" * 80)
    for s in all_summaries:
        print(f"\nModel: {s['model']}")
        print(f"  • LLM Success Rate:         {s['llm_success_rate']}")
        print(f"  • Template Fallbacks:       {s['template_fallback_rate']}")
        print(f"  • Urdu Pass Rate:           {s['urdu_pass_rate']}")
        print(f"  • Roman Urdu Pass Rate:     {s['roman_urdu_pass_rate']}")
        print(f"  • Latency:                  p50 = {s['p50_latency_s']}s, p95 = {s['p95_latency_s']}s")
        print(f"  • Validator Failures:       {s['validator_failures']}")

    out_path = data_dir / "rag" / "model_comparison_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\nSaved comparison JSON to {out_path}")


if __name__ == "__main__":
    main()
