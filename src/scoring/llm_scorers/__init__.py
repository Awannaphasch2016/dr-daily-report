# -*- coding: utf-8 -*-
"""
LLM-Based Scorers

These scorers use LLM-as-judge evaluation via external APIs.
They complement the rule-based scorers with semantic evaluation.

Two-tier scoring:
- Gate Tier (binary): HallucinationScorer (must pass to proceed)
- Ranking Tier (0-1): HelpfulnessScorer, ConcisenessScorer, AnswerRelevancyScorer
"""

from .hallucination_scorer import HallucinationScorer
from .helpfulness_scorer import HelpfulnessScorer
from .conciseness_scorer import ConcisenessScorer
from .answer_relevancy_scorer import AnswerRelevancyScorer

__all__ = [
    'HallucinationScorer',
    'HelpfulnessScorer',
    'ConcisenessScorer',
    'AnswerRelevancyScorer',
]
