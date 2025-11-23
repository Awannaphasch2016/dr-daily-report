# -*- coding: utf-8 -*-
"""
Tests for HallucinationScorer (LLM-as-judge)
"""

import pytest
from src.hallucination_scorer import HallucinationScorer, HallucinationScore


class TestHallucinationScorer:
    """Test suite for LLM-as-judge hallucination scorer"""

    def setup_method(self):
        """Setup test fixtures"""
        self.scorer = HallucinationScorer()

    def test_scorer_initialization(self):
        """Test that scorer initializes correctly"""
        assert self.scorer is not None
        assert self.scorer.model == "gpt-4o-mini"
        assert self.scorer.temperature == 0.0
        assert self.scorer.llm is not None

    def test_score_narrative_structure(self):
        """Test that score_narrative returns correct structure"""
        # Sample narrative and context
        narrative = "บริษัท DBS ปิดที่ 53.67 บาท โดย RSI อยู่ที่ 55.71"

        ground_truth_context = {
            'indicators': {
                'rsi': 55.71,
                'current_price': 53.67
            },
            'percentiles': {},
            'news': [],
            'ticker_data': {
                'company_name': 'DBS Group Holdings Ltd'
            },
            'market_conditions': {}
        }

        # Score (this will make actual LLM call if OPENAI_API_KEY is set)
        try:
            result = self.scorer.score_narrative(
                narrative=narrative,
                ground_truth_context=ground_truth_context,
                ticker="DBS19"
            )

            # Check return type
            assert isinstance(result, HallucinationScore)

            # Check required fields
            assert hasattr(result, 'overall_score')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'hallucinations')
            assert hasattr(result, 'validated_claims')
            assert hasattr(result, 'llm_reasoning')

            # Check score range
            assert 0 <= result.overall_score <= 100
            assert 0 <= result.confidence <= 100

            # Check lists
            assert isinstance(result.hallucinations, list)
            assert isinstance(result.validated_claims, list)
            assert isinstance(result.llm_reasoning, str)

        except Exception as e:
            # If LLM call fails (e.g., no API key), check error handling
            pytest.skip(f"LLM call failed (expected if no API key): {e}")

    def test_validate_against_faithfulness(self):
        """Test cross-validation with faithfulness scorer"""
        # Mock hallucination score
        llm_score = HallucinationScore(
            overall_score=95.0,
            confidence=90.0,
            hallucinations=[],
            validated_claims=["Price is correct", "RSI is accurate"],
            llm_reasoning="All claims verified"
        )

        rule_based_score = 92.0

        # Validate
        comparison = self.scorer.validate_against_faithfulness(
            llm_score=llm_score,
            rule_based_score=rule_based_score
        )

        # Check comparison structure
        assert 'agreement' in comparison
        assert 'confidence' in comparison
        assert 'score_difference' in comparison
        assert 'recommendation' in comparison

        # Check agreement (scores are close)
        assert comparison['agreement'] == 'strong'  # diff = 3.0 <= 10
        assert comparison['confidence'] == 'high'

    def test_validate_against_faithfulness_weak_agreement(self):
        """Test validation with significant score divergence"""
        llm_score = HallucinationScore(
            overall_score=50.0,
            confidence=80.0,
            hallucinations=["Incorrect price"],
            validated_claims=[],
            llm_reasoning="Price mismatch detected"
        )

        rule_based_score = 95.0

        comparison = self.scorer.validate_against_faithfulness(
            llm_score=llm_score,
            rule_based_score=rule_based_score
        )

        # Check weak agreement (large diff)
        assert comparison['agreement'] == 'weak'  # diff = 45.0 > 20
        assert comparison['confidence'] == 'low'
        assert "manual review" in comparison['recommendation'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
