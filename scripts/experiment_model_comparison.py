#!/usr/bin/env python
"""Compare LLM models for placeholder compliance via parallel Lambda invocations.

Usage:
    # Single ticker
    python scripts/experiment_model_comparison.py --ticker DBS19 --date 2026-03-16

    # All tickers (full portfolio experiment)
    python scripts/experiment_model_comparison.py --all-tickers --date 2026-03-16

    # All tickers with specific models
    python scripts/experiment_model_comparison.py --all-tickers --date 2026-03-16 \
        --models openai/gpt-4o,anthropic/claude-sonnet-4,google/gemini-2.5-pro-preview,anthropic/claude-opus-4

Requires: Lambda deployed with experiment mode support.
"""

import argparse
import csv
import json
import os
import statistics
import time
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

LAMBDA_FUNCTION = "dr-daily-report-report-worker-dev"
REGION = "ap-southeast-1"
TICKERS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "tickers.csv")

DEFAULT_MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro-preview",
    "anthropic/claude-opus-4",
]


def load_tickers_from_csv(csv_path: str) -> list[str]:
    """Read ticker symbols from data/tickers.csv."""
    tickers = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row["Symbol"].strip()
            if symbol:
                tickers.append(symbol)
    return tickers


def invoke_experiment(client, function: str, ticker: str, model: str, data_date: str = None,
                      include_report_data: bool = False) -> dict:
    """Invoke Lambda with experiment payload. Returns result dict."""
    payload = {
        "experiment": True,
        "ticker": ticker,
        "model": model,
    }
    if data_date:
        payload["data_date"] = data_date
    if include_report_data:
        payload["include_report_data"] = True

    start = time.time()
    response = client.invoke(
        FunctionName=function,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    wall_time = time.time() - start

    result = json.loads(response["Payload"].read())
    result["wall_time_s"] = round(wall_time, 1)
    result["ticker"] = ticker
    return result


def print_single_ticker_comparison(results: list, data_date: str = None) -> None:
    """Print formatted comparison table for a single ticker."""
    print(f"\n{'='*85}")
    print(f"EXPERIMENT RESULTS{f'  (data_date: {data_date})' if data_date else ''}")
    print(f"{'='*85}")

    header = f"{'Model':<40} {'Compliance':>10} {'Injected':>8} {'Unresolved':>10} {'Cost':>8} {'Wall':>6}"
    print(header)
    print("-" * 85)

    for r in results:
        if r.get("status") == "error":
            print(f"{r.get('model', '?'):<40} {'ERROR':>10}   {r.get('error', '')[:30]}")
            continue

        metrics = r.get("placeholder_metrics", {})
        print(
            f"{r.get('model', '?'):<40} "
            f"{r.get('placeholder_compliance', 0):>9.1f}% "
            f"{metrics.get('injected_count', 0):>8} "
            f"{metrics.get('unresolved_count', 0):>10} "
            f"${r.get('api_costs', {}).get('llm_estimated', 0):>6.4f} "
            f"{r.get('wall_time_s', 0):>5.1f}s"
        )

    # Quality scores breakdown
    print(f"\n{'Model':<40} {'Faith':>7} {'Complete':>8} {'Reason':>7} {'Comply':>7} {'Report':>7}")
    print("-" * 85)
    for r in results:
        if r.get("status") == "error":
            continue
        qs = r.get("quality_scores", {})
        print(
            f"{r.get('model', '?'):<40} "
            f"{qs.get('faithfulness', 0):>6.1f} "
            f"{qs.get('completeness', 0):>7.1f} "
            f"{qs.get('reasoning_quality', 0):>6.1f} "
            f"{qs.get('compliance', 0):>6.1f} "
            f"{r.get('report_length', 0):>6}"
        )


def _safe_mean(values: list[float]) -> float:
    """Return mean of values, or 0.0 if empty."""
    return statistics.mean(values) if values else 0.0


def print_full_report(results: list, models: list[str], tickers: list[str], data_date: str = None) -> None:
    """Print comprehensive multi-ticker report: summary, failures, per-ticker breakdown."""

    # Group results by model and by ticker
    by_model: dict[str, list[dict]] = {m: [] for m in models}
    by_ticker: dict[str, dict[str, dict]] = {t: {} for t in tickers}
    failures: list[dict] = []

    for r in results:
        model = r.get("model", "?")
        ticker = r.get("ticker", "?")
        if r.get("status") == "error":
            failures.append(r)
        else:
            if model in by_model:
                by_model[model].append(r)
            if ticker in by_ticker:
                by_ticker[ticker][model] = r

    # ── Summary by model ──
    print(f"\n{'='*100}")
    print(f"SUMMARY BY MODEL (avg across {len(tickers)} tickers)"
          f"{f'  —  data_date: {data_date}' if data_date else ''}")
    print(f"{'='*100}")

    header = (f"{'Model':<35} {'N':>3} {'Comp%':>7} {'Faith':>7} {'Complete':>8} "
              f"{'Reason':>7} {'Comply':>7} {'Cost':>8} {'Time':>6}")
    print(header)
    print("-" * 100)

    for model in models:
        model_results = by_model[model]
        n = len(model_results)
        if n == 0:
            print(f"{model:<35} {0:>3}   (no successful results)")
            continue

        avg_comp = _safe_mean([r.get("placeholder_compliance", 0) for r in model_results])
        avg_faith = _safe_mean([r.get("quality_scores", {}).get("faithfulness", 0) for r in model_results])
        avg_complete = _safe_mean([r.get("quality_scores", {}).get("completeness", 0) for r in model_results])
        avg_reason = _safe_mean([r.get("quality_scores", {}).get("reasoning_quality", 0) for r in model_results])
        avg_comply = _safe_mean([r.get("quality_scores", {}).get("compliance", 0) for r in model_results])
        avg_cost = _safe_mean([r.get("api_costs", {}).get("llm_estimated", 0) for r in model_results])
        avg_time = _safe_mean([r.get("wall_time_s", 0) for r in model_results])

        print(
            f"{model:<35} {n:>3} "
            f"{avg_comp:>6.1f}% "
            f"{avg_faith:>7.1f} "
            f"{avg_complete:>8.1f} "
            f"{avg_reason:>7.1f} "
            f"{avg_comply:>7.1f} "
            f"${avg_cost:>6.4f} "
            f"{avg_time:>5.0f}s"
        )

    # ── Failures ──
    print(f"\n{'='*100}")
    print(f"FAILURES ({len(failures)} of {len(results)} invocations)")
    print(f"{'='*100}")

    if not failures:
        print("  (none)")
    else:
        for r in failures:
            error_msg = r.get("error", "unknown error")
            if isinstance(error_msg, dict):
                error_msg = json.dumps(error_msg)[:80]
            else:
                error_msg = str(error_msg)[:80]
            print(f"  {r.get('ticker', '?'):<12} × {r.get('model', '?'):<35} {error_msg}")

    # ── Per-ticker breakdown ──
    # Build short model labels for column headers
    model_short = {}
    for m in models:
        # "anthropic/claude-sonnet-4" -> "Sonnet4"
        name = m.split("/")[-1]
        model_short[m] = name[:10]

    print(f"\n{'='*100}")
    print(f"PER-TICKER BREAKDOWN")
    print(f"{'='*100}")

    col_headers = "  ".join(f"{model_short[m]:>10}" for m in models)
    header = f"{'Ticker':<12} {'Best Model (compliance)':<35} {'Comp%':>6}  {col_headers}"
    print(header)
    print("-" * (60 + 12 * len(models)))

    for ticker in tickers:
        ticker_models = by_ticker.get(ticker, {})
        if not ticker_models:
            print(f"{ticker:<12} {'(all failed)':<35}")
            continue

        # Find best model by compliance for this ticker
        best_model = max(ticker_models, key=lambda m: ticker_models[m].get("placeholder_compliance", 0))
        best_comp = ticker_models[best_model].get("placeholder_compliance", 0)

        # Per-model compliance columns
        cols = []
        for m in models:
            r = ticker_models.get(m)
            if r is None:
                cols.append(f"{'FAIL':>10}")
            else:
                cols.append(f"{r.get('placeholder_compliance', 0):>9.1f}%")

        col_str = "  ".join(cols)
        print(f"{ticker:<12} {best_model:<35} {best_comp:>5.1f}%  {col_str}")

    # ── Totals ──
    successful = [r for r in results if r.get("status") != "error"]
    total_cost = sum(r.get("api_costs", {}).get("llm_estimated", 0) for r in successful)
    total_time = max((r.get("wall_time_s", 0) for r in results), default=0)
    print(f"\nTotal: {len(results)} invocations, {len(successful)} succeeded, "
          f"{len(failures)} failed | Est. cost: ${total_cost:.2f} | Wall time: {total_time:.0f}s")


def main():
    parser = argparse.ArgumentParser(description="Compare LLM models for placeholder compliance")
    parser.add_argument("--ticker", default="DBS19", help="Ticker to test (default: DBS19)")
    parser.add_argument("--all-tickers", action="store_true",
                        help="Run ALL tickers from data/tickers.csv (overrides --ticker)")
    parser.add_argument("--date", default=None, help="Data date YYYY-MM-DD (required if today's data not yet available)")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model IDs")
    parser.add_argument("--max-workers", type=int, default=20,
                        help="Max parallel Lambda invocations (default: 20, avoids Aurora connection exhaustion)")
    parser.add_argument("--include-report-data", action="store_true",
                        help="Include full report text and scoring context in output (for re-scoring)")
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--function", default=LAMBDA_FUNCTION)
    args = parser.parse_args()

    models = args.models.split(",")

    # Resolve tickers
    if args.all_tickers:
        csv_path = os.path.normpath(TICKERS_CSV)
        tickers = load_tickers_from_csv(csv_path)
        if not tickers:
            raise SystemExit(f"No tickers found in {csv_path}")
    else:
        tickers = [args.ticker]

    from botocore.config import Config
    client = boto3.client("lambda", region_name=args.region, config=Config(read_timeout=300))

    combinations = [(ticker, model) for ticker in tickers for model in models]
    max_workers = min(args.max_workers, len(combinations))

    print(f"Tickers:   {len(tickers)} {'(all from tickers.csv)' if args.all_tickers else tickers}")
    print(f"Data date: {args.date or '(today)'}")
    print(f"Models:    {models}")
    print(f"Lambda:    {args.function}")
    print(f"Workers:   {max_workers}")
    print(f"Total:     {len(combinations)} invocations ({len(tickers)} tickers × {len(models)} models)")
    print(f"\nInvoking {len(combinations)} Lambda(s) with max {max_workers} parallel...")

    results = []
    completed = 0
    start_all = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(invoke_experiment, client, args.function, ticker, model, args.date,
                        args.include_report_data): (ticker, model)
            for ticker, model in combinations
        }
        for future in as_completed(futures):
            ticker, model = futures[future]
            completed += 1
            try:
                result = future.result()
                results.append(result)
                status = result.get("status", "?")
                if status == "error":
                    print(f"  [{completed}/{len(combinations)}] FAILED: {ticker} × {model} -> "
                          f"{str(result.get('error', ''))[:60]}")
                else:
                    compliance = result.get("placeholder_compliance", "?")
                    print(f"  [{completed}/{len(combinations)}] Done: {ticker} × {model} -> "
                          f"compliance={compliance}%")
            except Exception as e:
                results.append({
                    "model": model,
                    "ticker": ticker,
                    "status": "error",
                    "error": str(e),
                })
                print(f"  [{completed}/{len(combinations)}] FAILED: {ticker} × {model} -> {e}")

    wall_total = time.time() - start_all
    print(f"\nAll invocations completed in {wall_total:.0f}s")

    # Sort by model order then ticker order
    model_order = {m: i for i, m in enumerate(models)}
    ticker_order = {t: i for i, t in enumerate(tickers)}
    results.sort(key=lambda r: (
        ticker_order.get(r.get("ticker", ""), 999),
        model_order.get(r.get("model", ""), 999),
    ))

    # Print report
    if args.all_tickers:
        print_full_report(results, models, tickers, data_date=args.date)
    else:
        print_single_ticker_comparison(results, data_date=args.date)

    # Save results
    out_path = "/tmp/experiment_full_results.json" if args.all_tickers else "/tmp/model_comparison.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results: {out_path}")


if __name__ == "__main__":
    main()
