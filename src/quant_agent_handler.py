"""QuantAgent Report Generation Lambda Handler

Processes report generation using the multi-agent Writer/Judge inner loop.
Invoked by report_worker Lambda when REPORT_GENERATION_MODE=quant_agent.

Flow:
1. Receive pre-computed raw_data (from report_worker data pipeline)
2. Run QuantAgent inner loop (Writer generates → Judge scores → Writer revises)
3. Return best report with quality scores
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger().setLevel(logging.INFO)


def _validate_required_config() -> None:
    """Validate required environment variables at startup.

    Principle #1: Defensive Programming — fail fast on missing config.
    """
    required_vars = {
        "OPENROUTER_API_KEY": "LLM report generation (Writer + DeepJudge)",
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
    """Lambda handler for QuantAgent report generation.

    Event structure (from report_worker delegation):
    {
        "raw_data": {
            "ticker": "DBS19",
            "ticker_data": {...},
            "indicators": {...},
            "percentiles": {...},
            "news": [...],
            ...
        },
        "ticker": "DBS19",
        "source": "report_worker"
    }

    Returns:
    {
        "report": "...",
        "quality_scores": {...},
        "aggregate_score": 78.5,
        "iterations_used": 2,
        "generation_mode": "quant_agent",
        "total_input_tokens": 12000,
        "total_output_tokens": 800,
        "timing_ms": 15234.5,
        "per_iteration_scores": [...],
        "status": "success"
    }
    """
    ticker = event.get("ticker", "UNKNOWN")
    logger.info(
        f"QuantAgent handler invoked | ticker={ticker} | "
        f"source={event.get('source', 'unknown')}"
    )

    _validate_required_config()

    raw_data = event.get("raw_data")
    if not raw_data:
        error_msg = "Event missing 'raw_data' field"
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg, "ticker": ticker}

    # Ensure ticker is in raw_data
    if "ticker" not in raw_data:
        raw_data["ticker"] = ticker

    try:
        # Lazy imports to keep cold start fast for validation failures
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

        llm = ChatOpenAI(
            model=config.writer_model,
            temperature=0.8,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        market_analyzer = MarketAnalyzer()
        technical_analyzer = TechnicalAnalyzer()
        data_formatter = DataFormatter()
        context_builder = ContextBuilder(market_analyzer, data_formatter, technical_analyzer)
        prompt_builder = PromptBuilder(context_builder=context_builder)
        number_injector = NumberInjector()
        scoring_service = ScoringService(enable_llm_scoring=False)

        generator = QuantAgentReportGenerator(
            llm=llm,
            context_builder=context_builder,
            prompt_builder=prompt_builder,
            number_injector=number_injector,
            scoring_service=scoring_service,
            market_analyzer=market_analyzer,
            config=config,
        )

        # Get Langfuse handler if available
        langfuse_handler = None
        try:
            from src.integrations.langfuse_client import get_langchain_handler
            langfuse_handler = get_langchain_handler()
        except Exception:
            pass

        result = generator.generate(raw_data, langfuse_handler=langfuse_handler)

        logger.info(
            f"QuantAgent complete | ticker={ticker} | "
            f"score={result.aggregate_score:.1f} | "
            f"iterations={result.iterations_used} | "
            f"timing={result.timing_ms:.0f}ms"
        )

        return {
            "report": result.report,
            "quality_scores": result.quality_scores,
            "aggregate_score": result.aggregate_score,
            "iterations_used": result.iterations_used,
            "generation_mode": result.generation_mode,
            "total_input_tokens": result.total_input_tokens,
            "total_output_tokens": result.total_output_tokens,
            "timing_ms": result.timing_ms,
            "per_iteration_scores": result.per_iteration_scores,
            "status": "success",
            "ticker": ticker,
        }

    except Exception as e:
        error_msg = f"QuantAgent failed for {ticker}: {e}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "ticker": ticker,
            "generation_mode": "quant_agent",
        }
