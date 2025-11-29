"""
Tests for QoSScorer
"""

import pytest
from src.scoring.qos_scorer import QoSScorer, QoSScore


class TestQoSScorer:
    """Test suite for QoSScorer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scorer = QoSScorer()
        
        # Sample timing metrics
        self.timing_metrics = {
            'data_fetch': 1.0,
            'news_fetch': 0.5,
            'technical_analysis': 0.3,
            'chart_generation': 0.8,
            'llm_generation': 4.5,
            'scoring': 0.1,
            'total': 7.2
        }
        
        # Sample database metrics
        self.database_metrics = {
            'query_count': 3,
            'cache_hit': False
        }
    
    def test_latency_excellent(self):
        """Test latency scoring with excellent performance"""
        timing = {'total': 4.5}
        score, issues, strengths = self.scorer._score_latency(timing, False)
        
        assert score == 100
        assert 'Excellent total latency' in strengths[0]
    
    def test_latency_good(self):
        """Test latency scoring with good performance"""
        timing = {'total': 8.0}
        score, issues, strengths = self.scorer._score_latency(timing, False)
        
        assert score == 85
        assert 'Good total latency' in strengths[0]
    
    def test_latency_acceptable(self):
        """Test latency scoring with acceptable performance"""
        timing = {'total': 15.0}
        score, issues, strengths = self.scorer._score_latency(timing, False)
        
        assert score == 70
        assert any('Acceptable latency' in issue for issue in issues)
    
    def test_latency_poor(self):
        """Test latency scoring with poor performance"""
        timing = {'total': 25.0}
        score, issues, strengths = self.scorer._score_latency(timing, False)
        
        assert score == 50
        assert any('Poor latency' in issue for issue in issues)
    
    def test_determinism_no_historical(self):
        """Test determinism scoring without historical data"""
        score, issues, strengths = self.scorer._score_determinism(
            self.timing_metrics, self.database_metrics, None
        )
        
        assert score == 90
        assert 'Deterministic components' in strengths[0]
    
    def test_reliability_no_error(self):
        """Test reliability scoring with no errors"""
        score, issues, strengths = self.scorer._score_reliability(False, False, self.timing_metrics)
        
        assert score == 100
        assert 'No errors during execution' in strengths[0]
    
    def test_reliability_with_error(self):
        """Test reliability scoring with error"""
        score, issues, strengths = self.scorer._score_reliability(True, False, self.timing_metrics)
        
        assert score == 30
        assert any('Error occurred' in issue for issue in issues)
    
    def test_resource_efficiency_good(self):
        """Test resource efficiency with good metrics"""
        db_metrics = {'query_count': 3}
        score, issues, strengths = self.scorer._score_resource_efficiency(
            db_metrics, 1, False
        )
        
        assert score == 100
        assert any('Efficient database usage' in strength for strength in strengths)
    
    def test_resource_efficiency_high_queries(self):
        """Test resource efficiency with high query count"""
        db_metrics = {'query_count': 15}
        score, issues, strengths = self.scorer._score_resource_efficiency(
            db_metrics, 1, False
        )
        
        assert score < 100
        assert any('High database query count' in issue for issue in issues)
    
    def test_scalability_good(self):
        """Test scalability scoring with good latency"""
        timing = {'total': 8.0}
        score, issues, strengths = self.scorer._score_scalability(timing, None)
        
        assert score == 90
        assert any('Low latency suggests' in strength for strength in strengths)
    
    def test_score_qos_full(self):
        """Test full QoS scoring"""
        score = self.scorer.score_qos(
            timing_metrics=self.timing_metrics,
            database_metrics=self.database_metrics,
            error_occurred=False,
            cache_hit=False,
            llm_calls=1,
            historical_data=None
        )
        
        assert isinstance(score, QoSScore)
        assert 0 <= score.overall_score <= 100
        assert 'latency' in score.dimension_scores
        assert 'determinism' in score.dimension_scores
        assert 'reliability' in score.dimension_scores
        assert 'resource_efficiency' in score.dimension_scores
        assert 'scalability' in score.dimension_scores
        assert 'cost_efficiency' not in score.dimension_scores  # Should be removed
    
    def test_score_qos_with_historical(self):
        """Test QoS scoring with historical data"""
        historical = {
            'timing': {
                'data_fetch': 1.0,
                'technical_analysis': 0.3
            }
        }
        
        score = self.scorer.score_qos(
            timing_metrics=self.timing_metrics,
            database_metrics=self.database_metrics,
            error_occurred=False,
            cache_hit=False,
            llm_calls=1,
            historical_data=historical
        )
        
        assert isinstance(score, QoSScore)
        assert score.dimension_scores['determinism'] >= 80
    
    def test_format_score_report(self):
        """Test score report formatting"""
        score = self.scorer.score_qos(
            timing_metrics=self.timing_metrics,
            database_metrics=self.database_metrics,
            error_occurred=False,
            cache_hit=False,
            llm_calls=1
        )
        
        report = self.scorer.format_score_report(score)
        
        assert "QoS SCORE REPORT" in report
        assert f"{score.overall_score:.1f}/100" in report
        assert "Dimension Scores:" in report
        assert "Note: Cost is tracked separately" in report
    
    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        score = self.scorer.score_qos(
            timing_metrics=self.timing_metrics,
            database_metrics=self.database_metrics,
            error_occurred=False,
            cache_hit=False,
            llm_calls=1
        )
        
        expected = (
            score.dimension_scores['latency'] * 0.30 +
            score.dimension_scores['determinism'] * 0.20 +
            score.dimension_scores['reliability'] * 0.25 +
            score.dimension_scores['resource_efficiency'] * 0.15 +
            score.dimension_scores['scalability'] * 0.10
        )
        
        assert abs(score.overall_score - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
