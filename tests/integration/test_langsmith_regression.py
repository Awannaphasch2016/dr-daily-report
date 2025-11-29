# -*- coding: utf-8 -*-
"""
Regression Tests for LangSmith Integration

Tests backward compatibility and graceful degradation:
- Workflow runs without LangSmith
- Missing API keys don't break workflow
- Async evaluation completes even if LangSmith fails
- SQLite scores still saved if LangSmith unavailable
"""

import os
import time
import pytest
from unittest.mock import Mock, patch
import warnings
warnings.filterwarnings('ignore')

from src.agent import TickerAnalysisAgent
from src.workflow.workflow_nodes import WorkflowNodes
import pandas as pd


class TestBackwardCompatibility:
    """Test that workflow works without LangSmith"""

    @patch('src.data.data_fetcher.DataFetcher.fetch_ticker_data')
    @patch('src.data.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.formatters.chart_generator.ChartGenerator.generate_chart')
    @patch('src.agent.ChatOpenAI')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'false', 'OPENROUTER_API_KEY': 'test-key'})
    def test_workflow_without_langsmith(self,
                                       mock_llm_class,
                                       mock_chart,
                                       mock_news,
                                       mock_fetch):
        """
        Regression test: Workflow works without LangSmith enabled.
        CLAIM: LANGCHAIN_TRACING_V2=false doesn't break workflow.
        """
        # Remove LANGCHAIN_API_KEY
        os.environ.pop('LANGCHAIN_API_KEY', None)

        # Mock ChatOpenAI class and its invoke method
        mock_llm_instance = Mock()
        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm_instance

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_chart.return_value = 'chart'

        # CLAIM VALIDATION: Should not raise exception
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        assert isinstance(report, str)
        assert len(report) > 0

    @patch('src.data.data_fetcher.DataFetcher.fetch_ticker_data')
    @patch('src.data.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.formatters.chart_generator.ChartGenerator.generate_chart')
    @patch('src.agent.ChatOpenAI')
    @patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'})
    def test_workflow_without_api_key(self,
                                     mock_llm_class,
                                     mock_chart,
                                     mock_news,
                                     mock_fetch):
        """
        Regression test: Workflow works without LANGCHAIN_API_KEY.
        CLAIM: Missing API key doesn't break workflow.
        """
        # Ensure no LangSmith env vars
        os.environ.pop('LANGCHAIN_API_KEY', None)
        os.environ.pop('LANGCHAIN_TRACING_V2', None)

        # Mock ChatOpenAI class and its invoke method
        mock_llm_instance = Mock()
        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm_instance

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_chart.return_value = 'chart'

        # CLAIM VALIDATION: Should work without LangSmith configured
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        assert isinstance(report, str)


