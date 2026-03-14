"""Writer agent — generates reports using existing pipeline + feedback injection.

Wraps existing ContextBuilder, PromptBuilder, and LLM. On iteration > 1,
appends DeepJudge revision feedback to the prompt so the LLM can self-correct.
"""

import logging
import time
from typing import Optional

from langchain_core.messages import HumanMessage

from src.quant_agent.context_buffer import ContextBuffer

logger = logging.getLogger(__name__)


class Writer:
    """Generates Thai financial reports using semantic layer architecture.

    Reuses existing components without duplication:
    - ContextBuilder.prepare_context() for Layer 2 semantic context
    - PromptBuilder.build_prompt() for prompt construction with placeholders
    - LLM via ChatOpenAI (OpenRouter endpoint)

    Adds:
    - Revision feedback injection from DeepJudge on iteration > 1
    """

    def __init__(self, llm, context_builder, prompt_builder):
        self.llm = llm
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder

    def generate(
        self,
        state_data: dict,
        ground_truth: dict,
        ctx_buffer: ContextBuffer,
        target_score: float,
        langfuse_handler=None,
    ) -> tuple[str, dict]:
        """Generate a report, optionally incorporating judge feedback.

        Args:
            state_data: Raw data dict (from extract_raw_data_for_storage).
            ground_truth: Calculated market conditions for semantic states.
            ctx_buffer: Context buffer with prior iteration feedback.
            target_score: Beta threshold for revision guidance formatting.
            langfuse_handler: Optional Langfuse callback for token tracking.

        Returns:
            Tuple of (raw_report_text, token_usage_dict).
        """
        start = time.perf_counter()
        ticker = state_data["ticker"]
        ticker_data = state_data.get("ticker_data", {})
        indicators = state_data.get("indicators", {})
        percentiles = state_data.get("percentiles", {})
        news = state_data.get("news", [])
        news_summary = state_data.get("news_summary", {})
        strategy_performance = state_data.get("strategy_performance")
        comparative_insights = state_data.get("comparative_insights", {})
        sec_filing_data = state_data.get("sec_filing_data", {})
        financial_markets_data = state_data.get("financial_markets_data", {})
        portfolio_insights = state_data.get("portfolio_insights", {})
        alpaca_data = state_data.get("alpaca_data", {})

        # 1. Build standard prompt (EXISTING pipeline, unchanged)
        context = self.context_builder.prepare_context(
            ticker, ticker_data, indicators, percentiles, news, news_summary,
            ground_truth=ground_truth,
            strategy_performance=strategy_performance,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data,
        )
        prompt = self.prompt_builder.build_prompt(
            ticker, context,
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data,
            strategy_performance=strategy_performance,
            comparative_insights=comparative_insights,
            sec_filing_data=sec_filing_data,
            financial_markets_data=financial_markets_data,
            portfolio_insights=portfolio_insights,
            alpaca_data=alpaca_data,
        )

        # 2. Append revision feedback from prior iteration (if any)
        if ctx_buffer.has_feedback():
            guidance = ctx_buffer.format_revision_guidance(target_score)
            prompt += f"\n\n{guidance}"
            logger.info("   Writer: appended revision guidance from DeepJudge")

        # 3. LLM call
        invoke_config = {}
        if langfuse_handler:
            invoke_config["callbacks"] = [langfuse_handler]

        response = self.llm.invoke([HumanMessage(content=prompt)], config=invoke_config)
        raw_report = response.content

        # Extract token usage
        token_usage = {}
        response_metadata = getattr(response, "response_metadata", {})
        usage = response_metadata.get("token_usage", {})
        if usage:
            token_usage["prompt_tokens"] = usage.get("prompt_tokens", 0)
            token_usage["completion_tokens"] = usage.get("completion_tokens", 0)
        else:
            token_usage["prompt_tokens"] = len(prompt) // 4
            token_usage["completion_tokens"] = len(raw_report) // 4

        elapsed = time.perf_counter() - start
        logger.info(
            f"   Writer: generated report ({len(raw_report)} chars, "
            f"{elapsed:.1f}s, {token_usage.get('prompt_tokens', 0)} in / "
            f"{token_usage.get('completion_tokens', 0)} out)"
        )

        return raw_report, token_usage
