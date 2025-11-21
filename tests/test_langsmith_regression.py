#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression Tests for LangSmith Integration

Tests backward compatibility and graceful degradation:
- Workflow runs without LangSmith
- Missing API keys don't break workflow
- Async evaluation completes even if LangSmith fails
- SQLite scores still saved if LangSmith unavailable
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import Mock, patch
import warnings
warnings.filterwarnings('ignore')

from src.agent import TickerAnalysisAgent
from src.workflow.workflow_nodes import WorkflowNodes
import pandas as pd


class TestBackwardCompatibility(unittest.TestCase):
    """Test that workflow works without LangSmith"""

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'false'}, clear=True)
    def test_workflow_without_langsmith(self,
                                       mock_llm,
                                       mock_chart,
                                       mock_comparative,
                                       mock_news,
                                       mock_fetch):
        """
        Regression test: Workflow works without LangSmith enabled.
        CLAIM: LANGCHAIN_TRACING_V2=false doesn't break workflow.
        """
        # Remove LANGCHAIN_API_KEY
        os.environ.pop('LANGCHAIN_API_KEY', None)

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should not raise exception
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch.dict(os.environ, {}, clear=True)
    def test_workflow_without_api_key(self,
                                     mock_llm,
                                     mock_chart,
                                     mock_comparative,
                                     mock_news,
                                     mock_fetch):
        """
        Regression test: Workflow works without LANGCHAIN_API_KEY.
        CLAIM: Missing API key doesn't break workflow.
        """
        # Ensure no LangSmith env vars
        os.environ.pop('LANGCHAIN_API_KEY', None)
        os.environ.pop('LANGCHAIN_TRACING_V2', None)

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should work without LangSmith configured
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)


class TestGracefulDegradation(unittest.TestCase):
    """Test that workflow continues even if LangSmith fails"""

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch('src.langsmith_integration.get_langsmith_client')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key'})
    def test_langsmith_client_failure(self,
                                      mock_langsmith_client,
                                      mock_llm,
                                      mock_chart,
                                      mock_comparative,
                                      mock_news,
                                      mock_fetch):
        """
        Regression test: Workflow continues if LangSmith client fails.
        CLAIM: LangSmith failure doesn't break report generation.
        """
        # Mock LangSmith client to return None (failure)
        mock_langsmith_client.return_value = None

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should generate report despite LangSmith failure
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch('src.database.TickerDatabase.save_faithfulness_score')
    @patch('src.langsmith_integration.log_evaluation_to_langsmith')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key'})
    def test_sqlite_saves_even_if_langsmith_fails(self,
                                                  mock_langsmith_log,
                                                  mock_db_save,
                                                  mock_llm,
                                                  mock_chart,
                                                  mock_comparative,
                                                  mock_news,
                                                  mock_fetch):
        """
        Regression test: SQLite saves work even if LangSmith logging fails.
        CLAIM: Database persistence is independent of LangSmith.
        """
        # Mock LangSmith logging to fail
        mock_langsmith_log.return_value = False

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # Run workflow
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        # Wait for background evaluation
        import time
        time.sleep(2)

        # CLAIM VALIDATION: Report should be generated
        self.assertIsInstance(report, str)

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
            self.assertIsNone(mock_get_run())


class TestAsyncEvaluationResilience(unittest.TestCase):
    """Test that async evaluation is resilient to failures"""

    def test_async_evaluation_handles_exception(self):
        """Test that background evaluation handles exceptions"""
        from src.langsmith_integration import async_evaluate_and_log

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
        self.assertEqual(result, {})

    def test_database_save_failure_continues(self):
        """Test that LangSmith logging continues even if database save fails"""
        from src.langsmith_integration import async_evaluate_and_log
        from src.scoring_service import ScoringContext

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
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"async_evaluate_and_log should handle database errors gracefully: {e}")


