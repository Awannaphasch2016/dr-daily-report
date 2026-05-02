"""Generation Lambda Handler — LLM report generation phase.

Reads raw data from S3, runs the selected generation strategy (single_pass),
and returns report text with {PLACEHOLDERS} still present.

Follows quant_agent_handler.py pattern: lazy imports, minimal config validation.

Input event (from Step Functions):
    {s3_key, ticker, dr_symbol, generation_strategy, model?, execution_id}

Output:
    {report_text, strategy_performance, api_costs, timing_ms, generation_mode}
"""

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)


def _validate_required_config() -> None:
    """Validate required environment variables. Fail fast."""
    required_vars = {
        'OPENROUTER_API_KEY': 'LLM report generation',
        'DATA_LAKE_BUCKET': 'S3 intermediate payload read',
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"All {len(required_vars)} required env vars present")


def handler(event: dict, context: Any) -> dict:
    """Generation Lambda handler — generate report from raw data.

    Args:
        event: {s3_key, ticker, dr_symbol, generation_strategy, model?, execution_id}
        context: Lambda context

    Returns:
        {report_text, strategy_performance, api_costs, timing_ms, generation_mode, status}
    """
    start_time = time.perf_counter()
    ticker = event.get('ticker', 'UNKNOWN')
    dr_symbol = event.get('dr_symbol', ticker)
    s3_key = event.get('s3_key')
    generation_strategy = event.get('generation_strategy', 'single_pass')

    if not s3_key:
        raise ValueError("Missing 's3_key' field in event")

    logger.info(
        f"Generation handler invoked | ticker={ticker} | "
        f"strategy={generation_strategy} | s3_key={s3_key}"
    )

    _validate_required_config()

    # Read raw data from S3
    from src.pipeline.s3_payload import read_payload
    raw_data = read_payload(s3_key)

    # Lazy imports for cold start optimization
    from langchain_openai import ChatOpenAI
    from src.analysis.market_analyzer import MarketAnalyzer
    from src.analysis.technical_analysis import TechnicalAnalyzer
    from src.analysis import StrategyAnalyzer
    from src.report.context_builder import ContextBuilder
    from src.report.prompt_builder import PromptBuilder
    from src.formatters import DataFormatter

    model = event.get('model') or os.getenv('LLM_MODEL', 'openai/gpt-4o')
    api_key = os.getenv('OPENROUTER_API_KEY')

    llm = ChatOpenAI(
        model=model,
        temperature=0.8,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    market_analyzer = MarketAnalyzer()
    technical_analyzer = TechnicalAnalyzer()
    data_formatter = DataFormatter()
    strategy_analyzer = StrategyAnalyzer()
    context_builder = ContextBuilder(market_analyzer, data_formatter, technical_analyzer)
    prompt_builder = PromptBuilder(context_builder=context_builder)

    # Get Langfuse handler if available
    langfuse_handler = None
    try:
        from src.integrations.langfuse_client import get_langchain_handler
        langfuse_handler = get_langchain_handler()
    except Exception:
        pass

    # Run generation strategy
    if generation_strategy == 'single_pass':
        from src.pipeline.single_pass_strategy import generate_single_pass

        result = generate_single_pass(
            raw_data=raw_data,
            llm=llm,
            context_builder=context_builder,
            prompt_builder=prompt_builder,
            strategy_analyzer=strategy_analyzer,
            market_analyzer=market_analyzer,
            langfuse_handler=langfuse_handler,
        )
    else:
        raise ValueError(f"Unknown generation_strategy: {generation_strategy}")

    # Validate report
    report_text = result.get('report_text', '')
    if not report_text or len(report_text.strip()) == 0:
        raise RuntimeError(f"Generation produced empty report for {ticker}")

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Build api_costs dict matching CostScorer format
    from src.scoring.cost_scorer import CostScorer
    cost_scorer = CostScorer()
    api_costs = cost_scorer.calculate_api_cost(
        result['total_input_tokens'],
        result['total_output_tokens'],
        actual_cost_usd=None,
    )

    logger.info(
        f"Generation complete | ticker={ticker} | strategy={generation_strategy} | "
        f"report_length={len(report_text)} | timing={elapsed_ms:.0f}ms"
    )

    return {
        'report_text': report_text,
        'strategy_performance': result.get('strategy_performance', {}),
        'api_costs': api_costs,
        'timing_ms': round(elapsed_ms, 1),
        'generation_mode': generation_strategy,
        'llm_calls': result.get('llm_calls', 1),
        'model': model,
        'status': 'success',
    }
