# -*- coding: utf-8 -*-
"""
Test that scheduler writes data matching UI's expected schema.

This is the PRODUCER side of the schema contract.
"""

import pytest
from datetime import date
from tests.contracts.cached_report_schema import validate_cached_report


class TestSchedulerSchemaContract:
    """Verify scheduler produces data matching schema contract"""

    @pytest.mark.integration
    def test_precompute_output_matches_schema(self):
        """
        Round-trip test: scheduler writes data, validate against schema.

        This test ensures scheduler doesn't write incomplete data
        that will break UI.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        # Generate report via scheduler
        service = PrecomputeService()
        result = service.compute_for_ticker('NVDA19', include_report=True)

        # Check that report was generated successfully
        assert result.get('report') is True, f"Report generation failed: {result.get('error', 'Unknown error')}"
        assert 'error' not in result, f"Precompute failed: {result.get('error')}"

        # Retrieve from Aurora (round-trip)
        cached = service.get_cached_report('NVDA19', date.today())

        assert cached is not None, "Precomputed data not found in Aurora"

        # Validate against schema contract
        is_valid, errors = validate_cached_report(cached)

        assert is_valid, f"Schema contract violated:\n" + "\n".join(f"  - {e}" for e in errors)

    @pytest.mark.integration
    def test_parallel_precompute_all_conform_to_schema(self):
        """
        Test that ALL tickers in parallel_precompute conform to schema.

        Prevents situation where some tickers work but others fail silently.
        """
        from src.data.aurora.precompute_service import PrecomputeService

        service = PrecomputeService()

        # Sample 5 recently cached tickers
        sample_tickers = ['NVDA19', 'DBS19', 'MWG19', 'TAIWAN19', 'TENCENT19']

        violations = []
        for ticker in sample_tickers:
            cached = service.get_cached_report(ticker, date.today())

            if cached is None:
                violations.append(f"{ticker}: Not found in cache")
                continue

            is_valid, errors = validate_cached_report(cached)
            if not is_valid:
                violations.append(f"{ticker}:\n" + "\n".join(f"    - {e}" for e in errors))

        assert len(violations) == 0, \
            "Schema violations found:\n" + "\n".join(violations)
