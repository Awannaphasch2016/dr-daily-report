#!/usr/bin/env python
"""Re-score experiment reports locally with variant analysis.

Compares scoring of a report with all placeholders injected vs.
a "broken Bollinger" variant where Bollinger values are replaced
back with unresolved placeholders.

Usage:
    # From saved experiment JSON (must have been run with --include-report-data)
    python scripts/rescore_experiment.py --input /tmp/model_comparison.json

    # Direct Lambda invocation (includes report data automatically)
    python scripts/rescore_experiment.py --ticker SGX19 --date 2026-03-16 \
        --model anthropic/claude-opus-4

    # Skip consistency scorer (avoids LLM cost)
    python scripts/rescore_experiment.py --input /tmp/model_comparison.json --skip-consistency
"""

import argparse
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Prevent src/scoring/__init__.py from importing ConsistencyScorer
# which pulls langchain_openai → langchain_core → transformers → torch (broken locally)
import importlib
import types
_scoring_pkg = types.ModuleType('src.scoring')
_scoring_pkg.__path__ = [os.path.join(os.path.dirname(__file__), '..', 'src', 'scoring')]
_scoring_pkg.__package__ = 'src.scoring'
sys.modules['src.scoring'] = _scoring_pkg


def load_experiment_data(input_path: str) -> dict:
    """Load experiment data from JSON file."""
    with open(input_path) as f:
        data = json.load(f)
    # Handle list format (experiment_model_comparison saves as list)
    if isinstance(data, list):
        if len(data) == 1:
            data = data[0]
        else:
            # Pick first successful result
            for d in data:
                if d.get('status') == 'success' and d.get('report_text'):
                    data = d
                    break
            else:
                raise ValueError("No successful results with report_text found")
    if 'report_text' not in data:
        raise ValueError(
            "Missing report_text. Re-run experiment with --include-report-data flag:\n"
            "  python scripts/experiment_model_comparison.py --ticker SGX19 "
            "--date 2026-03-16 --models anthropic/claude-opus-4 --include-report-data"
        )
    if 'scoring_context' not in data:
        raise ValueError("Missing scoring_context in experiment data")
    return data


