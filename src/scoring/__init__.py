"""
Scoring Layer - Report Quality Evaluation

Two-Tier Scoring Framework:
- Gate Tier (binary pass/fail): hallucination
- Ranking Tier (0-1 continuous): quality scores

Rule-based scorers (fast, free):
- FaithfulnessScorer, CompletenessScorer, ReasoningQualityScorer
- ComplianceScorer, ConsistencyScorer

LLM-as-judge scorers (API cost):
- HallucinationScorer, HelpfulnessScorer, ConcisenessScorer
- AnswerRelevancyScorer (via RAGAS)

Performance scorers:
- QoSScorer, CostScorer
"""
from .faithfulness_scorer import FaithfulnessScorer
from .completeness_scorer import CompletenessScorer
from .reasoning_quality_scorer import ReasoningQualityScorer
from .compliance_scorer import ComplianceScorer
from .consistency_scorer import ConsistencyScorer
from .qos_scorer import QoSScorer
from .cost_scorer import CostScorer
from .scoring_service import ScoringService, ScoringContext
from .types import (
    ScoreResult,
    ScoreSource,
    ScoreTier,
    LLMScoringContext,
    ScoringError,
    LangfuseEvaluationError,
    RAGASEvaluationError,
    ScoreValidationError,
)

__all__ = [
    # Rule-based scorers
    'FaithfulnessScorer',
    'CompletenessScorer',
    'ReasoningQualityScorer',
    'ComplianceScorer',
    'ConsistencyScorer',
    # Performance scorers
    'QoSScorer',
    'CostScorer',
    # Service
    'ScoringService',
    'ScoringContext',
    # Types
    'ScoreResult',
    'ScoreSource',
    'ScoreTier',
    'LLMScoringContext',
    # Exceptions
    'ScoringError',
    'LangfuseEvaluationError',
    'RAGASEvaluationError',
    'ScoreValidationError',
]
