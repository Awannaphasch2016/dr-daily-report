"""Single-pass report generation strategy.

Extracted from WorkflowNodes._generate_report_singlestage() to be importable
by both the old monolithic path and the new pipeline Generation Lambda.

Performs:
1. Ground truth calculation
2. Context building (Layer 2 semantic states)
3. Prompt building
4. LLM invocation (first pass)
5. Strategy filtering + optional second pass
6. Returns report text with {PLACEHOLDERS} still present (no number injection)
"""

import logging
import time

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def generate_single_pass(
    raw_data: dict,
    llm,
    context_builder,
    prompt_builder,
    strategy_analyzer,
    market_analyzer,
    langfuse_handler=None,
) -> dict:
    """Generate a report using single-pass (with optional second pass for strategies).

    This is a pure function: takes raw data + dependencies, returns report + metadata.
    Does NOT perform post-processing (number injection, scoring, etc.).

    Args:
        raw_data: Dict with RAW_DATA_FIELDS (ticker, ticker_data, indicators, etc.)
        llm: LangChain ChatOpenAI instance
        context_builder: ContextBuilder instance
        prompt_builder: PromptBuilder instance
        strategy_analyzer: StrategyAnalyzer instance
        market_analyzer: MarketAnalyzer instance
        langfuse_handler: Optional LangChain callback handler for tracing

    Returns:
        {
            'report_text': str,  # Report with {PLACEHOLDERS} (pre-injection)
            'strategy_performance': dict,  # Possibly filtered supporting strategies
            'total_input_tokens': int,
            'total_output_tokens': int,
            'llm_calls': int,
            'timing_ms': float,
        }
    """
    start_time = time.perf_counter()

    ticker = raw_data["ticker"]
    ticker_data = raw_data.get("ticker_data", {})
    indicators = raw_data.get("indicators", {})
    percentiles = raw_data.get("percentiles", {})
    strategy_performance = raw_data.get("strategy_performance", {})
    news = raw_data.get("news", [])
    news_summary = raw_data.get("news_summary", {})
    comparative_insights = raw_data.get("comparative_insights", {})
    sec_filing_data = raw_data.get("sec_filing_data", {})
    financial_markets_data = raw_data.get("financial_markets_data", {})
    portfolio_insights = raw_data.get("portfolio_insights", {})
    alpaca_data = raw_data.get("alpaca_data", {})

    total_input_tokens = 0
    total_output_tokens = 0
    llm_calls = 0

    # Layer 1: Ground truth calculation
    conditions = market_analyzer.calculate_market_conditions(indicators)
    ground_truth = {
        'uncertainty_score': indicators.get('uncertainty_score', 0),
        'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                   if indicators.get('current_price', 0) > 0 else 0,
        'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
        'volume_ratio': conditions.get('volume_ratio', 0),
    }

    # Layer 2+3: First pass — generate without strategy data
    context = context_builder.prepare_context(
        ticker, ticker_data, indicators, percentiles, news, news_summary,
        ground_truth=ground_truth,
        strategy_performance=None,
        comparative_insights=comparative_insights,
        sec_filing_data=sec_filing_data,
        financial_markets_data=financial_markets_data,
        portfolio_insights=portfolio_insights,
        alpaca_data=alpaca_data
    )
    prompt = prompt_builder.build_prompt(
        ticker, context,
        ground_truth=ground_truth,
        indicators=indicators,
        percentiles=percentiles,
        ticker_data=ticker_data,
        strategy_performance=None,
        comparative_insights=comparative_insights,
        sec_filing_data=sec_filing_data,
        financial_markets_data=financial_markets_data,
        portfolio_insights=portfolio_insights,
        alpaca_data=alpaca_data
    )

    invoke_config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}

    response = llm.invoke([HumanMessage(content=prompt)], config=invoke_config)
    initial_report = response.content
    llm_calls += 1

    # Extract token usage
    response_metadata = getattr(response, 'response_metadata', {})
    usage = response_metadata.get('token_usage', {})
    if usage:
        total_input_tokens += usage.get('prompt_tokens', 0)
        total_output_tokens += usage.get('completion_tokens', 0)
    else:
        total_input_tokens += len(prompt) // 4
        total_output_tokens += len(initial_report) // 4

    # Extract recommendation and filter supporting strategies
    recommendation = strategy_analyzer.extract_recommendation(initial_report)
    supporting = strategy_analyzer.filter_supporting_strategies(recommendation, strategy_performance)
    include_strategy = supporting['support_count'] > 0

    # Second pass: regenerate with supporting strategy data
    if include_strategy:
        strategy_performance = supporting

        context_with_strategy = context_builder.prepare_context(
            ticker, ticker_data, indicators, percentiles, news, news_summary,
            ground_truth=ground_truth,
            strategy_performance=supporting,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data
        )
        prompt_with_strategy = prompt_builder.build_prompt(
            ticker, context_with_strategy,
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data,
            strategy_performance=supporting,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data
        )

        response = llm.invoke([HumanMessage(content=prompt_with_strategy)], config=invoke_config)
        report = response.content
        llm_calls += 1

        response_metadata = getattr(response, 'response_metadata', {})
        usage = response_metadata.get('token_usage', {})
        if usage:
            total_input_tokens += usage.get('prompt_tokens', 0)
            total_output_tokens += usage.get('completion_tokens', 0)
        else:
            total_input_tokens += len(prompt_with_strategy) // 4
            total_output_tokens += len(report) // 4
    else:
        report = initial_report

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        f"Single-pass generation complete | ticker={ticker} | "
        f"llm_calls={llm_calls} | tokens_in={total_input_tokens} | "
        f"tokens_out={total_output_tokens} | timing={elapsed_ms:.0f}ms"
    )

    return {
        'report_text': report,
        'strategy_performance': strategy_performance,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'llm_calls': llm_calls,
        'timing_ms': elapsed_ms,
    }
