"""
Tests for refactored workflow nodes that return partial state.

These tests verify that nodes return only modified fields (not full AgentState)
to enable parallel execution without InvalidUpdateError.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.workflow.workflow_nodes import WorkflowNodes
from src.types import AgentState


class TestRefactoredNodes:
    """Test suite for workflow nodes refactored to return partial state"""

    def setup_method(self):
        """Set up test fixtures before each test"""
        # Mock all dependencies
        self.mock_data_fetcher = MagicMock()
        self.mock_technical_analyzer = MagicMock()
        self.mock_news_fetcher = MagicMock()
        self.mock_chart_generator = MagicMock()
        self.mock_db = MagicMock()
        self.mock_strategy_backtester = MagicMock()
        self.mock_strategy_analyzer = MagicMock()
        self.mock_comparative_analyzer = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_context_builder = MagicMock()
        self.mock_prompt_builder = MagicMock()
        self.mock_market_analyzer = MagicMock()
        self.mock_number_injector = MagicMock()
        self.mock_cost_scorer = MagicMock()
        self.mock_scoring_service = MagicMock()
        self.mock_qos_scorer = MagicMock()
        self.mock_faithfulness_scorer = MagicMock()
        self.mock_completeness_scorer = MagicMock()
        self.mock_reasoning_quality_scorer = MagicMock()
        self.mock_compliance_scorer = MagicMock()

        self.ticker_map = {
            'DBS19': 'D05.SI',
            'NVDA19': 'NVDA',
            'AAPL19': 'AAPL'
        }

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
            number_injector=self.mock_number_injector,
            cost_scorer=self.mock_cost_scorer,
            scoring_service=self.mock_scoring_service,
            qos_scorer=self.mock_qos_scorer,
            faithfulness_scorer=self.mock_faithfulness_scorer,
            completeness_scorer=self.mock_completeness_scorer,
            reasoning_quality_scorer=self.mock_reasoning_quality_scorer,
            compliance_scorer=self.mock_compliance_scorer,
            ticker_map=self.ticker_map,
            db_query_count_ref=[0]
        )

    def test_fetch_news_returns_partial_state(self):
        """Verify fetch_news returns only modified fields (not full state)"""
        # Mock state
        state = {
            "ticker": "DBS19",
            "ticker_data": {"symbol": "D05.SI"},
            "news": [],  # Old news
            "indicators": {"rsi": 50}  # Existing data that should NOT be returned
        }

        # Mock news fetcher
        mock_news = [
            {"title": "DBS Reports Strong Earnings", "sentiment": "positive", "score": 85}
        ]
        mock_summary = {"positive_count": 1, "negative_count": 0, "neutral_count": 0}
        self.mock_news_fetcher.filter_high_impact_news.return_value = mock_news
        self.mock_news_fetcher.get_news_summary.return_value = mock_summary

        # Execute node
        result = self.workflow_nodes.fetch_news(state)

        # ASSERT: Returns dict, not AgentState
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # ASSERT: Contains only modified fields
        assert set(result.keys()) == {"news", "news_summary"}, \
            f"Expected only news fields, got {result.keys()}"

        # ASSERT: Does NOT contain unmodified fields
        assert "ticker" not in result, "Should not return ticker field"
        assert "ticker_data" not in result, "Should not return ticker_data field"
        assert "indicators" not in result, "Should not return indicators field"

        # ASSERT: News data is valid
        assert result["news"] == mock_news
        assert result["news_summary"] == mock_summary

    def test_fetch_news_returns_empty_on_error(self):
        """Verify fetch_news returns empty dict when error in state"""
        state = {
            "ticker": "DBS19",
            "error": "Previous node failed"
        }

        result = self.workflow_nodes.fetch_news(state)

        # ASSERT: Returns empty dict on error
        assert result == {}, f"Expected empty dict on error, got {result}"

    def test_fetch_alpaca_data_returns_partial_state(self):
        """Verify fetch_alpaca_data returns only modified fields"""
        state = {
            "ticker": "NVDA19",
            "ticker_data": {"symbol": "NVDA"},
            "news": [{"title": "test"}],  # Existing data
        }

        # Mock MCP client
        with patch('src.integrations.mcp_client.get_mcp_client') as mock_get_mcp:
            mock_mcp = MagicMock()
            mock_mcp.is_server_available.return_value = False  # Server not available
            mock_get_mcp.return_value = mock_mcp

            result = self.workflow_nodes.fetch_alpaca_data(state)

            # ASSERT: Returns dict with only alpaca_data field
            assert isinstance(result, dict)
            assert set(result.keys()) == {"alpaca_data"}
            assert result["alpaca_data"] == {}

            # ASSERT: Does NOT contain unmodified fields
            assert "news" not in result

    def test_fetch_financial_markets_data_returns_partial_state(self):
        """Verify fetch_financial_markets_data returns only modified fields"""
        state = {
            "ticker": "DBS19",
            "indicators": {"rsi": 50}  # Existing data
        }

        # Mock MCP client not available
        with patch('src.integrations.mcp_client.get_mcp_client') as mock_get_mcp:
            mock_mcp = MagicMock()
            mock_mcp.is_server_available.return_value = False
            mock_get_mcp.return_value = mock_mcp

            result = self.workflow_nodes.fetch_financial_markets_data(state)

            # ASSERT: Returns only financial_markets_data field
            assert isinstance(result, dict)
            assert set(result.keys()) == {"financial_markets_data"}
            assert "indicators" not in result

    def test_fetch_sec_filing_returns_partial_state(self):
        """Verify fetch_sec_filing returns only modified fields (always disabled)"""
        state = {
            "ticker": "AAPL19",
            "news": [{"title": "test"}]
        }

        result = self.workflow_nodes.fetch_sec_filing(state)

        # ASSERT: Returns only sec_filing_data field
        assert isinstance(result, dict)
        assert set(result.keys()) == {"sec_filing_data"}
        assert result["sec_filing_data"] == {}
        assert "news" not in result

    def test_fetch_portfolio_insights_returns_partial_state(self):
        """Verify fetch_portfolio_insights returns only modified fields"""
        state = {
            "ticker": "DBS19",
            "comparative_data": {}  # Existing data
        }

        # Mock MCP client not available
        with patch('src.integrations.mcp_client.get_mcp_client') as mock_get_mcp:
            mock_mcp = MagicMock()
            mock_mcp.is_server_available.return_value = False
            mock_get_mcp.return_value = mock_mcp

            result = self.workflow_nodes.fetch_portfolio_insights(state)

            # ASSERT: Returns only portfolio_insights field
            assert isinstance(result, dict)
            assert set(result.keys()) == {"portfolio_insights"}
            assert "comparative_data" not in result

    def test_fetch_comparative_data_returns_partial_state(self):
        """Verify fetch_comparative_data returns only modified fields"""
        state = {
            "ticker": "DBS19",
            "ticker_data": {"symbol": "D05.SI", "sector": "Financials"},
            "news": [{"title": "test"}]  # Existing data
        }

        # Mock data fetcher
        self.mock_data_fetcher.fetch_historical_data.return_value = None

        result = self.workflow_nodes.fetch_comparative_data(state)

        # ASSERT: Returns only comparative_data field
        assert isinstance(result, dict)
        assert set(result.keys()) == {"comparative_data"}
        assert "news" not in result

    def test_parallel_execution_no_key_conflicts(self):
        """
        Verify multiple nodes can execute in parallel without key conflicts.

        This simulates parallel execution by calling multiple nodes and ensuring
        their returned dicts have no overlapping keys.
        """
        state = {
            "ticker": "DBS19",
            "ticker_data": {"symbol": "D05.SI"}
        }

        # Mock dependencies
        self.mock_news_fetcher.filter_high_impact_news.return_value = []
        self.mock_news_fetcher.get_news_summary.return_value = {}

        with patch('src.integrations.mcp_client.get_mcp_client') as mock_get_mcp:
            mock_mcp = MagicMock()
            mock_mcp.is_server_available.return_value = False
            mock_get_mcp.return_value = mock_mcp

            # Execute nodes in parallel (simulated)
            result_news = self.workflow_nodes.fetch_news(state)
            result_alpaca = self.workflow_nodes.fetch_alpaca_data(state)
            result_markets = self.workflow_nodes.fetch_financial_markets_data(state)
            result_sec = self.workflow_nodes.fetch_sec_filing(state)
            result_portfolio = self.workflow_nodes.fetch_portfolio_insights(state)

            # ASSERT: No overlapping keys
            all_keys = (
                set(result_news.keys()) |
                set(result_alpaca.keys()) |
                set(result_markets.keys()) |
                set(result_sec.keys()) |
                set(result_portfolio.keys())
            )

            expected_keys = {
                "news", "news_summary", "alpaca_data", "financial_markets_data",
                "sec_filing_data", "portfolio_insights"
            }

            assert all_keys == expected_keys, \
                f"Expected {expected_keys}, got {all_keys}"

    def test_node_returns_empty_dict_not_none_on_skip(self):
        """Verify nodes return {} not None when skipping due to missing ticker"""
        state = {
            "ticker": "INVALID_TICKER",  # Not in ticker_map
        }

        result = self.workflow_nodes.fetch_news(state)

        # ASSERT: Returns dict, not None
        assert result is not None, "Should return dict, not None"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
