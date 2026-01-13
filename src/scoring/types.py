# -*- coding: utf-8 -*-
"""
Scoring Types and Exceptions

Unified types for multi-source scoring architecture.
All scorers (rule-based, Langfuse, RAGAS) return ScoreResult.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ScoreSource(Enum):
    """Where the score comes from."""
    RULE_BASED = "rule_based"      # Custom scorers (fast, free)
    LANGFUSE = "langfuse"          # Langfuse LLM-as-judge
    RAGAS = "ragas"                # RAGAS library
    METRICS = "metrics"            # Performance metrics


class ScoreTier(Enum):
    """Which tier this score belongs to."""
    GATE = "gate"                  # Binary pass/fail
    RANKING = "ranking"            # Continuous 0-1


# =============================================================================
# Exceptions (per Principle #8: utilities raise exceptions)
# =============================================================================

class ScoringError(Exception):
    """Base exception for scoring failures."""
    pass


class LangfuseEvaluationError(ScoringError):
    """Langfuse API call failed."""
    pass


class RAGASEvaluationError(ScoringError):
    """RAGAS evaluation failed."""
    pass


class ScoreValidationError(ScoringError):
    """Score value is invalid."""
    pass


# =============================================================================
# Score Result (unified output from all scorers)
# =============================================================================

@dataclass
class ScoreResult:
    """
    Unified score result from any source.

    All scorers return this type for consistent handling.
    Value is normalized to 0-1 range.
    """
    name: str
    value: float                   # Normalized 0-1
    source: ScoreSource
    tier: ScoreTier
    raw_value: Optional[float] = None  # Original scale (e.g., 0-100)
    reasoning: Optional[str] = None     # LLM explanation
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    cost_usd: float = 0.0              # Cost of this evaluation
    latency_ms: float = 0.0            # Time to compute

    def __post_init__(self):
        """Defensive: Validate score is in valid range."""
        if not 0 <= self.value <= 1:
            raise ScoreValidationError(
                f"Score value must be 0-1, got {self.value} for {self.name}"
            )

    def passed_gate(self, threshold: float = 0.7) -> bool:
        """Check if this score passes a gate threshold."""
        return self.value >= threshold

    def to_langfuse_score(self) -> Dict[str, Any]:
        """Convert to Langfuse score format."""
        return {
            'name': self.name,
            'value': self.value,
            'comment': self.reasoning,
        }


# =============================================================================
# Scoring Context (input to all scorers)
# =============================================================================

@dataclass
class LLMScoringContext:
    """
    Context data for LLM-based scorers.

    Extended version of ScoringContext with fields needed for
    LLM-as-judge evaluation (query, contexts for RAG-style evaluation).
    """
    report_text: str               # Generated report (Thai narrative)
    ticker: str                    # Stock ticker symbol
    input_data: Dict[str, Any]     # Ground truth (prices, indicators)
    news_data: List[Dict]          # News items with titles
    query: Optional[str] = None    # User's original query

    def format_context_for_llm(self) -> str:
        """Format input data as context string for LLM evaluation."""
        lines = []

        # Add price/indicator data
        for key, value in self.input_data.items():
            if isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"{key}.{k}: {v}")

        # Add news
        if self.news_data:
            lines.append("\n--- News ---")
            for i, news in enumerate(self.news_data, 1):
                title = news.get('title', news.get('headline', ''))
                lines.append(f"[{i}] {title}")

        return "\n".join(lines)

    def get_contexts_list(self) -> List[str]:
        """Get contexts as list of strings for RAGAS evaluation."""
        contexts = []

        # Input data as one context
        data_context = "\n".join(
            f"{k}: {v}" for k, v in self.input_data.items()
            if isinstance(v, (int, float, str))
        )
        if data_context:
            contexts.append(data_context)

        # News as another context
        if self.news_data:
            news_context = "\n".join(
                news.get('title', news.get('headline', ''))
                for news in self.news_data
            )
            if news_context:
                contexts.append(news_context)

        return contexts

    def get_query(self) -> str:
        """Get query for evaluation (default if not provided)."""
        return self.query or f"Generate a stock analysis report for {self.ticker}"
