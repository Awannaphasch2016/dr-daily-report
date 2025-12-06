# -*- coding: utf-8 -*-
"""Integration tests for rankings service with Aurora cache.

TDD Tests:
1. RankedTicker model can include chart_data and key_scores
2. Rankings service queries Aurora cache for precomputed data
3. Rankings response includes lightweight chart/score data
"""

import pytest
from datetime import datetime, date
from pydantic import ValidationError


class TestRankedTickerModelExtension:
    """Test RankedTicker model supports chart_data and key_scores fields."""

    def test_ranked_ticker_accepts_chart_data(self):
        """Test RankedTicker can include optional chart_data field.

        This enables rankings API to return precomputed chart data
        from Aurora cache without requiring full report generation.
        """
        from src.api.models import RankedTicker, PriceDataPoint, ProjectionBand

        # Create sample chart data
        price_history = [
            PriceDataPoint(
                date='2025-12-05',
                open=150.0,
                high=152.0,
                low=149.0,
                close=151.0,
                volume=1000000,
                return_pct=1.0,
                portfolio_nav=1010.0
            )
        ]

        projections = [
            ProjectionBand(
                date='2025-12-06',
                expected_return=2.0,
                best_case_return=5.0,
                worst_case_return=-1.0,
                expected_nav=1020.0,
                best_case_nav=1050.0,
                worst_case_nav=990.0
            )
        ]

        # Create RankedTicker with chart_data
        ranked_ticker = RankedTicker(
            ticker='NVDA',
            company_name='NVIDIA Corporation',
            price=151.0,
            price_change_pct=1.0,
            currency='USD',
            stance='bullish',
            chart_data={
                'price_history': price_history,
                'projections': projections,
                'initial_investment': 1000.0
            }
        )

        # Verify chart_data is present
        assert ranked_ticker.chart_data is not None
        assert 'price_history' in ranked_ticker.chart_data
        assert len(ranked_ticker.chart_data['price_history']) == 1
        assert ranked_ticker.chart_data['initial_investment'] == 1000.0

    def test_ranked_ticker_accepts_key_scores(self):
        """Test RankedTicker can include optional key_scores field.

        This enables rankings API to return top 3 investment scores
        from Aurora cache for quick decision-making on market cards.
        """
        from src.api.models import RankedTicker, ScoringMetric

        # Create sample key scores
        key_scores = [
            ScoringMetric(
                category='Technical',
                score=7.5,
                max_score=10,
                rationale='Strong momentum indicators'
            ),
            ScoringMetric(
                category='Fundamental',
                score=6.0,
                max_score=10,
                rationale='Moderate valuation'
            )
        ]

        # Create RankedTicker with key_scores
        ranked_ticker = RankedTicker(
            ticker='NVDA',
            company_name='NVIDIA Corporation',
            price=151.0,
            price_change_pct=1.0,
            currency='USD',
            key_scores=key_scores
        )

        # Verify key_scores is present
        assert ranked_ticker.key_scores is not None
        assert len(ranked_ticker.key_scores) == 2
        assert ranked_ticker.key_scores[0].category == 'Technical'
        assert ranked_ticker.key_scores[0].score == 7.5

    def test_ranked_ticker_without_cache_data_still_valid(self):
        """Test RankedTicker works without chart_data/key_scores (backwards compat).

        When Aurora cache misses, rankings should still work with just
        price data (no charts/scores shown on UI).
        """
        from src.api.models import RankedTicker

        # Create minimal RankedTicker (no cache data)
        ranked_ticker = RankedTicker(
            ticker='NVDA',
            company_name='NVIDIA Corporation',
            price=151.0,
            price_change_pct=1.0,
            currency='USD'
        )

        # Verify model is valid
        assert ranked_ticker.chart_data is None
        assert ranked_ticker.key_scores is None
        assert ranked_ticker.ticker == 'NVDA'


class TestRankingsServiceCacheQuery:
    """Test rankings service queries Aurora cache for precomputed data."""

    @pytest.mark.integration
    def test_rankings_service_fetches_from_cache(self):
        """Test rankings service queries Aurora for cached chart/score data.

        Integration test: Verifies rankings service can fetch precomputed
        data from Aurora cache and include it in response.
        """
        from src.api.rankings_service import get_rankings_service
        import asyncio

        service = get_rankings_service()

        # Fetch trending rankings
        async def fetch():
            return await service.get_rankings('trending')

        rankings = asyncio.run(fetch())

        # Verify response structure
        assert len(rankings) > 0, "Should return at least one ticker"

        # Check if first ticker has cache data (may be None if cache miss)
        first_ticker = rankings[0]
        assert hasattr(first_ticker, 'chart_data'), "RankedTicker should have chart_data attribute"
        assert hasattr(first_ticker, 'key_scores'), "RankedTicker should have key_scores attribute"

        # If cache data exists, verify structure
        if first_ticker.chart_data:
            assert 'price_history' in first_ticker.chart_data
            assert 'projections' in first_ticker.chart_data
            assert 'initial_investment' in first_ticker.chart_data

    @pytest.mark.integration
    def test_cache_miss_returns_none_gracefully(self):
        """Test rankings service handles cache misses gracefully.

        When Aurora cache doesn't have data for a ticker, chart_data
        and key_scores should be None (not crash).
        """
        from src.api.rankings_service import RankingsService

        service = RankingsService()

        # Test with non-existent ticker (cache miss)
        import asyncio

        async def fetch_cache():
            return await service._fetch_from_cache('FAKE_TICKER_999')

        cached_data = asyncio.run(fetch_cache())

        # Should return None or empty dict on cache miss
        assert cached_data is None or cached_data == {}