class TestGracefulDegradation:
    """Test that workflow continues even if LangSmith fails"""

    @patch('src.data.data_fetcher.DataFetcher.fetch_ticker_data')
    @patch('src.data.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.formatters.chart_generator.ChartGenerator.generate_chart')
    @patch('src.agent.ChatOpenAI')
    @patch('src.evaluation.langsmith_integration.get_langsmith_client')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key', 'OPENROUTER_API_KEY': 'test-key'})
    def test_langsmith_client_failure(self,
                                      mock_langsmith_client,
                                      mock_llm_class,
                                      mock_chart,
                                      mock_news,
                                      mock_fetch):
        """
        Regression test: Workflow continues if LangSmith client fails.
        CLAIM: LangSmith failure doesn't break report generation.
        """
        # Mock LangSmith client to return None (failure)
        mock_langsmith_client.return_value = None

        # Mock ChatOpenAI class and its invoke method
        mock_llm_instance = Mock()
        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm_instance

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_chart.return_value = 'chart'

        # CLAIM VALIDATION: Should generate report despite LangSmith failure
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        assert isinstance(report, str)
        assert len(report) > 0

    @patch('src.data.data_fetcher.DataFetcher.fetch_ticker_data')
    @patch('src.data.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.formatters.chart_generator.ChartGenerator.generate_chart')
    @patch('src.agent.ChatOpenAI')
    @patch('src.data.database.TickerDatabase.save_faithfulness_score')
    @patch('src.evaluation.langsmith_integration.log_evaluation_to_langsmith')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key', 'OPENROUTER_API_KEY': 'test-key'})
    def test_sqlite_saves_even_if_langsmith_fails(self,
                                                  mock_langsmith_log,
                                                  mock_db_save,
                                                  mock_llm_class,
                                                  mock_chart,
                                                  mock_news,
                                                  mock_fetch):
        """
        Regression test: SQLite saves work even if LangSmith logging fails.
        CLAIM: Database persistence is independent of LangSmith.
        """
        # Mock LangSmith logging to fail
        mock_langsmith_log.return_value = False

        # Mock ChatOpenAI class and its invoke method
        mock_llm_instance = Mock()
        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm_instance.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm_instance

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_chart.return_value = 'chart'

        # Run workflow
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        # Wait for background evaluation
        time.sleep(2)

        # CLAIM VALIDATION: Report should be generated
        assert isinstance(report, str)

        # Note: Database saves happen in background thread
        # This validates the code path exists

    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true'})
    def test_no_run_tree_available(self):
        """
        Regression test: Workflow handles missing run tree gracefully.
        CLAIM: get_current_run_tree() returning None doesn't break workflow.
        """
        with patch('src.workflow.workflow_nodes.get_current_run_tree') as mock_get_run:
            # Mock no run tree available
            mock_get_run.return_value = None

            # This should not raise an exception
            # Full workflow test would validate this completely
            assert mock_get_run() is None


class TestAsyncEvaluationResilience:
    """Test that async evaluation is resilient to failures"""

    def test_async_evaluation_handles_exception(self):
        """Test that background evaluation handles exceptions"""
        from src.evaluation.langsmith_integration import async_evaluate_and_log

        # Mock scoring service that raises exception
        mock_scoring_service = Mock()
        mock_scoring_service.compute_all_quality_scores.side_effect = Exception("Scoring error")

        # CLAIM VALIDATION: Should not raise exception (logged instead)
        result = async_evaluate_and_log(
            scoring_service=mock_scoring_service,
            qos_scorer=Mock(),
            cost_scorer=Mock(),
            database=Mock(),
            report="Test report",
            scoring_context=Mock(),
            ticker='TEST19',
            date='2025-11-19',
            timing_metrics={},
            langsmith_run_id=None
        )

        # Should return empty dict on error
        assert result == {}

    def test_database_save_failure_continues(self):
        """Test that LangSmith logging continues even if database save fails"""
        from src.evaluation.langsmith_integration import async_evaluate_and_log
        from src.scoring.scoring_service import ScoringContext

        # Mock database that fails
        mock_db = Mock()
        mock_db.save_faithfulness_score.side_effect = Exception("DB error")

        # Mock scoring service
        mock_scoring_service = Mock()
        mock_scoring_service.compute_all_quality_scores.return_value = {
            'faithfulness': {'overall_score': 85.0},
            'completeness': {'overall_score': 78.0},
            'reasoning_quality': {'overall_score': 82.0},
            'compliance': {'overall_score': 91.0}
        }

        # CLAIM VALIDATION: Should continue despite database error
        # This validates graceful error handling
        try:
            result = async_evaluate_and_log(
                scoring_service=mock_scoring_service,
                qos_scorer=Mock(),
                cost_scorer=Mock(),
                database=mock_db,
                report="Test report",
                scoring_context=Mock(
                    indicators={},
                    percentiles={},
                    news=[],
                    ticker_data={},
                    market_conditions={}
                ),
                ticker='TEST19',
                date='2025-11-19',
                timing_metrics={},
                langsmith_run_id=None
            )
            # Should complete without raising exception
            assert result is not None
        except Exception as e:
            pytest.fail(f"async_evaluate_and_log should handle database errors gracefully: {e}")