def invoke_experiment_with_data(ticker: str, model: str, date: str,
                                function: str, region: str) -> dict:
    """Invoke Lambda experiment with include_report_data=true."""
    import boto3
    from botocore.config import Config

    client = boto3.client("lambda", region_name=region, config=Config(read_timeout=300))
    payload = {
        "experiment": True,
        "ticker": ticker,
        "model": model,
        "data_date": date,
        "include_report_data": True,
    }
    print(f"Invoking Lambda {function} for {ticker} (this takes ~3 min)...")
    response = client.invoke(
        FunctionName=function,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    result = json.loads(response["Payload"].read())
    if result.get('status') == 'error':
        raise RuntimeError(f"Experiment failed: {result.get('error')}")
    if 'report_text' not in result:
        raise RuntimeError("Lambda returned no report_text — check include_report_data support")
    return result


def create_broken_bollinger_variant(report_text: str, indicators: dict) -> tuple:
    """Replace resolved Bollinger values with unresolved placeholders.

    Returns (broken_text, replacements_made).
    """
    bollinger_map = {
        'bb_upper': '{BOLLINGER_UPPER}',
        'bb_lower': '{BOLLINGER_LOWER}',
        'bb_middle': '{BOLLINGER_MIDDLE}',
    }
    broken = report_text
    replacements_made = []
    for source_key, placeholder in bollinger_map.items():
        value = indicators.get(source_key)
        if value is not None and float(value) > 0:
            formatted = f"{float(value):.2f}"
            if formatted in broken:
                broken = broken.replace(formatted, placeholder)
                replacements_made.append(f"  {formatted} → {placeholder}")
    return broken, replacements_made


def score_report(report_text: str, context, skip_consistency: bool = False):
    """Score a report using individual scorers directly. Returns dict of {name: {overall, sub_scores}}.

    Imports scorers individually to avoid the heavy __init__.py chain
    (which pulls in torch via transformers via langchain).
    """
    from src.scoring.faithfulness_scorer import FaithfulnessScorer
    from src.scoring.completeness_scorer import CompletenessScorer
    from src.scoring.reasoning_quality_scorer import ReasoningQualityScorer
    from src.scoring.compliance_scorer import ComplianceScorer

    indicators = context.indicators
    percentiles = context.percentiles
    news = context.news
    ticker_data = context.ticker_data

    ground_truth = {
        'uncertainty_score': indicators.get('uncertainty_score', 0),
        'atr_pct': context.market_conditions.get('atr_pct', 0),
        'vwap_pct': context.market_conditions.get('price_vs_vwap_pct', 0),
        'volume_ratio': context.market_conditions.get('volume_ratio', 0),
    }

    raw_scores = {}
    raw_scores['faithfulness'] = FaithfulnessScorer().score_narrative(
        report_text, ground_truth, indicators, percentiles, news, ticker_data)
    raw_scores['completeness'] = CompletenessScorer().score_narrative(
        report_text, ticker_data, indicators, percentiles, news)
    raw_scores['reasoning_quality'] = ReasoningQualityScorer().score_narrative(
        report_text, indicators, percentiles, ticker_data)
    raw_scores['compliance'] = ComplianceScorer().score_narrative(
        report_text, indicators, news)

    if not skip_consistency:
        try:
            from src.scoring.consistency_scorer import ConsistencyScorer
            raw_scores['consistency'] = ConsistencyScorer().score_narrative(
                report_text, indicators, percentiles,
                context.market_conditions, ticker_data)
        except Exception as e:
            print(f"  ⚠️ Consistency scorer failed: {e}")

    results = {}
    for name, score_obj in raw_scores.items():
        entry = {'overall': score_obj.overall_score}
        sub = getattr(score_obj, 'dimension_scores', None) or getattr(score_obj, 'metric_scores', None)
        if sub:
            entry['sub_scores'] = {k: round(v, 2) for k, v in sub.items()}
        results[name] = entry
    return results


def print_comparison(scores_fixed: dict, scores_broken: dict, experiment_scores: dict,
                     replacements: list):
    """Print formatted comparison table."""
    print()
    print("=" * 72)
    print("VALIDATION GATE (re-scored Fixed must ≈ experiment scores)")
    print("=" * 72)
    print(f"{'Scorer':<22} {'Experiment':>10} {'Fixed(A)':>10} {'Match':>8}")
    print("-" * 72)

    all_match = True
    for name in scores_fixed:
        exp_val = experiment_scores.get(name, 0)
        fix_val = scores_fixed[name]['overall']
        delta = abs(fix_val - exp_val) if exp_val else 0
        match = "✅" if delta <= 0.5 else "⚠️"
        if delta > 0.5:
            all_match = False
        print(f"  {name:<20} {exp_val:>10.1f} {fix_val:>10.1f} {match:>8}")

    if all_match:
        print("→ Pipeline validated ✅ (all scores match within ±0.5)")
    else:
        print("→ ⚠️  Some scores differ — investigate before trusting deltas")

    print()
    print("=" * 72)
    print("BOLLINGER FIX IMPACT (Fixed - Broken)")
    print("=" * 72)
    print(f"{'Scorer':<22} {'Fixed(A)':>10} {'Broken(B)':>10} {'Delta':>8}")
    print("-" * 72)

    for name in scores_fixed:
        fix_val = scores_fixed[name]['overall']
        brk_val = scores_broken[name]['overall']
        delta = fix_val - brk_val
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        print(f"  {name:<20} {fix_val:>10.1f} {brk_val:>10.1f} {delta_str:>8}")

        # Print sub-scores if available
        fix_sub = scores_fixed[name].get('sub_scores', {})
        brk_sub = scores_broken[name].get('sub_scores', {})
        all_sub_keys = sorted(set(list(fix_sub.keys()) + list(brk_sub.keys())))
        for sk in all_sub_keys:
            fv = fix_sub.get(sk, 0)
            bv = brk_sub.get(sk, 0)
            sd = fv - bv
            sd_str = f"+{sd:.1f}" if sd >= 0 else f"{sd:.1f}"
            marker = " ***" if abs(sd) > 0.5 else ""
            print(f"    {sk:<18} {fv:>10.1f} {bv:>10.1f} {sd_str:>8}{marker}")

    if replacements:
        print()
        print("Bollinger values replaced in Broken variant:")
        for r in replacements:
            print(r)


def main():
    parser = argparse.ArgumentParser(description="Re-score experiment reports with variant analysis")
    parser.add_argument("--input", help="Path to experiment JSON (from --include-report-data run)")
    parser.add_argument("--ticker", help="Ticker for direct Lambda invocation")
    parser.add_argument("--model", default="anthropic/claude-opus-4")
    parser.add_argument("--date", help="Data date YYYY-MM-DD")
    parser.add_argument("--skip-consistency", action="store_true",
                        help="Skip LLM-based consistency scorer (saves cost)")
    parser.add_argument("--function", default="dr-daily-report-report-worker-dev")
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    # Load or invoke
    if args.input:
        data = load_experiment_data(args.input)
        print(f"Loaded experiment data from {args.input}")
    elif args.ticker and args.date:
        data = invoke_experiment_with_data(
            args.ticker, args.model, args.date, args.function, args.region)
        # Save for reuse
        out_path = "/tmp/experiment_with_report.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved experiment data to {out_path}")
    else:
        parser.error("Provide --input or (--ticker and --date)")

    report_text = data['report_text']
    experiment_scores = data.get('quality_scores', {})

    print(f"Ticker: {data.get('ticker', '?')}, Date: {data.get('data_date', '?')}")
    print(f"Report length: {len(report_text)} chars")
    print(f"Experiment scores: {experiment_scores}")

    # Reconstruct ScoringContext
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class ScoringContext:
        indicators: dict
        percentiles: dict
        news: list
        ticker_data: dict
        market_conditions: dict
        comparative_insights: Optional[dict] = None

    sc = data['scoring_context']
    context = ScoringContext(**sc)

    # Create broken Bollinger variant
    broken_text, replacements = create_broken_bollinger_variant(report_text, context.indicators)
    if not replacements:
        print("⚠️  No Bollinger values found in report text — nothing to compare")
        return
    print(f"Created broken variant: {len(replacements)} Bollinger value(s) replaced")

    # Score both variants
    print("Scoring fixed variant...")
    scores_fixed = score_report(report_text, context, skip_consistency=args.skip_consistency)
    print("Scoring broken variant...")
    scores_broken = score_report(broken_text, context, skip_consistency=args.skip_consistency)

    # Print comparison
    print_comparison(scores_fixed, scores_broken, experiment_scores, replacements)

    # Save results
    out = {
        'ticker': data.get('ticker'),
        'data_date': data.get('data_date'),
        'experiment_scores': experiment_scores,
        'scores_fixed': scores_fixed,
        'scores_broken': scores_broken,
        'bollinger_values': {
            k: float(context.indicators[k])
            for k in ['bb_upper', 'bb_lower', 'bb_middle']
            if k in context.indicators
        },
        'replacements': replacements,
    }
    out_path = "/tmp/rescore_comparison.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nFull results: {out_path}")


if __name__ == "__main__":
    main()
