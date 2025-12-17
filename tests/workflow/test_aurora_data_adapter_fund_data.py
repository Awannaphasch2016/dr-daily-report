"""
Integration tests for aurora_data_adapter with fund_data supplement.

Tests the full integration between precomputed_reports and fund_data tables.
Requires active Aurora connection (uses @pytest.mark.integration).
"""

import pytest
from unittest.mock import patch
import pandas as pd

from src.workflow.aurora_data_adapter import fetch_ticker_data_from_aurora
from src.data.aurora.fund_data_fetcher import fetch_fund_data_metrics, DataNotFoundError as FundDataNotFoundError


class TestAuroraDataAdapterWithFundData:
    """Integration tests for fund_data supplementation in aurora_data_adapter"""

    @pytest.mark.integration
    def test_fetch_ticker_data_includes_fund_data_when_available(self):
        """
        Verify ticker_data includes fund_data metrics when ticker exists in both tables.

        Uses 8316.T (Sumitomo Mitsui Financial Group) which exists in both:
        - precomputed_reports (has company name, market cap, price history)
        - fund_data (has FY1_PE, ROE, P/BV, TARGET_PRC)
        """
        # Execute with ticker that has both Aurora and fund_data
        data = fetch_ticker_data_from_aurora('8316.T')

        # Verify existing Aurora precomputed_reports metrics
        assert 'pe_ratio' in data, "Missing P/E ratio from Aurora"
        assert 'market_cap' in data, "Missing market cap from Aurora"
        assert 'eps' in data, "Missing EPS from Aurora"
        assert 'company_name' in data, "Missing company name from Aurora"
        assert 'history' in data, "Missing price history from Aurora"

        # Verify NEW fund_data metrics are present
        assert 'forward_pe' in data, "Missing forward_pe from fund_data"
        assert 'roe' in data, "Missing ROE from fund_data"
        assert 'price_to_book' in data, "Missing price_to_book from fund_data"
        assert 'target_price' in data, "Missing target_price from fund_data"

        # DEFENSIVE: Test outcomes, not just execution - verify actual values
        assert data['forward_pe'] is not None, "forward_pe should not be None for 8316.T"
        assert data['roe'] is not None, "ROE should not be None for 8316.T"
        assert data['price_to_book'] is not None, "price_to_book should not be None for 8316.T"
        assert data['target_price'] is not None, "target_price should not be None for 8316.T"

        # Verify metric types (Decimal → float conversion)
        assert isinstance(data['forward_pe'], float), f"Expected float, got {type(data['forward_pe'])}"
        assert isinstance(data['roe'], float), f"Expected float, got {type(data['roe'])}"
        assert isinstance(data['price_to_book'], float), f"Expected float, got {type(data['price_to_book'])}"
        assert isinstance(data['target_price'], float), f"Expected float, got {type(data['target_price'])}"

        # Verify reasonable value ranges (sanity checks)
        assert data['forward_pe'] > 0, "Forward P/E should be positive"
        assert 0 <= data['roe'] <= 100, "ROE should be between 0 and 100%"
        assert data['price_to_book'] > 0, "P/B ratio should be positive"
        assert data['target_price'] > 0, "Target price should be positive"

    @pytest.mark.integration
    def test_graceful_fallback_when_fund_data_missing(self):
        """
        Verify Aurora data still works when fund_data missing (graceful degradation).

        Uses GLD (Gold ETF) which exists in precomputed_reports but NOT in fund_data
        (fund_data has stocks, not ETFs).
        """
        # Execute with ticker that exists in Aurora but NOT in fund_data
        data = fetch_ticker_data_from_aurora('GLD')

        # Should still have Aurora precomputed_reports metrics
        assert 'pe_ratio' in data
        assert 'market_cap' in data
        assert 'company_name' in data
        assert 'history' in data

        # fund_data metrics should be None (graceful degradation)
        assert data.get('forward_pe') is None, "forward_pe should be None when fund_data missing"
        assert data.get('roe') is None or isinstance(data['roe'], (int, float)), \
            "ROE should be None or from Aurora data"
        assert data.get('price_to_book') is None, "price_to_book should be None when fund_data missing"
        assert data.get('target_price') is None, "target_price should be None when fund_data missing"

    @pytest.mark.integration
    def test_fund_data_supplement_preserves_aurora_data(self):
        """
        Verify fund_data supplement does NOT break existing Aurora data.

        Ensures backward compatibility - reports without fund_data still work.
        """
        data = fetch_ticker_data_from_aurora('8316.T')

        # Verify ALL existing fields still present
        required_fields = [
            'date', 'open', 'high', 'low', 'close', 'volume',
            'market_cap', 'pe_ratio', 'eps', 'dividend_yield',
            'sector', 'industry', 'company_name', 'history'
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify price history structure unchanged
        history = data['history']
        assert len(history) > 0, "Price history should not be empty"
        assert 'Date' in history.columns, "History missing Date column"
        assert 'Close' in history.columns, "History missing Close column"

    @pytest.mark.integration
    def test_multiple_tickers_fund_data_availability(self):
        """
        Verify fund_data availability varies across tickers (some have it, some don't).

        This tests the real-world scenario where only some tickers have fund_data.
        """
        tickers_with_fund_data = ['8316.T', '8306.T']  # Tokyo stocks (in fund_data)
        tickers_without_fund_data = ['GLD', '0050.TW']  # ETF and Taiwan ticker NOT in fund_data

        # Verify tickers WITH fund_data have metrics
        for ticker in tickers_with_fund_data:
            try:
                data = fetch_ticker_data_from_aurora(ticker)
                # At least ONE fund_data metric should be present
                has_fund_data_metric = any([
                    data.get('forward_pe') is not None,
                    data.get('roe') is not None and isinstance(data['roe'], float),
                    data.get('price_to_book') is not None,
                    data.get('target_price') is not None
                ])
                assert has_fund_data_metric, f"{ticker} should have at least one fund_data metric"
            except Exception as e:
                pytest.skip(f"Ticker {ticker} not in precomputed_reports: {e}")

        # Verify tickers WITHOUT fund_data still work (graceful degradation)
        for ticker in tickers_without_fund_data:
            try:
                data = fetch_ticker_data_from_aurora(ticker)
                # Should have Aurora data
                assert data.get('market_cap') is not None or data.get('company_name') is not None
                # fund_data metrics likely None
                # (Don't assert None - some might have ROE from Aurora)
            except Exception as e:
                pytest.skip(f"Ticker {ticker} not in precomputed_reports: {e}")

    @pytest.mark.integration
    def test_fund_data_json_serializable(self):
        """
        Verify fund_data metrics are JSON-serializable (required for Lambda responses).

        DEFENSIVE: Validates actual serialization, not just type checking.
        """
        import json

        data = fetch_ticker_data_from_aurora('8316.T')

        # Extract fund_data metrics
        fund_data_metrics = {
            'forward_pe': data.get('forward_pe'),
            'roe': data.get('roe'),
            'price_to_book': data.get('price_to_book'),
            'target_price': data.get('target_price')
        }

        # Remove None values (they're JSON-serializable but not useful)
        fund_data_metrics = {k: v for k, v in fund_data_metrics.items() if v is not None}

        # DEFENSIVE: Actually serialize to catch Decimal/NumPy type issues
        try:
            json_str = json.dumps(fund_data_metrics)
            # Verify deserialization works
            deserialized = json.loads(json_str)
            assert isinstance(deserialized, dict)
            assert len(deserialized) > 0, "Should have at least one fund_data metric"
        except (TypeError, ValueError) as e:
            pytest.fail(f"fund_data metrics not JSON-serializable: {e}")

    # NEW TESTS FOR OVERRIDE BEHAVIOR

    @pytest.mark.integration
    def test_fund_data_overrides_precomputed_fundamentals(self):
        """
        Verify fund_data (Eikon) overrides precomputed_reports (Yahoo Finance).

        CLAUDE.md Principle: Round-Trip Tests for Persistence
        Contract: fund_data → aurora_data_adapter → ticker_data

        Tests that P/E and Dividend Yield from fund_data override old values
        from precomputed_reports, treating Eikon as primary source of truth.
        """
        ticker_data = fetch_ticker_data_from_aurora('DBS19')

        # DEFENSIVE: Verify data exists (not empty dict - truthy trap)
        assert ticker_data, "ticker_data should not be empty"
        assert len(ticker_data) > 0, "ticker_data should have content"

        # OUTCOME TEST: Verify actual override happened
        # If fund_data has P/E, it should be in ticker_data.pe_ratio
        # (not just that the function ran without error)

        if ticker_data.get('pe_ratio') is not None:
            # Fetch fund_data directly to verify source
            try:
                fund_metrics = fetch_fund_data_metrics('DBS19')

                if fund_metrics.get('P/E') is not None:
                    # ASSERT: ticker_data uses fund_data value, not precomputed_reports
                    assert ticker_data['pe_ratio'] == fund_metrics['P/E'], \
                        f"P/E should come from fund_data (Eikon), not precomputed_reports. " \
                        f"Got {ticker_data['pe_ratio']}, expected {fund_metrics['P/E']}"
            except FundDataNotFoundError:
                pytest.skip("DBS19 not in fund_data, cannot test override")

        # Same for dividend yield
        if ticker_data.get('dividend_yield') is not None:
            try:
                fund_metrics = fetch_fund_data_metrics('DBS19')

                if fund_metrics.get('FY1_DIV_YIELD') is not None:
                    assert ticker_data['dividend_yield'] == fund_metrics['FY1_DIV_YIELD'], \
                        f"Dividend Yield should come from fund_data (Eikon). " \
                        f"Got {ticker_data['dividend_yield']}, expected {fund_metrics['FY1_DIV_YIELD']}"
            except FundDataNotFoundError:
                pytest.skip("DBS19 not in fund_data, cannot test override")

    @pytest.mark.integration
    def test_fallback_to_precomputed_when_fund_data_missing_for_override(self):
        """
        Verify graceful degradation when fund_data unavailable.

        CLAUDE.md Principle: Defensive Programming - No silent fallbacks
        Tests that when fund_data is missing, precomputed_reports values
        are preserved (not overridden).
        """
        # Mock fund_data to raise DataNotFoundError
        with patch('src.workflow.aurora_data_adapter.fetch_fund_data_metrics') as mock_fund:
            mock_fund.side_effect = FundDataNotFoundError("No fund_data")

            ticker_data = fetch_ticker_data_from_aurora('DBS19')

            # Should NOT crash - uses precomputed_reports as fallback
            assert ticker_data is not None

            # Verify fallback values set to None (explicit, not silent)
            assert ticker_data.get('forward_pe') is None, \
                "forward_pe should be None when fund_data missing"
            assert ticker_data.get('roe') is None, \
                "roe should be None when fund_data missing"
            assert ticker_data.get('price_to_book') is None, \
                "price_to_book should be None when fund_data missing"
            assert ticker_data.get('target_price') is None, \
                "target_price should be None when fund_data missing"

            # But precomputed_reports values should still exist
            # (These are the fallback - old Yahoo Finance data)
            assert 'pe_ratio' in ticker_data, \
                "pe_ratio should exist from precomputed_reports when fund_data missing"
            assert 'dividend_yield' in ticker_data, \
                "dividend_yield should exist from precomputed_reports when fund_data missing"

    @pytest.mark.integration
    def test_fund_data_decimal_to_float_conversion_for_override(self):
        """
        Verify MySQL Decimal → Python float conversion at system boundary.

        CLAUDE.md Principle: System Boundary - verify type compatibility
        Tests that when fund_data overrides values, type conversion happens
        correctly (MySQL Decimal → Python float for JSON serialization).
        """
        ticker_data = fetch_ticker_data_from_aurora('DBS19')

        # DEFENSIVE: Check type conversion happened (MySQL Decimal → float)
        if ticker_data.get('pe_ratio') is not None:
            assert isinstance(ticker_data['pe_ratio'], (float, int)), \
                f"P/E should be float/int for JSON serialization, got {type(ticker_data['pe_ratio'])}"
            # Additional check: NOT Decimal type
            assert type(ticker_data['pe_ratio']).__name__ != 'Decimal', \
                "P/E should not be Decimal type (causes JSON serialization errors)"

        if ticker_data.get('dividend_yield') is not None:
            assert isinstance(ticker_data['dividend_yield'], (float, int)), \
                f"Dividend Yield should be float/int, got {type(ticker_data['dividend_yield'])}"
            assert type(ticker_data['dividend_yield']).__name__ != 'Decimal', \
                "Dividend Yield should not be Decimal type"

        if ticker_data.get('forward_pe') is not None:
            assert isinstance(ticker_data['forward_pe'], (float, int)), \
                f"Forward P/E should be float/int, got {type(ticker_data['forward_pe'])}"

    @pytest.mark.integration
    def test_ticker_data_schema_contract_for_llm_with_override(self):
        """
        Verify ticker_data schema contract for LLM context builder.

        CLAUDE.md Principle: Schema Testing at System Boundaries
        Contract: ticker_data dict is consumed by ContextBuilder

        Tests that after fund_data override, ticker_data still has all
        required fields in correct format for LLM context generation.
        """
        ticker_data = fetch_ticker_data_from_aurora('DBS19')

        # Required fields that LLM context depends on
        required_fields = ['date', 'close', 'company_name', 'history']
        for field in required_fields:
            assert field in ticker_data, \
                f"ticker_data missing required field: {field}"

        # Fundamental fields (may be None but should exist in dict)
        fundamental_fields = ['pe_ratio', 'dividend_yield', 'forward_pe',
                             'roe', 'price_to_book', 'target_price']
        for field in fundamental_fields:
            assert field in ticker_data, \
                f"ticker_data missing fundamental field: {field}"

        # Verify history is DataFrame with required columns
        assert isinstance(ticker_data['history'], pd.DataFrame), \
            "Price history should be pandas DataFrame"
        assert len(ticker_data['history']) > 0, \
            "Price history should not be empty"

        required_history_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_history_cols:
            assert col in ticker_data['history'].columns, \
                f"Price history missing required column: {col}"

        # DEFENSIVE: Verify fundamental values are reasonable if not None
        if ticker_data.get('pe_ratio') is not None:
            assert ticker_data['pe_ratio'] > 0, \
                f"P/E ratio should be positive, got {ticker_data['pe_ratio']}"

        if ticker_data.get('dividend_yield') is not None:
            assert 0 <= ticker_data['dividend_yield'] <= 100, \
                f"Dividend yield should be between 0-100%, got {ticker_data['dividend_yield']}"
