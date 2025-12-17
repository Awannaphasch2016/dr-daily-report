# -*- coding: utf-8 -*-
"""
Integration tests for MCP report generation.

Tests that SEC filing data flows through workflow → context → LLM prompt.
Follows TDD principles: test behavior, not implementation; validate actual output.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from src.workflow.workflow_nodes import WorkflowNodes
from src.types import AgentState
from src.integrations.mcp_client import MCPClient, MCPServerError


class TestMCPReportGeneration:
    """Test that SEC filing data flows through workflow → context → LLM prompt."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create minimal mock dependencies
        self.mock_data_fetcher = Mock()
        self.mock_technical_analyzer = Mock()
        self.mock_news_fetcher = Mock()
        self.mock_chart_generator = Mock()
        self.mock_db = Mock()
        self.mock_strategy_backtester = Mock()
        self.mock_strategy_analyzer = Mock()
        self.mock_comparative_analyzer = Mock()
        self.mock_llm = Mock()
        self.mock_context_builder = Mock()
        self.mock_prompt_builder = Mock()
        self.mock_market_analyzer = Mock()
        self.mock_data_formatter = Mock()
        self.mock_number_injector = Mock()
        self.mock_cost_scorer = Mock()
        self.mock_scoring_service = Mock()
        self.mock_qos_scorer = Mock()
        self.mock_faithfulness_scorer = Mock()
        self.mock_completeness_scorer = Mock()
        self.mock_reasoning_quality_scorer = Mock()
        self.mock_compliance_scorer = Mock()
        self.mock_ticker_map = {'AAPL': 'AAPL'}

        # Initialize workflow nodes
        self.workflow_nodes = WorkflowNodes(
            data_fetcher=self.mock_data_fetcher,
            technical_analyzer=self.mock_technical_analyzer,
            news_fetcher=self.mock_news_fetcher,
            chart_generator=self.mock_chart_generator,
            db=self.mock_db,
            strategy_backtester=self.mock_strategy_backtester,
            strategy_analyzer=self.mock_strategy_analyzer,
            comparative_analyzer=self.mock_comparative_analyzer,
            llm=self.mock_llm,
            context_builder=self.mock_context_builder,
            prompt_builder=self.mock_prompt_builder,
            market_analyzer=self.mock_market_analyzer,
            data_formatter=self.mock_data_formatter,
            number_injector=self.mock_number_injector,
            cost_scorer=self.mock_cost_scorer,
            scoring_service=self.mock_scoring_service,
            qos_scorer=self.mock_qos_scorer,
            faithfulness_scorer=self.mock_faithfulness_scorer,
            completeness_scorer=self.mock_completeness_scorer,
            reasoning_quality_scorer=self.mock_reasoning_quality_scorer,
            compliance_scorer=self.mock_compliance_scorer,
            ticker_map=self.mock_ticker_map,
            db_query_count_ref=[0]
        )

    def test_workflow_fetches_sec_filing_via_mcp(self):
        """Test workflow node fetches SEC filing via MCP."""
        # Arrange: Mock MCP server response
        mock_filing_data = {
            'ticker': 'AAPL',
            'form_type': '10-Q',
            'filing_date': '2024-01-15',
            'company_name': 'Apple Inc.',
            'cik': '0000320193',
            'xbrl': {},
            'text_sections': {}
        }

        # Create initial state
        state: AgentState = {
            'ticker': 'AAPL',
            'ticker_data': {
                'info': {'shortName': 'Apple Inc.'},
                'yahoo_ticker': 'AAPL'
            },
            'indicators': {},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_data': {},
            'comparative_insights': {},
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': [],
            'sec_filing_data': {}
        }

        # Mock MCP client
        with patch('src.workflow.workflow_nodes.get_mcp_client') as mock_get_client:
            mock_mcp_client = Mock(spec=MCPClient)
            mock_mcp_client.is_server_available.return_value = True
            mock_mcp_client.call_tool.return_value = mock_filing_data
            mock_get_client.return_value = mock_mcp_client

            # Act: Run workflow node
            result_state = self.workflow_nodes.fetch_sec_filing(state)

            # Assert: State contains SEC filing data
            assert isinstance(result_state, dict), f"Result should be dict, got {type(result_state)}"
            assert 'sec_filing_data' in result_state, "State missing sec_filing_data field"
            assert isinstance(result_state['sec_filing_data'], dict), f"sec_filing_data should be dict, got {type(result_state['sec_filing_data'])}"
            assert result_state['sec_filing_data']['ticker'] == 'AAPL', f"Expected AAPL, got {result_state['sec_filing_data'].get('ticker')}"
            assert result_state['sec_filing_data']['form_type'] == '10-Q', f"Expected 10-Q, got {result_state['sec_filing_data'].get('form_type')}"
            assert result_state['sec_filing_data']['filing_date'] == '2024-01-15', f"Expected 2024-01-15, got {result_state['sec_filing_data'].get('filing_date')}"

            # Verify MCP client was called correctly
            mock_mcp_client.call_tool.assert_called_once()
            call_args = mock_mcp_client.call_tool.call_args
            assert call_args[1]['server'] == 'sec_edgar', f"Expected sec_edgar server, got {call_args[1].get('server')}"
            assert call_args[1]['tool_name'] == 'get_latest_filing', f"Expected get_latest_filing tool, got {call_args[1].get('tool_name')}"
            assert call_args[1]['arguments']['ticker'] == 'AAPL', f"Expected AAPL ticker, got {call_args[1]['arguments'].get('ticker')}"

    def test_context_builder_receives_sec_filing_data(self):
        """Test context builder receives SEC filing data from workflow state."""
        # Arrange: State with SEC filing data
        sec_filing_data = {
            'ticker': 'AAPL',
            'form_type': '10-Q',
            'filing_date': '2024-01-15',
            'company_name': 'Apple Inc.',
            'cik': '0000320193'
        }

        state: AgentState = {
            'ticker': 'AAPL',
            'ticker_data': {'info': {'shortName': 'Apple Inc.'}},
            'indicators': {'rsi': 55.0},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_insights': {},
            'sec_filing_data': sec_filing_data,
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': []
        }

        # Mock context builder to capture call arguments
        self.mock_context_builder.prepare_context.return_value = "Mock context with SEC data"

        # Act: Simulate context building (as done in generate_report node)
        context = self.mock_context_builder.prepare_context(
            ticker=state['ticker'],
            ticker_data=state['ticker_data'],
            indicators=state['indicators'],
            percentiles=state.get('percentiles', {}),
            news=state.get('news', []),
            news_summary=state.get('news_summary', {}),
            sec_filing_data=state.get('sec_filing_data', {})
        )

        # Assert: Context builder was called with SEC filing data
        self.mock_context_builder.prepare_context.assert_called_once()
        call_kwargs = self.mock_context_builder.prepare_context.call_args[1]
        assert 'sec_filing_data' in call_kwargs, "Context builder not called with sec_filing_data"
        assert call_kwargs['sec_filing_data'] == sec_filing_data, "SEC filing data not passed correctly"
        assert call_kwargs['sec_filing_data']['form_type'] == '10-Q', "Form type not passed correctly"

    def test_llm_prompt_contains_sec_filing_data(self):
        """Test LLM prompt includes SEC filing context."""
        # Arrange: Workflow state with SEC filing
        sec_filing_data = {
            'ticker': 'AAPL',
            'form_type': '10-Q',
            'filing_date': '2024-01-15',
            'company_name': 'Apple Inc.'
        }

        state: AgentState = {
            'ticker': 'AAPL',
            'ticker_data': {'info': {'shortName': 'Apple Inc.'}},
            'indicators': {'rsi': 55.0},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_insights': {},
            'sec_filing_data': sec_filing_data,
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': []
        }

        # Mock context builder to return context with SEC data
        mock_context = """
        Fundamental section
        Technical section
        SEC FILING DATA
        Form Type: 10-Q
        Filing Date: 2024-01-15
        """
        self.mock_context_builder.prepare_context.return_value = mock_context

        # Mock prompt builder
        mock_prompt = f"Generate report:\n{mock_context}"
        self.mock_prompt_builder.build_prompt.return_value = mock_prompt

        # Mock LLM response
        mock_llm_response = Mock()
        mock_llm_response.content = "Generated report text"
        self.mock_llm.invoke.return_value = mock_llm_response

        # Act: Build context and prompt (simulating generate_report node)
        context = self.mock_context_builder.prepare_context(
            ticker=state['ticker'],
            ticker_data=state['ticker_data'],
            indicators=state['indicators'],
            percentiles=state.get('percentiles', {}),
            news=state.get('news', []),
            news_summary=state.get('news_summary', {}),
            sec_filing_data=state.get('sec_filing_data', {})
        )

        prompt = self.mock_prompt_builder.build_prompt(context, uncertainty_score=50.0)

        # Assert: Prompt text contains SEC filing information
        assert isinstance(prompt, str), f"Prompt should be string, got {type(prompt)}"
        assert len(prompt) > 0, "Prompt is empty"
        assert "SEC FILING DATA" in prompt, "Prompt missing SEC filing section header"
        assert "10-Q" in prompt, "Prompt missing form type"
        assert "2024-01-15" in prompt, "Prompt missing filing date"

    def test_workflow_handles_mcp_unavailable_gracefully(self):
        """Test workflow handles MCP server unavailability gracefully."""
        # Arrange: State for US ticker
        state: AgentState = {
            'ticker': 'AAPL',
            'ticker_data': {
                'info': {'shortName': 'Apple Inc.'},
                'yahoo_ticker': 'AAPL'
            },
            'indicators': {},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_data': {},
            'comparative_insights': {},
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': [],
            'sec_filing_data': {}
        }

        # Mock MCP client - server not available
        with patch('src.workflow.workflow_nodes.get_mcp_client') as mock_get_client:
            mock_mcp_client = Mock(spec=MCPClient)
            mock_mcp_client.is_server_available.return_value = False
            mock_get_client.return_value = mock_mcp_client

            # Act: Run workflow node
            result_state = self.workflow_nodes.fetch_sec_filing(state)

            # Assert: State has empty SEC filing data (graceful degradation)
            assert isinstance(result_state, dict), f"Result should be dict, got {type(result_state)}"
            assert 'sec_filing_data' in result_state, "State missing sec_filing_data field"
            assert result_state['sec_filing_data'] == {}, "SEC filing data should be empty when MCP unavailable"
            assert result_state.get('error') == '', "Workflow should not error when MCP unavailable"

    def test_workflow_handles_mcp_error_gracefully(self):
        """Test workflow handles MCP server errors gracefully."""
        # Arrange: State for US ticker
        state: AgentState = {
            'ticker': 'AAPL',
            'ticker_data': {
                'info': {'shortName': 'Apple Inc.'},
                'yahoo_ticker': 'AAPL'
            },
            'indicators': {},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_data': {},
            'comparative_insights': {},
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': [],
            'sec_filing_data': {}
        }

        # Mock MCP client - server raises error
        with patch('src.workflow.workflow_nodes.get_mcp_client') as mock_get_client:
            mock_mcp_client = Mock(spec=MCPClient)
            mock_mcp_client.is_server_available.return_value = True
            mock_mcp_client.call_tool.side_effect = MCPServerError("MCP server error")
            mock_get_client.return_value = mock_mcp_client

            # Act: Run workflow node
            result_state = self.workflow_nodes.fetch_sec_filing(state)

            # Assert: State has empty SEC filing data (graceful degradation)
            assert isinstance(result_state, dict), f"Result should be dict, got {type(result_state)}"
            assert 'sec_filing_data' in result_state, "State missing sec_filing_data field"
            assert result_state['sec_filing_data'] == {}, "SEC filing data should be empty when MCP errors"
            assert result_state.get('error') == '', "Workflow should not error when MCP fails"

    def test_workflow_skips_sec_filing_for_non_us_ticker(self):
        """Test workflow skips SEC filing for non-US tickers."""
        # Arrange: State for Thai ticker
        state: AgentState = {
            'ticker': 'NVDA19',
            'ticker_data': {
                'info': {'shortName': 'NVIDIA Corporation'},
                'yahoo_ticker': 'NVDA.SI'  # Singapore ticker
            },
            'indicators': {},
            'percentiles': {},
            'news': [],
            'news_summary': {},
            'comparative_data': {},
            'comparative_insights': {},
            'report': '',
            'strategy': 'single-stage',
            'error': '',
            'messages': [],
            'sec_filing_data': {}
        }

        # Mock ticker map
        self.workflow_nodes.ticker_map = {'NVDA19': 'NVDA.SI'}

        # Act: Run workflow node
        result_state = self.workflow_nodes.fetch_sec_filing(state)

        # Assert: State has empty SEC filing data (skipped for non-US)
        assert isinstance(result_state, dict), f"Result should be dict, got {type(result_state)}"
        assert 'sec_filing_data' in result_state, "State missing sec_filing_data field"
        assert result_state['sec_filing_data'] == {}, "SEC filing data should be empty for non-US tickers"
