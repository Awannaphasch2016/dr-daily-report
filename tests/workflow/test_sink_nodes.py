"""
Tests for sink nodes that validate parallel merge checkpoints.

Sink nodes provide explicit validation and debugging checkpoints for parallel execution.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.workflow.workflow_nodes import WorkflowNodes
from src.types import AgentState


class TestSinkNodes:
    """Test suite for sink node validation logic"""

    def setup_method(self):
        """Set up test fixtures before each test"""
        # Mock all dependencies (sink nodes don't use most of these, but required for initialization)
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

        self.ticker_map = {'DBS19': 'D05.SI'}

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

    def test_merge_fundamental_data_validates_all_sources(self):
        """Verify SINK 1 validates all 6 fundamental data sources"""
        # Mock state with all 6 fundamental sources populated
        state = {
            "ticker": "DBS19",
            "news": [{"title": "Test News"}],
            "alpaca_data": {"quote": {"bid": 100}},
            "financial_markets_data": {"patterns": []},
            "sec_filing_data": {},
            "portfolio_insights": {},
            "comparative_data": {"NVDA19": []}
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_fundamental_data(state)

            # ASSERT: Returns empty dict (sink doesn't modify state)
            assert result == {}, f"Sink should return empty dict, got {result}"

            # ASSERT: Logged checkpoint message
            assert mock_logger.info.called, "Should log checkpoint info"
            log_messages = [str(call) for call in mock_logger.info.call_args_list]
            assert any("SINK 1" in msg for msg in log_messages), \
                "Should log SINK 1 checkpoint"

            # ASSERT: Validated all 6 sources
            assert any("News: 1 articles" in msg for msg in log_messages)
            assert any("Alpaca:" in msg for msg in log_messages)
            assert any("Markets:" in msg for msg in log_messages)
            assert any("SEC:" in msg for msg in log_messages)
            assert any("Portfolio:" in msg for msg in log_messages)
            assert any("Comparative: 1 tickers" in msg for msg in log_messages)

    def test_merge_fundamental_data_handles_empty_sources(self):
        """Verify SINK 1 handles empty data sources gracefully"""
        # Mock state with empty sources
        state = {
            "ticker": "DBS19",
            "news": [],
            "alpaca_data": {},
            "financial_markets_data": {},
            "sec_filing_data": {},
            "portfolio_insights": {},
            "comparative_data": {}
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_fundamental_data(state)

            # ASSERT: Returns empty dict
            assert result == {}

            # ASSERT: Logged that data is empty
            log_messages = [str(call) for call in mock_logger.info.call_args_list]
            assert any("News: 0 articles" in msg for msg in log_messages)
            assert any("empty" in msg.lower() for msg in log_messages)

    def test_merge_fundamental_data_detects_errors(self):
        """Verify SINK 1 detects and logs errors from parallel branches"""
        state = {
            "ticker": "DBS19",
            "error": "Network timeout in fetch_news",
            "news": [],
            "alpaca_data": {},
            "financial_markets_data": {},
            "sec_filing_data": {},
            "portfolio_insights": {},
            "comparative_data": {}
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_fundamental_data(state)

            # ASSERT: Returns empty dict
            assert result == {}

            # ASSERT: Logged error
            assert mock_logger.error.called, "Should log error"
            error_messages = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Network timeout" in msg for msg in error_messages)

    def test_merge_fund_tech_data_validates_both_pipelines(self):
        """Verify SINK 2 validates fundamental + technical data merged"""
        state = {
            "ticker": "DBS19",
            # Fundamental data (6 sources)
            "news": [{"title": "Test"}],
            "alpaca_data": {},
            "financial_markets_data": {},
            "sec_filing_data": {},
            "portfolio_insights": {},
            "comparative_data": {},
            # Technical data
            "indicators": {"rsi": 50, "macd": 0.5},
            "percentiles": {"rsi_percentile": 60}
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_fund_tech_data(state)

            # ASSERT: Returns empty dict
            assert result == {}

            # ASSERT: Logged checkpoint
            log_messages = [str(call) for call in mock_logger.info.call_args_list]
            assert any("SINK 2" in msg for msg in log_messages)

            # ASSERT: Validated fundamental count
            assert any("Fundamental: 1/6" in msg for msg in log_messages), \
                "Should count populated fundamental sources"

            # ASSERT: Validated technical fields
            assert any("Indicators=2 fields" in msg for msg in log_messages)
            assert any("Percentiles=1 fields" in msg for msg in log_messages)

    def test_merge_fund_tech_data_counts_populated_sources(self):
        """Verify SINK 2 correctly counts only populated fundamental sources"""
        state = {
            "ticker": "DBS19",
            # Only 3 of 6 fundamental sources populated
            "news": [{"title": "Test"}],
            "alpaca_data": {"quote": {}},
            "financial_markets_data": {},  # Empty
            "sec_filing_data": {},  # Empty
            "portfolio_insights": {},  # Empty
            "comparative_data": {"NVDA19": []},  # Populated
            # Technical data
            "indicators": {},
            "percentiles": {}
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_fund_tech_data(state)

            log_messages = [str(call) for call in mock_logger.info.call_args_list]

            # ASSERT: Counts 3/6 sources (news, alpaca, comparative have data)
            assert any("Fundamental: 3/6" in msg for msg in log_messages), \
                f"Should count 3 populated sources, logs: {log_messages}"

    def test_merge_all_pipelines_validates_final_state(self):
        """Verify SINK 3 validates scores + insights + chart ready"""
        state = {
            "ticker": "DBS19",
            # Scores (various _score fields)
            "faithfulness_score": {"score": 0.9},
            "completeness_score": {"score": 0.8},
            # Comparative insights
            "comparative_insights": {"peer_performance": "outperforming"},
            # Chart
            "chart_base64": "iVBORw0KGgoAAAANS..."
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_all_pipelines(state)

            # ASSERT: Returns empty dict
            assert result == {}

            # ASSERT: Logged checkpoint
            log_messages = [str(call) for call in mock_logger.info.call_args_list]
            assert any("SINK 3" in msg for msg in log_messages)
            assert any("FINAL MERGE" in msg for msg in log_messages)

            # ASSERT: Validated all components
            assert any("Scores: present" in msg for msg in log_messages)
            assert any("Comparative insights: present" in msg for msg in log_messages)
            assert any("Chart: generated" in msg for msg in log_messages)

    def test_merge_all_pipelines_detects_missing_components(self):
        """Verify SINK 3 detects missing scores, insights, or chart"""
        state = {
            "ticker": "DBS19",
            # No scores
            # No insights
            "comparative_insights": {},
            # No chart
            "chart_base64": ""
        }

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            result = self.workflow_nodes.merge_all_pipelines(state)

            log_messages = [str(call) for call in mock_logger.info.call_args_list]

            # ASSERT: Detected missing components
            assert any("Scores: missing" in msg for msg in log_messages)
            assert any("Comparative insights: empty" in msg for msg in log_messages)
            assert any("Chart: missing" in msg for msg in log_messages)

    def test_sink_nodes_return_dict_not_none(self):
        """Verify all sink nodes return dict, not None"""
        state = {"ticker": "DBS19"}

        with patch('src.workflow.workflow_nodes.logger'):
            result1 = self.workflow_nodes.merge_fundamental_data(state)
            result2 = self.workflow_nodes.merge_fund_tech_data(state)
            result3 = self.workflow_nodes.merge_all_pipelines(state)

            # ASSERT: All return dict, not None
            assert isinstance(result1, dict), "SINK 1 should return dict"
            assert isinstance(result2, dict), "SINK 2 should return dict"
            assert isinstance(result3, dict), "SINK 3 should return dict"

            # ASSERT: All return empty dict (validation only)
            assert result1 == {}
            assert result2 == {}
            assert result3 == {}

    def test_sink_logging_always_enabled(self):
        """Verify sink nodes always log checkpoints (not conditional)"""
        state = {"ticker": "DBS19"}

        with patch('src.workflow.workflow_nodes.logger') as mock_logger:
            self.workflow_nodes.merge_fundamental_data(state)
            self.workflow_nodes.merge_fund_tech_data(state)
            self.workflow_nodes.merge_all_pipelines(state)

            # ASSERT: All 3 sinks logged checkpoints
            assert mock_logger.info.call_count >= 9, \
                "Each sink should log at least 3 lines (header, body, footer)"