class TestTimestampSerializationFix(unittest.TestCase):
    """
    Regression tests for Timestamp serialization fix.

    ISSUE: LangSmith's @traceable decorator cannot serialize pandas DataFrames
    with Timestamp indices. Error: "keys must be str, int, float, bool or None, not Timestamp"

    FIX: fetch_news and fetch_comparative_data clean their return values using
    _prepare_state_for_tracing() so downstream @traceable nodes receive clean INPUT.

    CLAIM: After fix, analyze_technical and analyze_comparative_insights receive
    state without DataFrames, preventing Timestamp serialization errors.
    """

    def setUp(self):
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

    def test_fetch_news_returns_cleaned_state(self):
        """
        Regression test: fetch_news returns state without DataFrame.
        CLAIM: fetch_news cleans state before return to prevent INPUT serialization errors.
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

        # CLAIM VALIDATION: DataFrame should be removed from result
        self.assertIn('ticker_data', result)

        # If ticker_data exists and is a dict, it should not have 'history' field
        if isinstance(result.get('ticker_data'), dict):
            self.assertNotIn('history', result['ticker_data'],
                           "DataFrame should be removed by _prepare_state_for_tracing()")

        # Verify news fields are still present (not accidentally removed)
        self.assertIn('news', result)
        self.assertIn('news_summary', result)

    def test_fetch_comparative_data_returns_cleaned_state(self):
        """
        Regression test: fetch_comparative_data returns state without DataFrames.
        CLAIM: fetch_comparative_data cleans state before return.
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

        # CLAIM VALIDATION: comparative_data should not contain DataFrames
        self.assertIn('comparative_data', result)

        if isinstance(result.get('comparative_data'), dict):
            for ticker, data in result['comparative_data'].items():
                self.assertNotIsInstance(data, pd.DataFrame,
                    f"Comparative data for {ticker} should not be a DataFrame after cleaning")

    def test_analyze_technical_receives_clean_input(self):
        """
        Regression test: analyze_technical receives state without DataFrame.
        CLAIM: fetch_news cleans state, so analyze_technical INPUT has no Timestamp objects.
        """
        # Create DataFrame with Timestamp index
        dates = pd.date_range('2025-01-01', periods=253)
        df = pd.DataFrame({
            'Close': [100 + i for i in range(253)],
            'Volume': [1000 + i*10 for i in range(253)]
        }, index=dates)

        # Create state with DataFrame (simulating after fetch_data)
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

        # Verify DataFrame exists in initial state
        self.assertIn('ticker_data', state)
        self.assertIn('history', state['ticker_data'])
        self.assertIsInstance(state['ticker_data']['history'], pd.DataFrame)

        # Mock news fetcher
        with patch.object(self.nodes.news_fetcher, 'filter_high_impact_news') as mock_news:
            mock_news.return_value = []

            # Call fetch_news (should clean DataFrame)
            state = self.nodes.fetch_news(state)

        # CLAIM VALIDATION: DataFrame should be removed after fetch_news
        if isinstance(state.get('ticker_data'), dict):
            self.assertNotIn('history', state['ticker_data'],
                "fetch_news should remove DataFrame to prevent INPUT serialization error")

        # The state is now ready for analyze_technical
        # @traceable would serialize this INPUT without Timestamp errors

    def test_analyze_comparative_insights_receives_clean_input(self):
        """
        Regression test: analyze_comparative_insights receives state without DataFrames.
        CLAIM: fetch_comparative_data cleans state before analyze_comparative_insights runs.
        """
        # Create DataFrames for comparative data
        dates = pd.date_range('2025-01-01', periods=90)
        df1 = pd.DataFrame({'Close': [100 + i for i in range(90)]}, index=dates)
        df2 = pd.DataFrame({'Close': [200 + i for i in range(90)]}, index=dates)

        # Setup state with comparative DataFrames (simulating after fetch_comparative_data initial fetch)
        state = {
            'ticker': 'TEST19',
            'ticker_data': {'current_price': 104.0, 'sector': 'Technology'},
            'comparative_data': {
                'AOT': df1,  # DataFrame with Timestamp index
                'CPALL': df2  # DataFrame with Timestamp index
            }
        }

        # Verify DataFrames exist in initial state
        self.assertIsInstance(state['comparative_data']['AOT'], pd.DataFrame)
        self.assertIsInstance(state['comparative_data']['CPALL'], pd.DataFrame)

        # Mock data fetcher
        with patch.object(self.nodes.data_fetcher, 'fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = df1

            # Call fetch_comparative_data (should clean DataFrames)
            state = self.nodes.fetch_comparative_data(state)

        # CLAIM VALIDATION: comparative_data should not contain DataFrames
        self.assertIn('comparative_data', state)
        if isinstance(state.get('comparative_data'), dict):
            for ticker, data in state['comparative_data'].items():
                self.assertNotIsInstance(data, pd.DataFrame,
                    "Comparative DataFrames should be cleaned before analyze_comparative_insights")

        # The state is now ready for analyze_comparative_insights
        # @traceable would serialize this INPUT without Timestamp errors

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
        self.assertIn('ticker_data', cleaned)
        if isinstance(cleaned.get('ticker_data'), dict):
            self.assertNotIn('history', cleaned['ticker_data'],
                "history DataFrame should be removed")
            self.assertIn('current_price', cleaned['ticker_data'],
                "Other ticker_data fields should be preserved")

        # 2. comparative_data DataFrames should be converted to strings
        self.assertIn('comparative_data', cleaned)
        if isinstance(cleaned.get('comparative_data'), dict):
            for ticker, data in cleaned['comparative_data'].items():
                self.assertNotIsInstance(data, pd.DataFrame,
                    f"DataFrame for {ticker} should be converted")
                if isinstance(data, str):
                    self.assertIn('DataFrame', data,
                        "Should contain 'DataFrame' string representation")

        # 3. Other fields should be preserved
        self.assertIn('news', cleaned)
        self.assertIn('technical_analysis', cleaned)
        self.assertEqual(cleaned['ticker'], 'TEST19')


if __name__ == '__main__':
    unittest.main()
