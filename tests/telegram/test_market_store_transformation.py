#!/usr/bin/env python3
"""
Unit tests for frontend data transformation logic

Tests that RankedTicker API response is correctly transformed to Market model
with chart_data and key_scores.
"""

import pytest
from unittest.mock import Mock, patch


class TestMarketStoreTransformation:
    """Tests for transforming RankedTicker to Market model"""

    def test_ranked_ticker_with_chart_data_creates_market_report(self):
        """Test that RankedTicker.chart_data is transformed to Market.report"""
        from src.api.models import RankedTicker, PriceDataPoint, ProjectionBand, ScoringMetric

        # Arrange: API response with chart_data
        ranked_ticker = RankedTicker(
            ticker='NVDA19',
            company_name='NVIDIA Corporation',
            price=151.0,
            price_change_pct=2.5,
            currency='USD',
            stance='bullish',
            estimated_upside_pct=15.0,
            risk_level='medium',
            chart_data={
                'price_history': [
                    {
                        'date': '2025-12-05',
                        'open': 150.0,
                        'high': 152.0,
                        'low': 149.0,
                        'close': 151.0,
                        'volume': 1000000,
                        'return_pct': 1.0,
                        'portfolio_nav': 1010.0
                    }
                ],
                'projections': [
                    {
                        'date': '2025-12-06',
                        'expected_return': 2.0,
                        'best_case_return': 5.0,
                        'worst_case_return': -1.0,
                        'expected_nav': 1020.0,
                        'best_case_nav': 1050.0,
                        'worst_case_nav': 990.0
                    }
                ],
                'initial_investment': 1000.0
            },
            key_scores=[
                {
                    'category': 'Technical',
                    'score': 8.5,
                    'max_score': 10,
                    'rationale': 'Strong momentum'
                }
            ]
        )

        # Act: Transform to Market-like dict (simulating frontend logic)
        market_report = {
            'price_history': ranked_ticker.chart_data.get('price_history', []),
            'projections': ranked_ticker.chart_data.get('projections', []),
            'initial_investment': ranked_ticker.chart_data.get('initial_investment', 1000.0),
            'key_scores': ranked_ticker.key_scores or []
        }

        # Assert: Report data is populated
        assert market_report['price_history'] is not None
        assert len(market_report['price_history']) == 1
        assert market_report['price_history'][0]['date'] == '2025-12-05'

        assert market_report['projections'] is not None
        assert len(market_report['projections']) == 1
        assert market_report['projections'][0]['date'] == '2025-12-06'

        assert market_report['initial_investment'] == 1000.0

        assert market_report['key_scores'] is not None
        assert len(market_report['key_scores']) == 1
        assert market_report['key_scores'][0].category == 'Technical'

    def test_ranked_ticker_without_chart_data_has_no_report(self):
        """Test that RankedTicker without chart_data results in no market.report"""
        from src.api.models import RankedTicker

        # Arrange: API response WITHOUT chart_data
        ranked_ticker = RankedTicker(
            ticker='DBS19',
            company_name='DBS Group Holdings',
            price=35.0,
            price_change_pct=-1.2,
            currency='SGD'
        )

        # Act: Check if chart_data exists
        has_chart_data = ranked_ticker.chart_data is not None
        has_key_scores = ranked_ticker.key_scores is not None

        # Assert: No report data should be created
        assert not has_chart_data, "Should have no chart_data"
        assert not has_key_scores, "Should have no key_scores"

    def test_ranked_ticker_with_only_key_scores_creates_report(self):
        """Test that RankedTicker with only key_scores (no chart) still creates report"""
        from src.api.models import RankedTicker

        # Arrange: API response with key_scores but no chart_data
        ranked_ticker = RankedTicker(
            ticker='AAPL19',
            company_name='Apple Inc.',
            price=180.0,
            price_change_pct=0.5,
            currency='USD',
            key_scores=[
                {
                    'category': 'Fundamental',
                    'score': 7.0,
                    'max_score': 10,
                    'rationale': 'Strong fundamentals'
                }
            ]
        )

        # Act: Check if we should create report
        should_create_report = (
            ranked_ticker.chart_data is not None or
            ranked_ticker.key_scores is not None
        )

        # Assert: Report should be created (has key_scores)
        assert should_create_report, "Should create report when key_scores exist"
        assert ranked_ticker.key_scores is not None
        assert len(ranked_ticker.key_scores) == 1

    def test_transformation_handles_empty_arrays(self):
        """Test transformation handles empty price_history/projections gracefully"""
        from src.api.models import RankedTicker

        # Arrange: API response with empty arrays
        ranked_ticker = RankedTicker(
            ticker='TSLA19',
            company_name='Tesla Inc.',
            price=250.0,
            price_change_pct=3.0,
            currency='USD',
            chart_data={
                'price_history': [],
                'projections': [],
                'initial_investment': 1000.0
            }
        )

        # Act: Transform to Market report
        market_report = {
            'price_history': ranked_ticker.chart_data.get('price_history', []),
            'projections': ranked_ticker.chart_data.get('projections', []),
            'initial_investment': ranked_ticker.chart_data.get('initial_investment', 1000.0),
            'key_scores': ranked_ticker.key_scores or []
        }

        # Assert: Empty arrays are valid
        assert market_report['price_history'] == []
        assert market_report['projections'] == []
        assert market_report['initial_investment'] == 1000.0
        assert market_report['key_scores'] == []
