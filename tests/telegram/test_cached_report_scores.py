"""Test that cached reports return key_scores after transformation.

Regression test for transformer bug where transform_cached_report()
didn't call _build_scores() to convert user_facing_scores → key_scores.
"""
import pytest
from src.api.transformer import get_transformer
from src.api.ticker_service import get_ticker_service


class TestCachedReportScores:
    """Test transformer converts cached user_facing_scores → key_scores"""

    def setup_method(self):
        self.transformer = get_transformer()
        self.ticker_service = get_ticker_service()

    @pytest.mark.asyncio
    async def test_cached_report_returns_key_scores(self):
        """GIVEN cached report with user_facing_scores in report_json
        WHEN transform_cached_report is called
        THEN key_scores and all_scores must be populated (not empty)
        """
        # Simulate cached report from Aurora
        cached_report = {
            'id': 1,
            'symbol': 'NVDA',
            'report_text': 'Test report text...',
            'chart_base64': 'base64encodedimage...',
            'report_generated_at': '2025-12-07T10:00:00',
            'report_json': {
                'key_scores': [
                    {
                        'score': 9.0,
                        'category': 'Growth Potential',
                        'max_score': 10.0,
                        'rationale': 'Expanding market share'
                    },
                    {
                        'score': 8.5,
                        'category': 'Fundamental Strength',
                        'max_score': 10.0,
                        'rationale': 'Strong earnings growth'
                    },
                    {
                        'score': 7.2,
                        'category': 'Technical Signal',
                        'max_score': 10.0,
                        'rationale': 'Bullish trend confirmed'
                    }
                ],
                'all_scores': [
                    {
                        'score': 9.0,
                        'category': 'Growth Potential',
                        'max_score': 10.0,
                        'rationale': 'Expanding market share'
                    },
                    {
                        'score': 8.5,
                        'category': 'Fundamental Strength',
                        'max_score': 10.0,
                        'rationale': 'Strong earnings growth'
                    },
                    {
                        'score': 7.2,
                        'category': 'Technical Signal',
                        'max_score': 10.0,
                        'rationale': 'Bullish trend confirmed'
                    },
                    {
                        'score': 6.5,
                        'category': 'Risk Assessment',
                        'max_score': 10.0,
                        'rationale': 'Moderate volatility'
                    },
                    {
                        'score': 5.8,
                        'category': 'Valuation',
                        'max_score': 10.0,
                        'rationale': 'Slightly overvalued'
                    }
                ],
                'indicators': {},
                'price_history': [],
                'projections': [],
                'initial_investment': 1000.0
            }
        }

        ticker_info = self.ticker_service.get_ticker_info('NVDA19')

        # Transform cached report
        response = await self.transformer.transform_cached_report(
            cached_report,
            ticker_info
        )

        # BEHAVIOR TEST: key_scores must be populated
        assert len(response.key_scores) > 0, \
            "key_scores must not be empty for cached reports with user_facing_scores"

        assert len(response.key_scores) <= 3, \
            "key_scores should contain top 3 scores"

        assert len(response.all_scores) > 0, \
            "all_scores must not be empty"

        # Verify scores are sorted by score descending
        scores_list = [s.score for s in response.key_scores]
        assert scores_list == sorted(scores_list, reverse=True), \
            "key_scores must be sorted by score descending"

        # Verify top score is Growth Potential (9.0)
        assert response.key_scores[0].category == 'Growth Potential', \
            f"Top score should be Growth Potential, got {response.key_scores[0].category}"
        assert response.key_scores[0].score == 9.0

    @pytest.mark.asyncio
    async def test_cached_report_handles_missing_user_facing_scores(self):
        """GIVEN cached report WITHOUT user_facing_scores
        WHEN transform_cached_report is called
        THEN key_scores and all_scores should be empty (graceful degradation)
        """
        cached_report = {
            'id': 1,
            'symbol': 'NVDA',
            'report_text': 'Test report...',
            'chart_base64': '',
            'report_generated_at': '2025-12-07T10:00:00',
            'report_json': {
                # NO user_facing_scores field
                'indicators': {},
                'price_history': []
            }
        }

        ticker_info = self.ticker_service.get_ticker_info('NVDA19')

        response = await self.transformer.transform_cached_report(
            cached_report,
            ticker_info
        )

        # Should not crash, should return empty lists
        assert response.key_scores == []
        assert response.all_scores == []
