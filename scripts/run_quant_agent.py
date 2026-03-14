#!/usr/bin/env python
"""Run QuantAgent inner loop locally for a ticker.

Usage:
    python scripts/run_quant_agent.py D05.SI
    python scripts/run_quant_agent.py D05.SI --from-file /tmp/raw_data.json
    python scripts/run_quant_agent.py D05.SI --save-data /tmp/raw_data.json

Modes:
    Default:      Reconstruct raw_data from Aurora tables (no external API calls)
    --from-file:  Load raw_data from JSON file (fastest, no DB needed)
    --save-data:  Fetch from Aurora + save to file for reuse
"""

import argparse
import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s | %(message)s",
)
logger = logging.getLogger("run_quant_agent")


def collect_data_from_aurora(ticker: str) -> dict:
    """Reconstruct raw_data from Aurora tables (no external API calls).

    Uses:
    - precomputed_reports.report_json -> ticker_data (price history + fundamentals)
    - daily_indicators -> indicators
    - indicator_percentiles -> percentiles
    - news_items from report_json -> news
    """
    from datetime import date, datetime
    from zoneinfo import ZoneInfo

    from src.workflow.aurora_data_adapter import fetch_ticker_data_from_aurora
    from src.analysis.technical_analysis import TechnicalAnalyzer
    from src.data.aurora.client import get_aurora_client
    from src.data.aurora.table_names import PRECOMPUTED_REPORTS

    logger.info(f"Reconstructing raw_data from Aurora for {ticker}...")
    start = time.perf_counter()

    # 1. Get ticker_data (price history + fundamentals) from report_json
    ticker_data = fetch_ticker_data_from_aurora(ticker)

    # 2. Compute indicators from price history
    technical_analyzer = TechnicalAnalyzer()
    hist_df = ticker_data.get("history")
    if hist_df is None or hist_df.empty:
        raise ValueError(f"No price history for {ticker}")

    indicators = technical_analyzer.calculate_all_indicators(hist_df)
    if not indicators:
        raise ValueError(f"Failed to calculate indicators for {ticker}")
    indicators["current_price"] = ticker_data.get("close", 0)

    # 3. Calculate percentiles from indicators
    percentiles = technical_analyzer.calculate_percentiles(hist_df, indicators)

    # 4. Extract news from report_json
    client = get_aurora_client()
    row = client.fetch_one(
        f"SELECT report_json FROM {PRECOMPUTED_REPORTS} "
        f"WHERE symbol = %s AND status = 'completed' "
        f"ORDER BY report_date DESC LIMIT 1",
        (ticker,),
    )
    news = []
    news_summary = {}
    comparative_insights = {}
    if row:
        report = json.loads(row["report_json"])
        news_items = report.get("news_items", [])
        # Convert report_json news format to raw news format
        for item in news_items:
            news.append({
                "title": item.get("headline", item.get("title", "")),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "published": item.get("date", item.get("published", "")),
                "summary": item.get("summary", ""),
            })
        # Extract peers/comparative from report_json
        peers = report.get("peers", [])
        if peers:
            comparative_insights = {"peers": peers}

    elapsed = time.perf_counter() - start
    logger.info(f"Data reconstruction done in {elapsed:.1f}s "
                f"(indicators={len(indicators)}, news={len(news)})")

    return {
        "ticker": ticker,
        "ticker_data": ticker_data,
        "indicators": indicators,
        "percentiles": percentiles,
        "chart_patterns": [],
        "pattern_statistics": {},
        "strategy_performance": {},
        "news": news,
        "news_summary": news_summary,
        "comparative_data": {},
        "comparative_insights": comparative_insights,
        "sec_filing_data": {},
        "financial_markets_data": {},
        "portfolio_insights": {},
        "alpaca_data": {},
    }


def run_quant_agent(raw_data: dict) -> None:
    """Instantiate and run QuantAgent inner loop, print results."""
    from langchain_openai import ChatOpenAI
    from src.quant_agent.config import QuantAgentConfig
    from src.quant_agent.inner_loop import QuantAgentReportGenerator
    from src.analysis.market_analyzer import MarketAnalyzer
    from src.analysis.technical_analysis import TechnicalAnalyzer
    from src.report.context_builder import ContextBuilder
    from src.report.prompt_builder import PromptBuilder
    from src.report.number_injector import NumberInjector
    from src.scoring.scoring_service import ScoringService
    from src.formatters import DataFormatter

    config = QuantAgentConfig.from_env()
    api_key = os.getenv("OPENROUTER_API_KEY")

    logger.info(
        f"QuantAgent config: writer={config.writer_model}, "
        f"judge={config.deep_judge_model}, beta={config.beta}, "
        f"max_iter={config.max_iterations}"
    )

    llm = ChatOpenAI(
        model=config.writer_model,
        temperature=0.8,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    market_analyzer = MarketAnalyzer()
    context_builder = ContextBuilder(
        market_analyzer, DataFormatter(), TechnicalAnalyzer()
    )
    prompt_builder = PromptBuilder(context_builder=context_builder)

    generator = QuantAgentReportGenerator(
        llm=llm,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        number_injector=NumberInjector(),
        scoring_service=ScoringService(enable_llm_scoring=False),
        market_analyzer=market_analyzer,
        config=config,
    )

    result = generator.generate(raw_data)

    print()
    print(result.report)
    print()
    print("=" * 60)
    print(f"Score: {result.aggregate_score:.1f}/100")
    print(f"Iterations: {result.iterations_used}/{config.max_iterations}")
    print(f"Timing: {result.timing_ms:.0f}ms")
    print(f"Tokens: {result.total_input_tokens}in / {result.total_output_tokens}out")
    print(f"Per-iteration: {result.per_iteration_scores}")
    print(f"Quality: {result.quality_scores}")


def _serialize_for_json(obj):
    """Handle non-JSON-serializable types (DataFrame, numpy, etc.)."""
    import pandas as pd
    import numpy as np

    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def main():
    parser = argparse.ArgumentParser(description="Run QuantAgent inner loop locally")
    parser.add_argument("ticker", help="Ticker symbol (e.g., D05.SI)")
    parser.add_argument("--from-file", help="Load raw_data from JSON file (skip Aurora)")
    parser.add_argument("--save-data", help="Save raw_data to JSON file for reuse")
    args = parser.parse_args()

    ticker = args.ticker

    # Get raw_data
    if args.from_file:
        logger.info(f"Loading raw_data from {args.from_file}")
        with open(args.from_file) as f:
            raw_data = json.load(f)
        raw_data.setdefault("ticker", ticker)
    else:
        raw_data = collect_data_from_aurora(ticker)

    # Optionally save for reuse
    if args.save_data:
        logger.info(f"Saving raw_data to {args.save_data}")
        with open(args.save_data, "w") as f:
            json.dump(raw_data, f, default=_serialize_for_json)
        logger.info(f"Saved to {args.save_data}")

    # Run QuantAgent
    run_quant_agent(raw_data)


if __name__ == "__main__":
    main()
