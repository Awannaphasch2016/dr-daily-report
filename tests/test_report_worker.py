#!/usr/bin/env python3
"""
Tests for report worker Lambda handler

TDD: Tests for async report generation worker that processes SQS messages.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.api.job_service import Job, JobStatus


class TestReportWorkerHandler:
    """Tests for report_worker_handler.handler()"""

    @pytest.fixture
    def mock_job_service(self):
        """Mock job service"""
        with patch('src.report_worker_handler.get_job_service') as mock:
            service = Mock()
            service.start_job = Mock()
            service.complete_job = Mock()
            service.fail_job = Mock()
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_agent(self):
        """Mock TickerAnalysisAgent"""
        with patch('src.report_worker_handler.TickerAnalysisAgent') as mock:
            agent = Mock()
            agent.graph.invoke = Mock(return_value={
                'ticker': 'NVDA19',
                'report': 'Test report content',
                'indicators': {'rsi': 55},
                'percentiles': {},
                'error': ''
            })
            mock.return_value = agent
            yield mock

    @pytest.fixture
    def mock_transformer(self):
        """Mock response transformer"""
        with patch('src.report_worker_handler.get_transformer') as mock:
            transformer = Mock()
            transformer.transform_report = Mock(return_value=Mock(
                model_dump=Mock(return_value={
                    'ticker': 'NVDA19',
                    'company_name': 'NVIDIA',
                    'price': 150.0,
                    'stance': 'bullish'
                })
            ))
            mock.return_value = transformer
            yield transformer

    @pytest.fixture
    def mock_ticker_service(self):
        """Mock ticker service"""
        with patch('src.report_worker_handler.get_ticker_service') as mock:
            service = Mock()
            service.get_ticker_info = Mock(return_value={
                'symbol': 'NVDA19',
                'company_name': 'NVIDIA Corporation',
                'yahoo_symbol': 'NVDA'
            })
            mock.return_value = service
            yield service

    @pytest.fixture
    def sqs_event(self):
        """Create mock SQS event"""
        return {
            'Records': [
                {
                    'messageId': 'msg-123',
                    'body': json.dumps({
                        'job_id': 'rpt_abc123',
                        'ticker': 'NVDA19'
                    })
                }
            ]
        }

    def test_handler_updates_job_to_in_progress(
        self, sqs_event, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that handler marks job as in_progress at start"""
        from src.report_worker_handler import handler

        handler(sqs_event, None)

        mock_job_service.start_job.assert_called_once_with('rpt_abc123')

    def test_handler_invokes_agent_with_correct_ticker(
        self, sqs_event, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that handler invokes agent with correct ticker"""
        from src.report_worker_handler import handler

        handler(sqs_event, None)

        # Agent should be instantiated and invoke called
        mock_agent.assert_called_once()
        agent_instance = mock_agent.return_value
        agent_instance.graph.invoke.assert_called_once()

        # Check ticker in state
        call_args = agent_instance.graph.invoke.call_args
        state = call_args[0][0]
        assert state['ticker'] == 'NVDA19'

    def test_handler_success_marks_completed(
        self, sqs_event, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that successful processing marks job as completed"""
        from src.report_worker_handler import handler

        handler(sqs_event, None)

        mock_job_service.complete_job.assert_called_once()
        call_args = mock_job_service.complete_job.call_args
        assert call_args[0][0] == 'rpt_abc123'  # job_id
        assert 'ticker' in call_args[0][1]  # result dict

    def test_handler_failure_marks_failed_before_raising(
        self, sqs_event, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that failure marks job as failed before re-raising"""
        from src.report_worker_handler import handler

        # Make agent raise exception
        mock_agent.return_value.graph.invoke.side_effect = Exception("LLM API timeout")

        with pytest.raises(Exception) as exc_info:
            handler(sqs_event, None)

        assert "LLM API timeout" in str(exc_info.value)

        # Job should be marked as failed
        mock_job_service.fail_job.assert_called_once()
        call_args = mock_job_service.fail_job.call_args
        assert call_args[0][0] == 'rpt_abc123'  # job_id
        assert 'LLM API timeout' in call_args[0][1]  # error message

    def test_handler_agent_error_marks_failed(
        self, sqs_event, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that agent error in state marks job as failed"""
        from src.report_worker_handler import handler

        # Make agent return error in state
        mock_agent.return_value.graph.invoke.return_value = {
            'ticker': 'NVDA19',
            'error': 'Data fetch failed',
            'report': ''
        }

        with pytest.raises(Exception):
            handler(sqs_event, None)

        mock_job_service.fail_job.assert_called_once()
        call_args = mock_job_service.fail_job.call_args
        assert 'Data fetch failed' in call_args[0][1]

    def test_handler_processes_multiple_records(
        self, mock_job_service, mock_agent, mock_transformer, mock_ticker_service
    ):
        """Test that handler processes all SQS records"""
        from src.report_worker_handler import handler

        multi_event = {
            'Records': [
                {'messageId': 'msg-1', 'body': json.dumps({'job_id': 'rpt_001', 'ticker': 'NVDA19'})},
                {'messageId': 'msg-2', 'body': json.dumps({'job_id': 'rpt_002', 'ticker': 'DBS19'})}
            ]
        }

        handler(multi_event, None)

        # Should process both records
        assert mock_job_service.start_job.call_count == 2
        assert mock_job_service.complete_job.call_count == 2


class TestSQSMessageParsing:
    """Tests for SQS message parsing"""

    @pytest.fixture
    def mock_all_services(self):
        """Mock all services to prevent actual calls"""
        with patch('src.report_worker_handler.get_job_service') as mock_job, \
             patch('src.report_worker_handler.TickerAnalysisAgent') as mock_agent, \
             patch('src.report_worker_handler.get_transformer') as mock_transformer, \
             patch('src.report_worker_handler.get_ticker_service') as mock_ticker:

            job_service = Mock()
            job_service.start_job = Mock()
            job_service.complete_job = Mock()
            job_service.fail_job = Mock()
            mock_job.return_value = job_service

            agent = Mock()
            agent.graph.invoke = Mock(return_value={'ticker': 'NVDA19', 'report': 'Test', 'error': ''})
            mock_agent.return_value = agent

            transformer = Mock()
            transformer.transform_report = Mock(return_value=Mock(
                model_dump=Mock(return_value={'ticker': 'NVDA19'})
            ))
            mock_transformer.return_value = transformer

            ticker_service = Mock()
            ticker_service.get_ticker_info = Mock(return_value={'symbol': 'NVDA19', 'company_name': 'NVIDIA'})
            mock_ticker.return_value = ticker_service

            yield {
                'job': job_service,
                'agent': mock_agent,
                'transformer': transformer,
                'ticker': ticker_service
            }

    def test_parses_job_id_from_message(self, mock_all_services):
        """Test that job_id is correctly parsed from SQS message"""
        from src.report_worker_handler import handler

        event = {
            'Records': [
                {'messageId': 'msg-1', 'body': json.dumps({'job_id': 'rpt_custom_id', 'ticker': 'NVDA19'})}
            ]
        }

        handler(event, None)

        mock_all_services['job'].start_job.assert_called_with('rpt_custom_id')

    def test_parses_ticker_from_message(self, mock_all_services):
        """Test that ticker is correctly parsed from SQS message"""
        from src.report_worker_handler import handler

        event = {
            'Records': [
                {'messageId': 'msg-1', 'body': json.dumps({'job_id': 'rpt_123', 'ticker': 'DBS19'})}
            ]
        }

        handler(event, None)

        # Check ticker was used in agent call
        agent_instance = mock_all_services['agent'].return_value
        call_args = agent_instance.graph.invoke.call_args
        state = call_args[0][0]
        assert state['ticker'] == 'DBS19'

    def test_handles_malformed_message(self, mock_all_services):
        """Test that malformed messages are handled gracefully"""
        from src.report_worker_handler import handler

        event = {
            'Records': [
                {'messageId': 'msg-1', 'body': 'not valid json'}
            ]
        }

        # Should not crash, should mark job as failed or skip
        with pytest.raises(Exception):
            handler(event, None)
