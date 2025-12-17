# -*- coding: utf-8 -*-
"""
Integration tests for SEC EDGAR MCP disabled functionality.

Tests that SEC EDGAR node is properly disabled for Thai market focus.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.types import AgentState
from src.workflow.workflow_nodes import WorkflowNodes


class TestSECEdgarDisabled:
    """Test SEC EDGAR MCP disabled behavior."""

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
            ticker_map={'NVDA': 'NVDA'},
            db_query_count_ref=[0]
        )

    def test_fetch_sec_filing_always_skips(self):
        """Test that SEC EDGAR node always skips (disabled)."""
        state: AgentState = {
            "ticker": "NVDA",
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

        result = self.workflow_nodes.fetch_sec_filing(state)

        # Should always return empty sec_filing_data
        assert result["sec_filing_data"] == {}
        assert "error" not in result or result["error"] == ""
        
        # Should not call MCP client (node skips immediately, no MCP calls)
        # The node is disabled, so it never imports or calls get_mcp_client

    @patch.dict(os.environ, {'ENABLE_SEC_EDGAR': 'false'})
    def test_mcp_client_disables_sec_edgar_when_flag_false(self):
        """Test MCP client disables SEC EDGAR when ENABLE_SEC_EDGAR=false."""
        from src.integrations.mcp_client import MCPClient
        
        client = MCPClient()
        
        # SEC EDGAR should be None when flag is false
        assert client.servers.get('sec_edgar') is None

    @patch.dict(os.environ, {'ENABLE_SEC_EDGAR': 'true', 'SEC_EDGAR_MCP_URL': 'http://localhost:8002'})
    def test_mcp_client_enables_sec_edgar_when_flag_true(self):
        """Test MCP client enables SEC EDGAR when ENABLE_SEC_EDGAR=true."""
        from src.integrations.mcp_client import MCPClient
        
        client = MCPClient()
        
        # SEC EDGAR should be configured when flag is true
        assert client.servers.get('sec_edgar') == 'http://localhost:8002'
