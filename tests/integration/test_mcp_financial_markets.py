# -*- coding: utf-8 -*-
"""
Integration tests for Financial Markets MCP integration.

Tests workflow node integration with Financial Markets MCP server.
Validates graceful degradation when MCP server is unavailable.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.types import AgentState
from src.workflow.workflow_nodes import WorkflowNodes


class TestFinancialMarketsMCPIntegration:
    """Test Financial Markets MCP workflow integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create minimal WorkflowNodes instance with mocked dependencies
        self.workflow_nodes = WorkflowNodes(
            data_fetcher=MagicMock(),
            technical_analyzer=MagicMock(),
            news_fetcher=MagicMock(),
            chart_generator=MagicMock(),
            db=MagicMock(),
            strategy_backtester=MagicMock(),
            strategy_analyzer=MagicMock(),
            comparative_analyzer=MagicMock(),
            llm=MagicMock(),
            context_builder=MagicMock(),
            prompt_builder=MagicMock(),
            market_analyzer=MagicMock(),
            data_formatter=MagicMock(),
            number_injector=MagicMock(),
            cost_scorer=MagicMock(),
            scoring_service=MagicMock(),
            qos_scorer=MagicMock(),
            faithfulness_scorer=MagicMock(),
            completeness_scorer=MagicMock(),
            reasoning_quality_scorer=MagicMock(),
            compliance_scorer=MagicMock(),
            ticker_map={'DBS19': 'DBS.SI'},
            db_query_count_ref=[0]
        )

    def test_fetch_financial_markets_data_skips_when_no_ticker(self):
        """Test node skips gracefully when no yahoo_ticker found."""
        state: AgentState = {
            "ticker": "INVALID",
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "user_facing_scores": {},
            "sec_filing_data": {},
            "financial_markets_data": {},
            "portfolio_insights": {},
            "alpaca_data": {},
            "error": "",
            "strategy": "single-stage",
            "messages": []
        }

        result = self.workflow_nodes.fetch_financial_markets_data(state)

        assert result["financial_markets_data"] == {}
        assert "error" not in result or result["error"] == ""

    @patch('src.integrations.mcp_client.get_mcp_client')
    def test_fetch_financial_markets_data_skips_when_server_unavailable(self, mock_get_client):
        """Test node skips gracefully when MCP server not configured."""
        mock_client = MagicMock()
        mock_client.is_server_available.return_value = False
        mock_get_client.return_value = mock_client

        state: AgentState = {
            "ticker": "DBS19",
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "user_facing_scores": {},
            "sec_filing_data": {},
            "financial_markets_data": {},
            "portfolio_insights": {},
            "alpaca_data": {},
            "error": "",
            "strategy": "single-stage",
            "messages": []
        }

        result = self.workflow_nodes.fetch_financial_markets_data(state)

        assert result["financial_markets_data"] == {}
        assert "error" not in result or result["error"] == ""
        mock_client.is_server_available.assert_called_once_with('financial_markets')

    @patch('src.integrations.mcp_client.get_mcp_client')
    def test_fetch_financial_markets_data_handles_mcp_errors(self, mock_get_client):
        """Test node handles MCP errors gracefully."""
        from src.integrations.mcp_client import MCPServerError

        mock_client = MagicMock()
        mock_client.is_server_available.return_value = True
        mock_client.call_tool.side_effect = MCPServerError("MCP server error")
        mock_get_client.return_value = mock_client

        state: AgentState = {
            "ticker": "DBS19",
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "comparative_data": {},
            "comparative_insights": {},
            "chart_base64": "",
            "report": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "compliance_score": {},
            "qos_score": {},
            "cost_score": {},
            "timing_metrics": {},
            "api_costs": {},
            "database_metrics": {},
            "user_facing_scores": {},
            "sec_filing_data": {},
            "financial_markets_data": {},
            "portfolio_insights": {},
            "alpaca_data": {},
            "error": "",
            "strategy": "single-stage",
            "messages": []
        }

        result = self.workflow_nodes.fetch_financial_markets_data(state)

        assert result["financial_markets_data"] == {}
        assert "error" not in result or result["error"] == ""
