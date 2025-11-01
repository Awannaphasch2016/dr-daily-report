"""
Tests for CostScorer
"""

import pytest
from src.cost_scorer import CostScorer, CostScore


class TestCostScorer:
    """Test suite for CostScorer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scorer = CostScorer()
        
        # Sample API costs
        self.api_costs_good = {
            'llm_actual': None,
            'llm_estimated': 0.05,  # $0.05 USD
            'input_tokens': 2000,
            'output_tokens': 500
        }
        
        self.api_costs_high = {
            'llm_actual': None,
            'llm_estimated': 0.25,  # $0.25 USD
            'input_tokens': 10000,
            'output_tokens': 3000
        }
        
        # Sample database metrics
        self.database_metrics = {
            'query_count': 3
        }
    
    def test_cost_excellent(self):
        """Test cost scoring with excellent cost efficiency"""
        api_costs = {
            'llm_actual': None,
            'llm_estimated': 0.03,  # < 1.75 THB
            'input_tokens': 1500,
            'output_tokens': 400
        }
        
        score = self.scorer.score_cost(
            api_costs=api_costs,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert score.cost_efficiency_score == 100
        assert score.overall_cost_thb < self.scorer.COST_THRESHOLDS['excellent']
        assert any('Excellent cost efficiency' in strength for strength in score.strengths)
    
    def test_cost_good(self):
        """Test cost scoring with good cost efficiency"""
        api_costs = {
            'llm_actual': None,
            'llm_estimated': 0.08,  # ~2.8 THB
            'input_tokens': 3000,
            'output_tokens': 800
        }
        
        score = self.scorer.score_cost(
            api_costs=api_costs,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert score.cost_efficiency_score == 85
        assert self.scorer.COST_THRESHOLDS['excellent'] <= score.overall_cost_thb < self.scorer.COST_THRESHOLDS['good']
    
    def test_cost_acceptable(self):
        """Test cost scoring with acceptable cost"""
        api_costs = {
            'llm_actual': None,
            'llm_estimated': 0.15,  # ~5.25 THB
            'input_tokens': 5000,
            'output_tokens': 1500
        }
        
        score = self.scorer.score_cost(
            api_costs=api_costs,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert score.cost_efficiency_score == 70
        assert any('Acceptable cost' in issue for issue in score.issues)
    
    def test_cost_poor(self):
        """Test cost scoring with poor cost efficiency"""
        api_costs = {
            'llm_actual': None,
            'llm_estimated': 0.30,  # ~10.5 THB
            'input_tokens': 12000,
            'output_tokens': 4000
        }
        
        score = self.scorer.score_cost(
            api_costs=api_costs,
            llm_calls=2,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert score.cost_efficiency_score <= 50
        assert any('High cost' in issue for issue in score.issues)
    
    def test_cost_with_multiple_llm_calls(self):
        """Test cost scoring with multiple LLM calls"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=3,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert any('Multiple LLM calls' in issue for issue in score.issues)
        assert score.cost_efficiency_score < 100
    
    def test_cost_with_single_llm_call(self):
        """Test cost scoring with single LLM call"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert any('Single LLM call' in strength for strength in score.strengths)
    
    def test_cost_with_cache_hit(self):
        """Test cost scoring with cache hit"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=True
        )
        
        assert any('Cache hit reduced' in strength for strength in score.strengths)
    
    def test_cost_breakdown_calculation(self):
        """Test cost breakdown calculation"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert 'llm_cost_thb' in score.cost_breakdown
        assert 'db_cost_thb' in score.cost_breakdown
        assert 'total_cost_thb' in score.cost_breakdown
        assert 'llm_cost_usd' in score.cost_breakdown
        
        # Check THB conversion (approximately 35x USD)
        expected_thb = score.cost_breakdown['llm_cost_usd'] * self.scorer.USD_TO_THB_RATE
        assert abs(score.cost_breakdown['llm_cost_thb'] - expected_thb) < 0.01
        
        # Check total cost
        total = score.cost_breakdown['llm_cost_thb'] + score.cost_breakdown['db_cost_thb']
        assert abs(score.overall_cost_thb - total) < 0.01
    
    def test_token_usage_tracking(self):
        """Test token usage tracking"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        assert 'input_tokens' in score.token_usage
        assert 'output_tokens' in score.token_usage
        assert 'total_tokens' in score.token_usage
        assert score.token_usage['total_tokens'] == (
            score.token_usage['input_tokens'] + score.token_usage['output_tokens']
        )
    
    def test_calculate_api_cost(self):
        """Test API cost calculation"""
        result = self.scorer.calculate_api_cost(
            input_tokens=2000,
            output_tokens=500,
            actual_cost_usd=None
        )
        
        assert 'llm_actual' in result
        assert 'llm_estimated' in result
        assert 'input_tokens' in result
        assert 'output_tokens' in result
        
        # Check estimated cost calculation
        expected_cost = (
            2000 * self.scorer.GPT4O_INPUT_RATE_USD +
            500 * self.scorer.GPT4O_OUTPUT_RATE_USD
        )
        assert abs(result['llm_estimated'] - expected_cost) < 0.0001
    
    def test_calculate_api_cost_with_actual(self):
        """Test API cost calculation with actual cost"""
        actual_cost = 0.012
        result = self.scorer.calculate_api_cost(
            input_tokens=2000,
            output_tokens=500,
            actual_cost_usd=actual_cost
        )
        
        assert result['llm_actual'] == actual_cost
        assert result['llm_estimated'] is not None
    
    def test_format_score_report(self):
        """Test score report formatting"""
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=self.database_metrics,
            cache_hit=False
        )
        
        report = self.scorer.format_score_report(score)
        
        assert "COST SCORE REPORT" in report
        assert f"{score.overall_cost_thb:.4f} THB" in report
        assert f"{score.cost_efficiency_score:.1f}/100" in report
        assert "Cost Breakdown:" in report
        assert "Token Usage:" in report
        assert "Operation Details:" in report
    
    def test_db_cost_calculation(self):
        """Test database cost calculation"""
        db_metrics_high = {'query_count': 10}
        
        score = self.scorer.score_cost(
            api_costs=self.api_costs_good,
            llm_calls=1,
            database_metrics=db_metrics_high,
            cache_hit=False
        )
        
        expected_db_cost = 10 * self.scorer.DB_QUERY_COST_THB
        assert abs(score.cost_breakdown['db_cost_thb'] - expected_db_cost) < 0.001
        assert score.cost_breakdown['db_query_count'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
