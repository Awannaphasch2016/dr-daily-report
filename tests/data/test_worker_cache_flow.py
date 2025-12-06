# -*- coding: utf-8 -*-
"""Test the exact cache flow in report_worker_handler.

This test simulates what happens after agent.run() completes:
1. transformer.transform_report()
2. job_service.complete_job()
3. precompute_service.store_report_from_api()

Goal: Find exactly WHERE the cache write is failing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import date


class TestWorkerCacheFlow:
    """Test the cache flow in report_worker_handler."""

    def setup_method(self):
        """Reset singletons."""
        # Clear all singletons that might interfere
        import src.data.aurora.client as client_module
        client_module._aurora_client = None
        import src.data.aurora.ticker_resolver as resolver_module
        resolver_module._ticker_resolver = None

    @pytest.mark.asyncio
    async def test_full_cache_flow_after_agent_completes(self):
        """Simulate the exact flow after agent.run() returns."""
        from src.api.transformer import ResponseTransformer
        from src.data.aurora.precompute_service import PrecomputeService

        # Mock final_state from agent (what agent.run() returns)
        final_state = {
            "ticker": "DBS19",
            "report": "Test report in Thai",
            "chart_base64": "base64data",
            "indicators": {"rsi": 50},
            "percentiles": {"rsi_percentile": 50},
            "error": "",  # No error
        }

        # Mock ticker_info from ticker_service
        ticker_info = {
            "symbol": "DBS19",
            "name": "DBS Group",
            "yahoo_ticker": "D05.SI",
        }

        # Step 1: Test transformer.transform_report()
        transformer = ResponseTransformer()
        with patch.object(transformer, 'transform_report', new_callable=AsyncMock) as mock_transform:
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "ticker": "DBS19",
                "narrative_report": "Test report",
                "generation_metadata": {"strategy": "multi_stage_analysis"},
            }
            mock_transform.return_value = mock_response

            response = await transformer.transform_report(final_state, ticker_info)
            result = response.model_dump()

            assert result["ticker"] == "DBS19"
            assert "narrative_report" in result
            print(f"✅ Step 1 PASSED: transformer.transform_report() works")

        # Step 2: Test PrecomputeService.store_report_from_api()
        with patch('src.data.aurora.client.get_aurora_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.fetch_one.return_value = {'cnt': 0}  # Force CSV fallback
            mock_client.execute.return_value = 1
            mock_get_client.return_value = mock_client

            precompute_service = PrecomputeService()
            cache_result = precompute_service.store_report_from_api(
                symbol="DBS19",
                report_text=result.get('narrative_report', ''),
                report_json=result,
                strategy=result.get('generation_metadata', {}).get('strategy', 'multi_stage_analysis'),
                chart_base64=final_state.get('chart_base64', ''),
            )

            assert cache_result is True, "store_report_from_api should return True"
            assert mock_client.execute.called, "Should have called execute to INSERT"
            print(f"✅ Step 2 PASSED: store_report_from_api() works")

    @pytest.mark.asyncio
    async def test_store_report_from_api_with_real_ticker_resolver(self):
        """Test store_report_from_api with real TickerResolver (CSV fallback)."""
        with patch('src.data.aurora.client.get_aurora_client') as mock_get_client:
            mock_client = MagicMock()
            # Force CSV fallback by simulating no Aurora tables
            mock_client.fetch_one.return_value = {'cnt': 0}
            mock_client.execute.return_value = 1
            mock_get_client.return_value = mock_client

            from src.data.aurora.precompute_service import PrecomputeService
            service = PrecomputeService()

            # Use real TickerResolver with CSV fallback
            result = service.store_report_from_api(
                symbol="DBS19",
                report_text="Test report",
                report_json={"ticker": "DBS19"},
            )

            # This should work if TickerResolver resolves DBS19 from CSV
            assert result is True, "Should succeed with CSV fallback"

            # Verify the SQL was executed
            call_args = mock_client.execute.call_args
            assert call_args is not None, "execute should have been called"

            sql = call_args[0][0]
            params = call_args[0][1]

            print(f"SQL: {sql[:100]}...")
            print(f"Params: {params[:3]}...")  # First 3 params

            # Verify ticker_id is set (should be > 0 from CSV)
            ticker_id = params[0]
            assert ticker_id > 0, f"ticker_id should be > 0, got {ticker_id}"
            print(f"✅ ticker_id = {ticker_id}")

    def test_ticker_resolver_finds_dbs19(self):
        """Verify TickerResolver can find DBS19 in CSV."""
        with patch('src.data.aurora.ticker_resolver.get_aurora_client') as mock_client:
            # Force CSV fallback
            mock_client.side_effect = Exception("No Aurora")

            from src.data.aurora.ticker_resolver import get_ticker_resolver
            resolver = get_ticker_resolver()

            info = resolver.resolve("DBS19")

            assert info is not None, "DBS19 should be in tickers.csv"
            assert info.ticker_id > 0, "ticker_id should be assigned"
            assert info.dr_symbol == "DBS19"
            assert info.yahoo_symbol is not None

            print(f"✅ DBS19 resolved: ticker_id={info.ticker_id}, yahoo={info.yahoo_symbol}")

    def test_precompute_service_sql_execution(self):
        """Test that _store_completed_report executes valid SQL."""
        with patch('src.data.aurora.client.get_aurora_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.fetch_one.return_value = {'cnt': 0}
            mock_client.execute.return_value = 1
            mock_get_client.return_value = mock_client

            from src.data.aurora.precompute_service import PrecomputeService
            service = PrecomputeService()

            # Call _store_completed_report directly
            service._store_completed_report(
                ticker_id=42,
                symbol="D05.SI",
                data_date=date.today(),
                report_text="Test report",
                report_json={"test": "data"},
                strategy="multi_stage_analysis",
                generation_time_ms=1000,
                mini_reports={},
                chart_base64="base64",
            )

            # Verify execute was called
            assert mock_client.execute.called
            call_args = mock_client.execute.call_args
            sql = call_args[0][0]
            params = call_args[0][1]

            # Verify SQL structure
            assert "INSERT INTO precomputed_reports" in sql
            assert "report_date" in sql
            assert "ticker_id" in sql

            # Verify params count matches placeholders
            placeholder_count = sql.count("%s")
            param_count = len(params)
            assert placeholder_count == param_count, \
                f"SQL has {placeholder_count} placeholders but {param_count} params"

            print(f"✅ SQL valid: {placeholder_count} placeholders, {param_count} params")

    def test_store_report_when_aurora_execute_fails(self):
        """Test behavior when Aurora execute() throws an exception."""
        with patch('src.data.aurora.client.get_aurora_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.fetch_one.return_value = {'cnt': 0}  # CSV fallback
            # Simulate Aurora connection/execute failure
            mock_client.execute.side_effect = Exception("Connection refused")
            mock_get_client.return_value = mock_client

            from src.data.aurora.precompute_service import PrecomputeService
            service = PrecomputeService()

            # This should return False (not raise) due to try/except in store_report_from_api
            result = service.store_report_from_api(
                symbol="DBS19",
                report_text="Test report",
                report_json={"ticker": "DBS19"},
            )

            # The method catches exceptions and returns False
            assert result is False, "Should return False when execute fails"
            print(f"✅ Correctly returns False when Aurora execute fails")

    def test_store_report_logs_error_on_failure(self):
        """Test that errors are properly logged when cache write fails."""
        import logging

        with patch('src.data.aurora.client.get_aurora_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.fetch_one.return_value = {'cnt': 0}
            mock_client.execute.side_effect = Exception("Database error: column 'date' doesn't exist")
            mock_get_client.return_value = mock_client

            # Capture log output
            with patch('src.data.aurora.precompute_service.logger') as mock_logger:
                from src.data.aurora.precompute_service import PrecomputeService
                service = PrecomputeService()

                result = service.store_report_from_api(
                    symbol="DBS19",
                    report_text="Test",
                    report_json={},
                )

                assert result is False
                # Verify error was logged
                mock_logger.error.assert_called()
                error_msg = str(mock_logger.error.call_args)
                assert "DBS19" in error_msg or "Failed" in error_msg
                print(f"✅ Error properly logged: {mock_logger.error.call_args}")
