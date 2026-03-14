"""Inner loop orchestration — Writer/Judge iteration until quality threshold.

Implements Algorithm 1 from QuantAgent (arXiv:2402.03755), adapted for
Thai financial report generation. No Knowledge Base, no outer loop.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from langchain_openai import ChatOpenAI

from src.quant_agent.config import QuantAgentConfig
from src.quant_agent.context_buffer import ContextBuffer
from src.quant_agent.writer import Writer
from src.quant_agent.judge import FastJudge, DeepJudge
from src.analysis.market_analyzer import MarketAnalyzer
from src.report.context_builder import ContextBuilder
from src.report.prompt_builder import PromptBuilder
from src.report.number_injector import NumberInjector
from src.scoring.scoring_service import ScoringService, ScoringContext

logger = logging.getLogger(__name__)


@dataclass
class InnerLoopResult:
    """Result of the QuantAgent inner loop."""
    report: str
    aggregate_score: float
    quality_scores: dict
    iterations_used: int
    generation_mode: str = "quant_agent"
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    timing_ms: float = 0.0
    per_iteration_scores: list = field(default_factory=list)


class QuantAgentReportGenerator:
    """Orchestrates the Writer/Judge inner loop for report generation.

    Flow per iteration:
    1. Writer generates report (with feedback from prior iteration if any)
    2. NumberInjector post-processes (replaces placeholders with ground truth)
    3. FastJudge scores (rule-based, ~100ms, free)
    4. If score >= beta: return best report
    5. DeepJudge reviews (LLM feedback, ~3s)
    6. Feedback added to context buffer, goto 1
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        number_injector: NumberInjector,
        scoring_service: ScoringService,
        market_analyzer: MarketAnalyzer,
        config: Optional[QuantAgentConfig] = None,
    ):
        self.config = config or QuantAgentConfig.from_env()
        self.market_analyzer = market_analyzer
        self.number_injector = number_injector

        # Writer uses the main LLM (same model as existing single-pass)
        self.writer = Writer(llm, context_builder, prompt_builder)

        # FastJudge wraps existing scoring service
        self.fast_judge = FastJudge(scoring_service)

        # DeepJudge uses a cost-efficient model for feedback
        api_key = os.getenv("OPENROUTER_API_KEY")
        self.deep_judge = DeepJudge(
            model=self.config.deep_judge_model,
            api_key=api_key,
        )

    def generate(self, state_data: dict, langfuse_handler=None) -> InnerLoopResult:
        """Run the inner loop to generate a quality-refined report.

        Args:
            state_data: Raw data dict containing ticker, indicators, ticker_data, etc.
                        (from extract_raw_data_for_storage or direct AgentState fields)
            langfuse_handler: Optional Langfuse callback for Writer LLM tracking.

        Returns:
            InnerLoopResult with the best report and metadata.
        """
        loop_start = time.perf_counter()
        ticker = state_data.get("ticker", "UNKNOWN")
        indicators = state_data.get("indicators", {})

        logger.info(
            f"QuantAgent inner loop starting for {ticker} "
            f"(beta={self.config.beta}, max_iter={self.config.max_iterations})"
        )

        # Pre-compute shared context (done once, not per iteration)
        ground_truth = self._calculate_ground_truth(indicators)
        scoring_ctx = self._build_scoring_context(state_data, indicators, ground_truth)

        ctx_buffer = ContextBuffer()
        best_report = ""
        best_score = 0.0
        best_scores = {}
        total_input_tokens = 0
        total_output_tokens = 0
        per_iteration_scores = []

        for t in range(1, self.config.max_iterations + 1):
            iter_start = time.perf_counter()

            # Check time budget
            elapsed = time.perf_counter() - loop_start
            if elapsed > self.config.timeout_budget_seconds:
                logger.warning(
                    f"   Iteration {t}: timeout budget exceeded "
                    f"({elapsed:.1f}s > {self.config.timeout_budget_seconds}s), "
                    f"returning best so far (score={best_score:.1f})"
                )
                break

            logger.info(f"   --- Iteration {t}/{self.config.max_iterations} ---")

            # 1. Writer generates report
            raw_report, token_usage = self.writer.generate(
                state_data, ground_truth, ctx_buffer,
                target_score=self.config.beta,
                langfuse_handler=langfuse_handler,
            )
            total_input_tokens += token_usage.get("prompt_tokens", 0)
            total_output_tokens += token_usage.get("completion_tokens", 0)

            # 2. Post-process: number injection + news refs + footer
            report = self._post_process(raw_report, state_data, indicators, ground_truth)

            # 3. Fast Judge: rule-based scoring
            agg_score, scores = self.fast_judge.score(report, scoring_ctx)
            per_iteration_scores.append({"iteration": t, "score": agg_score})

            # Track best
            if agg_score > best_score:
                best_report = report
                best_score = agg_score
                best_scores = scores

            iter_elapsed = time.perf_counter() - iter_start
            logger.info(
                f"   Iteration {t}: score={agg_score:.1f}/100 "
                f"(best={best_score:.1f}) [{iter_elapsed:.1f}s]"
            )

            # 4. Threshold check — good enough, stop
            if agg_score >= self.config.beta:
                logger.info(
                    f"   Score {agg_score:.1f} >= beta {self.config.beta}, "
                    f"accepting report after {t} iteration(s)"
                )
                break

            # 5. Deep Judge: LLM feedback for next iteration
            if t < self.config.max_iterations:
                feedback = self.deep_judge.review(report, state_data, scores)
                ctx_buffer.add(t, report, agg_score, feedback)

        total_elapsed = time.perf_counter() - loop_start
        logger.info(
            f"QuantAgent loop complete: {ticker} | "
            f"iterations={t} | best_score={best_score:.1f} | "
            f"tokens={total_input_tokens}in/{total_output_tokens}out | "
            f"total={total_elapsed:.1f}s"
        )

        return InnerLoopResult(
            report=best_report,
            aggregate_score=best_score,
            quality_scores=self._serialize_scores(best_scores),
            iterations_used=t,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            timing_ms=total_elapsed * 1000,
            per_iteration_scores=per_iteration_scores,
        )

    def _calculate_ground_truth(self, indicators: dict) -> dict:
        """Calculate ground truth from indicators (same as existing pipeline)."""
        conditions = self.market_analyzer.calculate_market_conditions(indicators)
        return {
            "uncertainty_score": indicators.get("uncertainty_score", 0),
            "atr_pct": (
                (indicators.get("atr", 0) / indicators.get("current_price", 1)) * 100
                if indicators.get("current_price", 0) > 0
                else 0
            ),
            "vwap_pct": conditions.get("price_vs_vwap_pct", 0),
            "volume_ratio": conditions.get("volume_ratio", 0),
        }

    def _build_scoring_context(
        self, state_data: dict, indicators: dict, ground_truth: dict
    ) -> ScoringContext:
        """Build ScoringContext for FastJudge (same as existing pipeline)."""
        return ScoringContext(
            indicators=indicators,
            percentiles=state_data.get("percentiles", {}),
            news=state_data.get("news", []),
            ticker_data=state_data.get("ticker_data", {}),
            market_conditions={
                "uncertainty_score": ground_truth["uncertainty_score"],
                "atr_pct": ground_truth["atr_pct"],
                "price_vs_vwap_pct": ground_truth["vwap_pct"],
                "volume_ratio": ground_truth["volume_ratio"],
            },
            comparative_insights=state_data.get("comparative_insights", {}),
        )

    def _post_process(
        self, report: str, state_data: dict, indicators: dict, ground_truth: dict
    ) -> str:
        """Post-process report: number injection (same as existing pipeline).

        Note: News references and transparency footer are added by report_worker
        after receiving the report back, so we only do number injection here.
        """
        percentiles = state_data.get("percentiles", {})
        ticker_data = state_data.get("ticker_data", {})
        comparative_insights = state_data.get("comparative_insights", {})
        strategy_performance = state_data.get("strategy_performance")

        injected = self.number_injector.inject_deterministic_numbers(
            report, ground_truth, indicators, percentiles,
            ticker_data, comparative_insights,
            strategy_performance=strategy_performance,
        )

        return f"{injected}\n\n— QuantAgent"

    def _serialize_scores(self, scores: dict) -> dict:
        """Convert score objects to JSON-serializable dict."""
        result = {}
        for name, score_obj in scores.items():
            if hasattr(score_obj, "overall_score"):
                result[name] = score_obj.overall_score
        return result
