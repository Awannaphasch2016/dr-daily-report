# -*- coding: utf-8 -*-
"""
Integration tests for Portfolio Manager MCP integration.

Tests workflow node integration with Portfolio Manager MCP server.
Validates graceful degradation when MCP server is unavailable.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.types import AgentState
from src.workflow.workflow_nodes import WorkflowNodes


class TestPortfolioManagerMCPIntegration:
    """Test Portfolio Manager MCP workflow integration."""

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

    @patch('src.integrations.mcp_client.get_mcp_client')
    def test_fetch_portfolio_insights_skips_when_server_unavailable(self, mock_get_client):
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

        result = self.workflow_nodes.fetch_portfolio_insights(state)

        assert result["portfolio_insights"] == {}
        assert "error" not in result or result["error"] == ""
        mock_client.is_server_available.assert_called_once_with('portfolio_manager')

    def test_fetch_portfolio_insights_skips_when_no_portfolio_context(self):
        """Test node skips when no portfolio context is available."""
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

        with patch('src.integrations.mcp_client.get_mcp_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.is_server_available.return_value = True
            mock_get_client.return_value = mock_client

            result = self.workflow_nodes.fetch_portfolio_insights(state)

            assert result["portfolio_insights"] == {}
            assert "error" not in result or result["error"] == ""
