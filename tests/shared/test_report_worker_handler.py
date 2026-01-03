# -*- coding: utf-8 -*-
"""Unit tests for report_worker_handler caching behavior.

TDD Goal: Verify that PrecomputeService.store_report_from_api() is called
after job completion, with correct arguments, and that caching failures
don't break job completion.

These tests answer: "Is the caching code path executed?"
- Mocks all external dependencies
- Verifies method calls and arguments
- Fast feedback loop for debugging
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch


class TestReportWorkerCaching:
    """Test caching behavior in report_worker_handler."""

    def setup_method(self):
        """Reset singletons before each test."""
        # Clear module-level singletons
        import src.api.job_service as job_mod
        import src.api.ticker_service as ticker_mod
        import src.api.transformer as transformer_mod

        job_mod._job_service = None
        ticker_mod._ticker_service = None
        transformer_mod._transformer = None

    @pytest.fixture
    def mock_dependencies(self):
        """Create all mocked dependencies for process_record."""
        # Mock TickerAnalysisAgent
        mock_agent_class = MagicMock()
        mock_agent = MagicMock()
        mock_agent.graph.invoke.return_value = {
            "ticker": "D05.SI",  # Yahoo symbol (worker resolves DBS19 → D05.SI)
            "report": "Test Thai report",
            "chart_base64": "BASE64_CHART_DATA",
            "indicators": {"rsi": 50},
            "percentiles": {"rsi_percentile": 50},
            "error": "",  # No error - successful run
        }
        mock_agent_class.return_value = mock_agent

        # Mock transformer (async)
        mock_transformer = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "ticker": "D05.SI",  # Yahoo symbol (worker uses Yahoo symbols for Aurora queries)
            "narrative_report": "Thai language report text",
            "generation_metadata": {},
        }
        mock_transformer.transform_report = AsyncMock(return_value=mock_response)

        # Mock job_service
        mock_job_service = MagicMock()
        mock_job_service.start_job = MagicMock()
        mock_job_service.complete_job = MagicMock()
        mock_job_service.fail_job = MagicMock()

        # Mock ticker_service
        mock_ticker_service = MagicMock()
        mock_ticker_service.get_ticker_info.return_value = {
            "symbol": "DBS19",
            "name": "DBS Group Holdings",
            "yahoo_ticker": "D05.SI",
        }

        # Mock PrecomputeService
        mock_precompute_class = MagicMock()
        mock_precompute = MagicMock()
        mock_precompute.store_report_from_api.return_value = True
        mock_precompute_class.return_value = mock_precompute

        return {
            "agent_class": mock_agent_class,
            "agent": mock_agent,
            "transformer": mock_transformer,
            "job_service": mock_job_service,
            "ticker_service": mock_ticker_service,
            "precompute_class": mock_precompute_class,
            "precompute": mock_precompute,
        }

    @pytest.mark.asyncio
    async def test_caching_called_after_job_complete(self, mock_dependencies):
        """Verify PrecomputeService.store_report_from_api() is called after job completes.

        This is the CORE test - answers "is caching code path executed?"
        """
        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_dependencies["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_dependencies["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_dependencies["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_dependencies["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mock_dependencies["precompute_class"]):

            from src.report_worker_handler import process_record

            # Create SQS record
            record = {
                "messageId": "test-msg-123",
                "body": json.dumps({"job_id": "rpt_test123", "ticker": "DBS19"})
            }

            # Execute
            await process_record(record)

            # Assert: Job was marked complete
            mock_dependencies["job_service"].complete_job.assert_called_once()
            call_args = mock_dependencies["job_service"].complete_job.call_args
            assert call_args[0][0] == "rpt_test123", "Should complete job with correct job_id"

            # Assert: PrecomputeService was instantiated
            mock_dependencies["precompute_class"].assert_called_once()

            # Assert: store_report_from_api was called
            mock_dependencies["precompute"].store_report_from_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_caching_called_with_correct_arguments(self, mock_dependencies):
        """Verify store_report_from_api receives correct arguments.

        Checks:
        - symbol matches ticker
        - report_text comes from result['narrative_report']
        - strategy comes from generation_metadata
        - chart_base64 comes from final_state (not result)
        """
        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_dependencies["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_dependencies["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_dependencies["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_dependencies["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mock_dependencies["precompute_class"]):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test-msg-456",
                "body": json.dumps({"job_id": "rpt_test456", "ticker": "DBS19"})
            }

            await process_record(record)

            # Get the call arguments
            call_kwargs = mock_dependencies["precompute"].store_report_from_api.call_args.kwargs

            # Verify each argument
            # Worker resolves DBS19 → D05.SI (Yahoo symbol) for Aurora queries
            assert call_kwargs["symbol"] == "D05.SI", \
                f"symbol should be 'D05.SI' (Yahoo symbol), got {call_kwargs.get('symbol')}"

            assert call_kwargs["report_text"] == "Thai language report text", \
                f"report_text should match narrative_report, got {call_kwargs.get('report_text')}"

            assert call_kwargs["chart_base64"] == "BASE64_CHART_DATA", \
                f"chart_base64 should be 'BASE64_CHART_DATA', got {call_kwargs.get('chart_base64')}"

            # Verify report_json is passed
            assert "report_json" in call_kwargs, "report_json should be passed"
            assert call_kwargs["report_json"]["ticker"] == "D05.SI"

    @pytest.mark.asyncio
    async def test_caching_failure_does_fail_job(self, mock_dependencies):
        """Verify job fails if Aurora storage fails.

        Aurora is now the primary storage (not optional) - reports MUST be stored
        for downstream PDF generation workflow.
        """
        # Make caching throw an exception
        mock_dependencies["precompute"].store_report_from_api.side_effect = Exception(
            "Aurora connection refused"
        )

        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_dependencies["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_dependencies["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_dependencies["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_dependencies["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mock_dependencies["precompute_class"]):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test-msg-789",
                "body": json.dumps({"job_id": "rpt_test789", "ticker": "DBS19"})
            }

            # SHOULD raise exception (Aurora storage is critical)
            with pytest.raises(Exception) as exc_info:
                await process_record(record)

            assert "Aurora connection refused" in str(exc_info.value)

            # Job should still be marked complete BEFORE storage attempted
            mock_dependencies["job_service"].complete_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_caching_returns_false_does_fail_job(self, mock_dependencies):
        """Verify job fails if store_report_from_api returns False.

        Aurora storage is critical - False indicates storage failed.
        """
        mock_dependencies["precompute"].store_report_from_api.return_value = False

        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_dependencies["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_dependencies["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_dependencies["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_dependencies["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mock_dependencies["precompute_class"]):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test-msg-warn",
                "body": json.dumps({"job_id": "rpt_warn", "ticker": "DBS19"})
            }

            # SHOULD raise exception (Aurora storage is critical)
            with pytest.raises(ValueError) as exc_info:
                await process_record(record)

            assert "Failed to store report for D05.SI" in str(exc_info.value)

            # Job should still be marked complete BEFORE storage attempted
            mock_dependencies["job_service"].complete_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_caching_not_called_when_agent_fails(self, mock_dependencies):
        """Verify caching is NOT called if agent returns error."""
        # Make agent return error state
        mock_dependencies["agent"].graph.invoke.return_value = {
            "ticker": "BAD19",
            "report": "",
            "chart_base64": "",
            "error": "Failed to fetch ticker data",  # Error state
        }

        # Mock resolver to return identity mapping (BAD19 → BAD19)
        mock_resolver = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.dr_symbol = "BAD19"
        mock_resolver.resolve.return_value = mock_resolved

        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_dependencies["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_dependencies["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_dependencies["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_dependencies["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mock_dependencies["precompute_class"]), \
             patch('src.report_worker_handler.get_ticker_resolver', return_value=mock_resolver):

            from src.report_worker_handler import process_record, AgentError

            record = {
                "messageId": "test-msg-error",
                "body": json.dumps({"job_id": "rpt_error", "ticker": "BAD19"})
            }

            # Should raise AgentError (agent error is re-raised for SQS DLQ)
            with pytest.raises(AgentError):
                await process_record(record)

            # Job should be marked failed (not complete)
            mock_dependencies["job_service"].fail_job.assert_called_once()
            mock_dependencies["job_service"].complete_job.assert_not_called()

            # Caching should NOT be attempted
            mock_dependencies["precompute"].store_report_from_api.assert_not_called()


class TestReportWorkerLambdaHandler:
    """Test the Lambda handler entry point."""

    @pytest.fixture(autouse=True)
    def mock_env_vars(self, monkeypatch):
        """Mock required environment variables (autouse for all tests)"""
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        monkeypatch.setenv('AURORA_HOST', 'test-host')
        monkeypatch.setenv('PDF_BUCKET_NAME', 'test-bucket')
        monkeypatch.setenv('JOBS_TABLE_NAME', 'test-table')

    @pytest.fixture
    def mock_process_record(self):
        """Mock process_record for handler tests."""
        with patch('src.report_worker_handler.process_record', new_callable=AsyncMock) as mock:
            yield mock

    def test_handler_processes_all_records(self, mock_process_record):
        """Verify handler processes each SQS record."""
        from src.report_worker_handler import handler

        event = {
            "Records": [
                {"messageId": "msg1", "body": '{"job_id": "rpt_1", "ticker": "DBS19"}'},
                {"messageId": "msg2", "body": '{"job_id": "rpt_2", "ticker": "OCBC19"}'},
            ]
        }

        result = handler(event, None)

        assert result["statusCode"] == 200
        assert "2 records" in result["body"]
        assert mock_process_record.call_count == 2

    def test_handler_returns_processed_count(self, mock_process_record):
        """Verify handler returns correct count."""
        from src.report_worker_handler import handler

        event = {"Records": []}

        result = handler(event, None)

        assert result["statusCode"] == 200
        assert "0 records" in result["body"]


class TestCachingArgumentSources:
    """Test that caching arguments come from correct sources.

    chart_base64 should come from final_state, not result.
    This is important because transform_report may not include chart_base64.
    """

    def setup_method(self):
        """Reset singletons."""
        import src.api.job_service as job_mod
        import src.api.ticker_service as ticker_mod
        import src.api.transformer as transformer_mod

        job_mod._job_service = None
        ticker_mod._ticker_service = None
        transformer_mod._transformer = None

    @pytest.mark.asyncio
    async def test_chart_base64_from_final_state_not_result(self):
        """Verify chart_base64 comes from final_state, not result.

        The handler code should use:
            chart_base64=final_state.get('chart_base64', '')
        NOT:
            chart_base64=result.get('chart_base64', '')
        """
        # Mock agent with chart_base64 in final_state
        mock_agent_class = MagicMock()
        mock_agent = MagicMock()
        mock_agent.graph.invoke.return_value = {
            "ticker": "DBS19",
            "report": "Test report",
            "chart_base64": "CHART_FROM_FINAL_STATE",  # This should be used
            "error": "",
        }
        mock_agent_class.return_value = mock_agent

        # Mock transformer that returns result WITHOUT chart_base64
        mock_transformer = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "ticker": "DBS19",
            "narrative_report": "Report text",
            "generation_metadata": {},
            # No chart_base64 here - it's not in the API response model
        }
        mock_transformer.transform_report = AsyncMock(return_value=mock_response)

        # Mock other services
        mock_job_service = MagicMock()
        mock_ticker_service = MagicMock()
        mock_ticker_service.get_ticker_info.return_value = {"symbol": "DBS19", "name": "DBS"}

        mock_precompute_class = MagicMock()
        mock_precompute = MagicMock()
        mock_precompute.store_report_from_api.return_value = True
        mock_precompute_class.return_value = mock_precompute

        with patch('src.report_worker_handler.TickerAnalysisAgent', mock_agent_class), \
             patch('src.report_worker_handler.get_transformer', return_value=mock_transformer), \
             patch('src.report_worker_handler.get_job_service', return_value=mock_job_service), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mock_ticker_service), \
             patch('src.report_worker_handler.PrecomputeService', mock_precompute_class):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test",
                "body": json.dumps({"job_id": "rpt_chart", "ticker": "DBS19"})
            }

            await process_record(record)

            # Verify chart_base64 came from final_state
            call_kwargs = mock_precompute.store_report_from_api.call_args.kwargs
            assert call_kwargs["chart_base64"] == "CHART_FROM_FINAL_STATE", \
                f"chart_base64 should come from final_state, got: {call_kwargs.get('chart_base64')}"


class TestWorkerSymbolValidation:
    """CRITICAL: Verify worker validates and normalizes incoming symbols.

    This is defensive validation - even if scheduler sends wrong format,
    worker should resolve and normalize to DR symbol.

    TDD Goal: Worker should use TickerResolver to validate symbols,
    so it can handle Yahoo symbols (D05.SI) even though it expects DR symbols (DBS19).
    """

    def setup_method(self):
        """Reset singletons before each test."""
        import src.api.job_service as job_mod
        import src.api.ticker_service as ticker_mod
        import src.api.transformer as transformer_mod

        job_mod._job_service = None
        ticker_mod._ticker_service = None
        transformer_mod._transformer = None

    def _create_mock_resolved_ticker(self, dr_symbol: str, yahoo_symbol: str = None):
        """Create a mock resolved ticker object."""
        mock_resolved = MagicMock()
        mock_resolved.dr_symbol = dr_symbol
        mock_resolved.yahoo_symbol = yahoo_symbol or dr_symbol
        mock_resolved.ticker_id = 1
        mock_resolved.company_name = f"Test Company for {dr_symbol}"
        return mock_resolved

    def _create_base_mocks(self):
        """Create all base mocks needed for process_record."""
        # Mock TickerAnalysisAgent
        mock_agent_class = MagicMock()
        mock_agent = MagicMock()
        mock_agent.graph.invoke.return_value = {
            "ticker": "DBS19",
            "report": "Test Thai report",
            "chart_base64": "CHART_DATA",
            "error": "",
        }
        mock_agent_class.return_value = mock_agent

        # Mock transformer (async)
        mock_transformer = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "ticker": "DBS19",
            "narrative_report": "Thai report",
            "generation_metadata": {},
        }
        mock_transformer.transform_report = AsyncMock(return_value=mock_response)

        # Mock job_service
        mock_job_service = MagicMock()

        # Mock ticker_service
        mock_ticker_service = MagicMock()
        mock_ticker_service.get_ticker_info.return_value = {
            "symbol": "DBS19",
            "name": "DBS Group",
            "yahoo_ticker": "D05.SI",
        }

        # Mock PrecomputeService
        mock_precompute_class = MagicMock()
        mock_precompute = MagicMock()
        mock_precompute.store_report_from_api.return_value = True
        mock_precompute_class.return_value = mock_precompute

        return {
            "agent_class": mock_agent_class,
            "agent": mock_agent,
            "transformer": mock_transformer,
            "job_service": mock_job_service,
            "ticker_service": mock_ticker_service,
            "precompute_class": mock_precompute_class,
            "precompute": mock_precompute,
        }

    @pytest.mark.asyncio
    async def test_worker_resolves_ticker_before_processing(self):
        """Worker should use resolver to validate incoming ticker."""
        mocks = self._create_base_mocks()

        # Mock resolver
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = self._create_mock_resolved_ticker("DBS19", "D05.SI")

        with patch('src.report_worker_handler.TickerAnalysisAgent', mocks["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mocks["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mocks["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mocks["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mocks["precompute_class"]), \
             patch('src.report_worker_handler.get_ticker_resolver', return_value=mock_resolver):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test",
                "body": json.dumps({"job_id": "rpt_resolve", "ticker": "DBS19"})
            }

            await process_record(record)

            # Verify resolver was called
            mock_resolver.resolve.assert_called_once_with("DBS19")

    @pytest.mark.asyncio
    async def test_worker_handles_yahoo_symbol_via_resolution(self):
        """CRITICAL: Worker should handle Yahoo symbols (D05.SI) via resolver.

        Even if scheduler accidentally sends Yahoo format, worker should
        resolve it to DR format (DBS19) and process successfully.
        """
        mocks = self._create_base_mocks()

        # Update agent mock to use resolved ticker
        mocks["agent"].graph.invoke.return_value = {
            "ticker": "DBS19",  # Resolved from D05.SI
            "report": "Test report",
            "chart_base64": "",
            "error": "",
        }

        # Mock resolver - Yahoo symbol resolves to DR symbol
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = self._create_mock_resolved_ticker("DBS19", "D05.SI")

        with patch('src.report_worker_handler.TickerAnalysisAgent', mocks["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mocks["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mocks["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mocks["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mocks["precompute_class"]), \
             patch('src.report_worker_handler.get_ticker_resolver', return_value=mock_resolver):

            from src.report_worker_handler import process_record

            # Send Yahoo symbol (simulating scheduler bug)
            record = {
                "messageId": "test-yahoo",
                "body": json.dumps({"job_id": "rpt_yahoo", "ticker": "D05.SI"})
            }

            # Should NOT raise - resolver handles conversion
            await process_record(record)

            # Verify resolver was called with Yahoo symbol
            mock_resolver.resolve.assert_called_once_with("D05.SI")

            # Verify job completed (not failed)
            mocks["job_service"].complete_job.assert_called_once()
            mocks["job_service"].fail_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_worker_fails_job_for_unknown_ticker(self):
        """Worker should fail job gracefully for unknown/invalid tickers."""
        mocks = self._create_base_mocks()

        # Mock resolver - returns None for unknown ticker
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = None

        with patch('src.report_worker_handler.TickerAnalysisAgent', mocks["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mocks["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mocks["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mocks["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mocks["precompute_class"]), \
             patch('src.report_worker_handler.get_ticker_resolver', return_value=mock_resolver):

            from src.report_worker_handler import process_record

            record = {
                "messageId": "test-unknown",
                "body": json.dumps({"job_id": "rpt_unknown", "ticker": "INVALID123"})
            }

            # Should raise exception for unknown ticker
            with pytest.raises(Exception) as exc_info:
                await process_record(record)

            assert "Unknown ticker" in str(exc_info.value) or "INVALID123" in str(exc_info.value)

            # Verify job was marked as failed (may be called twice - once in validation, once in exception handler)
            assert mocks["job_service"].fail_job.call_count >= 1
            # Check the first call has correct job_id and message
            fail_args = mocks["job_service"].fail_job.call_args_list[0]
            assert fail_args[0][0] == "rpt_unknown"  # job_id
            assert "INVALID123" in fail_args[0][1]  # error message contains ticker

    @pytest.mark.asyncio
    async def test_worker_uses_dr_symbol_in_state_for_workflow_nodes(self):
        """Worker should pass DR symbol in state['ticker'] for workflow node ticker_map lookups.

        Workflow nodes expect DR symbols in state['ticker'] because their ticker_map is indexed
        by DR symbols (DBS19, NVDA19). Workflow nodes internally convert DR → Yahoo for Aurora queries.
        """
        mocks = self._create_base_mocks()

        # Mock resolver
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = self._create_mock_resolved_ticker("DBS19", "D05.SI")

        with patch('src.report_worker_handler.TickerAnalysisAgent', mocks["agent_class"]), \
             patch('src.report_worker_handler.get_transformer', return_value=mocks["transformer"]), \
             patch('src.report_worker_handler.get_job_service', return_value=mocks["job_service"]), \
             patch('src.report_worker_handler.get_ticker_service', return_value=mocks["ticker_service"]), \
             patch('src.report_worker_handler.PrecomputeService', mocks["precompute_class"]), \
             patch('src.report_worker_handler.get_ticker_resolver', return_value=mock_resolver):

            from src.report_worker_handler import process_record

            # Send Yahoo symbol (will be resolved to DR symbol for state)
            record = {
                "messageId": "test-dr",
                "body": json.dumps({"job_id": "rpt_dr", "ticker": "D05.SI"})
            }

            await process_record(record)

            # Verify agent.graph.invoke received DR symbol (DBS19) in state['ticker']
            # Workflow nodes expect DR symbols for their ticker_map lookups
            invoke_args = mocks["agent"].graph.invoke.call_args[0][0]
            assert invoke_args["ticker"] == "DBS19", \
                f"Agent should receive DR symbol 'DBS19' in state, got '{invoke_args['ticker']}'"


class TestDirectInvocationMode:
    """Test direct Step Functions invocation mode

    Related: Migration plan to replace SQS with direct Lambda invocation.
    Tests handler routing and process_ticker_direct() function.
    """

    @pytest.fixture(autouse=True)
    def mock_env_vars(self, monkeypatch):
        """Set required environment variables for all tests."""
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        monkeypatch.setenv('AURORA_HOST', 'test-host')
        monkeypatch.setenv('PDF_BUCKET_NAME', 'test-bucket')
        monkeypatch.setenv('JOBS_TABLE_NAME', 'test-table')

    def test_direct_mode_detected(self):
        """Verify handler routes to direct invocation when ticker + source present."""
        with patch('src.report_worker_handler.process_ticker_direct', new_callable=AsyncMock) as mock:
            mock.return_value = {
                'ticker': 'DBS19',
                'status': 'success',
                'pdf_s3_key': 'test.pdf',
                'error': ''
            }

            from src.report_worker_handler import handler
            event = {
                'ticker': 'DBS19',
                'execution_id': 'exec_123',
                'source': 'step_functions_precompute'
            }
            result = handler(event, None)

            mock.assert_called_once()
            assert result['ticker'] == 'DBS19'
            assert result['status'] == 'success'

    def test_sqs_mode_backward_compatible(self):
        """Verify SQS mode still works (backward compatibility)."""
        with patch('src.report_worker_handler.process_record', new_callable=AsyncMock):
            from src.report_worker_handler import handler
            event = {
                'Records': [{
                    'messageId': 'msg_123',
                    'body': '{"job_id": "rpt_123", "ticker": "DBS19"}'
                }]
            }
            result = handler(event, None)

            assert result['statusCode'] == 200
            assert '1 records' in result['body']

    @pytest.mark.asyncio
    async def test_process_ticker_direct_success(self):
        """Test successful direct processing returns success status."""
        with patch('src.report_worker_handler.process_record', new_callable=AsyncMock), \
             patch('src.report_worker_handler.get_job_service') as mock_svc:

            mock_svc.return_value.get_job_status.return_value = {
                'status': 'completed',
                'result': {'pdf_s3_key': 'test.pdf'}
            }

            from src.report_worker_handler import process_ticker_direct
            result = await process_ticker_direct({
                'ticker': 'DBS19',
                'execution_id': 'exec_123',
                'source': 'step_functions_precompute'
            })

            assert result['status'] == 'success'
            assert result['ticker'] == 'DBS19'
            assert result['pdf_s3_key'] == 'test.pdf'
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_process_ticker_direct_failure(self):
        """Test failed processing returns failed status."""
        with patch('src.report_worker_handler.process_record', new_callable=AsyncMock), \
             patch('src.report_worker_handler.get_job_service') as mock_svc:

            mock_svc.return_value.get_job_status.return_value = {
                'status': 'failed',
                'error': 'Agent error: ticker not found'
            }

            from src.report_worker_handler import process_ticker_direct
            result = await process_ticker_direct({
                'ticker': 'INVALID',
                'execution_id': 'exec_123',
                'source': 'step_functions_precompute'
            })

            assert result['status'] == 'failed'
            assert result['ticker'] == 'INVALID'
            assert result['pdf_s3_key'] is None
            assert 'Agent error' in result['error']

    @pytest.mark.asyncio
    async def test_process_ticker_direct_missing_ticker(self):
        """Test validation fails fast on missing ticker (defensive programming)."""
        from src.report_worker_handler import process_ticker_direct

        with pytest.raises(ValueError) as exc:
            await process_ticker_direct({'execution_id': 'exec_123'})

        assert 'ticker' in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_process_ticker_direct_exception_handling(self):
        """Test exception during processing returns failed status (not raise)."""
        with patch('src.report_worker_handler.process_record', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Database connection error")

            from src.report_worker_handler import process_ticker_direct
            result = await process_ticker_direct({
                'ticker': 'DBS19',
                'execution_id': 'exec_123',
                'source': 'step_functions_precompute'
            })

            assert result['status'] == 'failed'
            assert result['ticker'] == 'DBS19'
            assert 'Database connection error' in result['error']
