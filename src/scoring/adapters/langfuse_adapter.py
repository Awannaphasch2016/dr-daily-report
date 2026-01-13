# -*- coding: utf-8 -*-
"""
Langfuse-Style LLM Adapter

Implements LLM-as-judge evaluations using the same prompts that
Langfuse built-in evaluators use. This allows real-time scoring
during report generation (vs async scoring on traces).

Supports evaluators:
- hallucination: Check if output contains fabricated information
- helpfulness: Check if output is useful to the user
- conciseness: Check if output is appropriately brief
- coherence: Check if output is logically structured
"""

import os
import time
import logging
from typing import Optional, Dict, Any

from openai import OpenAI

from src.scoring.types import (
    ScoreResult,
    ScoreSource,
    ScoreTier,
    LangfuseEvaluationError,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Langfuse-style Evaluation Prompts
# These mirror the prompts used by Langfuse's built-in evaluators
# =============================================================================

EVALUATION_PROMPTS = {
    "hallucination": """You are an expert evaluator checking for hallucinations in AI-generated content.

A hallucination is when the AI makes claims or statements that are NOT supported by the provided context.

Context (ground truth information):
{context}

AI Output to evaluate:
{output}

Task: Evaluate if the AI output contains hallucinations (information not supported by the context).

Score the output on a scale of 0 to 1:
- 1.0 = No hallucinations, all claims are supported by context
- 0.7-0.9 = Minor unsupported claims that don't affect the main message
- 0.4-0.6 = Some hallucinations present but mixed with supported content
- 0.1-0.3 = Significant hallucinations that mislead the reader
- 0.0 = Completely fabricated, no connection to context

Respond in JSON format:
{{"score": <float 0-1>, "reasoning": "<brief explanation>"}}""",

    "helpfulness": """You are an expert evaluator assessing the helpfulness of AI-generated content.

User Query/Intent:
{query}

AI Output to evaluate:
{output}

Task: Evaluate how helpful the AI output is for addressing the user's needs.

Score the output on a scale of 0 to 1:
- 1.0 = Extremely helpful, fully addresses the query with actionable insights
- 0.7-0.9 = Very helpful, addresses most aspects of the query
- 0.4-0.6 = Moderately helpful, partially addresses the query
- 0.1-0.3 = Slightly helpful, minimal relevant information
- 0.0 = Not helpful at all, irrelevant to the query

Respond in JSON format:
{{"score": <float 0-1>, "reasoning": "<brief explanation>"}}""",

    "conciseness": """You are an expert evaluator assessing the conciseness of AI-generated content.

AI Output to evaluate:
{output}

Task: Evaluate if the output is appropriately concise while still being complete.

Score the output on a scale of 0 to 1:
- 1.0 = Perfectly concise, every word adds value
- 0.7-0.9 = Good conciseness, minimal redundancy
- 0.4-0.6 = Moderate conciseness, some unnecessary content
- 0.1-0.3 = Verbose, significant unnecessary repetition or filler
- 0.0 = Extremely verbose, mostly irrelevant content

Respond in JSON format:
{{"score": <float 0-1>, "reasoning": "<brief explanation>"}}""",

    "coherence": """You are an expert evaluator assessing the coherence of AI-generated content.

AI Output to evaluate:
{output}

Task: Evaluate if the output is logically structured and coherent.

Consider:
- Logical flow of ideas
- Consistent terminology and tone
- Clear transitions between sections
- No contradictions

Score the output on a scale of 0 to 1:
- 1.0 = Perfectly coherent, excellent logical structure
- 0.7-0.9 = Very coherent, minor flow issues
- 0.4-0.6 = Moderately coherent, some disjointed sections
- 0.1-0.3 = Poorly coherent, difficult to follow
- 0.0 = Incoherent, no logical structure

Respond in JSON format:
{{"score": <float 0-1>, "reasoning": "<brief explanation>"}}""",
}


class LangfuseLLMAdapter:
    """
    Adapter for LLM-as-judge evaluations.

    Uses OpenRouter/OpenAI to run evaluation prompts that mirror
    Langfuse's built-in evaluators.
    """

    def __init__(
        self,
        model: str = "openai/gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the LLM adapter.

        Args:
            model: Model to use for evaluation (default: gpt-4o-mini for cost efficiency)
            api_key: API key (defaults to OPENROUTER_API_KEY env var)
            base_url: API base URL (defaults to OpenRouter)
        """
        self._model = model
        self._api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        self._base_url = base_url or "https://openrouter.ai/api/v1"
        self._client: Optional[OpenAI] = None

        # Validate at startup (Principle #1: Defensive Programming)
        if not self._api_key:
            logger.warning("LangfuseLLMAdapter: No API key configured - evaluations will fail")

    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client (lazy initialization)."""
        if self._client is None:
            if not self._api_key:
                raise LangfuseEvaluationError("API key not configured for LLM evaluation")

            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def evaluate(
        self,
        evaluator_name: str,
        output: str,
        context: Optional[str] = None,
        query: Optional[str] = None,
    ) -> ScoreResult:
        """
        Run a Langfuse-style LLM evaluation.

        Args:
            evaluator_name: One of "hallucination", "helpfulness", "conciseness", "coherence"
            output: The AI output to evaluate
            context: Context/ground truth (required for hallucination)
            query: User query (required for helpfulness)

        Returns:
            ScoreResult with evaluation result

        Raises:
            LangfuseEvaluationError: If evaluation fails
        """
        if evaluator_name not in EVALUATION_PROMPTS:
            raise LangfuseEvaluationError(
                f"Unknown evaluator: {evaluator_name}. "
                f"Available: {list(EVALUATION_PROMPTS.keys())}"
            )

        # Build prompt with available context
        prompt_template = EVALUATION_PROMPTS[evaluator_name]
        prompt = prompt_template.format(
            output=output,
            context=context or "No context provided",
            query=query or "Analyze the content",
        )

        # Run LLM evaluation
        start_time = time.time()
        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "You are an expert content evaluator. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Deterministic for consistency
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            latency_ms = (time.time() - start_time) * 1000

            # Parse response
            result_text = response.choices[0].message.content
            if not result_text:
                raise LangfuseEvaluationError(f"Empty response from LLM for {evaluator_name}")

            import json
            result = json.loads(result_text)

            score = float(result.get('score', 0))
            reasoning = result.get('reasoning', '')

            # Estimate cost (gpt-4o-mini pricing)
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost_usd = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000

            logger.debug(f"LLM evaluation {evaluator_name}: {score:.2f} ({latency_ms:.0f}ms)")

            return ScoreResult(
                name=evaluator_name,
                value=score,
                source=ScoreSource.LANGFUSE,
                tier=ScoreTier.RANKING,
                reasoning=reasoning,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                metadata={
                    "model": self._model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )

        except json.JSONDecodeError as e:
            raise LangfuseEvaluationError(f"Failed to parse LLM response for {evaluator_name}: {e}")
        except Exception as e:
            raise LangfuseEvaluationError(f"LLM evaluation failed for {evaluator_name}: {e}")

    # Convenience methods for specific evaluators

    async def evaluate_hallucination(self, output: str, context: str) -> ScoreResult:
        """Evaluate hallucination (grounding in context)."""
        return await self.evaluate("hallucination", output, context=context)

    async def evaluate_helpfulness(self, output: str, query: str) -> ScoreResult:
        """Evaluate helpfulness for user query."""
        return await self.evaluate("helpfulness", output, query=query)

    async def evaluate_conciseness(self, output: str) -> ScoreResult:
        """Evaluate conciseness of output."""
        return await self.evaluate("conciseness", output)

    async def evaluate_coherence(self, output: str) -> ScoreResult:
        """Evaluate coherence/logical structure of output."""
        return await self.evaluate("coherence", output)
