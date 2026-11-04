"""
Evaluation Harness for Clinical Guideline Explainer (Day 2).

Measures end-to-end performance of the grounded guideline explainer:
- Evaluates real Groq LLM calls under production explain guards (guarded_explain).
- Enforces a hard 150,000 token daily budget stop cap.
- Captures validator acceptance vs rejection breakdown (V1-V5, budget timeouts, rate limits).
- Computes latency percentiles (p50, p95), fallback rates, and bootstrap 95% CIs.
- Checks Arabic script character ratio for Urdu outputs.
- Runs paired baseline template runs (llm=None).

Zero chunk text printed or committed.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

# Ensure backend-poc-technical and repo root are in python path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
ML_DIR = BACKEND_DIR / "ml"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm import groq_client
from ml.evaluation import bootstrap_ci
from rag.explain_guards import (
    CircuitBreaker,
    ExplainCache,
    TokenCapGuard,
    guarded_explain,
    reset_explain_guards,
)
from rag.store import ChunkStore, JsonlChunkStore

# Constants
DEFAULT_DAILY_TOKEN_LIMIT = 150000
RECOMMENDED_MODEL = "qwen/qwen3.8-27b"

# Arabic script Unicode range
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_PATTERN = re.compile(r"[a-zA-Z]")


def check_arabic_script_share(text: str) -> tuple[float, int, int]:
    """
    Computes the share of Arabic-script characters relative to total letters.
    Returns (ratio, arabic_chars_count, latin_chars_count).
    """
    if not text:
        return 0.0, 0, 0
    arabic_count = len(ARABIC_PATTERN.findall(text))
    latin_count = len(LATIN_PATTERN.findall(text))
    total_letters = arabic_count + latin_count
    if total_letters == 0:
        return 0.0, arabic_count, latin_count
    return float(arabic_count / total_letters), arabic_count, latin_count


def compute_series_ci(scores: list[float], n_boot: int = 1000) -> tuple[float, float | None, float | None]:
    """Computes mean and 95% bootstrap confidence interval using ml.evaluation.bootstrap_ci."""
    if not scores:
        return 0.0, None, None
    if len(scores) == 1:
        return float(scores[0]), None, None

    y = np.array([i % 2 for i in range(len(scores))], dtype=int)
    p = np.array(scores, dtype=float)

    def mean_metric(_y: np.ndarray, p_arr: np.ndarray) -> float:
        return float(np.mean(p_arr))

    try:
        ci = bootstrap_ci(y=y, p=p, metric_fn=mean_metric, n_boot=n_boot, stratified=False)
        return float(ci.point), ci.low, ci.high
    except (ValueError, ZeroDivisionError, RuntimeError):
        point = float(np.mean(p))
        return point, None, None


def format_metric_ci(point: float, low: float | None, high: float | None) -> str:
    """Formats point estimate and confidence interval to 3 decimal places."""
    if low is None or high is None:
        return f"{point:.3f} [N/A, N/A]"
    return f"{point:.3f} [{low:.3f}, {high:.3f}]"


def compute_percentiles(values: list[float]) -> tuple[float, float]:
    """Computes p50 and p95 for a list of values."""
    if not values:
        return 0.0, 0.0
    arr = np.array(values, dtype=float)
    p50 = float(np.percentile(arr, 50))
    p95 = float(np.percentile(arr, 95))
    return p50, p95


class TokenTrackingLLM:
    """Wrapper around groq_client.chat_with_usage with token counting and hard cap."""

    def __init__(
        self,
        real_client_fn: Callable[..., Any] | None = None,
        token_cap: int = DEFAULT_DAILY_TOKEN_LIMIT,
        model: str = RECOMMENDED_MODEL,
    ):
        self.real_client_fn = real_client_fn or groq_client.chat_with_usage
        self.token_cap = token_cap
        self.model = model
        self.cumulative_prompt_tokens = 0
        self.cumulative_completion_tokens = 0
        self.cumulative_total_tokens = 0
        self.call_count = 0
        self.cap_reached = False

    def __call__(self, messages: Any, **kwargs: Any) -> tuple[str, int]:
        if self.cumulative_total_tokens >= self.token_cap:
            self.cap_reached = True
            raise RuntimeError(f"Token cap reached: cumulative {self.cumulative_total_tokens} >= {self.token_cap}")

        call_model = kwargs.pop("model", None) or self.model
        resp_obj = self.real_client_fn(messages, model=call_model, **kwargs)

        if isinstance(resp_obj, tuple) and len(resp_obj) == 2:
            resp_text, usage = resp_obj
            if isinstance(usage, dict):
                prompt_tok = usage.get("prompt_tokens", 0)
                comp_tok = usage.get("completion_tokens", 0)
                tot_tok = usage.get("total_tokens", prompt_tok + comp_tok)
            elif isinstance(usage, int):
                prompt_tok, comp_tok, tot_tok = usage, 0, usage
            else:
                prompt_tok, comp_tok, tot_tok = 0, 0, 0
        else:
            resp_text = str(resp_obj)
            prompt_tok, comp_tok, tot_tok = 0, 0, 0

        self.cumulative_prompt_tokens += prompt_tok
        self.cumulative_completion_tokens += comp_tok
        self.cumulative_total_tokens += tot_tok
        self.call_count += 1

        if self.cumulative_total_tokens >= self.token_cap:
            self.cap_reached = True

        return resp_text, tot_tok


def evaluate_single_case(
    case: dict[str, Any],
    store: ChunkStore | None,
    llm: Any,
    budget_seconds: float = 8.0,
    use_cache: bool = False,
) -> dict[str, Any]:
    """Runs a single explanation case under guarded_explain."""
    triage_result = copy.deepcopy(case.get("triage_result") or {"level": case.get("triage_level", "routine")})
    readings = copy.deepcopy(case.get("readings") or {})
    lang = case.get("language", "en")
    cond = case.get("condition", "diabetes")

    # Isolated fresh cache per case if use_cache is False to prevent unverified cross-run reuse
    case_cache = ExplainCache(max_size=100) if not use_cache else None
    case_guard = TokenCapGuard(cap=200000)
    case_breaker = CircuitBreaker(failures_threshold=5, cooldown_seconds=30.0)

    start_time = time.monotonic()
    result = guarded_explain(
        triage_result=triage_result,
        readings=readings,
        language=lang,
        store=store,
        llm=llm,
        condition=cond,
        budget_seconds=budget_seconds,
        cache=case_cache,
        daily_token_guard=case_guard,
        breaker=case_breaker,
    )
    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    # Extract full text
    sentences = result.get("sentences", [])
    full_text = " ".join(s.get("text", "") for s in sentences if isinstance(s, dict))

    return {
        "case_id": case.get("case_id"),
        "persona_id": case.get("persona_id"),
        "condition": cond,
        "language": lang,
        "triage_level": case.get("triage_level"),
        "mode": result.get("mode", "template"),
        "reason": result.get("reason", "unknown"),
        "rejected_reasons": result.get("rejected_reasons", []),
        "latency_ms": elapsed_ms,
        "sentences_count": len(sentences),
        "explanation_text": full_text,
        "cites": [c for s in sentences if isinstance(s, dict) for c in s.get("cites", [])],
    }


def run_evaluation(
    cases: list[dict[str, Any]],
    store: ChunkStore | None,
    llm_callable: Callable[..., Any] | None,
    model_name: str,
    run_llm: bool = True,
    token_cap: int = DEFAULT_DAILY_TOKEN_LIMIT,
) -> dict[str, Any]:
    """Executes the full evaluation pipeline across all cases."""
    reset_explain_guards()

    llm_eval_results = []
    template_eval_results = []

    tracking_llm = None
    if run_llm and llm_callable is not None:
        tracking_llm = TokenTrackingLLM(
            real_client_fn=llm_callable,
            token_cap=token_cap,
            model=model_name,
        )

    print(f"\nRunning Explainer Evaluation across {len(cases)} cases...")
    print(f"Model: {model_name} | Daily Token Cap: {token_cap:,}")

    # 1. Baseline Template Run (llm=None)
    print("\n--- Running Baseline Template Run (llm=None) ---")
    for idx, c in enumerate(cases):
        res = evaluate_single_case(c, store=store, llm=None)
        template_eval_results.append(res)

    # 2. LLM Run (if configured)
    if tracking_llm is not None:
        print("\n--- Running Guarded LLM Run ---")
        for idx, c in enumerate(cases):
            if tracking_llm.cap_reached:
                print(f"  [STOP] Token budget limit reached at case {idx}/{len(cases)}. Halting LLM calls.")
                # Mark remaining as token cap fallbacks
                res = evaluate_single_case(c, store=store, llm=None)
                res["mode"] = "template"
                res["reason"] = "token_cap_exceeded"
                res["rejected_reasons"] = ["Daily evaluation token budget limit (150k) reached"]
                llm_eval_results.append(res)
                continue

            try:
                res = evaluate_single_case(c, store=store, llm=tracking_llm)
                llm_eval_results.append(res)
                status_icon = "PASS" if res["mode"] == "llm" else f"FALLBACK ({res['reason']})"
                print(f"  [{c['case_id']}] {c['condition']}/{c['language']} ({c['triage_level']}) -> {status_icon} in {res['latency_ms']:.1f}ms")
            except Exception as e:  # noqa: BLE001
                print(f"  [{c['case_id']}] Exception: {e}")
                res = evaluate_single_case(c, store=store, llm=None)
                res["mode"] = "template"
                res["reason"] = "execution_error"
                res["rejected_reasons"] = [str(e)]
                llm_eval_results.append(res)
    else:
        print("\n--- Real LLM is NOT RUN (GROQ_API_KEY not configured or --baseline-only specified) ---")

    # 3. Compute Metrics
    summary = compute_summary_metrics(
        cases=cases,
        llm_results=llm_eval_results,
        template_results=template_eval_results,
        tracking_llm=tracking_llm,
        model_name=model_name,
    )
    return summary


def compute_summary_metrics(
    cases: list[dict[str, Any]],
    llm_results: list[dict[str, Any]],
    template_results: list[dict[str, Any]],
    tracking_llm: TokenTrackingLLM | None,
    model_name: str,
) -> dict[str, Any]:
    """Aggregates raw evaluation results into report metrics."""
    n_cases = len(cases)
    has_llm = len(llm_results) == n_cases and any(r["mode"] == "llm" for r in llm_results)

    # Acceptance & fallback
    acceptance_scores = [1.0 if r["mode"] == "llm" else 0.0 for r in llm_results] if has_llm else []
    acc_pt, acc_lo, acc_hi = compute_series_ci(acceptance_scores) if acceptance_scores else (0.0, None, None)
    fallback_rate = (1.0 - acc_pt) if has_llm else 1.0

    # Rejection breakdown
    rejections: dict[str, int] = {}
    validator_rejections: dict[str, int] = {"V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0}
    for r in llm_results:
        if r["mode"] == "template":
            reason = r.get("reason", "unknown")
            rejections[reason] = rejections.get(reason, 0) + 1
            for rej in r.get("rejected_reasons", []):
                for v in ("V1", "V2", "V3", "V4", "V5"):
                    if rej.startswith(v) or f" {v}:" in rej:
                        validator_rejections[v] += 1

    # Latencies
    llm_latencies = [r["latency_ms"] for r in llm_results] if has_llm else []
    tmpl_latencies = [r["latency_ms"] for r in template_results]

    llm_p50, llm_p95 = compute_percentiles(llm_latencies)
    tmpl_p50, tmpl_p95 = compute_percentiles(tmpl_latencies)

    # Tokens
    tot_tokens = tracking_llm.cumulative_total_tokens if tracking_llm else 0
    prompt_tokens = tracking_llm.cumulative_prompt_tokens if tracking_llm else 0
    comp_tokens = tracking_llm.cumulative_completion_tokens if tracking_llm else 0
    avg_tokens_per_call = (tot_tokens / tracking_llm.call_count) if (tracking_llm and tracking_llm.call_count > 0) else 0.0

    # Arabic script analysis for Urdu outputs
    urdu_script_metrics = []
    english_leaks_in_urdu = []
    for r in (llm_results if has_llm else template_results):
        if r["language"] == "ur":
            text = r["explanation_text"]
            ratio, ar_cnt, lat_cnt = check_arabic_script_share(text)
            urdu_script_metrics.append({
                "case_id": r["case_id"],
                "arabic_ratio": ratio,
                "arabic_count": ar_cnt,
                "latin_count": lat_cnt,
                "text_snippet": text[:80] + "..." if len(text) > 80 else text,
            })
            if ratio < 0.20 and lat_cnt > 10:
                english_leaks_in_urdu.append(r["case_id"])

    # Metrics by Language
    by_lang: dict[str, Any] = {}
    for lang in ("en", "ur", "roman_ur"):
        lang_res = [r for r in llm_results if r["language"] == lang] if has_llm else []
        if lang_res:
            scores = [1.0 if r["mode"] == "llm" else 0.0 for r in lang_res]
            pt, lo, hi = compute_series_ci(scores)
            lats = [r["latency_ms"] for r in lang_res]
            p50, p95 = compute_percentiles(lats)
            by_lang[lang] = {
                "count": len(lang_res),
                "acceptance": (pt, lo, hi),
                "p50_ms": p50,
                "p95_ms": p95,
            }

    # Metrics by Triage Level
    by_level: dict[str, Any] = {}
    for lvl in ("routine", "review", "urgent"):
        lvl_res = [r for r in llm_results if r["triage_level"] == lvl] if has_llm else []
        if lvl_res:
            scores = [1.0 if r["mode"] == "llm" else 0.0 for r in lvl_res]
            pt, lo, hi = compute_series_ci(scores)
            lats = [r["latency_ms"] for r in lvl_res]
            p50, p95 = compute_percentiles(lats)
            by_level[lvl] = {
                "count": len(lvl_res),
                "acceptance": (pt, lo, hi),
                "p50_ms": p50,
                "p95_ms": p95,
            }

    return {
        "model_name": model_name,
        "n_cases": n_cases,
        "has_llm_run": has_llm,
        "acceptance": (acc_pt, acc_lo, acc_hi),
        "fallback_rate": fallback_rate,
        "rejections_by_reason": rejections,
        "validator_rejections": validator_rejections,
        "latency_llm": {"p50_ms": llm_p50, "p95_ms": llm_p95},
        "latency_template": {"p50_ms": tmpl_p50, "p95_ms": tmpl_p95},
        "tokens": {
            "total_tokens": tot_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": comp_tokens,
            "avg_tokens_per_call": avg_tokens_per_call,
            "cap_reached": tracking_llm.cap_reached if tracking_llm else False,
        },
        "by_lang": by_lang,
        "by_level": by_level,
        "urdu_script_metrics": urdu_script_metrics,
        "english_leaks_in_urdu": english_leaks_in_urdu,
        "raw_llm_results": llm_results,
        "raw_template_results": template_results,
    }


def print_evaluation_report(summary: dict[str, Any]) -> None:
    """Prints formatted evaluation report with real numbers."""
    print("\n" + "=" * 80)
    print("CLINICAL GUIDELINE EXPLAINER EVALUATION REPORT (DAY 2)")
    print("=" * 80)
    print(f"Total Evaluation Cases: {summary['n_cases']}")
    print(f"Configured Model:       {summary['model_name']}")
    print(f"LLM Run Status:         {'COMPLETED' if summary['has_llm_run'] else 'NOT RUN (Template Baseline Only)'}")

    tok = summary["tokens"]
    print(f"Tokens Consumed:        {tok['total_tokens']:,} (Prompt: {tok['prompt_tokens']:,}, Completion: {tok['completion_tokens']:,})")
    print(f"Token Cap Reached:      {'YES (Stopped at 150k)' if tok['cap_reached'] else 'NO'}")

    acc_pt, acc_lo, acc_hi = summary["acceptance"]
    print("\n--- Overall Acceptance & Fallback ---")
    print(f"  LLM Acceptance Rate:  {format_metric_ci(acc_pt, acc_lo, acc_hi)} ({acc_pt * 100:.1f}%)")
    print(f"  Fallback Rate:        {summary['fallback_rate'] * 100:.1f}%")

    print("\n--- Latency Performance ---")
    print(f"  Guarded LLM Latency:  p50 = {summary['latency_llm']['p50_ms']:.1f} ms | p95 = {summary['latency_llm']['p95_ms']:.1f} ms")
    print(f"  Template Baseline:    p50 = {summary['latency_template']['p50_ms']:.1f} ms | p95 = {summary['latency_template']['p95_ms']:.1f} ms")

    print("\n--- Rejection Breakdown by Validator / Guard ---")
    print(f"  Guard Reasons:        {summary['rejections_by_reason']}")
    print(f"  Validator Violations: {summary['validator_rejections']}")

    print("\n--- Slices by Language ---")
    for lang, metrics in summary["by_lang"].items():
        pt, lo, hi = metrics["acceptance"]
        print(f"  Language {lang.upper():<8} (N={metrics['count']}): Acceptance = {format_metric_ci(pt, lo, hi)} | p50 = {metrics['p50_ms']:.1f}ms | p95 = {metrics['p95_ms']:.1f}ms")

    print("\n--- Slices by Triage Level ---")
    for lvl, metrics in summary["by_level"].items():
        pt, lo, hi = metrics["acceptance"]
        print(f"  Level {lvl.capitalize():<10} (N={metrics['count']}): Acceptance = {format_metric_ci(pt, lo, hi)} | p50 = {metrics['p50_ms']:.1f}ms | p95 = {metrics['p95_ms']:.1f}ms")

    print("\n--- Urdu Script Verification ---")
    u_metrics = summary["urdu_script_metrics"]
    print(f"  Total Urdu Cases Evaluated: {len(u_metrics)}")
    if u_metrics:
        avg_ratio = float(np.mean([m["arabic_ratio"] for m in u_metrics]))
        print(f"  Mean Arabic-Script Character Share: {avg_ratio * 100:.1f}%")
        leaks = summary["english_leaks_in_urdu"]
        print(f"  English-Only Leak Cases in Urdu:    {len(leaks)} ({leaks if leaks else 'None'})")

    print("=" * 80)
    print("[SUCCESS] Explainer evaluation completed.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate clinical guideline explainer")
    parser.add_argument("--cases", default="docs/explain_eval/cases.json", help="Path to cases JSON")
    parser.add_argument("--output", default="docs/explain_eval/results.json", help="Path to save evaluation output")
    parser.add_argument("--baseline-only", action="store_true", help="Run template baseline only without LLM")
    parser.add_argument("--token-cap", type=int, default=DEFAULT_DAILY_TOKEN_LIMIT, help="Max daily tokens")
    args = parser.parse_args()

    # Load cases
    cases_path = REPO_ROOT / args.cases
    if not cases_path.exists():
        print(f"Error: Cases file not found at {cases_path}")
        sys.exit(1)

    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    # Ingest / load corpus store
    data_dir = os.environ.get("CHRONICCARE_DATA_DIR", "")
    chunks_file = Path(data_dir) / "rag" / "chunks.jsonl" if data_dir else (REPO_ROOT / "rag" / "chunks.jsonl")

    store: ChunkStore | None = None
    if chunks_file.exists():
        store = JsonlChunkStore(chunks_file)
        print(f"Loaded {store.total_chunks()} chunks from {chunks_file}")
    else:
        print(f"Notice: Corpus chunks file not found at {chunks_file}; running in template/no-chunk mode.")

    # Check Groq configuration
    is_groq_set = groq_client.is_configured()
    print(f"GROQ_API_KEY: {'SET' if is_groq_set else 'NOT SET'}")

    configured_model = groq_client.get_configured_model() or RECOMMENDED_MODEL
    print(f"Model: {configured_model}")

    run_llm = is_groq_set and not args.baseline_only
    llm_callable = groq_client.chat_with_usage if is_groq_set else None

    summary = run_evaluation(
        cases=cases,
        store=store,
        llm_callable=llm_callable,
        model_name=configured_model,
        run_llm=run_llm,
        token_cap=args.token_cap,
    )

    print_evaluation_report(summary)

    # Save output JSON
    out_path = REPO_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved evaluation results to {out_path}")


if __name__ == "__main__":
    main()
