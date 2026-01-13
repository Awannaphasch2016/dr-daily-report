# -*- coding: utf-8 -*-
"""
RAGAS Adapter

Integrates RAGAS (RAG Assessment) library for evaluation metrics.
RAGAS provides standardized metrics for evaluating RAG-style outputs.

Available metrics:
- answer_relevancy: How relevant is the answer to the question
- faithfulness: Is the answer grounded in the provided context
- factual_correctness: Are the facts in the answer correct
"""

import os
import time
import logging
from typing import List, Optional

from src.scoring.types import (
    ScoreResult,
    ScoreSource,
    ScoreTier,
    RAGASEvaluationError,
)

logger = logging.getLogger(__name__)


class RAGASAdapter:
    """
    Adapter for RAGAS evaluation metrics.

    Uses the ragas library to evaluate answer quality.
    Requires OpenAI API key for LLM-based evaluation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RAGAS adapter.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY or OPENROUTER_API_KEY)
        """
        self._api_key = api_key or os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
        self._initialized = False

        if not self._api_key:
            logger.warning("RAGASAdapter: No API key configured - evaluations will fail")

    def _ensure_initialized(self):
        """Lazy initialization of RAGAS."""
        if self._initialized:
            return

        try:
            # Set OpenAI API key for RAGAS
            if self._api_key:
                os.environ['OPENAI_API_KEY'] = self._api_key

            # Import RAGAS components
            from ragas.metrics import answer_relevancy
            from ragas import evaluate

            self._answer_relevancy = answer_relevancy
            self._evaluate = evaluate
            self._initialized = True

            logger.info("RAGAS adapter initialized successfully")

        except ImportError as e:
            raise RAGASEvaluationError(f"RAGAS library not installed: {e}")
        except Exception as e:
            raise RAGASEvaluationError(f"Failed to initialize RAGAS: {e}")

    async def evaluate_answer_relevancy(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> ScoreResult:
        """
        Evaluate answer relevancy using RAGAS.

        Measures how relevant the answer is to the question.

        Args:
            question: The user's question/query
            answer: The generated answer to evaluate
            contexts: List of context strings used to generate the answer

        Returns:
            ScoreResult with answer relevancy score

        Raises:
            RAGASEvaluationError: If evaluation fails
        """
        self._ensure_initialized()

        start_time = time.time()

        try:
            from datasets import Dataset

            # Create dataset for RAGAS
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            dataset = Dataset.from_dict(data)

            # Run RAGAS evaluation
            result = self._evaluate(
                dataset,
                metrics=[self._answer_relevancy],
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract score
            score = result['answer_relevancy']
            if hasattr(score, '__iter__'):
                score = list(score)[0] if len(list(score)) > 0 else 0.0

            score = float(score) if score is not None else 0.0

            logger.debug(f"RAGAS answer_relevancy: {score:.2f} ({latency_ms:.0f}ms)")

            return ScoreResult(
                name="answer_relevancy",
                value=score,
                source=ScoreSource.RAGAS,
                tier=ScoreTier.RANKING,
                latency_ms=latency_ms,
                cost_usd=0.01,  # Estimated cost
                metadata={
                    "metric": "answer_relevancy",
                    "ragas_version": "0.2.x",
                },
            )

        except Exception as e:
            raise RAGASEvaluationError(f"RAGAS answer_relevancy evaluation failed: {e}")

    async def evaluate_faithfulness(
        self,
        question: str,
        answer: str,
        contexts: List[str],
    ) -> ScoreResult:
        """
        Evaluate faithfulness using RAGAS.

        Measures if the answer is grounded in the provided context.

        Args:
            question: The user's question/query
            answer: The generated answer to evaluate
            contexts: List of context strings used to generate the answer

        Returns:
            ScoreResult with faithfulness score
        """
        self._ensure_initialized()

        start_time = time.time()

        try:
            from datasets import Dataset
            from ragas.metrics import faithfulness

            # Create dataset for RAGAS
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            dataset = Dataset.from_dict(data)

            # Run RAGAS evaluation
            result = self._evaluate(
                dataset,
                metrics=[faithfulness],
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract score
            score = result['faithfulness']
            if hasattr(score, '__iter__'):
                score = list(score)[0] if len(list(score)) > 0 else 0.0

            score = float(score) if score is not None else 0.0

            logger.debug(f"RAGAS faithfulness: {score:.2f} ({latency_ms:.0f}ms)")

            return ScoreResult(
                name="ragas_faithfulness",
                value=score,
                source=ScoreSource.RAGAS,
                tier=ScoreTier.RANKING,
                latency_ms=latency_ms,
                cost_usd=0.01,
                metadata={
                    "metric": "faithfulness",
                    "ragas_version": "0.2.x",
                },
            )

        except Exception as e:
            raise RAGASEvaluationError(f"RAGAS faithfulness evaluation failed: {e}")
