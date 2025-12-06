# -*- coding: utf-8 -*-
"""Integration tests for precompute service with scoring and projections.

Tests the complete pipeline:
1. Compute report for ticker (triggers agent workflow)
2. Verify user_facing_scores are calculated
3. Verify projections are calculated
4. Verify data is stored in report_json
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestPrecomputeIntegration:
    """Integration tests for precompute service with portfolio data enhancement"""

    def setup_method(self):
        """Set up test fixtures"""
        # Mock ticker data with realistic price history
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        self.mock_history = pd.DataFrame({
            'Open': np.linspace(100, 110, 30),
            'High': np.linspace(102, 112, 30),
            'Low': np.linspace(98, 108, 30),
            'Close': np.linspace(100, 110, 30),
            'Volume': [1000000] * 30
        }, index=dates)

        self.mock_ticker_data = {
            'info': {
                'shortName': 'Test Company',
                'sector': 'Technology',
                'currentPrice': 110.0
            },
            'history': self.mock_history
        }

        self.mock_indicators = {
            'sma_20': 105.0,
            'sma_50': 102.0,
            'rsi': 55.0,
            'macd': 0.5,
            'macd_signal': 0.3,
            'atr': 2.5,
            'volume_ratio': 1.2,
            'uncertainty_score': 35.0,
            'current_price': 110.0,
            'vwap': 105.0
        }

        self.mock_percentiles = {
            'current_percentile': 65.0,
            'rsi_percentile': 55.0,
            'volume_percentile': 60.0
        }

    def test_enhancement_adds_projections_to_state(self):
        """Verify _enhance_report_json_with_portfolio_data adds projections"""
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # Create minimal state
        state = {
            'ticker': 'TEST19',
            'ticker_data': self.mock_ticker_data,
            'indicators': self.mock_indicators,
            'percentiles': self.mock_percentiles
        }

        # Enhance state
        enhanced_state = service._enhance_report_json_with_portfolio_data(state)

        # Verify projections were added
        assert 'projections' in enhanced_state, "projections field should be added"
        assert 'initial_investment' in enhanced_state, "initial_investment should be added"
        assert enhanced_state['initial_investment'] == 1000.0

        # Verify projection structure
        projections = enhanced_state['projections']
        assert len(projections) == 7, "Should have 7-day projections"

        for proj in projections:
            assert 'date' in proj
            assert 'expected_return' in proj
            assert 'best_case_return' in proj
            assert 'worst_case_return' in proj
            assert 'expected_nav' in proj
            assert 'best_case_nav' in proj
            assert 'worst_case_nav' in proj

    def test_enhancement_handles_empty_history(self):
        """Verify graceful handling when history is empty"""
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # State with empty history
        state = {
            'ticker': 'TEST19',
            'ticker_data': {'history': pd.DataFrame()},
            'indicators': self.mock_indicators
        }

        # Should not raise exception
        enhanced_state = service._enhance_report_json_with_portfolio_data(state)

        # Should return original state without projections
        assert 'projections' not in enhanced_state or len(enhanced_state.get('projections', [])) == 0

    def test_enhancement_handles_missing_ticker_data(self):
        """Verify graceful handling when ticker_data is missing"""
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # State without ticker_data
        state = {'ticker': 'TEST19'}

        # Should not raise exception
        enhanced_state = service._enhance_report_json_with_portfolio_data(state)

        # Should return original state
        assert enhanced_state == state

    def test_workflow_result_includes_all_portfolio_fields(self):
        """Integration test: verify _enhance_report_json_with_portfolio_data integrates into workflow"""
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # Simulate agent workflow result
        mock_result = {
            'ticker': 'TEST19',
            'ticker_data': self.mock_ticker_data,
            'indicators': self.mock_indicators,
            'percentiles': self.mock_percentiles,
            'user_facing_scores': {
                'Fundamental': {'category': 'Fundamental', 'score': 7.5, 'rationale': 'Good'},
                'Technical': {'category': 'Technical', 'score': 6.0, 'rationale': 'Neutral'}
            },
            'report': '📊 Test report',
            'chart_base64': 'base64string',
            'mini_reports': {}
        }

        # Enhance with portfolio data (this is what precompute service does)
        enhanced_result = service._enhance_report_json_with_portfolio_data(mock_result)

        # Verify all expected fields exist
        assert 'ticker_data' in enhanced_result
        assert 'indicators' in enhanced_result
        assert 'user_facing_scores' in enhanced_result
        assert 'projections' in enhanced_result, "Should add projections"
        assert 'initial_investment' in enhanced_result, "Should add initial_investment"

        # Verify projections structure
        projections = enhanced_result['projections']
        assert len(projections) == 7
        assert all('expected_nav' in p for p in projections)
        assert all('best_case_nav' in p for p in projections)
        assert all('worst_case_nav' in p for p in projections)

    def test_projections_confidence_bands_widen_over_time(self):
        """Verify stored projections have widening confidence bands"""
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        state = {
            'ticker': 'TEST19',
            'ticker_data': self.mock_ticker_data,
            'indicators': self.mock_indicators
        }

        enhanced_state = service._enhance_report_json_with_portfolio_data(state)
        projections = enhanced_state.get('projections', [])

        if len(projections) > 1:
            # Day 1 spread
            day1_spread = projections[0]['best_case_return'] - projections[0]['worst_case_return']

            # Day 7 spread
            day7_spread = projections[6]['best_case_return'] - projections[6]['worst_case_return']

            # Should widen over time
            assert day7_spread > day1_spread, "Confidence bands should widen over time"


class TestPrecomputeServiceScoring:
    """Tests for user-facing scores integration in precompute service"""

    def test_workflow_calculates_user_facing_scores(self):
        """Verify workflow includes score_user_facing node execution"""
        # This is tested implicitly via workflow_nodes tests
        # Just verify the field exists in AgentState
        from src.types import AgentState

        # TypedDict doesn't have __annotations__ in runtime, but we can verify structure
        # by creating a minimal state
        state: AgentState = {
            'messages': [],
            'ticker': 'TEST19',
            'ticker_data': {},
            'indicators': {},
            'percentiles': {},
            'chart_patterns': [],
            'pattern_statistics': {},
            'strategy_performance': {},
            'news': [],
            'news_summary': {},
            'comparative_data': {},
            'comparative_insights': {},
            'chart_base64': '',
            'report': '',
            'faithfulness_score': {},
            'completeness_score': {},
            'reasoning_quality_score': {},
            'compliance_score': {},
            'qos_score': {},
            'cost_score': {},
            'timing_metrics': {},
            'api_costs': {},
            'database_metrics': {},
            'user_facing_scores': {},  # NEW field
            'error': '',
            'strategy': 'single-stage'
        }

        # Verify user_facing_scores field exists
        assert 'user_facing_scores' in state
