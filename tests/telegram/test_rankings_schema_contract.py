# -*- coding: utf-8 -*-
"""
Test that UI receives data matching scheduler's output schema.

This is the CONSUMER side of the schema contract.
"""

import pytest
from datetime import date
from tests.contracts.cached_report_schema import validate_cached_report


class TestRankingsSchemaContract:
    """Verify rankings API returns data matching schema contract"""

    @pytest.mark.asyncio
    async def test_rankings_api_returns_schema_compliant_data(self):
        """
        Test that rankings API returns chart_data matching schema.

        This ensures UI can safely assume data structure.
        """
        from src.api.rankings_service import get_rankings_service

        service = get_rankings_service()

        # Fetch rankings (which queries Aurora cache)
        rankings = await service.get_rankings('top_gainers')

        assert len(rankings) > 0, "Rankings should have data"

        # Check first ticker has complete schema
        first_ticker = rankings[0]

        # Build cached report format from API response
        cached_format = {
            'ticker': first_ticker.ticker,
            'report_date': date.today().isoformat(),
            'price_history': first_ticker.chart_data.get('price_history', []) if first_ticker.chart_data else [],
            'projections': first_ticker.chart_data.get('projections', []) if first_ticker.chart_data else [],
            'initial_investment': first_ticker.chart_data.get('initial_investment', 1000.0) if first_ticker.chart_data else 1000.0,
            'user_facing_scores': first_ticker.key_scores if first_ticker.key_scores else {},
            'stance': first_ticker.stance if first_ticker.stance else 'neutral',
            'report_text': '',  # Not returned by rankings API
            'strategy': 'multi-stage',
            'created_at': ''
        }

        # Validate against schema
        is_valid, errors = validate_cached_report(cached_format)

        assert is_valid, \
            f"Rankings API returned non-compliant data for {first_ticker.ticker}:\n" + \
            "\n".join(f"  - {e}" for e in errors)

    @pytest.mark.asyncio
    async def test_all_ranking_categories_conform_to_schema(self):
        """
        Test that ALL ranking categories return schema-compliant data.

        Prevents schema drift across different ranking types.
        """
        from src.api.rankings_service import get_rankings_service

        service = get_rankings_service()

        categories = ['top_gainers', 'top_losers', 'most_active', 'high_momentum']
        violations = []

        for category in categories:
            try:
                rankings = await service.get_rankings(category)

                if len(rankings) == 0:
                    violations.append(f"{category}: No rankings returned")
                    continue

                # Check first ticker from each category
                first_ticker = rankings[0]

                cached_format = {
                    'ticker': first_ticker.ticker,
                    'report_date': date.today().isoformat(),
                    'price_history': first_ticker.chart_data.get('price_history', []) if first_ticker.chart_data else [],
                    'projections': first_ticker.chart_data.get('projections', []) if first_ticker.chart_data else [],
                    'initial_investment': first_ticker.chart_data.get('initial_investment', 1000.0) if first_ticker.chart_data else 1000.0,
                    'user_facing_scores': first_ticker.key_scores if first_ticker.key_scores else {},
                    'stance': first_ticker.stance if first_ticker.stance else 'neutral',
                    'report_text': '',
                    'strategy': 'multi-stage',
                    'created_at': ''
                }

                is_valid, errors = validate_cached_report(cached_format)
                if not is_valid:
                    violations.append(f"{category} ({first_ticker.ticker}):\n" + "\n".join(f"    - {e}" for e in errors))

            except Exception as e:
                violations.append(f"{category}: Exception - {e}")

        assert len(violations) == 0, \
            "Schema violations found:\n" + "\n".join(violations)