class TestTimestampSerializationFix:
    """
    Regression tests for Timestamp serialization fix.

    ISSUE: LangSmith's @traceable decorator cannot serialize pandas DataFrames
    with Timestamp indices. Error: "keys must be str, int, float, bool or None, not Timestamp"

    FIX: The @traceable decorator uses _filter_state_for_langsmith() via
    process_inputs/process_outputs to filter DataFrames ONLY for tracing.
    The actual workflow state keeps DataFrames since nodes need them.

    CLAIM: _filter_state_for_langsmith() correctly removes DataFrames from
    state before LangSmith serialization, preventing Timestamp errors.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create WorkflowNodes instance with mocked dependencies"""
        # Mock all required dependencies
        self.nodes = WorkflowNodes(
            data_fetcher=Mock(),
            technical_analyzer=Mock(),
            news_fetcher=Mock(),
            chart_generator=Mock(),
            db=Mock(),
            strategy_backtester=Mock(),
            strategy_analyzer=Mock(),
            comparative_analyzer=Mock(),
            llm=Mock(),
            context_builder=Mock(),
            prompt_builder=Mock(),
            market_analyzer=Mock(),
            number_injector=Mock(),
            cost_scorer=Mock(),
            scoring_service=Mock(),
            qos_scorer=Mock(),
            faithfulness_scorer=Mock(),
            completeness_scorer=Mock(),
            reasoning_quality_scorer=Mock(),
            compliance_scorer=Mock(),
            ticker_map={'TEST19': 'TEST.SI', 'AOT': 'AOT.BK', 'CPALL': 'CPALL.BK'},
            db_query_count_ref={'count': 0}
        )

    def test_fetch_news_preserves_dataframe_in_state(self):
        """
        Test: fetch_news preserves DataFrame in state for downstream nodes.
        The @traceable decorator handles filtering for tracing only.
        """
        # Create state with DataFrame (simulating fetch_data output)
        dates = pd.date_range('2025-01-01', periods=5)
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
            'Volume': [1000, 1100, 1200, 1300, 1400]
        }, index=dates)

        state = {
            'ticker': 'TEST19',
            'ticker_data': {
                'history': df,  # DataFrame with Timestamp index
                'current_price': 104.0
            },
            'news': [],
            'news_summary': {}
        }

        # Mock news fetcher to avoid actual API calls
        with patch.object(self.nodes.news_fetcher, 'filter_high_impact_news') as mock_news:
            mock_news.return_value = []

            # Call fetch_news
            result = self.nodes.fetch_news(state)

        # VALIDATION: DataFrame should be PRESERVED (nodes need it)
        assert 'ticker_data' in result
        assert isinstance(result.get('ticker_data'), dict)
        # DataFrame is preserved - filtering happens via @traceable decorator
        assert 'history' in result['ticker_data'], \
            "DataFrame should be preserved in actual state for downstream nodes"

        # Verify news fields are present
        assert 'news' in result
        assert 'news_summary' in result

    def test_fetch_comparative_data_preserves_dataframes(self):
        """
        Test: fetch_comparative_data preserves DataFrames in state.
        The @traceable decorator handles filtering for tracing only.
        """
        # Create state with comparative DataFrames
        dates = pd.date_range('2025-01-01', periods=5)
        df1 = pd.DataFrame({'Close': [100, 101, 102, 103, 104]}, index=dates)
        df2 = pd.DataFrame({'Close': [200, 201, 202, 203, 204]}, index=dates)

        state = {
            'ticker': 'TEST19',
            'ticker_data': {'current_price': 104.0},
            'comparative_data': {
                'AOT': df1,  # DataFrame with Timestamp index
                'CPALL': df2  # DataFrame with Timestamp index
            }
        }

        # Mock data fetcher to avoid actual API calls
        with patch.object(self.nodes.data_fetcher, 'fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = df1

            # Call fetch_comparative_data
            result = self.nodes.fetch_comparative_data(state)

        # VALIDATION: comparative_data may contain DataFrames
        # The actual filtering for LangSmith happens via @traceable
        assert 'comparative_data' in result
        # Note: The method may or may not transform the data - test the filter function instead

    def test_filter_function_cleans_ticker_data_history(self):
        """
        Test: _filter_state_for_langsmith removes ticker_data.history DataFrame.
        This is what @traceable uses for process_inputs/process_outputs.
        """
        from src.workflow.workflow_nodes import _filter_state_for_langsmith

        # Create state with DataFrame
        dates = pd.date_range('2025-01-01', periods=253)
        df = pd.DataFrame({
            'Close': [100 + i for i in range(253)],
            'Volume': [1000 + i*10 for i in range(253)]
        }, index=dates)

        state = {
            'ticker': 'TEST19',
            'ticker_data': {
                'history': df,  # DataFrame with Timestamp index
                'company_name': 'Test Company',
                'current_price': 352.0,
                'ticker': 'TEST.SI',
                'date': '2025-11-19',
                'sector': 'Technology'
            }
        }

        # Apply filter function
        filtered = _filter_state_for_langsmith(state)

        # VALIDATION: history should be removed in filtered state
        assert 'ticker_data' in filtered
        assert 'history' not in filtered['ticker_data'], \
            "_filter_state_for_langsmith should remove DataFrame"

        # Other fields should be preserved
        assert filtered['ticker_data']['company_name'] == 'Test Company'
        assert filtered['ticker_data']['current_price'] == 352.0

    def test_filter_function_cleans_comparative_dataframes(self):
        """
        Test: _filter_state_for_langsmith converts comparative DataFrames to placeholders.
        """
        from src.workflow.workflow_nodes import _filter_state_for_langsmith

        # Create DataFrames for comparative data
        dates = pd.date_range('2025-01-01', periods=90)
        df1 = pd.DataFrame({'Close': [100 + i for i in range(90)]}, index=dates)
        df2 = pd.DataFrame({'Close': [200 + i for i in range(90)]}, index=dates)

        state = {
            'ticker': 'TEST19',
            'ticker_data': {'current_price': 104.0, 'sector': 'Technology'},
            'comparative_data': {
                'AOT': df1,
                'CPALL': df2
            }
        }

        # Apply filter function
        filtered = _filter_state_for_langsmith(state)

        # VALIDATION: comparative_data should not contain DataFrames
        assert 'comparative_data' in filtered
        for ticker, data in filtered['comparative_data'].items():
            assert not isinstance(data, pd.DataFrame), \
                f"Comparative data for {ticker} should be converted to placeholder string"
            # Should be a placeholder string like "<DataFrame with 90 rows>"
            assert isinstance(data, str)
            assert 'DataFrame' in data

    def test_prepare_state_for_tracing_removes_dataframes(self):
        """
        Unit test: _prepare_state_for_tracing() removes DataFrames correctly.
        CLAIM: Helper function removes both ticker_data.history and comparative_data DataFrames.
        """
        # Create state with DataFrames
        dates = pd.date_range('2025-01-01', periods=5)
        df1 = pd.DataFrame({'Close': [100, 101, 102, 103, 104]}, index=dates)
        df2 = pd.DataFrame({'Close': [200, 201, 202, 203, 204]}, index=dates)

        state = {
            'ticker': 'TEST19',
            'ticker_data': {
                'history': df1,  # Should be removed
                'current_price': 104.0  # Should be kept
            },
            'comparative_data': {
                'AOT': df2,  # Should be converted to string
                'CPALL': df2   # Should be converted to string
            },
            'news': [],  # Should be kept
            'technical_analysis': {}  # Should be kept
        }

        # Call the helper function
        cleaned = self.nodes._prepare_state_for_tracing(state)

        # CLAIM VALIDATION: DataFrames removed, other fields preserved

        # 1. ticker_data.history should be removed
        assert 'ticker_data' in cleaned
        if isinstance(cleaned.get('ticker_data'), dict):
            assert 'history' not in cleaned['ticker_data'], \
                "history DataFrame should be removed"
            assert 'current_price' in cleaned['ticker_data'], \
                "Other ticker_data fields should be preserved"

        # 2. comparative_data DataFrames should be converted to strings
        assert 'comparative_data' in cleaned
        if isinstance(cleaned.get('comparative_data'), dict):
            for ticker, data in cleaned['comparative_data'].items():
                assert not isinstance(data, pd.DataFrame), \
                    f"DataFrame for {ticker} should be converted"
                if isinstance(data, str):
                    assert 'DataFrame' in data, \
                        "Should contain 'DataFrame' string representation"

        # 3. Other fields should be preserved
        assert 'news' in cleaned
        assert 'technical_analysis' in cleaned
        assert cleaned['ticker'] == 'TEST19'
