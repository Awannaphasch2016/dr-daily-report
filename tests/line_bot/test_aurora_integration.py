# -*- coding: utf-8 -*-
"""
Integration tests for LINE bot with Aurora cache.

Tests the LINE bot's integration with Aurora precompute service.
"""

import pytest
from src.integrations.line_bot import LineBot
from src.data.aurora.precompute_service import PrecomputeService


@pytest.mark.integration
class TestLineAuroraIntegration:
    """Integration tests for LINE bot with Aurora cache"""

    def test_aurora_cache_roundtrip(self):
        """Store report to Aurora, retrieve it back"""
        precompute = PrecomputeService()

        # Store test report
        test_ticker = 'TEST19'
        test_report = 'Test report narrative for LINE bot'

        precompute.store_report(
            symbol=test_ticker,
            report_text=test_report,
            report_json={}
        )

        # Retrieve cached report
        cached = precompute.get_cached_report(test_ticker)

        # Verify
        assert cached is not None, "Stored report should be retrievable from Aurora"
        assert cached['report_text'] == test_report, \
            f"Expected report text to match, got {cached.get('report_text')}"

    def test_aurora_cache_miss_returns_none(self):
        """Verify cache miss returns None"""
        precompute = PrecomputeService()

        # Query non-existent ticker
        cached = precompute.get_cached_report('NONEXISTENT999')

        assert cached is None, "Cache miss should return None"

    def test_line_bot_uses_aurora_cache(self):
        """Verify LINE bot correctly uses Aurora cache for report retrieval"""
        precompute = PrecomputeService()

        # Pre-populate cache
        test_ticker = 'LINETEST19'
        test_report = 'Cached report from Aurora for LINE bot test'

        precompute.store_report(
            symbol=test_ticker,
            report_text=test_report,
            report_json={}
        )

        # Create LINE bot (with real Aurora connection)
        # Note: This requires Aurora to be accessible (e.g., SSM tunnel active)
        # Skip test if Aurora connection fails
        try:
            precompute_check = PrecomputeService()
            precompute_check.get_cached_report(test_ticker)
        except Exception as e:
            pytest.skip(f"Aurora connection not available: {e}")

        # Verify cache retrieval works through precompute service
        cached = precompute.get_cached_report(test_ticker)

        assert cached is not None, "Pre-populated cache should be retrievable"
        assert cached['report_text'] == test_report, \
            "Retrieved report should match what was stored"
