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
        import os

        service = get_rankings_service()

        # Fetch rankings (which queries Aurora cache)
        rankings = await service.get_rankings('top_gainers')

        # Skip test if Aurora is not configured (CI environment)
        if len(rankings) == 0 and not os.environ.get('AURORA_HOST') and not os.environ.get('AURORA_SECRET_ARN'):
            pytest.skip("Aurora not configured - cannot test schema with live cache data")

        assert len(rankings) > 0, "Rankings should have data"

        # Check first ticker has complete schema
        first_ticker = rankings[0]

        # rankings_service.get_rankings() returns List[Dict], not Pydantic models
        # Handle dict return type
        ticker = first_ticker.get('ticker') if isinstance(first_ticker, dict) else first_ticker.ticker
        chart_data = first_ticker.get('chart_data', {}) if isinstance(first_ticker, dict) else first_ticker.chart_data

        # Skip EARLY if cache data is incomplete (CI environment without Aurora)
        # Check before extracting other fields to avoid validation errors
        if not os.environ.get('AURORA_HOST') and not os.environ.get('AURORA_SECRET_ARN'):
            # Check if chart_data exists and has content
            if not chart_data or len(chart_data.get('price_history', [])) == 0:
                pytest.skip("Aurora not configured - cache data incomplete (empty price_history)")

        # Continue extracting fields only if we're not skipping
        key_scores = first_ticker.get('key_scores', {}) if isinstance(first_ticker, dict) else first_ticker.key_scores
        stance = first_ticker.get('stance', 'neutral') if isinstance(first_ticker, dict) else first_ticker.stance

        # Build cached report format from API response
        cached_format = {
            'ticker': ticker,
            'report_date': date.today().isoformat(),
            'price_history': chart_data.get('price_history', []) if chart_data else [],
            'projections': chart_data.get('projections', []) if chart_data else [],
            'initial_investment': chart_data.get('initial_investment', 1000.0) if chart_data else 1000.0,
            'user_facing_scores': key_scores if key_scores else {},
            'stance': stance if stance else 'neutral',
            'report_text': '',  # Not returned by rankings API
            'created_at': ''
        }

        # Validate against schema
        is_valid, errors = validate_cached_report(cached_format)

        assert is_valid, \
            f"Rankings API returned non-compliant data for {ticker}:\n" + \
            "\n".join(f"  - {e}" for e in errors)

    @pytest.mark.asyncio
    async def test_all_ranking_categories_conform_to_schema(self):
        """
        Test that ALL ranking categories return schema-compliant data.

        Prevents schema drift across different ranking types.
        """
        from src.api.rankings_service import get_rankings_service
        import os

        service = get_rankings_service()

        # Use correct category names from RankingCategory enum
        categories = ['top_gainers', 'top_losers', 'volume_surge', 'trending']
        violations = []

        for category in categories:
            try:
                rankings = await service.get_rankings(category)

                if len(rankings) == 0:
                    # Skip if Aurora is not configured (CI environment)
                    if not os.environ.get('AURORA_HOST') and not os.environ.get('AURORA_SECRET_ARN'):
                        continue  # Skip this category, don't mark as violation
                    else:
                        violations.append(f"{category}: No rankings returned")
                    continue

                # Check first ticker from each category
                first_ticker = rankings[0]

                # Handle dict return type
                ticker = first_ticker.get('ticker') if isinstance(first_ticker, dict) else first_ticker.ticker
                chart_data = first_ticker.get('chart_data', {}) if isinstance(first_ticker, dict) else first_ticker.chart_data

                # Skip EARLY if cache data is incomplete (CI environment without Aurora)
                # Check before extracting other fields to avoid validation errors
                if not os.environ.get('AURORA_HOST') and not os.environ.get('AURORA_SECRET_ARN'):
                    # Check if chart_data exists and has content
                    if not chart_data or len(chart_data.get('price_history', [])) == 0:
                        continue  # Skip this category, cache data incomplete

                # Continue extracting fields only if we're not skipping
                key_scores = first_ticker.get('key_scores', {}) if isinstance(first_ticker, dict) else first_ticker.key_scores
                stance = first_ticker.get('stance', 'neutral') if isinstance(first_ticker, dict) else first_ticker.stance

                cached_format = {
                    'ticker': ticker,
                    'report_date': date.today().isoformat(),
                    'price_history': chart_data.get('price_history', []) if chart_data else [],
                    'projections': chart_data.get('projections', []) if chart_data else [],
                    'initial_investment': chart_data.get('initial_investment', 1000.0) if chart_data else 1000.0,
                    'user_facing_scores': key_scores if key_scores else {},
                    'stance': stance if stance else 'neutral',
                    'report_text': '',
                    'created_at': ''
                }

                is_valid, errors = validate_cached_report(cached_format)
                if not is_valid:
                    violations.append(f"{category} ({ticker}):\n" + "\n".join(f"    - {e}" for e in errors))

            except Exception as e:
                violations.append(f"{category}: Exception - {e}")

        assert len(violations) == 0, \
            "Schema violations found:\n" + "\n".join(violations)
